# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Added
- MCP server (`mcp` SDK v2, stdio) with read tools: `list_controllers`, `get_port_settings`,
  `get_port_settings_raw`, `get_device_settings`, `list_automations`, `get_automations_raw`.
- Write tools guarded by `user_authorized`: `set_port_mode`, `set_port_power`, `set_port_timer`,
  `set_port_cycle`, `set_port_schedule`, `set_auto_triggers`, `set_vpd_triggers` — implemented
  for both controller families, **not yet verified against live hardware**.
- Tent vs. ambient climate split for AI controllers (probe = inside, onboard sensor = outside).
- Advance Automation decoding incl. family-specific `currentMode` tables and partial
  `sensorModeData` thresholds.
- API documentation in `docs/api/` distilled from the Home Assistant integration, the
  ober37/ac-infinity-mcp quirk list and live captures.
