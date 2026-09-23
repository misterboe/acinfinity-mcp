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
