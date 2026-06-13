"""species.py — Champions species lookup (types, base stats, formats).

Loaded from ``smogon_champions_slim.json`` in this directory.
Keys are canonical species names as used by Smogon/Showdown
(e.g. "Garchomp", "Charizard-Mega-Y", "Lopunny-Mega").
"""
from __future__ import annotations
import json, pathlib
from typing import Optional

_DATA_FILE = pathlib.Path(__file__).parent / "smogon_champions_slim.json"

_SPECIES: dict[str, dict] = {}

# Mega-evolution base stats not present in smogon_champions_slim.json.
# Stats sourced from the Champions format spreadsheet.
# Add entries here as new mega users are encountered.
# Alternate battle-form aliases for species whose in-battle form name differs
# from the entry in smogon_champions_slim.json but shares the same typing.
# Maps the Showdown form name → canonical name in _SPECIES.
# Add entries here whenever a new alternate-form species is encountered.
# Suffixes that denote a competitively DISTINCT Pokémon (different typing,
# stats or movepool).  The progressive suffix-strip fallback must never cross
# these: "Stunfisk-Galar" (Ground/Steel) must NOT resolve to base Stunfisk
# (Ground/Electric) — better an honest miss (synthetic fallback + data_gaps
# flag) than silently wrong data.  Cosmetic suffixes (Alcremie decorations,
# Vivillon patterns, …) are open-ended and deliberately NOT listed.
_DISTINCT_FORME_SUFFIXES: frozenset[str] = frozenset({
    "Galar", "Alola", "Hisui", "Paldea",          # regional formes
    "Therian", "Origin", "Bloodmoon", "Crowned",  # stat/typing-changing formes
    "Mega", "X", "Y",                             # mega formes (own entries)
    "F",                                          # female formes can differ (Meowstic/Indeedee/Basculegion)
})

_FORM_ALIASES: dict[str, str] = {
    # Aegislash switches between Shield (default) and Blade (attack) forms.
    # Both are Steel/Ghost.
    "Aegislash-Blade":  "Aegislash",
    "Aegislash-Shield": "Aegislash",
    # Mimikyu-Busted appears after its disguise is broken. Still Ghost/Fairy.
    "Mimikyu-Busted":   "Mimikyu",
    # Palafin-Hero is the powered-up form via the Hero ability. Still Water.
    "Palafin-Hero":     "Palafin",
    # Morpeko-Hangry is the Hangry Mode from Hunger Switch. Still Electric/Dark.
    "Morpeko-Hangry":   "Morpeko",
    # Greninja-Ash (Battle Bond activated). Still Water/Dark.
    "Greninja-Ash":     "Greninja",
    # Showdown's species string for male Meowstic is the bare name; the slim
    # DB only has the gendered entries (identical stats/typing).  Without this
    # alias an opposing Meowstic had no stats/types at all — invisible to the
    # engine in both damage directions (caught live by data_gaps, 0.7.6 run).
    "Meowstic":         "Meowstic-M",
}

_MEGA_SUPPLEMENTS: dict[str, dict] = {
    "Abomasnow-Mega":    {"name":"Abomasnow-Mega",    "types":["Grass","Ice"],        "hp":90,  "atk":132,"def":105,"spa":132,"spd":105,"spe":30,  "formats":["OU"]},
    "Absol-Mega":        {"name":"Absol-Mega",         "types":["Dark"],               "hp":65,  "atk":150,"def":60, "spa":115,"spd":60, "spe":115, "formats":["OU"]},
    "Aerodactyl-Mega":   {"name":"Aerodactyl-Mega",    "types":["Rock","Flying"],       "hp":80,  "atk":135,"def":85, "spa":70, "spd":95, "spe":150, "formats":["OU"]},
    "Aggron-Mega":       {"name":"Aggron-Mega",        "types":["Steel"],              "hp":70,  "atk":140,"def":230,"spa":60, "spd":80, "spe":50,  "formats":["OU"]},
    "Alakazam-Mega":     {"name":"Alakazam-Mega",      "types":["Psychic"],            "hp":55,  "atk":50, "def":65, "spa":175,"spd":105,"spe":150, "formats":["OU"]},
    "Altaria-Mega":      {"name":"Altaria-Mega",       "types":["Dragon","Fairy"],     "hp":75,  "atk":110,"def":110,"spa":110,"spd":105,"spe":80,  "formats":["OU"]},
    "Ampharos-Mega":     {"name":"Ampharos-Mega",      "types":["Electric","Dragon"],  "hp":90,  "atk":95, "def":105,"spa":165,"spd":110,"spe":45,  "formats":["OU"]},
    "Audino-Mega":       {"name":"Audino-Mega",        "types":["Normal","Fairy"],     "hp":103, "atk":60, "def":126,"spa":80, "spd":126,"spe":50,  "formats":["OU"]},
    "Banette-Mega":      {"name":"Banette-Mega",       "types":["Ghost"],              "hp":64,  "atk":165,"def":75, "spa":93, "spd":83, "spe":75,  "formats":["OU"]},
    "Beedrill-Mega":     {"name":"Beedrill-Mega",      "types":["Bug","Poison"],       "hp":65,  "atk":150,"def":40, "spa":15, "spd":80, "spe":145, "formats":["OU"]},
    "Blastoise-Mega":    {"name":"Blastoise-Mega",     "types":["Water"],              "hp":79,  "atk":103,"def":120,"spa":135,"spd":115,"spe":78,  "formats":["OU"]},
    "Camerupt-Mega":     {"name":"Camerupt-Mega",      "types":["Fire","Ground"],      "hp":70,  "atk":120,"def":100,"spa":145,"spd":105,"spe":20,  "formats":["OU"]},
    "Chandelure-Mega":   {"name":"Chandelure-Mega",    "types":["Ghost","Fire"],       "hp":60,  "atk":75, "def":110,"spa":175,"spd":110,"spe":90,  "formats":["OU"]},
    "Charizard-Mega-X":  {"name":"Charizard-Mega-X",   "types":["Fire","Dragon"],      "hp":78,  "atk":130,"def":111,"spa":130,"spd":85, "spe":100, "formats":["OU"]},
    "Charizard-Mega-Y":  {"name":"Charizard-Mega-Y",   "types":["Fire","Flying"],      "hp":78,  "atk":104,"def":78, "spa":159,"spd":115,"spe":100, "formats":["OU"]},
    "Chesnaught-Mega":   {"name":"Chesnaught-Mega",    "types":["Grass","Fighting"],   "hp":88,  "atk":137,"def":172,"spa":74, "spd":115,"spe":44,  "formats":["OU"]},
    "Chimecho-Mega":     {"name":"Chimecho-Mega",      "types":["Psychic","Steel"],    "hp":75,  "atk":50, "def":110,"spa":135,"spd":120,"spe":65,  "formats":["OU"]},
    "Clefable-Mega":     {"name":"Clefable-Mega",      "types":["Fairy","Flying"],     "hp":95,  "atk":80, "def":93, "spa":135,"spd":110,"spe":70,  "formats":["OU"]},
    "Crabominable-Mega": {"name":"Crabominable-Mega",  "types":["Normal","Dragon"],    "hp":97,  "atk":157,"def":122,"spa":62, "spd":107,"spe":33,  "formats":["OU"]},
    "Delphox-Mega":      {"name":"Delphox-Mega",       "types":["Fire","Psychic"],     "hp":75,  "atk":69, "def":72, "spa":159,"spd":125,"spe":134, "formats":["OU"]},
    "Drampa-Mega":       {"name":"Drampa-Mega",        "types":["Grass","Fire"],       "hp":78,  "atk":85, "def":110,"spa":160,"spd":116,"spe":36,  "formats":["OU"]},
    "Dragonite-Mega":    {"name":"Dragonite-Mega",     "types":["Dragon","Flying"],    "hp":91,  "atk":124,"def":115,"spa":145,"spd":125,"spe":100, "formats":["OU"]},
    "Emboar-Mega":       {"name":"Emboar-Mega",        "types":["Fire","Fighting"],    "hp":110, "atk":148,"def":75, "spa":110,"spd":110,"spe":75,  "formats":["OU"]},
    "Excadrill-Mega":    {"name":"Excadrill-Mega",     "types":["Ground","Steel"],     "hp":110, "atk":165,"def":100,"spa":65, "spd":65, "spe":103, "formats":["OU"]},
    "Feraligatr-Mega":   {"name":"Feraligatr-Mega",    "types":["Water","Dragon"],     "hp":85,  "atk":160,"def":125,"spa":89, "spd":93, "spe":78,  "formats":["OU"]},
    "Floette-Mega":      {"name":"Floette-Mega",       "types":["Fairy"],              "hp":74,  "atk":85, "def":87, "spa":155,"spd":148,"spe":102, "formats":["OU"]},
    "Froslass-Mega":     {"name":"Froslass-Mega",      "types":["Ice","Ghost"],        "hp":70,  "atk":80, "def":70, "spa":140,"spd":100,"spe":120, "formats":["OU"]},
    "Gallade-Mega":      {"name":"Gallade-Mega",       "types":["Psychic","Fighting"], "hp":68,  "atk":165,"def":95, "spa":65, "spd":115,"spe":110, "formats":["OU"]},
    "Garchomp-Mega":     {"name":"Garchomp-Mega",      "types":["Dragon","Ground"],    "hp":108, "atk":170,"def":115,"spa":120,"spd":95, "spe":92,  "formats":["OU"]},
    "Gardevoir-Mega":    {"name":"Gardevoir-Mega",     "types":["Psychic","Fairy"],    "hp":68,  "atk":85, "def":65, "spa":165,"spd":135,"spe":100, "formats":["OU"]},
    "Gengar-Mega":       {"name":"Gengar-Mega",        "types":["Ghost","Poison"],     "hp":60,  "atk":65, "def":80, "spa":170,"spd":95, "spe":130, "formats":["OU"]},
    "Glalie-Mega":       {"name":"Glalie-Mega",        "types":["Ice"],                "hp":80,  "atk":120,"def":80, "spa":120,"spd":80, "spe":100, "formats":["OU"]},
    "Glimmora-Mega":     {"name":"Glimmora-Mega",      "types":["Rock","Poison"],      "hp":83,  "atk":90, "def":105,"spa":150,"spd":96, "spe":101, "formats":["OU"]},
    "Golurk-Mega":       {"name":"Golurk-Mega",        "types":["Ground","Ghost"],     "hp":89,  "atk":159,"def":105,"spa":70, "spd":105,"spe":55,  "formats":["OU"]},
    "Greninja-Mega":     {"name":"Greninja-Mega",      "types":["Water","Dark"],       "hp":72,  "atk":125,"def":77, "spa":133,"spd":81, "spe":142, "formats":["OU"]},
    "Gyarados-Mega":     {"name":"Gyarados-Mega",      "types":["Water","Dark"],       "hp":95,  "atk":155,"def":109,"spa":70, "spd":130,"spe":81,  "formats":["OU"]},
    "Hawlucha-Mega":     {"name":"Hawlucha-Mega",      "types":["Fighting","Ice"],     "hp":78,  "atk":137,"def":100,"spa":74, "spd":93, "spe":118, "formats":["OU"]},
    "Heracross-Mega":    {"name":"Heracross-Mega",     "types":["Bug","Fighting"],     "hp":80,  "atk":185,"def":115,"spa":40, "spd":105,"spe":75,  "formats":["OU"]},
    "Houndoom-Mega":     {"name":"Houndoom-Mega",      "types":["Dark","Fire"],        "hp":75,  "atk":90, "def":90, "spa":140,"spd":90, "spe":115, "formats":["OU"]},
    "Kangaskhan-Mega":   {"name":"Kangaskhan-Mega",    "types":["Normal"],             "hp":105, "atk":125,"def":100,"spa":60, "spd":100,"spe":100, "formats":["OU"]},
    "Lopunny-Mega":      {"name":"Lopunny-Mega",       "types":["Normal","Fighting"],  "hp":65,  "atk":136,"def":94, "spa":54, "spd":96, "spe":135, "formats":["OU"]},
    "Lucario-Mega":      {"name":"Lucario-Mega",       "types":["Fighting","Steel"],   "hp":70,  "atk":145,"def":88, "spa":140,"spd":70, "spe":112, "formats":["OU"]},
    "Manectric-Mega":    {"name":"Manectric-Mega",     "types":["Electric"],           "hp":70,  "atk":75, "def":80, "spa":135,"spd":80, "spe":135, "formats":["OU"]},
    "Medicham-Mega":     {"name":"Medicham-Mega",      "types":["Fighting","Psychic"], "hp":60,  "atk":100,"def":85, "spa":80, "spd":85, "spe":100, "formats":["OU"]},
    "Meganium-Mega":     {"name":"Meganium-Mega",      "types":["Grass","Fairy"],      "hp":80,  "atk":92, "def":115,"spa":143,"spd":115,"spe":80,  "formats":["OU"]},
    "Meowstic-F-Mega":   {"name":"Meowstic-F-Mega",   "types":["Fighting","Flying"],  "hp":74,  "atk":48, "def":76, "spa":83, "spd":81, "spe":104, "formats":["OU"]},
    "Meowstic-M-Mega":   {"name":"Meowstic-M-Mega",   "types":["Psychic"],            "hp":74,  "atk":48, "def":76, "spa":143,"spd":101,"spe":124, "formats":["OU"]},
    "Pidgeot-Mega":      {"name":"Pidgeot-Mega",       "types":["Normal","Flying"],    "hp":83,  "atk":80, "def":80, "spa":135,"spd":80, "spe":121, "formats":["OU"]},
    "Pinsir-Mega":       {"name":"Pinsir-Mega",        "types":["Bug","Flying"],       "hp":65,  "atk":155,"def":120,"spa":65, "spd":90, "spe":105, "formats":["OU"]},
    "Sableye-Mega":      {"name":"Sableye-Mega",       "types":["Dark","Ghost"],       "hp":50,  "atk":85, "def":125,"spa":85, "spd":115,"spe":20,  "formats":["OU"]},
    "Scizor-Mega":       {"name":"Scizor-Mega",        "types":["Bug","Steel"],        "hp":70,  "atk":150,"def":140,"spa":65, "spd":100,"spe":75,  "formats":["OU"]},
    "Scovillain-Mega":   {"name":"Scovillain-Mega",    "types":["Rock","Poison"],      "hp":65,  "atk":138,"def":85, "spa":138,"spd":85, "spe":75,  "formats":["OU"]},
    "Sharpedo-Mega":     {"name":"Sharpedo-Mega",      "types":["Water","Dark"],       "hp":70,  "atk":140,"def":70, "spa":110,"spd":65, "spe":105, "formats":["OU"]},
    "Skarmory-Mega":     {"name":"Skarmory-Mega",      "types":["Steel","Flying"],     "hp":65,  "atk":140,"def":110,"spa":40, "spd":100,"spe":110, "formats":["OU"]},
    "Slowbro-Mega":      {"name":"Slowbro-Mega",       "types":["Water","Psychic"],    "hp":95,  "atk":75, "def":180,"spa":130,"spd":80, "spe":30,  "formats":["OU"]},
    "Starmie-Mega":      {"name":"Starmie-Mega",       "types":["Water","Psychic"],    "hp":60,  "atk":100,"def":105,"spa":130,"spd":105,"spe":120, "formats":["OU"]},
    "Steelix-Mega":      {"name":"Steelix-Mega",       "types":["Steel","Ground"],     "hp":75,  "atk":125,"def":230,"spa":55, "spd":95, "spe":30,  "formats":["OU"]},
    "Tyranitar-Mega":    {"name":"Tyranitar-Mega",     "types":["Rock","Dark"],        "hp":100, "atk":164,"def":150,"spa":95, "spd":120,"spe":71,  "formats":["OU"]},
    "Venusaur-Mega":     {"name":"Venusaur-Mega",      "types":["Grass","Poison"],     "hp":80,  "atk":100,"def":123,"spa":122,"spd":120,"spe":80,  "formats":["OU"]},
    "Victreebel-Mega":   {"name":"Victreebel-Mega",    "types":["Grass","Poison"],     "hp":80,  "atk":125,"def":85, "spa":135,"spd":95, "spe":70,  "formats":["OU"]},
}


# Mega-evolution abilities (Champions format).
# Keyed by the same mega form names used in _MEGA_SUPPLEMENTS.
_MEGA_ABILITY_SUPPLEMENTS: dict[str, str] = {
    "Abomasnow-Mega":    "Snow Warning",
    "Absol-Mega":        "Magic Bounce",
    "Aerodactyl-Mega":   "Tough Claws",
    "Aggron-Mega":       "Filter",
    "Alakazam-Mega":     "Trace",
    "Altaria-Mega":      "Pixilate",
    "Ampharos-Mega":     "Mold Breaker",
    "Audino-Mega":       "Healer",
    "Banette-Mega":      "Prankster",
    "Beedrill-Mega":     "Adaptability",
    "Blastoise-Mega":    "Mega Launcher",
    "Camerupt-Mega":     "Sheer Force",
    "Chandelure-Mega":   "Infiltrator",
    "Charizard-Mega-X":  "Tough Claws",
    "Charizard-Mega-Y":  "Drought",
    "Chesnaught-Mega":   "Bulletproof",
    "Chimecho-Mega":     "Levitate",
    "Clefable-Mega":     "Magic Bounce",
    "Crabominable-Mega": "Iron Fist",
    "Delphox-Mega":      "Levitate",
    "Drampa-Mega":       "Berserk",
    "Dragonite-Mega":    "Multiscale",
    "Emboar-Mega":       "Mold Breaker",
    "Excadrill-Mega":    "Piercing Drill",
    "Feraligatr-Mega":   "Dragonize",
    "Floette-Mega":      "Fairy Aura",
    "Froslass-Mega":     "Snow Warning",
    "Gallade-Mega":      "Inner Focus",
    "Garchomp-Mega":     "Sand Force",
    "Gardevoir-Mega":    "Pixilate",
    "Gengar-Mega":       "Shadow Tag",
    "Glalie-Mega":       "Refrigerate",
    "Glimmora-Mega":     "Adaptability",
    "Golurk-Mega":       "Unseen Fist",
    "Greninja-Mega":     "Protean",
    "Gyarados-Mega":     "Mold Breaker",
    "Hawlucha-Mega":     "No Guard",
    "Heracross-Mega":    "Skill Link",
    "Houndoom-Mega":     "Solar Power",
    "Kangaskhan-Mega":   "Parental Bond",
    "Lopunny-Mega":      "Scrappy",
    "Lucario-Mega":      "Adaptability",
    "Manectric-Mega":    "Intimidate",
    "Medicham-Mega":     "Pure Power",
    "Meganium-Mega":     "Mega Sol",
    "Meowstic-F-Mega":   "Trace",
    "Meowstic-M-Mega":   "Trace",
    "Pidgeot-Mega":      "No Guard",
    "Pinsir-Mega":       "Aerilate",
    "Sableye-Mega":      "Magic Bounce",
    "Scizor-Mega":       "Technician",
    "Scovillain-Mega":   "Spicy Spray",
    "Sharpedo-Mega":     "Strong Jaw",
    "Skarmory-Mega":     "Stalwart",
    "Slowbro-Mega":      "Shell Armor",
    "Starmie-Mega":      "Huge Power",
    "Steelix-Mega":      "Sand Force",
    "Tyranitar-Mega":    "Sand Stream",
    "Venusaur-Mega":     "Thick Fat",
    "Victreebel-Mega":   "Innards Out",
}


def _load() -> None:
    global _SPECIES
    if _SPECIES:
        return
    with open(_DATA_FILE, encoding="utf-8") as f:
        raw: list[dict] = json.load(f)
    _SPECIES = {entry["name"]: entry for entry in raw}
    # Merge mega supplements (not present in slim JSON)
    for name, entry in _MEGA_SUPPLEMENTS.items():
        if name not in _SPECIES:
            _SPECIES[name] = entry


# ── Public API ───────────────────────────────────────────────────────────────

def get_species(name: str) -> Optional[dict]:
    """Return species data dict or None if not found.

    Resolution order: exact match → alias table (in-battle alternate forms,
    e.g. ``"Aegislash-Blade"`` → ``"Aegislash"``) → progressive suffix
    stripping (``"Alcremie-Rainbow-Swirl"`` → ``"Alcremie-Rainbow"`` →
    ``"Alcremie"``).  The last step makes cosmetic/decoration formes — which
    Showdown reports verbatim and which share the base entry's typing and
    stats — resolve without enumerating every variant (caught live by
    data_gaps in the 0.7.7 run).
    """
    _load()
    entry = _SPECIES.get(name)
    if entry is not None:
        return entry
    canonical = _FORM_ALIASES.get(name)
    if canonical and canonical in _SPECIES:
        return _SPECIES[canonical]
    base = name
    while "-" in base:
        base, removed = base.rsplit("-", 1)
        if removed in _DISTINCT_FORME_SUFFIXES:
            return None   # never resolve across a competitively distinct forme
        if base in _SPECIES:
            return _SPECIES[base]
        alias = _FORM_ALIASES.get(base)
        if alias and alias in _SPECIES:
            return _SPECIES[alias]
    return None


def base_stats(name: str) -> Optional[dict[str, int]]:
    """Return ``{'hp','atk','def','spa','spd','spe'}`` or None."""
    entry = get_species(name)
    if entry is None:
        return None
    return {k: entry[k] for k in ("hp", "atk", "def", "spa", "spd", "spe")}


def base_spe(name: str) -> Optional[int]:
    """Return the base Speed stat for a species, or None."""
    entry = get_species(name)
    return entry["spe"] if entry else None


def types_of(name: str) -> Optional[list[str]]:
    """Return ['Type1'] or ['Type1', 'Type2'] for a species, or None."""
    entry = get_species(name)
    return entry["types"] if entry else None


def ability_of(name: str) -> Optional[str]:
    """Return the primary ability for a species, or None if unknown.

    For mega forms, returns the Champions-format mega ability from
    ``_MEGA_ABILITY_SUPPLEMENTS``.  For base forms, returns the first entry
    in the species' ability list (the most common / default ability).
    """
    if name in _MEGA_ABILITY_SUPPLEMENTS:
        return _MEGA_ABILITY_SUPPLEMENTS[name]
    entry = get_species(name)
    if entry is None:
        return None
    abilities = entry.get("abilities", [])
    return abilities[0] if abilities else None


def all_species() -> dict[str, dict]:
    """Return the full ``{name: data}`` mapping (read-only copy)."""
    _load()
    return dict(_SPECIES)


def is_legal(name: str) -> bool:
    """Return True if the species appears in the Champions legal list."""
    _load()
    return name in _SPECIES


# ── Weight table ──────────────────────────────────────────────────────────────
# Pokémon weights in kg, sourced from official game data.
# Used for weight-based move power (Low Kick / Grass Knot / Heat Crash / Heavy Slam).
# Default fallback: 50.0 kg → 80 BP Low Kick (reasonable mid-range estimate).

POKEMON_WEIGHTS: dict[str, float] = {
    # Gen 1
    "Venusaur":       100.0, "Charizard":      90.5, "Blastoise":       85.5,
    "Beedrill":        29.5, "Pidgeot":         39.5, "Arbok":           65.0,
    "Raichu":          30.0, "Clefable":        40.0, "Ninetales":       19.9,
    "Gyarados":       235.0, "Lapras":         220.0, "Snorlax":        460.0,
    "Dragonite":      210.0, "Gengar":          40.5, "Alakazam":        48.0,
    "Machamp":        130.0, "Tentacruel":      55.0, "Slowbro":         78.5,
    "Magneton":        60.0, "Dodrio":          85.2, "Dewgong":        120.0,
    "Haunter":          0.1, "Starmie":         80.0, "Scyther":         56.0,
    "Tauros":          88.4, "Ditto":            4.0, "Aerodactyl":      59.0,
    "Pikachu":          6.0,
    # Gen 2
    "Meganium":       100.5, "Typhlosion":      79.5, "Feraligatr":      88.8,
    "Ariados":         33.5, "Ampharos":        61.5, "Azumarill":       28.5,
    "Politoed":        33.9, "Espeon":          26.5, "Umbreon":         27.0,
    "Slowking":        79.5, "Misdreavus":       1.0, "Forretress":     125.8,
    "Steelix":        400.0, "Scizor":          118.0, "Heracross":      54.0,
    "Skarmory":        50.5, "Houndoom":        35.0, "Kingdra":         152.0,
    "Tyrania":        202.0, "Tyranitar":       202.0, "Blissey":        46.8,
    "Raikou":         178.0, "Entei":           198.0, "Suicune":        187.0,
    # Gen 3
    "Blaziken":        52.0, "Swampert":        81.9, "Sableye":         11.0,
    "Aggron":         360.0, "Medicham":        31.5, "Manectric":       40.2,
    "Sharpedo":        88.8, "Wailord":        398.0, "Camerupt":       220.0,
    "Torkoal":         80.4, "Altaria":         20.6, "Castform":         0.8,
    "Banette":         12.5, "Absol":           47.0, "Salamence":      102.6,
    "Metagross":      550.0, "Glalie":          256.5, "Garchomp":        95.0,
    "Milotic":        162.0, "Chimecho":         1.0,
    # Gen 4
    "Torterra":       310.0, "Infernape":        55.0, "Empoleon":        84.5,
    "Lucario":         54.0, "Hippowdon":       300.0, "Toxicroak":       44.4,
    "Abomasnow":      135.5, "Weavile":          34.0, "Rhyperior":      282.8,
    "Leafeon":         25.5, "Glaceon":          25.9, "Gliscor":         42.5,
    "Mamoswine":      291.0, "Gallade":          52.0, "Froslass":        26.6,
    "Rotom":            0.3, "Rotom-Wash":        0.3, "Rotom-Heat":       0.3,
    "Rotom-Frost":      0.3, "Rotom-Mow":         0.3, "Rotom-Fan":        0.3,
    "Roserade":        14.5, "Rampardos":        102.5, "Bastiodon":      149.5,
    "Lopunny":         33.3, "Spiritomb":       108.0, "Drifloon":         1.2,
    "Drifblim":        15.0, "Togekiss":         38.0, "Yanmega":         51.5,
    "Luxray":          42.0, "Vespiquen":        38.5,
    # Gen 5
    "Serperior":       63.0, "Emboar":          150.0, "Samurott":        94.6,
    "Liepard":         37.5, "Conkeldurr":       87.0, "Reuniclus":       20.1,
    "Vanilluxe":       41.4, "Chandelure":       34.3, "Beartic":        260.0,
    "Golurk":         330.0, "Hydreigon":       160.0, "Volcarona":       46.0,
    "Krookodile":      96.3, "Zoroark":          81.1, "Excadrill":        40.4,
    "Audino":          31.0, "Whimsicott":        6.6, "Stunfisk":        11.0,
    "Stunfisk-Galar":  11.0, "Runerigus":        66.6, "Cofagrigus":      76.5,
    "Garbodor":       107.3, "Emolga":            5.0, "Amoonguss":       10.5,
    # Gen 6
    "Chesnaught":      90.0, "Delphox":          39.0, "Greninja":        40.0,
    "Talonflame":      24.5, "Aromatisse":       15.5, "Slurpuff":         5.0,
    "Aegislash":       53.0, "Clawitzer":        35.3, "Heliolisk":       21.0,
    "Tyrantrum":      270.0, "Aurorus":          225.0, "Sylveon":         23.5,
    "Hawlucha":        21.5, "Dedenne":            2.2, "Goodra":         150.0,
    "Klefki":           3.0, "Trevenant":         71.0, "Gourgeist":       12.5,
    "Gourgeist-Small":  9.5, "Gourgeist-Large":   14.0, "Gourgeist-Super": 39.0,
    "Avalugg":        505.0, "Noivern":           85.0, "Pangoro":        136.0,
    "Dragalge":        81.5, "Furfrou":            28.0, "Arcanine":      155.0,
    "Meowstic-M":       8.5, "Meowstic-F":         8.5, "Vivillon":        17.0,
    "Florges":         10.0, "Gardevoir":         48.4, "Venusaur":       100.0,
    "Pyroar":          81.5,
    # Gen 7
    "Decidueye":       40.0, "Incineroar":        83.0, "Primarina":       44.0,
    "Toucannon":       26.0, "Crabominable":     180.0, "Lycanroc":        25.0,
    "Lycanroc-Dusk":   25.0, "Lycanroc-Midnight": 25.0, "Toxapex":         14.5,
    "Mudsdale":       920.0, "Araquanid":         82.0, "Tsareena":         21.4,
    "Passimian":       82.8, "Oranguru":          76.0, "Mimikyu":           0.7,
    "Drampa":          185.0, "Kommo-o":           78.2, "Salazzle":         22.2,
    # Gen 8
    "Corviknight":     75.0, "Eldegoss":           2.5, "Drednaw":         115.5,
    "Coalossal":      310.5, "Flapple":            14.0, "Appletun":         13.0,
    "Toxtricity":      40.0, "Centiskorch":        120.0, "Hatterene":         5.1,
    "Grimmsnarl":     61.0, "Alcremie":            0.5, "Morpeko":            3.0,
    "Dragapult":       50.0, "Sandaconda":          65.5, "Polteageist":        0.9,
    "Runerigus":       66.6, "Dracovish":          41.5, "Zacian":           110.0,
    "Zamazenta":      235.0, "Calyrex":              1.2,
    # Gen 9
    "Meowscarada":    31.2,  "Skeledirge":         195.0, "Quaquaval":        61.9,
    "Maushold":        1.4,  "Maushold-Four":         2.8, "Garganacl":       305.0,
    "Armarouge":      85.0,  "Ceruledge":            62.0, "Bellibolt":        113.0,
    "Espathra":       90.0,  "Scovillain":           15.0, "Tinkaton":         114.0,
    "Glimmora":       45.0,  "Palafin":              60.2, "Kleavor":           89.0,
    "Wyrdeer":        95.1,  "Basculegion":         110.0, "Basculegion-F":    110.0,
    "Sneasler":       43.0,  "Avalugg-Hisui":       262.4, "Goodra-Hisui":      60.0,
    "Decidueye-Hisui": 37.0, "Samurott-Hisui":       58.2, "Typhlosion-Hisui":  79.5,
    "Arcanine-Hisui": 168.0, "Zoroark-Hisui":        73.0, "Slowbro-Galar":     70.3,
    "Slowking-Galar":  79.5, "Stunfisk-Galar":        11.0, "Farigiraf":        160.0,
    "Orthworm":       310.0, "Annihilape":            56.0, "Kingambit":        120.0,
    # Megas
    "Aerodactyl-Mega":   59.0, "Charizard-Mega-X":   110.5, "Charizard-Mega-Y": 100.5,
    "Blastoise-Mega":   101.1, "Venusaur-Mega":       155.5, "Gengar-Mega":       40.5,
    "Garchomp-Mega":     95.0, "Lucario-Mega":         57.5, "Gardevoir-Mega":    48.4,
    "Alakazam-Mega":     48.0, "Gyarados-Mega":       305.0, "Dragonite-Mega":   210.0,
    "Greninja-Mega":     40.0, "Lopunny-Mega":         33.3, "Kangaskhan-Mega":  100.0,
    "Scizor-Mega":      125.0, "Tyranitar-Mega":      255.0,
    "Pinsir-Mega":       59.0, "Gallade-Mega":         56.4, "Ampharos-Mega":     61.5,
    "Beedrill-Mega":     29.5, "Medicham-Mega":        31.5, "Manectric-Mega":    44.0,
    "Sharpedo-Mega":    130.3, "Camerupt-Mega":       320.5, "Altaria-Mega":      20.6,
    "Glalie-Mega":      350.2, "Starmie-Mega":         80.0, "Houndoom-Mega":     49.0,
    "Heracross-Mega":    62.5, "Pidgeot-Mega":         50.5, "Excadrill-Mega":    40.4,
    "Floette-Mega":       3.0,
}


def get_weight(name: str) -> float:
    """Return weight in kg for *name*.

    Falls back to 50.0 kg (80 BP Low Kick) for any unlisted species, then
    tries the base form by stripping the last hyphen-suffix (e.g. "Drampa-Mega").
    """
    w = POKEMON_WEIGHTS.get(name)
    if w is not None:
        return w
    base = name.rsplit("-", 1)[0]
    if base != name:
        w = POKEMON_WEIGHTS.get(base)
        if w is not None:
            return w
    return 50.0  # default: mid-range → 80 BP Low Kick
