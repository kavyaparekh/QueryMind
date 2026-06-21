"""QueryMind FastAPI application entry point.

Phase 0: health check only.
Phase 1: /chat endpoint (single-pass pipeline).
Phase 2: /chat updated to run the full LangGraph agent.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
async def health() -> dict:
    """Liveness probe — returns 200 when the server is running."""
    return {"status": "ok", "phase": 0}
