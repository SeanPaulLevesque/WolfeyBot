"""our_leads.py — OUR lead-pair performance stats (the empirical pair prior).

The engine-grounded lead eval scores boards, but a board score is a turn-1
model — it can systematically favour pairs that don't convert (v9: the eval's
favourite Aero+Basculegion sat at 49% over 281 games while barely-picked
Kingambit+Lycanroc ran 10-1).  This module tracks how each of OUR lead pairs
actually performs and turns it into a smoothed multiplier for the pair score.

Data persisted at ``Battle Data/our_lead_stats.json``::

    {
        "meta-team@v9": {
            "Aerodactyl|Basculegion": {"w": 139, "g": 281},
            ...
        }
    }

* Keyed per ``team@version`` — pair performance doesn't transfer across
  rosters; a fresh team version starts neutral and learns from its own games.
* Pair keys are sorted base-forme names joined with ``|``.
* Recorded live by ``recorder.record_outcome`` (mirrors ``record_leads``);
  rebuildable from the battle logs with ``tools/build_our_lead_stats.py``.

Smoothing: ``pair_factor`` returns ``smoothed_wr / 0.5`` with a Beta prior of
``SMOOTHING_K`` pseudo-games at 50% — an unseen pair is exactly ×1.0, and it
takes a real sample to move far from neutral (10-1 → ×1.43, 18-34 → ×0.74).
"""
from __future__ import annotations

import json
import os
import pathlib

_PROJECT_ROOT = pathlib.Path(os.path.dirname(os.path.abspath(__file__))).parent
_STATS_FILE   = _PROJECT_ROOT / "Battle Data" / "our_lead_stats.json"

SMOOTHING_K = 10   # pseudo-games at 50% blended into every observed record


def _pair_key(a: str, b: str) -> str:
    from .sets import base_forme
    return "|".join(sorted((base_forme(a), base_forme(b))))


def _load() -> dict:
    if _STATS_FILE.exists():
        try:
            with open(_STATS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save(data: dict) -> None:
    _STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_result(team_spec: str, lead_a: str, lead_b: str, won: bool) -> None:
    """Record one game's outcome for OUR lead pair under *team_spec*."""
    if not (team_spec and lead_a and lead_b):
        return
    data = _load()
    team = data.setdefault(team_spec, {})
    rec = team.setdefault(_pair_key(lead_a, lead_b), {"w": 0, "g": 0})
    rec["g"] += 1
    rec["w"] += bool(won)
    _save(data)


def pair_record(team_spec: str, lead_a: str, lead_b: str) -> tuple[int, int]:
    """(wins, games) for the pair under *team_spec* — (0, 0) if unseen."""
    rec = _load().get(team_spec, {}).get(_pair_key(lead_a, lead_b))
    return (rec["w"], rec["g"]) if rec else (0, 0)


def pair_factor(team_spec: str, lead_a: str, lead_b: str,
                *, k: int = SMOOTHING_K) -> float:
    """Smoothed performance multiplier for the pair (1.0 = neutral / unseen).

    ``(wins + k/2) / (games + k) / 0.5`` — the Beta-smoothed win rate scaled so
    50% is exactly ×1.0.  Bounded ~[0.2, 1.8] in practice by the smoothing."""
    w, g = pair_record(team_spec, lead_a, lead_b)
    if g == 0:
        return 1.0
    return ((w + k / 2.0) / (g + k)) / 0.5


def reset() -> None:
    """Clear all pair stats (used by the rebuild tool)."""
    _save({})
