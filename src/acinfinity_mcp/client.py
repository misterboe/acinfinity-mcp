"""Async client for the (unofficial) AC Infinity cloud API.

Endpoint shapes, quirks and write flows: docs/api/. This module knows nothing about MCP.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from urllib.parse import urlencode

import httpx2

from .models import AI_CONTROLLER_TYPES, Mode

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.acinfinityserver.com"
USER_AGENT = "okhttp/4.12.0"
PASSWORD_MAX_LEN = 25
REQUEST_TIMEOUT = 10.0
MAX_RETRIES = 3
DEVICE_LIST_TTL = 5.0

PATH_LOGIN = "/api/user/appUserLogin"
PATH_DEVICE_LIST = "/api/user/devInfoListAll"
PATH_MODE_SETTINGS = "/api/dev/getdevModeSettingList"
PATH_ADD_DEV_MODE = "/api/dev/addDevMode"
PATH_DEV_SETTING = "/api/dev/getDevSetting"
PATH_UPDATE_ADV_SETTING = "/api/dev/updateAdvSetting"
PATH_MODE_AND_SETTING = "/api/dev/modeAndSetting"
# "Advance Automation" programs and alarms live on the versioned v2 surface. The literal
# `version=2.0` path segment is real. Never send `version`/`requestId` headers here (403).
PATH_V2_GROUPS = "/api/version=2.0/dev/getGroups"
PATH_V2_ALARMS = "/api/version=2.0/dev/getAlarms"

# Keys that are sent back verbatim on writes. Kept here (not in models.py) because they are
# an API contract, not a data model. See docs/api/controls-and-settings.md.
CONTROL_KEYS: tuple[str, ...] = (
    "devId",
    "externalPort",
    "modeSetid",
    "modeType",
    "masterPort",
    "surplus",
    "onSpead",
    "offSpead",
    "onSelfSpead",
    "atType",
    "powerState",
    "power",
    "loadState",
    "loadType",
    "speak",
    "abnormalState",
    "toward",
    "schedStartTime",
    "schedEndtTime",
    "acitveTimerOn",
    "acitveTimerOff",
    "activeCycleOn",
    "activeCycleOff",
    "activeHtVpd",
    "activeHtVpdNums",
    "activeLtVpd",
    "activeLtVpdNums",
    "vpdstatus",
    "vpdnums",
    "vpdSettingMode",
    "targetVpd",
    "targetVpdSwitch",
    "isUpdateVpdNums",
    "devHt",
    "activeHt",
    "devLt",
    "activeLt",
    "temperature",
    "targetTemp",
    "targetTSwitch",
    "insideTemp",
    "outsideTemp",
    "devHtf",
    "devLtf",
    "temperatureF",
    "targetTempF",
    "devHh",
    "activeHh",
    "devLh",
    "activeLh",
    "humidity",
    "targetHumi",
    "targetHumiSwitch",
    "photocellSwitch",
    "trend",
    "tTrend",
    "hTrend",
    "insideTrend",
    "outsideTrend",
    "unit",
    "ecOrTds",
    "ecUnit",
    "tdsUnit",
    "ecTdsSettingMode",
    "ecTdsAccuracy",
    "ecTdsTargetSwitch",
    "ecTdsTargetValueEcUs",
    "ecTdsTargetValueEcMs",
    "ecTdsTargetValueTdsPpm",
    "ecTdsTargetValueTdsPpt",
    "ecTdsHighSwitch",
    "ecTdsHighValueEcUs",
    "ecTdsHighValueEcMs",
    "ecTdsHighValueTdsPpm",
    "ecTdsHighValueTdsPpt",
    "ecTdsLowSwitchEc",
    "ecTdsLowSwitchTds",
    "ecTdsLowValueEcUs",
    "ecTdsLowValueEcMs",
    "ecTdsLowValueTdsPpm",
    "ecTdsLowValueTdsPpt",
    "phSettingMode",
    "phAccuracy",
    "phTargetSwitch",
    "phTargetValue",
    "phHighSwitch",
    "phHighValue",
    "phLowSwitch",
    "phLowValue",
    "co2SettingMode",
    "co2Accuracy",
    "co2TargetSwitch",
    "co2TargetValue",
    "co2HighSwitch",
    "co2HighValue",
    "co2LowSwitch",
    "co2LowValue",
    "co2FanSettingMode",
    "co2FanAccuracy",
    "co2FanTargetSwitch",
    "co2FanTargetValue",
    "co2FanHighSwitch",
    "co2FanHighValue",
    "co2FanLowSwitch",
    "co2FanLowValue",
    "moistureSettingMode",
    "moistureAccuracy",
    "moistureTargetSwitch",
    "moistureTargetValue",
    "moistureHighSwitch",
    "moistureHighValue",
    "moistureLowSwitch",
    "moistureLowValue",
    "waterLevelSettingMode",
    "waterLevelAccuracy",
    "waterLevelTargetSwitch",
    "waterLevelTargetValue",
    "waterLevelHighSwitch",
    "waterLevelHighValue",
    "waterLevelLowSwitch",
    "waterLevelLowValue",
    "waterTempSettingMode",
    "waterTempAccuracy",
    "waterTempTargetSwitch",
    "waterTempTargetValue",
    "waterTempHighSwitch",
    "waterTempHighValue",
    "waterTempLowSwitch",
    "waterTempLowValue",
    "waterTempTargetValueF",
    "waterTempHighValueF",
    "waterTempLowValueF",
    "isOpenAutomation",
    "settingMode",
    "onlyUpdateSpeed",
    "restore",
)

SETTING_KEYS: tuple[str, ...] = (
    "devId",
    "devName",
    "port",
    "subDeviceId",
    "subDeviceType",
    "devCompany",
    "devCt",
    "devCth",
    "devCth2",
    "devCt2",
    "devCh",
    "vpdCt",
    "vpdCth",
    "tempCompare",
    "humiCompare",
    "loadType",
    "isFlag",
    "devTt",
    "devTth",
    "devTh",
    "vpdTransition",
    "devBt",
    "devBth",
    "devBh",
    "devBvpd",
    "onTimeSwitch",
    "onTime",
    "onMinTime",
    "onMaxTime",
    "isOnMinMaxTime",
    "offDoseTime",
    "onDoseTime",
    "isOpenDoseTime",
    "onSpead",
    "offSpead",
    "onSelfSpead",
    "atType",
    "settingMode",
    "vpdSettingMode",
    "powerState",
    "sensorOneType",
    "sensorTwoType",
    "zoneSensorType",
    "interchangeSensor",
    "paramSensors",
    "sensorSettingStr",
    "sensorTransBuffStr",
    "ecUnit",
    "tdsUnit",
    "ecOrTds",
    "photocellSwitch",
    "keytoneSwitch",
    "hasKeytoneSwitch",
    "backlightSwitch",
    "hasBacklightSwitch",
    "targetVpdSwitch",
    "externalPort",
    "portParamData",
    "secFucDevtype",
    "secFucDevEffect",
    "secFucParams",
    "secFucParamNums",
    "secFucStatus",
    "devLight",
    "otaUpdating",
    "supportOta",
    "isShare",
    "toward",
)

# AI controllers take controls + settings in one PUT; keys = union minus devSetting-only noise.
MODE_AND_SETTING_KEYS: tuple[str, ...] = tuple(
    dict.fromkeys(CONTROL_KEYS + SETTING_KEYS + ("modeAndSettingIdStr", "subDeviceVersion"))
)

_MODE_AND_SETTING_ID_STR = {
    Mode.OFF: "[16,17]",
    Mode.ON: "[16,18]",
    Mode.AUTO: "[112,16,19,32,98,99]",
    Mode.TIMER_TO_ON: "[16,20,21]",
    Mode.TIMER_TO_OFF: "[16,20,21]",
    Mode.CYCLE: "[16,22,23,40]",
    Mode.SCHEDULE: "[16,22,23,40]",
    Mode.VPD: "[16,81,32,98,99]",
}
_MODE_AND_SETTING_ID_STR_SENSOR = "[16,97,32,98,99]"


class AcInfinityError(Exception):
    """Base class for client errors; message is safe to show to the model."""


class AuthError(AcInfinityError):
    pass


class ConnectError(AcInfinityError):
    pass


class RequestFailed(AcInfinityError):
    def __init__(self, body: dict[str, Any]) -> None:
        self.code = body.get("code")
        super().__init__(f"AC Infinity API error {self.code}: {body.get('msg', 'unknown')}")


def _serialise(
    keys: tuple[str, ...], new: dict[str, Any], existing: dict[str, Any]
) -> dict[str, Any]:
    """HA `__transfer_values`: full object, None→0, bool→'true'/'false', containers→JSON."""
    out: dict[str, Any] = {}
    for key in keys:
        value = new.get(key, existing.get(key, 0))
        if value is None:
            out[key] = 0
        elif isinstance(value, dict | list):
            out[key] = json.dumps(value)
        elif isinstance(value, bool):
            out[key] = str(value).lower()
        else:
            out[key] = value
    return out


class AcInfinityClient:
    def __init__(
        self,
        email: str,
        password: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._email = email
        self._password = password[:PASSWORD_MAX_LEN]
        self._token: str | None = None
        self._lock = asyncio.Lock()
        self._device_cache: tuple[float, list[dict[str, Any]]] | None = None
        # devId -> (devType, devPortCount), refreshed with every device list
        self._device_info: dict[str, tuple[int, int]] = {}
        self._http = httpx2.AsyncClient(
            base_url=base_url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------ transport

    def _headers(self, *, auth: bool = True, min_version: bool = False) -> dict[str, str]:
        headers: dict[str, str] = {}
        if auth:
            if not self._token:
                raise AuthError("not logged in")
            headers["token"] = self._token
        if min_version:
            headers["minversion"] = "3.5"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._http.request(method, path, data=data, headers=headers)
        except httpx2.HTTPError as exc:
            raise ConnectError(f"cannot reach AC Infinity API: {exc.__class__.__name__}") from exc
        if response.status_code != 200:
            raise ConnectError(f"AC Infinity API returned HTTP {response.status_code}")
        body = response.json()
        if body.get("code") != 200:
            if path == PATH_LOGIN:
                raise AuthError("AC Infinity rejected the e-mail/password")
            raise RequestFailed(body)
        return body

    async def _authed(
        self, method: str, path: str, *, data=None, min_version=False
    ) -> dict[str, Any]:
        """Authenticated call: re-login on auth loss, exponential backoff on flaky failures."""
        if not self._token:
            await self.login()
        delay = 1.0
        for attempt in range(MAX_RETRIES + 1):
            try:
                return await self._request(
                    method, path, data=data, headers=self._headers(min_version=min_version)
                )
            except RequestFailed as exc:
                # The API answers with a non-200 body code (not HTTP 401) when the token is stale.
                if attempt == 0 and exc.code in (401, 403, 10001, 10002):
                    log.info("token rejected (%s), re-logging in", exc.code)
                    self._token = None
                    await self.login()
                    continue
                if attempt == MAX_RETRIES:
                    raise
            except ConnectError:
                if attempt == MAX_RETRIES:
                    raise
            log.warning(
                "AC Infinity call %s failed, retry %d/%d in %.0fs",
                path,
                attempt + 1,
                MAX_RETRIES,
                delay,
            )
            await asyncio.sleep(delay)
            delay *= 2
        raise AssertionError("unreachable")

    # ------------------------------------------------------------------ reads

    async def login(self) -> None:
        body = await self._request(
            "POST",
            PATH_LOGIN,
            data={"appEmail": self._email, "appPasswordl": self._password},
            headers=self._headers(auth=False),
        )
        self._token = str(body["data"]["appId"])
        log.info("logged in to AC Infinity")

    async def list_controllers(self, *, force: bool = False) -> list[dict[str, Any]]:
        async with self._lock:
            now = time.monotonic()
            if not force and self._device_cache and now - self._device_cache[0] < DEVICE_LIST_TTL:
                return self._device_cache[1]
            if not self._token:
                await self.login()
            body = await self._authed("POST", PATH_DEVICE_LIST, data={"userId": self._token})
            devices: list[dict[str, Any]] = body.get("data") or []
            self._device_cache = (now, devices)
            self._device_info = {
                str(d["devId"]): (
                    d.get("devType") or 0,
                    d.get("devPortCount") or len((d.get("deviceInfo") or {}).get("ports") or []),
                )
                for d in devices
            }
            return devices

    async def describe(self, controller_id: str) -> tuple[bool, int]:
        """(is_ai, port_count) for a known controller; raises AcInfinityError for unknown ids."""
        if controller_id not in self._device_info:
            await self.list_controllers(force=True)
        if controller_id not in self._device_info:
            known = ", ".join(self._device_info) or "none"
            raise AcInfinityError(
                f"unknown controller id {controller_id!r}; known ids: {known} "
                "(use list_controllers)"
            )
        dev_type, port_count = self._device_info[controller_id]
        return dev_type in AI_CONTROLLER_TYPES, port_count

    async def validate_port(
        self, controller_id: str, port: int, *, allow_zero: bool = False
    ) -> None:
        """Reject ports the controller does not have before the API answers with a cryptic 403."""
        _, port_count = await self.describe(controller_id)
        low = 0 if allow_zero else 1
        if not low <= port <= port_count:
            raise AcInfinityError(
                f"controller {controller_id} has ports {low if low else 1}-{port_count}"
                + (" (0 = controller level)" if allow_zero else "")
                + f"; got {port}"
            )

    async def get_port_settings(self, controller_id: str, port: int) -> dict[str, Any]:
        async with self._lock:
            return await self._get_port_settings(controller_id, port)

    async def _get_port_settings(self, controller_id: str, port: int) -> dict[str, Any]:
        body = await self._authed(
            "POST", PATH_MODE_SETTINGS, data={"devId": controller_id, "port": port}
        )
        return body["data"]

    async def get_automations(self, controller_id: str) -> list[dict[str, Any]]:
        """Raw Advance Automation rules (one entry per rule; a program = same advName)."""
        await self.describe(controller_id)
        async with self._lock:
            body = await self._authed("POST", PATH_V2_GROUPS, data={"devId": controller_id})
            return body.get("data") or []

    async def get_alarms(self, controller_id: str) -> list[dict[str, Any]]:
        await self.describe(controller_id)
        async with self._lock:
            body = await self._authed("POST", PATH_V2_ALARMS, data={"devId": controller_id})
            return body.get("data") or []

    async def get_device_settings(self, controller_id: str, port: int) -> dict[str, Any]:
        async with self._lock:
            body = await self._authed(
                "POST", PATH_DEV_SETTING, data={"devId": controller_id, "port": port}
            )
            return body["data"]

    # ------------------------------------------------------------------ writes

    async def update_port_controls(
        self, controller_id: str, port: int, changes: dict[str, Any]
    ) -> None:
        """Read-modify-write of mode/trigger controls for one port (family-aware)."""
        await self.validate_port(controller_id, port)
        is_ai, _ = await self.describe(controller_id)
        async with self._lock:
            if is_ai:
                await self._write_ai(controller_id, port, changes)
            else:
                existing = await self._get_port_settings(controller_id, port)
                payload = _serialise(CONTROL_KEYS, changes, existing)
                await self._authed("POST", f"{PATH_ADD_DEV_MODE}?{urlencode(payload)}")
            self._device_cache = None

    async def update_device_settings(
        self, controller_id: str, port: int, device_name: str, changes: dict[str, Any]
    ) -> None:
        """Read-modify-write of advanced settings (port 0 = controller); standard family only."""
        await self.validate_port(controller_id, port, allow_zero=True)
        is_ai, _ = await self.describe(controller_id)
        async with self._lock:
            if is_ai:
                await self._write_ai(controller_id, port, changes)
                return
            body = await self._authed(
                "POST", PATH_DEV_SETTING, data={"devId": controller_id, "port": port}
            )
            payload = _serialise(SETTING_KEYS, changes, body["data"])
            payload["devName"] = device_name
            await self._authed("POST", f"{PATH_UPDATE_ADV_SETTING}?{urlencode(payload)}")
            self._device_cache = None

    async def _write_ai(self, controller_id: str, port: int, changes: dict[str, Any]) -> None:
        existing = await self._get_port_settings(controller_id, port)
        flattened = dict(existing.get("devSetting") or {})
        flattened.update(existing)
        payload = _serialise(MODE_AND_SETTING_KEYS, changes, flattened)
        at_type = int(payload.get("atType") or Mode.OFF)
        payload["modeAndSettingIdStr"] = _MODE_AND_SETTING_ID_STR.get(
            at_type, _MODE_AND_SETTING_ID_STR_SENSOR
        )
        await self._authed("PUT", f"{PATH_MODE_AND_SETTING}?{urlencode(payload)}", min_version=True)
