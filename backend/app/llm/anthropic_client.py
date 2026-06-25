"""Anthropic Claude implementation of the LLM client interface."""

from __future__ import annotations

import os
import re

import anthropic

from app.llm.base import LLMClient

_DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

_SQL_SYSTEM_PROMPT = """\
You are a SQL expert working with a PostgreSQL database.
Given a schema and a user question, write a single SELECT query that answers it.

Rules:
- Only write SELECT statements. Never use INSERT, UPDATE, DELETE, DROP, ALTER, or any DDL.
- Use double quotes around all identifiers: SELECT "Name" FROM "Artist"
- Do not add a LIMIT clause unless the question explicitly asks for a fixed number of results.
- Only select the columns needed to answer the question.

Respond in this exact format and nothing else:
<reasoning>
Brief explanation of your approach
</reasoning>
<sql>
Your SELECT query
</sql>\
"""

_ANSWER_SYSTEM_PROMPT = """\
You are a helpful data analyst.
Given a question, the SQL that was executed, and the results, write a clear concise answer in plain English.
State the answer directly first. Do not mention SQL, databases, tables, or any technical details.\
"""


class AnthropicClient(LLMClient):

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = model

    def _parse_tag(self, text: str, tag: str) -> str:
        """Extract the content between <tag> and </tag>."""
        match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        if not match:
            raise ValueError(
                f"LLM response missing <{tag}> block.\nFull response:\n{text}"
            )
        return match.group(1).strip()

    def generate_sql(self, question: str, schema: str) -> tuple[str, str]:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=_SQL_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"DATABASE SCHEMA:\n{schema}\n\nQUESTION: {question}",
                }
            ],
        )
        response_text = message.content[0].text
        sql = self._parse_tag(response_text, "sql")
        reasoning = self._parse_tag(response_text, "reasoning")
        return sql, reasoning

    def format_answer(self, question: str, sql: str, results: list[dict]) -> str:
        # Cap results sent to the LLM to avoid enormous prompts.
        preview = results[:20]
        message = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=_ANSWER_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f'Question: "{question}"\n\n'
                        f"SQL executed:\n{sql}\n\n"
                        f"Results:\n{preview}"
                    ),
                }
            ],
        )
        return message.content[0].text.strip()
