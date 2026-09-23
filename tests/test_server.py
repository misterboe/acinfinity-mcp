"""Protocol-level tests: tools called through an in-memory MCP client session."""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import httpx2
import pytest
from mcp.client import Client

from acinfinity_mcp import server
from acinfinity_mcp.client import PATH_ADD_DEV_MODE, AcInfinityClient
from tests.conftest import AI_ID, STD_ID, FakeApi

Connect = Callable[[], AbstractAsyncContextManager[Client]]


@pytest.fixture
def connect(api: FakeApi, monkeypatch) -> Connect:
    """Factory: `async with connect() as c` inside the test keeps enter/exit in one task
    (anyio cancel scopes refuse to be closed from a different task than they were opened in)."""
    monkeypatch.setenv(server.ENV_EMAIL, "me@example.com")
    monkeypatch.setenv(server.ENV_PASSWORD, "secret")
    monkeypatch.setattr("acinfinity_mcp.client.LOG_CALL_SPACING", 0)
    monkeypatch.setattr("acinfinity_mcp.client.WRITE_SPACING", 0)
    fake = AcInfinityClient("me@example.com", "secret", transport=httpx2.MockTransport(api.handler))
    monkeypatch.setattr(server, "AcInfinityClient", lambda *a, **k: fake)

    @asynccontextmanager
    async def _connect() -> AsyncIterator[Client]:
        async with Client(server.mcp) as c:
            yield c

    return _connect


async def test_tools_are_listed_with_annotations(connect: Connect):
    async with connect() as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
    assert tools["list_controllers"].annotations.read_only_hint is True
    assert tools["set_port_mode"].annotations.read_only_hint is False
    assert tools["set_port_mode"].annotations.destructive_hint is False
    assert "user_authorized" in tools["set_port_mode"].input_schema["properties"]
    assert tools["list_controllers"].output_schema is not None


async def test_list_controllers_returns_structured_content(connect: Connect):
    async with connect() as c:
        result = await c.call_tool("list_controllers", {})
    assert result.is_error is False
    controllers = result.structured_content["controllers"]
    assert {x["id"] for x in controllers} == {STD_ID, AI_ID}
    assert controllers[1]["tent"]["temperature_c"] == 26.6
    assert controllers[1]["ambient"]["temperature_c"] == 21.9


async def test_get_port_settings(connect: Connect):
    async with connect() as c:
        result = await c.call_tool("get_port_settings", {"controller_id": STD_ID, "port": 1})
    assert result.structured_content["mode"] == 8
    assert result.structured_content["vpd_low_kpa"] == {"enabled": True, "value": 1.3}


async def test_write_without_authorization_is_tool_error(connect: Connect, api: FakeApi):
    async with connect() as c:
        result = await c.call_tool("set_port_mode", {"controller_id": STD_ID, "port": 1, "mode": 2})
    assert result.is_error is True
    assert "user_authorized=true" in result.content[0].text
    assert api.writes(PATH_ADD_DEV_MODE) == []


async def test_authorized_write_hits_api(connect: Connect, api: FakeApi):
    async with connect() as c:
        result = await c.call_tool(
            "set_port_power",
            {"controller_id": STD_ID, "port": 1, "on_power": 7, "user_authorized": True},
        )
    assert result.is_error is False
    assert result.structured_content["changed"] == {"onSpead": 7, "onSelfSpead": 7}
    (query,) = api.writes(PATH_ADD_DEV_MODE)
    assert query["onSpead"] == "7"


async def test_out_of_range_input_is_rejected_before_execution(connect: Connect, api: FakeApi):
    async with connect() as c:
        result = await c.call_tool(
            "set_port_power",
            {"controller_id": STD_ID, "port": 1, "on_power": 11, "user_authorized": True},
        )
    assert result.is_error is True
    assert api.writes(PATH_ADD_DEV_MODE) == []


async def test_port_beyond_controller_is_helpful_tool_error(connect: Connect):
    async with connect() as c:
        result = await c.call_tool("get_port_settings", {"controller_id": STD_ID, "port": 7})
    assert result.is_error is True
    assert "has ports 1-4" in result.content[0].text


async def test_mode_name_is_exposed(connect: Connect):
    async with connect() as c:
        result = await c.call_tool("list_controllers", {})
    port = result.structured_content["controllers"][0]["ports"][0]
    assert (port["mode"], port["mode_name"]) == (8, "VPD")


async def test_list_automations(connect: Connect):
    async with connect() as c:
        result = await c.call_tool("list_automations", {"controller_id": AI_ID})
    assert result.is_error is False
    rules = result.structured_content["rules"]
    assert [r["mode"] for r in rules] == ["Auto", "On", "VPD"]
    assert rules[2]["thresholds"][0]["sensor_kind"] == "vpd"


async def test_backup_compare_restore_roundtrip(
    connect: Connect, api: FakeApi, tmp_path, monkeypatch
):
    from acinfinity_mcp.client import PATH_ADD_DEV_MODE, PATH_V2_UPDATE_GROUP

    monkeypatch.setenv("ACINFINITY_BACKUP_DIR", str(tmp_path))
    async with connect() as c:
        info = (
            await c.call_tool("backup_settings", {"controller_id": AI_ID, "label": "t"})
        ).structured_content
        assert info["ports"] == 8 and info["automation_rules"] == 3
        listed = (await c.call_tool("list_backups", {})).structured_content
        assert [b["backup_id"] for b in listed["backups"]] == [info["backup_id"]]
        cmp = (
            await c.call_tool("compare_backup", {"backup_id": info["backup_id"]})
        ).structured_content
        assert cmp["changes"] == [] and cmp["missing_rules"] == []
        # nothing differs -> restore writes nothing
        res = (
            await c.call_tool(
                "restore_settings", {"backup_id": info["backup_id"], "user_authorized": True}
            )
        ).structured_content
        assert res["ports_restored"] == [] and res["rules_restored"] == []
        assert api.writes(PATH_ADD_DEV_MODE) == [] and api.writes(PATH_V2_UPDATE_GROUP) == []
        # forced full restore writes every port (not port 0) and every rule
        res = (
            await c.call_tool(
                "restore_settings",
                {"backup_id": info["backup_id"], "only_changed": False, "user_authorized": True},
            )
        ).structured_content
        assert res["ports_restored"] == list(range(1, 9)) and res["rules_restored"] == [
            2596136,
            2596144,
            2596148,
        ]
        assert "controller record" in res["skipped"][0]
        assert (
            len(api.writes(PATH_ADD_DEV_MODE)) == 8 and len(api.writes(PATH_V2_UPDATE_GROUP)) == 3
        )
        assert res["remaining_changes"] == []


async def test_rename_port_tool(connect: Connect, api: FakeApi):
    from acinfinity_mcp.client import PATH_MODE_AND_SETTING

    async with connect() as c:
        result = await c.call_tool(
            "rename_port",
            {"controller_id": AI_ID, "port": 5, "name": "undercanopy", "user_authorized": True},
        )
    assert result.is_error is False
    (query,) = api.writes(PATH_MODE_AND_SETTING)
    assert query["devName"] == "undercanopy"


async def test_get_history_aggregates_and_summarises(connect: Connect):
    async with connect() as c:
        result = await c.call_tool(
            "get_history", {"controller_id": AI_ID, "hours": 1, "sample_minutes": 10}
        )
    assert result.is_error is False
    data = result.structured_content
    assert data["raw_rows"] == 5 and 1 <= len(data["points"]) <= 2
    point = data["points"][0]
    assert point["tent"]["temperature_c"] and point["ambient"]["temperature_c"]
    assert point["port_power"]["1"] == 3 and point["port_power"]["2"] == 6  # portSpead 0x63 nibbles
    assert "tent_temperature_c" in data["summary"] and data["summary"]["tent_vpd_kpa"]["max"] > 1


async def test_get_event_log_decodes_ai_actions(connect: Connect, api: FakeApi):
    async with connect() as c:
        result = await c.call_tool(
            "get_event_log", {"controller_id": AI_ID, "days": 7, "limit": 25}
        )
    data = result.structured_content
    assert len(data["events"]) == 25 and data["truncated"] is True
    kinds = {e["category"] for e in data["events"]}
    assert "ai_control" in kinds
    ctrl = next(e for e in data["events"] if e["category"] == "ai_control")
    assert ctrl["port"] and ctrl["reason"] in {
        "lower_vpd",
        "raise_vpd",
        "efficiency",
        "lower_temperature",
        "raise_temperature",
        None,
    }
    from acinfinity_mcp.client import PATH_EVENT_LOG

    assert len(api.writes(PATH_EVENT_LOG)) == 1  # limit 25 -> single page
