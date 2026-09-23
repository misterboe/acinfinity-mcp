import pytest

from acinfinity_mcp.client import (
    CONTROL_KEYS,
    PATH_ADD_DEV_MODE,
    PATH_DEVICE_LIST,
    PATH_LOGIN,
    PATH_MODE_AND_SETTING,
    PATH_UPDATE_ADV_SETTING,
    PATH_V2_TOGGLE_GROUP,
    AuthError,
)
from tests.conftest import AI_ID, STD_ID


async def test_login_truncates_password_and_sets_token(client, api):
    await client.login()
    method, path, form, _ = api.calls[0]
    assert (method, path) == ("POST", PATH_LOGIN)
    assert form["appEmail"] == "me@example.com"
    assert form["appPasswordl"] == "x" * 25


async def test_login_failure_raises_auth_error(client, api):
    api.fail_login = True
    with pytest.raises(AuthError):
        await client.login()


async def test_list_controllers_logs_in_lazily_and_caches(client, api):
    devices = await client.list_controllers()
    assert [d["devId"] for d in devices] == [STD_ID, AI_ID]
    assert [p for _, p, _, _ in api.calls] == [PATH_LOGIN, PATH_DEVICE_LIST]
    await client.list_controllers()
    assert len(api.calls) == 2  # served from cache


async def test_transient_http_error_is_retried(client, api, monkeypatch):
    monkeypatch.setattr("acinfinity_mcp.client.asyncio.sleep", _no_sleep)
    api.flaky_once = True
    devices = await client.list_controllers()
    assert len(devices) == 2
    assert [p for _, p, _, _ in api.calls].count(PATH_DEVICE_LIST) == 2


async def test_standard_write_is_full_object_form_body(client, api):
    await client.update_port_controls(STD_ID, 1, {"atType": 2, "onSpead": 7})
    (form,) = api.writes(PATH_ADD_DEV_MODE)
    assert form["atType"] == "2" and form["onSpead"] == "7"
    assert set(CONTROL_KEYS) <= set(form)  # every key sent, even ones the API omitted
    assert form["restore"] == "false"  # bool → "false"
    assert form["insideTemp"] == "0"  # missing → 0
    assert "devSetting" not in form
    method, _, _, _ = next(c for c in api.calls if c[1] == PATH_ADD_DEV_MODE)
    assert method == "POST"


async def test_standard_settings_write_keeps_device_name(client, api):
    await client.update_device_settings(STD_ID, 1, "Lüftung", {"loadType": 6})
    (query,) = api.writes(PATH_UPDATE_ADV_SETTING)
    assert query["devName"] == "Lüftung" and query["loadType"] == "6"


async def test_ai_control_write_uses_add_dev_mode_with_minversion(client, api):
    await client.update_port_controls(AI_ID, 1, {"atType": 4, "acitveTimerOn": 86400})
    (form,) = api.writes(PATH_ADD_DEV_MODE)
    assert form["atType"] == "4" and form["acitveTimerOn"] == "86400"
    assert api.writes(PATH_MODE_AND_SETTING) == []


async def test_ai_settings_write_follows_the_app_recipe(client, api):
    await client.update_device_settings(AI_ID, 1, "Abluft", {"loadType": 129})
    (query,) = api.writes(PATH_MODE_AND_SETTING)
    assert query["loadType"] == "129" and query["devName"] == "Abluft"
    assert query["modeAndSettingIdStr"] == "[16,17]"  # port is Off in the fixture
    assert "devCompany" in query and "atType" in query  # setting key + mode field
    assert "devSetting" not in query and "calibrationTime" not in query  # nested / non-app keys
    assert int(query["devHtf"]) >= 32  # °F twins are clamped like the app does


async def test_ai_rename_is_minimal_put_with_group_17(client, api):
    await client.rename_port(AI_ID, 1, "Exhaust")
    (query,) = api.writes(PATH_MODE_AND_SETTING)
    assert query["devName"] == "Exhaust" and query["atType"] == "1"
    assert query["modeAndSettingIdStr"] == "[16,17]" and query["offSpead"] == "0"
    assert "onSpead" not in query  # only the listed group's fields travel


async def test_standard_writes_are_signed(client, api):
    await client.update_port_controls(STD_ID, 1, {"atType": 2})
    headers = next(h for m, p, h in api.headers if p == PATH_ADD_DEV_MODE)
    assert headers["version"] == "2.0.8" and len(headers["sign"]) == 32
    assert headers["requestapp"] == "app-x" and "minversion" not in headers
    await client.update_port_controls(AI_ID, 1, {"atType": 2})
    ai_headers = [h for m, p, h in api.headers if p == PATH_ADD_DEV_MODE][-1]
    assert "sign" not in ai_headers and ai_headers["minversion"] == "3.5"


async def test_toggle_automation_only_when_state_differs(client, api):
    await client.set_automation_enabled(AI_ID, 2596136, True)  # already on in the fixture
    assert api.writes(PATH_V2_TOGGLE_GROUP) == []
    await client.set_automation_enabled(AI_ID, 2596136, False)
    (form,) = api.writes(PATH_V2_TOGGLE_GROUP)
    assert form == {"advId": "2596136", "isDel": "0", "isflag": "1"}


async def _no_sleep(_: float) -> None:
    return None


async def test_unknown_controller_id_is_rejected_before_write(client, api):
    from acinfinity_mcp.client import AcInfinityError

    with pytest.raises(AcInfinityError, match="unknown controller id"):
        await client.update_port_controls("999", 1, {"atType": 2})
    assert api.writes(PATH_ADD_DEV_MODE) == []


async def test_port_out_of_range_is_rejected_before_write(client, api):
    from acinfinity_mcp.client import AcInfinityError

    with pytest.raises(AcInfinityError, match="has ports 1-4"):
        await client.update_port_controls(STD_ID, 7, {"atType": 2})
    assert api.writes(PATH_ADD_DEV_MODE) == []


async def test_write_to_empty_port_is_refused(client, api):
    from acinfinity_mcp.client import AcInfinityError

    with pytest.raises(AcInfinityError, match="no device plugged in"):
        await client.rename_port(AI_ID, 8, "x")  # port 8: online 0, portResistance 65535
    with pytest.raises(AcInfinityError, match="no device plugged in"):
        await client.update_port_controls(AI_ID, 8, {"atType": 2})
    assert api.writes(PATH_MODE_AND_SETTING) == [] and api.writes(PATH_ADD_DEV_MODE) == []


async def test_rename_program_rewrites_each_rule_with_raw_fields(client, api, monkeypatch):
    from acinfinity_mcp.client import PATH_V2_UPDATE_GROUP

    monkeypatch.setattr("acinfinity_mcp.client.asyncio.sleep", _no_sleep)
    ids = await client.rename_program(AI_ID, "Automatisierung 1", "Flowering")
    assert ids == [2596136, 2596144, 2596148]
    forms = api.writes(PATH_V2_UPDATE_GROUP)
    assert [f["advName"] for f in forms] == ["Flowering"] * 3
    assert forms[0]["sensorModeData"].startswith("[0, 13, 5")  # raw string untouched
    assert "portState" not in forms[0] or forms[0]["portState"] != "None"  # nulls skipped
    assert forms[0]["isDel"] == "false"
