"""Async client for the (unofficial) AC Infinity cloud API.

Endpoint shapes, quirks and write flows: docs/api/. This module knows nothing about MCP.
"""

from __future__ import annotations

import asyncio
import hashlib
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
PATH_V2_UPDATE_GROUP = "/api/version=2.0/dev/updateGroupsById"
PATH_V2_TOGGLE_GROUP = "/api/version=2.0/dev/updateGroupsIsOn"

# Version name of the Android build whose request-signing scheme standard controllers
# (devType 11/18) require for writes — see docs/api/connection.md "Signed writes".
APP_VERSION = "2.0.8"

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


def build_sign(
    token: str, app_version: str, secret_id: str | None, request_app: str | None, request_id: str
) -> str:
    """Request signature of the Android app (md5 chain over token, version, secretId,
    requestApp and requestId; the body is not covered). Reproduced from the decompiled app
    by Backroads4Me/homeassistant-acinfinity; required by standard controllers for writes."""

    def md5(value: str) -> str:
        return hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()

    left = md5(token + app_version)
    right = (
        md5(secret_id + request_app + request_id) if secret_id and request_app else md5(request_id)
    )
    return md5(left + right)


# The 35 `devSetting` keys the app copies into a `modeAndSetting` PUT (ModesHModel, app 2.0.8).
AI_SETTING_KEYS_IN_PUT: tuple[str, ...] = (
    "offSpead",
    "backlightSwitch",
    "devCompany",
    "devLight",
    "devName",
    "portParamData",
    "ecOrTds",
    "hasBacklightSwitch",
    "hasKeytoneSwitch",
    "isOnMinMaxTime",
    "isOpenDoseTime",
    "keytoneSwitch",
    "loadType",
    "offDoseTime",
    "onDoseTime",
    "onMaxTime",
    "onMinTime",
    "onTime",
    "onTimeSwitch",
    "otaUpdating",
    "photocellSwitch",
    "secFucDevEffect",
    "secFucDevtype",
    "secFucParamNums",
    "secFucParams",
    "secFucStatus",
    "sensorOneType",
    "sensorSettingStr",
    "sensorTransBuffStr",
    "sensorTwoType",
    "subDeviceId",
    "subDeviceType",
    "subDeviceVersion",
    "supportOta",
    "zoneSensorType",
)
_FAHRENHEIT_CLAMP_KEYS = (
    "devHtf",
    "targetTempF",
    "devLtf",
    "waterTempTargetValueF",
    "waterTempHighValueF",
    "waterTempLowValueF",
)


def _app_mode_and_setting_payload(
    existing: dict[str, Any], changes: dict[str, Any], device_name: str
) -> dict[str, Any]:
    """Build the `modeAndSetting` PUT exactly like the app: non-null mode fields (the app's
    `transBean2Map` skips nulls), the 35 setting keys from `devSetting`, `devName` from the
    port list, °F twins clamped to 32, and the id list for the resulting `atType`."""
    setting = existing.get("devSetting") or {}
    payload = {k: v for k, v in existing.items() if v is not None and k != "devSetting"}
    payload.update({k: setting[k] for k in AI_SETTING_KEYS_IN_PUT if setting.get(k) is not None})
    payload["devName"] = device_name
    payload.update({k: v for k, v in changes.items() if v is not None})
    for key in _FAHRENHEIT_CLAMP_KEYS:
        if isinstance(payload.get(key), int) and payload[key] < 32:
            payload[key] = 32
    at_type = int(payload.get("atType") or Mode.OFF)
    payload["modeAndSettingIdStr"] = _MODE_AND_SETTING_ID_STR.get(
        at_type, _MODE_AND_SETTING_ID_STR_SENSOR
    )
    return {
        k: (
            json.dumps(v)
            if isinstance(v, dict | list)
            else str(v).lower()
            if isinstance(v, bool)
            else v
        )
        for k, v in payload.items()
    }


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
        self._secret_id: str | None = None
        self._request_app: str | None = None
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

    def _headers(
        self, *, auth: bool = True, min_version: bool = False, signed: bool = False
    ) -> dict[str, str]:
        headers: dict[str, str] = {}
        if auth:
            if not self._token:
                raise AuthError("not logged in")
            headers["token"] = self._token
        if min_version:
            headers["minversion"] = "3.5"
        if signed:
            # Standard controllers apply a write only when it is signed like the app's;
            # v2 endpoints reject these headers, so they are opt-in per call.
            request_id = str(int(time.time() * 1000))
            headers.update(
                {
                    "requestApp": self._request_app or "",
                    "version": APP_VERSION,
                    "requestId": request_id,
                    "sign": build_sign(
                        self._token or "",
                        APP_VERSION,
                        self._secret_id,
                        self._request_app,
                        request_id,
                    ),
                }
            )
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
        self, method: str, path: str, *, data=None, min_version=False, signed=False
    ) -> dict[str, Any]:
        """Authenticated call: re-login on auth loss, exponential backoff on flaky failures."""
        if not self._token:
            await self.login()
        delay = 1.0
        for attempt in range(MAX_RETRIES + 1):
            try:
                return await self._request(
                    method,
                    path,
                    data=data,
                    headers=self._headers(min_version=min_version, signed=signed),
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
        data = body["data"]
        self._token = str(data["appId"])
        self._secret_id = data.get("secretId")
        self._request_app = data.get("requestApp")
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

    async def require_device(self, controller_id: str, port: int) -> None:
        """Writes to a port with nothing plugged in are rejected by the controller with
        `999999 Data saving failed` (verified live: rename of an empty port). Fail early."""
        await self.validate_port(controller_id, port)
        devices = await self.list_controllers()
        device = next((d for d in devices if str(d["devId"]) == controller_id), None)
        entry = next(
            (
                p
                for p in ((device or {}).get("deviceInfo") or {}).get("ports") or []
                if p.get("port") == port
            ),
            None,
        )
        if entry and entry.get("online") == 0 and entry.get("portResistance") == 65535:
            raise AcInfinityError(
                f"port {port} has no device plugged in; the controller rejects every setting "
                "write for an empty port (999999). Plug a device in first."
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
        """Read-modify-write of mode/trigger controls for one port.

        Both families use `addDevMode` with the full control object as form body. AI
        controllers additionally need the `minversion: 3.5` header — without it the API answers
        `100001`; with a query-string payload the standard family answers 200 but discards the
        write (ober37 Quirks 13/14). Verified live on an AI+ 2026-09-23 (Timer-to-On round trip).
        """
        await self.require_device(controller_id, port)
        is_ai, _ = await self.describe(controller_id)
        async with self._lock:
            existing = await self._get_port_settings(controller_id, port)
            await self._post_controls(
                controller_id, _serialise(CONTROL_KEYS, changes, existing), is_ai
            )

    async def restore_port_controls(
        self, controller_id: str, port: int, saved: dict[str, Any]
    ) -> None:
        """Write a previously captured getdevModeSettingList object back (backup restore)."""
        await self.validate_port(controller_id, port)
        is_ai, _ = await self.describe(controller_id)
        async with self._lock:
            payload = _serialise(CONTROL_KEYS, {}, saved)
            payload["devId"], payload["externalPort"] = controller_id, port
            await self._post_controls(controller_id, payload, is_ai)

    async def _post_controls(
        self, controller_id: str, payload: dict[str, Any], is_ai: bool
    ) -> None:
        await self._authed(
            "POST", PATH_ADD_DEV_MODE, data=payload, min_version=is_ai, signed=not is_ai
        )
        self._device_cache = None

    async def update_automation_rule(self, rule: dict[str, Any]) -> None:
        """Write a complete rule object (as returned by getGroups, with its advId) back in place."""
        controller_id = str(rule["devId"])
        await self.describe(controller_id)
        async with self._lock:
            payload = {k: v for k, v in _serialise(tuple(rule), {}, rule).items()}
            await self._authed("POST", PATH_V2_UPDATE_GROUP, data=payload)

    async def set_automation_enabled(self, controller_id: str, rule_id: int, enabled: bool) -> None:
        """updateGroupsIsOn TOGGLES; read first so the call only happens when needed."""
        is_ai, _ = await self.describe(controller_id)
        async with self._lock:
            body = await self._authed("POST", PATH_V2_GROUPS, data={"devId": controller_id})
            rule = next((r for r in body.get("data") or [] if r.get("advId") == rule_id), None)
            if rule is None:
                raise AcInfinityError(f"no automation rule with id {rule_id} on {controller_id}")
            if (rule.get("isOn") == 1) == enabled:
                return
            await self._authed(
                "POST",
                PATH_V2_TOGGLE_GROUP,
                data={"advId": rule_id, "isDel": 0, "isflag": 1},
                min_version=is_ai,
            )

    async def update_device_settings(
        self, controller_id: str, port: int, device_name: str, changes: dict[str, Any]
    ) -> None:
        """Read-modify-write of advanced settings (port 0 = controller).

        Standard family: `updateAdvSetting` with the full `getDevSetting` object (signed).
        AI family: the app's own `modeAndSetting` recipe (`ModesHModel.setSettingForNet`,
        app 2.0.8): every non-null field of the mode object + the 35 setting keys in
        `AI_SETTING_KEYS_IN_PUT` taken from `devSetting`, `devName` = current port name,
        `modeAndSettingIdStr` for the current mode, °F twins clamped to >= 32.
        """
        await self.validate_port(controller_id, port, allow_zero=True)
        if port:
            await self.require_device(controller_id, port)
        is_ai, _ = await self.describe(controller_id)
        async with self._lock:
            if is_ai:
                existing = await self._get_port_settings(controller_id, port)
                payload = _app_mode_and_setting_payload(existing, changes, device_name)
                payload["devId"], payload["port"] = controller_id, port
                await self._authed(
                    "PUT", f"{PATH_MODE_AND_SETTING}?{urlencode(payload)}", min_version=True
                )
            else:
                body = await self._authed(
                    "POST", PATH_DEV_SETTING, data={"devId": controller_id, "port": port}
                )
                payload = _serialise(SETTING_KEYS, changes, body["data"])
                payload["devName"] = device_name
                await self._authed("POST", PATH_UPDATE_ADV_SETTING, data=payload, signed=True)
            self._device_cache = None

    async def rename_port(self, controller_id: str, port: int, name: str) -> None:
        """Rename a port. AI: minimal `modeAndSetting` PUT with `devName` (verified live, it is
        how the port name was restored after the full-object incident). Standard: the
        `updateAdvSetting` round trip whose `devName` field the app uses for the same purpose."""
        await self.require_device(controller_id, port)
        is_ai, _ = await self.describe(controller_id)
        if not is_ai:
            await self.update_device_settings(controller_id, port, name, {})
            return
        existing = await self.get_port_settings(controller_id, port)
        await self.put_mode_fields(
            controller_id,
            port,
            int(existing.get("atType") or Mode.OFF),
            [17],
            {"offSpead": existing.get("offSpead") or 0, "devName": name},
        )

    async def put_mode_fields(
        self,
        controller_id: str,
        port: int,
        at_type: int,
        group_ids: list[int],
        fields: dict[str, Any],
    ) -> None:
        """App-native AI write: `PUT modeAndSetting` carrying ONLY `atType`, the listed
        field-group ids (`modeAndSettingIdStr`) and the values of every field in those groups.
        A listed group whose values are missing is reset to defaults by the server
        (`onSelfSpead` → 0 observed live), so callers must pass the complete group.
        """
        await self.require_device(controller_id, port)
        params = {
            "devId": controller_id,
            "port": port,
            "atType": at_type,
            "modeAndSettingIdStr": json.dumps(sorted(set(group_ids) | {16}), separators=(",", ":")),
            **fields,
        }
        async with self._lock:
            await self._authed(
                "PUT", f"{PATH_MODE_AND_SETTING}?{urlencode(params)}", min_version=True
            )
            self._device_cache = None
