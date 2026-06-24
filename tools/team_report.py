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

    Keys per mon: bring, lead, games_brought, wins_brought, wins_led, kos, faints.
    KO = one of our hits whose damage removed the target's remaining HP
    (``d >= h0``); faint = our mon observed at 0 HP (counted once per game).
    ``wins_led`` enables WR-when-led, separating lead value from bring value."""
    stats = collections.defaultdict(lambda: dict(
        bring=0, lead=0, games_brought=0, wins_brought=0, wins_led=0, kos=0, faints=0))
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
            if win:
                stats[sp]["wins_led"] += 1
        # Faint detection (once per game per mon).  A fainted mon is replaced by
        # its switch-in before the next decision snapshot, so scanning `my` for
        # hp<=0 almost never catches it — count faints the same way KOs are
        # counted: an *incoming* hit that removed our mon's remaining HP
        # (d >= h0).  The hp<=0 snapshot is kept as a fallback for the rarer
        # residual/recoil faints (no attacker event) that linger in a
        # force-switch snapshot.
        fainted_seen = set()
        for t in turns:
            for m in t.get("my", []):
                if m and m.get("hp", 1) <= 0:
                    sp = base_forme(m["s"])
                    if sp not in fainted_seen:
                        stats[sp]["faints"] += 1
                        fainted_seen.add(sp)
            for e in t.get("ev", []):
                d, h0 = e.get("d"), e.get("h0")
                lethal = d is not None and h0 and d >= h0 - 0.02
                if e.get("sd") == "us":
                    if lethal:
                        stats[base_forme(e.get("a"))]["kos"] += 1
                elif e.get("sd") == "opp" and lethal:
                    sp = base_forme(e.get("tg"))
                    if sp not in fainted_seen:
                        stats[sp]["faints"] += 1
                        fainted_seen.add(sp)
    return dict(stats)


def lead_outcomes(games, opening_turns=3):
    """Assess lead/opening decisions (not just per-mon descriptive stats).

    Returns ``{"pairs": [...], "opening": {...}}``:
    * ``pairs`` — per lead PAIR (the two turn-1 actives, base-forme, order-
      independent): games, wins, win rate. Shows which openings the engine
      picks and how they fare.
    * ``opening`` — the opening exchange over the first *opening_turns* turns:
      our KOs vs our faints (same d>=h0 attribution as the roster), the net,
      and win rate split by whether we came out of the opening ahead (net>0),
      even (net==0), or behind (net<0). This is the closest read on whether the
      lead engine is choosing good openings, independent of late-game play.
    """
    pairs = collections.defaultdict(lambda: dict(games=0, wins=0))
    ahead = collections.defaultdict(lambda: dict(games=0, wins=0))  # sign -> rec
    tot_kos = tot_faints = 0
    for g in games:
        win = g.get("outcome") == "win"
        turns = g.get("turns", [])
        if not turns:
            continue
        leads = tuple(sorted({base_forme(m["s"]) for m in turns[0].get("my", []) if m}))
        if len(leads) == 2:
            pairs[leads]["games"] += 1
            pairs[leads]["wins"] += win
        kos = faints = 0
        for t in turns[:opening_turns]:
            for e in t.get("ev", []):
                d, h0 = e.get("d"), e.get("h0")
                if not (d is not None and h0 and d >= h0 - 0.02):
                    continue
                if e.get("sd") == "us":
                    kos += 1
                elif e.get("sd") == "opp":
                    faints += 1
        tot_kos += kos
        tot_faints += faints
        sign = (kos > faints) - (kos < faints)   # 1 ahead / 0 even / -1 behind
        ahead[sign]["games"] += 1
        ahead[sign]["wins"] += win
    return {"pairs": dict(pairs), "opening": {
        "turns": opening_turns, "kos": tot_kos, "faints": tot_faints,
        "by_sign": dict(ahead)}}


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


# Observed-weather short keys -> archetype label (snow logs as "hail").
_WEATHER_ARCH = {"rain": "Rain", "sun": "Sun", "sand": "Sand", "hail": "Snow"}


def archetype_breakdown(games):
    """Return ``{archetype: [wins, total]}`` of W/L vs each opponent archetype.

    A game is tagged with every condition the opponent established during it, so a
    game can count toward several archetypes (e.g. Tailwind + Sun).  ``None`` is
    games where the opponent ran no Trick Room / Tailwind / weather.  Trick Room
    and weather come from the global per-turn fields (our rosters set neither, so
    they're the opponent's); Tailwind uses the opponent side specifically."""
    cats = ["Trick Room", "Tailwind", "Rain", "Sun", "Sand", "Snow", "None"]
    out = collections.OrderedDict((c, [0, 0]) for c in cats)
    for g in games:
        if g.get("outcome") not in ("win", "loss"):
            continue
        win = g.get("outcome") == "win"
        tags = set()
        for t in g.get("turns", []):
            if t.get("tr"):
                tags.add("Trick Room")
            if (t.get("tw") or {}).get("opp"):
                tags.add("Tailwind")
            w = t.get("w")
            if w in _WEATHER_ARCH:
                tags.add(_WEATHER_ARCH[w])
        if not tags:
            tags.add("None")
        for tag in tags:
            out[tag][1] += 1
            out[tag][0] += 1 if win else 0
    return out


def opp_mega_breakdown(games):
    """Return ``{mega_species: [wins, total]}`` of W/L vs each opponent mega that
    actually appeared (a mon revealed as a ``-Mega`` forme), ordered by games desc.

    `None (no mega)` = games where the opponent never mega-evolved.  A game can in
    principle count toward more than one mega, but only one mega-evolves per battle,
    so it's effectively one tag per game."""
    raw = collections.defaultdict(lambda: [0, 0])
    for g in games:
        if g.get("outcome") not in ("win", "loss"):
            continue
        win = g.get("outcome") == "win"
        if "opp_formes" in g:
            # Reliable parser-recorded list of every opponent forme that appeared
            # (0.22.0+). Preferred over reconstructing from snapshots/events.
            megas = {s for s in g["opp_formes"] if "-Mega" in s}
        else:
            # Back-compat for older logs without opp_formes: triangulate across
            # the per-turn opp snapshots, opp event actors, and our hits' targets
            # (the last catches a mega KO'd the turn it evolved, which is in
            # neither the pre-evo snapshot nor an opp actor).
            megas = {o["s"] for t in g.get("turns", []) for o in t.get("opp", [])
                     if o and "-Mega" in o.get("s", "")}
            megas |= {e["a"] for t in g.get("turns", []) for e in t.get("ev", [])
                      if e.get("sd") == "opp" and "-Mega" in str(e.get("a", ""))}
            megas |= {e["tg"] for t in g.get("turns", []) for e in t.get("ev", [])
                      if e.get("sd") == "us" and "-Mega" in str(e.get("tg", ""))}
        for k in (megas or {"None (no mega)"}):
            raw[k][1] += 1
            raw[k][0] += 1 if win else 0
    items = sorted(raw.items(),
                   key=lambda kv: (kv[0] == "None (no mega)", -kv[1][1], kv[0]))
    return collections.OrderedDict(items)


# ── Markdown rendering ──────────────────────────────────────────────────────────

def _pct(x):
    return f"{x*100:.0f}%"


def _is_forfeit(g):
    """A non-battle: the opponent never took an action (preview/turn-1 forfeit or
    timeout — e.g. a turn-1 'win').  Such games have no opponent move events and
    distort every W/L breakdown, so the report excludes them wholesale."""
    return not any(e.get("sd") == "opp"
                   for t in g.get("turns", []) for e in t.get("ev", []))


def build_markdown(games, label, slop=0.15, team_name=None, team_version=None,
                   team_paste=None):
    """Render the full report for *games* as a GitHub-flavoured Markdown string.

    *team_name*/*team_version*/*team_paste* (optional) record which roster these
    logs came from; the engine version(s) are read from the logs themselves.

    Immediate forfeits (opponent never acted) are filtered from the **entire**
    report — they aren't real battles and skew every breakdown."""
    n_forfeit = sum(1 for g in games if _is_forfeit(g))
    games = [g for g in games if not _is_forfeit(g)]
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
    if n_forfeit:
        meta.append(f"**Excluded:** {n_forfeit} immediate forfeit(s)")
    out.append(" | ".join(meta))
    out.append("")
    out.append(f"*Source: `{label}`*")

    # 0. TEAM
    if team_paste:
        out += ["", "## Team", "", "```", team_paste, "```"]

    # 1. ROSTER
    stats = roster_stats(games)
    out += ["", "## Roster", "",
            "Sorted by net (KOs - faints). KDR = KOs/faints (∞ = no faints). "
            "*WR (brought)/(led)* are subject to selection bias; compare them to "
            "the team's overall win rate, not 50%.",
            "",
            "| Mon | Bring | Lead | WR (brought) | WR (led) | KOs | Faints | Net | KDR |",
            "|---|--:|--:|--:|--:|--:|--:|--:|--:|"]
    for sp in sorted(stats, key=lambda s: -(stats[s]["kos"] - stats[s]["faints"])):
        d = stats[sp]
        gb = d["games_brought"] or 1
        net = d["kos"] - d["faints"]
        kdr = (f"{d['kos']/d['faints']:.2f}" if d["faints"]
               else ("∞" if d["kos"] else "0.00"))
        wr_led = _pct(d["wins_led"] / d["lead"]) if d["lead"] else "—"
        out.append(f"| {sp} | {_pct(d['bring']/nG)} | {_pct(d['lead']/nG)} | "
                   f"{_pct(d['wins_brought']/gb)} | {wr_led} | {d['kos']} | {d['faints']} | "
                   f"{net:+d} | {kdr} |")

    # 1b. LEADS — decision-success view (not per-mon descriptive)
    lo = lead_outcomes(games)
    op = lo["opening"]
    out += ["", "## Leads", "",
            f"Opening exchange = first {op['turns']} turns. *Ahead/even/behind* "
            "= whether our KOs out/under-paced our faints in that window; the win "
            "rate beside each shows how often the opening result held up.",
            "",
            f"**Opening KOs {op['kos']} vs faints {op['faints']}** "
            f"(net {op['kos']-op['faints']:+d} over {nG} games).",
            "",
            "| Opening result | Games | Win rate |",
            "|---|--:|--:|"]
    for sign, lbl in ((1, "ahead"), (0, "even"), (-1, "behind")):
        rec = op["by_sign"].get(sign)
        if rec and rec["games"]:
            out.append(f"| {lbl} | {rec['games']} | {_pct(rec['wins']/rec['games'])} |")
    pairs = lo["pairs"]
    if pairs:
        out += ["", "Lead pairs (order-independent), by games led:", "",
                "| Lead pair | Games | W-L | Win rate |",
                "|---|--:|--:|--:|"]
        for pr in sorted(pairs, key=lambda p: -pairs[p]["games"]):
            r = pairs[pr]; w = r["wins"]; gp = r["games"]
            out.append(f"| {' + '.join(pr)} | {gp} | {w}-{gp-w} | {_pct(w/gp)} |")

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

    # 3b. OPPONENT ARCHETYPES
    arch = archetype_breakdown(games)
    out += ["", "## Opponent archetypes", "",
            "*W/L when the opponent established each condition. A game can count in "
            "several (e.g. Tailwind + Sun); `None` = no TR/TW/weather.*", "",
            "| Archetype | Record | Win rate | Games |",
            "|---|---|--:|--:|"]
    for a, (w, n) in arch.items():
        if n:
            out.append(f"| {a} | {w}-{n-w} | {_pct(w/n)} | {n} |")

    # 3c. OPPONENT MEGAS
    megas = opp_mega_breakdown(games)
    out += ["", "## Opponent megas", "",
            "*W/L vs the opponent mega that appeared (one mega-evolves per battle); "
            "`None (no mega)` = opponent never mega-evolved.*", "",
            "| Opponent mega | Record | Win rate | Games |",
            "|---|---|--:|--:|"]
    for m, (w, n) in megas.items():
        if n:
            out.append(f"| {m} | {w}-{n-w} | {_pct(w/n)} | {n} |")

    # 4. PREDICTION ACCURACY — every case carries a disposition: `gap` (actionable
    # model error) or `accepted: <reason>` (explained / correct). The goal is to
    # drive *gaps* to zero; accepted cases stay on the ledger so the checks remain
    # visible and catch any future recurrence.
    s = compute_prediction(games, slop)

    def _ngap(rows, idx):
        return sum(1 for r in rows if r[idx] == "gap")
    off_g = _ngap(s["off_miss"], 6)
    def_g = _ngap(s["def_under"], 6)
    imm_g = _ngap(s["off_immune"], 4)
    to_g = sum(1 for m in s["to_miss"] if m["disposition"] == "gap")

    out += ["", "## Prediction accuracy", "",
            "*Each case is a **gap** (actionable) or **accepted** (explained, with "
            "reason). Goal: gaps to zero; accepted rows stay so the checks keep "
            "running.*", ""]
    out.append(
        f"**Offense** {len(s['off_miss'])} ({off_g} gaps) | "
        f"**Defense** {len(s['def_under'])} ({def_g} gaps) | "
        f"**Turn order** {len(s['to_miss'])} misreads ({to_g} gaps) | "
        f"**Immunity** {len(s['off_immune'])} ({imm_g} gaps)")

    def _disp_sort_def(x):     # gaps first, then by error size
        return (x[6] != "gap", -x[0])

    # Defensive mis-model
    if s["def_under"]:
        out += ["", "### Defensive mis-model",
                "*Incoming hits >slop above prediction (crits/misses excluded).*",
                "",
                "| Attacker | Move | vs Defender | Predicted | Actual | Disposition |",
                "|---|---|---|--:|--:|---|"]
        for err, atk, dfd, mv, pred, act, disp, loc in sorted(s["def_under"], key=_disp_sort_def):
            pstr = _pct(pred) if pred is not None else "n/a"
            out.append(f"| {atk} | {mv} | {dfd} | {pstr} | {_pct(act)} | {disp}<!-- {loc} --> |")

    # Offensive mis-model
    if s["off_miss"]:
        out += ["", "### Offensive mis-model",
                "*Our outgoing damage vs actual (|error| > slop). Dir = over/under.*",
                "",
                "| Attacker | Move | vs Target | Predicted | Actual | Dir | Disposition |",
                "|---|---|---|--:|--:|:-:|---|"]
        for err, our_mon, mv, tg, pred, act, disp, loc in sorted(
                s["off_miss"], key=lambda x: (x[6] != "gap", -abs(x[0]))):
            out.append(f"| {our_mon} | {mv} | {tg} | {_pct(pred)} | {_pct(act)} | "
                       f"{'over' if err < 0 else 'under'} | {disp}<!-- {loc} --> |")

    # Turn order
    if s["to_total"]:
        out += ["", "### Turn order",
                "*Predicted resolution position (1 = fastest of 4) vs actual, over "
                "full 4-move turns. Protect/Endure jumping ahead is excluded.*",
                "",
                "| Result | Count | Share |",
                "|---|--:|--:|",
                f"| exact | {s['to_exact']} | {_pct(s['to_exact']/s['to_total'])} |",
                f"| off by 1 | {s['to_off1']} | {_pct(s['to_off1']/s['to_total'])} |",
                f"| off by 2+ | {s['to_worse']} | {_pct(s['to_worse']/s['to_total'])} |"]
        real = [m for m in s["to_miss"] if m["diff"] >= 2]
        if real:
            out += ["", "Off-by-2+ misreads (board state at the misread turn; "
                    "*Predicted* = where we expected the flagged mon, *Actual* = the "
                    "real resolution order):", "",
                    "| Turn | my[a] | my[b] | opp[a] | opp[b] | TR | TW | Predicted | Actual order | Disposition |",
                    "|--:|---|---|---|---|:-:|:-:|---|---|---|"]

            def _g(lst, i):
                return lst[i] if i < len(lst) and lst[i] else "-"

            for m in sorted(real, key=lambda x: (x["disposition"] != "gap", -x["diff"])):
                tw = m["tw"]
                tw_s = "/".join(k for k in ("us", "opp") if tw.get(k)) or "-"
                tr_s = "yes" if m["tr"] else "-"
                out.append(
                    f"| {m['turn']} | {_g(m['my'],0)} | {_g(m['my'],1)} | "
                    f"{_g(m['opp'],0)} | {_g(m['opp'],1)} | {tr_s} | {tw_s} | "
                    f"{m['mon']} {m['pred_pos']}/4 | {' > '.join(m['order'])} | "
                    f"{m['disposition']}<!-- {m['loc']} --> |")

    # Immunity
    if s["off_immune"]:
        out += ["", "### Immunity",
                "*Move fired into an immune target.*",
                "",
                "| Move | vs Target | Predicted | Why | Disposition |",
                "|---|---|--:|---|---|"]
        for pred, mv, tg, abil, disp, loc in sorted(s["off_immune"], key=lambda x: (x[4] != "gap", -x[0])):
            why = f"ability: {abil}" if abil else "type immunity"
            out.append(f"| {mv} | {tg} | {_pct(pred)} | {why} | {disp}<!-- {loc} --> |")

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
