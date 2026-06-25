"""Fetch the full database schema and format it for prompt injection.

Phase 1 dumps the entire schema into every prompt.
Phase 2 will replace this with a pgvector semantic top-k retrieval.
"""

from __future__ import annotations

from app.database import admin_conn

# Tables owned by QueryMind internals — never expose to the LLM.
_EXCLUDED_TABLES = {"schema_embeddings"}

_SCHEMA_QUERY = """
    SELECT
        c.table_name,
        c.column_name,
        c.data_type,
        c.is_nullable
    FROM information_schema.columns  c
    JOIN information_schema.tables   t
        ON  c.table_name   = t.table_name
        AND c.table_schema = t.table_schema
    WHERE c.table_schema = 'public'
      AND t.table_type   = 'BASE TABLE'
    ORDER BY c.table_name, c.ordinal_position;
"""


def fetch_full_schema() -> str:
    """Return all public tables and columns as a formatted string.

    Example output:
        Table: Artist
          - ArtistId (integer, NOT NULL)
          - Name (character varying, NULL)

        Table: Album
          - AlbumId (integer, NOT NULL)
          ...
    """
    with admin_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_QUERY)
            rows = cur.fetchall()

    # Group columns by table
    tables: dict[str, list[tuple[str, str, str]]] = {}
    for table_name, col_name, data_type, is_nullable in rows:
        if table_name in _EXCLUDED_TABLES:
            continue
        tables.setdefault(table_name, []).append((col_name, data_type, is_nullable))

    lines: list[str] = []
    for table_name, columns in tables.items():
        lines.append(f"Table: {table_name}")
        for col_name, data_type, is_nullable in columns:
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            lines.append(f"  - {col_name} ({data_type}, {nullable})")
        lines.append("")

    return "\n".join(lines)
