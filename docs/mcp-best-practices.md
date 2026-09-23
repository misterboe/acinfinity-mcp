# MCP Best Practices for this server

Distilled on 2026-09-23 from:
- MCP spec (modelcontextprotocol.io, revision 2025-06-18 "Tools"; the 2026-07-28 revision deprecates protocol logging/roots/sampling)
- modelcontextprotocol.info docs (Concepts → Tools/Transports/Architecture, Best Practices)
- Python SDK v2 docs (py.sdk.modelcontextprotocol.io — `mcp` 2.2.0)

These are the rules we build against. Anything here overrides habits from `mcp` 1.x tutorials.

## 1. SDK v2 — what changed (do not copy 1.x examples)

| 1.x | 2.x (use this) |
|-----|----------------|
| `from mcp.server.fastmcp import FastMCP` | `from mcp.server import MCPServer` |
| `FastMCP("name", "instructions")` | `MCPServer("name", instructions="…", version="…")` — keyword args only |
| `mcp.get_context()` | declare `ctx: Context` (or `Context[AppState]`) as a tool parameter |
| `import httpx` | `import httpx2` — the SDK depends on `httpx2>=2.5`; use the same lib for our client |
| `mcp.types` camelCase (`isError`, `inputSchema`) | snake_case (`is_error`, `input_schema`); wire format unchanged |
| `McpError` | `MCPError` (`mcp.shared.exceptions`) |
| `MCP_*` env vars / `.env` auto-loaded, `pydantic-settings` | **not loaded** — read env yourself and pass explicitly |
| transport args in constructor | `mcp.run(transport=…, port=…)` |
| `await ctx.info("msg")` protocol logging | deprecated — use stdlib `logging` |
| sync `def` tools run on event loop | sync tools run on a **worker thread** — use `async def` for anything touching our async HTTP client |

Python ≥ 3.10 is the SDK floor; we require **≥ 3.12**.

## 2. Server shape

```python
from mcp.server import MCPServer

mcp = MCPServer(
    "acinfinity",
    instructions="Read sensors and control ports of AC Infinity UIS controllers …",
    version=__version__,
    log_level="INFO",
)

if __name__ == "__main__":
    mcp.run()  # stdio; blocks
```

- One server, one purpose (spec best practice: single responsibility). No unrelated tools.
- `if __name__ == "__main__":` guard is mandatory — `mcp dev`, tests and the entry point all import the module.
- Shared `AcInfinityClient` lives in a **lifespan** (`@asynccontextmanager`, yield a typed state object); tools read it via `ctx.request_context.lifespan_context`. Create the HTTP client on startup, close it in `finally`.
- Stdio: **never `print()`**. stdout is the protocol channel. Constructing `MCPServer` already configures `logging.basicConfig` to stderr; just use `logging.getLogger(__name__)`.

## 3. Tools

- `async def`, typed parameters, docstring = description. "The type hints are the schema": invalid input is rejected before the function runs.
- Every parameter gets `Annotated[T, Field(description=…, ge/le/…)]`. Ranges from `docs/api/controls-and-settings.md` go into `Field` constraints (e.g. `speed: Annotated[int, Field(ge=0, le=10)]`), so the model self-corrects.
- Return **Pydantic models** (or `dict[str, Any]`) → automatic `outputSchema` + `structuredContent`. Scalars get wrapped in `{"result": …}`; lists are wrapped and flattened — prefer a model with a list field. Classes without type hints silently produce no schema.
- Set `annotations=ToolAnnotations(...)` on every tool:
  - reads: `read_only_hint=True, idempotent_hint=True, open_world_hint=False`
  - writes: `read_only_hint=False, destructive_hint=True/False, idempotent_hint=True` (setting a value twice is idempotent)
  - Annotations are hints for the client UI, **never** a security control.
- Give each tool a `title` (human UI name) besides `name` (snake_case verb: `list_devices`, `set_port_mode`).
- Keep tools atomic and focused; one tool = one API operation the user would name. Don't expose a raw "send any key/value" tool by default.

## 4. Errors

- Raise `ToolError` (`mcp.server.mcpserver.exceptions`) for anything a smarter call could avoid: unknown device, port offline, value outside range, API returned `code != 200`, timeout. Message must be actionable and contain no secrets/stack traces.
- Any other exception reaches the model only as `"Error executing tool <name>"` — so wrap client exceptions and re-raise as `ToolError`.
- Never `return` an error string: `is_error` would be `False` and the model would think it succeeded.
- `MCPError` only for protocol-level rejection (should not be needed here).

## 5. Security & safety (spec: servers MUST validate inputs, implement access control, rate-limit, sanitize output)

- Human in the loop for writes: every mutating tool takes `user_authorized: bool` and raises `ToolError` unless `True`; the docstring explains that the user must have explicitly approved the change.
- Validate everything with Pydantic constraints; re-check semantic rules the schema can't express (e.g. timer keys only valid for `atType` 4/5) and raise `ToolError`.
- Credentials only from env vars; never echo them in logs or results. Strip the raw API envelope before returning (no `appPasswordl`, no tokens).
- Rate limiting: serialise API calls through one `asyncio.Lock`, cache `devInfoListAll` for a few seconds, per-call timeout 10 s, retry with exponential backoff (1/2/4/8 s) on transport/`code != 200` errors, never on auth errors.
- Clean up on failure: the HTTP client is closed by the lifespan `finally`.

## 6. Distribution (so that "anyone can use it")

- `pyproject.toml` with `[project.scripts] acinfinity-mcp = "acinfinity_mcp.server:main"`, so `uvx acinfinity-mcp` works from PyPI and `uv run acinfinity-mcp` works from a checkout.
- README with copy-paste blocks for Claude Code (`claude mcp add` / `.mcp.json`), Claude Desktop (`claude_desktop_config.json`, absolute paths) and Codex (`~/.codex/config.toml` `[mcp_servers.acinfinity]`), each with `env` for `ACINFINITY_EMAIL` / `ACINFINITY_PASSWORD`.
- Local testing: `uv run mcp dev src/acinfinity_mcp/server.py` (Inspector). `mcp install` registers with Claude Desktop.

## 7. Testing

- Unit-test the client with `httpx2.MockTransport` (inject the transport into `AcInfinityClient`) using the fixtures in `docs/api/`. `respx` and `pytest-httpx` only support `httpx` 0.x, not `httpx2` (checked 2026-09-23).
- Protocol-level tests: call tools through an in-memory client session (`mcp.client` connected to the server object) and assert `structured_content` and `is_error`.
- No live API calls in the test suite.
