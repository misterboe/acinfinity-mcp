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
    is_on: bool = Field(description="The connected device is currently powered.")
    power: int = Field(ge=0, le=10, description="Current power level 0-10.")
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
    return Port(
        port=raw["port"],
        name=raw.get("portName") or f"Port {raw['port']}",
        online=raw.get("online") == 1,
        is_on=raw.get("loadState") == 1,
        power=raw.get("speak") or 0,
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
    """One `sensorModeData` record of a new-framework Auto/VPD rule (11 ints per sensor).

    Layout is partially reverse-engineered: [0]=sensorType, [6]=low value, [8]=high value.
    A value at its rail (temp 32 °F / 0 °C, humidity 0 or 100, VPD 0 or 9.9) means "not set".
    Everything else is exposed raw until confirmed.
    """

    sensor_kind: str
    sensor_location: str
    unit: str
    low: float | None = Field(description="Tentative: record position 6, sensor units.")
    high: float | None = Field(description="Tentative: record position 8, sensor units.")
    raw: list[int]


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
    window_start: str | None = Field(description="Daily start HH:MM (controller local time).")
    window_end: str | None
    days: list[str] = Field(description="Weekdays the window applies to.")
    continuous: bool = Field(description="switchTime bit 7: the app treats the rule as 24/7.")
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


def _decode_threshold(record: list[int]) -> AutomationThreshold | None:
    if len(record) < _SENSOR_MODE_RECORD_LEN or record[0] not in _SENSOR_META:
        return None
    kind, unit, location = _SENSOR_META[record[0]]
    scale = 10 if kind == "vpd" else 1
    return AutomationThreshold(
        sensor_kind=kind,
        sensor_location=location,
        unit="°F"
        if record[0] in (SensorType.PROBE_TEMPERATURE_F, SensorType.CONTROLLER_TEMPERATURE_F)
        else unit,
        low=record[6] / scale,
        high=record[8] / scale,
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
    return [t for t in (_decode_threshold(r) for r in records) if t]


def decode_automation_rule(raw: dict[str, Any], *, is_ai: bool) -> AutomationRule:
    table = _AUTOMATION_MODE_NEW_FRAMEWORK if is_ai else _AUTOMATION_MODE_LEGACY
    mode_id = raw.get("currentMode")
    mode = table.get(mode_id, f"Unknown ({mode_id})")
    days, continuous = _days_from_switch_time(raw.get("switchTime"))
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
        window_start=_minutes_to_hhmm(raw.get("beginTime")),
        window_end=_minutes_to_hhmm(raw.get("endTime")),
        days=days,
        continuous=continuous,
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
