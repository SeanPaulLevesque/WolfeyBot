"""tools/seed_lead_stats.py — reset opponent lead stats and reseed from recent logs.

The lead-frequency prior in ``Battle Data/lead_stats.json`` (used by
``team_preview.select_leads`` to predict opponent leads) was accumulated over
the Reg M-A ladder.  After the roll to Reg M-B the M-A counts are a stale prior,
so this clears them and rebuilds from the *most recent* battle logs — the
opponent's turn-1 actives (their leads), exactly what the live recorder records
per game via ``data.lead_stats.record_leads``.

Usage::

    .venv\\Scripts\\python.exe tools/seed_lead_stats.py            # last 50 M-B games
    .venv\\Scripts\\python.exe tools/seed_lead_stats.py --last 100
    .venv\\Scripts\\python.exe tools/seed_lead_stats.py --format regma --dry-run
    .venv\\Scripts\\python.exe tools/seed_lead_stats.py --dir "Battle Data/0.29.0/meta-team/v7"
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data import lead_stats  # noqa: E402
import glob  # noqa: E402


def _recent_logs(fmt: str, last: int) -> list[str]:
    """The *last* battle-log paths for *fmt*, most-recent first (by mtime)."""
    logs = [f for f in glob.glob(os.path.join(ROOT, "Battle Data", "**", "*.json"),
                                 recursive=True)
            if fmt in os.path.basename(f) and "lead_stats" not in f]
    logs.sort(key=os.path.getmtime, reverse=True)
    return logs[:last]


def _opp_leads(path: str) -> list[str]:
    """The opponent's turn-1 active species (their leads) for one game log."""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    turns = d.get("turns") or []
    if not turns:
        return []
    return [o["s"] for o in turns[0].get("opp", []) if o and o.get("s")]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Reset + reseed opponent lead stats.")
    ap.add_argument("--last", type=int, default=50,
                    help="number of most-recent games to seed from (default 50)")
    ap.add_argument("--format", default="regmb",
                    help="battle-id format substring to match (default regmb)")
    ap.add_argument("--dir", default=None,
                    help="seed from ALL *.json under this folder (e.g. one team "
                         "version's games) instead of the most-recent N; "
                         "ignores --last/--format")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be seeded without writing")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if args.dir:
        base = args.dir if os.path.isabs(args.dir) else os.path.join(ROOT, args.dir)
        logs = [f for f in glob.glob(os.path.join(base, "**", "*.json"),
                                     recursive=True) if "lead_stats" not in f]
        src = args.dir
    else:
        logs = _recent_logs(args.format, args.last)
        src = f"most-recent '{args.format}'"
    if not logs:
        where = args.dir if args.dir else f"'{args.format}' logs under Battle Data/"
        print(f"No battle logs found in {where}.")
        return

    games = [(p, _opp_leads(p)) for p in logs]
    games = [(p, ls) for p, ls in games if ls]   # skip logs with no turn-1 opp

    print(f"Before: {lead_stats.total_battles()} battles, "
          f"{len(lead_stats.all_lead_counts())} species.")
    print(f"Seeding from {len(games)} of {len(logs)} {src} logs "
          f"(skipped {len(logs) - len(games)} with no turn-1 opp).")

    if args.dry_run:
        from collections import Counter
        c = Counter(s for _, ls in games for s in ls)
        print("DRY RUN — would seed (top 12):")
        for sp, n in c.most_common(12):
            print(f"   {sp:20} {n}")
        return

    lead_stats.reset()
    for _, ls in games:
        lead_stats.record_leads(ls)

    print(f"After:  {lead_stats.total_battles()} battles, "
          f"{len(lead_stats.all_lead_counts())} species.")
    print("Top opponent leads now:")
    for sp, n in list(lead_stats.all_lead_counts().items())[:12]:
        print(f"   {sp:20} {n}")


if __name__ == "__main__":
    main()
