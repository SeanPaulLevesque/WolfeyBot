"""sets.py — Parses the Smogon usage sets file for Champions VGC 2026 Reg MA.

Source: ``sets-gen9championsvgc2026regma-1760.txt`` in this directory.

Per-Pokémon data:
  - raw_count, viability ceiling
  - abilities    : list of (name, pct)
  - items        : list of (name, pct)
  - spreads      : list of ("Nature:HP/Atk/Def/SpA/SpD/Spe", pct)
  - moves        : list of (name, pct)
  - tera_types   : list of (type, pct)
  - teammates    : list of (name, pct)

All lists are sorted by pct descending and exclude the "Other" bucket.
"""
from __future__ import annotations
import re, pathlib
from typing import Optional

_DATA_FILE = (
    pathlib.Path(__file__).parent
    / "sets-gen9championsvgc2026regma-1760.txt"
)

# Spread string pattern: "Jolly:2/32/0/0/0/32"
_SPREAD_RE = re.compile(
    r'^([A-Za-z]+):(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)$'
)
_PCT_RE = re.compile(r'^(.+?)\s+([\d.]+)%\s*$')

_SETS: dict[str, dict] = {}

# Maps lower-case section header text → entry key
_SECTION_MAP: dict[str, str] = {
    "abilities":  "abilities",
    "items":      "items",
    "spreads":    "spreads",
    "moves":      "moves",
    "tera types": "tera_types",
    "teammates":  "teammates",
}

# Formes whose Smogon usage data is filed under a differently-named entry.
# (Base forms that appear only as their Mega in this format — Lopunny, Pidgeot,
#  Beedrill, … — are handled generically by the "<name>-Mega" rule in
#  _resolve_name, so they are NOT listed here.  Anything that still does not
#  resolve, e.g. rare mons or type-shifted formes like Stunfisk-Galar, falls
#  back to a synthetic STAB estimate in damage.incoming_damage.)
_FORME_ALIASES: dict[str, str] = {
    "Meowstic-M":            "Meowstic",
    "Meowstic-F":            "Meowstic",
    "Maushold-Four":         "Maushold",
    "Vivillon-Fancy":        "Vivillon",
    "Vivillon-Pokeball":     "Vivillon",
    "Polteageist-Antique":   "Polteageist",
    "Sinistcha-Masterpiece": "Sinistcha",
    "Gourgeist":             "Gourgeist-Super",
    "Gourgeist-Large":       "Gourgeist-Super",
    "Gourgeist-Small":       "Gourgeist-Super",
}


# ── Parser ───────────────────────────────────────────────────────────────────

def _parse_pct_line(text: str) -> Optional[tuple[str, float]]:
    m = _PCT_RE.match(text.strip())
    if m:
        return m.group(1).strip(), float(m.group(2))
    return None


def _flush(name: Optional[str], entry: Optional[dict]) -> None:
    """Sort and store an entry, if both name and entry are set."""
    if name and entry is not None:
        for key in ("abilities", "items", "spreads", "moves",
                    "tera_types", "teammates"):
            entry[key].sort(key=lambda x: -x[1])
        _SETS[name] = entry


def _load() -> None:
    global _SETS
    if _SETS:
        return

    with open(_DATA_FILE, encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    # ── State-machine parser ─────────────────────────────────────────────────
    # The file has this structure per Pokémon:
    #
    #   +---+          separator
    #   | PokémonName |  ← name header (follows separator; no colon; not a section kw)
    #   +---+
    #   | Raw count: N |  ← metadata (has colon)
    #   | Avg. weight:  |  ← metadata (has colon)
    #   | Viability Ceiling: N |  ← metadata (has colon)
    #   +---+
    #   | Abilities |   ← section header (follows separator; in _SECTION_MAP)
    #   | Ability X pct% |
    #   ...
    #   +---+
    #   | Items |
    #   ...
    #   +---+
    #   +---+          ← double separator → next Pokémon follows
    #
    # Key: after a separator, a | ... | line is either:
    #   (a) a Pokémon name:  not a section keyword, no colon
    #   (b) a section header: in _SECTION_MAP
    #   (c) a metadata line:  contains a colon (Raw count:, Viability:, Avg.:)

    current_name: Optional[str] = None
    entry:        Optional[dict] = None
    current_section: Optional[str] = None
    prev_was_sep: bool = False   # True if the previous non-empty line was +---+

    for raw in raw_lines:
        line = raw.rstrip()

        # ── Separator line ───────────────────────────────────────────────────
        if line.startswith('+-'):
            prev_was_sep = True
            current_section = None
            continue

        if not line.startswith('|'):
            prev_was_sep = False
            continue

        inner = line[1:].strip().rstrip('|').strip()
        if not inner:
            prev_was_sep = False
            continue

        inner_lower = inner.lower()

        # ── Metadata lines (always parsed regardless of position) ────────────
        if inner_lower.startswith('raw count:'):
            if entry is not None:
                m = re.search(r'(\d+)', inner)
                if m:
                    entry["raw_count"] = int(m.group(1))
            prev_was_sep = False
            continue
        if inner_lower.startswith('viability ceiling:'):
            if entry is not None:
                m = re.search(r'(\d+)', inner)
                if m:
                    entry["viability"] = int(m.group(1))
            prev_was_sep = False
            continue
        if inner_lower.startswith('avg.'):
            prev_was_sep = False
            continue

        # ── Lines that follow a separator ────────────────────────────────────
        if prev_was_sep:
            prev_was_sep = False
            if inner_lower in _SECTION_MAP:
                # Section header
                current_section = _SECTION_MAP[inner_lower]
            else:
                # Pokémon name → start new block
                _flush(current_name, entry)
                current_name = inner
                entry = {
                    "raw_count":  0,
                    "viability":  0,
                    "abilities":  [],
                    "items":      [],
                    "spreads":    [],
                    "moves":      [],
                    "tera_types": [],
                    "teammates":  [],
                }
                current_section = None
            continue

        prev_was_sep = False

        # ── Data lines ───────────────────────────────────────────────────────
        if entry is not None and current_section is not None:
            parsed = _parse_pct_line(inner)
            if parsed and parsed[0].lower() != 'other':
                entry[current_section].append(parsed)

    # Flush final entry
    _flush(current_name, entry)


# ── Public API ───────────────────────────────────────────────────────────────

def _resolve_name(name: str) -> Optional[str]:
    """Resolve *name* to an existing usage-data key, or None.

    Order: exact match → explicit forme alias (``_FORME_ALIASES``) →
    ``"<name>-Mega"`` (base forms that appear only as their Mega in this format,
    e.g. Lopunny → Lopunny-Mega).  Names that still do not resolve (rare mons or
    type-shifted formes such as Stunfisk-Galar) return None; callers should fall
    back gracefully rather than treat the mon as having no data.
    """
    _load()
    if name in _SETS:
        return name
    alias = _FORME_ALIASES.get(name)
    if alias and alias in _SETS:
        return alias
    mega = f"{name}-Mega"
    if mega in _SETS:
        return mega
    return None


def get_sets(name: str) -> Optional[dict]:
    """Return full usage data dict for a Pokémon, resolving forme / Mega name
    aliases (see :func:`_resolve_name`), or None if nothing matches.

    All distribution accessors below go through this, so the resolution applies
    uniformly to moves, spreads, abilities, items, tera types and teammates.
    """
    resolved = _resolve_name(name)
    return _SETS.get(resolved) if resolved else None


def item_distribution(name: str) -> list[tuple[str, float]]:
    """Return ``[(item_name, pct), …]`` sorted descending, or ``[]``."""
    d = get_sets(name)
    return list(d["items"]) if d else []


def spread_distribution(name: str) -> list[tuple[str, float]]:
    """Return ``[("Nature:HP/Atk/Def/SpA/SpD/Spe", pct), …]`` sorted
    descending, or ``[]``."""
    d = get_sets(name)
    return list(d["spreads"]) if d else []


def ability_distribution(name: str) -> list[tuple[str, float]]:
    """Return ``[(ability_name, pct), …]`` sorted descending, or ``[]``."""
    d = get_sets(name)
    return list(d["abilities"]) if d else []


def move_distribution(name: str) -> list[tuple[str, float]]:
    """Return ``[(move_name, pct), …]`` sorted descending, or ``[]``."""
    d = get_sets(name)
    return list(d["moves"]) if d else []


def teammate_distribution(name: str) -> list[tuple[str, float]]:
    """Return ``[(teammate_name, pct), …]`` sorted descending, or ``[]``."""
    d = get_sets(name)
    return list(d["teammates"]) if d else []


def parse_spread(spread_str: str) -> Optional[dict]:
    """
    Parse ``'Jolly:2/32/0/0/0/32'`` into::

        {'nature': 'Jolly', 'hp': 2, 'atk': 32, 'def': 0,
         'spa': 0, 'spd': 0, 'spe': 32}

    Returns None on parse failure.
    """
    m = _SPREAD_RE.match(spread_str)
    if not m:
        return None
    keys = ("hp", "atk", "def", "spa", "spd", "spe")
    return {
        "nature": m.group(1),
        **{k: int(m.group(i + 2)) for i, k in enumerate(keys)}
    }


def scarf_probability(name: str) -> float:
    """Return the Choice Scarf usage probability (0.0–1.0) for a Pokémon."""
    for item_name, pct in item_distribution(name):
        if item_name == "Choice Scarf":
            return pct / 100.0
    return 0.0


def all_pokemon() -> list[str]:
    """Return names of all Pokémon present in the sets file."""
    _load()
    return list(_SETS.keys())
