"""Populate schema_embeddings with Voyage AI embeddings.

Run once after seeding the database, or any time the schema changes:

    PYTHONPATH=backend .venv/bin/python backend/scripts/embed_schema.py

Each public table gets one embedding whose description includes all its
columns.  Existing rows for a table are deleted before re-inserting so
the script is safe to re-run (idempotent).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
import voyageai
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]
VOYAGE_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-3")

_EXCLUDED_TABLES = {"schema_embeddings"}

_SCHEMA_QUERY = """
    SELECT
        c.table_name,
        c.column_name,
        c.data_type,
        c.is_nullable
    FROM information_schema.columns c
    JOIN information_schema.tables  t
        ON  c.table_name   = t.table_name
        AND c.table_schema = t.table_schema
    WHERE c.table_schema = 'public'
      AND t.table_type   = 'BASE TABLE'
    ORDER BY c.table_name, c.ordinal_position;
"""


def _build_table_descriptions() -> dict[str, str]:
    """Return {table_name: description_text} for every public table."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_QUERY)
            rows = cur.fetchall()
    finally:
        conn.close()

    tables: dict[str, list[str]] = {}
    for table_name, col_name, data_type, is_nullable in rows:
        if table_name in _EXCLUDED_TABLES:
            continue
        nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
        tables.setdefault(table_name, []).append(
            f"{col_name} ({data_type}, {nullable})"
        )

    return {
        name: f"Table: {name}. Columns: {', '.join(cols)}."
        for name, cols in tables.items()
    }


def _upsert_embeddings(
    descriptions: dict[str, str],
    embeddings: list[list[float]],
) -> None:
    """Delete existing rows for each table then insert fresh ones."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            for (table_name, description), embedding in zip(
                descriptions.items(), embeddings
            ):
                cur.execute(
                    "DELETE FROM schema_embeddings WHERE object_type = 'table' AND object_name = %s",
                    (table_name,),
                )
                cur.execute(
                    """
                    INSERT INTO schema_embeddings (object_type, object_name, description, embedding)
                    VALUES ('table', %s, %s, %s)
                    """,
                    (table_name, description, embedding),
                )
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    print("=" * 55)
    print("  QueryMind — Embed Schema")
    print("=" * 55)

    print("  Fetching table descriptions from Postgres...")
    descriptions = _build_table_descriptions()
    print(f"  Found {len(descriptions)} tables to embed.")

    texts = list(descriptions.values())

    print(f"  Calling Voyage AI ({VOYAGE_MODEL}) for {len(texts)} embeddings...")
    vc = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    result = vc.embed(texts, model=VOYAGE_MODEL, input_type="document")
    embeddings = result.embeddings
    print(f"  Received {len(embeddings)} embeddings (dim={len(embeddings[0])}).")

    print("  Upserting into schema_embeddings...")
    _upsert_embeddings(descriptions, embeddings)

    print(f"  Done. {len(descriptions)} tables embedded and stored.")
    print()


if __name__ == "__main__":
    main()
