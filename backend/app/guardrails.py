"""Input guardrail for the QueryMind chat endpoint.

Checks the user's question for data-mutation intent before the agent runs.
This is a belt-and-suspenders check — the read-only DB role and the
validate_sql node already block mutations at lower layers.  Catching them
here returns a cleaner error message sooner and avoids burning LLM tokens.
"""

from __future__ import annotations

import re

# Patterns that indicate SQL mutation intent in natural language.
# Kept specific to avoid false positives on legitimate analytical questions
# (e.g. "which tracks were removed from a playlist" won't match "delete from").
_MUTATION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bdrop\s+(table|database|index|view|schema)\b", re.IGNORECASE),
    re.compile(r"\btruncate\b", re.IGNORECASE),
    re.compile(r"\binsert\s+into\b", re.IGNORECASE),
    re.compile(r"\bdelete\s+from\b", re.IGNORECASE),
    re.compile(r"\bupdate\s+\w+\s+set\b", re.IGNORECASE),
    re.compile(r"\balter\s+table\b", re.IGNORECASE),
    re.compile(r"\bcreate\s+(table|database|index|view|schema)\b", re.IGNORECASE),
    re.compile(r"\bgrant\b", re.IGNORECASE),
    re.compile(r"\brevoke\b", re.IGNORECASE),
]

_BLOCKED_MESSAGE = (
    "This question appears to request a data modification. "
    "QueryMind only supports read-only SELECT queries."
)


def check_question(question: str) -> str | None:
    """Return an error message if the question should be blocked, else None."""
    for pattern in _MUTATION_PATTERNS:
        if pattern.search(question):
            return _BLOCKED_MESSAGE
    return None
