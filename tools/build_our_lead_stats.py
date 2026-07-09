"""tools/build_our_lead_stats.py — rebuild OUR lead-pair performance stats.

Scans every battle log under ``Battle Data/`` (0.21.0+, matching the opponent
lead-stats cutoff), extracts our turn-1 lead pair + outcome per (team@version),
and rewrites ``Battle Data/our_lead_stats.json`` from scratch (safe to re-run;
no double counting).  Live games also accumulate via
``recorder.record_outcome`` → ``data.our_leads.record_result``.

    .venv\\Scripts\\python.exe tools/build_our_lead_stats.py
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data import base_forme          # noqa: E402
from data import our_leads           # noqa: E402

_MIN_VERSION = (0, 21, 0)


def _ver_ok(path: str) -> bool:
    parts = os.path.relpath(path, os.path.join(ROOT, "Battle Data")).split(os.sep)
    try:
        v = tuple(int(x) for x in parts[0].split("."))
        return len(v) == 3 and v >= _MIN_VERSION
    except ValueError:
        return False


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    data: dict = {}
    n = skipped = 0
    for f in glob.glob(os.path.join(ROOT, "Battle Data", "**", "*.json"),
                       recursive=True):
        if "lead_stats" in f or not _ver_ok(f):
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            skipped += 1
            continue
        turns = d.get("turns") or []
        outcome = d.get("outcome")
        team, ver = d.get("team"), d.get("team_version")
        if not turns or outcome not in ("win", "loss") or not (team and ver):
            skipped += 1
            continue
        my = [m["s"] for m in turns[0].get("my", []) if m]
        if len(my) != 2:
            skipped += 1
            continue
        key = "|".join(sorted(base_forme(s) for s in my))
        rec = data.setdefault(f"{team}@{ver}", {}).setdefault(key, {"w": 0, "g": 0})
        rec["g"] += 1
        rec["w"] += outcome == "win"
        n += 1

    our_leads._save(data)
    print(f"Rebuilt from {n} games ({skipped} skipped) -> "
          f"{our_leads._STATS_FILE.relative_to(ROOT)}")
    for spec in sorted(data):
        pairs = data[spec]
        g = sum(r["g"] for r in pairs.values())
        print(f"  {spec}: {len(pairs)} pairs over {g} games")


if __name__ == "__main__":
    main()
