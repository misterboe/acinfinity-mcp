# Endpoints

All requests: `User-Agent: okhttp/4.12.0`, form-encoded bodies, `token: <appId>` header (except login).
See [connection.md](connection.md).

| # | Method | Path | Purpose | Family |
|---|--------|------|---------|--------|
| 1 | POST | `/api/user/appUserLogin` | login → token | all |
| 2 | POST | `/api/user/devInfoListAll` | list controllers incl. ports, sensors, current readings | all |
| 3 | POST | `/api/dev/getdevModeSettingList` | mode/trigger settings + advanced settings for one port | all |
| 4 | POST | `/api/dev/addDevMode` | write mode/trigger settings for one port (form body; AI needs `minversion`) | all |
| 5 | POST | `/api/dev/getDevSetting` | advanced settings for one port (port 0 = controller) | all |
| 6 | POST | `/api/dev/updateAdvSetting` | write advanced settings (signed, form body) | standard |
| 7 | PUT | `/api/dev/modeAndSetting` | app-native AI write: `atType` + field groups (`modeAndSettingIdStr`) + their values | AI |
| 8 | GET | `/api/dev/ml/secFuc?devId=` | per-port `secFuc*` + `portParamData` (works **without** `minversion`; 404 with it) | AI |
| 9 | POST | `/api/version=2.0/dev/getGroups` | Advance Automation rules — see [automations.md](automations.md) | all |
| 10 | POST | `/api/version=2.0/dev/getAlarms` | alarm definitions | all |
| 11 | GET | `/api/version=2.0/dev/recipe?advVersion=1` | grow-stage templates | all |
| 12 | POST | `/api/log/dataPage` | sensor history (time-cursor pagination, see ober37 Quirk 3) | all |

### 12. History (`/api/log/dataPage`)

```
POST /api/log/dataPage
devId=<id>&time=<unix start>&endTime=<unix end>&pageNum=1&pageSize=2000
```

`data = {rows: [...], total, validFrom}`; `pageNum` is ignored (paginate by advancing `time` past the
last `createTime`). Observed on the AI+ (2026-09-23), one row per ~5 min:

```jsonc
{"createTime": 1790172240, "temperature": 2200, "humidity": 6040, "vpdNums": 104,   // ×100, note vpdNums casing
 "portSpead": 99,          // 4-bit nibble per port, LSB = port 1: 0x63 → port1=3, port2=6
 "portStatus": 0,          // 1 bit per port: automation-triggered
 "allSpead": 0, "dataStatus": 0, "sensorDataBlock": 6, "devVersion": 13,
 "sensors": [ {"sensorType": 3, "accessPort": 1, "sensorData": 159, "sensorPrecision": 3, "interchangeSensor": 0}, … ],
 "leafTemp": 0, "leafTempF": 0, "thermalMin/Max/Avg/Center": 0, "thermalImagingSensorOnline": 0,
 "internalSensor*", "external1Sensor*", "external2Sensor*": null,   // older sensor slots
 "portDataBytes": null, "portStateData": null, "portSpeedMin": 0}
```

The `sensors[]` array carries the same per-sensor records as the live device list, so probe vs
onboard history can be separated. `/api/log/logdataByAll` answers `500` on this account.

## Endpoint census (2026-09-23)

Every public client that talks to `acinfinityserver.com` was cloned and grepped for API paths
(GitHub code search for `acinfinityserver`, `devInfoListAll`, `getdevModeSettingList`,
`appPasswordl`: dalinicus & Backroads4Me HA integrations, ober37/ac-infinity-mcp,
keithah/homebridge-acinfinity, i8beef/I8Beef.ACInfinity, awysocki/ACInfinity,
kornpow/ac-infinity-api, jakobgoerke/ac-infinity-client, ToBee94/ac-infinity-php,
LukeEvansTech/acinfinity-exporter + fansync, dwot/isley + ACScraper, sinister-labs/growpanion,
bselee/enviroflow.app). The union of AC Infinity paths they use:

| Path | Used by | Status here |
|------|---------|-------------|
| `/api/user/appUserLogin` | all | ✅ |
| `/api/user/devInfoListAll` | all | ✅ |
| `/api/dev/getdevModeSettingList` | all | ✅ |
| `/api/dev/addDevMode` | HA, ober37, homebridge, i8beef, php, ts | ✅ verified live (AI) |
| `/api/dev/modeAndSetting` | HA, ober37 | ✅ minimal PUT verified live |
| `/api/dev/getDevSetting` / `updateAdvSetting` | HA, ober37 | ✅ read / ⚠️ write standard only |
| `/api/dev/ml/secFuc` | HA Bruno | ✅ read |
| `/api/log/dataPage` | ober37, exporter, isley | ✅ read |
| `/api/log/logdataByAll`, `DELETE /api/log/log` | ober37 | ✗ 500 here / not tried (destructive) |
| `/api/version=2.0/dev/getGroups` … `delByid` | ober37 | ✅ read, edit, toggle / create+delete not wired |
| `/api/version=2.0/dev/getAlarms` … `delAlarmsByid` | ober37 | ✅ read / writes not wired |
| `/api/version=2.0/dev/recipe` | ober37 | ✅ read (3 `advVersion` variants) |
| `/api/upgrade/getUpgrade` | ober37 | ✅ read: `POST fFamily=<devType>&firmwareVersion=&hardwareVersion=` → `{"msg":"No Entity","data":{"iosSupportVersion":"2.0.7","iosSupportMax":"2.9.9","androidSupportVersion":"2.0.6","androidSupportMax":"2.9.9"}}` when no firmware update exists |
| `/api/upgrade/downgrade` | ober37 | not tried (needs `devMacAddr`; returns a firmware download URL) |

No public client knows more than this list. The **complete** inventory — every Retrofit
declaration of the Android app, 179 method+path pairs — is in [app-endpoints.md](app-endpoints.md).

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

## 4. Write mode settings (both families)

```
POST /api/dev/addDevMode
Content-Type: application/x-www-form-urlencoded
<all CONTROL_KEYS fields>            # AI: header minversion: 3.5   standard: sign headers
```

The full control object from endpoint 3 (minus `devSetting`) goes into the **form body**, with the changed
keys overlaid. Value serialisation: `None → 0`, `bool → "true"/"false"`, `dict/list → json.dumps(...)`.
Verified live on an AI+ (2026-09-23). The query-string variant the old HA client used returns `100001`
on AI controllers and is silently discarded on standard ones (HA issue #157). Fields that do not belong
to the written `atType` are discarded with `200` — send a mode's parameters together with that mode.

## 5. Advanced settings for a port (standard controllers)

```
POST /api/dev/getDevSetting
devId=<controllerId>&port=<0..n>
```

`data` is the advanced-settings object (same shape as `devSetting` inside endpoint 3). Port 0 = controller
settings (temp unit, calibration, display), port n = per-device settings (load type, dynamic response, sunrise timer…).

## 6. Write advanced settings (standard controllers)

```
POST /api/dev/updateAdvSetting
<all SETTING_KEYS fields>&devName=<current name>     # form body + sign headers (connection.md)
```

Same read-modify-write pattern with the `getDevSetting` result. `devName` **must** be set to the current controller
name (port 0) or port name (port n) or the device is renamed. On AI controllers the endpoint answers
`999999 Operation failed` (with `minversion` it 404s) — use the minimal `modeAndSetting` PUT there.

## 7. Write controls + settings (AI controllers)

```
PUT /api/dev/modeAndSetting?devId=…&port=…&atType=<n>&modeAndSettingIdStr=[16,…]&<fields of the listed groups>
Header: minversion: 3.5
(empty body)
```

This is how the app writes AI controllers (HA Bruno captures, verified live): **only** the changed field
groups travel, identified by `modeAndSettingIdStr`; see [controls-and-settings.md](controls-and-settings.md)
for the group-id table and the "send the whole group" rule. The HA integration's full-object variant
(`{**devSetting, **result}` flattened) is accepted with `200` but **must not be used** — it renamed a port
to "0" in a live test because `devSetting.devName` is null on AI controllers. Group ids per `atType`:

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
