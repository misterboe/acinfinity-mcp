# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

MCP server (stdio) for AC Infinity grow controllers (Controller 69 Pro/Pro+, AI+ etc.) so that Claude Code and OpenAI Codex can read sensor data (temperature, humidity, VPD) and control ports (fans, lights, etc.) through natural language.

The repository is a greenfield project. Decisions made at kickoff (2026-09-23):

- **Stack:** Python with `MCPServer` from the `mcp` 2.x SDK, `httpx2` for HTTP (the SDK's own HTTP lib), packaged with `uv` (`pyproject.toml`). Run via `uvx`/`uv run`.
- **Device access:** AC Infinity **cloud API** (the unofficial app API at `https://www.acinfinityserver.com`, same as the Home Assistant integration `dalinicus/homeassistant-acinfinity`). No Bluetooth. Everything known about the API is documented in `docs/api/` — read it before touching `client.py`, and update it when you learn something new.
- **Scope:** read + write. Every write tool (set fan level, change mode, edit triggers) must require an explicit `user_authorized: true` argument and refuse otherwise — same security model as the sibling project `../strapi-mcp-server`.

## Rules (non-negotiable)

1. **Best-practice MCP.** Follow the official MCP spec and the **`mcp` Python SDK v2** idioms — the rules are in `docs/mcp-best-practices.md`, read it before writing server code. Non-negotiables: `MCPServer` (not `FastMCP`), `async def` tools with `Annotated[..., Field(...)]` parameters, Pydantic return models (structured output), `ToolAnnotations` on every tool, `ToolError` for every user-facing failure (never return error strings), shared client in a lifespan, stdlib logging to stderr, never `print()`.
2. **Latest SDK and package versions.** Before adding or bumping a dependency, check PyPI (`curl -s https://pypi.org/pypi/<pkg>/json`) and pin the current release in `pyproject.toml` with `>=`. Never copy versions from memory or from the sibling project. Baseline at kickoff (2026-09-23): `mcp 2.2.0` (depends on `httpx2>=2.5`, `pydantic>=2.12`), `httpx2 2.13.1`, `pydantic 2.13.5`, `pytest 9.1.1`, `pytest-asyncio 1.4.0`, `ruff 0.16.8`. No `pydantic-settings` (SDK v2 dropped it; read env vars explicitly), no `respx`/`pytest-httpx` (httpx 0.x only — mock with `httpx2.MockTransport`). Requires Python ≥ 3.12.
3. **Standard-conform and usable by anyone.** The server must run with one command on a fresh machine: `uvx acinfinity-mcp` (publishable to PyPI, `[project.scripts]` entry point, `README.md` with copy-paste config blocks for Claude Code, Claude Desktop and Codex). No hard-coded paths, no machine-specific config, all secrets via env vars, `.env.example` checked in, MIT license.

## Development Commands

Once the project is scaffolded, keep these working and update this section if they change:

```bash
uv sync                                        # install deps into .venv
uv run --env-file .env acinfinity-mcp          # start the server over stdio with local creds
uv run pytest                                  # run all tests (mocked API, no network)
uv run pytest tests/test_client.py -k ai_write # single test
uv run ruff check . && uv run ruff format .    # lint / format (both must be clean)
uv run --env-file .env mcp dev src/acinfinity_mcp/server.py   # MCP Inspector
```

Live read-only smoke test against the real API (never run writes unattended):
`uv run --env-file .env python -c "..."` using `AcInfinityClient` directly — see the pattern in
`tests/conftest.py` for which calls exist. `.env` is git-ignored and only for development; end users
put the variables into their MCP client config (README.md).

## Configuration

Credentials come from environment variables (or a `.env` loaded at startup), never from code:

- `ACINFINITY_EMAIL`, `ACINFINITY_PASSWORD` – app login. The API only accepts the first 25 characters of the password; truncate before sending.
- `ACINFINITY_LOG_LEVEL` – optional, logs go to **stderr** only (stdout is the MCP transport).

Client registration:
- Claude Code: `.mcp.json` in this repo (`command: "uv", args: ["run", "acinfinity-mcp"]`).
- Codex: `[mcp_servers.acinfinity]` block in `~/.codex/config.toml` with the same command/args/env.

## Architecture (intended)

```
src/acinfinity_mcp/
  server.py     # MCPServer instance + lifespan, tool definitions only (thin: validate → call client → return model)
  client.py     # AcInfinityClient (httpx2): login/token, retry+backoff, lock, standard vs AI write paths; no MCP knowledge
  models.py     # Pydantic models for devices, ports, sensors, mode settings + raw→unit conversion
  __main__.py   # entry point used by the `acinfinity-mcp` script
tests/          # pytest; HTTP mocked with httpx2.MockTransport, tools called via in-memory client session; no live API calls
```

Key API facts (full detail in `docs/api/`):
- Login `POST /api/user/appUserLogin` (form fields `appEmail`, `appPasswordl` — the trailing `l` is intentional, password truncated to 25 chars) → `data.appId`, sent as `token` header on all later calls. Always send `User-Agent: okhttp/4.12.0`.
- `POST /api/user/devInfoListAll` lists controllers with ports and (AI only) sensors. `POST /api/dev/getdevModeSettingList` reads one port's controls + `devSetting`.
- Writes are full-object read-modify-write via query string: standard controllers use `addDevMode` / `updateAdvSetting`, AI controllers (`devType` 20–22) use `PUT modeAndSetting` with `minversion: 3.5` and `modeAndSettingIdStr`. Keep the family split in `client.py`.
- Values are scaled integers (temp/humidity/VPD ×100 on controllers, VPD/pH ×10 in settings, timers in seconds, schedule in minutes with 65535 = off); convert in `models.py`, not in tools. Temperature writes must set both °C and °F keys.
- The API has no official rate limit docs and is flaky; retry with backoff, cache device lists briefly, never poll inside tools.
- AI-controller configuration lives in **Advance Automations** (`/api/version=2.0/dev/getGroups`), not in the per-port mode settings; `currentMode` numbering differs per family with On/Off inverted (`docs/api/automations.md`). Before extending anything, check `ober37/ac-infinity-mcp` `docs/API.md` (39 quirks) — it is the most complete public reference.

## Conventions

- Tool names are `snake_case` verbs: `list_devices`, `get_sensor_readings`, `set_port_power`, …
- Tool docstrings are the user-facing description — write them for the LLM (what it does, units, what `user_authorized` means).
- Return structured data (dicts/models), not pre-formatted prose, so both Claude and Codex can reason over it.
- German is fine for conversation; code, docstrings and commit messages are English.
