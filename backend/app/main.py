"""QueryMind FastAPI application.

Phase 1: single-pass pipeline.
  POST /chat  →  fetch full schema  →  Claude generates SQL  →
  validate (SELECT only)  →  execute (read-only role)  →
  Claude formats answer  →  return response.

Phase 2 will replace this with the full LangGraph agent.
"""

from __future__ import annotations

import time

import sqlglot
import sqlglot.expressions as exp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import RealDictCursor

from app.database import (
    QUERY_ROW_LIMIT,
    QUERY_TIMEOUT_MS,
    readonly_conn,
    serialize_row,
)
from app.llm.anthropic_client import AnthropicClient
from app.models import ChatRequest, ChatResponse
from app.schema_fetcher import fetch_full_schema

app = FastAPI(
    title="QueryMind",
    description="Natural-language-to-SQL agent with safety guardrails.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server (Phase 5)
    allow_methods=["*"],
    allow_headers=["*"],
)

_llm = AnthropicClient()


def _validate_sql(sql: str) -> None:
    """Reject anything that is not a pure SELECT statement.

    Uses sqlglot to parse the SQL so this check works regardless of
    whitespace, casing, or comments.
    """
    try:
        statements = sqlglot.parse(sql, dialect="postgres")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"SQL parse error: {exc}")

    if not statements:
        raise HTTPException(status_code=400, detail="No SQL statement found.")

    for stmt in statements:
        if not isinstance(stmt, exp.Select):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Only SELECT statements are permitted. "
                    f"Received: {type(stmt).__name__}"
                ),
            )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "phase": 1}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Single-pass NL-to-SQL pipeline.

    1. Fetch full schema from Postgres.
    2. Ask Claude to generate SQL + reasoning.
    3. Validate: SELECT only.
    4. Execute against the read-only role with timeout + row cap.
    5. Ask Claude to format a plain-English answer.
    6. Return answer, SQL, reasoning, and raw rows.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. Schema
    try:
        schema = fetch_full_schema()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Schema fetch failed: {exc}")

    # 2. Generate SQL
    try:
        sql, reasoning = _llm.generate_sql(question, schema)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SQL generation failed: {exc}")

    # 3. Validate
    _validate_sql(sql)

    # 4. Execute
    try:
        with readonly_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SET statement_timeout = {QUERY_TIMEOUT_MS}")
                t0 = time.perf_counter()
                cur.execute(sql)
                raw_rows = cur.fetchmany(QUERY_ROW_LIMIT)
                execution_time_ms = (time.perf_counter() - t0) * 1000
        rows = [serialize_row(dict(r)) for r in raw_rows]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {exc}")

    # 5. Format answer
    try:
        answer = _llm.format_answer(question, sql, rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Answer formatting failed: {exc}")

    return ChatResponse(
        answer=answer,
        sql=sql,
        reasoning=reasoning,
        rows=rows,
        row_count=len(rows),
        execution_time_ms=round(execution_time_ms, 2),
    )
