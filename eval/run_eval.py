"""QueryMind Evaluation Harness — Phase 4.

Runs each NL question in eval_set.json through the /chat API, executes the
ground-truth SQL directly against the database, compares result sets (not raw
SQL text), and prints an accuracy report broken down by category.

Result-set comparison is value-based and order-insensitive: each row is
normalised to a sorted tuple of its values so that column aliases and row
ordering in the agent's SQL do not cause false failures.

Usage:
    # From repo root (backend must be running):
    make eval

    # Or directly:
    cd eval
    python run_eval.py [--api-url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(Path(__file__).parent.parent / ".env")

EVAL_SET_PATH = Path(__file__).parent / "eval_set.json"
DEFAULT_API_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
READONLY_DATABASE_URL = os.getenv(
    "READONLY_DATABASE_URL",
    "postgresql://querymind_ro:querymind_ro_pass@localhost:5432/querymind",
)


# ── Normalisation ─────────────────────────────────────────────────────────────

def _normalize_value(v: Any) -> str:
    """Convert a DB value to a canonical string for comparison."""
    if isinstance(v, float):
        return str(round(v, 2))
    if isinstance(v, Decimal):
        return str(round(float(v), 2))
    if v is None:
        return "NULL"
    return str(v)


def _normalize_row(row: dict) -> tuple:
    """Convert a row dict to a sorted tuple of normalised value strings.

    Sorting makes comparison insensitive to both column ordering and the
    column aliases used in the agent's generated SQL.
    """
    return tuple(sorted(_normalize_value(v) for v in row.values()))


def _normalize_rows(rows: list[dict]) -> Counter:
    """Return a multiset of normalised rows (handles duplicate rows correctly)."""
    return Counter(_normalize_row(r) for r in rows)


# ── Data loading ──────────────────────────────────────────────────────────────

def load_eval_set() -> list[dict]:
    with open(EVAL_SET_PATH) as f:
        data = json.load(f)
    return [e for e in data if "question" in e]


# ── Ground-truth execution ────────────────────────────────────────────────────

def run_ground_truth(sql: str) -> list[dict]:
    """Execute ground-truth SQL and return rows as list of dicts."""
    conn = psycopg2.connect(READONLY_DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Agent call ────────────────────────────────────────────────────────────────

def call_agent(question: str, api_url: str) -> list[dict] | None:
    """POST to /chat and return the rows field, or None on any failure."""
    try:
        resp = httpx.post(
            f"{api_url}/chat",
            json={"question": question},
            timeout=90.0,
        )
        if resp.status_code != 200:
            return None
        return resp.json().get("rows", [])
    except Exception:
        return None


# ── Evaluation loop ───────────────────────────────────────────────────────────

def run_eval(api_url: str) -> int:
    """Run the full eval. Returns the number of failing cases (exit code)."""
    cases = load_eval_set()
    total = len(cases)
    passed = 0
    by_category: dict[str, dict[str, int]] = defaultdict(lambda: {"pass": 0, "total": 0})
    failures: list[str] = []

    print(f"\nQueryMind Eval  —  {total} cases  |  API: {api_url}\n")
    print(f"{'#':<4} {'Category':<16} {'Result':<8} Question")
    print("─" * 76)

    for i, case in enumerate(cases, 1):
        question = case["question"]
        sql = case["sql"]
        category = case.get("category", "unknown")

        by_category[category]["total"] += 1

        try:
            truth_rows = run_ground_truth(sql)
        except Exception as exc:
            print(f"{i:<4} {category:<16} {'ERROR':<8} {question[:50]}")
            print(f"     Ground-truth SQL failed: {exc}")
            failures.append(question)
            continue

        agent_rows = call_agent(question, api_url)

        short_q = question[:50] + "…" if len(question) > 50 else question

        if agent_rows is not None and _normalize_rows(truth_rows) == _normalize_rows(agent_rows):
            result = "PASS"
            passed += 1
            by_category[category]["pass"] += 1
        else:
            result = "FAIL"
            failures.append(question)
            if agent_rows is None:
                result = "ERROR"

        print(f"{i:<4} {category:<16} {result:<8} {short_q}")

    print("─" * 76)
    pct = round(100 * passed / total) if total else 0
    print(f"\nOverall: {passed}/{total}  ({pct}%)\n")

    print("By category:")
    for cat in sorted(by_category):
        p = by_category[cat]["pass"]
        t = by_category[cat]["total"]
        cat_pct = round(100 * p / t) if t else 0
        print(f"  {cat:<16}  {p}/{t}  ({cat_pct}%)")

    if failures:
        print(f"\nFailed questions ({len(failures)}):")
        for q in failures:
            print(f"  • {q}")

    print()
    return total - passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QueryMind evaluation harness")
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"Backend API base URL (default: {DEFAULT_API_URL})",
    )
    args = parser.parse_args()

    sys.exit(run_eval(args.api_url))
