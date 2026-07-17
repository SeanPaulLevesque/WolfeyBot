"""tools/preview_ab.py — A/B table for team-preview scoring experiments.

For each opponent six in the spec, print the (variant-independent) lead-pair
prediction once, then what we BRING / MEGA / LEAD under each variant — changed
cells vs baseline marked with *.  Fixed command, no args — reads
``tools/scratch/preview_ab.json``:

    {"team": "meta-team@v11",
     "opponents": [["Blastoise","Sneasler",...], ...],
     "variants": [
       {"name": "baseline"},
       {"name": "opp mega x2", "team_preview._OPP_MEGA_WEIGHT": 2.0},
       {"name": "urgency x3",  "decision.modules.SETUP_URGENCY": 3.0}]}

Variant entries are generic ``"module.attr": value`` overrides — applied via
setattr inside try/finally and restored between variants, so new experiments
are a JSON edit, not a tool change.  Knobs that exist for this purpose:
team_preview._OPP_MEGA_WEIGHT / _OFF_WEIGHT / _DEF_WEIGHT /
_LEAD_COVERAGE_FACTOR / _PAIR_PRIOR_POWER / _DOOMED_LEAD_FACTOR /
_SWITCH_WANT_FACTOR, and decision.modules.SETUP_URGENCY / SETUP_DENIAL.
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SPEC = os.path.join(ROOT, "tools", "scratch", "preview_ab.json")


def _apply(overrides: dict) -> list[tuple[object, str, object]]:
    """setattr each ``"module.attr": value``; return undo list."""
    undo = []
    for key, value in overrides.items():
        if key == "name":
            continue
        mod_name, _, attr = key.rpartition(".")
        mod = importlib.import_module(mod_name)
        undo.append((mod, attr, getattr(mod, attr)))
        setattr(mod, attr, value)
    return undo


def _restore(undo) -> None:
    for mod, attr, value in reversed(undo):
        setattr(mod, attr, value)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.disable(logging.CRITICAL)   # the selectors log per-pair evals
    if not os.path.exists(SPEC):
        raise SystemExit(f"write {SPEC} first — see this file's docstring")
    spec = json.load(open(SPEC, encoding="utf-8"))

    import team as team_mod
    if spec.get("team"):
        team_mod.set_active_team(spec["team"])
    members = team_mod.get_team(reload=True)

    from team_preview import (select_team, select_mega, select_leads,
                              _assumed_weather_for_six)
    from data.lead_stats import predict_pairs

    variants = spec.get("variants") or [{"name": "baseline"}]

    for opp in spec.get("opponents") or []:
        print(f"\n{'=' * 78}")
        print(f"OPP  {' / '.join(opp)}")
        weather = _assumed_weather_for_six(opp)
        if weather:
            print(f"     assumed weather: {weather}")
        hedge = predict_pairs(opp)
        print("     predicted leads: "
              + "  |  ".join(f"{' + '.join(p)} ({w:.0%})" for p, w in hedge))
        print()

        base: dict[str, object] = {}
        w = {"v": 24, "bring": 44, "mega": 12}
        print(f"  {'variant':<{w['v']}} {'bring':<{w['bring']}} "
              f"{'mega':<{w['mega']}} our lead")
        for var in variants:
            undo = _apply(var)
            try:
                picked = select_team(opp, members, 4)
                mega = select_mega(picked, members, opp)
                final = select_leads(picked, members, opp)
            finally:
                _restore(undo)
            bring = ", ".join(sorted(members[i - 1].name for i in picked))
            lead = " + ".join(members[i - 1].name for i in final[:2])
            if not base:
                base = {"bring": bring, "mega": mega, "lead": lead}
            def _m(key, val):
                return f"{val} *" if base[key] != val else val
            print(f"  {var['name']:<{w['v']}} {_m('bring', bring):<{w['bring']}} "
                  f"{_m('mega', str(mega)):<{w['mega']}} {_m('lead', lead)}")


if __name__ == "__main__":
    main()
