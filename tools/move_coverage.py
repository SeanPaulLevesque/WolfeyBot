"""tools/move_coverage.py — move-data coverage cross-reference.

For every Pokémon that has usage data (data/sets.py), checks whether its
commonly-used moves exist in data/champions_moves.json.  Surfaces two gaps:

  1. Mons whose TOP usage moves are missing move-property data (the engine
     can't score those moves) — sorted by the missing move's usage %.
  2. Reg M-B / newly-added species that have NO usage data yet (so no moveset
     can be assumed for them until usage is compiled by hand / published).

Usage (from repo root):
    .venv\\Scripts\\python.exe tools/move_coverage.py            # default ≥20% threshold
    .venv\\Scripts\\python.exe tools/move_coverage.py --min 10   # widen to ≥10%
"""
import argparse
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from data.moves import get_move                       # noqa: E402
from data.sets import all_pokemon, move_distribution  # noqa: E402
from data.species import get_species, _MEGA_SUPPLEMENTS, _load  # noqa: E402


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Move-data coverage cross-reference.")
    ap.add_argument("--min", type=float, default=20.0,
                    help="usage%% threshold for a move to count as 'top' (default 20)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # Usage-data placeholders that are not real moves (empty slot / Transform-only).
    _NOT_A_MOVE = {"Nothing", "Other", ""}

    mons = all_pokemon()
    gaps = []          # (mon, move, usage_pct)
    for mon in mons:
        for move, pct in move_distribution(mon):
            if move in _NOT_A_MOVE:
                continue
            if pct >= args.min and get_move(move) is None:
                gaps.append((mon, move, pct))

    print(f"\n{'='*66}\n MOVE-DATA COVERAGE — {len(mons)} mons with usage data, "
          f"top-move threshold ≥{args.min:g}%\n{'='*66}")
    if gaps:
        print(f" {len(gaps)} top-usage move(s) MISSING from champions_moves.json:")
        for mon, move, pct in sorted(gaps, key=lambda g: -g[2]):
            print(f"   {mon:18} {move:18} {pct:5.1f}% usage  — NOT in move DB")
    else:
        print(" Every mon's top-usage moves are all present in the move DB. ✓")

    # ── Reg M-B / new species with no usage data yet ─────────────────────────
    _load()
    with_usage = set(mons)
    # New Reg M-B additions are tagged formats=["Champions"]; split them out from
    # pre-existing low-usage mons so the actionable set (new mons needing
    # hand-compiled usage) is clear.
    new_no_usage, old_no_usage = [], []
    for n, e in sorted(((s["name"], s) for s in [get_species(x) for x in
                        {se["name"] for se in __import__("json").load(
                            open(_REPO / "data" / "smogon_champions_slim.json", encoding="utf-8"))}
                        | set(_MEGA_SUPPLEMENTS)] if s)):
        if n in with_usage:
            continue
        (new_no_usage if e.get("formats") == ["Champions"] else old_no_usage).append(n)

    print(f"\n── Reg M-B additions with NO usage data yet (hand-compile when available) "
          f"— {len(new_no_usage)} ──")
    print("   " + ", ".join(new_no_usage))
    print(f"\n── pre-existing species with no usage data (low-usage / never brought) "
          f"— {len(old_no_usage)} ──")
    print("   " + ", ".join(old_no_usage))
    print()


if __name__ == "__main__":
    main()
