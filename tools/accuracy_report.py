"""tools/accuracy_report.py — Prediction-accuracy report from instrumented
battle logs (0.8.4+).

Compares the engine's logged predictions against what actually happened, to
surface places the model is miscalibrated.  Three sections:

  1. HIGH-LEVEL STATS — win rate, offense damage accuracy, defensive
     under-prediction count, turn-order accuracy.
  2. TURN ORDER — predicted resolution position vs actual (full 4-move turns).
  3. PER-CASE — one line per flagged case (attacker, defender, predicted,
     actual).  The headline list is *defensive under-predictions*: a mon we
     thought was safe took more than predicted.  Crits and misses are excluded
     (crits are flagged ``cr`` in the log; misses deal no damage so never
     trigger an under-prediction).

Usage (from repo root):
    .venv\\Scripts\\python.exe tools/accuracy_report.py 0.8.4
    .venv\\Scripts\\python.exe tools/accuracy_report.py 0.17.0 --team v2 --slop 0.15

The prediction analysis is exposed as ``prediction_report(games, slop)`` and the
loader as ``_load(version, team_version)`` so ``tools/team_report.py`` can reuse
them in a combined roster + accuracy report.
"""
import json
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import base_forme as _base   # canonical forme-equivalence normaliser

DMG_RE = re.compile(r"damage_output: (\d+)% HP")
POS_RE = re.compile(r"pos (\d)/4")

# Moves that resolve early (via +priority) but don't threaten us — a Protect (or
# Endure) moving "before" our attacker is fine and shouldn't count as our mon
# being slow.  Excluded when computing the actual turn-order position.
_NONTHREAT_FIRST = frozenset({
    "Protect", "Detect", "King's Shield", "Spiky Shield", "Baneful Bunker",
    "Silk Trap", "Burning Bulwark", "Wide Guard", "Quick Guard", "Crafty Shield",
    "Mat Block", "Max Guard", "Obstruct", "Endure",
})


def _load(version, team_version=None):
    """Load all battle logs for *version*; optionally filter to *team_version*.

    Named-team runs nest logs under ``<version>/<team>/<team_version>/``; passing
    e.g. ``team_version="v2"`` keeps only logs under a ``/v2/`` path segment."""
    files = glob.glob(os.path.join("Battle Data", version, "**", "*.json"), recursive=True)
    if team_version:
        seg = os.sep + team_version + os.sep
        files = [f for f in files if seg in f]
    return [json.load(open(f, encoding="utf-8")) for f in files]


def compute_prediction(games, slop=0.15):
    """Compute prediction-accuracy stats for a pre-loaded *games* list and return
    them as a dict (no printing).  Shared by the console ``prediction_report`` and
    the Markdown renderer in tools/team_report.py.

    Returns keys: ``off_within``/``off_total`` (offense damage within ±slop),
    ``off_miss`` [(err,mv,tg,pred,act)], ``off_immune`` [(pred,mv,tg,ability)],
    ``def_under`` [(err,atk,def,mv,pred,act,kind)], and turn-order
    ``to_exact``/``to_off1``/``to_worse``/``to_total``."""
    # ── gather offense / defense / turn-order samples ────────────────────────
    off_within = off_total = 0
    off_miss = []                      # (err, our_mon, mv, tg, pred, act)
    off_immune = []                    # (pred, mv, tg, ability) — predicted dmg on immune target
    def_under = []                     # (err, attacker, defender, mv, pred, act, mode)
    to_miss = []                       # (diff, our_mon, mv, predicted_pos, actual_pos)
    to_exact = to_off1 = to_worse = to_total = 0

    for g in games:
        for t in g.get("turns", []):
            ev = t.get("ev", [])
            my = t.get("my", [])
            pin = t.get("pin", [])

            # us-events keyed for offense matching (forme-normalised target)
            us_ev = {(e["mv"], _base(e.get("tg"))): e for e in ev if e["sd"] == "us"}

            # ---- OFFENSE: predicted damage_output % vs actual d (cap at h0) ----
            # ---- TURN ORDER: predicted pos X/4 vs actual rank (full turns) ----
            full_turn = (len(ev) == 4)
            for d in t.get("dec", []):
                ch, ct = d.get("ch"), d.get("ct")
                sl = d.get("sl")
                actor = my[sl]["s"] if (sl is not None and sl < len(my)) else None
                chosen = next((a for a in d.get("acts", []) if a.get("lb") == ch), None)
                if not chosen:
                    continue
                reasons = " ".join(chosen.get("r", []))

                if full_turn and actor:
                    pm = POS_RE.search(reasons)
                    e = us_ev.get((ch, _base(ct))) or next(
                        (x for x in ev if x["sd"] == "us" and _base(x["a"]) == _base(actor)
                         and x["mv"] == ch), None)
                    # Skip turns where a Protect/Endure-type move (non-threatening,
                    # +priority) resolved before our mon: it jumping ahead doesn't
                    # mean we were slow, so it shouldn't count as a miss.  Real
                    # speed mispredictions (no priority move ahead) are still scored.
                    blocked_ahead = (e is not None and any(
                        x["o"] < e["o"] and x["mv"] in _NONTHREAT_FIRST for x in ev))
                    if pm and e is not None and not blocked_ahead:
                        predicted_pos = int(pm.group(1))
                        actual_pos = e["o"] + 1
                        diff = abs(actual_pos - predicted_pos)
                        to_total += 1
                        to_exact += diff == 0
                        to_off1 += diff == 1
                        to_worse += diff >= 2
                        if diff >= 1:
                            to_miss.append((diff, actor, ch, predicted_pos, actual_pos))

                if ch == "Protect" or not ct:
                    continue
                md = DMG_RE.search(reasons)
                e = us_ev.get((ch, _base(ct)))
                if not (md and e and not e.get("cr")):
                    continue
                # `damage_output` is % of the opponent's CURRENT HP (the calc
                # overrides the HP denominator with observed current HP), but the
                # logged `d` is % of MAX HP.  A Roosting / chipped target would
                # otherwise look badly over-predicted (e.g. 60% of a 48%-HP mon
                # vs 14% of max).  Scale the prediction to % of max by ×h0 (the
                # pre-hit HP fraction), capping the per-current fraction at 1.0.
                h0 = e.get("h0", 1.0) or 1.0
                pred = min(int(md.group(1)) / 100.0, 1.0) * h0
                z = e.get("z")
                if z == "immune":
                    # We predicted damage but the target was IMMUNE — a wrong
                    # assumed ability (or type) gap, NOT noise.  Surface it.
                    off_immune.append((pred, ch, ct, e.get("za")))
                elif z in ("miss", "protect", "sub"):
                    continue                       # genuine non-connect — drop
                elif e.get("h0", 0) > 0 and e.get("d") and e["d"] > 0:
                    # Real connecting hit.  (Untagged 0-damage from older logs or
                    # a switch-away still falls through here and is skipped.)
                    act = e["d"]
                    off_total += 1
                    if abs(act - pred) <= slop:
                        off_within += 1
                    else:
                        off_miss.append((act - pred, actor, ch, ct, pred, act))

            # ---- DEFENSE: actual incoming vs predicted, per ACTUAL move -------
            # pin: [{"a": attacker, "df": defender, "mvs": {move: pred_frac}}]
            our_bases = {_base(m["s"]) for m in my}
            for e in ev:
                if e["sd"] != "opp" or _base(e.get("tg")) not in our_bases:
                    continue
                if e.get("d") is None or e.get("cr") or e.get("h0", 1) <= 0:
                    continue                      # skip misses (no d) and crits
                defender, attacker, mv, act = e["tg"], e["a"], e["mv"], e["d"]
                entry = next((p for p in pin if _base(p["df"]) == _base(defender)
                              and _base(p["a"]) == _base(attacker)), None)
                # 0.8.6+ stores per-move map "mvs"; older logs stored a single
                # scariest {"mv","p"} — fall back to that for backward compat.
                if entry and "mvs" in entry:
                    assessed = entry["mvs"]
                elif entry and "mv" in entry:
                    assessed = {entry["mv"]: entry.get("p", 0.0)}
                else:
                    assessed = {}
                if mv in assessed:
                    pred = assessed[mv]               # we assessed this exact move
                    if act - pred > slop:
                        def_under.append((act - pred, attacker, defender, mv, pred, act, "known"))
                else:
                    # move we never assessed (off-meta tech, or below usage cutoff)
                    worst = max(assessed.values()) if assessed else 0.0
                    if act - worst > slop:
                        def_under.append((act - worst, attacker, defender, mv, None, act, "tech"))

    return {
        "off_within": off_within, "off_total": off_total,
        "off_miss": off_miss, "off_immune": off_immune,
        "def_under": def_under,
        "to_miss": to_miss,
        "to_exact": to_exact, "to_off1": to_off1,
        "to_worse": to_worse, "to_total": to_total,
    }


def prediction_report(games, slop=0.15):
    """Print the prediction-accuracy sections (offense / turn-order / defense /
    immunity) for a pre-loaded *games* list (console format)."""
    s = compute_prediction(games, slop)
    off_within, off_total = s["off_within"], s["off_total"]
    off_miss, off_immune = s["off_miss"], s["off_immune"]
    def_under = s["def_under"]
    to_exact, to_off1, to_worse, to_total = s["to_exact"], s["to_off1"], s["to_worse"], s["to_total"]

    # ── 1. HIGH-LEVEL ────────────────────────────────────────────────────────
    print(f"\n── PREDICTION ACCURACY ──")
    if off_total:
        print(f" Offense  : {off_within}/{off_total} damage predictions within "
              f"±{int(slop*100)}%  ({off_within/off_total:.0%})  |  {len(off_miss)} mis-models")
    if to_total:
        print(f" TurnOrder: {to_exact}/{to_total} exact ({to_exact/to_total:.0%}), "
              f"±1 {to_off1/to_total:.0%}, off-by-2+ {to_worse/to_total:.0%}")
    n_known = sum(1 for c in def_under if c[6] == "known")
    n_tech = sum(1 for c in def_under if c[6] == "tech")
    print(f" Defense  : {len(def_under)} cases hit harder than predicted by "
          f">{int(slop*100)}% (crits/misses excluded) — {n_known} on assessed "
          f"moves (model gaps), {n_tech} on unassessed moves (tech/off-meta)")
    if off_immune:
        print(f" Immunity : {len(off_immune)} times we predicted damage on an "
              f"IMMUNE target (wrong assumed ability/type)")

    # ── 2. TURN ORDER ────────────────────────────────────────────────────────
    print(f"\n── TURN ORDER (full 4-move turns, n={to_total}) ──")
    if to_total:
        print(f"   exact position : {to_exact:4} ({to_exact/to_total:.0%})")
        print(f"   off by 1       : {to_off1:4} ({to_off1/to_total:.0%})")
        print(f"   off by 2+      : {to_worse:4} ({to_worse/to_total:.0%})   <- real misses")

    # ── 3. PER-CASE: defensive under-predictions (the danger cases) ──────────
    print(f"\n── DEFENSIVE UNDER-PREDICTIONS (attacker's MOVE -> defender: predicted | actual) ──")
    print(f"   [known] = move we assessed but under-rated (model gap)   "
          f"[TECH] = move we never assessed (off-meta)")
    if not def_under:
        print("   none — every incoming hit was within prediction + slop.")
    for err, atk, dfd, mv, pred, act, kind in sorted(def_under, key=lambda x: -x[0]):
        if kind == "known":
            print(f"   [known] {atk:14} {mv:16} -> {dfd:12} predicted {pred:>4.0%} | actual {act:>4.0%}  (+{err:.0%})")
        else:
            print(f"   [TECH ] {atk:14} {mv:16} -> {dfd:12} NOT ASSESSED        | actual {act:>4.0%}")

    # offense mis-models, secondary
    if off_miss:
        print(f"\n── OFFENSE MIS-MODELS (move -> target: predicted | actual) ──")
        for err, our_mon, mv, tg, pred, act in sorted(off_miss, key=lambda x: -abs(x[0])):
            sign = "over" if err < 0 else "under"
            print(f"   {our_mon:14} {mv:16} -> {tg:14} predicted {pred:>4.0%} | "
                  f"actual {act:>4.0%}  [{sign} {abs(err):.0%}]")

    # immunity model gaps — we fired into an immune target (wrong assumed ability)
    if off_immune:
        print(f"\n── IMMUNITY MODEL GAPS (predicted damage on an IMMUNE target) ──")
        print(f"   we chose this move expecting damage, but the target was immune")
        for pred, mv, tg, abil in sorted(off_immune, key=lambda x: -x[0]):
            why = f"ability: {abil}" if abil else "type immunity"
            print(f"   {mv:16} -> {tg:14} predicted {pred:>4.0%} | IMMUNE ({why})")
    print()


def report(version, slop=0.15, team_version=None):
    """Standalone prediction-accuracy report for a version (optionally a single
    team-version)."""
    games = _load(version, team_version)
    if not games:
        print(f"No battle logs found for version {version}"
              f"{'/' + team_version if team_version else ''}.")
        return
    wins = sum(1 for g in games if g.get("outcome") == "win")
    label = f"v{version}" + (f"/{team_version}" if team_version else "")
    print(f"\n{'='*64}\n ACCURACY REPORT — {label}  ({len(games)} games)\n{'='*64}")
    print(f" Win rate: {wins}-{len(games)-wins}  ({wins/len(games):.0%})")
    prediction_report(games, slop)


if __name__ == "__main__":
    # The report uses box-drawing glyphs; force UTF-8 so it doesn't crash on the
    # Windows cp1252 console.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = sys.argv[1:]
    ver = args[0] if args and not args[0].startswith("--") else None
    slop = 0.15
    if "--slop" in args:
        slop = float(args[args.index("--slop") + 1])
    team_version = args[args.index("--team") + 1] if "--team" in args else None
    if not ver:
        print("usage: accuracy_report.py <version> [--team v2] [--slop 0.15]")
        sys.exit(1)
    report(ver, slop, team_version)
