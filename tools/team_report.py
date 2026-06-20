"""tools/team_report.py — Combined roster-performance + prediction-accuracy
report from instrumented battle logs.

One report per version (optionally a single named-team version), covering:

  1. ROSTER       — per-mon bring rate, lead rate, win-rate-when-brought, KOs
                    dealt, faints suffered, net (KO − faint).
  2. MOVE USAGE   — how often each move was actually chosen, per mon; the
                    least-used move is flagged as a dead-weight / swap candidate.
  3. GAME LENGTH  — W/L bucketed by number of turns (do we win fast / lose long?).
  4. PREDICTION   — offense / turn-order / defensive accuracy + per-case misses,
                    reused verbatim from tools/accuracy_report.

The compute helpers (``roster_stats`` / ``move_usage`` / ``length_buckets``)
return plain dicts and take a pre-loaded games list, so they're unit-tested in
tests/test_team_report.py without touching the filesystem.

Usage (from repo root):
    .venv\\Scripts\\python.exe tools/team_report.py 0.17.0
    .venv\\Scripts\\python.exe tools/team_report.py 0.17.0 --team v2 --slop 0.15

Caveats: KO attribution uses a damage≥remaining-HP heuristic and spread moves log
only their first target, so KO/faint counts are approximate.  Win-rate-when-
brought is subject to selection bias (a rarely-brought mon is brought only in
favourable matchups).
"""
import os
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import base_forme
# Reuse the loader + prediction analysis from the accuracy report (no dup logic).
from tools.accuracy_report import _load, prediction_report

# Switch / Protect-family labels are decisions, not damaging move uses.
_PROTECTS = frozenset({
    "Protect", "Detect", "King's Shield", "Spiky Shield", "Baneful Bunker",
    "Silk Trap", "Burning Bulwark", "Wide Guard", "Quick Guard", "Max Guard",
    "Obstruct",
})


def _len_bucket(nturns):
    return "1-3" if nturns <= 3 else "4-6" if nturns <= 6 else "7-9" if nturns <= 9 else "10+"


def roster_stats(games):
    """Return ``{species: {...}}`` of per-mon performance over *games*.

    Keys per mon: bring, lead, games_brought, wins_brought, kos, faints.
    KO = one of our hits whose damage removed the target's remaining HP
    (``d >= h0``); faint = our mon observed at 0 HP (counted once per game)."""
    stats = collections.defaultdict(lambda: dict(
        bring=0, lead=0, games_brought=0, wins_brought=0, kos=0, faints=0))
    for g in games:
        win = g.get("outcome") == "win"
        turns = g.get("turns", [])
        t0 = turns[0] if turns else {}
        brought = {base_forme(m["s"]) for m in t0.get("team", []) if m}
        leads = {base_forme(m["s"]) for m in t0.get("my", []) if m}
        for sp in brought:
            stats[sp]["bring"] += 1
            stats[sp]["games_brought"] += 1
            if win:
                stats[sp]["wins_brought"] += 1
        for sp in leads:
            stats[sp]["lead"] += 1
        fainted_seen = set()
        for t in turns:
            for m in t.get("my", []):
                if m and m.get("hp", 1) <= 0:
                    sp = base_forme(m["s"])
                    if sp not in fainted_seen:
                        stats[sp]["faints"] += 1
                        fainted_seen.add(sp)
            for e in t.get("ev", []):
                if e.get("sd") != "us":
                    continue
                d, h0 = e.get("d"), e.get("h0")
                if d is not None and h0 and d >= h0 - 0.02:
                    stats[base_forme(e.get("a"))]["kos"] += 1
    return dict(stats)


def move_usage(games):
    """Return ``{species: Counter(move -> times_chosen)}`` from each turn's chosen
    action (``dec[].ch``), excluding switches."""
    use = collections.defaultdict(collections.Counter)
    for g in games:
        for t in g.get("turns", []):
            my = t.get("my", [])
            for d in t.get("dec", []):
                sl, ch = d.get("sl"), d.get("ch", "")
                if (sl is not None and sl < len(my) and my[sl]
                        and ch and not ch.startswith("Switch")):
                    use[base_forme(my[sl]["s"])][ch] += 1
    return {sp: dict(c) for sp, c in use.items()}


def length_buckets(games):
    """Return ``{bucket: [wins, total]}`` keyed by turn-count bucket."""
    out = collections.OrderedDict((b, [0, 0]) for b in ("1-3", "4-6", "7-9", "10+"))
    for g in games:
        if g.get("outcome") not in ("win", "loss"):
            continue
        b = _len_bucket(len(g.get("turns", [])))
        out[b][1] += 1
        if g.get("outcome") == "win":
            out[b][0] += 1
    return out


# ── Printing ──────────────────────────────────────────────────────────────────

def print_team_report(version, team_version=None, slop=0.15):
    games = _load(version, team_version)
    if not games:
        print(f"No battle logs found for version {version}"
              f"{'/' + team_version if team_version else ''}.")
        return
    nG = len(games)
    wins = sum(1 for g in games if g.get("outcome") == "win")
    label = f"v{version}" + (f"/{team_version}" if team_version else "")
    print(f"\n{'='*78}\n TEAM REPORT — {label}  ({nG} games)\n{'='*78}")
    print(f" Win rate: {wins}-{nG-wins}  ({wins/nG:.0%})")

    # 1. ROSTER
    stats = roster_stats(games)
    print(f"\n── ROSTER (sorted by net KO − faint) ──")
    print(f"  {'mon':16}{'bring':>7}{'lead':>6}{'WR|br':>7}{'KOs':>5}{'faints':>8}{'net':>6}")
    for sp in sorted(stats, key=lambda s: -(stats[s]["kos"] - stats[s]["faints"])):
        d = stats[sp]
        gb = d["games_brought"] or 1
        print(f"  {sp:16}{d['bring']/nG:>6.0%}{d['lead']/nG:>6.0%}"
              f"{d['wins_brought']/gb:>7.0%}{d['kos']:>5}{d['faints']:>8}"
              f"{d['kos']-d['faints']:>+6}")

    # 2. MOVE USAGE
    use = move_usage(games)
    print(f"\n── MOVE USAGE (times chosen; lowest flagged as swap candidate) ──")
    for sp in sorted(use, key=lambda s: -stats.get(s, {}).get("bring", 0)):
        items = sorted(use[sp].items(), key=lambda kv: -kv[1])
        if not items:
            continue
        lo = min(items, key=lambda kv: kv[1])
        body = ", ".join(f"{m} {c}" for m, c in items)
        print(f"  {sp:14} lowest=[{lo[0]} {lo[1]}]  |  {body}")

    # 3. GAME LENGTH
    print(f"\n── W/L BY GAME LENGTH (turns) ──")
    for b, (w, n) in length_buckets(games).items():
        if n:
            print(f"  {b:5} turns: {w:2}W-{n-w:2}L  ({w/n:.0%})   n={n}")

    # 4. PREDICTION ACCURACY (reused from accuracy_report)
    prediction_report(games, slop)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = sys.argv[1:]
    ver = args[0] if args and not args[0].startswith("--") else None
    slop = float(args[args.index("--slop") + 1]) if "--slop" in args else 0.15
    tv = args[args.index("--team") + 1] if "--team" in args else None
    if not ver:
        print("usage: team_report.py <version> [--team v2] [--slop 0.15]")
        sys.exit(1)
    print_team_report(ver, tv, slop)
