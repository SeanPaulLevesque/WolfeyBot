"""tools/build_lead_stats.py — Rebuild lead_stats.json from battle data.

Scans every versioned battle-data directory at or above v0.21.0, extracts
the opponent's turn-1 actives (= the actual leads) from each recorded
battle, and writes a cumulative ``lead_stats.json`` (individual ``counts`` +
co-led ``pairs``).

Run from the project root::

    python -m tools.build_lead_stats

The output file is written to ``Battle Data/lead_stats.json``.  The script
is safe to re-run: the file is always rebuilt from scratch so there is no
risk of double-counting across reruns.
"""
from __future__ import annotations

import itertools
import json
import pathlib
import sys

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
_BATTLE_DATA  = _PROJECT_ROOT / "Battle Data"
_STATS_OUT    = _BATTLE_DATA  / "lead_stats.json"

# Only include battles from this version onward.
_MIN_VERSION: tuple[int, ...] = (0, 21, 0)


def _parse_version(name: str) -> tuple[int, ...] | None:
    """Parse a ``"MAJOR.MINOR.PATCH"`` directory name into a comparable tuple.

    Returns ``None`` for directory names that are not valid version strings
    (e.g. hidden dirs, ``__pycache__``, or future alternate naming schemes).
    """
    try:
        parts = tuple(int(x) for x in name.split("."))
        if len(parts) != 3:
            return None
        return parts
    except ValueError:
        return None


def main() -> None:
    counts:        dict[str, int] = {}
    pairs:         dict[str, int] = {}
    total_battles: int            = 0
    scanned_files: int            = 0
    skipped:       int            = 0

    # Iterate version directories in sorted order so progress output is tidy.
    version_dirs = sorted(
        d for d in _BATTLE_DATA.iterdir()
        if d.is_dir()
    )

    for version_dir in version_dirs:
        ver = _parse_version(version_dir.name)
        if ver is None or ver < _MIN_VERSION:
            continue

        # Logs are nested under <version>/<team>/<team-version>/*.json (the named-
        # team A/B layout), so recurse — and skip any stray stats file.
        battle_files = [f for f in version_dir.rglob("*.json")
                        if "lead_stats" not in f.name]
        print(f"  v{version_dir.name}  ({len(battle_files)} files)")

        for battle_file in battle_files:
            try:
                with open(battle_file, encoding="utf-8") as f:
                    battle = json.load(f)
            except Exception as exc:
                print(
                    f"    SKIP  {battle_file.name}  (read error: {exc})",
                    file=sys.stderr,
                )
                skipped += 1
                continue

            scanned_files += 1

            # Find turn 1 — the only turn that records actual leads.
            turn1 = next(
                (t for t in battle.get("turns", []) if t.get("n") == 1),
                None,
            )
            if turn1 is None:
                skipped += 1
                continue

            opp   = turn1.get("opp", [])
            leads = [m["s"] for m in opp if m is not None and "s" in m]
            if not leads:
                skipped += 1
                continue

            total_battles += 1
            for s in leads:
                counts[s] = counts.get(s, 0) + 1
            for a, b in itertools.combinations(sorted(set(leads)), 2):
                key = "|".join((a, b))   # leads already sorted -> canonical key
                pairs[key] = pairs.get(key, 0) + 1

    # Persist — sort descending for human readability.
    sorted_counts = dict(sorted(counts.items(), key=lambda x: -x[1]))
    sorted_pairs  = dict(sorted(pairs.items(),  key=lambda x: -x[1]))
    data = {"total_battles": total_battles, "counts": sorted_counts,
            "pairs": sorted_pairs}

    _STATS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(_STATS_OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print(f"Scanned      : {scanned_files} battle files (v0.5.0+)")
    print(f"With leads   : {total_battles}")
    if skipped:
        print(f"Skipped      : {skipped}  (no turn-1 data or parse error)")
    print()

    if not sorted_counts:
        print("No lead data found.")
    else:
        print("Top opponent leads:")
        for species, count in list(sorted_counts.items())[:20]:
            pct = count / total_battles * 100 if total_battles else 0
            print(f"  {species:<25s}  {count:>4d}  ({pct:5.1f}%)")

    if sorted_pairs:
        print("\nTop co-led pairs:")
        for key, count in list(sorted_pairs.items())[:20]:
            pct = count / total_battles * 100 if total_battles else 0
            print(f"  {key:<35s}  {count:>4d}  ({pct:5.1f}%)")

    print(f"\nWritten to: {_STATS_OUT}")


if __name__ == "__main__":
    main()
