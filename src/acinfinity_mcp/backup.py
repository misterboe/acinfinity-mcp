"""Full-state backups of a controller and their restoration.

A backup is one JSON file with everything the API lets us read back and write again:
the device-list entry, every port's mode settings (0 = controller record) and the
Advance Automation rules. Files live in ACINFINITY_BACKUP_DIR (default
~/.acinfinity-mcp/backups) and are never uploaded anywhere.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .client import CONTROL_KEYS, AcInfinityClient

ENV_BACKUP_DIR = "ACINFINITY_BACKUP_DIR"
DEFAULT_BACKUP_DIR = Path.home() / ".acinfinity-mcp" / "backups"
FORMAT_VERSION = 1

# Control keys that describe live state rather than configuration; restoring them is
# meaningless and they are excluded from the change list.
_VOLATILE = frozenset(
    {
        "temperature",
        "temperatureF",
        "humidity",
        "vpdnums",
        "vpdstatus",
        "trend",
        "tTrend",
        "hTrend",
        "insideTrend",
        "outsideTrend",
        "insideTemp",
        "outsideTemp",
        "speak",
        "loadState",
        "power",
        "powerState",
        "abnormalState",
        "surplus",
        "isUpdateVpdNums",
    }
)
_RULE_VOLATILE = frozenset({"runState", "portState", "isExist", "advStateValue", "updateData"})


def backup_dir() -> Path:
    return Path(os.environ.get(ENV_BACKUP_DIR) or DEFAULT_BACKUP_DIR)


class BackupInfo(BaseModel):
    backup_id: str = Field(description="Use this id with restore_settings / compare_backup.")
    path: str
    created_at: str
    controller_id: str
    controller_name: str
    ports: int
    automation_rules: int
    label: str | None = None


class BackupList(BaseModel):
    backup_dir: str
    backups: list[BackupInfo]


class FieldChange(BaseModel):
    scope: str = Field(description="'port <n>', 'controller' or 'automation <rule id>'.")
    key: str
    backup_value: Any
    current_value: Any


class BackupDiff(BaseModel):
    backup_id: str
    controller_id: str
    changes: list[FieldChange]
    missing_rules: list[int] = Field(
        default_factory=list, description="Rule ids present in the backup but gone from the device."
    )
    new_rules: list[int] = Field(
        default_factory=list, description="Rule ids on the device that the backup does not know."
    )


class RestoreResult(BaseModel):
    backup_id: str
    controller_id: str
    ports_restored: list[int]
    rules_restored: list[int]
    skipped: list[str] = Field(default_factory=list)
    remaining_changes: list[FieldChange] = Field(
        description="Differences that still exist after the restore (re-read from the device)."
    )


async def capture(
    client: AcInfinityClient, controller_id: str, label: str | None
) -> dict[str, Any]:
    devices = await client.list_controllers(force=True)
    device = next((d for d in devices if str(d["devId"]) == controller_id), None)
    if device is None:
        raise ValueError(f"unknown controller id {controller_id}")
    _, port_count = await client.describe(controller_id)
    ports = {}
    for port in range(0, port_count + 1):
        ports[str(port)] = await client.get_port_settings(controller_id, port)
    return {
        "format": FORMAT_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "label": label,
        "controller_id": controller_id,
        "controller_name": device.get("devName"),
        "device": device,
        "ports": ports,
        "automations": await client.get_automations(controller_id),
        "alarms": await client.get_alarms(controller_id),
    }


def save(data: dict[str, Any]) -> BackupInfo:
    directory = backup_dir()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    label = (data.get("label") or "").strip().replace(" ", "-")
    backup_id = f"{stamp}-{data['controller_id']}" + (f"-{label}" if label else "")
    path = directory / f"{backup_id}.json"
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return info(path)


def info(path: Path) -> BackupInfo:
    data = json.loads(path.read_text())
    return BackupInfo(
        backup_id=path.stem,
        path=str(path),
        created_at=data.get("created_at", ""),
        controller_id=str(data.get("controller_id", "")),
        controller_name=data.get("controller_name") or "",
        ports=max(len(data.get("ports", {})) - 1, 0),
        automation_rules=len(data.get("automations") or []),
        label=data.get("label"),
    )


def list_backups() -> BackupList:
    directory = backup_dir()
    files = sorted(directory.glob("*.json"), reverse=True) if directory.exists() else []
    return BackupList(backup_dir=str(directory), backups=[info(p) for p in files])


def load(backup_id: str) -> dict[str, Any]:
    if "/" in backup_id or backup_id.startswith("."):
        raise ValueError("invalid backup id")
    path = backup_dir() / f"{backup_id}.json"
    if not path.exists():
        raise ValueError(f"backup {backup_id!r} not found in {backup_dir()}")
    return json.loads(path.read_text())


def diff(saved: dict[str, Any], current: dict[str, Any]) -> BackupDiff:
    changes: list[FieldChange] = []
    for port, old in saved["ports"].items():
        new = current["ports"].get(port) or {}
        scope = "controller" if port == "0" else f"port {port}"
        for key in CONTROL_KEYS:
            if key in _VOLATILE:
                continue
            if old.get(key) != new.get(key):
                changes.append(
                    FieldChange(
                        scope=scope, key=key, backup_value=old.get(key), current_value=new.get(key)
                    )
                )
    old_rules = {r["advId"]: r for r in saved.get("automations") or []}
    new_rules = {r["advId"]: r for r in current.get("automations") or []}
    for rule_id, old in old_rules.items():
        new = new_rules.get(rule_id)
        if new is None:
            continue
        for key in old:
            if key in _RULE_VOLATILE or old.get(key) == new.get(key):
                continue
            changes.append(
                FieldChange(
                    scope=f"automation {rule_id}",
                    key=key,
                    backup_value=old.get(key),
                    current_value=new.get(key),
                )
            )
    return BackupDiff(
        backup_id="",
        controller_id=saved["controller_id"],
        changes=changes,
        missing_rules=sorted(set(old_rules) - set(new_rules)),
        new_rules=sorted(set(new_rules) - set(old_rules)),
    )


async def restore(
    client: AcInfinityClient,
    saved: dict[str, Any],
    *,
    ports: bool = True,
    automations: bool = True,
    only_changed: bool = True,
) -> RestoreResult:
    controller_id = saved["controller_id"]
    before = diff(saved, await capture(client, controller_id, None))
    changed_scopes = {c.scope for c in before.changes}
    ports_restored: list[int] = []
    rules_restored: list[int] = []
    skipped: list[str] = []
    if ports:
        for port_str, old in saved["ports"].items():
            port = int(port_str)
            scope = "controller" if port == 0 else f"port {port}"
            if only_changed and scope not in changed_scopes:
                continue
            if port == 0:
                skipped.append("controller record (port 0) is not restored automatically")
                continue
            await client.restore_port_controls(controller_id, port, old)
            ports_restored.append(port)
    if automations:
        for rule in saved.get("automations") or []:
            rule_id = rule["advId"]
            if rule_id in before.missing_rules:
                skipped.append(f"automation {rule_id} no longer exists on the device")
                continue
            if only_changed and f"automation {rule_id}" not in changed_scopes:
                continue
            clean = {k: v for k, v in rule.items() if k not in _RULE_VOLATILE}
            await client.update_automation_rule(clean)
            rules_restored.append(rule_id)
    after = diff(saved, await capture(client, controller_id, None))
    return RestoreResult(
        backup_id="",
        controller_id=controller_id,
        ports_restored=ports_restored,
        rules_restored=rules_restored,
        skipped=skipped,
        remaining_changes=after.changes,
    )
