"""QueryMind FastAPI application.

Phase 2: LangGraph agent with pgvector schema retrieval + self-correction.
  POST /chat  →  agent.invoke()  →  return response.

The agent graph lives in app/agent/graph.py.
Phase 3 will add the MCP server.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent.graph import agent
from app.models import ChatRequest, ChatResponse

app = FastAPI(
    title="QueryMind",
    description="Natural-language-to-SQL agent with safety guardrails.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server (Phase 5)
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "phase": 2}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """LangGraph NL-to-SQL agent pipeline.

    Delegates entirely to the compiled agent graph which handles:
    schema retrieval, SQL generation, validation, execution,
    self-correction (up to 3 retries), and answer formatting.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        state = agent.invoke({"question": question, "retries": 0, "error": ""})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # If max retries were hit the agent ends without an answer
    if not state.get("answer"):
        error = state.get("error", "Unknown error")
        raise HTTPException(
            status_code=400,
            detail=f"Agent failed after max retries. Last error: {error}",
        )

    return ChatResponse(
        answer=state["answer"],
        sql=state["sql"],
        reasoning=state["reasoning"],
        rows=state["rows"],
        row_count=len(state["rows"]),
        execution_time_ms=state.get("execution_time_ms", 0.0),
    )
