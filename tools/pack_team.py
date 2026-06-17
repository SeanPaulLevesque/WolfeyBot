"""tools/pack_team.py — Convert team.txt (Showdown paste format) to Showdown packed format.

Showdown's /utm command requires a "packed" team string — a compact single-line
representation of the team.  This module converts the human-readable paste
format in team.txt to that string automatically so the user never has to
manually export it from the Teambuilder.

Packed format (one Pokémon per segment, segments separated by ']'):
    nickname|speciesid|itemid|abilityid|move1,move2,move3,move4|nature|evs|gender|ivs|shiny|level|happiness

Field notes:
    nickname  — blank (server uses species name)
    speciesid — Showdown ID: lowercase, alphanumeric only  (e.g. "rotomwash")
    EVs/IVs   — 6 comma-separated values: hp,atk,def,spa,spd,spe; blank field = 0 (EVs) / 31 (IVs)
    gender    — "M", "F", or blank
    shiny     — "S" if shiny, blank otherwise
    level     — integer string; blank = 100

Usage::

    from tools.pack_team import to_packed
    print(to_packed())          # packed string ready for /utm

    # command-line helper
    python tools/pack_team.py
"""
from __future__ import annotations

import pathlib
import re
from typing import Optional

# The frozen baseline roster lives under snapshots/ (one level above tools/).
TEAM_FILE = pathlib.Path(__file__).parent.parent / "snapshots" / "baseline_team.txt"

# Showdown EV line abbreviation → index in [hp, atk, def, spa, spd, spe]
_EV_ABBREV: dict[str, int] = {
    "HP": 0, "Atk": 1, "Def": 2, "SpA": 3, "SpD": 4, "Spe": 5,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_id(name: str) -> str:
    """Convert any Showdown name to its internal ID (lowercase, alphanumeric only).

    Examples::
        "Rotom-Wash"    → "rotomwash"
        "Charizardite Y"→ "charizarditey"
        "Air Slash"     → "airslash"
        "Rough Skin"    → "roughskin"
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _pack_evs(evs: list[int]) -> str:
    """Encode [hp, atk, def, spa, spd, spe] as packed EV string.

    Zero values are encoded as blank fields; trailing blank fields are dropped.

        [252, 0, 4, 0, 0, 252]  → "252,,4,,,252"
        [14, 0, 13, 13, 13, 13] → "14,,13,13,13,13"
        [0, 0, 0, 0, 0, 0]      → ""
    """
    parts = [str(v) if v != 0 else "" for v in evs]
    # Drop trailing blank fields to keep the string compact
    while parts and parts[-1] == "":
        parts.pop()
    return ",".join(parts)


# ── Main converter ────────────────────────────────────────────────────────────

def to_packed(path: Optional[pathlib.Path] = None) -> str:
    """Parse *path* (defaults to team.txt) and return the Showdown packed string."""
    fpath = path or TEAM_FILE
    with open(fpath, encoding="utf-8") as fh:
        content = fh.read()

    packed_mons: list[str] = []

    for block in re.split(r"\n{2,}", content.strip()):
        lines = [ln.rstrip() for ln in block.strip().splitlines() if ln.strip()]
        if not lines:
            continue

        # ── Header: "Name @ Item"  or just  "Name" ───────────────────────────
        name, item = "", ""
        first = lines[0]
        if " @ " in first:
            name, item = (p.strip() for p in first.split(" @ ", 1))
        else:
            name = first.strip()

        # Strip Showdown's redundant gender annotation: "Basculegion-F (F)" → "Basculegion-F"
        name = re.sub(r"\s*\([MF]\)\s*$", "", name)

        ability = ""
        nature  = ""
        level   = 50
        shiny   = False
        evs: list[int] = [0, 0, 0, 0, 0, 0]
        moves:  list[str] = []

        for ln in lines[1:]:
            if ln.startswith("- "):
                moves.append(ln[2:].strip())
            elif ln.startswith("Ability:"):
                ability = ln.split(":", 1)[1].strip()
            elif ln.startswith("Level:"):
                level = int(ln.split(":", 1)[1].strip())
            elif ln.startswith("Shiny:"):
                shiny = ln.split(":", 1)[1].strip().lower() == "yes"
            elif ln.startswith("EVs:"):
                ev_str = ln.split(":", 1)[1].strip()
                for part in ev_str.split("/"):
                    part = part.strip()
                    m = re.match(r"(\d+)\s+(\w+)", part)
                    if m:
                        val, abbrev = int(m.group(1)), m.group(2)
                        idx = _EV_ABBREV.get(abbrev)
                        if idx is not None:
                            evs[idx] = val
            elif ln.endswith("Nature"):
                nature = ln.replace("Nature", "").strip()

        # Infer gender from form suffix ("-F" / "-M") when present
        gender = ""
        if name.endswith("-F"):
            gender = "F"
        elif name.endswith("-M"):
            gender = "M"

        # ── Assemble packed fields ────────────────────────────────────────────
        fields = [
            "",                                   # nickname (blank → use species)
            _to_id(name),                         # species ID
            _to_id(item) if item else "",         # item ID
            _to_id(ability) if ability else "",   # ability ID
            ",".join(_to_id(mv) for mv in moves), # move IDs
            nature,                               # nature (title-case, unchanged)
            _pack_evs(evs),                       # EVs
            gender,                               # gender
            "",                                   # IVs (blank = all 31)
            "S" if shiny else "",                 # shiny flag
            str(level),                           # level
            "",                                   # happiness (blank = 255)
        ]

        packed_mons.append("|".join(fields))

    return "]".join(packed_mons)


# ── CLI helper ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    packed = to_packed()
    print(packed)
