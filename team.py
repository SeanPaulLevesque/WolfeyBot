"""team.py — Loads and caches the bot's team from team.txt.

Parses the Showdown paste format (with EV/SP values) and computes exact
final stats at Level 50 for each team member using the Champions SP formula.

Mega evolution forms are looked up automatically; both pre- and post-mega
stats are stored so the decision module can use the correct speed tier.

Usage::

    from team import get_team, find_member

    team = get_team()           # cached list of TeamMember
    mon  = find_member("Lopunny")
    print(mon.stats["spe"])     # 155  (pre-mega)
    print(mon.mega_stats["spe"]) # 188 (post-mega Lopunny-Mega)
"""
from __future__ import annotations

import pathlib, re
from dataclasses import dataclass, field
from typing import Optional

from data import calc_all_stats, base_stats as get_base_stats, get_species

TEAM_FILE = pathlib.Path(__file__).parent / "team.txt"

# Showdown EV abbreviation → internal stat key
_ABBREV = {
    "HP":  "hp",
    "Atk": "atk",
    "Def": "def",
    "SpA": "spa",
    "SpD": "spd",
    "Spe": "spe",
}

# Known mega name mappings (base → mega form name in species data)
# Extended as needed; falls back to "{name}-Mega" automatically.
_MEGA_NAMES: dict[str, str] = {
    "Charizard":  "Charizard-Mega-Y",   # default Charizard mega
    "Mewtwo":     "Mewtwo-Mega-Y",
}


@dataclass
class TeamMember:
    """One team member with exact computed stats."""
    name:       str                      # e.g. "Lopunny"
    item:       str                      # e.g. "Lopunnite"
    ability:    str
    nature:     str
    sp:         dict[str, int]           # SP per stat (hp/atk/def/spa/spd/spe)
    moves:      list[str]
    shiny:      bool = False

    # Computed stats (pre-mega)
    stats:      dict[str, int] = field(default_factory=dict)

    # Computed stats for mega form, or None if no mega stone
    mega_name:  Optional[str] = None
    mega_stats: Optional[dict[str, int]] = None

    @property
    def speed(self) -> int:
        """Pre-mega Speed stat."""
        return self.stats.get("spe", 0)

    @property
    def mega_speed(self) -> Optional[int]:
        """Post-mega Speed stat, or None."""
        return self.mega_stats.get("spe") if self.mega_stats else None

    def has_mega(self) -> bool:
        return self.mega_stats is not None


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse_evs(ev_string: str) -> dict[str, int]:
    """Parse '1 HP / 32 Atk / 1 SpD / 32 Spe' → {hp:1, atk:32, spd:1, spe:32}."""
    result = {k: 0 for k in _ABBREV.values()}
    for part in ev_string.split("/"):
        part = part.strip()
        m = re.match(r"(\d+)\s+(\w+)", part)
        if m:
            val, abbrev = int(m.group(1)), m.group(2)
            key = _ABBREV.get(abbrev)
            if key:
                result[key] = val
    return result


def _mega_form_name(base_name: str) -> Optional[str]:
    """Return the mega form species name, or None if unknown."""
    if base_name in _MEGA_NAMES:
        return _MEGA_NAMES[base_name]
    candidate = f"{base_name}-Mega"
    if get_species(candidate) is not None:
        return candidate
    return None


def _is_mega_stone(item: str) -> bool:
    """Return True if *item* is a Mega Stone.

    Handles plain stones ("Lopunnite") and X/Y suffixed stones
    ("Charizardite Y", "Mewtwonite X") that Showdown exports with a trailing
    space + letter.
    """
    # Strip trailing " X" / " Y" before checking the -ite suffix
    base = re.sub(r"\s+[XY]$", "", item.strip())
    return base.endswith("ite") and item not in (
        "Eviolite", "Leftovers", "Rocky Helmet",
    )


def load_team(path: Optional[pathlib.Path] = None) -> list[TeamMember]:
    """
    Parse Showdown paste from *path* (defaults to team.txt) and return a
    list of :class:`TeamMember` with fully computed stats.
    """
    fpath = path or TEAM_FILE
    with open(fpath, encoding="utf-8") as fh:
        content = fh.read()

    members: list[TeamMember] = []

    for block in re.split(r"\n{2,}", content.strip()):
        lines = [ln.rstrip() for ln in block.strip().splitlines() if ln.strip()]
        if not lines:
            continue

        name, item = "", ""
        first = lines[0]
        if " @ " in first:
            name, item = (p.strip() for p in first.split(" @ ", 1))
        else:
            name = first.strip()

        # Strip Showdown's redundant gender tag: "Basculegion-F (F)" → "Basculegion-F"
        name = re.sub(r"\s*\([MF]\)\s*$", "", name)

        ability, nature, shiny = "", "", False
        sp = {k: 0 for k in _ABBREV.values()}
        moves: list[str] = []

        for ln in lines[1:]:
            if ln.startswith("- "):
                moves.append(ln[2:].strip())
            elif ln.startswith("Ability:"):
                ability = ln.split(":", 1)[1].strip()
            elif ln.startswith("Shiny:"):
                shiny = ln.split(":", 1)[1].strip().lower() == "yes"
            elif ln.startswith("EVs:"):
                sp = _parse_evs(ln.split(":", 1)[1].strip())
            elif ln.endswith("Nature"):
                nature = ln.replace("Nature", "").strip()

        # ── Compute stats ────────────────────────────────────────────────────
        bs = get_base_stats(name)
        if bs is None:
            # Try without suffix (e.g. "Basculegion-F" → "Basculegion")
            base_try = name.split("-")[0]
            bs = get_base_stats(base_try)

        computed = calc_all_stats(bs, sp, nature) if bs else {}

        # ── Mega form ────────────────────────────────────────────────────────
        mega_name: Optional[str] = None
        mega_computed: Optional[dict] = None
        if _is_mega_stone(item):
            mega_name = _mega_form_name(name)
            if mega_name:
                mega_bs = get_base_stats(mega_name)
                if mega_bs:
                    # Post-mega: same SP/nature, different base stats
                    mega_computed = calc_all_stats(mega_bs, sp, nature)

        members.append(TeamMember(
            name=name, item=item, ability=ability, nature=nature,
            sp=sp, moves=moves, shiny=shiny,
            stats=computed,
            mega_name=mega_name, mega_stats=mega_computed,
        ))

    return members


# ── Cached singleton ──────────────────────────────────────────────────────────

_CACHED_TEAM: Optional[list[TeamMember]] = None


def get_team(reload: bool = False) -> list[TeamMember]:
    """Return the cached team, loading from team.txt on first call."""
    global _CACHED_TEAM
    if _CACHED_TEAM is None or reload:
        _CACHED_TEAM = load_team()
    return _CACHED_TEAM


def find_member(species: str) -> Optional[TeamMember]:
    """
    Find a team member by species name.

    Handles both base names ("Lopunny") and mega names ("Lopunny-Mega") by
    checking ``name`` and ``mega_name`` fields.

    Also resolves gender-form mismatches in both directions:
    * Forward: battle reports "Basculegion-F", team stored as "Basculegion"
      → "Basculegion-F".startswith("Basculegion") is True
    * Reverse: battle reports "Basculegion", team stored as "Basculegion-F"
      → "Basculegion-F".startswith("Basculegion-") is True
    """
    for m in get_team():
        if m.name == species or m.mega_name == species:
            return m
        # Forward form match: battle "Basculegion-F" vs team "Basculegion"
        if species.startswith(m.name + "-") or species == m.name:
            return m
        # Reverse form match: battle "Basculegion" vs team "Basculegion-F"
        if m.name.startswith(species + "-"):
            return m
    return None
