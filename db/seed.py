#!/usr/bin/env python3
"""
Seed the QueryMind database with the Chinook sample dataset.

What this script does
─────────────────────
1. Downloads the official Chinook PostgreSQL SQL from GitHub.
2. Pipes it into psql running inside the Docker container (the most
   reliable approach — no need for psql on the host, handles multi-
   statement scripts, COPY, and psql metacommands correctly).
3. Grants SELECT on all tables to the read-only role (querymind_ro).
4. Verifies the seed by counting rows in the Artist table.

Usage
─────
    # From the project root:
    make seed

    # Or directly:
    cd db && pip install -r requirements.txt && python seed.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "querymind")
DB_USER = os.getenv("DB_USER", "querymind")
DB_PASSWORD = os.getenv("DB_PASSWORD", "querymind")

CHINOOK_SQL_URL = (
    "https://raw.githubusercontent.com/lerocha/chinook-database/"
    "master/ChinookDatabase/DataSources/Chinook_PostgreSql.sql"
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def _chinook_is_seeded() -> bool:
    """Return True if the Artist table already has rows."""
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS("
                "  SELECT 1 FROM information_schema.tables"
                "  WHERE table_schema = 'public' AND table_name = 'artist'"
                ")"
            )
            return cur.fetchone()[0]  # type: ignore[index]
    except psycopg2.OperationalError:
        return False


def _fetch_chinook_sql() -> bytes:
    print(f"  Downloading Chinook SQL from GitHub...", end=" ", flush=True)
    with urllib.request.urlopen(CHINOOK_SQL_URL, timeout=60) as resp:
        data = resp.read()
    print(f"{len(data):,} bytes")
    return data


def _apply_via_docker_psql(sql: bytes) -> None:
    """Pipe SQL into psql inside the running Docker container."""
    result = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "postgres",
            "psql", "-U", DB_USER, "-d", DB_NAME,
            "--set=ON_ERROR_STOP=1",
        ],
        input=sql,
        capture_output=True,
        cwd=ROOT_DIR,
    )
    stdout = result.stdout.decode(errors="replace")
    stderr = result.stderr.decode(errors="replace")

    # psql emits NOTICE messages to stderr — only fail on ERROR lines.
    error_lines = [l for l in stderr.splitlines() if "ERROR" in l]
    if error_lines or result.returncode not in (0, 3):
        # Exit code 3 = ON_ERROR_STOP hit; surface the context.
        raise RuntimeError(
            f"psql exited {result.returncode}.\n"
            f"stderr:\n{stderr[:2000]}\n"
            f"stdout:\n{stdout[:500]}"
        )


def _grant_readonly() -> None:
    """Explicitly grant SELECT on all current tables to querymind_ro.

    ALTER DEFAULT PRIVILEGES (set in 02_roles.sql) covers tables created
    after that init script ran, but an explicit GRANT ALL TABLES is a
    belt-and-suspenders safety net.
    """
    with _connect() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "GRANT SELECT ON ALL TABLES IN SCHEMA public TO querymind_ro;"
            )
            cur.execute(
                "GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO querymind_ro;"
            )


def _verify() -> int:
    """Return the row count of the Artist table as a smoke-test."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM "Artist"')
        return cur.fetchone()[0]  # type: ignore[index]


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 55)
    print("  QueryMind — Database Seed")
    print("=" * 55)

    if _chinook_is_seeded():
        print("  Chinook already seeded — skipping download/import.")
        print("  Re-granting read-only permissions (idempotent)...")
        _grant_readonly()
        artist_count = _verify()
        print(f"  Verified: {artist_count} artists in DB.")
        print("Done.")
        return

    # 1. Download
    chinook_sql = _fetch_chinook_sql()

    # 2. Apply via psql in Docker
    print("  Applying Chinook schema + data (may take ~30s)...", end=" ", flush=True)
    _apply_via_docker_psql(chinook_sql)
    print("OK")

    # 3. Permissions
    print("  Granting SELECT to querymind_ro...", end=" ", flush=True)
    _grant_readonly()
    print("OK")

    # 4. Verify
    artist_count = _verify()
    print(f"  Verified: {artist_count} artists in DB.")

    print()
    print("Seed complete!")
    print(f"  Admin URL:     postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"  Read-only URL: postgresql://querymind_ro@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print()
    print("Next step:  cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)
