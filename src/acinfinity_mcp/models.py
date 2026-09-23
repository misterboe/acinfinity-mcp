"""Typed views over the AC Infinity cloud API payloads.

Raw JSON shapes and scaling rules are documented in docs/api/data-model.md and
docs/api/controls-and-settings.md. All unit conversion happens here; tools and the
client never touch scaled integers directly.
"""

from __future__ import annotations

import json
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field

SCHEDULE_DISABLED = 65535


class ControllerType(IntEnum):
    UIS_69_PRO = 11
    UIS_69_PRO_PLUS = 18
    UIS_89_AI_PLUS = 20
    UIS_OUTLET_AI = 21
    UIS_OUTLET_AI_PLUS = 22


AI_CONTROLLER_TYPES = frozenset(
    {ControllerType.UIS_89_AI_PLUS, ControllerType.UIS_OUTLET_AI, ControllerType.UIS_OUTLET_AI_PLUS}
)

CONTROLLER_MODEL_NAMES = {
    ControllerType.UIS_69_PRO: "UIS Controller 69 Pro (CTR69P)",
    ControllerType.UIS_69_PRO_PLUS: "UIS Controller 69 Pro+ (CTR69Q)",
    ControllerType.UIS_89_AI_PLUS: "UIS Controller AI+ (CTR89Q)",
    ControllerType.UIS_OUTLET_AI: "UIS Controller Outlet AI (AC-ADA4)",
    ControllerType.UIS_OUTLET_AI_PLUS: "UIS Controller Outlet AI+ (AC-ADA8)",
}


class Mode(IntEnum):
    """`atType` / `curMode` of a port."""

    OFF = 1
    ON = 2
    AUTO = 3
    TIMER_TO_ON = 4
    TIMER_TO_OFF = 5
    CYCLE = 6
    SCHEDULE = 7
    VPD = 8
    CO2 = 9
    CO2_FAN = 10
    MOISTURE = 11
    WATER_TEMP = 12
    PH = 13
    EC = 14
    WATER_DETECT = 15


MODE_NAMES: dict[int, str] = {
    Mode.OFF: "Off",
    Mode.ON: "On",
    Mode.AUTO: "Auto",
    Mode.TIMER_TO_ON: "Timer to On",
    Mode.TIMER_TO_OFF: "Timer to Off",
    Mode.CYCLE: "Cycle",
    Mode.SCHEDULE: "Schedule",
    Mode.VPD: "VPD",
    Mode.CO2: "CO2",
    Mode.CO2_FAN: "CO2 Fan",
    Mode.MOISTURE: "Moisture",
    Mode.WATER_TEMP: "Water Temp",
    Mode.PH: "pH",
    Mode.EC: "EC",
    Mode.WATER_DETECT: "Water Detect",
}


def mode_name(value: int) -> str:
    return MODE_NAMES.get(value, f"Unknown mode {value}")


class SensorType(IntEnum):
    PROBE_TEMPERATURE_F = 0
    PROBE_TEMPERATURE_C = 1
    PROBE_HUMIDITY = 2
    PROBE_VPD = 3
    CONTROLLER_TEMPERATURE_F = 4
    CONTROLLER_TEMPERATURE_C = 5
    CONTROLLER_HUMIDITY = 6
    CONTROLLER_VPD = 7
    SOIL = 10
    CO2 = 11
    LIGHT = 12
    HYDRO_PH = 13
    HYDRO_EC_US = 14
    HYDRO_EC_MS = 15
    HYDRO_TDS_PPM = 16
    HYDRO_TDS_PPT = 17
    HYDRO_WATER_TEMPERATURE_F = 18
    HYDRO_WATER_TEMPERATURE_C = 19
    WATER = 20


LOCATION_PROBE = "probe"  # external sensor probe on a cable, normally hung inside the tent
LOCATION_ONBOARD = "onboard"  # sensor inside the controller housing, normally outside the tent
LOCATION_ACCESSORY = "accessory"  # CO2/light/soil/hydro/water sensors, wherever they are placed

# (kind, unit, location) per sensor type; temperatures are always reported in °C after conversion.
_SENSOR_META: dict[int, tuple[str, str, str]] = {
    SensorType.PROBE_TEMPERATURE_F: ("temperature", "°C", LOCATION_PROBE),
    SensorType.PROBE_TEMPERATURE_C: ("temperature", "°C", LOCATION_PROBE),
    SensorType.PROBE_HUMIDITY: ("humidity", "%", LOCATION_PROBE),
    SensorType.PROBE_VPD: ("vpd", "kPa", LOCATION_PROBE),
    SensorType.CONTROLLER_TEMPERATURE_F: ("temperature", "°C", LOCATION_ONBOARD),
    SensorType.CONTROLLER_TEMPERATURE_C: ("temperature", "°C", LOCATION_ONBOARD),
    SensorType.CONTROLLER_HUMIDITY: ("humidity", "%", LOCATION_ONBOARD),
    SensorType.CONTROLLER_VPD: ("vpd", "kPa", LOCATION_ONBOARD),
    SensorType.SOIL: ("soil_moisture", "%", LOCATION_ACCESSORY),
    SensorType.CO2: ("co2", "ppm", LOCATION_ACCESSORY),
    SensorType.LIGHT: ("light", "%", LOCATION_ACCESSORY),
    SensorType.HYDRO_PH: ("hydro_ph", "pH", LOCATION_ACCESSORY),
    SensorType.HYDRO_EC_US: ("hydro_ec", "µS/cm", LOCATION_ACCESSORY),
    SensorType.HYDRO_EC_MS: ("hydro_ec", "mS/cm", LOCATION_ACCESSORY),
    SensorType.HYDRO_TDS_PPM: ("hydro_tds", "ppm", LOCATION_ACCESSORY),
    SensorType.HYDRO_TDS_PPT: ("hydro_tds", "ppt", LOCATION_ACCESSORY),
    SensorType.HYDRO_WATER_TEMPERATURE_F: ("hydro_water_temperature", "°C", LOCATION_ACCESSORY),
    SensorType.HYDRO_WATER_TEMPERATURE_C: ("hydro_water_temperature", "°C", LOCATION_ACCESSORY),
    SensorType.WATER: ("water_detected", "bool", LOCATION_ACCESSORY),
}

_TEMPERATURE_TYPES = frozenset(
    {
        SensorType.PROBE_TEMPERATURE_F,
        SensorType.PROBE_TEMPERATURE_C,
        SensorType.CONTROLLER_TEMPERATURE_F,
        SensorType.CONTROLLER_TEMPERATURE_C,
        SensorType.HYDRO_WATER_TEMPERATURE_F,
        SensorType.HYDRO_WATER_TEMPERATURE_C,
    }
)


class SensorReading(BaseModel):
    kind: str = Field(description="Measurement: temperature, humidity, vpd, co2, hydro_ph, ...")
    location: str = Field(
        description="'probe' = external probe (normally inside the tent), "
        "'onboard' = sensor in the controller housing (normally outside the tent), "
        "'accessory' = plug-in sensor (CO2, light, soil, hydro, water)."
    )
    value: float | bool
    unit: str
    sensor_port: int = Field(description="USB-C sensor port the reading comes from.")
    raw_type: int = Field(description="API sensorType id, see docs/api/data-model.md.")


class Climate(BaseModel):
    temperature_c: float | None = None
    humidity_pct: float | None = None
    vpd_kpa: float | None = None


class Port(BaseModel):
    port: int = Field(description="1-based port number as printed on the controller.")
    name: str
    online: bool = Field(description="A UIS device is plugged in and responding.")
    is_on: bool = Field(
        description="The connected device is currently running (power > 0 or loadState=1)."
    )
    power: int = Field(ge=0, le=10, description="Current power level 0-10 actually applied.")
    mode: Mode | int = Field(description="Active mode id (atType).")
    mode_name: str = Field(description="Human-readable mode, e.g. 'Off', 'Auto', 'VPD'.")
    load_type: int
    seconds_until_next_change: int | None = Field(
        default=None,
        description="Seconds until the running timer/cycle/schedule flips the port; "
        "null unless such a mode is active and counting.",
    )


class Controller(BaseModel):
    id: str = Field(description="devId — use this for all other tools.")
    name: str
    model: str
    type: int
    is_ai: bool = Field(
        description="AI family controllers expose a sensors[] array and use a different write path."
    )
    online: bool
    port_count: int
    mac_address: str
    firmware_version: str | None = None
    hardware_version: str | None = None
    timezone: str | None = None
    tent: Climate | None = Field(
        default=None,
        description="Climate INSIDE the grow tent: the external probe. This is what the plants "
        "experience and what Auto/VPD triggers act on. Null when the probe is missing or offline.",
    )
    ambient: Climate | None = Field(
        default=None,
        description="Climate at the controller housing (onboard sensor), normally OUTSIDE the "
        "tent. Only AI controllers have this; do not report it as the tent climate.",
    )
    ports: list[Port]
    sensors: list[SensorReading] = Field(
        default_factory=list,
        description="All individual sensor readings (AI controllers); tent/ambient are derived.",
    )


class ControllerList(BaseModel):
    controllers: list[Controller]


class ThresholdTrigger(BaseModel):
    enabled: bool
    value: float


class PortSettings(BaseModel):
    """Decoded mode settings of one port (from getdevModeSettingList)."""

    controller_id: str
    port: int
    mode: Mode | int = Field(description="Active mode id (atType).")
    mode_name: str
    on_power: int = Field(ge=0, le=10)
    off_power: int = Field(ge=0, le=10)
    auto_setting_mode: str = Field(description="'triggers' (high/low) or 'target'.")
    temp_high_c: ThresholdTrigger
    temp_low_c: ThresholdTrigger
    target_temp_c: ThresholdTrigger
    humidity_high_pct: ThresholdTrigger
    humidity_low_pct: ThresholdTrigger
    target_humidity_pct: ThresholdTrigger
    vpd_setting_mode: str
    vpd_high_kpa: ThresholdTrigger
    vpd_low_kpa: ThresholdTrigger
    target_vpd_kpa: ThresholdTrigger
    timer_to_on_minutes: int
    timer_to_off_minutes: int
    cycle_on_minutes: int
    cycle_off_minutes: int
    schedule_start: str | None = Field(description="HH:MM or null when disabled.")
    schedule_end: str | None


class WriteResult(BaseModel):
    ok: bool = True
    controller_id: str
    port: int
    changed: dict[str, Any] = Field(description="API keys that were written, in API units.")


# --------------------------------------------------------------------------- decoding


def _decode_sensor(raw: dict[str, Any]) -> SensorReading | None:
    sensor_type = raw.get("sensorType")
    if sensor_type not in _SENSOR_META:
        return None
    kind, unit, location = _SENSOR_META[sensor_type]
    precision = raw.get("sensorPrecision") or 1
    data = raw.get("sensorData") or 0
    value: float = data / (10 ** (precision - 1)) if precision > 1 else data
    if sensor_type in _TEMPERATURE_TYPES and (raw.get("sensorUnit") or 0) == 0:
        value = round((value - 32) * 5 / 9, max(precision - 1, 1))
    return SensorReading(
        kind=kind,
        location=location,
        value=bool(value) if kind == "water_detected" else value,
        unit=unit,
        sensor_port=raw.get("accessPort", 0),
        raw_type=sensor_type,
    )


def _climate_from_sensors(sensors: list[SensorReading], location: str) -> Climate | None:
    values = {s.kind: s.value for s in sensors if s.location == location}
    if not values:
        return None
    return Climate(
        temperature_c=values.get("temperature"),
        humidity_pct=values.get("humidity"),
        vpd_kpa=values.get("vpd"),
    )


def _decode_port(raw: dict[str, Any]) -> Port:
    remain = raw.get("remainTime")
    mode = raw.get("curMode") or Mode.OFF
    power = raw.get("speak") or 0
    return Port(
        port=raw["port"],
        name=raw.get("portName") or f"Port {raw['port']}",
        online=raw.get("online") == 1,
        # loadState stays 0 on AI controllers while an Advance Automation drives the port,
        # so the applied power level is the reliable signal (observed live 2026-09-23).
        is_on=raw.get("loadState") == 1 or power > 0,
        power=power,
        mode=mode,
        mode_name=mode_name(mode),
        load_type=raw.get("loadType") or 0,
        seconds_until_next_change=remain if remain and remain > 0 else None,
    )


OFFLINE_SENTINEL = -32768  # int16 min; the cloud reports it when the controller is offline


def _hundredths(value: Any) -> float | None:
    if not isinstance(value, int | float) or value == OFFLINE_SENTINEL:
        return None
    return value / 100


def decode_controller(raw: dict[str, Any]) -> Controller:
    info = raw.get("deviceInfo") or {}
    dev_type = raw.get("devType")
    try:
        model = CONTROLLER_MODEL_NAMES[ControllerType(dev_type)]
    except ValueError:
        model = f"UIS Controller Type {dev_type}"
    is_ai = dev_type in AI_CONTROLLER_TYPES
    sensors = [s for s in (_decode_sensor(x) for x in info.get("sensors") or []) if s]
    if is_ai:
        # deviceInfo.temperature/humidity/vpdnums duplicate the ONBOARD sensor on AI controllers
        # (verified live 2026-09-23), so the tent climate must come from the probe entries.
        tent = _climate_from_sensors(sensors, LOCATION_PROBE)
        ambient = _climate_from_sensors(sensors, LOCATION_ONBOARD)
    else:
        # Standard controllers have no onboard sensor; deviceInfo values are the probe.
        tent = Climate(
            temperature_c=_hundredths(info.get("temperature")),
            humidity_pct=_hundredths(info.get("humidity")),
            vpd_kpa=_hundredths(info.get("vpdnums")),
        )
        if tent.temperature_c is None and tent.humidity_pct is None:
            tent = None
        ambient = None
    return Controller(
        id=str(raw["devId"]),
        name=raw.get("devName") or str(raw["devId"]),
        model=model,
        type=dev_type,
        is_ai=is_ai,
        online=raw.get("online") == 1,
        port_count=raw.get("devPortCount") or len(info.get("ports") or []),
        mac_address=raw.get("devMacAddr") or "",
        firmware_version=raw.get("firmwareVersion"),
        hardware_version=raw.get("hardwareVersion"),
        timezone=raw.get("zoneId"),
        tent=tent,
        ambient=ambient,
        ports=[_decode_port(p) for p in info.get("ports") or []],
        sensors=sensors,
    )


def _minutes_to_hhmm(value: Any) -> str | None:
    if not isinstance(value, int) or value < 0 or value > 1439:
        return None
    return f"{value // 60:02d}:{value % 60:02d}"


def hhmm_to_minutes(value: str | None) -> int:
    if value is None:
        return SCHEDULE_DISABLED
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _trigger(raw: dict[str, Any], switch: str, value: str, scale: float = 1) -> ThresholdTrigger:
    return ThresholdTrigger(enabled=raw.get(switch) == 1, value=(raw.get(value) or 0) / scale)


def decode_port_settings(controller_id: str, port: int, raw: dict[str, Any]) -> PortSettings:
    mode = raw.get("atType") or Mode.OFF
    return PortSettings(
        controller_id=controller_id,
        port=port,
        mode=mode,
        mode_name=mode_name(mode),
        on_power=raw.get("onSpead") or 0,
        off_power=raw.get("offSpead") or 0,
        auto_setting_mode="target" if raw.get("settingMode") == 1 else "triggers",
        temp_high_c=_trigger(raw, "activeHt", "devHt"),
        temp_low_c=_trigger(raw, "activeLt", "devLt"),
        target_temp_c=_trigger(raw, "targetTSwitch", "targetTemp"),
        humidity_high_pct=_trigger(raw, "activeHh", "devHh"),
        humidity_low_pct=_trigger(raw, "activeLh", "devLh"),
        target_humidity_pct=_trigger(raw, "targetHumiSwitch", "targetHumi"),
        vpd_setting_mode="target" if raw.get("vpdSettingMode") == 1 else "triggers",
        vpd_high_kpa=_trigger(raw, "activeHtVpd", "activeHtVpdNums", 10),
        vpd_low_kpa=_trigger(raw, "activeLtVpd", "activeLtVpdNums", 10),
        target_vpd_kpa=_trigger(raw, "targetVpdSwitch", "targetVpd", 10),
        timer_to_on_minutes=(raw.get("acitveTimerOn") or 0) // 60,
        timer_to_off_minutes=(raw.get("acitveTimerOff") or 0) // 60,
        cycle_on_minutes=(raw.get("activeCycleOn") or 0) // 60,
        cycle_off_minutes=(raw.get("activeCycleOff") or 0) // 60,
        schedule_start=_minutes_to_hhmm(raw.get("schedStartTime")),
        schedule_end=_minutes_to_hhmm(raw.get("schedEndtTime")),
    )


def celsius_to_fahrenheit(value: float) -> int:
    return round(value * 1.8 + 32)


# --------------------------------------------------------------------- Advance Automations
#
# `currentMode` of a rule is numbered differently per controller family and On/Off are
# inverted between them (verified on live hardware by ober37/ac-infinity-mcp, Quirk 35).
_AUTOMATION_MODE_NEW_FRAMEWORK = {1: "Off", 2: "On", 3: "Auto", 6: "Cycle", 8: "VPD"}
_AUTOMATION_MODE_LEGACY = {1: "On", 2: "Off", 3: "Cycle", 4: "Auto", 6: "VPD"}
_DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_SENSOR_MODE_RECORD_LEN = 11


class AutomationThreshold(BaseModel):
    """One sensor of a new-framework Auto/VPD rule, decoded from `sensorModeData`.

    Record layout (11 bytes per sensor) taken from the app's own parser
    (`extractSensorData`, app 2.0.8): [0] sensorType, [1] switch bits, [2] precision codes,
    [3] transition, [4] buffer, [5:7] target, [7:9] high, [9:11] low (int16).
    Temperature is normalised to °C (the API stores a °F twin record).
    """

    sensor_kind: str
    sensor_location: str
    unit: str
    control: str = Field(
        description="'target' (hold a setpoint), 'triggers' (high/low thresholds) or 'none'."
    )
    target: float | None = Field(description="Setpoint when control='target', else null.")
    high: float | None = Field(description="Turn on above this value; null = not enabled.")
    low: float | None = Field(description="Turn on below this value; null = not enabled.")
    buffer: float | None = Field(
        default=None, description="Hysteresis band around the threshold, sensor units."
    )
    transition: float | None = Field(
        default=None, description="Dynamic-response step per level, sensor units."
    )
    raw: list[int] = Field(
        description="The 11-int record(s) as stored; bits 4/8/16 of [1] unknown."
    )


class AutomationRule(BaseModel):
    rule_id: int = Field(description="advId — identifies this rule.")
    program: str = Field(description="advName — rules sharing a name form one program.")
    enabled: bool = Field(description="isOn: the rule is switched on in the app.")
    running: bool = Field(description="runState: the rule is currently in effect.")
    ports: list[int] = Field(
        description="Ports governed by this rule (from the grouptDevType bitmask)."
    )
    mode: str = Field(description="Off, On, Auto, Cycle, VPD or 'Unknown (n)'.")
    on_power: int = Field(ge=0, le=10)
    off_power: int = Field(ge=0, le=10)
    continuous: bool = Field(
        description="True = the app's 24/7 switch is on: the rule applies at all times and "
        "any stored time window/days are IGNORED. False = only within window/days."
    )
    schedule: str = Field(description="Human summary: '24/7' or 'Mon-Fri 09:00-17:00'.")
    window_start: str | None = Field(
        description="Daily start HH:MM (controller local time); null when continuous."
    )
    window_end: str | None = Field(description="Daily end HH:MM; null when continuous.")
    days: list[str] = Field(description="Weekdays the window applies to; empty when continuous.")
    stored_window: str | None = Field(
        default=None,
        description="The window/days still stored on the rule while the 24/7 switch is on "
        "(inactive; becomes the schedule again when the switch is turned off).",
    )
    cycle_on_minutes: int | None = None
    cycle_off_minutes: int | None = None
    min_on_minutes: int | None = Field(default=None, description="onMinTime when isOnMinMaxTime=1.")
    thresholds: list[AutomationThreshold] = Field(
        default_factory=list,
        description="Auto/VPD sensor thresholds on AI controllers (from sensorModeData).",
    )
    legacy_triggers: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-rail auto*/target*/vpd trigger fields (standard controllers keep "
        "thresholds here; on AI controllers these are usually parked at rails).",
    )


class AutomationList(BaseModel):
    controller_id: str
    programs: list[str] = Field(description="Distinct program names, in API order.")
    rules: list[AutomationRule]


def _ports_from_mask(mask: int | None) -> list[int]:
    mask = mask or 0
    return [i + 1 for i in range(8) if mask & (1 << i)]


def _days_from_switch_time(value: int | None) -> tuple[list[str], bool]:
    value = value or 0
    days = [name for i, name in enumerate(_DAY_NAMES) if value & (1 << i)]
    return days, bool(value & 0x80)


_LEGACY_TRIGGER_KEYS = (
    ("autoHighTempF", 32),
    ("autoLowTempF", 32),
    ("autoHighTempC", 90),
    ("autoLowTempC", 0),
    ("autoHighHumi", 100),
    ("autoLowHumi", 0),
    ("targetTempF", 32),
    ("targetHumi", 0),
    ("targetVpd", 0),
    ("highVpd", 99),
    ("lowVpd", 0),
    ("settingMode", None),
)


_FAHRENHEIT_TYPES = frozenset(
    {
        SensorType.PROBE_TEMPERATURE_F,
        SensorType.CONTROLLER_TEMPERATURE_F,
        SensorType.HYDRO_WATER_TEMPERATURE_F,
    }
)
# (low rail, high rail) per unit: a threshold parked at its rail is "not set".
_THRESHOLD_RAILS: dict[str, tuple[float, float]] = {
    "°C": (0, 90),
    "%": (0, 100),
    "kPa": (0, 9.9),
    "ppm": (0, 9999),
    "pH": (0, 14),
}


# sensorModeData record = 11 bytes, decoded by the app's `extractSensorData` (aw4.java, app 2.0.8):
#   [0] sensorType
#   [1] flag bits: 1 highSwitch, 2 lowSwitch, 4 targetSwitch, 8 transSwitch, 16 bufferSwitch,
#       32 autoOrTarget (1 = target mode, 0 = trigger mode)
#   [2] precision codes: bits 2-3 for the int16 values, bits 0-1 for trans/buffer
#   [3] transValue, [4] bufferValue (uint8)
#   [5:7] targetValue, [7:9] highValue, [9:11] lowValue (int16 big-endian)
# Values are scaled x10 for VPD/pH (sensorType 3, 7, 13) after applying the precision.
_SMD_FLAG_HIGH = 1
_SMD_FLAG_LOW = 2
_SMD_FLAG_TARGET_SWITCH = 4
_SMD_FLAG_TRANS = 8
_SMD_FLAG_BUFFER = 16
_SMD_FLAG_TARGET_MODE = 32


def _threshold_value(value: float, unit: str, *, high: bool) -> float | None:
    low_rail, high_rail = _THRESHOLD_RAILS.get(unit, (None, None))
    return None if value == (high_rail if high else low_rail) else value


def _smd_scaled(raw: int, precision_code: int) -> float:
    """`Sensor.getActualValueFloat`: code 0 -> x10, 2 -> /10, 3 -> /100, else as is."""
    if raw == -32768:
        return float(raw)
    return {0: raw * 10.0, 2: raw / 10.0, 3: raw / 100.0}.get(precision_code, float(raw))


def _decode_threshold(record: list[int]) -> AutomationThreshold | None:
    if len(record) < _SENSOR_MODE_RECORD_LEN or record[0] not in _SENSOR_META:
        return None
    kind, unit, location = _SENSOR_META[record[0]]
    flags = record[1]
    value_code, tb_code = (record[2] >> 2) & 3, record[2] & 3
    multiply = (
        10
        if record[0] in (SensorType.PROBE_VPD, SensorType.CONTROLLER_VPD, SensorType.HYDRO_PH)
        else 1
    )
    target, high, low = (
        _smd_scaled(int.from_bytes(bytes(record[i : i + 2]), "big", signed=True), value_code)
        * multiply
        for i in (5, 7, 9)
    )
    transition, buffer = (_smd_scaled(record[i], tb_code) * multiply for i in (3, 4))
    if kind in ("vpd", "hydro_ph"):
        target, high, low, transition, buffer = (
            v / 10 for v in (target, high, low, transition, buffer)
        )
    elif record[0] in _FAHRENHEIT_TYPES:
        target, high, low = (round((v - 32) * 5 / 9, 1) for v in (target, high, low))
        transition, buffer = (round(v * 5 / 9, 1) for v in (transition, buffer))
    target_mode = bool(flags & _SMD_FLAG_TARGET_MODE)
    has_high = bool(flags & _SMD_FLAG_HIGH) and not target_mode
    has_low = bool(flags & _SMD_FLAG_LOW) and not target_mode
    control = "target" if target_mode else ("triggers" if has_high or has_low else "none")
    return AutomationThreshold(
        sensor_kind=kind,
        sensor_location=location,
        unit=unit,
        control=control,
        target=target if target_mode else None,
        high=_threshold_value(high, unit, high=True) if has_high else None,
        low=_threshold_value(low, unit, high=False) if has_low else None,
        buffer=buffer if flags & _SMD_FLAG_BUFFER else None,
        transition=transition if flags & _SMD_FLAG_TRANS else None,
        raw=list(record),
    )


def _decode_sensor_mode_data(raw: Any) -> list[AutomationThreshold]:
    if not raw:
        return []
    try:
        values = json.loads(raw) if isinstance(raw, str) else list(raw)
    except ValueError:
        return []
    records = [
        values[i : i + _SENSOR_MODE_RECORD_LEN]
        for i in range(0, len(values), _SENSOR_MODE_RECORD_LEN)
    ]
    # The API stores temperature twice (°F and °C record); merge them into one °C entry,
    # preferring the °C record's values and keeping both raw records for later decoding.
    merged: dict[tuple[str, str], AutomationThreshold] = {}
    for record in records:
        t = _decode_threshold(record)
        if t is None:
            continue
        key = (t.sensor_location, t.sensor_kind)
        if key in merged:
            existing = merged[key]
            if record[0] in _FAHRENHEIT_TYPES:
                existing.raw.extend(t.raw)
            else:
                t.raw = existing.raw + t.raw
                merged[key] = t
        else:
            merged[key] = t
    return list(merged.values())


def _schedule_summary(days: list[str], start: str | None, end: str | None) -> str:
    if not days or start is None or end is None:
        return "never (no days or window)"
    if len(days) == 7:
        day_part = "daily"
    elif days == list(_DAY_NAMES[:5]):
        day_part = "Mon-Fri"
    elif days == list(_DAY_NAMES[5:]):
        day_part = "Sat-Sun"
    else:
        day_part = ",".join(days)
    return f"{day_part} {start}-{end}"


def decode_automation_rule(raw: dict[str, Any], *, is_ai: bool) -> AutomationRule:
    table = _AUTOMATION_MODE_NEW_FRAMEWORK if is_ai else _AUTOMATION_MODE_LEGACY
    mode_id = raw.get("currentMode")
    mode = table.get(mode_id, f"Unknown ({mode_id})")
    days, continuous = _days_from_switch_time(raw.get("switchTime"))
    start, end = _minutes_to_hhmm(raw.get("beginTime")), _minutes_to_hhmm(raw.get("endTime"))
    legacy = {
        key: raw.get(key) for key, rail in _LEGACY_TRIGGER_KEYS if raw.get(key) not in (None, rail)
    }
    return AutomationRule(
        rule_id=raw.get("advId") or 0,
        program=raw.get("advName") or "",
        enabled=raw.get("isOn") == 1,
        running=raw.get("runState") == 1,
        ports=_ports_from_mask(raw.get("grouptDevType")),
        mode=mode,
        on_power=raw.get("onSpeed") or 0,
        off_power=raw.get("offSpeed") or 0,
        continuous=continuous,
        # With the 24/7 switch on, the app ignores the stored window entirely — hide it so
        # nobody reports "runs 09:00-17:00" for a rule that runs all day.
        schedule="24/7" if continuous else _schedule_summary(days, start, end),
        window_start=None if continuous else start,
        window_end=None if continuous else end,
        days=[] if continuous else days,
        stored_window=_schedule_summary(days, start, end) if continuous else None,
        cycle_on_minutes=(raw.get("cycleOn") or 0) // 60 if mode == "Cycle" else None,
        cycle_off_minutes=(raw.get("cycleOff") or 0) // 60 if mode == "Cycle" else None,
        min_on_minutes=raw.get("onMinTime") if raw.get("isOnMinMaxTime") == 1 else None,
        thresholds=_decode_sensor_mode_data(raw.get("sensorModeData")) if is_ai else [],
        legacy_triggers=legacy,
    )


def decode_automations(
    controller_id: str, raw: list[dict[str, Any]], *, is_ai: bool
) -> AutomationList:
    rules = [decode_automation_rule(r, is_ai=is_ai) for r in raw]
    return AutomationList(
        controller_id=controller_id,
        programs=list(dict.fromkeys(r.program for r in rules)),
        rules=rules,
    )


# ------------------------------------------------------------------------- History & logs


class HistoryPoint(BaseModel):
    time: int = Field(description="Unix timestamp (seconds) of the sample.")
    tent: Climate | None = Field(default=None, description="Probe climate (inside the tent).")
    ambient: Climate | None = Field(
        default=None, description="Onboard-sensor climate (controller housing); AI controllers."
    )
    port_power: dict[int, int] = Field(
        default_factory=dict, description="Applied power level 0-10 per port (from portSpead)."
    )
    automation_ports: list[int] = Field(
        default_factory=list, description="Ports whose automation was triggering (portStatus bits)."
    )
    samples: int = Field(default=1, description="Raw 1-minute rows aggregated into this point.")


class HistorySeries(BaseModel):
    controller_id: str
    start: int
    end: int
    sample_minutes: int
    raw_rows: int = Field(description="1-minute rows fetched from the API before aggregation.")
    points: list[HistoryPoint]
    summary: dict[str, dict[str, float]] = Field(
        description="min/avg/max per series (tent_temperature_c, tent_humidity_pct, ...)."
    )


def _decode_history_row(row: dict[str, Any], port_count: int) -> HistoryPoint:
    sensors = [s for s in (_decode_sensor(x) for x in row.get("sensors") or []) if s]
    if sensors:
        tent = _climate_from_sensors(sensors, LOCATION_PROBE)
        ambient = _climate_from_sensors(sensors, LOCATION_ONBOARD)
    else:
        tent = Climate(
            temperature_c=_hundredths(row.get("temperature")),
            humidity_pct=_hundredths(row.get("humidity")),
            vpd_kpa=_hundredths(row.get("vpdNums", row.get("vpdnums"))),
        )
        ambient = None
    speads = int(row.get("portSpead") or 0)
    status = int(row.get("portStatus") or 0)
    return HistoryPoint(
        time=int(row["createTime"]),
        tent=tent,
        ambient=ambient,
        port_power={p: (speads >> (4 * (p - 1))) & 0xF for p in range(1, port_count + 1)},
        automation_ports=[p for p in range(1, port_count + 1) if status & (1 << (p - 1))],
    )


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _aggregate(points: list[HistoryPoint]) -> HistoryPoint:
    def clim(attr: str) -> Climate | None:
        cs = [getattr(p, attr) for p in points if getattr(p, attr) is not None]
        if not cs:
            return None
        return Climate(
            temperature_c=_mean([c.temperature_c for c in cs if c.temperature_c is not None]),
            humidity_pct=_mean([c.humidity_pct for c in cs if c.humidity_pct is not None]),
            vpd_kpa=_mean([c.vpd_kpa for c in cs if c.vpd_kpa is not None]),
        )

    ports = sorted({p for pt in points for p in pt.port_power})
    return HistoryPoint(
        time=points[0].time,
        tent=clim("tent"),
        ambient=clim("ambient"),
        port_power={
            p: round(_mean([pt.port_power.get(p, 0) for pt in points]) or 0) for p in ports
        },
        automation_ports=sorted({p for pt in points for p in pt.automation_ports}),
        samples=len(points),
    )


def decode_history(
    controller_id: str,
    rows: list[dict[str, Any]],
    *,
    port_count: int,
    start: int,
    end: int,
    sample_minutes: int,
) -> HistorySeries:
    raw = sorted((_decode_history_row(r, port_count) for r in rows), key=lambda p: p.time)
    bucket = max(sample_minutes, 1) * 60
    groups: dict[int, list[HistoryPoint]] = {}
    for p in raw:
        groups.setdefault(p.time - (p.time % bucket), []).append(p)
    points = [_aggregate(g) if len(g) > 1 else g[0] for _, g in sorted(groups.items())]
    for pt, key in zip(points, sorted(groups), strict=True):
        pt.time = key
    summary: dict[str, dict[str, float]] = {}
    for scope in ("tent", "ambient"):
        for attr in ("temperature_c", "humidity_pct", "vpd_kpa"):
            values = [
                getattr(getattr(p, scope), attr)
                for p in raw
                if getattr(p, scope) is not None and getattr(getattr(p, scope), attr) is not None
            ]
            if values:
                summary[f"{scope}_{attr}"] = {
                    "min": min(values),
                    "avg": _mean(values) or 0,
                    "max": max(values),
                }
    return HistorySeries(
        controller_id=controller_id,
        start=start,
        end=end,
        sample_minutes=sample_minutes,
        raw_rows=len(rows),
        points=points,
        summary=summary,
    )


# Event log (logdataByAll). Decoding follows the app's Log builders (protocol/a.java,
# NetLog.toLog04): logType 2 = alert, 3 = AI, 4 = mode/automation info, 5 = controller info.
_AI_REASONS = {
    1: "raise_temperature",
    2: "lower_temperature",
    3: "raise_humidity",
    4: "lower_humidity",
    5: "raise_vpd",
    6: "lower_vpd",
    7: "co2",
    8: "efficiency",
    9: "raise_temp_and_humidity",
    10: "lower_temp_and_humidity",
    11: "raise_temp_lower_humidity",
    12: "lower_temp_raise_humidity",
}
_AI_MODE_EVENTS = {
    0: "ai_paused",
    1: "ai_started",
    2: "ai_resumed",
    3: "ai_deleted",
    4: "tentwork_activated",
    5: "tentwork_ended",
    6: "unfavorable_environment",
    7: "extreme_conditions",
    8: "unfavorable_environment",
    9: "extreme_conditions",
    10: "unfavorable_humidity",
    11: "clip_fan_setting_changed",
    16: "night_mode_enabled",
    17: "night_mode_disabled",
}
_AI_USER_ACTIONS = {
    1: "target_range_updated",
    2: "schedule_updated",
    3: "light_schedule_updated",
    4: "port_device_type_changed",
    5: "port_added_or_removed",
    6: "sensor_connection_changed",
    7: "dynamic_light_schedule",
}
_CONTROLLER_INFO = {
    0: "co2_over_5000ppm_devices_paused",
    1: "power_protection_shut_off_outlet",
    2: "low_water_detected",
    3: "builtin_clip_fan_lost",
    4: "builtin_fan_lost",
    5: "builtin_grow_light_lost",
    6: "builtin_sensor_lost",
    7: "carbon_filter_alert",
}


class LogEvent(BaseModel):
    time: int = Field(description="Unix timestamp (seconds).")
    log_id: str
    category: str = Field(
        description="ai_control | ai_user_action | ai_mode | alert | mode_info | controller_info"
    )
    event: str = Field(description="Machine-readable event name (see docs/api/history.md).")
    port: int | None = None
    level: int | None = Field(default=None, description="Power level the AI set (ai_control).")
    trend: str | None = Field(default=None, description="'increase' / 'decrease' for ai_control.")
    reason: str | None = None
    details: dict[str, Any] = Field(
        default_factory=dict, description="Remaining non-zero API fields for this entry."
    )


def decode_log_event(raw: dict[str, Any]) -> LogEvent:
    log_type, business = raw.get("logType"), raw.get("businessType")
    port = raw.get("portSelection") or None
    level = trend = reason = None
    if log_type == 3 and business == 1:
        category, event = "ai_control", "ai_set_port"
        level = raw.get("mlVariation")
        trend = {1: "decrease", 2: "increase"}.get(raw.get("mlVariationTrend"))
        reason = _AI_REASONS.get(raw.get("pauseReason"))
    elif log_type == 3 and business == 2:
        category = "ai_user_action"
        event = _AI_USER_ACTIONS.get(
            raw.get("mlVariationType"), f"user_action_{raw.get('mlVariationType')}"
        )
    elif log_type == 3 and business == 3:
        category = "ai_mode"
        event = _AI_MODE_EVENTS.get(
            raw.get("mlVariationType"), f"ai_mode_{raw.get('mlVariationType')}"
        )
    elif log_type == 2:
        category, event = "alert", f"alert_business_{business}"
    elif log_type == 4:
        category, event = "mode_info", f"mode_{raw.get('currentMode')}_business_{business}"
    elif log_type == 5:
        category, event = (
            "controller_info",
            _CONTROLLER_INFO.get(business, f"controller_{business}"),
        )
    else:
        category, event = "unknown", f"type_{log_type}_business_{business}"
    skip = {
        "appId",
        "devId",
        "devMacAddr",
        "logId",
        "id",
        "logTime",
        "logType",
        "logFormat",
        "businessType",
        "portSelection",
        "mlVariation",
        "mlVariationTrend",
        "pauseReason",
        "mlVariationType",
    }
    details = {k: v for k, v in raw.items() if k not in skip and v not in (None, 0, "", False)}
    return LogEvent(
        time=int(raw.get("logTime") or 0),
        log_id=str(raw.get("logId") or raw.get("id")),
        category=category,
        event=event,
        port=port,
        level=level,
        trend=trend,
        reason=reason,
        details=details,
    )


class LogEvents(BaseModel):
    controller_id: str
    start: int
    end: int
    events: list[LogEvent]
    truncated: bool = Field(description="True when more events exist than `limit` allowed.")
