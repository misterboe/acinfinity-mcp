"""Shared fixtures: a fake AC Infinity API served through httpx2.MockTransport.

Fixture payloads are anonymised captures of real responses (2026-09-23), see tests/fixtures/.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import httpx2
import pytest

from acinfinity_mcp.client import (
    PATH_ADD_DEV_MODE,
    PATH_DEV_SETTING,
    PATH_DEVICE_LIST,
    PATH_LOGIN,
    PATH_MODE_AND_SETTING,
    PATH_MODE_SETTINGS,
    PATH_UPDATE_ADV_SETTING,
    PATH_V2_ALARMS,
    PATH_V2_GROUPS,
    AcInfinityClient,
)

FIXTURES = Path(__file__).parent / "fixtures"
STD_ID = "54929097239553773072"
AI_ID = "87210463819275016439"
TOKEN = "11763238626156107487"


def load(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def envelope(data: Any, code: int = 200) -> httpx2.Response:
    return httpx2.Response(
        200, json={"msg": "Success" if code == 200 else "Fail", "code": code, "data": data}
    )


@dataclass
class FakeApi:
    """Records every request; `calls` is a list of (method, path, form-dict, query-dict)."""

    calls: list[tuple[str, str, dict[str, str], dict[str, str]]] = field(default_factory=list)
    fail_login: bool = False
    flaky_once: bool = False

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        query = {k: v[0] for k, v in parse_qs(request.url.query.decode()).items()}
        self.calls.append((request.method, path, form, query))

        if path == PATH_LOGIN:
            if self.fail_login:
                return envelope(None, code=10000)
            return envelope({"appId": TOKEN, "appEmail": form["appEmail"]})

        assert request.headers.get("token") == TOKEN, "authenticated call without token"
        assert request.headers.get("User-Agent") == "okhttp/4.12.0"

        if self.flaky_once:
            self.flaky_once = False
            return httpx2.Response(502, text="bad gateway")

        if path == PATH_DEVICE_LIST:
            return envelope(load("devInfoListAll"))
        if path == PATH_MODE_SETTINGS:
            tag = "ai" if form["devId"] == AI_ID else "std"
            port = "0" if form["port"] == "0" else "1"
            return envelope(load(f"modeSettings_{tag}_port{port}"))
        if path == PATH_DEV_SETTING:
            return envelope(load("devSetting_std_port1"))
        if path == PATH_V2_GROUPS:
            assert "version" not in request.headers and "requestId" not in request.headers
            return envelope(load("getGroups_ai") if form["devId"] == AI_ID else [])
        if path == PATH_V2_ALARMS:
            return envelope([])
        if path in (PATH_ADD_DEV_MODE, PATH_UPDATE_ADV_SETTING):
            assert not query and form, "writes must carry the payload as form body"
            if form["devId"] == AI_ID and request.headers.get("minversion") != "3.5":
                return envelope(None, code=100001)  # what the live API does (ober37 Quirk 14)
            return envelope(None)
        if path == PATH_MODE_AND_SETTING:
            assert request.method == "PUT"
            assert request.headers.get("minversion") == "3.5"
            return envelope(None)
        return httpx2.Response(404)

    def writes(self, path: str) -> list[dict[str, str]]:
        """Payloads of write calls to `path` (form body, or query string for the PUT)."""
        return [f or q for _, p, f, q in self.calls if p == path]


@pytest.fixture
def api() -> FakeApi:
    return FakeApi()


@pytest.fixture
async def client(api: FakeApi):
    c = AcInfinityClient("me@example.com", "x" * 40, transport=httpx2.MockTransport(api.handler))
    yield c
    await c.aclose()
