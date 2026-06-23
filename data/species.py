"""species.py — Champions species lookup (types, base stats, formats).

Loaded from ``smogon_champions_slim.json`` in this directory.
Keys are canonical species names as used by Smogon/Showdown
(e.g. "Garchomp", "Charizard-Mega-Y", "Lopunny-Mega").
"""
from __future__ import annotations
import json, pathlib
from typing import Optional

_DATA_FILE = pathlib.Path(__file__).parent / "smogon_champions_slim.json"
# Champions mega formes (types/stats/ability) — not present in the slim usage
# file, so kept as a sibling data file and loaded the same way (no hardcoded
# Python tables; correct any value by editing the JSON).
_MEGA_FILE = pathlib.Path(__file__).parent / "champions_megas.json"

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



def _load() -> None:
    global _SPECIES
    if _SPECIES:
        return
    with open(_DATA_FILE, encoding="utf-8") as f:
        raw: list[dict] = json.load(f)
    _SPECIES = {entry["name"]: entry for entry in raw}
    # Merge Champions mega formes from their data file (not in the slim JSON).
    # Same schema as base species (types/stats/abilities), so all lookups —
    # types_of, base_stats, ability_of — resolve them through the normal path.
    with open(_MEGA_FILE, encoding="utf-8") as f:
        for entry in json.load(f):
            _SPECIES.setdefault(entry["name"], entry)


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


# In-battle formes whose stats the species data does NOT distinguish from the
# base entry — the suffix-strip fallback in get_species returns base-forme stats
# (e.g. "Palafin-Hero" -> Palafin's Zero-form Atk 70, "Aegislash-Blade" ->
# Shield's 50/140).  These are the canonical Champions-legal stat-changing
# transformers; values are the forme's real base stats.  Types and base Speed
# are unchanged from the base entry for both, so only stats need overriding.
_BATTLE_FORME_STATS: dict[str, dict[str, int]] = {
    # Zero-to-Hero: Hero is the permanent post-switch forme (huge Atk).
    "Palafin-Hero":    {"hp": 100, "atk": 160, "def": 97, "spa": 106, "spd": 87, "spe": 100},
    # Stance Change: Blade is the offensive forme; Shield form = base "Aegislash".
    "Aegislash-Blade": {"hp": 60,  "atk": 140, "def": 50, "spa": 140, "spd": 50, "spe": 60},
}


def base_stats(name: str) -> Optional[dict[str, int]]:
    """Return ``{'hp','atk','def','spa','spd','spe'}`` or None."""
    if name in _BATTLE_FORME_STATS:
        return dict(_BATTLE_FORME_STATS[name])
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

    Returns the first entry in the species' ability list (the most common /
    default ability).  Mega formes carry their Champions mega ability as the
    sole entry in that list (from ``champions_megas.json``), so they resolve
    through the same path as base forms.
    """
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
