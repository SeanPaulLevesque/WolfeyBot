"""tools/endgame_autopsy.py — fingerprint long-game losses vs wins.

Long games are where we bleed (v9: 10+ turns → 34% win).  For games of at
least --min-turns, this compares wins vs losses on late-turn behaviour:
Protect / switch rates, damage exchanged, opponent boost presence, Struggle
(dead Choice locks), and the terminal board — to localise WHERE the endgame
goes wrong before proposing engine changes.

    .venv\\Scripts\\python.exe tools/endgame_autopsy.py "Battle Data/0.39.0/meta-team/v9"
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _late(turns, start):
    return [t for t in turns if t.get("n", 0) >= start]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Endgame loss autopsy.")
    ap.add_argument("path", help="logs dir")
    ap.add_argument("--min-turns", type=int, default=10)
    ap.add_argument("--late-from", type=int, default=7,
                    help="turn number where 'late game' starts")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    base = args.path if os.path.isabs(args.path) else os.path.join(ROOT, args.path)
    buckets = {"win": [], "loss": []}
    for f in glob.glob(os.path.join(base, "**", "*.json"), recursive=True):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        turns = d.get("turns") or []
        if len(turns) >= args.min_turns and d.get("outcome") in buckets:
            buckets[d.get("outcome")].append(d)

    print(f"{len(buckets['win'])} wins / {len(buckets['loss'])} losses "
          f"with >= {args.min_turns} turns  (late = turn {args.late_from}+)\n")

    for outcome, games in buckets.items():
        n_turns = protects = switches = decs = struggles = 0
        dmg_us = dmg_opp = 0.0
        boosted_opp_turns = 0
        mons_left_us = mons_left_opp = 0
        protect_loops = 0   # same slot Protecting on consecutive late turns
        for g in games:
            late = _late(g["turns"], args.late_from)
            n_turns += len(late)
            prev_protect: dict[int, bool] = {}
            for t in late:
                cur_protect: dict[int, bool] = {}
                for dec in t.get("dec", []):
                    decs += 1
                    ch = dec.get("ch", "")
                    sl = dec.get("sl")
                    if ch in ("Protect", "Detect", "King's Shield", "Spiky Shield"):
                        protects += 1
                        cur_protect[sl] = True
                        if prev_protect.get(sl):
                            protect_loops += 1
                    elif ch.startswith("Switch"):
                        switches += 1
                    elif ch == "Struggle":
                        struggles += 1
                prev_protect = cur_protect
                for e in t.get("ev", []):
                    d_ = e.get("d") or 0
                    if e.get("sd") == "us":
                        dmg_us += d_
                    else:
                        dmg_opp += d_
                if any((m or {}).get("b", {}) and
                       max((m or {}).get("b", {}).values(), default=0) > 0
                       for m in t.get("opp", []) if m):
                    boosted_opp_turns += 1
            fin = g.get("final") or {}
            mons_left_us += sum(1 for m in fin.get("team", []) if m and m.get("hp", 0) > 0)
            mons_left_opp += sum(1 for m in fin.get("opp", []) if m and m.get("hp", 0) > 0)

        ng = max(len(games), 1)
        nt = max(n_turns, 1)
        nd = max(decs, 1)
        print(f"── {outcome.upper()} ({len(games)} games) ──")
        print(f"  late decisions: Protect {protects/nd:.0%}  Switch {switches/nd:.0%}"
              f"  Struggle {struggles}")
        print(f"  consecutive-Protect loops per game: {protect_loops/ng:.2f}")
        print(f"  late damage per turn: us {dmg_us/nt:.2f}  opp {dmg_opp/nt:.2f}"
              f"  (ratio {dmg_us/max(dmg_opp,0.01):.2f})")
        print(f"  opp had a positive boost in {boosted_opp_turns/nt:.0%} of late turns")
        print(f"  avg mons alive at end: us {mons_left_us/ng:.1f}  opp {mons_left_opp/ng:.1f}\n")


if __name__ == "__main__":
    main()
