# AC Infinity Cloud API (unofficial)

Reverse-engineered notes on the API used by the AC Infinity mobile app. Everything here was extracted
from [dalinicus/homeassistant-acinfinity](https://github.com/dalinicus/homeassistant-acinfinity)
(commit `4134e95`, 2026-09-20): `client.py`, `const.py`, `core.py`, the entity platforms, the test
fixtures in `tests/data_models.py` and the Bruno collection in `.bruno/`.

There is no official documentation. Field names are misspelled in places (`appPasswordl`, `onSpead`,
`acitveTimerOn`, `schedEndtTime`) — always use them exactly as written.

| File | Content |
|------|---------|
| [connection.md](connection.md) | Base URL, login, headers, response envelope, error handling, retry policy |
| [endpoints.md](endpoints.md) | Every known endpoint with request shape |
| [data-model.md](data-model.md) | JSON returned by the device list: controller, ports, sensors, enums, value scaling |
| [controls-and-settings.md](controls-and-settings.md) | Writable keys (mode, speed, triggers, advanced settings), ranges, scaling, and the read-modify-write flows per controller family |
| [automations.md](automations.md) | Advance Automation programs & alarms on the `/api/version=2.0/` surface — where AI-controller configuration actually lives |

Further reverse-engineering references: [ober37/ac-infinity-mcp](https://github.com/ober37/ac-infinity-mcp)
(`docs/API.md`, 39 documented quirks incl. v2 automation writes) and
[keithah/homebridge-acinfinity](https://github.com/keithah/homebridge-acinfinity/blob/master/API_REFERENCE.md).

## Compatibility

Only Wi‑Fi controllers that sync to the UIS cloud: Controller 69 Wifi, 69 Pro, 69 Pro+, AI+, Outlet AI / AI+.
Bluetooth-only devices (Controller 67, base Controller 69) are not reachable through this API.

## Quick mental model

```
login  ──► token (appId)
            │
            ▼
devInfoListAll ──► controllers[] ─┬─ deviceInfo.ports[]    (port status, current speed, name)
                                  ├─ deviceInfo.sensors[]  (AI controllers only)
                                  └─ deviceInfo.temperature/humidity/vpdnums (standard controllers)
            │
            ▼
getdevModeSettingList(devId, port) ──► mode/trigger settings for one port
                                        └─ devSetting{}  (advanced settings for that port; port 0 = controller)
            │
            ▼ write
Standard controller:  addDevMode (controls)  /  updateAdvSetting (settings)
AI controller:        modeAndSetting (controls + settings in one PUT)
```

All writes are **full-object writes**: read the current settings, overlay the changed keys, send everything back.
