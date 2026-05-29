"""moves.py — Champions move data.

Loaded from ``champions_moves.json`` in this directory.

Each entry::
    {
        "type":        str,   # e.g. "Fire"
        "category":    str,   # "Physical" | "Special" | "Status"
        "power":       Optional[int],
        "accuracy":    Optional[int],   # None = never misses
        "pp":          Optional[int],
        "priority":    int,          # default 0
        "target":      str,          # human-readable target string
        "description": str,
        "championsChanges": str,     # present only when changed
    }
"""
from __future__ import annotations
import json, pathlib
from typing import Optional

_DATA_FILE = pathlib.Path(__file__).parent / "champions_moves.json"
_MOVES: dict[str, dict] = {}

# Multi-hit move expected hit counts.
# Fixed-count: exact value.  Variable 2-5 hits: Gen-5+ average ≈ 3.17.
# Damage is scored as power × expected_hits so two-hit moves aren't undervalued.
_MULTI_HIT_COUNTS: dict[str, float] = {
    # Fixed 2 hits
    "Bonemerang":        2.0,
    "Double Hit":        2.0,
    "Double Iron Bash":  2.0,
    "Double Kick":       2.0,
    "Dual Chop":         2.0,
    "Dual Wingbeat":     2.0,
    "Gear Grind":        2.0,
    "Twineedle":         2.0,
    # Fixed 3 hits
    "Triple Kick":       3.0,
    # Triple Axel: 20+40+60 total = 120; approximate as 3 hits of avg 40 power
    "Triple Axel":       3.0,
    # Fixed 5 hits
    "Surging Strikes":   5.0,
    # Variable 2-5 hits (Gen 5+ distribution: avg 3.17)
    "Arm Thrust":        3.17,
    "Bullet Seed":       3.17,
    "Fury Attack":       3.17,
    "Fury Swipes":       3.17,
    "Icicle Spear":      3.17,
    "Pin Missile":       3.17,
    "Rock Blast":        3.17,
    "Scale Shot":        3.17,
    "Tail Slap":         3.17,
    "Water Shuriken":    3.17,
    "Population Bomb":   3.17,  # actually 1-10 but treat as variable
}

# Spread move target strings (hit multiple Pokémon with 0.75× penalty)
SPREAD_TARGETS = frozenset({
    "spread (both opponents, 0.75x penalty)",
    "spread (all adjacent incl. ally, 0.75x penalty)",
})

# Move target strings that need no explicit target in the choice string
NO_TARGET_STRINGS = frozenset({
    "self",
    "own side (field effect)",
    "own team",
    "opponent side (field effect)",
    "all pokemon (field effect)",
    "all pokemon (field effect)",
    "scripted",
})


def _load() -> None:
    global _MOVES
    if _MOVES:
        return
    with open(_DATA_FILE, encoding="utf-8") as f:
        _MOVES = json.load(f)


# ── Public API ───────────────────────────────────────────────────────────────

def get_move(name: str) -> Optional[dict]:
    """Return move data dict or None."""
    _load()
    return _MOVES.get(name)


def move_power(name: str) -> Optional[int]:
    """Return base power or None (Status / move not found)."""
    m = get_move(name)
    if m is None:
        return None
    return m.get("power") or None   # treat 0 as None


def move_type(name: str) -> Optional[str]:
    """Return type string or None."""
    m = get_move(name)
    return m.get("type") if m else None


def move_category(name: str) -> Optional[str]:
    """Return 'Physical', 'Special', or 'Status', or None."""
    m = get_move(name)
    return m.get("category") if m else None


def move_priority(name: str) -> int:
    """Return move priority (0 if unknown or not found)."""
    m = get_move(name)
    return m.get("priority", 0) if m else 0


def is_priority_move(name: str) -> bool:
    """Return True if the move has positive priority."""
    return move_priority(name) > 0


def is_spread_move(name: str) -> bool:
    """Return True if the move hits multiple targets (0.75× penalty applies)."""
    m = get_move(name)
    if m is None:
        return False
    return m.get("target", "") in SPREAD_TARGETS


def needs_target(name: str) -> bool:
    """
    Return True if the move requires an explicit target index in doubles.

    Moves that target self / field / own side don't need one.
    """
    m = get_move(name)
    if m is None:
        return True   # assume targeting needed if unknown
    return m.get("target", "") not in NO_TARGET_STRINGS


def expected_hits(name: str) -> float:
    """
    Return the expected number of hits for *name* (1.0 for single-hit moves).

    Used to scale power in the damage formula so multi-hit moves like
    Dual Wingbeat (2 × 40 = 80 effective) aren't undervalued vs single-hit
    moves with higher per-hit power (Ice Fang = 65).
    """
    return _MULTI_HIT_COUNTS.get(name, 1.0)


def all_moves() -> dict[str, dict]:
    """Return the full move dictionary (read-only copy)."""
    _load()
    return dict(_MOVES)
