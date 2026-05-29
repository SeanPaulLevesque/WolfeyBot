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

def get_ability(name: str) -> Optional[dict]:
    """Return ability data dict or None."""
    _load()
    return _ABILITIES.get(name)


def ability_description(name: str) -> str:
    """Return the ability description string (empty string if not found)."""
    a = get_ability(name)
    return a["description"] if a else ""


def speed_multiplier_for_ability(ability: str, weather: Optional[str] = None,
                                 terrain: Optional[str] = None) -> float:
    """
    Return the Speed multiplier granted by *ability* given current field state.

    ``weather`` should be one of: 'rain', 'sun', 'sand', 'hail', or None.
    ``terrain`` should be one of: 'electric_terrain', or None.
    """
    required_condition = WEATHER_SPEED_ABILITIES.get(ability)
    if required_condition:
        active = weather or terrain
        if active == required_condition:
            return 2.0
    return 1.0


def all_abilities() -> dict[str, dict]:
    """Return the full ``{name: data}`` mapping (read-only copy)."""
    _load()
    return dict(_ABILITIES)
