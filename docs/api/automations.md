# Advance Automations & Alarms (v2 API)

The app's "Automations" tab (named programs that govern one or more ports) does **not** live in
`getdevModeSettingList`. Ports governed by a program keep `atType = 1` (Off) there while the
program drives them (observed live 2026-09-23: AI+ ports at `speak` 3/6 with `atType 1`).
On AI controllers this is where the real configuration lives.

Source for the endpoint surface: [ober37/ac-infinity-mcp `docs/API.md`](https://github.com/ober37/ac-infinity-mcp/blob/main/docs/API.md)
(Quirks 18, 32, 33, 35, 39 — network captures of the iOS/Android app). Read endpoints verified on this account.

## Endpoints

| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | `/api/version=2.0/dev/getGroups` | `devId` | all automation rules of a controller |
| POST | `/api/version=2.0/dev/getAlarms` | `devId` | alarm definitions |
| GET | `/api/version=2.0/dev/recipe?advVersion=1` | – | grow-stage templates (Seedling, Vegetative, Flowering, Plant Kit, Drying) |
| POST | `/api/version=2.0/dev/addGroups` | ~50 form fields | create rule (`isFlag=1` new program, `isFlag=0` append) — **needs `minversion: 3.5` on AI, otherwise hangs** |
| POST | `/api/version=2.0/dev/updateGroupsById` | full rule + `advId` | edit in place (read-modify-write) |
| POST | `/api/version=2.0/dev/updateGroupsIsOn` | `advId&isDel=0&isflag=1` | **toggles** isOn (no explicit value) — needs `minversion` on AI |
| POST | `/api/version=2.0/dev/delByid` | `advId&isDel=1&isflag=1|0` | delete whole program (1) or single rule (0) — needs `minversion` on AI |
| POST | `/api/version=2.0/dev/addAlarms` / `updateAlarmsById` / `delAlarmsByid` | alarm object | alarms; `isOn` explicit here |

The literal `version=2.0` path segment is real. Send only `token` + `User-Agent`; the `version`
and `requestId` headers make the server answer `403 "Login Expired"` (it then expects a `sign`).
`minversion: 3.5` is a literal magic string — other values (3.4, 3.6, 99.9) are rejected.

## Rule object (`getGroups` entry)

One entry = one rule; a **program** = all entries with the same `advName` (also same
`groupNums`/`sortType` slot, `subNumber` 0,1,2…). Live example (AI+, program "Automatisierung 1"):

```jsonc
{
  "advId": 2596136, "advName": "Automatisierung 1", "advType": 5,
  "isOn": 1,             // enabled in the app
  "runState": 1,         // currently in effect
  "currentMode": 3,      // family-dependent! see below
  "grouptDevType": 1,    // PORT BITMASK: port N -> 1 << (N-1)
  "onSpeed": 4, "offSpeed": 0,
  "beginTime": 540, "endTime": 1020,   // minutes from midnight, controller local time
  "switchTime": 255,     // bits 0-6 = Mon..Sun, bit 7 = continuous (app ignores window)
  "isOnMinMaxTime": 1, "onMinTime": 5, "onMaxTime": 0,
  "onDoseTime": 60, "offDoseTime": 1, "dualZoneSwitch": 1,
  "cycleOn": 0, "cycleOff": 0,          // seconds
  "autoHighTempF": 32, "autoLowTempF": 32, "targetTempF": 32,   // rails on AI controllers
  "sensorModeDataNum": 3,
  "sensorModeData": "[0,13,5,2,0,0,32,0,77,0,32, 1,13,5,1,0,0,0,0,25,0,0, 2,12,5,0,0,0,0,0,100,0,0]",
  "advStateValue": "1-1-0", "advKey": "0-0", "subNumber": 0
}
```

### `currentMode` — two enums, On/Off inverted

| Mode | Standard (devType 11/18) | AI / new framework (devType ≥ 20) |
|------|--------------------------|-----------------------------------|
| On | 1 | 2 |
| Off | 2 | 1 |
| Cycle | 3 | 6 |
| Auto | 4 | 3 |
| VPD | 6 | 8 |

Writing the wrong table energises equipment. `models.py` keys the table on `is_ai`.

### Thresholds

- **Standard controllers** store them in the flat fields: `autoHighTempF/C`, `autoLowTempF/C`,
  `autoHighHumi`, `autoLowHumi`, `targetHumi`, `targetVpd`/`highVpd`/`lowVpd` (kPa × 10),
  `settingMode` (0 trigger / 1 target), `setSelect`, each with a `…Switch`. Values at their rail
  (temp 32 °F / 90 °C, humidity 0/100, VPD 0/99) mean "not set".
- **AI controllers** leave those at rails and keep the real configuration in `sensorModeData`:
  a JSON int array, `sensorModeDataNum` records of **11 ints**. Partially decoded:

  | pos | meaning | evidence |
  |-----|---------|----------|
  | 0 | `sensorType` (0 probe °F, 1 probe °C, 2 probe humidity, 3 probe VPD …) | matches sensor table |
  | 6 | low threshold | 32 °F / 0 °C / 0 % / 15 (=1.5 kPa) |
  | 8 | high threshold | 77 °F = 25 °C / 100 % (rail) / 99 (rail) |
  | 3 | probably which triggers are enabled (`1` where exactly one non-rail threshold exists, `0` for the all-rail humidity record, `2` on the °F twin) | hypothesis |
  | 1, 2 | unknown (`13/12/47`, `5/10`) — maybe hysteresis/buffer and a speed bound | open |

  Temperature is stored twice (a °F record and a °C record with the same meaning); the server
  merges them into one °C entry. Rails are reported as `null` ("not set"). Confirmed against the
  app on 2026-09-23: port 1 Auto = high 25 °C only, port 3 VPD = low 1.5 kPa only.

### Other fields

- `beginTime`/`endTime` minutes from midnight; `switchTime` day bitmask (`127` all days,
  `255` = all days + continuous, `31` weekdays, `96` weekends). **When bit 7 (continuous, the
  app's "24 h" switch) is set, the stored window is ignored** — the rule applies all day. The
  user's live program stores 09:00–17:00 with `switchTime 255` and runs 24/7 (confirmed in the
  app). Never report the window for a continuous rule.
- Ports driven by a program keep `loadState 0` in `devInfoListAll` even while running (`speak` > 0);
  use `speak` to tell whether the device is on.
- `cycleOn`/`cycleOff` in seconds (app shows minutes).
- `isOnMinMaxTime`/`onMinTime`/`onMaxTime`: minimum/maximum run time in minutes.
- `portType`: device identity, exposed by no read endpoint; copy from existing rules on writes.
- On AI controllers `isOpenAutomation` in the port list stays `0` even while a program runs — it is
  **not** a reliable "governed by automation" flag there; derive it from `getGroups` instead.

## Write status

Not implemented in this server yet. Known from ober37: `addGroups` needs the full ~50-field body,
`updateGroupsIsOn` toggles blindly (read first), deletes with `isflag=1` wipe the whole program,
rapid writes wedge the controller (`100001` until power-cycle), a program rejects overlapping
windows on the same port (`500 "Adv exist!"`), and 1.5 s spacing between writes avoids `403`.
