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

Hand-entered supplement
-----------------------
``sets_supplement.json`` (same directory) lets you add usage data for species
absent from the main file — the new Reg M-B Pokémon/megas, until Smogon M-B
stats land.  It is merged into the parsed data at load time and feeds **every**
accessor below (items, abilities, spreads, moves, teammates, ``assumed_forme``,
``mega_stones``, ``mega_forme_for_stone``).  Gap-fill only: a species already in
the main file is never overridden.  See that file's ``_README``/``_schema``.
"""
from __future__ import annotations
import re, json, pathlib
from typing import Optional

_DATA_FILE = (
    pathlib.Path(__file__).parent
    / "sets-gen9championsvgc2026regma-1760.txt"
)
_SUPPLEMENT_FILE = pathlib.Path(__file__).parent / "sets_supplement.json"

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
    # Mid-battle forme changes (|detailschange|): usage data is filed under
    # the base name.  Without these the engine lost the mon's move/set data
    # the moment its forme changed (caught live by data_gaps, 0.7.6 run:
    # Mimikyu-Busted, Aegislash-Blade, Palafin-Hero all flagged).
    "Aegislash-Blade":       "Aegislash",
    "Aegislash-Shield":      "Aegislash",
    "Mimikyu-Busted":        "Mimikyu",
    "Palafin-Hero":          "Palafin",
    "Morpeko-Hangry":        "Morpeko",
    "Greninja-Ash":          "Greninja",
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

    # Fold in any hand-entered usage data for species the main file lacks.
    _merge_supplement()


# ── Hand-entered supplement (sets_supplement.json) ────────────────────────────

def _as_sorted_pairs(d: Optional[dict]) -> list[tuple[str, float]]:
    """Turn a ``{name: pct}`` mapping into a ``[(name, pct), …]`` list sorted by
    pct descending — matching the shape the main parser produces."""
    if not d:
        return []
    return sorted(((str(k), float(v)) for k, v in d.items()), key=lambda x: -x[1])


def _merge_supplement() -> None:
    """Merge ``sets_supplement.json`` into ``_SETS`` (gap-fill; main file wins).

    Top-level keys beginning with ``_`` are documentation (``_README``,
    ``_schema``, ``_example``, ``_todo``) and are ignored.  A malformed file
    raises (fail loud) so a hand-edit typo can't silently drop data.
    """
    if not _SUPPLEMENT_FILE.exists():
        return
    with open(_SUPPLEMENT_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    for name, raw in data.items():
        if name.startswith("_"):          # documentation key — not a species
            continue
        # Gap-fill by default (main usage file wins), EXCEPT entries flagged
        # ``"override": true`` — used when the M-A main file carries a stale
        # pre-mega count for a base that Reg M-B made mega-dominant (e.g. base
        # Raichu's 94720 from before Raichunite existed), so the M-B Pikalytics
        # split must win for the base-vs-mega forme decision.
        if name in _SETS and not raw.get("override"):
            continue
        _SETS[name] = {
            "raw_count":  int(raw.get("raw_count", 0)),
            "viability":  int(raw.get("viability", 0)),
            "abilities":  _as_sorted_pairs(raw.get("abilities")),
            "items":      _as_sorted_pairs(raw.get("items")),
            "spreads":    _as_sorted_pairs(raw.get("spreads")),
            "moves":      _as_sorted_pairs(raw.get("moves")),
            "tera_types": _as_sorted_pairs(raw.get("tera_types")),
            "teammates":  _as_sorted_pairs(raw.get("teammates")),
        }


# ── Public API ───────────────────────────────────────────────────────────────

def _resolve_name(name: str) -> Optional[str]:
    """Resolve *name* to an existing usage-data key, or None.

    Order: exact match → explicit forme alias (``_FORME_ALIASES``) →
    ``"<name>-Mega"`` (base forms that appear only as their Mega in this format,
    e.g. Lopunny → Lopunny-Mega) → progressive suffix stripping
    (``"Alcremie-Rainbow-Swirl"`` → ``"Alcremie"`` — cosmetic formes Showdown
    reports verbatim share the base entry's usage data).  Names that still do
    not resolve return None; callers should fall back gracefully rather than
    treat the mon as having no data.
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
    from .species import _DISTINCT_FORME_SUFFIXES
    base = name
    while "-" in base:
        base, removed = base.rsplit("-", 1)
        if removed in _DISTINCT_FORME_SUFFIXES:
            return None   # never resolve across a competitively distinct forme
        if base in _SETS:
            return base
        alias = _FORME_ALIASES.get(base)
        if alias and alias in _SETS:
            return alias
    return None


def base_forme(name: str) -> str:
    """Strip a Mega suffix so two names referring to the same line compare equal.

    This is the canonical forme-equivalence normaliser — the single source of
    truth used for **identity matching only** (membership-set lookups, reconciling
    predicted-incoming logs against actual-event logs).  It is **not** a modelling
    decision: stats/types/ability/item/damage/speed all keep using the *inferred*
    forme from :func:`assumed_forme`.  ``base_forme`` only answers "are these the
    same species, ignoring mega state?".

    Base and Mega share a movepool, so this is correct for move-level matching too.
    Non-mega names (and unknown names) resolve to themselves.
    """
    if not name:
        return name
    for suf in ("-Mega-X", "-Mega-Y", "-Mega"):
        if name.endswith(suf):
            return name[:-len(suf)]
    return name


def assumed_forme(name: str) -> str:
    """Most-likely battle forme for *name*, weighted by usage raw counts.

    The usage stats file mega formes as separate entries (Charizard vs
    Charizard-Mega-X/-Y), so a pre-mega "Charizard" on the field is drawn
    from the combined population.  If the mega entries together outnumber
    the base entry, return the highest-count mega forme; otherwise return
    *name* unchanged.  Names with no mega entries resolve to themselves.
    """
    _load()
    base = _SETS.get(name)
    megas = [(k, _SETS[k]["raw_count"])
             for k in (f"{name}-Mega", f"{name}-Mega-X", f"{name}-Mega-Y")
             if k in _SETS]
    if not megas:
        return name
    base_count = base["raw_count"] if base else 0
    if sum(c for _, c in megas) > base_count:
        return max(megas, key=lambda t: t[1])[0]
    return name


def default_mega_forme(base: str) -> Optional[str]:
    """The **highest-usage** mega forme for *base*, or None if it has none.

    Unlike :func:`assumed_forme` (which only megas when mega usage outnumbers
    the base population), this assumes a mega is happening and just answers
    *which* one — so it is the data-driven tiebreaker for two-mega species when
    the held stone is unknown (Charizard → -Mega-Y while Y leads X in usage,
    flipping automatically if X ever overtakes).  Used by ``team._mega_form_name``
    as the no-stone fallback instead of a hardcoded X/Y default.
    """
    _load()
    megas = [(k, _SETS[k]["raw_count"])
             for k in (f"{base}-Mega", f"{base}-Mega-X", f"{base}-Mega-Y")
             if k in _SETS]
    if not megas:
        return None
    return max(megas, key=lambda t: t[1])[0]


_MEGA_STONES: Optional[frozenset] = None


def mega_stones() -> frozenset:
    """All mega stones in the format — the (100%) top item of every -Mega entry."""
    global _MEGA_STONES
    if _MEGA_STONES is None:
        _load()
        _MEGA_STONES = frozenset(
            e["items"][0][0]
            for k, e in _SETS.items()
            if "-Mega" in k and e["items"]
        )
    return _MEGA_STONES


_STONE_TO_FORME: Optional[dict] = None


def mega_forme_for_stone(stone: str) -> Optional[str]:
    """Return the ``-Mega`` forme that holds *stone*, or None.

    Each mega stone is forme-specific (Charizardite-X → Charizard-Mega-X,
    Delphoxite → Delphox-Mega), so a Pokémon *revealed* to be holding one will
    evolve to exactly that forme — letting the engine commit to the mega's
    stats before the ``|detailschange|`` arrives, instead of falling back to the
    population-weighted guess (which can be the base forme).
    """
    global _STONE_TO_FORME
    if _STONE_TO_FORME is None:
        _load()
        m: dict[str, str] = {}
        for k, e in _SETS.items():
            if "-Mega" in k and e["items"]:
                m.setdefault(e["items"][0][0], k)
        _STONE_TO_FORME = m
    return _STONE_TO_FORME.get(stone)


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


def all_pokemon() -> list[str]:
    """Return names of all Pokémon present in the sets file."""
    _load()
    return list(_SETS.keys())
