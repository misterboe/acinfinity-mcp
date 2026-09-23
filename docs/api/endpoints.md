# Endpoints

All requests: `User-Agent: okhttp/4.12.0`, form-encoded bodies, `token: <appId>` header (except login).
See [connection.md](connection.md).

| # | Method | Path | Purpose | Family |
|---|--------|------|---------|--------|
| 1 | POST | `/api/user/appUserLogin` | login → token | all |
| 2 | POST | `/api/user/devInfoListAll` | list controllers incl. ports, sensors, current readings | all |
| 3 | POST | `/api/dev/getdevModeSettingList` | mode/trigger settings + advanced settings for one port | all |
| 4 | POST | `/api/dev/addDevMode` | write mode/trigger settings for one port | standard |
| 5 | POST | `/api/dev/getDevSetting` | advanced settings for one port (port 0 = controller) | standard |
| 6 | POST | `/api/dev/updateAdvSetting` | write advanced settings | standard |
| 7 | PUT | `/api/dev/modeAndSetting` | write controls **and** settings in one call | AI |
| 8 | GET | `/api/dev/ml/secFuc?devId=` | per-port `secFuc*` + `portParamData` (works **without** `minversion`; 404 with it) | AI |
| 9 | POST | `/api/version=2.0/dev/getGroups` | Advance Automation rules — see [automations.md](automations.md) | all |
| 10 | POST | `/api/version=2.0/dev/getAlarms` | alarm definitions | all |
| 11 | GET | `/api/version=2.0/dev/recipe?advVersion=1` | grow-stage templates | all |
| 12 | POST | `/api/log/dataPage` | sensor history (time-cursor pagination, see ober37 Quirk 3) | all |

**`minversion: 3.5` header rewrites the route to `/api/3.5/…`** (visible in 404 bodies). On
`getdevModeSettingList` it adds `standardMode`, `devAdvGroups`, `insideTemp`/`outsideTemp`,
`isAdvTempTrigger` and fills `sensorSettingStr`/`sensorTransBuffStr`; other values (4.0 … 10.0)
fall back to the unversioned response. It is required for AI-controller writes (`addDevMode`,
`modeAndSetting`, v2 `addGroups`/`updateGroupsIsOn`/`delByid`).

"Standard" = Controller 69 Wifi / Pro / Pro+ (`devType` 11, 18). "AI" = AI+, Outlet AI, Outlet AI+ (`devType` 20, 21, 22).

---

## 1. Login

```
POST /api/user/appUserLogin
appEmail=<email>&appPasswordl=<password[:25]>
```
Returns `data.appId` → token. Details in [connection.md](connection.md).

## 2. Device list

```
POST /api/user/devInfoListAll
userId=<appId>
```

`data` is an array of controller objects (see [data-model.md](data-model.md)). Includes for each controller:
metadata, online state, `deviceInfo.ports[]` with per-port speed/state/name, controller-level temperature /
humidity / VPD, and on AI controllers `deviceInfo.sensors[]`. Does **not** include mode settings.

## 3. Mode settings for a port

```
POST /api/dev/getdevModeSettingList
devId=<controllerId>&port=<0..n>
```

(Bruno sends `devId`/`port` as query params, `userId` in the body and `minversion: 3.5`; the HA client sends
`devId`/`port` in the form body without `minversion`. Both work.)

`data` is a flat object with all control keys for that port (`atType`, `onSpead`, triggers, timers, …) plus a nested
`devSetting` object containing the advanced settings. Port `0` returns controller-level settings. Full key list in
[controls-and-settings.md](controls-and-settings.md), fixture in the same file.

## 4. Write mode settings (standard controllers)

```
POST /api/dev/addDevMode?<all DeviceControlKey fields url-encoded>
(empty body)
```

The full control object from endpoint 3 (minus `devSetting`) goes into the **query string**, with the changed
keys overlaid. Value serialisation: `None → 0`, `bool → "true"/"false"`, `dict/list → json.dumps(...)`.

## 5. Advanced settings for a port (standard controllers)

```
POST /api/dev/getDevSetting
devId=<controllerId>&port=<0..n>
```

`data` is the advanced-settings object (same shape as `devSetting` inside endpoint 3). Port 0 = controller
settings (temp unit, calibration, display), port n = per-device settings (load type, dynamic response, sunrise timer…).

## 6. Write advanced settings (standard controllers)

```
POST /api/dev/updateAdvSetting?<all AdvancedSettingsKey fields url-encoded>&devName=<name>
(empty body)
```

Same read-modify-write pattern with the `getDevSetting` result. `devName` **must** be set to the current controller
name (port 0) or port name (port n) or the call fails / renames the device. AI controllers do not support this endpoint
for controller-level settings (HA raises `NotImplementedError`).

## 7. Write controls + settings (AI controllers)

```
PUT /api/dev/modeAndSetting?<all ModeAndSettingKeys fields url-encoded>&modeAndSettingIdStr=[...]
Header: minversion: 3.5
(empty body)
```

Source object: endpoint 3 result, with `devSetting` **flattened into the top level** (`{**devSetting, **result}` —
top-level wins on conflicts). Overlay changed keys, then set `modeAndSettingIdStr` according to the resulting `atType`:

| `atType` | `modeAndSettingIdStr` |
|----------|-----------------------|
| 1 Off | `[16,17]` |
| 2 On | `[16,18]` |
| 3 Auto | `[112,16,19,32,98,99]` |
| 4 Timer to On / 5 Timer to Off | `[16,20,21]` |
| 6 Cycle / 7 Schedule | `[16,22,23,40]` |
| 8 VPD | `[16,81,32,98,99]` |
| 9–15 (sensor modes: CO2, CO2 Fan, Moisture, Water Temp, pH, EC, Water Detect) | `[16,97,32,98,99]` |

Complete example query string (Off mode) is in the HA repo at `.bruno/basic-controller/update-mode-and-settings.yml`.

## 8. ML security function (AI, unused)

```
GET /api/dev/ml/secFuc?devId=<controllerId>
```
Only documented via the Bruno collection; payload unknown. Related keys: `secFucStatus`, `secFucDevtype`,
`secFucDevEffect`, `secFucParams`, `secFucParamNums`.
