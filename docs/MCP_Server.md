# MCP Server (app/mcp_server.py) — analysis and usage

## What this file is
`app/mcp_server.py` spins up an MCP tool server using `FastMCP`. It registers a set of tools:
- search_conversations
- ingest_conversation
- get_conversations
- get_conversation
- delete_conversation
- health_check

Each tool uses `httpx` to call the FastAPI REST backend at `FASTAPI_BASE_URL` (env var, default `http://localhost:8000`) and returns Pydantic schema objects.

## What it is solving
- Exposes a Model Context Protocol (MCP) toolset so AI agents (or other MCP-aware clients) can call high-level conversation/search operations.
- The server acts as a proxy to FastAPI: keep FastAPI as the canonical data/embedding/storage layer, expose a tool layer for agents.

## How it is started
- The module runs when executed as `python -m app.mcp_server` (it calls `mcp_app.run()`).
- Currently not automatically started by `docker-compose up -d` unless you add a docker-compose service or hook it in `scripts/start-dev.sh`.

## How it is used
Two practical ways to use it:
1. Call FastAPI endpoints directly (what the MCP server does): use `httpx`/`requests` to call `/search`, `/ingest`, `/conversations`.
2. Use MCP protocol: if you have an MCP client implementation (from the `mcp` package), start this server and call tools via that protocol.

## Shortcomings & recommendations
- Add a docker-compose service for `mcp_server` so it runs automatically in deployed/dev environments.
- Add authentication between MCP server and FastAPI (API key / service-to-service token).
- Expose a sample MCP client (repo-level `app/mcp_client.py`) so consumers have a simple interface.
- Improve startup logs and healthchecks. Add a readiness probe: verify FastAPI_BASE_URL/health before advertising tools.
- Add rate-limiting & retry logic for httpx requests to improve resilience.

## Example usage
- Quick test (calls FastAPI directly):
```py
from app.mcp_client import MCPClient
client = MCPClient(base_url="http://localhost:8000")
resp = client.search("database connection", top_k=5)
print(resp)