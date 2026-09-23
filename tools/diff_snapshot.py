"""Compare two snapshot folders: prints every key whose value differs, per file.

Usage: uv run python tools/diff_snapshot.py backups/<a> backups/<b> [--ignore key,key]
Volatile keys (timestamps, live readings) are ignored by default.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

VOLATILE = {
    "timestamp",
    "createTime",
    "temperature",
    "temperatureF",
    "humidity",
    "vpdnums",
    "vpdstatus",
    "tTrend",
    "hTrend",
    "trend",
    "speak",
    "loadState",
    "remainTime",
    "devAccesstime",
    "devOfftime",
    "endTime",
    "lastDataTime",
    "sensors",
    "sensorData",
    "sensorTrend",
    "secFucReportTime",
    "reportSeq",
    "appReqId",
    "timeGMT",
    "timeZone",
    "aiSetModifiedTime",
    "online",
    "runState",
    "devTimeZone",
    "sensorReadings",
    "advUpdateTime",
}


def flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list) and obj and isinstance(obj[0], dict):
        for i, v in enumerate(obj):
            key = v.get("port", v.get("advId", i)) if isinstance(v, dict) else i
            yield from flatten(v, f"{prefix}[{key}]")
    else:
        yield prefix, obj


def main(a: Path, b: Path, ignore: set[str]) -> int:
    changed = 0
    for fa in sorted(a.glob("*.json")):
        fb = b / fa.name
        if not fb.exists():
            print(f"{fa.name}: missing in {b}")
            continue
        da = dict(flatten(json.loads(fa.read_text())))
        db = dict(flatten(json.loads(fb.read_text())))
        for key in sorted(set(da) | set(db)):
            leaf = key.rsplit(".", 1)[-1].split("[")[0]
            if leaf in ignore:
                continue
            if da.get(key) != db.get(key):
                changed += 1
                print(f"{fa.name}: {key}: {da.get(key)!r} -> {db.get(key)!r}")
    print(f"{changed} changed keys")
    return changed


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    extra = set()
    for x in sys.argv[1:]:
        if x.startswith("--ignore="):
            extra = set(x.split("=", 1)[1].split(","))
    main(Path(args[0]), Path(args[1]), VOLATILE | extra)
