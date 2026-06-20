"""tools/team_report.py — Combined roster-performance + prediction-accuracy
report from instrumented battle logs, rendered as GitHub-flavoured Markdown.

Point it at a directory (or glob) of battle-log JSON files; it processes every
log it finds (recursively), optionally filtered to one named-team version.

Sections:
  1. ROSTER       — per-mon bring/lead rate, win-rate-when-brought, KOs, faints, net.
  2. MOVE USAGE   — how often each move was chosen, per mon; least-used flagged.
  3. GAME LENGTH  — W/L bucketed by number of turns.
  4. PREDICTION   — offense / turn-order / defensive accuracy (from accuracy_report).

The compute helpers (``roster_stats`` / ``move_usage`` / ``length_buckets`` /
``load_games``) are pure and unit-tested in tests/test_team_report.py.

Usage (from repo root):
    # a version's logs (the usual layout under Battle Data/)
    .venv\\Scripts\\python.exe tools/team_report.py "Battle Data/0.17.0" --team v2
    # any folder of logs, write Markdown to a file
    .venv\\Scripts\\python.exe tools/team_report.py path/to/logs --out report.md

Caveats: KO attribution uses a damage≥remaining-HP heuristic and spread moves log
only their first target, so KO/faint counts are approximate.  Win-rate-when-
brought is subject to selection bias (a rarely-brought mon is brought only in
favourable matchups).
"""
import os
import sys
import glob
import json
import collections

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import base_forme
# Reuse the prediction analysis from the accuracy report (no duplicated logic).
from tools.accuracy_report import compute_prediction


def find_log_files(path, team_version=None):
    """Return the battle-log JSON file paths under *path* (a directory or glob),
    recursively; if *team_version* is given keep only those with a
    ``/<team_version>/`` path segment."""
    if os.path.isdir(path):
        files = glob.glob(os.path.join(path, "**", "*.json"), recursive=True)
    else:
        files = glob.glob(path, recursive=True)
    if team_version:
        seg = os.sep + team_version + os.sep
        files = [f for f in files if seg in f]
    return sorted(files)


def load_games(path, team_version=None):
    """Load every battle-log JSON under *path* (see :func:`find_log_files`)."""
    return [json.load(open(f, encoding="utf-8")) for f in find_log_files(path, team_version)]


def derive_team_meta(files):
    """Best-effort ``(team_name, team_version)`` from the log paths.

    Named-team runs nest as ``Battle Data/<version>/<team>/<tv>/<file>.json``, so
    the two path segments between the version and the filename are the team name
    and version.  Returns ``(None, None)`` for flat/baseline layouts."""
    for f in files:
        parts = f.replace("\\", "/").split("/")
        if "Battle Data" in parts:
            i = parts.index("Battle Data")
            segs = parts[i + 2:-1]          # between <version> and the filename
            if len(segs) >= 2:
                return segs[0], segs[1]
    return None, None


def load_paste(team_name, team_version):
    """Return the verbatim team paste from ``teams/<name>/<tv>.txt``, or None."""
    if not team_name or not team_version:
        return None
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(root, "teams", team_name, f"{team_version}.txt")
    if os.path.isfile(p):
        return open(p, encoding="utf-8").read().strip()
    return None


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
    """Return ``{species: {move: times_chosen}}`` from each turn's chosen action
    (``dec[].ch``), excluding switches."""
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


# ── Markdown rendering ──────────────────────────────────────────────────────────

def _pct(x):
    return f"{x*100:.0f}%"


def build_markdown(games, label, slop=0.15, team_name=None, team_version=None,
                   team_paste=None):
    """Render the full report for *games* as a GitHub-flavoured Markdown string.

    *team_name*/*team_version*/*team_paste* (optional) record which roster these
    logs came from; the engine version(s) are read from the logs themselves."""
    nG = len(games)
    wins = sum(1 for g in games if g.get("outcome") == "win")
    versions = sorted({g.get("v") for g in games if g.get("v")})
    title = team_name or label
    if team_version:
        title += f" {team_version}"
    out = []
    out.append(f"# Team Report - {title}")
    out.append("")
    meta = [f"**Games:** {nG}",
            f"**Win rate:** {wins}-{nG-wins} ({_pct(wins/nG) if nG else 'n/a'})",
            f"**Engine:** {', '.join('v' + v for v in versions) if versions else 'unknown'}"]
    out.append(" | ".join(meta))
    out.append("")
    out.append(f"*Source: `{label}`*")

    # 0. TEAM
    if team_paste:
        out += ["", "## Team", "", "```", team_paste, "```"]

    # 1. ROSTER
    stats = roster_stats(games)
    out += ["", "## Roster", "",
            "Sorted by net (KOs - faints). *WR (brought)* is subject to selection bias.",
            "",
            "| Mon | Bring | Lead | WR (brought) | KOs | Faints | Net |",
            "|---|--:|--:|--:|--:|--:|--:|"]
    for sp in sorted(stats, key=lambda s: -(stats[s]["kos"] - stats[s]["faints"])):
        d = stats[sp]
        gb = d["games_brought"] or 1
        net = d["kos"] - d["faints"]
        out.append(f"| {sp} | {_pct(d['bring']/nG)} | {_pct(d['lead']/nG)} | "
                   f"{_pct(d['wins_brought']/gb)} | {d['kos']} | {d['faints']} | "
                   f"{net:+d} |")

    # 2. MOVE USAGE
    use = move_usage(games)
    out += ["", "## Move usage", "",
            "Times each move was chosen (excludes switches). **Lowest** = swap candidate.",
            "",
            "| Mon | Moves (chosen count) | Lowest |",
            "|---|---|---|"]
    for sp in sorted(use, key=lambda s: -stats.get(s, {}).get("bring", 0)):
        items = sorted(use[sp].items(), key=lambda kv: -kv[1])
        if not items:
            continue
        lo = min(items, key=lambda kv: kv[1])
        body = ", ".join(f"{m} {c}" for m, c in items)
        out.append(f"| {sp} | {body} | **{lo[0]} {lo[1]}** |")

    # 3. GAME LENGTH
    out += ["", "## Game length", "",
            "| Turns | Record | Win rate |",
            "|---|---|--:|"]
    for b, (w, n) in length_buckets(games).items():
        if n:
            out.append(f"| {b} | {w}-{n-w} | {_pct(w/n)} |")

    # 4. PREDICTION ACCURACY
    s = compute_prediction(games, slop)
    pct = int(slop * 100)
    n_known = sum(1 for c in s["def_under"] if c[6] == "known")
    n_tech = sum(1 for c in s["def_under"] if c[6] == "tech")
    out += ["", "## Prediction accuracy", ""]
    summ = []
    if s["off_total"]:
        summ.append(f"**Offense** {_pct(s['off_within']/s['off_total'])} "
                    f"({s['off_within']}/{s['off_total']} within +/-{pct}%, "
                    f"{len(s['off_miss'])} mis-models)")
    if s["to_total"]:
        summ.append(f"**Turn order** {_pct(s['to_exact']/s['to_total'])} exact "
                    f"(+/-1 {_pct(s['to_off1']/s['to_total'])}, "
                    f"off-by-2+ {_pct(s['to_worse']/s['to_total'])})")
    summ.append(f"**Defense** {len(s['def_under'])} under-predictions "
                f"({n_known} model gaps, {n_tech} tech)")
    if s["off_immune"]:
        summ.append(f"**Immunity** {len(s['off_immune'])} fired into immune target")
    out.append(" | ".join(summ))

    if s["def_under"]:
        out += ["", "### Defensive under-predictions",
                "*Took >slop more than predicted (crits/misses excluded). "
                "`known` = assessed move under-rated; `tech` = move never assessed.*",
                "",
                "| Attacker | Move | vs Defender | Predicted | Actual | Delta | Kind |",
                "|---|---|---|--:|--:|--:|---|"]
        for err, atk, dfd, mv, pred, act, kind in sorted(s["def_under"], key=lambda x: -x[0]):
            pstr = _pct(pred) if pred is not None else "n/a"
            out.append(f"| {atk} | {mv} | {dfd} | {pstr} | {_pct(act)} | "
                       f"+{_pct(err)} | {kind} |")

    if s["off_miss"]:
        out += ["", "### Offense mis-models",
                "*Our predicted damage vs actual (|error| > slop).*",
                "",
                "| Move | vs Target | Predicted | Actual | Error |",
                "|---|---|--:|--:|---|"]
        for err, mv, tg, pred, act in sorted(s["off_miss"], key=lambda x: -abs(x[0])):
            sign = "over" if err < 0 else "under"
            out.append(f"| {mv} | {tg} | {_pct(pred)} | {_pct(act)} | "
                       f"{sign} {_pct(abs(err))} |")

    if s["off_immune"]:
        out += ["", "### Immunity gaps",
                "*Chose a move expecting damage, but the target was immune.*",
                "",
                "| Move | vs Target | Why |",
                "|---|---|---|"]
        for pred, mv, tg, abil in sorted(s["off_immune"], key=lambda x: -x[0]):
            out.append(f"| {mv} | {tg} | {('ability: ' + abil) if abil else 'type immunity'} |")

    out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    path = args[0] if args and not args[0].startswith("--") else None
    slop = float(args[args.index("--slop") + 1]) if "--slop" in args else 0.15
    tv = args[args.index("--team") + 1] if "--team" in args else None
    out_file = args[args.index("--out") + 1] if "--out" in args else None
    if not path:
        print("usage: team_report.py <logs-dir|glob> [--team v2] [--slop 0.15] [--out report.md]")
        sys.exit(1)
    files = find_log_files(path, tv)
    games = [json.load(open(f, encoding="utf-8")) for f in files]
    if not games:
        print(f"No battle logs found under {path}" + (f" (team {tv})" if tv else "") + ".")
        sys.exit(1)
    team_name, derived_tv = derive_team_meta(files)
    team_version = tv or derived_tv
    paste = load_paste(team_name, team_version)
    label = path + (f" - team {tv}" if tv else "")
    md = build_markdown(games, label, slop, team_name, team_version, paste)
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Wrote {out_file} ({len(games)} games).")
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print(md)
