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

### Added (backup & rename)
- `backup_settings`, `list_backups`, `compare_backup`, `restore_settings`: full-configuration
  backups as local JSON, field-level diff against the live device, and restore of changed
  ports (full `addDevMode` round trip) and automation rules (`updateGroupsById`).
- `rename_port` — app-native minimal `modeAndSetting` PUT on AI controllers, `updateAdvSetting`
  on standard ones. Writes to ports with nothing plugged in are refused up front (the
  controller answers `999999`).
- Standard-controller writes carry the app's request signature (`sign`/`requestId`/`version`
  headers, algorithm from the decompiled Android app via Backroads4Me's fork).

### Removed
- The full-object `modeAndSetting` PUT for AI advanced settings: it renamed a port to "0"
  in a live test because `devSetting.devName` is null on AI controllers. AI advanced-settings
  writes are refused until the app's field-group ids are mapped.

### Changed
- Port control writes go to `addDevMode` as form body on both families, with the
  `minversion: 3.5` header on AI controllers — verified live (Timer-to-On round trip on an
  AI+). The query-string variant is rejected with `100001` there.
- `sensorModeData` (AI-controller automation thresholds) is now fully decoded — target,
  high, low, buffer, transition and control mode — verified against all 30 grow-stage
  template rules the API ships in both encodings. A VPD rule previously shown as a "low
  trigger" is a target setpoint.

### Fixed
- Automation rules with the 24/7 switch (`switchTime` bit 7) no longer report a time window;
  a `schedule` summary states "24/7" or the effective days/window.
- Automation temperature thresholds are merged into one °C entry; thresholds at their rail
  are reported as `null` instead of 0 / 100 / 9.9.
- `is_on` of a port now follows the applied power level, because AI controllers keep
  `loadState 0` while an automation drives the port.
