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

# Permanent type-boosting held items (×1.2 to the matching move type).  Gems
# (Fire Gem etc.) are intentionally excluded — they are one-time ×1.3 consumables
# with a different mechanic the engine doesn't model.
TYPE_BOOST_ITEMS: dict[str, frozenset[str]] = {
    "Normal":   frozenset({"Silk Scarf"}),
    "Fire":     frozenset({"Charcoal"}),
    "Water":    frozenset({"Mystic Water"}),
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


# Reverse map: held item → the single type it boosts (derived from TYPE_BOOST_ITEMS).
_TYPE_BOOST_ITEM_TYPE: dict[str, str] = {
    item: typ for typ, names in TYPE_BOOST_ITEMS.items() for item in names
}


def type_boost_multiplier(item: Optional[str], move_type: str) -> float:
    """Damage multiplier from a type-boosting held item: 1.2 if *item* boosts
    *move_type*, else 1.0.  Generalizes the per-item check at the call site."""
    return 1.2 if item and _TYPE_BOOST_ITEM_TYPE.get(item) == move_type else 1.0


def _load() -> None:
    global _ITEMS
    if _ITEMS:
        return
    with open(_DATA_FILE, encoding="utf-8") as f:
        _ITEMS = json.load(f)


# ── Public API ───────────────────────────────────────────────────────────────

_ID_TO_NAME: dict[str, str] = {}


def _to_id(s: str) -> str:
    """Showdown item/ability ID: lowercase, alphanumerics only."""
    return "".join(c for c in s.lower() if c.isalnum())


def name_from_id(item: Optional[str]) -> Optional[str]:
    """Map a Showdown item **ID** (``"choicescarf"``) to its display name
    (``"Choice Scarf"``).  Inputs that are already display names (or unknown, or
    empty) pass through unchanged.  Needed because the ``|request|`` JSON gives
    our own items in ID form, but every item lookup is keyed by display name."""
    if not item:
        return item
    _load()
    if item in _ITEMS:            # already a display name
        return item
    global _ID_TO_NAME
    if not _ID_TO_NAME:
        _ID_TO_NAME = {_to_id(k): k for k in _ITEMS}
    return _ID_TO_NAME.get(_to_id(item), item)


def get_item(name: str) -> Optional[str]:
    """Return item description string or None if not found."""
    _load()
    return _ITEMS.get(name)


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
