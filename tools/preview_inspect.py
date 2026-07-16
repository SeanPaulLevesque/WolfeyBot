"""tools/preview_inspect.py — explain ONE team-preview decision end to end.

The counterpart to preview_backtest.py (which re-runs the selector over a whole
corpus): this focuses on a SINGLE opponent six and prints the full reasoning —
so you can edit a constant in team_preview.py, re-run, and watch that one pick
move.  Fixed command, no args — it reads ``tools/scratch/preview.json``:

    # a literal opponent six
    {"team": "meta-team@v11",
     "opp": ["Sneasler","Incineroar","Delphox","Sinistcha","Kingambit","Blastoise"]}

    # or a real logged matchup (pulls the opp six + what we actually did + outcome)
    {"team": "meta-team@v11", "battle": "2648801146"}   # id substring

Sections printed:
  MEGA    — select_mega value for each stone holder
  BRING   — every member's engine matchup score (mega / base), the 4 picked *
  PREDICT — predict_pair + hedged predict_pairs (opp lead pairs, weighted)
  LEADS   — every C(4,2) lead-pair board score, chosen pair *, with eval notes
  RESULT  — bring / mega / lead  (+ vs what actually happened, if a logged game)
"""
from __future__ import annotations

import glob
import json
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SPEC = os.path.join(ROOT, "tools", "scratch", "preview.json")


class _Capture(logging.Handler):
    """Collect team_preview INFO lines (they carry the per-pair eval notes)."""
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.lines: list[str] = []

    def emit(self, record):
        self.lines.append(record.getMessage())


def _resolve_battle(sub: str):
    """Find a logged battle whose filename contains *sub*; return (opp6, actual)."""
    hits = [f for f in glob.glob(os.path.join(ROOT, "Battle Data", "**", "*.json"),
                                 recursive=True)
            if sub in os.path.basename(f) and "lead_stats" not in f]
    if not hits:
        raise SystemExit(f"no battle log matches {sub!r} under Battle Data/")
    d = json.load(open(sorted(hits)[0], encoding="utf-8"))
    pv = d.get("preview") or {}
    turns = d.get("turns") or []
    led = [m.get("s") for m in ((turns[0].get("my") if turns else None) or []) if m]
    actual = {
        "bring": pv.get("bring"), "mega": pv.get("mega"),
        "pred": pv.get("pred"), "led": led, "outcome": d.get("outcome"),
        "team": f"{d.get('team')}@{d.get('team_version')}",
        "file": os.path.basename(sorted(hits)[0]),
    }
    return pv.get("opp") or [], actual


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if not os.path.exists(SPEC):
        raise SystemExit(f"write {SPEC} first — see this file's docstring")
    spec = json.load(open(SPEC, encoding="utf-8"))

    actual = None
    if spec.get("battle"):
        opp, actual = _resolve_battle(str(spec["battle"]))
        team_spec = spec.get("team") or actual["team"]
    else:
        opp = spec.get("opp") or []
        team_spec = spec.get("team")
    if len(opp) < 2:
        raise SystemExit("need an opponent six (spec['opp'] or a resolvable battle)")

    import team as team_mod
    if team_spec:
        team_mod.set_active_team(team_spec)
    members = team_mod.get_team(reload=True)

    cap = _Capture()
    tp_log = logging.getLogger("team_preview")
    tp_log.addHandler(cap)
    tp_log.setLevel(logging.INFO)

    from team_preview import (select_team, select_mega, select_leads,
                              _engine_matchup_scores, _score_lead_pairs,
                              _assumed_weather_for_six)
    from data.lead_stats import predict_pair, predict_pairs

    print(f"TEAM {team_spec}   vs OPP {opp}")
    print(f"assumed weather (bring): {_assumed_weather_for_six(opp)}\n")

    # ── MEGA ──────────────────────────────────────────────────────────────────
    scores = _engine_matchup_scores(opp, members)   # {1-based slot: (mega, base)}
    picked = select_team(opp, members, 4)
    mega = select_mega(picked, members, opp)
    print("MEGA (stone holders):")
    for i, m in enumerate(members, 1):
        if m.mega_name:
            mv, bv = (scores or {}).get(i, (None, None))
            star = " *chosen*" if m.name == mega else ""
            print(f"  {m.name:16} mega={mv}  base={bv}{star}")

    # ── BRING ─────────────────────────────────────────────────────────────────
    print("\nBRING (engine matchup score, mega / base; * = brought):")
    ranked = sorted(range(1, len(members) + 1),
                    key=lambda i: -(scores or {}).get(i, (0, 0))[0])
    for i in ranked:
        mv, bv = (scores or {}).get(i, (None, None))
        star = " *" if i in picked else "  "
        print(f" {star} {members[i-1].name:16} {mv}/{bv}")

    # ── PREDICT ───────────────────────────────────────────────────────────────
    pp = predict_pair(opp)
    hedge = predict_pairs(opp)
    print(f"\nPREDICT opp leads: {pp}")
    print("  hedged pairs:")
    for p, w in hedge:
        print(f"    {' + '.join(p):34} w={w:.2f}")

    # ── LEADS ─────────────────────────────────────────────────────────────────
    lp = _score_lead_pairs(picked, members, hedge, opp) or {}
    final = select_leads(picked, members, opp)
    lead_pair = tuple(final[:2])
    print("\nLEADS (C(4,2) board score; * = chosen):")
    for (a, b), (sc, _ord) in sorted(lp.items(), key=lambda kv: -kv[1][0]):
        star = " *" if {a, b} == set(lead_pair) else "  "
        note = next((ln.split("[", 1)[1].rstrip("]")
                     for ln in cap.lines
                     if ln.strip().startswith("LEAD EVAL")
                     and f"{members[a-1].name}+{members[b-1].name}" in ln and "[" in ln),
                    "")
        print(f" {star} {members[a-1].name} + {members[b-1].name:16} "
              f"score={sc:.3f}   {note}")

    # ── RESULT ────────────────────────────────────────────────────────────────
    print("\nRESULT")
    print(f"  bring: {[members[i-1].name for i in picked]}")
    print(f"  mega:  {mega}")
    print(f"  lead:  {[members[i-1].name for i in final[:2]]}")
    if actual:
        print(f"\nACTUAL (game {actual['file'][-20:]}, outcome={actual['outcome']}):")
        print(f"  predicted then: {actual['pred']}")
        print(f"  brought:        {actual['bring']}")
        print(f"  led:            {actual['led']}")


if __name__ == "__main__":
    main()
