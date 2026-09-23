"""Dump the complete live state of every controller into backups/<timestamp>/ (git-ignored).

Usage: uv run --env-file .env python tools/snapshot.py [label]
Restore reference for write experiments; compare two snapshots with tools/diff_snapshot.py.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from acinfinity_mcp.client import AcInfinityClient

ROOT = Path(__file__).resolve().parent.parent / "backups"


async def main(label: str) -> None:
    stamp = time.strftime("%Y%m%d-%H%M%S") + (f"-{label}" if label else "")
    out = ROOT / stamp
    out.mkdir(parents=True)
    client = AcInfinityClient(os.environ["ACINFINITY_EMAIL"], os.environ["ACINFINITY_PASSWORD"])
    try:
        devices = await client.list_controllers(force=True)
        (out / "devInfoListAll.json").write_text(json.dumps(devices, indent=1, ensure_ascii=False))
        for dev in devices:
            dev_id = str(dev["devId"])
            port_count = dev.get("devPortCount") or 4
            for port in range(0, port_count + 1):
                mode = await client.get_port_settings(dev_id, port)
                (out / f"{dev_id}_modeSettings_port{port}.json").write_text(
                    json.dumps(mode, indent=1)
                )
                setting = await client.get_device_settings(dev_id, port)
                (out / f"{dev_id}_devSetting_port{port}.json").write_text(
                    json.dumps(setting, indent=1)
                )
            (out / f"{dev_id}_automations.json").write_text(
                json.dumps(await client.get_automations(dev_id), indent=1, ensure_ascii=False)
            )
            (out / f"{dev_id}_alarms.json").write_text(
                json.dumps(await client.get_alarms(dev_id), indent=1, ensure_ascii=False)
            )
    finally:
        await client.aclose()
    print(out)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else ""))
