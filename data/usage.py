"""usage.py — Metagame archetype priors.

Source file (must be in this directory):
  - ``metagame-gen9championsvgc2026regma-1760.txt`` → archetype usage %

Archetype keys are lower-case strings: 'trickroom', 'tailwind', 'sun',
'rain', 'sand', 'hail', 'balance', 'offense', etc.
"""
from __future__ import annotations
import re, pathlib

_META_FILE = (
    pathlib.Path(__file__).parent
    / "metagame-gen9championsvgc2026regma-1760.txt"
)

_META: dict[str, float] = {}


# ── Loaders ──────────────────────────────────────────────────────────────────

def _load_meta() -> None:
    global _META
    if _META:
        return
    with open(_META_FILE, encoding="utf-8") as f:
        for line in f:
            # balance...........60.94301%
            m = re.match(r'^([a-zA-Z]+)\.+\s*([\d.]+)%', line.strip())
            if m:
                _META[m.group(1).lower()] = float(m.group(2))


# ── Public API ───────────────────────────────────────────────────────────────

def archetype_usage(archetype: str) -> float:
    """
    Return the metagame % for an archetype key, e.g. ``'trickroom'``.

    Returns 0.0 if the archetype is not found.
    Common keys: balance, offense, weatherless, sun, rain, hail, sand,
                 trickroom, tailwind, multiweather.
    """
    _load_meta()
    return _META.get(archetype.lower(), 0.0)


def all_archetypes() -> dict[str, float]:
    """Return ``{archetype: pct}`` for all metagame archetypes."""
    _load_meta()
    return dict(_META)


def is_trick_room_team(threshold_pct: float = 4.0) -> bool:
    """
    Quick helper: True if trick room is above *threshold_pct* in the meta
    (useful for priors about whether an unscouted team uses TR).
    """
    return archetype_usage("trickroom") >= threshold_pct
