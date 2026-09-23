# Controls & Settings (read‑modify‑write)

Two objects per port, both returned by `POST /api/dev/getdevModeSettingList` (`devId`, `port`):

- **Controls** — the flat top-level object: active mode, speeds, triggers, timers, targets.
- **Settings** — the nested `devSetting` object: advanced/per-device settings (load type, calibration, dynamic response, sunrise timer, display).

Port `0` = controller-level (settings only relevant there: temp unit, calibration, outside-climate compare, display).

## Write flow

```
controls (both families) — VERIFIED LIVE on AI+ 2026-09-23
  POST getdevModeSettingList → overlay changed keys → POST addDevMode  (form body, all CONTROL_KEYS)
  AI family additionally: header `minversion: 3.5`  (without it: body code 100001)

settings, standard controller (devType 11, 18) — HA-verified
  POST getDevSetting → overlay → POST updateAdvSetting (form body, all SETTING_KEYS + devName=<current name>)

settings, AI controller (devType 20, 21, 22) — accepted (200) in a no-op test, persistence unverified
  POST getdevModeSettingList → flatten {**devSetting, **top} → overlay
  → set modeAndSettingIdStr by atType → PUT modeAndSetting?<all keys>  (header minversion: 3.5)
```

Live no-op experiment on an idle AI+ port (identical values written back):

| Variant | Result |
|---------|--------|
| `addDevMode`, payload in **query string**, no `minversion` (HA legacy style) | `100001 Something went wrong` |
| `addDevMode`, payload as **form body**, `minversion: 3.5` | `200 success` |
| `PUT modeAndSetting?…`, `minversion: 3.5` | `200 success` |

Persistence check: `{atType: 4, acitveTimerOn: 86400}` → read-back `atType 4`, `remainTime 86400`,
port stayed off; `{atType: 1}` → read-back Off. **Fields irrelevant to the mode being written are
silently discarded** (`acitveTimerOn: 0` sent together with `atType: 1` was ignored, the timer value
stayed at 86400) — ober37 Quirk 37. To change a mode's parameters, send them together with that
`atType`.

Serialisation of every key (HA `__transfer_values`): missing → `0`, `None` → `0`, `bool` → `"true"/"false"`,
`dict`/`list` → JSON string, else as-is. **Send every known key**, not only the changed ones.

Temperature writes must set **both** the °C and °F key (`devHt` + `devHtf`, `devLt` + `devLtf`,
`targetTemp` + `targetTempF`, `waterTemp*Value` + `waterTemp*ValueF`) — `°F = round(°C * 1.8 + 32)`.

## Control keys (`DeviceControlKey`)

Ranges/scaling are what the HA UI enforces; the API itself does not validate much.

### Mode & power

| Key | Meaning | Value |
|-----|---------|-------|
| `atType` | active mode | 1–15, see [data-model.md](data-model.md#modes-attype--curmode) |
| `onSpead` | power level when "on" | 0–10 |
| `offSpead` | power level when "off" | 0–10 |
| `onSelfSpead` | power level in On mode (AI) | 0–10, not in Off mode |
| `speak` | current power (read-only) | 0–10 |
| `loadState` | currently powered (read-only) | 0/1 |
| `powerState`, `power`, `surplus`, `abnormalState`, `toward`, `modeType`, `masterPort`, `modeSetid`, `externalPort`, `devId` | pass through unchanged | |
| `onlyUpdateSpeed` | 0/1 | pass through |
| `restore` | bool | pass through |
| `isOpenAutomation` | 0/1 | pass through |

### Timer / cycle / schedule

| Key | Meaning | Storage | UI range |
|-----|---------|---------|----------|
| `acitveTimerOn` | Timer-to-On duration | **seconds** | 0–1440 min |
| `acitveTimerOff` | Timer-to-Off duration | seconds | 0–1440 min |
| `activeCycleOn` | Cycle on duration | seconds | 0–1440 min |
| `activeCycleOff` | Cycle off duration | seconds | 0–1440 min |
| `schedStartTime` | Schedule on time | minutes from midnight, `65535` = disabled | 0–1439 |
| `schedEndtTime` | Schedule off time | minutes from midnight, `65535` = disabled | 0–1439 |

Schedule "enabled" = value in 0..1439. Defaults when enabling: start `0`, end `1439`.

### Auto mode (temperature / humidity)

| Key | Meaning | Storage | Range |
|-----|---------|---------|-------|
| `settingMode` | 0 = high/low triggers, 1 = target | | |
| `activeHt` / `devHt` / `devHtf` | high temp trigger enabled / °C / °F | whole degrees | |
| `activeLt` / `devLt` / `devLtf` | low temp trigger enabled / °C / °F | whole degrees | |
| `targetTSwitch` / `targetTemp` / `targetTempF` | target temp enabled / °C / °F | whole degrees | |
| `activeHh` / `devHh` | high humidity trigger enabled / % | int | 0–100 |
| `activeLh` / `devLh` | low humidity trigger enabled / % | int | 0–100 |
| `targetHumiSwitch` / `targetHumi` | target humidity enabled / % | int | 0–100 |
| `temperature`, `temperatureF`, `humidity`, `insideTemp`, `outsideTemp`, `trend`, `tTrend`, `hTrend`, `insideTrend`, `outsideTrend`, `unit` | current readings, read-only pass-through | ×100 | |

### VPD mode

| Key | Meaning | Storage | Range |
|-----|---------|---------|-------|
| `vpdSettingMode` | 0 = triggers, 1 = target | | |
| `activeHtVpd` / `activeHtVpdNums` | high VPD enabled / value | **kPa × 10** (`102` = 10.2) | 0–9.9 |
| `activeLtVpd` / `activeLtVpdNums` | low VPD enabled / value | kPa × 10 | 0–9.9 |
| `targetVpdSwitch` / `targetVpd` | target VPD enabled / value | kPa × 10 | 0–9.9 |
| `vpdnums`, `vpdstatus`, `isUpdateVpdNums` | read-only pass-through | | |

### AI sensor modes (CO₂, CO₂ fan, moisture, water level, water temp, pH, EC/TDS)

Each group `<x>` ∈ {`co2`, `co2Fan`, `moisture`, `waterLevel`, `waterTemp`, `ph`, `ecTds`} has the same shape:

| Key pattern | Meaning |
|-------------|---------|
| `<x>SettingMode` | 0 = triggers, 1 = target |
| `<x>Accuracy` | hysteresis |
| `<x>TargetSwitch` / `<x>TargetValue` | target enabled / value |
| `<x>HighSwitch` / `<x>HighValue` | high trigger enabled / value |
| `<x>LowSwitch` / `<x>LowValue` | low trigger enabled / value |

Specifics: CO₂ values 0–9999 ppm; moisture 0–100 %; pH stored **×10** (`65` = 6.5), range 0–14; water temp
has `…Value` (°C) and `…ValueF` (°F) which must be written together; EC/TDS has four value variants per
trigger — `EcUs`, `EcMs`, `TdsPpm`, `TdsPpt` — plus `ecOrTds`, `ecUnit`, `tdsUnit`, and the low switch is split
into `ecTdsLowSwitchEc` / `ecTdsLowSwitchTds`. `waterLevelLowSwitch` doubles as the "water detect" enable.
`photocellSwitch` is the CO₂-mode photocell enable.

## Setting keys (`AdvancedSettingsKey`, the `devSetting` object)

### Controller-level (port 0)

| Key | Meaning | Storage / range |
|-----|---------|-----------------|
| `devName` | controller name — **must be sent unchanged** on `updateAdvSetting` | |
| `devCompany` | temperature unit: 0 = °F, else °C | |
| `devCt` / `devCth` | temperature calibration °C / °F | −20…20 °F, −10…10 °C |
| `devCt2` / `devCth2` | second sensor calibration | |
| `devCh` | humidity calibration | −10…10 |
| `vpdCt` / `vpdCth` | VPD leaf temperature offset °C / °F | −10…10 / −20…20 |
| `tempCompare` / `humiCompare` | outside climate: 0 Neutral, 1 Lower, 2 Higher | |
| `backlightSwitch`, `hasBacklightSwitch`, `keytoneSwitch`, `hasKeytoneSwitch`, `devLight` | display / beep | pass through |
| `sensorOneType`, `sensorTwoType`, `zoneSensorType`, `interchangeSensor`, `paramSensors`, `sensorSettingStr`, `sensorTransBuffStr` | sensor config (AI), JSON strings | pass through |
| `otaUpdating`, `supportOta`, `isShare`, `subDeviceId`, `subDeviceType`, `secFuc*`, `portParamData` | pass through | |

### Per-port (port 1..n)

| Key | Meaning | Storage / range |
|-----|---------|-----------------|
| `loadType` | device type, see load types in data-model.md | |
| `isFlag` | dynamic response: 0 Transition, 1 Buffer | |
| `devTt` / `devTth` | transition temperature °C / °F | int |
| `devTh` | transition humidity % | int |
| `vpdTransition` | transition VPD | kPa × 10 |
| `devBt` / `devBth` | buffer temperature °C / °F | int |
| `devBh` | buffer humidity % | int |
| `devBvpd` | buffer VPD | kPa × 10 |
| `onTimeSwitch` / `onTime` | sunrise timer enabled / minutes | |
| `isOnMinMaxTime` / `onMinTime` / `onMaxTime` | min/max on time | |
| `isOpenDoseTime` / `onDoseTime` / `offDoseTime` | dosing pump timing | |
| `onSpead`, `offSpead`, `onSelfSpead`, `atType`, `settingMode`, `vpdSettingMode`, `powerState`, `photocellSwitch`, `targetVpdSwitch`, `ecUnit`, `tdsUnit`, `ecOrTds`, `toward`, `externalPort`, `port`, `devId` | duplicated from controls, pass through | |

## Fixture: `getdevModeSettingList` response (standard controller, port 1)

Abridged from HA `tests/data_models.py::DEVICE_CONTROLS`; every key listed above appears in the real payload.

```jsonc
{
  "modeSetid": "8473928473928473928",
  "devId": "54929097239553773072",
  "externalPort": 4,
  "atType": 2,
  "onSpead": 5, "offSpead": 0, "onSelfSpead": 0,
  "activeHt": 0, "devHt": 66, "devHtf": 152,
  "activeLt": 0, "devLt": 25, "devLtf": 77,
  "activeHh": 0, "devHh": 18, "activeLh": 0, "devLh": 25,
  "acitveTimerOn": 21240, "acitveTimerOff": 2100,
  "activeCycleOn": 0, "activeCycleOff": 0,
  "schedStartTime": 0, "schedEndtTime": 0,
  "activeHtVpd": 0, "activeLtVpd": 0, "activeHtVpdNums": 0, "activeLtVpdNums": 0,
  "settingMode": 0, "vpdSettingMode": 0,
  "targetTSwitch": 0, "targetTemp": 0, "targetTempF": 32,
  "targetHumiSwitch": 0, "targetHumi": 0,
  "targetVpdSwitch": 0, "targetVpd": 0, "isUpdateVpdNums": false,
  "co2…": 0, "co2Fan…": 0, "moisture…": 0, "waterTemp…": 0, "ph…": 0, "ecTds…": 0, "waterLevel…": 0,
  "humidity": 4735, "temperature": 2238, "temperatureF": 7228,
  "speak": 0, "loadState": 0, "loadType": 8, "abnormalState": 0,
  "isOpenAutomation": 0, "onlyUpdateSpeed": 0, "restore": false,
  "surplus": 0, "modeType": 0, "masterPort": null,
  "ecOrTds": null, "tdsUnit": 0, "ecUnit": 0,
  "devSetting": {
    "devId": "54929097239553773072", "port": 1, "externalPort": 1, "devName": null,
    "devLight": 163, "hasBacklightSwitch": 1, "backlightSwitch": 1, "hasKeytoneSwitch": 0, "keytoneSwitch": 1,
    "devCth": 0, "devCt": 0, "devCth2": null, "devCt2": null, "devCh": 0,
    "devTt": 0, "devTh": 1, "devTth": 1, "vpdTransition": 1,
    "devBt": 7, "devBth": 14, "devBh": 3, "devBvpd": 6, "isFlag": 0,
    "devCompany": 0, "vpdCth": 0, "vpdCt": 0,
    "offSpead": 0, "onSpead": 10, "onSelfSpead": 0,
    "loadType": 0, "tempCompare": 2, "humiCompare": 1,
    "settingMode": 0, "vpdSettingMode": 0, "atType": null,
    "onTimeSwitch": 1, "onTime": 60,
    "isOnMinMaxTime": 2, "onMinTime": 0, "onMaxTime": 0,
    "isOpenDoseTime": 0, "onDoseTime": 0, "offDoseTime": 0,
    "photocellSwitch": 1, "ecOrTds": 0, "ecUnit": 0, "tdsUnit": 0, "interchangeSensor": 0,
    "portParamData": "[0, 2, 1, 2, 3, 232, 2, 1, 0]",
    "sensorSettingStr": null, "sensorTransBuffStr": null,
    "subDeviceId": null, "subDeviceVersion": null, "subDeviceType": null
  }
}
```

## Observed live (2026-09-23) — keys beyond the HA lists

`getdevModeSettingList` returned 142 top-level keys and 92 `devSetting` keys on both a 69 Pro (fw 3.2.56) and an
AI+ (fw 12.8.26). Compared with the key lists above:

- **Extra top-level keys** (not in `CONTROL_KEYS`, not sent on writes): `flowRate`, `interval`, `waterDuration`,
  `maxWateringAmount`, `schedModeFlowRate`, `sensorModeFlowRate`, `quickRunState`, `quickRunTime`, `protection`,
  `ipcSetting`, `fieldSet`, `reportSeq`, `timestamp`, `devMacAddr`, `devTimeZone` — watering-pump features.
- **`CONTROL_KEYS` absent from the response** (sent as `0` like HA does): `insideTemp`, `insideTrend`, `outsideTemp`,
  `outsideTrend`, `photocellSwitch`, `power`, `powerState`, `toward`, `vpdnums`, `vpdstatus`.
- **Extra `devSetting` keys** (not in `SETTING_KEYS`): `devCl`, `devCsm1..4`, `isLeafBulitIn`, `isLeafSensor1/2`,
  `calibrationTime`, `plantCode`, `plantingNum`, `potSize`, `matterCode`, `matterSta`, `qrPayLoad`, `uuid*`,
  `deviceColor`, `secFucReportTime`, `updateAllPort`, `portResistance`, `setId`, `subDeviceVersion`, `sensorSetting`,
  `sensorTransBuff`, `fieldSet`, `timestamp`, `devMacAddr`, `devTimeZone`.
- **`SETTING_KEYS` absent from `devSetting`**: `isShare`, `paramSensors`, `sensorOneType`, `sensorTwoType`,
  `targetVpdSwitch`, `zoneSensorType`.

The write path mirrors HA exactly (send the HA key set, default missing to 0). Whether the newer keys must be
echoed back is **untested** — verify on the first real write and extend the key tuples in `client.py` if the API
rejects or resets something.

## Availability rules worth mirroring in tool validation

- Timer keys only meaningful when `atType` is 4/5; cycle keys when 6; schedule when 7; VPD keys when 8; auto keys when 3; sensor-mode keys when 9–15.
- A port is "available" when `ports[].online == 1`.
- `updateAdvSetting` for controller-level settings is **not supported on AI controllers**.
