"""tools/inspect_battle.py — compact, token-cheap summary of one battle log.

Replaces the ad-hoc inline-Python battle inspection: point it at a battle-id
fragment and get the whole game turn-by-turn — board HP, the chosen action per
slot with its weight, move-resolution events, faints and switches — in a screen
or two instead of raw JSON.

    .venv\\Scripts\\python.exe tools/inspect_battle.py 2640366837
    .venv\\Scripts\\python.exe tools/inspect_battle.py 2640366837 --turn 7

``--turn N`` prints the full detail for that turn: every recorded action with
its reason strings, plus the complete ``wall`` weight map.

Read-only.  Finds the newest log matching the fragment under ``Battle Data/**``.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def find_log(fragment: str) -> str:
    """Newest battle-log path under Battle Data/** whose name contains *fragment*."""
    hits = [f for f in glob.glob(os.path.join(ROOT, "Battle Data", "**", "*.json"),
                                 recursive=True)
            if fragment in os.path.basename(f) and "lead_stats" not in f]
    if not hits:
        raise SystemExit(f"no battle log matching '{fragment}' under Battle Data/")
    return max(hits, key=os.path.getmtime)


def load_log(fragment: str) -> tuple[dict, str]:
    path = find_log(fragment)
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def _hp(m: dict) -> str:
    pct = round(m.get("hp", 0) * 100)
    s = f"{m['s']} {pct}%"
    if pct <= 0:
        s += "†"
    if m.get("sts"):
        s += f" [{m['sts']}]"
    if m.get("b"):
        s += "[" + ",".join(f"{k}{v:+d}" for k, v in m["b"].items()) + "]"
    return s


def _chosen_line(dec: dict, opp: list[dict]) -> str:
    ch = dec.get("ch", "?")
    # find the chosen action to get target + weight
    act = next((a for a in dec.get("acts", []) if a.get("lb") == ch), None)
    tgt = w = ""
    if act:
        ts = act.get("ts")
        if ts is not None and ts < len(opp) and opp[ts]:
            tgt = f">{opp[ts]['s']}"
        w = f" w={act.get('w')}"
    return f"s{dec.get('sl')}: {ch}{tgt}{w}"


def _ev_line(e: dict) -> str:
    s = f"{e.get('sd')}: {e.get('a')} {e.get('mv')}"
    if e.get("tg"):
        s += f">{e['tg']}"
    if e.get("z"):
        s += f" ({e['z']})"
    elif e.get("d") is not None:
        s += f" d={e['d']}" + (" crit" if e.get("cr") else "")
    elif e.get("tg"):
        s += " (no effect)"
    return s


def _field_tags(t: dict) -> str:
    tags = []
    if t.get("w"):
        tags.append(t["w"])
    if t.get("te"):
        tags.append(t["te"])
    if t.get("tr"):
        tags.append("TR")
    tw = t.get("tw") or {}
    if tw.get("us"):
        tags.append("TW-us")
    if tw.get("opp"):
        tags.append("TW-opp")
    return f" [{'/'.join(tags)}]" if tags else ""


def print_turn_detail(t: dict) -> None:
    """Full detail for one turn: every action with reasons + the wall map."""
    for dec in t.get("dec", []):
        print(f"  slot {dec.get('sl')}  (chose: {dec.get('ch')})")
        for a in dec.get("acts", []):
            ts = a.get("ts")
            tgt = f" ts={ts}" if ts is not None else ""
            sw = f" sw={a['sw']}" if a.get("sw") else ""
            print(f"    {a.get('lb')}{tgt}{sw}  w={a.get('w')}")
            for r in a.get("r", []):
                print(f"        {r}")
        wall = dec.get("wall")
        if wall:
            items = sorted(wall.items(), key=lambda kv: -kv[1])
            print("    wall: " + "  ".join(f"{k}={v}" for k, v in items))
    for p in t.get("pin", []):
        mvs = "  ".join(f"{m}={d}" for m, d in sorted(p.get("mvs", {}).items(),
                                                      key=lambda kv: -kv[1]))
        print(f"  pin: {p.get('a')} -> {p.get('df')}:  {mvs}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Compact battle-log summary.")
    ap.add_argument("fragment", help="battle-id fragment (e.g. 2640366837)")
    ap.add_argument("--turn", type=int, default=None,
                    help="print full detail (actions + reasons + wall) for this turn")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    d, path = load_log(args.fragment)
    print(f"{os.path.relpath(path, ROOT)}")
    print(f"engine v{d.get('v')}  team={d.get('team')}@{d.get('team_version')}  "
          f"outcome={d.get('outcome')}")
    pv = d.get("preview")
    if pv:
        print(f"preview: bring={pv.get('bring')}  mega={pv.get('mega')}")
        print(f"         opp={pv.get('opp')}")
        if pv.get("pred"):
            print(f"         predicted opp leads={pv['pred']}")
    if d.get("data_gaps"):
        print(f"DATA GAPS: {d['data_gaps']}")

    for t in d.get("turns", []):
        n = t.get("n")
        my = ", ".join(_hp(m) for m in t.get("my", []) if m)
        op = ", ".join(_hp(m) for m in t.get("opp", []) if m)
        print(f"\nT{n}{_field_tags(t)}  my: {my}  |  opp: {op}")
        opp = t.get("opp", [])
        for dec in t.get("dec", []):
            print(f"  {_chosen_line(dec, opp)}")
        for e in t.get("ev", []):
            print(f"  ev {e.get('o')}: {_ev_line(e)}")
        res = t.get("res") or {}
        if res.get("us") or res.get("opp"):
            print(f"  faints: us={res.get('us', [])} opp={res.get('opp', [])}")
        for s in t.get("sw", []):
            print(f"  switch {s.get('sd')}: {s.get('out')} -> {s.get('in')}")
        if args.turn == n:
            print_turn_detail(t)

    fin = d.get("final")
    if fin:
        my = ", ".join(_hp(m) for m in fin.get("my", []) if m)
        op = ", ".join(_hp(m) for m in fin.get("opp", []) if m)
        print(f"\nfinal  my: {my}  |  opp: {op}")


if __name__ == "__main__":
    main()
