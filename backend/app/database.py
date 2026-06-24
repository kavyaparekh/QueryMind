"""Database connection helpers for QueryMind.

Two connections are used:
  - admin_conn   — full privileges, used only for schema inspection.
  - readonly_conn — querymind_ro role, SELECT only, used for all query execution.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://querymind:querymind@localhost:5432/querymind",
)
READONLY_DATABASE_URL = os.getenv(
    "READONLY_DATABASE_URL",
    "postgresql://querymind_ro:querymind_ro_pass@localhost:5432/querymind",
)
QUERY_TIMEOUT_MS = int(os.getenv("QUERY_TIMEOUT_MS", "5000"))
QUERY_ROW_LIMIT = int(os.getenv("QUERY_ROW_LIMIT", "500"))


@contextmanager
def admin_conn():
    """Yield a psycopg2 connection with admin privileges."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def readonly_conn():
    """Yield a psycopg2 connection restricted to SELECT only."""
    conn = psycopg2.connect(READONLY_DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def serialize_value(v: Any) -> Any:
    """Convert DB types that are not JSON-serialisable."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def serialize_row(row: dict) -> dict:
    return {k: serialize_value(val) for k, val in row.items()}
