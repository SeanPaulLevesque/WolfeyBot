"""abilities.py — Champions ability data.

Loaded from ``champions_abilities.json`` in this directory.

Each entry::
    {
        "description":   str,
        "championsNote": str,   # present only when Champions-modified
    }
"""
from __future__ import annotations
import json, pathlib
from typing import Optional

_DATA_FILE = pathlib.Path(__file__).parent / "champions_abilities.json"
_ABILITIES: dict[str, dict] = {}

# ── Well-known ability sets ──────────────────────────────────────────────────

# Abilities that double Speed in a specific weather/terrain
WEATHER_SPEED_ABILITIES: dict[str, str] = {
    "Swift Swim":   "rain",
    "Chlorophyll":  "sun",
    "Sand Rush":    "sand",
    "Slush Rush":   "hail",
    "Surge Surfer": "electric_terrain",
}

# Abilities that boost Speed via an internal mechanism
SPEED_BOOST_ABILITIES = frozenset({
    "Speed Boost",   # +1 Speed per turn
    "Unburden",      # 2× Speed after losing held item
})

# All abilities that can affect Speed
SPEED_RELATED_ABILITIES = frozenset(WEATHER_SPEED_ABILITIES) | SPEED_BOOST_ABILITIES

# Abilities that may affect turn order in non-Speed ways
PRIORITY_ABILITIES = frozenset({
    "Prankster",    # +1 priority to status moves
    "Gale Wings",   # +1 priority to Flying moves at full HP
    "Triage",       # +3 priority to healing moves
    "Stall",        # move last in priority bracket
    "Mycelium Might", # status moves always go last, immune to Prankster
})

# Intimidate-related
INTIMIDATE_ABILITIES = frozenset({"Intimidate"})

# Abilities that negate Intimidate
INTIMIDATE_IMMUNE_ABILITIES = frozenset({
    "Inner Focus", "Own Tempo", "Oblivious", "Scrappy", "Simple",
    "Clear Body", "White Smoke", "Full Metal Body", "Hyper Cutter",
})


def _load() -> None:
    global _ABILITIES
    if _ABILITIES:
        return
    with open(_DATA_FILE, encoding="utf-8") as f:
        _ABILITIES = json.load(f)


# ── Public API ───────────────────────────────────────────────────────────────

_ID_TO_NAME: dict[str, str] = {}


def name_from_id(ability: Optional[str]) -> Optional[str]:
    """Map a Showdown ability **ID** (``"roughskin"``) to its display name
    (``"Rough Skin"``).  Already-display names / unknown / empty pass through.
    The ``|request|`` JSON gives our own abilities in ID form, but ability
    lookups (Unburden, weather-speed abilities, atk_modifier) are keyed by name."""
    if not ability:
        return ability
    _load()
    if ability in _ABILITIES:
        return ability
    global _ID_TO_NAME
    if not _ID_TO_NAME:
        _ID_TO_NAME = {"".join(c for c in k.lower() if c.isalnum()): k
                       for k in _ABILITIES}
    key = "".join(c for c in ability.lower() if c.isalnum())
    return _ID_TO_NAME.get(key, ability)


def get_ability(name: str) -> Optional[dict]:
    """Return ability data dict or None."""
    _load()
    return _ABILITIES.get(name)


