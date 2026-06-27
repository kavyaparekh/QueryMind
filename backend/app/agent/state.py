"""LangGraph agent state for the QueryMind NL-to-SQL pipeline."""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    question: str          # original user question (set once, never mutated)
    schema: str            # retrieved schema snippet
    sql: str               # generated SELECT statement
    reasoning: str         # Claude's reasoning for the SQL
    rows: list[dict]       # raw result rows from Postgres
    error: str             # last validation or execution error (empty = none)
    retries: int           # number of correction attempts so far
    answer: str            # final plain-English answer
    execution_time_ms: float
