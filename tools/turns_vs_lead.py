"""tools/turns_vs_lead.py — every logged turn 1 against a given opponent lead pair.

Matchup study: find all battles where the opponent's actual turn-1 leads were
the given pair (order-independent, mega formes folded), and show what we
brought/led, what each side did on turn 1, and how the game ended.

    .venv\\Scripts\\python.exe tools/turns_vs_lead.py Swampert Pelipper
    .venv\\Scripts\\python.exe tools/turns_vs_lead.py Swampert Pelipper --dir "Battle Data/0.38.0"
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data import base_forme  # noqa: E402


def _hp(m: dict) -> str:
    pct = round(m.get("hp", 0) * 100)
    return f"{m['s']} {pct}%" + ("†" if pct <= 0 else "")


def _chosen(dec: dict, opp: list[dict]) -> str:
    ch = dec.get("ch", "?")
    act = next((a for a in dec.get("acts", []) if a.get("lb") == ch), None)
    tgt = w = ""
    if act:
        ts = act.get("ts")
        if ts is not None and ts < len(opp) and opp[ts]:
            tgt = f">{opp[ts]['s']}"
        w = f" (w={act.get('w')})"
    return f"{ch}{tgt}{w}"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="All turn 1s vs an opponent lead pair.")
    ap.add_argument("lead_a")
    ap.add_argument("lead_b")
    ap.add_argument("--dir", default="Battle Data",
                    help="logs root (default: all of Battle Data)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    want = frozenset((base_forme(args.lead_a), base_forme(args.lead_b)))
    base = args.dir if os.path.isabs(args.dir) else os.path.join(ROOT, args.dir)
    files = [f for f in glob.glob(os.path.join(base, "**", "*.json"), recursive=True)
             if "lead_stats" not in f]

    hits = 0
    wins = 0
    for path in sorted(files):
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        turns = d.get("turns") or []
        if not turns:
            continue
        t1 = turns[0]
        opp = [m for m in t1.get("opp", []) if m]
        if frozenset(base_forme(m["s"]) for m in opp) != want:
            continue
        hits += 1
        won = d.get("outcome") == "win"
        wins += won
        pv = d.get("preview") or {}
        print(f"═══ {os.path.basename(path)[:52]}")
        print(f"    v{d.get('v')}  team={d.get('team')}@{d.get('team_version')}  "
              f"outcome={d.get('outcome', '?').upper()}")
        if pv:
            print(f"    bring={pv.get('bring')}  pred={pv.get('pred')}  mega={pv.get('mega')}")
        my = ", ".join(_hp(m) for m in t1.get("my", []) if m)
        op = ", ".join(_hp(m) for m in opp)
        print(f"    T1 board: my {my}  |  opp {op}")
        for dec in t1.get("dec", []):
            print(f"      s{dec.get('sl')}: {_chosen(dec, opp)}")
        for e in t1.get("ev", []):
            s = f"{e.get('sd')}: {e.get('a')} {e.get('mv')}"
            if e.get("tg"):
                s += f">{e['tg']}"
            if e.get("z"):
                s += f" ({e['z']})"
            elif e.get("d") is not None:
                s += f" d={e['d']}"
            print(f"      ev {e.get('o')}: {s}")
        res = t1.get("res") or {}
        if res.get("us") or res.get("opp"):
            print(f"      T1 faints: us={res.get('us', [])} opp={res.get('opp', [])}")
        for s in t1.get("sw", []):
            print(f"      T1 switch {s.get('sd')}: {s.get('out')} -> {s.get('in')}")
        print()

    print(f"{hits} games vs {args.lead_a}+{args.lead_b}  |  record {wins}-{hits - wins}")


if __name__ == "__main__":
    main()
