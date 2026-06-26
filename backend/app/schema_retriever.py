"""Semantic schema retrieval using pgvector + Voyage AI.

Phase 2 replacement for schema_fetcher.py.
Embeds the user's question and returns only the top-k most relevant
tables rather than dumping the entire schema into every prompt.
"""

from __future__ import annotations

import os
import time

import voyageai

from app.database import readonly_conn

VOYAGE_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-3")
# Chinook has 11 tables; 8 ensures complex multi-table joins always have
# the necessary tables in context while still excluding irrelevant ones.
TOP_K = int(os.getenv("SCHEMA_TOP_K", "8"))

_voyage_client: voyageai.Client | None = None


def _get_voyage_client() -> voyageai.Client:
    global _voyage_client
    if _voyage_client is None:
        _voyage_client = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    return _voyage_client


def retrieve_relevant_schema(question: str) -> str:
    """Return a formatted schema string for the tables most relevant to question.

    Steps:
      1. Embed the question with Voyage AI (with one retry on rate-limit).
      2. Query schema_embeddings for the top-k nearest tables (cosine distance).
      3. Format and return in the same shape as fetch_full_schema().
    """
    vc = _get_voyage_client()
    try:
        result = vc.embed([question], model=VOYAGE_MODEL, input_type="query")
    except Exception as exc:
        if "rate" in str(exc).lower():
            time.sleep(20)
            result = vc.embed([question], model=VOYAGE_MODEL, input_type="query")
        else:
            raise
    question_embedding = result.embeddings[0]

    # Convert to a Postgres vector literal for the <=> cosine operator
    vec_literal = "[" + ",".join(str(x) for x in question_embedding) + "]"

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
                (vec_literal, TOP_K),
            )
            rows = cur.fetchall()

    if not rows:
        raise RuntimeError(
            "schema_embeddings is empty — run scripts/embed_schema.py first."
        )

    lines: list[str] = []
    for object_name, description in rows:
        # description is already a formatted string; convert to block style
        # e.g. "Table: Artist. Columns: ArtistId (integer, NOT NULL), Name (character varying, NULL)."
        lines.append(description)
        lines.append("")

    return "\n".join(lines).strip()
