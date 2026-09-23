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

### Fixed (history)
- Aggregated buckets reported a rounded mean power per port, which erased short device
  cycles (a 3-minute dehumidifier run in a 15-minute bucket became 0). Each port now carries
  `avg_power` (float), `max_power` and `on_minutes`, and the summary adds per-port
  on-minutes, duty cycle and run count.

### Added (history)
- `get_history`: 1-minute sensor/port history from `log/dataPage` (tent + ambient climate,
  per-port power from the `portSpead` nibbles, automation flags), fetched in 24 h windows with
  rate-limit pacing, aggregated into buckets with min/avg/max.
- `get_event_log`: the app's Logs tab from `log/logdataByAll` with id-cursor pagination and
  decoding of AI control actions (port, level, trend, reason), AI mode events, user actions,
  alerts and controller notices per the app's log builders.

### Added (automations)
- `rename_automation`: rewrites every rule of a program with the new `advName` via
  `updateGroupsById`, exactly like the app's edit path (non-null fields, raw `sensorModeData`),
  with 1.5 s spacing between writes.
- Automation rules under the 24/7 switch now also report `stored_window` (the inactive
  window/days still saved on the rule) so the null window is not mistaken for a regression.
- Project `.claude/settings.json` pre-allows the read-only and backup tools.

### Added (from the decompiled Android app 2.0.8)
- `docs/api/app-endpoints.{md,json}`: the complete endpoint inventory — 179 Retrofit
  declarations with parameters, headers and return types.
- `sensorModeData` decoder now mirrors the app's parser byte for byte (switch bits, precision
  codes, int16 values).
- AI advanced-settings writes use the app's own `modeAndSetting` recipe (non-null mode fields +
  35 setting keys + port name + °F clamp) instead of the HA-style flattened object that renamed
  a port to "0".

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
