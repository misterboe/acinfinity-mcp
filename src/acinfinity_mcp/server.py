"""MCP server exposing AC Infinity UIS controllers. Tools are thin: validate → client → model."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__, backup
from .client import AcInfinityClient, AcInfinityError
from .models import (
    SCHEDULE_DISABLED,
    AutomationList,
    ControllerList,
    Mode,
    PortSettings,
    WriteResult,
    celsius_to_fahrenheit,
    decode_automations,
    decode_controller,
    decode_port_settings,
    hhmm_to_minutes,
)

log = logging.getLogger(__name__)
# httpx2 logs every request at INFO; that only adds noise on stderr.
logging.getLogger("httpx2").setLevel(logging.WARNING)

ENV_EMAIL = "ACINFINITY_EMAIL"
ENV_PASSWORD = "ACINFINITY_PASSWORD"
ENV_LOG_LEVEL = "ACINFINITY_LOG_LEVEL"


@dataclass
class AppState:
    client: AcInfinityClient


@asynccontextmanager
async def lifespan(_: MCPServer) -> AsyncIterator[AppState]:
    email = os.environ.get(ENV_EMAIL)
    password = os.environ.get(ENV_PASSWORD)
    if not email or not password:
        raise RuntimeError(
            f"{ENV_EMAIL} and {ENV_PASSWORD} must be set in the MCP client config "
            "(see README.md) or in a local .env used with `uv run --env-file .env`."
        )
    client = AcInfinityClient(email, password)
    try:
        yield AppState(client=client)
    finally:
        await client.aclose()


mcp = MCPServer(
    "acinfinity",
    title="AC Infinity",
    instructions=(
        "Read sensors and control ports of AC Infinity UIS grow controllers (69 Pro/Pro+, AI+). "
        "Start with list_controllers to get controller ids and port numbers. "
        "All set_* tools change a real device and require user_authorized=true — only pass it "
        "after the user explicitly confirmed the specific change."
    ),
    version=__version__,
    log_level=os.environ.get(ENV_LOG_LEVEL, "INFO").upper(),  # type: ignore[arg-type]
    lifespan=lifespan,
)

READ = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)
# Writes a file on this machine, never the device.
WRITE_LOCAL = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False
)
BackupId = Annotated[
    str, Field(pattern=r"^[A-Za-z0-9._-]+$", description="Backup id from backup_settings.")
]

ControllerId = Annotated[str, Field(description="Controller id (`id` from list_controllers).")]
PortNo = Annotated[
    int, Field(ge=1, le=8, description="Port number as printed on the controller (1-based).")
]
Authorized = Annotated[
    bool,
    Field(
        description="Must be true. Set only after the user explicitly approved this exact change."
    ),
]
Power = Annotated[int, Field(ge=0, le=10, description="Power level 0 (off) to 10 (max).")]
Minutes = Annotated[int, Field(ge=0, le=1440, description="Duration in minutes (0-1440).")]
HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


def _client(ctx: Context[AppState]) -> AcInfinityClient:
    return ctx.request_context.lifespan_context.client


def _require_auth(user_authorized: bool) -> None:
    if not user_authorized:
        raise ToolError(
            "This tool changes a physical device. Ask the user to confirm the exact change, "
            "then call again with user_authorized=true."
        )


async def _call[T](coro: Awaitable[T]) -> T:
    try:
        return await coro
    except AcInfinityError as exc:
        raise ToolError(str(exc)) from exc


async def _check_port(
    ctx: Context[AppState], controller_id: str, port: int, *, allow_zero: bool = False
) -> None:
    """Fail early with a helpful message instead of the API's '403 Data saving failed'."""
    await _call(_client(ctx).validate_port(controller_id, port, allow_zero=allow_zero))


async def _write(
    ctx: Context[AppState], controller_id: str, port: int, changes: dict[str, Any]
) -> WriteResult:
    await _call(_client(ctx).update_port_controls(controller_id, port, changes))
    return WriteResult(controller_id=controller_id, port=port, changed=changes)


# ---------------------------------------------------------------------------- read tools


@mcp.tool(title="List controllers", annotations=READ)
async def list_controllers(ctx: Context[AppState]) -> ControllerList:
    """List all AC Infinity controllers on the account with current readings and port status.

    `tent` is the climate inside the grow tent (external probe: temperature °C, humidity %,
    VPD kPa) — use this when the user asks how the tent is doing. `ambient` (AI controllers
    only) is the onboard sensor in the controller housing, i.e. the room outside the tent.
    Also returns every port with name, power level (0-10), on/off state and active mode, and
    on AI controllers every individual sensor reading. Readings are null while offline.

    A port whose mode is 'Off' but whose power is > 0 is being driven by an Advance
    Automation program — call list_automations to see the rules governing it.
    """
    raw = await _call(_client(ctx).list_controllers())
    return ControllerList(controllers=[decode_controller(r) for r in raw])


@mcp.tool(title="Get port settings", annotations=READ)
async def get_port_settings(
    ctx: Context[AppState], controller_id: ControllerId, port: PortNo
) -> PortSettings:
    """Get the mode configuration of one port: active mode, on/off power, auto temperature and
    humidity triggers (°C / %), VPD triggers (kPa), timer and cycle durations (minutes) and the
    schedule window (HH:MM). Units are already converted; nothing is scaled.
    """
    await _check_port(ctx, controller_id, port)
    raw = await _call(_client(ctx).get_port_settings(controller_id, port))
    return decode_port_settings(controller_id, port, raw)


@mcp.tool(title="Get raw port settings", annotations=READ)
async def get_port_settings_raw(
    ctx: Context[AppState], controller_id: ControllerId, port: Annotated[int, Field(ge=0, le=8)]
) -> dict[str, Any]:
    """Return the unmodified API object for a port (getdevModeSettingList) including the nested
    `devSetting` advanced settings. Port 0 = controller-level settings. Values are in API units
    (see docs/api/controls-and-settings.md); use get_port_settings for converted values.
    """
    await _check_port(ctx, controller_id, port, allow_zero=True)
    return await _call(_client(ctx).get_port_settings(controller_id, port))


@mcp.tool(title="Get advanced device settings", annotations=READ)
async def get_device_settings(
    ctx: Context[AppState], controller_id: ControllerId, port: Annotated[int, Field(ge=0, le=8)]
) -> dict[str, Any]:
    """Return the advanced settings object (getDevSetting) for a port, or for the controller when
    port=0: temperature unit, calibration offsets, load type, dynamic response, sunrise timer,
    display options. Values are in API units. Works on both controller families; on AI
    controllers the same data is also nested as `devSetting` in get_port_settings_raw.
    """
    await _check_port(ctx, controller_id, port, allow_zero=True)
    return await _call(_client(ctx).get_device_settings(controller_id, port))


@mcp.tool(title="List automations", annotations=READ)
async def list_automations(ctx: Context[AppState], controller_id: ControllerId) -> AutomationList:
    """List the Advance Automation programs of a controller (the app's "Automations" tab).

    A program is a named set of rules; each rule governs one or more ports with a mode
    (On/Off/Auto/Cycle/VPD), on/off power, a schedule and, for Auto/VPD, sensor thresholds.
    These rules override the per-port mode from get_port_settings while they run — on AI
    controllers this is where the real configuration lives.

    Use `schedule`/`continuous` for when a rule applies: `continuous=true` means the app's
    24/7 switch is on and the rule runs at all times (window/days are then null/empty).
    Thresholds: `low`/`high` are null when that trigger is not set; the underlying record
    is only partially reverse-engineered (see `raw`), so report values as decoded from the
    device rather than as guaranteed.
    """
    client = _client(ctx)
    is_ai, _ = await _call(client.describe(controller_id))
    raw = await _call(client.get_automations(controller_id))
    return decode_automations(controller_id, raw, is_ai=is_ai)


@mcp.tool(title="Get raw automations", annotations=READ)
async def get_automations_raw(
    ctx: Context[AppState], controller_id: ControllerId
) -> dict[str, Any]:
    """Unmodified Advance Automation rule objects (getGroups) plus alarms (getAlarms) for a
    controller, in API units. Use list_automations for the decoded view.
    """
    client = _client(ctx)
    rules = await _call(client.get_automations(controller_id))
    alarms = await _call(client.get_alarms(controller_id))
    return {"rules": rules, "alarms": alarms}


# ---------------------------------------------------------------------------- backup tools


@mcp.tool(title="Backup settings", annotations=WRITE_LOCAL)
async def backup_settings(
    ctx: Context[AppState],
    controller_id: ControllerId,
    label: Annotated[
        str | None, Field(max_length=40, description="Optional tag for the file name.")
    ] = None,
) -> backup.BackupInfo:
    """Save the complete configuration of a controller (every port's mode settings, the
    controller record, all Advance Automation rules and alarms) to a local JSON file. Nothing
    on the device changes. Do this before any set_* call; restore_settings undoes changes.
    """
    data = await _call(backup.capture(_client(ctx), controller_id, label))
    return backup.save(data)


@mcp.tool(title="List backups", annotations=READ)
async def list_backups(ctx: Context[AppState]) -> backup.BackupList:
    """List saved backups (newest first) with their ids for restore_settings/compare_backup."""
    return backup.list_backups()


@mcp.tool(title="Compare backup", annotations=READ)
async def compare_backup(ctx: Context[AppState], backup_id: BackupId) -> backup.BackupDiff:
    """Show every configuration field that differs between a backup and the device right now
    (per port and per automation rule), without changing anything. Use it after write
    experiments to verify the device is back in its original state.
    """
    saved = _load_backup(backup_id)
    current = await _call(backup.capture(_client(ctx), saved["controller_id"], None))
    result = backup.diff(saved, current)
    result.backup_id = backup_id
    return result


@mcp.tool(title="Restore settings", annotations=WRITE)
async def restore_settings(
    ctx: Context[AppState],
    backup_id: BackupId,
    ports: Annotated[bool, Field(description="Restore per-port mode settings.")] = True,
    automations: Annotated[bool, Field(description="Restore Advance Automation rules.")] = True,
    only_changed: Annotated[
        bool, Field(description="Only write ports/rules that differ from the backup.")
    ] = True,
    user_authorized: Authorized = False,
) -> backup.RestoreResult:
    """Write a backup back to the device: each changed port's full mode settings and each
    changed automation rule (in place, by id). The controller record (port 0) and rules that
    no longer exist are skipped and reported. Afterwards the device is re-read and any
    remaining differences are returned — an empty `remaining_changes` means fully restored.
    """
    _require_auth(user_authorized)
    saved = _load_backup(backup_id)
    result = await _call(
        backup.restore(
            _client(ctx), saved, ports=ports, automations=automations, only_changed=only_changed
        )
    )
    result.backup_id = backup_id
    return result


def _load_backup(backup_id: str) -> dict[str, Any]:
    try:
        return backup.load(backup_id)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


# ---------------------------------------------------------------------------- write tools


@mcp.tool(title="Rename port", annotations=WRITE)
async def rename_port(
    ctx: Context[AppState],
    controller_id: ControllerId,
    port: PortNo,
    name: Annotated[
        str, Field(min_length=1, max_length=30, description="New port name shown in the app.")
    ],
    user_authorized: Authorized = False,
) -> WriteResult:
    """Rename a port (the label shown in the AC Infinity app). Does not change any mode or power."""
    _require_auth(user_authorized)
    await _call(_client(ctx).rename_port(controller_id, port, name))
    return WriteResult(controller_id=controller_id, port=port, changed={"devName": name})


@mcp.tool(title="Set port mode", annotations=WRITE)
async def set_port_mode(
    ctx: Context[AppState],
    controller_id: ControllerId,
    port: PortNo,
    mode: Annotated[
        Mode,
        Field(
            description="1 Off, 2 On, 3 Auto, 4 Timer to On, 5 Timer to Off, 6 Cycle, "
            "7 Schedule, 8 VPD, 9 CO2, 10 CO2 Fan, 11 Moisture, 12 Water Temp, 13 pH, "
            "14 EC, 15 Water Detect."
        ),
    ],
    user_authorized: Authorized = False,
) -> WriteResult:
    """Switch the active mode of a port (e.g. Off, On, Auto, Schedule). The mode's parameters
    (power, triggers, timers) keep their current values — set them first with the other tools.
    """
    _require_auth(user_authorized)
    return await _write(ctx, controller_id, port, {"atType": int(mode)})


@mcp.tool(title="Set port power", annotations=WRITE)
async def set_port_power(
    ctx: Context[AppState],
    controller_id: ControllerId,
    port: PortNo,
    on_power: Annotated[
        int | None, Field(ge=0, le=10, description="Power level used while the port is 'on'.")
    ] = None,
    off_power: Annotated[
        int | None, Field(ge=0, le=10, description="Power level used while the port is 'off'.")
    ] = None,
    user_authorized: Authorized = False,
) -> WriteResult:
    """Set the power levels (0-10) a port uses in its on and/or off state. Applies to every mode;
    in On mode `on_power` is the running level. Pass only the values you want to change.
    """
    _require_auth(user_authorized)
    changes: dict[str, Any] = {}
    if on_power is not None:
        changes["onSpead"] = on_power
        changes["onSelfSpead"] = on_power
    if off_power is not None:
        changes["offSpead"] = off_power
    if not changes:
        raise ToolError("Provide on_power and/or off_power.")
    return await _write(ctx, controller_id, port, changes)


@mcp.tool(title="Set port timer", annotations=WRITE)
async def set_port_timer(
    ctx: Context[AppState],
    controller_id: ControllerId,
    port: PortNo,
    minutes: Minutes,
    direction: Annotated[
        str, Field(pattern="^(to_on|to_off)$", description="'to_on' or 'to_off'.")
    ],
    activate: Annotated[
        bool, Field(description="Also switch the port into the matching timer mode.")
    ] = True,
    user_authorized: Authorized = False,
) -> WriteResult:
    """Configure a countdown timer: the port turns on (to_on) or off (to_off) after `minutes`."""
    _require_auth(user_authorized)
    changes: dict[str, Any]
    if direction == "to_on":
        changes = {"acitveTimerOn": minutes * 60}
        mode = Mode.TIMER_TO_ON
    else:
        changes = {"acitveTimerOff": minutes * 60}
        mode = Mode.TIMER_TO_OFF
    if activate:
        changes["atType"] = int(mode)
    return await _write(ctx, controller_id, port, changes)


@mcp.tool(title="Set port cycle", annotations=WRITE)
async def set_port_cycle(
    ctx: Context[AppState],
    controller_id: ControllerId,
    port: PortNo,
    on_minutes: Minutes,
    off_minutes: Minutes,
    activate: Annotated[bool, Field(description="Also switch the port into Cycle mode.")] = True,
    user_authorized: Authorized = False,
) -> WriteResult:
    """Configure Cycle mode: repeat `on_minutes` on, then `off_minutes` off."""
    _require_auth(user_authorized)
    changes: dict[str, Any] = {"activeCycleOn": on_minutes * 60, "activeCycleOff": off_minutes * 60}
    if activate:
        changes["atType"] = int(Mode.CYCLE)
    return await _write(ctx, controller_id, port, changes)


@mcp.tool(title="Set port schedule", annotations=WRITE)
async def set_port_schedule(
    ctx: Context[AppState],
    controller_id: ControllerId,
    port: PortNo,
    start: Annotated[
        str | None, Field(pattern=HHMM, description="Daily on time HH:MM, or null to disable.")
    ],
    end: Annotated[
        str | None, Field(pattern=HHMM, description="Daily off time HH:MM, or null to disable.")
    ],
    activate: Annotated[bool, Field(description="Also switch the port into Schedule mode.")] = True,
    user_authorized: Authorized = False,
) -> WriteResult:
    """Configure Schedule mode: on at `start`, off at `end` (controller local time). A window
    crossing midnight (e.g. 18:00 → 06:00) is allowed. Null disables that edge (API value 65535).
    """
    _require_auth(user_authorized)
    changes: dict[str, Any] = {
        "schedStartTime": hhmm_to_minutes(start) if start else SCHEDULE_DISABLED,
        "schedEndtTime": hhmm_to_minutes(end) if end else SCHEDULE_DISABLED,
    }
    if activate:
        changes["atType"] = int(Mode.SCHEDULE)
    return await _write(ctx, controller_id, port, changes)


@mcp.tool(title="Set auto triggers", annotations=WRITE)
async def set_auto_triggers(
    ctx: Context[AppState],
    controller_id: ControllerId,
    port: PortNo,
    temp_high_c: Annotated[
        float | None, Field(ge=0, le=90, description="Turn on above this °C; null = unchanged.")
    ] = None,
    temp_high_enabled: bool | None = None,
    temp_low_c: Annotated[
        float | None, Field(ge=0, le=90, description="Turn on below this °C.")
    ] = None,
    temp_low_enabled: bool | None = None,
    humidity_high_pct: Annotated[int | None, Field(ge=0, le=100)] = None,
    humidity_high_enabled: bool | None = None,
    humidity_low_pct: Annotated[int | None, Field(ge=0, le=100)] = None,
    humidity_low_enabled: bool | None = None,
    activate: Annotated[bool, Field(description="Also switch the port into Auto mode.")] = False,
    user_authorized: Authorized = False,
) -> WriteResult:
    """Configure Auto-mode temperature/humidity triggers. Each trigger has a value and an
    enabled flag; pass only what should change. Temperatures are °C (the °F twin is derived).
    """
    _require_auth(user_authorized)
    changes: dict[str, Any] = {}
    if temp_high_c is not None:
        changes["devHt"] = int(temp_high_c)
        changes["devHtf"] = celsius_to_fahrenheit(temp_high_c)
    if temp_low_c is not None:
        changes["devLt"] = int(temp_low_c)
        changes["devLtf"] = celsius_to_fahrenheit(temp_low_c)
    if humidity_high_pct is not None:
        changes["devHh"] = humidity_high_pct
    if humidity_low_pct is not None:
        changes["devLh"] = humidity_low_pct
    for flag, key in (
        (temp_high_enabled, "activeHt"),
        (temp_low_enabled, "activeLt"),
        (humidity_high_enabled, "activeHh"),
        (humidity_low_enabled, "activeLh"),
    ):
        if flag is not None:
            changes[key] = int(flag)
    if activate:
        changes["atType"] = int(Mode.AUTO)
        changes["settingMode"] = 0
    if not changes:
        raise ToolError("Nothing to change: pass at least one trigger value or flag.")
    return await _write(ctx, controller_id, port, changes)


@mcp.tool(title="Set VPD triggers", annotations=WRITE)
async def set_vpd_triggers(
    ctx: Context[AppState],
    controller_id: ControllerId,
    port: PortNo,
    vpd_high_kpa: Annotated[
        float | None, Field(ge=0, le=9.9, description="Turn on above this VPD (kPa).")
    ] = None,
    vpd_high_enabled: bool | None = None,
    vpd_low_kpa: Annotated[
        float | None, Field(ge=0, le=9.9, description="Turn on below this VPD (kPa).")
    ] = None,
    vpd_low_enabled: bool | None = None,
    activate: Annotated[bool, Field(description="Also switch the port into VPD mode.")] = False,
    user_authorized: Authorized = False,
) -> WriteResult:
    """Configure VPD-mode high/low triggers in kPa (one decimal). Pass only what should change."""
    _require_auth(user_authorized)
    changes: dict[str, Any] = {}
    if vpd_high_kpa is not None:
        changes["activeHtVpdNums"] = round(vpd_high_kpa * 10)
    if vpd_low_kpa is not None:
        changes["activeLtVpdNums"] = round(vpd_low_kpa * 10)
    if vpd_high_enabled is not None:
        changes["activeHtVpd"] = int(vpd_high_enabled)
    if vpd_low_enabled is not None:
        changes["activeLtVpd"] = int(vpd_low_enabled)
    if activate:
        changes["atType"] = int(Mode.VPD)
        changes["vpdSettingMode"] = 0
    if not changes:
        raise ToolError("Nothing to change: pass at least one trigger value or flag.")
    return await _write(ctx, controller_id, port, changes)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
