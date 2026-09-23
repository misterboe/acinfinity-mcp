from acinfinity_mcp.models import (
    Mode,
    decode_controller,
    decode_port_settings,
    hhmm_to_minutes,
)
from tests.conftest import AI_ID, STD_ID, load


def test_decode_standard_controller_offline_readings_are_none():
    std = next(c for c in load("devInfoListAll") if c["devId"] == STD_ID)
    ctl = decode_controller(std)
    assert ctl.id == STD_ID and not ctl.is_ai and ctl.model.startswith("UIS Controller 69 Pro")
    assert ctl.online is False
    assert ctl.tent is None and ctl.ambient is None
    assert [p.port for p in ctl.ports] == [1, 2, 3, 4]
    assert ctl.ports[0].mode == Mode.VPD


def test_port_is_on_follows_applied_power_under_automation():
    ai = next(c for c in load("devInfoListAll") if c["devId"] == AI_ID)
    ports = {p.port: p for p in decode_controller(ai).ports}
    # AI+ ports driven by an Advance Automation report loadState 0 but speak > 0
    assert ports[1].power == 2 and ports[1].is_on is True
    assert ports[5].power == 0 and ports[5].is_on is False


def test_decode_ai_controller_sensors():
    ai = next(c for c in load("devInfoListAll") if c["devId"] == AI_ID)
    ctl = decode_controller(ai)
    assert ctl.is_ai and ctl.port_count == 8 and len(ctl.ports) == 8
    # tent = external probe (inside), ambient = onboard sensor (controller housing, outside)
    assert (ctl.tent.temperature_c, ctl.tent.humidity_pct, ctl.tent.vpd_kpa) == (26.6, 58.0, 1.46)
    assert (ctl.ambient.temperature_c, ctl.ambient.humidity_pct, ctl.ambient.vpd_kpa) == (
        21.9,
        60.2,
        1.04,
    )
    by_loc = {(s.location, s.kind): s for s in ctl.sensors}
    assert by_loc[("probe", "temperature")].sensor_port == 1
    assert by_loc[("onboard", "temperature")].sensor_port == 2


def test_decode_sensor_fahrenheit_is_converted():
    raw = {
        "devId": "1",
        "devType": 20,
        "deviceInfo": {
            "ports": [],
            "sensors": [
                {
                    "sensorType": 0,
                    "sensorUnit": 0,
                    "sensorPrecision": 3,
                    "accessPort": 1,
                    "sensorData": 7610,
                }
            ],
        },
    }
    ctl = decode_controller(raw)
    assert ctl.sensors[0].value == 24.5 and ctl.sensors[0].unit == "°C"
    assert ctl.tent.temperature_c == 24.5 and ctl.ambient is None


def test_decode_port_settings_units():
    s = decode_port_settings(STD_ID, 1, load("modeSettings_std_port1"))
    assert s.mode == Mode.VPD
    assert s.on_power == 5 and s.off_power == 0
    assert s.temp_high_c.enabled and s.temp_high_c.value == 29.0
    assert s.vpd_low_kpa.enabled and s.vpd_low_kpa.value == 1.3
    assert s.cycle_on_minutes == 2 and s.cycle_off_minutes == 60
    assert s.schedule_start is None and s.schedule_end is None


def test_hhmm_roundtrip():
    assert hhmm_to_minutes("00:00") == 0
    assert hhmm_to_minutes("23:59") == 1439
    assert hhmm_to_minutes(None) == 65535


def test_decode_ai_automations():
    from acinfinity_mcp.models import decode_automations

    result = decode_automations(AI_ID, load("getGroups_ai"), is_ai=True)
    assert result.programs == ["Automatisierung 1"]
    assert [(r.ports, r.mode, r.on_power) for r in result.rules] == [
        ([1], "Auto", 4),
        ([2], "On", 6),
        ([3], "VPD", 5),
    ]
    rule = result.rules[0]
    assert rule.enabled and rule.running
    # switchTime 255 = 24/7 switch on -> the stored 09:00-17:00 window is ignored
    assert rule.continuous and rule.schedule == "24/7"
    assert rule.window_start is None and rule.window_end is None and rule.days == []
    assert rule.min_on_minutes == 5
    # °F and °C records merged into one °C entry; rails (0 °C / 0-100 %) become null
    by_kind = {t.sensor_kind: t for t in rule.thresholds}
    assert set(by_kind) == {"temperature", "humidity"}
    assert (
        by_kind["temperature"].unit,
        by_kind["temperature"].low,
        by_kind["temperature"].high,
    ) == ("°C", None, 25.0)
    assert len(by_kind["temperature"].raw) == 22
    assert (by_kind["humidity"].low, by_kind["humidity"].high) == (None, None)
    vpd = result.rules[2].thresholds[0]
    assert (vpd.sensor_kind, vpd.low, vpd.high) == ("vpd", 1.5, None)


def test_legacy_automation_mode_table_is_inverted():
    from acinfinity_mcp.models import decode_automation_rule

    raw = {"advId": 1, "advName": "x", "currentMode": 2, "grouptDevType": 8, "switchTime": 31}
    raw.update({"beginTime": 540, "endTime": 1020})
    legacy = decode_automation_rule(raw, is_ai=False)
    ai = decode_automation_rule(raw, is_ai=True)
    assert (legacy.mode, ai.mode) == ("Off", "On")
    assert legacy.ports == [4] and legacy.days == ["Mon", "Tue", "Wed", "Thu", "Fri"]
    assert legacy.continuous is False and legacy.schedule == "Mon-Fri 09:00-17:00"
