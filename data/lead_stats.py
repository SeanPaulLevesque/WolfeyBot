"""lead_stats.py — Opponent lead frequency statistics.

Tracks which Pokémon opponents lead with against our team, accumulated
across all recorded battles from v0.5.0 onward.  Used by team_preview
to predict likely opponent leads and optimise our own lead order.

Data persisted at:
    Battle Data/lead_stats.json

Schema::

    {
        "total_battles": 42,
        "counts": {
            "Farigiraf": 10,
            "Charizard": 7,
            ...
        }
    }

Counts are per-individual-slot, not per-battle: a battle where Farigiraf
and Charizard both led increments each species by 1 (total_battles by 1).
"""
from __future__ import annotations

import json
import os
import pathlib

_PROJECT_ROOT = pathlib.Path(os.path.dirname(os.path.abspath(__file__))).parent
_STATS_FILE   = _PROJECT_ROOT / "Battle Data" / "lead_stats.json"


def _load() -> dict:
    """Read the stats file; return a blank structure if absent or unreadable."""
    if _STATS_FILE.exists():
        try:
            with open(_STATS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_battles": 0, "counts": {}}


def _save(data: dict) -> None:
    _STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Public read API ───────────────────────────────────────────────────────────

def lead_frequency(species: str) -> int:
    """Number of times *species* has been seen as an opponent lead."""
    return _load()["counts"].get(species, 0)


def all_lead_counts() -> dict[str, int]:
    """Return ``{species: count}`` for all seen leads, sorted by count descending."""
    data = _load()
    return dict(sorted(data["counts"].items(), key=lambda x: -x[1]))


def total_battles() -> int:
    """Total number of battles recorded in the lead stats."""
    return _load().get("total_battles", 0)


# ── Public write API ──────────────────────────────────────────────────────────

def record_leads(leads: list[str]) -> None:
    """Increment lead counts for each species in *leads* and persist.

    Also increments ``total_battles`` by 1 regardless of how many leads
    are provided (normally 2 for a doubles game).

    Non-empty species strings only; blank entries are silently skipped.
    """
    data   = _load()
    counts = data.get("counts", {})
    data["total_battles"] = data.get("total_battles", 0) + 1
    for s in leads:
        if s:
            counts[s] = counts.get(s, 0) + 1
    data["counts"] = counts
    _save(data)
