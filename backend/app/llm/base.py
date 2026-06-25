"""Abstract LLM client interface.

Keeping the LLM behind an interface means swapping Claude for a different
model (GPT-4, Gemini, a local model) requires only a new implementation of
this class — nothing else in the codebase changes.
"""

from abc import ABC, abstractmethod


class LLMClient(ABC):

    @abstractmethod
    def generate_sql(self, question: str, schema: str) -> tuple[str, str]:
        """Generate a SQL query from a natural language question.

        Args:
            question: The user's plain-English question.
            schema:   Formatted database schema string.

        Returns:
            (sql, reasoning) — the generated SELECT statement and a brief
            explanation of the approach taken.
        """
        ...

    @abstractmethod
    def format_answer(self, question: str, sql: str, results: list[dict]) -> str:
        """Turn raw query results into a natural language answer.

        Args:
            question: The original user question.
            sql:      The SQL that was executed.
            results:  List of result row dicts.

        Returns:
            A concise plain-English answer.
        """
        ...
