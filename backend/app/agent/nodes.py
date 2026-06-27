"""LangGraph node functions for the QueryMind agent.

Each node receives the full AgentState and returns a dict of fields to
merge into the state.  Nodes never mutate state directly.
"""

from __future__ import annotations

import time

import sqlglot
import sqlglot.expressions as exp
from psycopg2.extras import RealDictCursor

from app.database import QUERY_ROW_LIMIT, QUERY_TIMEOUT_MS, readonly_conn, serialize_row
from app.llm.anthropic_client import AnthropicClient
from app.schema_retriever import retrieve_relevant_schema
from app.agent.state import AgentState

_llm = AnthropicClient()

MAX_RETRIES = 3


# ── Node: retrieve_schema ──────────────────────────────────────────────────────

def retrieve_schema(state: AgentState) -> dict:
    schema = retrieve_relevant_schema(state["question"])
    return {"schema": schema, "retries": state.get("retries", 0), "error": ""}


# ── Node: generate_sql ────────────────────────────────────────────────────────

def generate_sql(state: AgentState) -> dict:
    """Ask Claude to produce SQL, passing back any previous error for self-correction."""
    error = state.get("error", "")
    sql, reasoning = _llm.generate_sql(
        question=state["question"],
        schema=state["schema"],
        previous_error=error or None,
    )
    return {"sql": sql, "reasoning": reasoning}


# ── Node: validate_sql ────────────────────────────────────────────────────────

def validate_sql(state: AgentState) -> dict:
    """Parse the SQL with sqlglot and confirm it is a pure SELECT."""
    sql = state["sql"]
    try:
        statements = sqlglot.parse(sql, dialect="postgres")
    except Exception as exc:
        return {"error": f"SQL parse error: {exc}"}

    if not statements:
        return {"error": "No SQL statement found in LLM response."}

    for stmt in statements:
        if not isinstance(stmt, exp.Select):
            return {
                "error": (
                    f"Only SELECT statements are permitted. "
                    f"Got: {type(stmt).__name__}"
                )
            }

    return {"error": ""}


# ── Node: execute_sql ─────────────────────────────────────────────────────────

def execute_sql(state: AgentState) -> dict:
    """Run the validated SQL under the read-only role."""
    sql = state["sql"]
    try:
        with readonly_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SET statement_timeout = {QUERY_TIMEOUT_MS}")
                t0 = time.perf_counter()
                cur.execute(sql)
                raw_rows = cur.fetchmany(QUERY_ROW_LIMIT)
                execution_time_ms = (time.perf_counter() - t0) * 1000
        rows = [serialize_row(dict(r)) for r in raw_rows]
        return {"rows": rows, "execution_time_ms": round(execution_time_ms, 2), "error": ""}
    except Exception as exc:
        return {"error": str(exc)}


# ── Node: format_answer ───────────────────────────────────────────────────────

def format_answer(state: AgentState) -> dict:
    answer = _llm.format_answer(
        question=state["question"],
        sql=state["sql"],
        results=state["rows"],
    )
    return {"answer": answer}


# ── Routing helpers ───────────────────────────────────────────────────────────

def route_after_validate(state: AgentState) -> str:
    """Continue to execute_sql, or loop back to generate_sql to self-correct."""
    if not state.get("error"):
        return "execute_sql"
    retries = state.get("retries", 0) + 1
    if retries >= MAX_RETRIES:
        return "max_retries"
    return "retry"


def route_after_execute(state: AgentState) -> str:
    """Continue to format_answer, or loop back to generate_sql to self-correct."""
    if not state.get("error"):
        return "format_answer"
    retries = state.get("retries", 0) + 1
    if retries >= MAX_RETRIES:
        return "max_retries"
    return "retry"


def increment_retries(state: AgentState) -> dict:
    """Increment the retry counter before looping back to generate_sql."""
    return {"retries": state.get("retries", 0) + 1}
