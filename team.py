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

import json, pathlib, re
from dataclasses import dataclass, field
from typing import Optional

from data import calc_all_stats, base_stats as get_base_stats, get_species

# Repo-root ``team.txt`` is the *frozen baseline* — the roster that
# ``turn1_summary.md`` and the test suite are built from.  It is the fallback
# used whenever no named team is selected (see ``get_team``).
TEAM_FILE = pathlib.Path(__file__).parent / "team.txt"

# Named teams for A/B testing live under ``teams/<name>/v<n>.txt`` with a
# ``teams/teams.json`` manifest binding each to an account.  See teams/README.md.
TEAMS_DIR     = pathlib.Path(__file__).parent / "teams"
TEAMS_MANIFEST = TEAMS_DIR / "teams.json"

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


# ── Named teams / manifest ──────────────────────────────────────────────────

_MANIFEST_CACHE: Optional[dict] = None


def _load_manifest() -> dict:
    """Parse ``teams/teams.json`` (name → {label, account, current}); {} if absent.

    Cached for the process — the manifest doesn't change during a run, and a
    single ``set_active_team`` otherwise re-reads it several times (via
    ``current_version`` / ``team_account`` / ``team_file``).  Tests that swap
    ``TEAMS_MANIFEST`` must call :func:`_reset_manifest_cache`.
    """
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is None:
        if TEAMS_MANIFEST.exists():
            try:
                _MANIFEST_CACHE = json.loads(TEAMS_MANIFEST.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                _MANIFEST_CACHE = {}
        else:
            _MANIFEST_CACHE = {}
    return _MANIFEST_CACHE


def _reset_manifest_cache() -> None:
    """Drop the cached manifest (for tests that point ``TEAMS_MANIFEST`` elsewhere)."""
    global _MANIFEST_CACHE
    _MANIFEST_CACHE = None


def list_teams() -> list[str]:
    """Named teams that have a directory under ``teams/`` (sorted)."""
    if not TEAMS_DIR.exists():
        return []
    return sorted(p.name for p in TEAMS_DIR.iterdir() if p.is_dir())


def team_versions(name: str) -> list[str]:
    """Version slugs available for *name* (``v1``, ``v2`` …), sorted naturally."""
    d = TEAMS_DIR / name
    if not d.exists():
        return []
    vers = [p.stem for p in d.glob("v*.txt")]
    # Natural sort by the integer after the leading 'v' (v2 < v10).
    return sorted(vers, key=lambda v: int(re.sub(r"\D", "", v) or 0))


def current_version(name: str) -> Optional[str]:
    """The manifest's ``current`` version for *name*, else the highest on disk."""
    declared = _load_manifest().get(name, {}).get("current")
    if declared:
        return declared
    vers = team_versions(name)
    return vers[-1] if vers else None


def team_account(name: str) -> Optional[str]:
    """The account-profile name bound to *name* in the manifest, or None."""
    return _load_manifest().get(name, {}).get("account")


def team_label(name: str) -> str:
    """Human label for *name* (manifest ``label``, else the slug)."""
    return _load_manifest().get(name, {}).get("label", name)


def resolve_team_spec(spec: str) -> tuple[str, Optional[str]]:
    """Split a ``--team`` spec into (name, version).

    ``"meta-team"``      → ("meta-team", <current version>)
    ``"meta-team@v2"``   → ("meta-team", "v2")
    """
    if "@" in spec:
        name, ver = spec.split("@", 1)
        name, ver = name.strip(), ver.strip()
    else:
        name, ver = spec.strip(), None
    if not ver:
        ver = current_version(name)
    return name, ver


def team_file(name: str, version: Optional[str]) -> pathlib.Path:
    """Path to ``teams/<name>/<version>.txt`` (version defaults to current)."""
    version = version or current_version(name)
    return TEAMS_DIR / name / f"{version}.txt"


def validate_team(name: str, version: Optional[str] = None) -> tuple[bool, str]:
    """Try to load *name*[@version]; return (ok, message).

    Used by ``--list-teams`` to surface a roster that is missing, empty, or has
    a member whose stats failed to compute (the classic ``None`` data bug).
    """
    version = version or current_version(name)
    if version is None:
        return False, "no version files (add v1.txt)"
    fpath = team_file(name, version)
    if not fpath.exists():
        return False, f"{version}.txt missing"
    try:
        members = load_team(fpath)
    except Exception as exc:                                   # pragma: no cover
        return False, f"parse error: {exc}"
    if not members:
        return False, "empty paste"
    for m in members:
        if not m.stats or any(v is None for v in m.stats.values()):
            return False, f"{m.name}: stats failed to compute"
    return True, f"{len(members)} mons OK"


# ── Active team + cached singleton ────────────────────────────────────────────

_CACHED_TEAM: Optional[list[TeamMember]] = None
_ACTIVE_NAME: Optional[str] = None
_ACTIVE_VERSION: Optional[str] = None


def set_active_team(spec: Optional[str], version: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """Select the active named team for this process.

    *spec* may be ``"name"`` or ``"name@version"``; an explicit *version*
    argument overrides the ``@`` suffix.  Passing ``None`` clears the selection
    (reverting to the ``team.txt`` baseline).  Invalidates the cache and returns
    the resolved (name, version).
    """
    global _ACTIVE_NAME, _ACTIVE_VERSION, _CACHED_TEAM
    if spec is None:
        _ACTIVE_NAME = _ACTIVE_VERSION = None
    else:
        name, ver = resolve_team_spec(spec)
        if version is not None:
            ver = version
        _ACTIVE_NAME, _ACTIVE_VERSION = name, ver
    _CACHED_TEAM = None
    return _ACTIVE_NAME, _ACTIVE_VERSION


def active_team() -> Optional[str]:
    return _ACTIVE_NAME


def active_team_version() -> Optional[str]:
    return _ACTIVE_VERSION


def active_team_file() -> Optional[pathlib.Path]:
    """Resolved paste path for the active team, or None for the baseline."""
    if _ACTIVE_NAME is None:
        return None
    return team_file(_ACTIVE_NAME, _ACTIVE_VERSION)


def get_team(reload: bool = False) -> list[TeamMember]:
    """Return the cached team.

    Loads the active named team (set via :func:`set_active_team`) if one is
    selected, otherwise the ``team.txt`` baseline.  No selection → identical to
    the historical behaviour, so tests and ``turn1_summary`` are unaffected.
    """
    global _CACHED_TEAM
    if _CACHED_TEAM is None or reload:
        fpath = active_team_file()           # None → load_team() uses TEAM_FILE
        _CACHED_TEAM = load_team(fpath)
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
