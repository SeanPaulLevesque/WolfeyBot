"""stat_calc.py — Champions stat formula at Level 50.

The SP system uses 66 total SP (max 32 per stat) replacing the standard
510 EV system.  The SP→EV mapping is now confirmed (web sources + the
Champions stat reference + empirical match against Showdown's own HP values
for our team):

    32 SP == 252 EV  →  1 SP == 7.875 EV

so the classic formula's ``floor(EV/4)`` term becomes
``floor(SP × 7.875 / 4) == floor(SP × 1.96875)``.

This means a maxed stat (32 SP) contributes a ``floor(EV/4)`` term of 63,
exactly as 252 EVs did in the base game.  Prior to 0.8.0 this used the wrong
``1 SP == 1 floor(EV/4) unit`` assumption, which undercounted every invested
stat by ~half for both our team and all opponents.  Only
``sp_to_ev_quarter()`` encodes the mapping; everything else inherits it.
"""
from __future__ import annotations
import math

# ── Nature modifier constants ────────────────────────────────────────────────
BOOSTED  = 1.1
HINDERED = 0.9
NEUTRAL  = 1.0

# (boosted_stat_key, hindered_stat_key).  "none" = neutral.
NATURE_MODS: dict[str, tuple[str, str]] = {
    "Lonely":  ("atk", "def"),  "Brave":   ("atk", "spe"),
    "Adamant": ("atk", "spa"),  "Naughty": ("atk", "spd"),
    "Bold":    ("def", "atk"),  "Relaxed": ("def", "spe"),
    "Impish":  ("def", "spa"),  "Lax":     ("def", "spd"),
    "Timid":   ("spe", "atk"),  "Hasty":   ("spe", "def"),
    "Jolly":   ("spe", "spa"),  "Naive":   ("spe", "spd"),
    "Modest":  ("spa", "atk"),  "Mild":    ("spa", "def"),
    "Quiet":   ("spa", "spe"),  "Rash":    ("spa", "spd"),
    "Calm":    ("spd", "atk"),  "Gentle":  ("spd", "def"),
    "Sassy":   ("spd", "spe"),  "Careful": ("spd", "spa"),
    # Neutral
    "Hardy": ("none","none"), "Docile": ("none","none"),
    "Serious": ("none","none"), "Bashful": ("none","none"),
    "Quirky": ("none","none"),
}

STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")


# ── Core helpers ─────────────────────────────────────────────────────────────

def nature_modifier(nature: str, stat_key: str) -> float:
    """Return 1.1, 0.9, or 1.0 for a given nature and stat key."""
    entry = NATURE_MODS.get(nature)
    if entry is None:
        return NEUTRAL
    boosted, hindered = entry
    if stat_key == boosted:
        return BOOSTED
    if stat_key == hindered:
        return HINDERED
    return NEUTRAL


def sp_to_ev_quarter(sp: int) -> int:
    """
    Convert SP (0–32) to the ``floor(EV/4)`` term used in the stat formula.

    Mapping: 32 SP == 252 EV (1 SP == 7.875 EV), so the term is
    ``floor(SP × 7.875 / 4) == floor(SP × 1.96875)``.  Confirmed against the
    Champions stat reference and Showdown's own HP values (6/6 of our team).
    """
    sp = max(0, min(sp, 32))
    return int(sp * 252 / 32 // 4)


# ── Stat calculators ─────────────────────────────────────────────────────────

def calc_stat(base: int, sp: int, iv: int = 31,
              nature_mod: float = 1.0, level: int = 50) -> int:
    """
    Compute a non-HP stat.

    Formula::
        floor(((2 * base + iv + floor(EV/4)) * level / 100 + 5) * nature_mod)

    With SP substituted for floor(EV/4).
    """
    ev_q = sp_to_ev_quarter(sp)
    inner = math.floor((2 * base + iv + ev_q) * level / 100 + 5)
    return math.floor(inner * nature_mod)


def calc_hp(base: int, sp: int, iv: int = 31, level: int = 50) -> int:
    """
    Compute the HP stat.

    Formula::
        floor((2 * base + iv + floor(EV/4)) * level / 100 + level + 10)
    """
    ev_q = sp_to_ev_quarter(sp)
    return math.floor((2 * base + iv + ev_q) * level / 100 + level + 10)


def calc_speed(base: int, sp: int, nature: str,
               iv: int = 31, level: int = 50) -> int:
    """Compute Speed given a nature string (uses 'spe' stat key)."""
    mod = nature_modifier(nature, "spe")
    return calc_stat(base, sp, iv, mod, level)


def calc_all_stats(base_stats: dict[str, int],
                   sp_spread: dict[str, int],
                   nature: str,
                   iv: int = 31, level: int = 50) -> dict[str, int]:
    """
    Compute all six stats at once.

    Args:
        base_stats:  {'hp':…,'atk':…,'def':…,'spa':…,'spd':…,'spe':…}
        sp_spread:   same keys with SP values (0–32 each)
        nature:      nature name string
        iv:          uniform IV assumption (default 31)
        level:       battle level (default 50)

    Returns:
        dict with the same keys holding computed final stats.
    """
    result: dict[str, int] = {}
    for key in STAT_KEYS:
        base = base_stats.get(key, 0)
        sp   = sp_spread.get(key, 0)
        if key == "hp":
            result[key] = calc_hp(base, sp, iv, level)
        else:
            mod = nature_modifier(nature, key)
            result[key] = calc_stat(base, sp, iv, mod, level)
    return result


def speed_range(base_spe: int,
                min_sp: int = 0, max_sp: int = 32,
                natures: tuple[str, ...] = ("Jolly", "Timid",
                                            "Neutral",
                                            "Adamant", "Modest"),
                iv: int = 31, level: int = 50) -> tuple[int, int]:
    """
    Return ``(min_speed, max_speed)`` over the given SP range and natures.

    Pass ``"Neutral"`` in natures to include nature_mod=1.0.
    """
    speeds: list[int] = []
    for sp in (min_sp, max_sp):
        for nat in natures:
            mod = 1.0 if nat == "Neutral" else nature_modifier(nat, "spe")
            speeds.append(math.floor(
                math.floor((2 * base_spe + iv + sp_to_ev_quarter(sp))
                           * level / 100 + 5) * mod
            ))
    return min(speeds), max(speeds)
