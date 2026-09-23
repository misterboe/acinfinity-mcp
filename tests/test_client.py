import pytest

from acinfinity_mcp.client import (
    CONTROL_KEYS,
    PATH_ADD_DEV_MODE,
    PATH_DEVICE_LIST,
    PATH_LOGIN,
    PATH_MODE_AND_SETTING,
    PATH_UPDATE_ADV_SETTING,
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


async def test_standard_write_is_full_object_in_query_string(client, api):
    await client.update_port_controls(STD_ID, 1, {"atType": 2, "onSpead": 7})
    (query,) = api.writes(PATH_ADD_DEV_MODE)
    assert query["atType"] == "2" and query["onSpead"] == "7"
    assert set(CONTROL_KEYS) <= set(query)  # every key sent, even ones the API omitted
    assert query["restore"] == "false"  # bool → "false"
    assert query["insideTemp"] == "0"  # missing → 0
    assert "devSetting" not in query


async def test_standard_settings_write_keeps_device_name(client, api):
    await client.update_device_settings(STD_ID, 1, "Lüftung", {"loadType": 6})
    (query,) = api.writes(PATH_UPDATE_ADV_SETTING)
    assert query["devName"] == "Lüftung" and query["loadType"] == "6"


async def test_ai_write_uses_put_mode_and_setting(client, api):
    await client.update_port_controls(AI_ID, 1, {"atType": 8})
    assert api.writes(PATH_ADD_DEV_MODE) == []
    (query,) = api.writes(PATH_MODE_AND_SETTING)
    assert query["atType"] == "8"
    assert query["modeAndSettingIdStr"] == "[16,81,32,98,99]"
    assert "devCompany" in query  # flattened devSetting key


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
