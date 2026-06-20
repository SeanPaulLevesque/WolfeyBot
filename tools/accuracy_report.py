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
from data.moves import move_priority, move_category, move_type
from decision.modules import _assumed_ability

DMG_RE = re.compile(r"damage_output: (\d+)% HP")
POS_RE = re.compile(r"pos (\d)/4")


def _eff_priority(species, mv):
    """Move priority including ability (Prankster +1 on status, Gale Wings +1 on
    Flying) — used to tell a priority-driven turn-order miss from a speed one."""
    pr = move_priority(mv)
    ab = _assumed_ability(_base(species)) or ""
    if ab == "Prankster" and move_category(mv) == "Status":
        pr += 1
    elif ab == "Gale Wings" and move_type(mv) == "Flying":
        pr += 1
    return pr


def _classify_turn_order(ev, our_o, our_mv, our_actor, tr, paralyzed):
    """Disposition for a turn-order misread: 'gap' (genuine speed misread) or an
    'accepted: <reason>' (priority bracket / Trick Room / paralysis explains it)."""
    our_pr = _eff_priority(our_actor, our_mv)
    ahead = [x for x in ev if x["o"] < our_o]
    behind = [x for x in ev if x["o"] > our_o]
    if any(_eff_priority(x["a"], x["mv"]) > our_pr for x in ahead):
        return "accepted: priority (higher-priority move resolved ahead)"
    if any(_eff_priority(x["a"], x["mv"]) < our_pr for x in behind):
        return "accepted: priority (lower-priority move resolved behind)"
    if tr:
        return "accepted: trick room (speed order inverted)"
    if paralyzed:
        return "accepted: paralysis (our speed halved)"
    return "gap"

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

    Every per-case row carries a trailing *disposition*: ``"gap"`` (actionable
    model error) or ``"accepted: <reason>"`` (explained / correct behaviour).
    Returns keys: ``off_within``/``off_total``; ``off_miss``
    [(err,our_mon,mv,tg,pred,act,disp)]; ``off_immune`` [(pred,mv,tg,ability,disp)];
    ``def_under`` [(err,atk,def,mv,pred,act,disp)]; ``to_miss`` [dict w/ ``disposition``];
    and turn-order ``to_exact``/``to_off1``/``to_worse``/``to_total``."""
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
                            opp_l = t.get("opp", [])

                            def _slot_label(e2, _my=my, _opp=opp_l):
                                spx = _base(e2.get("a"))
                                seq = _my if e2.get("sd") == "us" else _opp
                                pre = "my" if e2.get("sd") == "us" else "opp"
                                for i, mm in enumerate(seq):
                                    if mm and _base(mm.get("s")) == spx:
                                        return f"{pre}[{'ab'[i]}]" if i < 2 else f"{pre}[{i}]"
                                return f"{pre}:{spx or '?'}"

                            paralyzed = (my[sl].get("sts") == "par"
                                         if (sl is not None and sl < len(my)) else False)
                            to_miss.append({
                                "diff": diff,
                                "turn": t.get("n"),
                                "mon": f"my[{'ab'[sl]}]" if (sl is not None and sl < 2) else (actor or "?"),
                                "pred_pos": predicted_pos,
                                "act_pos": actual_pos,
                                "my": [_base(m.get("s")) for m in my],
                                "opp": [_base(o.get("s")) for o in opp_l],
                                "tr": bool(t.get("tr")),
                                "tw": t.get("tw") or {},
                                "order": [_slot_label(x) for x in sorted(ev, key=lambda z: z["o"])],
                                "disposition": _classify_turn_order(
                                    ev, e["o"], ch, actor, bool(t.get("tr")), paralyzed),
                            })

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
                    # Disposition: a >0% prediction into an immune target is a real
                    # gap (wrong assumed ability/type).  A 0% prediction is correct
                    # and the move was forced — a Choice-locked attacker with the
                    # immune mon as its sole surviving target — so it's accepted.
                    disp = ("gap" if pred > 0 else
                            "accepted: forced (0% predicted, Choice-locked into sole immune target)")
                    off_immune.append((pred, ch, ct, e.get("za"), disp))
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
                        # Disposition defaults to 'gap'; specific accepted rules
                        # are added as offense buckets are investigated.
                        off_miss.append((act - pred, actor, ch, ct, pred, act, "gap"))

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
                        # We assessed this move but under-rated it -> real gap.
                        def_under.append((act - pred, attacker, defender, mv, pred, act, "gap"))
                else:
                    # Move we never assessed (off-meta tech / below usage cutoff):
                    # accepted as a coverage limit, tracked separately.
                    worst = max(assessed.values()) if assessed else 0.0
                    if act - worst > slop:
                        def_under.append((act - worst, attacker, defender, mv, None, act,
                                          "accepted: unassessed move (off-meta / below usage cutoff)"))

    return {
        "off_within": off_within, "off_total": off_total,
        "off_miss": off_miss, "off_immune": off_immune,
        "def_under": def_under,
        "to_miss": to_miss,
        "to_exact": to_exact, "to_off1": to_off1,
        "to_worse": to_worse, "to_total": to_total,
    }


def _gap(disp):
    return disp == "gap"


def prediction_report(games, slop=0.15):
    """Print the prediction-accuracy sections (offense / turn-order / defense /
    immunity) for a pre-loaded *games* list (console format).  Each case carries a
    disposition — `gap` (actionable) or `accepted: <reason>` — and the headline
    counts only gaps."""
    s = compute_prediction(games, slop)
    off_miss, off_immune, def_under, to_miss = (
        s["off_miss"], s["off_immune"], s["def_under"], s["to_miss"])
    to_total, to_worse = s["to_total"], s["to_worse"]

    def gaps(lst, idx):
        return sum(1 for c in lst if c[idx] == "gap")
    def_gap = gaps(def_under, 6)
    off_gap = gaps(off_miss, 6)
    imm_gap = gaps(off_immune, 4)
    to_gap = sum(1 for m in to_miss if m["disposition"] == "gap")

    print(f"\n── PREDICTION ACCURACY (gaps = actionable; accepted = explained) ──")
    print(f" Offense  : {len(off_miss):3} mis-models ({off_gap} gaps)")
    print(f" Defense  : {len(def_under):3} mis-models ({def_gap} gaps)")
    print(f" TurnOrder: {len(to_miss):3} misreads  ({to_gap} gaps); off-by-2+ {to_worse}")
    print(f" Immunity : {len(off_immune):3} cases     ({imm_gap} gaps)")

    def _section(title, rows, fmt):
        print(f"\n── {title} ──")
        if not rows:
            print("   none.")
            return
        for r in rows:
            print(fmt(r))

    _section("DEFENSIVE MIS-MODEL (attacker MOVE -> defender)",
             sorted(def_under, key=lambda x: (x[6] != "gap", -x[0])),
             lambda r: f"   [{'GAP' if r[6]=='gap' else 'acc'}] {r[1]:14} {r[3]:16} -> {r[2]:12} "
                       f"pred {('%4.0f%%'%(r[4]*100)) if r[4] is not None else ' n/a'} | "
                       f"act {r[5]:>4.0%}" + ("" if r[6]=='gap' else f"  ({r[6]})"))

    _section("OFFENSIVE MIS-MODEL (our_mon MOVE -> target)",
             sorted(off_miss, key=lambda x: (x[6] != "gap", -abs(x[0]))),
             lambda r: f"   [{'GAP' if r[6]=='gap' else 'acc'}] {r[1]:14} {r[2]:16} -> {r[3]:14} "
                       f"pred {r[4]:>4.0%} | act {r[5]:>4.0%} [{'over' if r[0]<0 else 'under'}]"
                       + ("" if r[6]=='gap' else f"  ({r[6]})"))

    _section(f"TURN ORDER (off-by-2+ misreads, full turns n={to_total})",
             sorted([m for m in to_miss if m["diff"] >= 2],
                    key=lambda m: (m["disposition"] != "gap", -m["diff"])),
             lambda m: f"   [{'GAP' if m['disposition']=='gap' else 'acc'}] {m['mon']} {m['pred_pos']}/4->"
                       f"{m['act_pos']}/4  order: {' > '.join(m['order'])}"
                       + ("" if m["disposition"]=="gap" else f"  ({m['disposition']})"))

    _section("IMMUNITY (move -> immune target)",
             sorted(off_immune, key=lambda x: (x[4] != "gap", -x[0])),
             lambda r: f"   [{'GAP' if r[4]=='gap' else 'acc'}] {r[1]:16} -> {r[2]:14} "
                       f"pred {r[0]:>4.0%}" + ("" if r[4]=='gap' else f"  ({r[4]})"))
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
