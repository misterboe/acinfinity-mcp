# History & event log (`/api/log`)

Two surfaces, both verified live on an AI+ on 2026-09-23 and both rate-limited.

## Rate limiting

Bursts of log calls answer `{"code": 999998, "msg": "Rate Limiting!"}` (HTTP 200). The app treats
`999998` as non-fatal and polls history segments every 2 s; in practice ≥ 2.5 s between calls
and a 10 s back-off after a `999998` keep things flowing. Do **not** read `999998` as "no data" —
that misled the first probes.

## Sensor history — `POST /api/log/dataPage`

```
appId=<token>&devId=<id>&time=<newer bound, unix s>&endTime=<older bound, unix s>&pageSize=<n>&orderDirection=1
```

App signature (`LogApi.getDataListPage`): `time` is the **newer** bound, `endTime` the **older**
one (the app sends `now + 59` and `selected start`), `orderDirection=1` = newest first. Older-than-
newer windows also work, but a span longer than ~24 h is rejected with `999998` — fetch day by
day. `pageNum` is ignored; `pageSize=2000` returns a whole day (1440 rows).

- Resolution: **one row per minute** (`createTime`, unix s). Retention: at least **90 days**
  (1440 rows/day at −90 d on this account, `validFrom 0`).
- Per row: `temperature`/`humidity` (×100, onboard sensor on AI controllers = probe on standard
  ones), `vpdNums` (×100), `fTemperature` (°F ×100), `portSpead` (4-bit nibble per port, LSB = port 1,
  applied level 0–10), `portStatus` (bit per port: automation triggered), `allSpead`, `dataStatus`,
  `sensorDataBlock`, `devVersion`, and `sensors[]` with the same `sensorType/accessPort/sensorData/
  sensorPrecision` records as the live device list (so probe vs onboard history is separable).
  `thermal*`, `leafTemp*`, `internalSensor*`, `external*Sensor*`, `portDataBytes`,
  `portStateData` are present but empty on this hardware.
- `DELETE /api/log/data?devId&time` (header `devType`) deletes history — not wired.

The server's `get_history` tool fetches the span in 24 h windows, decodes rows into tent/ambient
climate + per-port power, aggregates into `sample_minutes` buckets and adds min/avg/max.

## Event log — `POST /api/log/logdataByAll`

```
appId=<token>&devId=<id>&id=<cursor, 0 first>&time=<newer, unix s>&endTime=<older>&pageSize=<≤1000>&orderDirection=1
```

Returns `{rows, total, validFrom}` newest first; `total` is capped at `pageSize`. Paginate by passing
the last row's `id` as the cursor. `pageSize=1000` works. The single-page variant without
`endTime`/`orderDirection` returns nothing useful.

Row = `NetLog` (84 fields). Decoding per the app (`NetLog.toLog04`, `protocol/a.getLogStringH`):

| `logType` | `businessType` | meaning | fields used |
|-----------|----------------|---------|-------------|
| 3 (AI, `logFormat` 4) | 1 | **AI set a port**: `portSelection` port, `mlVariation` level, `currentStatus` on/off, `mlVariationTrend` 1 decrease / 2 increase, `pauseReason` → reason table below, `loadId`/`loadType`/`portResistance` device identity | |
| 3 | 2 | **user action** in AI mode: `mlVariationType` 1 target range updated, 2 schedule updated, 3 light schedule, 4 port device type changed, 5 port added/removed, 6 sensor connection, 7 dynamic light schedule; `mlVariationMin/Max`, `targetType` | |
| 3 | 3 | **AI mode event**: `mlVariationType` 0 paused, 1 started, 2 resumed, 3 deleted, 4/5 tentwork on/off, 6/8 unfavorable environment, 7/9 extreme conditions, 10 humidity > 90 %, 11 clip-fan setting, 16/17 night mode on/off; `plantType`, `growStageSeq`, `mlType` | |
| 2 | * | alert (`alarmHigh*/alarmLow*`, `advanceName`) | |
| 4 | * | mode / automation info (`currentMode`, `autoHigh*/autoLow*`, `cycleOn/Off`, `schedStart/End`, `advanceName`) | |
| 5 | 0–7 | controller notice: CO₂ > 5000 ppm paused, power protection, low water, built-in clip fan / fan / light / sensor lost, carbon-filter alert | |

`pauseReason` (AI control reason): 1 raise temperature, 2 lower temperature, 3 raise humidity,
4 lower humidity, 5 raise VPD, 6 lower VPD, 7 CO₂, 8 efficiency, 9 raise temp & humidity,
10 lower temp & humidity, 11 raise temp / lower humidity, 12 lower temp / raise humidity.

The human-readable texts are string-resource **keys** in the app (`history_log_ai_control`, …);
the actual sentences come from a server language pack (`GET language/languageDataByVersion`,
returned `null` for us), so the server exposes machine-readable event names instead.

- `DELETE /api/log/log?devId&time` deletes the event log — not wired.
- `log/log_c` is a UI route, not an endpoint (404).
