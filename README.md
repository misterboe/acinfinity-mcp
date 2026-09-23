# acinfinity-mcp

[![CI](https://github.com/misterboe/acinfinity-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/misterboe/acinfinity-mcp/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![MCP SDK v2](https://img.shields.io/badge/MCP%20SDK-v2-black)](https://py.sdk.modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

MCP server for [AC Infinity](https://acinfinity.com) UIS grow controllers (Controller 69 Pro / Pro+, AI+, Outlet AI).
Lets Claude Code, Claude Desktop, Codex or any other MCP client read your tent's climate and change port settings
through natural language.

> "How is the tent doing?" → 26.5 °C / 57 % / 1.49 kPa, exhaust fan at level 3 driven by automation *Automatisierung 1* …

Uses the same unofficial cloud API as the AC Infinity app, so the controller must be connected to Wi‑Fi
(Bluetooth-only models such as Controller 67 are not supported). Not affiliated with AC Infinity.

## Status

| Area | State |
|------|-------|
| Reading controllers, sensors, port settings, automations | ✅ verified live on a Controller AI+ (CTR89Q) and a 69 Pro |
| Writing port modes / power / timers / triggers | ✅ verified live on the AI+ (mode + timer round trip); standard family follows the Home Assistant integration's proven path |
| Writing advanced settings (calibration, load type, …) | ⚠️ implemented, accepted by the API, persistence not yet verified |
| Creating / editing automations | 🚧 next up (endpoints and rule encoding documented in [`docs/api/automations.md`](docs/api/automations.md)) |

## Tools

| Tool | What it does |
|------|--------------|
| `list_controllers` | All controllers with `tent` climate (probe: °C / % / kPa), `ambient` climate (AI+ onboard sensor, outside the tent), port status/power/mode and every raw sensor reading |
| `get_port_settings` | Decoded mode configuration of one port: on/off power, auto & VPD triggers, timers, cycle, schedule |
| `get_port_settings_raw` | Unmodified API object incl. advanced settings (`port=0` = controller) |
| `get_device_settings` | Advanced settings (calibration, load type, dynamic response, …) |
| `list_automations` | Advance Automation programs: rules per port with mode, power, time window, days, thresholds — the real configuration on AI+ controllers |
| `get_automations_raw` | Unmodified automation rules + alarms |
| `set_port_mode` | Switch a port to Off / On / Auto / Timer / Cycle / Schedule / VPD / … |
| `set_port_power` | On/off power level 0–10 |
| `set_port_timer` | Countdown to on / to off |
| `set_port_cycle` | Repeating on/off minutes |
| `set_port_schedule` | Daily HH:MM on/off window |
| `set_auto_triggers` | Auto-mode temperature / humidity thresholds |
| `set_vpd_triggers` | VPD-mode thresholds |

Every `set_*` tool refuses to run unless it is called with `user_authorized: true`, so the assistant has to ask you
before touching a device.

## Install

Requires Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uvx acinfinity-mcp          # once published to PyPI
# or from a checkout:
uv run acinfinity-mcp
```

Credentials are passed as environment variables — the e‑mail and password of your AC Infinity app account:

| Variable | Required | Description |
|----------|----------|-------------|
| `ACINFINITY_EMAIL` | yes | App login e‑mail |
| `ACINFINITY_PASSWORD` | yes | App password (only the first 25 characters are used — that's an API limitation) |
| `ACINFINITY_LOG_LEVEL` | no | `DEBUG`, `INFO` (default), `WARNING`, `ERROR` |

## Client configuration

### Claude Code

```bash
claude mcp add acinfinity -e ACINFINITY_EMAIL=you@example.com -e ACINFINITY_PASSWORD=secret -- uvx acinfinity-mcp
```

or in `.mcp.json` / `~/.claude.json`:

```json
{
  "mcpServers": {
    "acinfinity": {
      "command": "uvx",
      "args": ["acinfinity-mcp"],
      "env": {
        "ACINFINITY_EMAIL": "you@example.com",
        "ACINFINITY_PASSWORD": "secret"
      }
    }
  }
}
```

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows). Use an absolute path to `uvx` if it is not on Claude's PATH.

```json
{
  "mcpServers": {
    "acinfinity": {
      "command": "uvx",
      "args": ["acinfinity-mcp"],
      "env": {
        "ACINFINITY_EMAIL": "you@example.com",
        "ACINFINITY_PASSWORD": "secret"
      }
    }
  }
}
```

### OpenAI Codex

`~/.codex/config.toml`:

```toml
[mcp_servers.acinfinity]
command = "uvx"
args = ["acinfinity-mcp"]

[mcp_servers.acinfinity.env]
ACINFINITY_EMAIL = "you@example.com"
ACINFINITY_PASSWORD = "secret"
```

## Development

```bash
uv sync                                        # deps into .venv
cp .env.example .env                           # local creds (git-ignored)
uv run --env-file .env acinfinity-mcp          # run over stdio
uv run --env-file .env mcp dev src/acinfinity_mcp/server.py   # MCP Inspector
uv run pytest                                  # tests (no live API calls)
uv run ruff check . && uv run ruff format .
```

The API is undocumented; everything known about it lives in [`docs/api/`](docs/api/README.md).
Writes are full read‑modify‑write round trips; standard and AI controllers use different endpoints
(see [`docs/api/endpoints.md`](docs/api/endpoints.md)).

## Security

- Your AC Infinity credentials only ever go to `www.acinfinityserver.com` (the same host the app uses) and are never logged.
- Every mutating tool requires `user_authorized: true`; the server never changes a device on its own initiative.
- Tool annotations mark reads as `readOnlyHint` so clients can auto-approve them and prompt for writes.

## Contributing

Issues and PRs are welcome — especially captures from other controller models (Outlet AI, 69 Pro+) and help
decoding the remaining `sensorModeData` fields. Run `uv run pytest` and `uv run ruff check .` before opening a PR;
never include real device ids, MAC addresses or account data in fixtures.

## Credits

API knowledge reverse-engineered from [dalinicus/homeassistant-acinfinity](https://github.com/dalinicus/homeassistant-acinfinity),
[ober37/ac-infinity-mcp](https://github.com/ober37/ac-infinity-mcp) and
[keithah/homebridge-acinfinity](https://github.com/keithah/homebridge-acinfinity).

## License

[MIT](LICENSE)
