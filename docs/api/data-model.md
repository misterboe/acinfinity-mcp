# Data Model (`/api/user/devInfoListAll`)

`data` is an array of controllers. Identifiers are large integers; treat `devId` as a **string** everywhere
(the fixtures show it as a string at top level and as an int inside `deviceInfo`).

## Controller object

```jsonc
{
  "devId": "54929097239553773072",
  "devCode": "ABCDEFG",
  "devName": "Grow Tent",          // name set in the app
  "devType": 11,                   // see Controller types
  "devPortCount": 4,
  "devMacAddr": "2B120D62DC00",    // stable unique id (HA uses it for entity ids)
  "devVersion": 7,
  "online": 1,
  "isShare": 0,
  "firmwareVersion": "3.2.25",
  "hardwareVersion": "1.1",
  "workMode": 1,
  "zoneId": "America/Chicago",     // IANA tz — used to turn remainTime into a timestamp
  "devTimeZone": "GMT+00:00",
  "devAccesstime": 1692328784, "devOfftime": 1692328718,
  "deviceInfo": {
    "devId": 54929097239553773072,
    "temperature": 2417,           // °C × 100 (standard controllers)
    "temperatureF": 7551,          // °F × 100
    "humidity": 7200,              // % × 100
    "vpdnums": 83,                 // kPa × 100
    "vpdstatus": 0,
    "tTrend": 0, "hTrend": 0, "trend": 0,
    "unit": 0,
    "online": 1,
    "curMode": 3, "modeTye": 15,
    "master": 0, "masterPort": 2, "allPortStatus": 7,
    "tempCompare": 1, "humiCompare": 2,
    "isOpenAutomation": 0, "loadState": 0, "abnormalState": 0, "overcurrentStatus": 0,
    "ports": [ /* Port objects */ ],
    "sensors": null                // array on AI controllers, null otherwise
  }
}
```

### Controller types (`devType`)

| Value | Model | Family |
|-------|-------|--------|
| 11 | UIS Controller 69 Pro (CTR69P) | standard |
| 18 | UIS Controller 69 Pro+ (CTR69Q) | standard |
| 20 | UIS Controller AI+ (CTR89Q) | AI |
| 21 | UIS Controller Outlet AI (AC-ADA4) | AI |
| 22 | UIS Controller Outlet AI+ (AC-ADA8) | AI |

Family decides which write endpoints to use (see [endpoints.md](endpoints.md)).

## Port object (`deviceInfo.ports[]`)

```jsonc
{
  "port": 1,                 // 1-based index as printed on the controller
  "portName": "Grow Lights", // user-set name
  "speak": 5,                // current power level 0–10
  "loadState": 1,            // 1 = device currently on, 0 = off
  "online": 1,               // 1 = something plugged in / responding
  "curMode": 7,              // current atType (see Modes)
  "remainTime": 500,         // seconds until next scheduled state change; null/0 = none
  "modeTye": 0,
  "loadType": 0,
  "portResistance": 3300,    // 65535 when nothing is connected
  "isOpenAutomation": 0,
  "abnormalState": 0, "overcurrentStatus": 0,
  "deviceType": null, "portAccess": null, "advUpdateTime": null, "trend": 0
}
```

`next state change = now(zoneId) + remainTime seconds` (only when `remainTime > 0`).

## Sensor object (`deviceInfo.sensors[]`, AI controllers only)

```jsonc
{
  "accessPort": 1,        // USB-C sensor port; 7 = built-in controller sensor
  "sensorType": 1,        // see Sensor types
  "sensorUnit": 1,        // temperature: 0 = °F, 1 = °C
  "sensorPrecision": 3,   // number of significant digits incl. decimals
  "sensorData": 2450,     // raw integer
  "sensorTrend": 0
}
```

**Value decoding:** `value = sensorData / 10 ** (sensorPrecision - 1)` when `sensorPrecision > 1`, else `sensorData`.
For temperature types additionally: if `sensorUnit == 0` (°F) convert `°C = (value - 32) * 5 / 9`, rounded to
`sensorPrecision - 1` decimals. Examples: `2450, precision 3 → 24.50 °C`; `7610, precision 3, unit 0 → 76.1 °F → 24.5 °C`;
`723, precision 1 → 723 ppm CO₂`; `204, precision 3 → 2.04 kPa`.

### Sensor types (`sensorType`)

| Value | Meaning | Unit | Physical sensor |
|-------|---------|------|-----------------|
| 0 | Probe temperature | °F | AC-SPC24 probe |
| 1 | Probe temperature | °C | AC-SPC24 probe |
| 2 | Probe humidity | % | AC-SPC24 probe |
| 3 | Probe VPD | kPa | AC-SPC24 probe |
| 4 | Controller temperature | °F | built-in |
| 5 | Controller temperature | °C | built-in |
| 6 | Controller humidity | % | built-in |
| 7 | Controller VPD | kPa | built-in |
| 10 | Soil moisture | % | AC-SLS3 |
| 11 | CO₂ | ppm | AC-COS3 |
| 12 | Light | % | AC-COS3 |
| 13 | Hydro pH | pH | AC-HDS3 |
| 14 | Hydro EC | µS/cm | AC-HDS3 |
| 15 | Hydro EC | mS/cm | AC-HDS3 |
| 16 | Hydro TDS | ppm | AC-HDS3 |
| 17 | Hydro TDS | ppt | AC-HDS3 |
| 18 | Hydro water temperature | °F | AC-HDS3 |
| 19 | Hydro water temperature | °C | AC-HDS3 |
| 20 | Water detect | 0/1 | AC-WDS3 |

Pairs (0/1, 4/5, 14/15, 16/17, 18/19) are mutually exclusive: a device reports one of the two depending on its unit
setting. Expose one logical reading per pair.

## Observed live (2026-09-23, account with one 69 Pro and one AI+)

- **Offline sentinel:** an offline standard controller reports `temperature`, `humidity` and `vpdnums` as
  `-32768` (int16 min). Treat it as "no reading", never as −327.68.
- The controller object now carries many more top-level keys than the HA fixtures (`devTypeName`, `deviceColor`,
  `newFrameworkDevice`, `mqttdevice`, `ipc*`, `cameraSeries`, `familyH*`, `outlet`, `airTap`, …) and `deviceInfo`
  has additional ones (`sensorReadings` — was `null`, `thermal*`, `insideRoomName`, `isLock`, `scene`, `hOsc`/`vOsc`,
  `currentWatering`/`nextWatering`, `calibration`, `climateSensorOnline`). All were `null`/0 on the test account;
  ignore unknown keys, never fail on them.
- Sensor objects carry an extra `sensorKey` (`"<sensorType>-<accessPort>"`). On the AI+ the built-in
  climate sensor was on `accessPort` **2**, not 7 as in the HA fixtures — do not hard-code the port.
- **Inside vs. outside on AI controllers:** `deviceInfo.temperature` / `humidity` / `vpdnums` are byte-identical
  to the `sensorType` 4–7 ("controller") entries, i.e. the **onboard sensor in the controller housing**, which
  physically sits outside the tent. The **probe** entries (`sensorType` 0–3) are the tent climate. The server
  exposes them as `ambient` (onboard) and `tent` (probe); never present the controller-level values as the tent
  climate on an AI controller. Standard controllers have no onboard sensor, so their `deviceInfo` values *are*
  the probe.
- The AI+ (CTR89Q) reports `devPortCount: 8`.
- `remainTime` is `0`/`null` whenever the port is not in a counting mode (Off, On, Auto, VPD). A configured
  `acitveTimerOn` in the mode settings does not start a countdown until `atType` is 4/5.
- Wrong ids surface as body codes, not HTTP errors: unknown `devId` → `code 401 "Data saving failed"`,
  port beyond `devPortCount` → `code 403 "Data saving failed"`. The client validates both before calling.
- Anonymised copies of the live payloads are in `tests/fixtures/`.

## Standard-controller readings

Standard controllers (types 11, 18) have no `sensors` array. Readings live directly in `deviceInfo`:
`temperature` (°C×100), `temperatureF` (°F×100), `humidity` (%×100), `vpdnums` (kPa×100). Divide by 100.

## Modes (`atType` / `curMode`)

| Value | Mode | Notes |
|-------|------|-------|
| 1 | Off | |
| 2 | On | uses `onSpead` |
| 3 | Auto | temp/humidity triggers or targets |
| 4 | Timer to On | `acitveTimerOn` seconds |
| 5 | Timer to Off | `acitveTimerOff` seconds |
| 6 | Cycle | `activeCycleOn`/`activeCycleOff` seconds |
| 7 | Schedule | `schedStartTime`/`schedEndtTime` minutes from midnight |
| 8 | VPD | VPD triggers or target |
| 9 | CO₂ | AI sensor modes from here down |
| 10 | CO₂ Fan | |
| 11 | Moisture | |
| 12 | Water Temp | |
| 13 | pH | |
| 14 | EC | |
| 15 | Water Detect | |

## Load types (`loadType`, in advanced settings)

Standard controllers: `0` No Device Type, `1` Grow Light, `2` Humidifier, `3` Dehumidifier, `4` Heater, `5` AC,
`6` Fan, `8` Water Pump.
AI controllers: `128` Outlet, `129` Grow Light, `130` Humidifier, `131` Dehumidifier, `132` Heater, `133` AC,
`134` Circulation Fan, `135` Ventilation Fan, `136` Peristaltic Pump, `137` Water Pump, `138` CO₂ Regulator.

## Other enums

- `tempCompare` / `humiCompare` (outside climate): `0` Neutral, `1` Lower, `2` Higher
- `isFlag` (dynamic response type): `0` Transition, `1` Buffer
- `settingMode` / `vpdSettingMode`: `0` Auto (high/low triggers), `1` Target
- `devCompany` (temperature unit of the controller): `0` = °F, `>0` = °C
