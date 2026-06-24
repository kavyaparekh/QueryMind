"""Pydantic request/response models for the QueryMind API."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sql: str
    reasoning: str
    rows: list[dict]
    row_count: int
    execution_time_ms: float
