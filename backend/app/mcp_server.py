"""QueryMind MCP Server.

Exposes the Chinook database as 5 tools that any MCP-compatible client
(Claude Desktop, Cursor, etc.) can call directly.

Run via:
    PYTHONPATH=backend .venv/bin/python -m app.mcp_server

Or via the Makefile:
    make mcp
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import sqlglot
import sqlglot.expressions as exp
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from psycopg2.extras import RealDictCursor

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.database import (
    QUERY_ROW_LIMIT,
    QUERY_TIMEOUT_MS,
    admin_conn,
    readonly_conn,
    serialize_row,
)

mcp = FastMCP(
    "QueryMind",
    instructions=(
        "You have access to the Chinook music database. "
        "Use list_tables to discover available tables, get_table_schema to inspect "
        "columns, search_schema to find relevant tables by keyword, validate_query "
        "to check your SQL before running it, and run_query to execute SELECT statements."
    ),
)

_EXCLUDED_TABLES = {"schema_embeddings"}


# ── Tool 1: list_tables ────────────────────────────────────────────────────────

@mcp.tool()
def list_tables() -> str:
    """Return a list of all queryable tables in the database."""
    with admin_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type   = 'BASE TABLE'
                ORDER BY table_name;
                """
            )
            rows = cur.fetchall()

    tables = [r[0] for r in rows if r[0] not in _EXCLUDED_TABLES]
    return json.dumps(tables)


# ── Tool 2: get_table_schema ──────────────────────────────────────────────────

@mcp.tool()
def get_table_schema(table_name: str) -> str:
    """Return the columns and data types for a specific table.

    Args:
        table_name: Name of the table to inspect (e.g. 'invoice_line').
    """
    with admin_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name   = %s
                ORDER BY ordinal_position;
                """,
                (table_name,),
            )
            rows = cur.fetchall()

    if not rows:
        return json.dumps({"error": f"Table '{table_name}' not found."})

    columns = [
        {
            "column": col,
            "type": dtype,
            "nullable": nullable == "YES",
        }
        for col, dtype, nullable in rows
    ]
    return json.dumps({"table": table_name, "columns": columns})


# ── Tool 3: search_schema ─────────────────────────────────────────────────────

@mcp.tool()
def search_schema(query: str, top_k: int = 5) -> str:
    """Semantic search over the schema — returns the most relevant tables.

    Embeds the query with Voyage AI and compares against schema_embeddings.
    Use this to find which tables are relevant before writing SQL.

    Args:
        query: Natural language description of what you're looking for.
        top_k: Number of tables to return (default 5).
    """
    import time
    import voyageai

    voyage_model = os.getenv("EMBEDDING_MODEL", "voyage-3")
    vc = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])

    try:
        result = vc.embed([query], model=voyage_model, input_type="query")
    except Exception as exc:
        if "rate" in str(exc).lower():
            time.sleep(20)
            result = vc.embed([query], model=voyage_model, input_type="query")
        else:
            raise

    embedding = result.embeddings[0]
    vec_literal = "[" + ",".join(str(x) for x in embedding) + "]"

    with readonly_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT object_name, description
                FROM schema_embeddings
                WHERE object_type = 'table'
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (vec_literal, top_k),
            )
            rows = cur.fetchall()

    if not rows:
        return json.dumps({
            "error": "schema_embeddings is empty — run make embed first."
        })

    results = [{"table": name, "description": desc} for name, desc in rows]
    return json.dumps(results)


# ── Tool 4: validate_query ────────────────────────────────────────────────────

@mcp.tool()
def validate_query(sql: str) -> str:
    """Check whether a SQL string is a valid, safe SELECT statement.

    Uses sqlglot to parse the SQL. Returns ok=true if the query is safe
    to run, or ok=false with a reason if it is not.

    Args:
        sql: The SQL query to validate.
    """
    try:
        statements = sqlglot.parse(sql, dialect="postgres")
    except Exception as exc:
        return json.dumps({"ok": False, "reason": f"Parse error: {exc}"})

    if not statements:
        return json.dumps({"ok": False, "reason": "No SQL statement found."})

    for stmt in statements:
        if not isinstance(stmt, exp.Select):
            return json.dumps({
                "ok": False,
                "reason": (
                    f"Only SELECT statements are permitted. "
                    f"Got: {type(stmt).__name__}"
                ),
            })

    return json.dumps({"ok": True, "reason": "Valid SELECT statement."})


# ── Tool 5: run_query ─────────────────────────────────────────────────────────

@mcp.tool()
def run_query(sql: str) -> str:
    """Execute a SELECT query against the Chinook database and return results.

    The query runs under a read-only role — INSERT, UPDATE, DELETE, and DDL
    are blocked at the database level. A 5-second timeout and 500-row cap
    are enforced.

    Always call validate_query first to confirm your SQL is safe.

    Args:
        sql: A SELECT statement to execute.
    """
    # Enforce SELECT-only at the application layer too
    validation = json.loads(validate_query(sql))
    if not validation["ok"]:
        return json.dumps({"error": validation["reason"], "rows": []})

    try:
        with readonly_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SET statement_timeout = {QUERY_TIMEOUT_MS}")
                cur.execute(sql)
                raw_rows = cur.fetchmany(QUERY_ROW_LIMIT)
        rows = [serialize_row(dict(r)) for r in raw_rows]
        return json.dumps({"rows": rows, "row_count": len(rows)})
    except Exception as exc:
        return json.dumps({"error": str(exc), "rows": []})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
