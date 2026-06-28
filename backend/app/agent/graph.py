"""LangGraph StateGraph for the QueryMind NL-to-SQL agent.

Flow:
    retrieve_schema
        → generate_sql
        → validate_sql ──(pass)──→ execute_sql ──(pass)──→ format_answer → END
               │                        │
          (fail, retry)            (fail, retry)
               ↓                        ↓
         increment_retries       increment_retries
               └──────────────────────→ generate_sql
               (max retries reached → END with error in state)
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent.state import AgentState
from app.agent.nodes import (
    execute_sql,
    format_answer,
    generate_sql,
    increment_retries,
    retrieve_schema,
    route_after_execute,
    route_after_validate,
    validate_sql,
)


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    g.add_node("retrieve_schema", retrieve_schema)
    g.add_node("generate_sql", generate_sql)
    g.add_node("validate_sql", validate_sql)
    g.add_node("execute_sql", execute_sql)
    g.add_node("increment_retries", increment_retries)
    g.add_node("format_answer", format_answer)

    # ── Entry ──────────────────────────────────────────────────────────────────
    g.set_entry_point("retrieve_schema")

    # ── Edges ──────────────────────────────────────────────────────────────────
    g.add_edge("retrieve_schema", "generate_sql")
    g.add_edge("generate_sql", "validate_sql")

    g.add_conditional_edges(
        "validate_sql",
        route_after_validate,
        {
            "execute_sql": "execute_sql",
            "retry": "increment_retries",
            "max_retries": END,
        },
    )

    g.add_conditional_edges(
        "execute_sql",
        route_after_execute,
        {
            "format_answer": "format_answer",
            "retry": "increment_retries",
            "max_retries": END,
        },
    )

    g.add_edge("increment_retries", "generate_sql")
    g.add_edge("format_answer", END)

    return g


# Compiled graph — import and call .invoke() from main.py
agent = build_graph().compile()
