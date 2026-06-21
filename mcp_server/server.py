"""QueryMind MCP Server — Phase 3 stub.

Exposes five tools over the Model Context Protocol:
  - list_tables      List all tables in the public schema.
  - get_table_schema Return column names and types for a given table.
  - search_schema    Semantic search over schema_embeddings (pgvector).
  - validate_query   Parse SQL with sqlglot; reject non-SELECT statements.
  - run_query        Execute a SELECT against the read-only role with row/time limits.

Implementation lives in Phase 3.
"""

# Phase 3: implement using the `mcp` SDK.
# See: https://github.com/modelcontextprotocol/python-sdk
