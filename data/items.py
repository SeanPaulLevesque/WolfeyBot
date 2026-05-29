"""items.py — Champions item data.

Loaded from ``champions_items.json`` in this directory.
Maps ``item_name -> description_string``.
"""
from __future__ import annotations
import json, pathlib
from typing import Optional

_DATA_FILE = pathlib.Path(__file__).parent / "champions_items.json"
_ITEMS: dict[str, str] = {}

# ── Well-known item sets ─────────────────────────────────────────────────────

# Items that multiply Speed by 1.5×
SPEED_BOOST_ITEMS = frozenset({"Choice Scarf"})

# Items that halve Speed
SPEED_HALVE_ITEMS = frozenset({"Iron Ball", "Macho Brace"})

# Items that lock the holder to one move
CHOICE_ITEMS = frozenset({"Choice Scarf", "Choice Band", "Choice Specs"})

# Items that always survive one hit at full HP
FOCUS_SASH_ITEMS = frozenset({"Focus Sash"})

# Type-boosting items: maps type → item names
TYPE_BOOST_ITEMS: dict[str, frozenset[str]] = {
    "Normal":   frozenset({"Silk Scarf"}),
    "Fire":     frozenset({"Charcoal", "Fire Gem"}),
    "Water":    frozenset({"Mystic Water", "Water Gem"}),
    "Electric": frozenset({"Magnet"}),
    "Grass":    frozenset({"Miracle Seed"}),
    "Ice":      frozenset({"Never-Melt Ice"}),
    "Fighting": frozenset({"Black Belt"}),
    "Poison":   frozenset({"Poison Barb"}),
    "Ground":   frozenset({"Soft Sand"}),
    "Flying":   frozenset({"Sharp Beak"}),
    "Psychic":  frozenset({"Twisted Spoon"}),
    "Bug":      frozenset({"Silver Powder"}),
    "Rock":     frozenset({"Hard Stone"}),
    "Ghost":    frozenset({"Spell Tag"}),
    "Dragon":   frozenset({"Dragon Fang"}),
    "Dark":     frozenset({"Black Glasses"}),
    "Steel":    frozenset({"Metal Coat"}),
    "Fairy":    frozenset({"Fairy Feather"}),
}


def _load() -> None:
    global _ITEMS
    if _ITEMS:
        return
    with open(_DATA_FILE, encoding="utf-8") as f:
        _ITEMS = json.load(f)


# ── Public API ───────────────────────────────────────────────────────────────

def get_item(name: str) -> Optional[str]:
    """Return item description string or None if not found."""
    _load()
    return _ITEMS.get(name)


def item_exists(name: str) -> bool:
    """Return True if the item is in the Champions legal item list."""
    _load()
    return name in _ITEMS


def speed_multiplier(item: Optional[str]) -> float:
    """Return the Speed multiplier granted by *item* (1.0 if none)."""
    if item in SPEED_BOOST_ITEMS:
        return 1.5
    if item in SPEED_HALVE_ITEMS:
        return 0.5
    return 1.0


def is_mega_stone(item: str) -> bool:
    """Return True if the item name ends in 'ite' (mega stone pattern)."""
    return item.endswith("ite")


def all_items() -> dict[str, str]:
    """Return the full ``{name: description}`` mapping (read-only copy)."""
    _load()
    return dict(_ITEMS)
