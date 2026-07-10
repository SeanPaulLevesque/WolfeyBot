"""damage.py — Damage calculation for Champions VGC.

Modular design — the core function takes plain numbers and multipliers so
every input can be overridden.  Higher-level helpers derive the multipliers
automatically from species / move / ability data.

Formula (Gen 9, Level 50)
--------------------------
    base  = floor(floor(22 × power × A_eff / D_eff) / 50) + 2
    final = base × targets × weather × crit × STAB × type_eff × burn × other
    range : final × 85/100  …  final × 100/100   (16 equal-probability rolls)

Stat boosts are applied to A / D before the formula:
    A_eff = floor(A × max(2, 2+boost) / max(2, 2−boost))
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from data import (
    get_move,
    is_spread_move, expected_hits,
    types_of, base_stats as get_base_stats,
    spread_distribution, parse_spread,
    calc_all_stats, get_weight,
    note_gap, is_contact, move_has_flag,
    type_boost_multiplier,
)


# ── Type chart ────────────────────────────────────────────────────────────────
# TYPE_CHART[attacking_type][defending_type] = multiplier
# Only non-1.0 values are stored; missing entries default to 1.0.
TYPE_CHART: dict[str, dict[str, float]] = {
    "Normal":   {"Rock": 0.5, "Steel": 0.5, "Ghost": 0.0},
    "Fire":     {"Fire": 0.5, "Water": 0.5, "Rock": 0.5, "Dragon": 0.5,
                 "Grass": 2.0, "Ice": 2.0, "Bug": 2.0, "Steel": 2.0},
    "Water":    {"Water": 0.5, "Grass": 0.5, "Dragon": 0.5,
                 "Fire": 2.0, "Rock": 2.0, "Ground": 2.0},
    "Electric": {"Electric": 0.5, "Grass": 0.5, "Dragon": 0.5, "Ground": 0.0,
                 "Water": 2.0, "Flying": 2.0},
    "Grass":    {"Fire": 0.5, "Poison": 0.5, "Flying": 0.5, "Bug": 0.5,
                 "Dragon": 0.5, "Steel": 0.5, "Grass": 0.5,
                 "Water": 2.0, "Ground": 2.0, "Rock": 2.0},
    "Ice":      {"Fire": 0.5, "Water": 0.5, "Ice": 0.5, "Steel": 0.5,
                 "Grass": 2.0, "Ground": 2.0, "Flying": 2.0, "Dragon": 2.0},
    "Fighting": {"Ghost": 0.0, "Poison": 0.5, "Bug": 0.5, "Psychic": 0.5,
                 "Flying": 0.5, "Fairy": 0.5,
                 "Normal": 2.0, "Ice": 2.0, "Rock": 2.0, "Dark": 2.0, "Steel": 2.0},
    "Poison":   {"Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5,
                 "Steel": 0.0,
                 "Grass": 2.0, "Fairy": 2.0},
    "Ground":   {"Flying": 0.0, "Grass": 0.5, "Bug": 0.5,
                 "Fire": 2.0, "Electric": 2.0, "Poison": 2.0,
                 "Rock": 2.0, "Steel": 2.0},
    "Flying":   {"Electric": 0.5, "Rock": 0.5, "Steel": 0.5,
                 "Grass": 2.0, "Fighting": 2.0, "Bug": 2.0},
    "Psychic":  {"Psychic": 0.5, "Steel": 0.5, "Dark": 0.0,
                 "Fighting": 2.0, "Poison": 2.0},
    "Bug":      {"Fire": 0.5, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5,
                 "Ghost": 0.5, "Steel": 0.5, "Fairy": 0.5,
                 "Grass": 2.0, "Psychic": 2.0, "Dark": 2.0},
    "Rock":     {"Fighting": 0.5, "Ground": 0.5, "Steel": 0.5,
                 "Fire": 2.0, "Ice": 2.0, "Flying": 2.0, "Bug": 2.0},
    "Ghost":    {"Normal": 0.0, "Dark": 0.5,
                 "Ghost": 2.0, "Psychic": 2.0},
    "Dragon":   {"Steel": 0.5, "Fairy": 0.0,
                 "Dragon": 2.0},
    "Dark":     {"Fighting": 0.5, "Dark": 0.5, "Fairy": 0.5,
                 "Ghost": 2.0, "Psychic": 2.0},
    "Steel":    {"Steel": 0.5, "Fire": 0.5, "Water": 0.5, "Electric": 0.5,
                 "Ice": 2.0, "Rock": 2.0, "Fairy": 2.0},
    "Fairy":    {"Fire": 0.5, "Poison": 0.5, "Steel": 0.5,
                 "Fighting": 2.0, "Dragon": 2.0, "Dark": 2.0},
}

# Abilities that change Normal moves to another type and add 1.2× power
_NORMALIZE_ABILITIES: dict[str, str] = {
    "Pixilate":   "Fairy",
    "Refrigerate": "Ice",
    "Aerilate":   "Flying",
    "Galvanize":  "Electric",
    "Dragonize":  "Dragon",  # Feraligatr-Mega (Champions custom mega) — caught
                             # live: Double-Edge into Basculegion predicted 0%
                             # (Normal vs Ghost), dealt 89% as Dragon
    "Normalize":  "Normal",   # forces all moves to Normal (no boost)
}


# ── Weight-based move helpers ─────────────────────────────────────────────────

# Moves whose base power depends on the *target's* weight.
_TARGET_WEIGHT_MOVES: frozenset[str] = frozenset({"Low Kick", "Grass Knot"})

# Moves whose base power depends on the *ratio* of user weight to target weight.
_USER_WEIGHT_MOVES: frozenset[str] = frozenset({"Heat Crash", "Heavy Slam"})

# ── Always-critical-hit moves ─────────────────────────────────────────────────
# These moves always land as critical hits regardless of the opponent's stat
# stages (subject to Battle Armor / Shell Armor, which we do not currently
# track).  The crit multiplier (×1.5) and the Gen 6+ crit boost-clamping rules
# are applied automatically inside full_damage_calc.
_ALWAYS_CRIT_MOVES: frozenset[str] = frozenset({
    "Flower Trick",   # Grass  70 BP Physical — Lilligant-H etc.
    "Frost Breath",   # Ice    60 BP Special
    "Storm Throw",    # Fight  60 BP Physical
})

# Items/abilities that prevent a one-hit KO from full HP (single-hit moves only).
_KO_PREVENTING_ITEMS: frozenset[str] = frozenset({"Focus Sash"})
_KO_PREVENTING_ABILITIES: frozenset[str] = frozenset({"Sturdy"})

# Weather Ball: in weather it becomes the weather's type at 100 BP (base is
# Normal 50 BP).  Keyed by the normalised weather string (see battle.py).
_WEATHER_BALL_TYPE: dict[str, str] = {
    "rain": "Water", "sun": "Fire", "sand": "Rock", "hail": "Ice",
}

# Personal-weather abilities (Champions): the holder's own moves are used as if
# this weather were active — attacker-side only, never the field (no
# Chlorophyll for allies, no effect on moves aimed AT the holder).  Applied by
# rebinding full_damage_calc's local ``weather`` for that attacker's calc.
# Table-driven: the next such ability is one new row.
_PERSONAL_WEATHER_ABILITIES: dict[str, str] = {
    "Mega Sol": "sun",     # Meganium-Mega: Solar Beam no-charge, Fire Weather Ball ×1.5
}

# Abilities whose holder's type changes to the FIRST move it uses after
# entering the field (once per switch-in) — so an unspent holder gets STAB on
# everything, and after the change its current types (parser-tracked
# ``types_override``) drive both STAB and defense.  Greninja-Mega = Protean.
_PROTEAN_ABILITIES: frozenset[str] = frozenset({"Protean", "Libero"})


# ── Terrain (0.41.0) ──────────────────────────────────────────────────────────
# Canonical short keys ("electric" / "grassy" / "psychic" / "misty"), set by
# the parser from |-fieldstart| and assumed from surge abilities (Raichu-Mega-X
# = Electric Surge) by decision.modules._assumed_terrain.  All terrain effects
# apply to GROUNDED mons only.

def is_grounded(species: str, ability: str = "", item: Optional[str] = None) -> bool:
    """Grounded = touches the terrain: not Flying-type, no Ground-immunity
    ability (Levitate / Eelevate), no Air Balloon."""
    if "Flying" in (types_of(species) or []):
        return False
    if _ABILITY_TYPE_IMMUNITY.get(ability) == "Ground":
        return False
    if item == "Air Balloon":
        return False
    return True


# Moves halved by Grassy Terrain's protective canopy (vs grounded targets).
_GRASSY_HALVED_MOVES = frozenset({"Earthquake", "Bulldoze", "Magnitude"})


def terrain_modifier(move_name: str, eff_type: str, terrain: Optional[str],
                     atk_grounded: bool, def_grounded: bool) -> float:
    """Combined terrain damage multiplier (×1.0 when no terrain applies).

    * Electric/Grassy/Psychic: the matching move type ×1.3 from a GROUNDED
      attacker.
    * Misty: Dragon moves ×0.5 into a grounded target.
    * Grassy: Earthquake/Bulldoze/Magnitude ×0.5 into a grounded target.
    """
    if not terrain:
        return 1.0
    mult = 1.0
    boost = {"electric": "Electric", "grassy": "Grass", "psychic": "Psychic"}
    if atk_grounded and boost.get(terrain) == eff_type:
        mult *= 1.3
    if def_grounded:
        if terrain == "misty" and eff_type == "Dragon":
            mult *= 0.5
        if terrain == "grassy" and move_name in _GRASSY_HALVED_MOVES:
            mult *= 0.5
    return mult

# Foul Play computes damage from the *target's* Attack stat (and the target's
# Attack stat stages), not the user's.
_FOUL_PLAY = "Foul Play"
_BODY_PRESS = "Body Press"

# Move contact / slicing / punch / bite flags live in data/move_flags.py
# (positive per-move sets, used by Tough Claws and future Sharpness/Iron Fist/
# Strong Jaw).  Imported via ``is_contact`` above.


def _low_kick_power(target_weight_kg: float) -> int:
    """Return Low Kick / Grass Knot power from target weight (kg)."""
    if target_weight_kg <  10.0: return 20
    if target_weight_kg <  25.0: return 40
    if target_weight_kg <  50.0: return 60
    if target_weight_kg < 100.0: return 80
    if target_weight_kg < 200.0: return 100
    return 120


def _heat_crash_power(user_weight_kg: float, target_weight_kg: float) -> int:
    """Return Heat Crash / Heavy Slam power from user-to-target weight ratio."""
    if target_weight_kg <= 0:
        return 40
    ratio = user_weight_kg / target_weight_kg
    if ratio >= 5: return 120
    if ratio >= 4: return 100
    if ratio >= 3: return 80
    if ratio >= 2: return 60
    return 40


# ── Data containers ───────────────────────────────────────────────────────────

@dataclass
class DamageResult:
    """Full result of a single damage calculation."""
    move:            str
    power:           int
    category:        str          # "Physical" | "Special" | "Status"
    effective_type:  str          # after ability type changes

    attacker:        str
    defender:        str

    stab:            float
    effectiveness:   float
    atk_modifier:    float
    def_modifier:    float

    damage_min:      int
    damage_max:      int
    damage_avg:      float

    defender_hp:     int = 0
    hits:            float = 1.0
    ko_prevented:    bool = False

    @property
    def hp_fraction_min(self) -> float:
        return self.damage_min / self.defender_hp if self.defender_hp else 0.0

    @property
    def hp_fraction_max(self) -> float:
        return self.damage_max / self.defender_hp if self.defender_hp else 0.0

    @property
    def hp_fraction_avg(self) -> float:
        return self.damage_avg / self.defender_hp if self.defender_hp else 0.0

    @property
    def is_ohko(self) -> bool:
        """True if the minimum damage roll knocks out the defender."""
        return (self.defender_hp > 0 and self.damage_min >= self.defender_hp
                and not self.ko_prevented)

    @property
    def ohko_with_max_roll(self) -> bool:
        """True if the maximum damage roll knocks out the defender."""
        return (self.defender_hp > 0 and self.damage_max >= self.defender_hp
                and not self.ko_prevented)

    @property
    def is_2hko(self) -> bool:
        """True if two average hits KO (useful for chip damage planning)."""
        return self.defender_hp > 0 and self.damage_avg * 2 >= self.defender_hp

    def summary(self) -> str:
        eff_tag = ""
        if self.effectiveness == 0:   eff_tag = " [immune]"
        elif self.effectiveness < 1:  eff_tag = " [resisted]"
        elif self.effectiveness > 1:  eff_tag = " [super effective]"
        ko_tag = " OHKO" if self.is_ohko else (" 2HKO" if self.is_2hko else "")
        pct = f"{self.hp_fraction_avg:.0%}" if self.defender_hp else "?%"
        return (f"{self.move} -> {self.defender}: "
                f"{self.damage_min}-{self.damage_max} ({pct}){eff_tag}{ko_tag}")


# ── Type helpers ──────────────────────────────────────────────────────────────

def type_effectiveness(move_type: str, defender_types: list[str]) -> float:
    """
    Return the combined type effectiveness multiplier.

    Handles dual-type defenders (multipliers are compounded).
    Returns 0.0, 0.25, 0.5, 1.0, 2.0, or 4.0.
    """
    chart = TYPE_CHART.get(move_type, {})
    mult = 1.0
    for def_type in defender_types:
        mult *= chart.get(def_type, 1.0)
    return mult


def effective_move_type(move_type: str, attacker_ability: str) -> str:
    """
    Return the move's actual type after ability type-changing effects.

    Pixilate / Refrigerate / Aerilate / Galvanize convert Normal → other type.
    """
    if move_type == "Normal" and attacker_ability in _NORMALIZE_ABILITIES:
        return _NORMALIZE_ABILITIES[attacker_ability]
    return move_type


def stab_multiplier(eff_type: str, attacker_types: list[str],
                    attacker_ability: str = "") -> float:
    """
    Return the STAB multiplier.

    * 2.0 if Adaptability and STAB type
    * 1.5 if normal STAB
    * 1.0 otherwise
    """
    if eff_type not in attacker_types:
        return 1.0
    if attacker_ability == "Adaptability":
        return 2.0
    return 1.5


# ── Stat helpers ──────────────────────────────────────────────────────────────

def stat_with_boost(base: int, boost: int) -> int:
    """Apply a stat stage (−6 … +6) to a stat value."""
    if boost == 0:
        return base
    if boost > 0:
        return math.floor(base * (2 + boost) / 2)
    return math.floor(base * 2 / (2 - boost))


# ── Modifier helpers ──────────────────────────────────────────────────────────

# Pinch abilities: own-type ×1.5 when the user is at ≤⅓ HP.
_PINCH_ABILITIES: dict[str, str] = {
    "Blaze": "Fire", "Overgrow": "Grass", "Torrent": "Water", "Swarm": "Bug",
}


def atk_modifier(
        ability: str,
        item: Optional[str],
        move_name: str,
        move_type: str,
        power: int,
        category: str,
        *,
        original_type: str = "",
        weather: Optional[str] = None,
        attacker_hp_fraction: float = 1.0,
        attacker_status: str = "",
        ally_faint_count: int = 0,
        flash_fire_active: bool = False,
) -> float:
    """
    Return the combined offensive modifier from ability + item.

    Covers the most strategically important cases.  Complex
    interactions (Sheer Force secondary effects, etc.) are approximated.

    Args:
        move_type:     The *effective* move type (after any ability type change).
        original_type: The move's raw type before ability conversion.  Pass this
                       so Pixilate / Aerilate / etc. can detect that the move was
                       originally Normal and apply their 1.2× bonus correctly.
        weather:       Current weather ("sun"/"rain"/"sand"/"hail") for
                       weather-gated abilities (Solar Power, Sand Force).
        attacker_hp_fraction: User's current HP fraction (0–1) for pinch
                       abilities (Blaze/Overgrow/Torrent/Swarm, Defeatist).
        attacker_status: User's status ("brn"/"psn"/"tox"/… or "") for
                       status-gated abilities (Guts, Flare Boost, Toxic Boost).
        ally_faint_count: Fainted teammates on the user's side (Supreme Overlord).
        flash_fire_active: True once the user has absorbed a Fire move this stint
                       (Flash Fire's +50% Fire boost).
    """
    mod = 1.0

    # ── Ability ──────────────────────────────────────────────────────────────
    if ability == "Adaptability":
        pass  # handled in stab_multiplier

    elif ability in _NORMALIZE_ABILITIES:
        # Pixilate / Aerilate / etc. add 1.2× when they convert a Normal move.
        # Use original_type when available (full_damage_calc passes raw_type);
        # fall back to move_type for callers that don't supply it.
        src_type = original_type if original_type else move_type
        if src_type == "Normal" and ability != "Normalize":
            mod *= 1.2

    elif ability == "Technician" and power <= 60:
        mod *= 1.5

    elif ability == "Sheer Force":
        # Approximate: most moves with secondary effects get ~1.3×
        # Exact list is complex; mark moves that are known Sheer Force targets
        mod *= 1.3   # conservative; caller can override

    elif ability == "Hustle" and category == "Physical":
        mod *= 1.5

    elif ability == "Solar Power" and weather == "sun" and category == "Special":
        mod *= 1.5   # SpA ×1.5 in sun only (was wrongly applied in all weather)

    elif ability == "Transistor" and move_type == "Electric":
        mod *= 1.3   # +30% Electric (Champions reference)

    elif ability == "Fire Mane" and move_type == "Fire":
        mod *= 1.5   # +50% Fire (Mega Pyroar, Reg M-B)

    elif ability == "Tough Claws" and is_contact(move_name):
        mod *= 1.3   # contact moves only (see data/move_flags.py)

    elif ability == "Sharpness" and move_has_flag(move_name, "slicing"):
        mod *= 1.5   # slicing moves (Kowtow Cleave, Night Slash, Dragon Claw, …)

    elif ability == "Strong Jaw" and move_has_flag(move_name, "bite"):
        mod *= 1.5   # biting moves (Crunch, Ice Fang, Psychic Fangs, …)

    elif ability == "Iron Fist" and move_has_flag(move_name, "punch"):
        mod *= 1.2   # punching moves (Ice Punch, Mach Punch, Meteor Mash, …)

    elif ability == "Mega Launcher" and move_has_flag(move_name, "pulse"):
        mod *= 1.5   # pulse/aura moves (Aura Sphere, Dark/Dragon/Water Pulse, …)

    elif ability == "Punk Rock" and move_has_flag(move_name, "sound"):
        mod *= 1.3   # sound moves (Boomburst, Hyper Voice, Bug Buzz, …)

    elif ability == "Reckless" and move_has_flag(move_name, "recoil"):
        mod *= 1.2   # recoil/crash moves (Flare Blitz, Brave Bird, Wave Crash, …)

    elif ability == "Fairy Aura" and move_type == "Fairy":
        mod *= 1.33  # +33% all Fairy moves (both sides — modelled per-attacker)

    elif ability == "Steely Spirit" and move_type == "Steel":
        mod *= 1.5   # +50% Steel (self; ally boost needs doubles context — TODO)

    elif ability == "Water Bubble" and move_type == "Water":
        mod *= 2.0   # +100% Water (defensive Fire-halving is in def_modifier)

    elif ability in ("Huge Power", "Pure Power") and category == "Physical":
        mod *= 2.0   # doubles Attack (≈ ×2 physical damage) — Medicham-Mega etc.

    elif ability == "Gorilla Tactics" and category == "Physical":
        mod *= 1.5   # +50% Attack (Choice-lock side effect not modelled)

    # ── Conditional-fact abilities (need attacker HP / status / weather / faint) ──
    elif (ability in _PINCH_ABILITIES
          and move_type == _PINCH_ABILITIES[ability]
          and attacker_hp_fraction <= 1.0 / 3.0):
        mod *= 1.5   # Blaze/Overgrow/Torrent/Swarm at ≤⅓ HP

    elif ability == "Defeatist" and attacker_hp_fraction <= 0.5:
        mod *= 0.5   # Atk & SpA both halved at ≤½ HP

    elif ability == "Guts" and attacker_status and category == "Physical":
        mod *= 1.5   # Atk ×1.5 while statused (also ignores burn's Atk drop)

    elif ability == "Flare Boost" and attacker_status == "brn" and category == "Special":
        mod *= 1.5   # SpA ×1.5 while burned

    elif (ability == "Toxic Boost" and attacker_status in ("psn", "tox")
          and category == "Physical"):
        mod *= 1.5   # Atk ×1.5 while poisoned

    elif (ability == "Sand Force" and weather == "sand"
          and move_type in ("Rock", "Ground", "Steel")):
        mod *= 1.3   # Rock/Ground/Steel ×1.3 in sand

    elif ability == "Supreme Overlord" and ally_faint_count > 0:
        mod *= 1.0 + 0.1 * min(ally_faint_count, 5)   # +10% Atk&SpA per faint, cap +50%

    elif ability == "Flash Fire" and flash_fire_active and move_type == "Fire":
        mod *= 1.5   # Fire ×1.5 once a Fire move has been absorbed this stint

    # Flag-keyed abilities (Tough Claws/Sharpness/Strong Jaw/Iron Fist/Mega
    # Launcher/Punk Rock/Reckless) read the positive sets in data/move_flags.py.
    # Doubles/ally abilities (Battery/Power Spot/Plus/Minus/Aura both-sides) and
    # prediction-gated ones (Analytic/Merciless/Stakeout) are not yet wired.

    # ── Item ─────────────────────────────────────────────────────────────────
    if item == "Choice Band" and category == "Physical":
        mod *= 1.5
    elif item == "Choice Specs" and category == "Special":
        mod *= 1.5
    elif item == "Life Orb":
        mod *= 1.3
    else:
        # Permanent type-boosting items (Charcoal/Mystic Water/… → ×1.2 on the
        # matching type) via data/items.py — returns 1.0 for any other item.
        mod *= type_boost_multiplier(item, move_type)

    return mod


def def_modifier(
        ability: str,
        item: Optional[str],
        move_type: str,
        category: str,
        effectiveness: float,
        is_full_hp: bool = True,
) -> float:
    """
    Return the combined defensive modifier from ability + item.

    A value < 1.0 means the defender takes less damage (e.g. Multiscale).
    A value > 1.0 means the defender takes more damage (rare).
    """
    mod = 1.0

    # ── Ability ──────────────────────────────────────────────────────────────
    if ability == "Multiscale" and is_full_hp:
        mod *= 0.5

    elif ability in ("Filter", "Solid Rock", "Prism Armor") and effectiveness > 1.0:
        mod *= 0.75

    elif ability == "Ice Scales" and category == "Special":
        mod *= 0.5

    elif ability == "Fur Coat" and category == "Physical":
        mod *= 0.5

    elif ability == "Fluffy":
        if category == "Physical":
            mod *= 0.5
        if move_type == "Fire":
            mod *= 2.0   # Fluffy doubles Fire damage (separate multiplication)

    elif ability == "Thick Fat" and move_type in ("Fire", "Ice"):
        mod *= 0.5

    elif ability == "Heatproof" and move_type == "Fire":
        mod *= 0.5

    elif ability == "Water Bubble" and move_type == "Fire":
        mod *= 0.5

    elif ability == "Punk Rock" and category == "Special":
        # Punk Rock halves sound-based moves — hard to detect without tagging
        # moves as sound-based; leave for caller to specify
        pass

    # ── Item ─────────────────────────────────────────────────────────────────
    if item == "Assault Vest" and category == "Special":
        mod *= (2 / 3)   # SpDef × 1.5 → effective ÷ 1.5 on incoming SpA

    elif item == "Rocky Helmet":
        pass   # only deals recoil, doesn't reduce damage

    # Resistance berries
    elif item == "Occa Berry"  and move_type == "Fire"     and effectiveness >= 2: mod *= 0.5
    elif item == "Passho Berry" and move_type == "Water"   and effectiveness >= 2: mod *= 0.5
    elif item == "Wacan Berry" and move_type == "Electric" and effectiveness >= 2: mod *= 0.5
    elif item == "Rindo Berry" and move_type == "Grass"    and effectiveness >= 2: mod *= 0.5
    elif item == "Yache Berry" and move_type == "Ice"      and effectiveness >= 2: mod *= 0.5
    elif item == "Chople Berry" and move_type == "Fighting" and effectiveness >= 2: mod *= 0.5
    elif item == "Kebia Berry" and move_type == "Poison"   and effectiveness >= 2: mod *= 0.5
    elif item == "Shuca Berry" and move_type == "Ground"   and effectiveness >= 2: mod *= 0.5
    elif item == "Coba Berry"  and move_type == "Flying"   and effectiveness >= 2: mod *= 0.5
    elif item == "Payapa Berry" and move_type == "Psychic" and effectiveness >= 2: mod *= 0.5
    elif item == "Tanga Berry" and move_type == "Bug"      and effectiveness >= 2: mod *= 0.5
    elif item == "Charti Berry" and move_type == "Rock"    and effectiveness >= 2: mod *= 0.5
    elif item == "Kasib Berry" and move_type == "Ghost"    and effectiveness >= 2: mod *= 0.5
    elif item == "Haban Berry" and move_type == "Dragon"   and effectiveness >= 2: mod *= 0.5
    elif item == "Colbur Berry" and move_type == "Dark"    and effectiveness >= 2: mod *= 0.5
    elif item == "Babiri Berry" and move_type == "Steel"   and effectiveness >= 2: mod *= 0.5
    elif item == "Roseli Berry" and move_type == "Fairy"   and effectiveness >= 2: mod *= 0.5
    elif item == "Chilan Berry" and move_type == "Normal":                         mod *= 0.5

    return mod


def weather_modifier(move_type: str, weather: Optional[str]) -> float:
    """Return 1.5, 0.5, or 1.0 based on weather and move type."""
    if weather == "sun":
        if move_type == "Fire":   return 1.5
        if move_type == "Water":  return 0.5
    elif weather == "rain":
        if move_type == "Water":  return 1.5
        if move_type == "Fire":   return 0.5
    return 1.0


# ── Core formula ─────────────────────────────────────────────────────────────

def calc_damage(
        power: int,
        atk: int,
        def_: int,
        *,
        stab: float = 1.0,
        effectiveness: float = 1.0,
        spread_move: bool = False,
        weather: float = 1.0,           # pre-computed weather multiplier
        crit: bool = False,
        atk_boost: int = 0,
        def_boost: int = 0,
        atk_mod: float = 1.0,
        def_mod: float = 1.0,
        burn: bool = False,
        level: int = 50,
) -> tuple[int, int, float]:
    """
    Compute ``(min_damage, max_damage, avg_damage)`` from raw inputs.

    This is the fully modular core — every value can be overridden by the
    caller.

    Args:
        power:          Base power of the move.
        atk:            Attacker's offensive stat (Atk or SpA).
        def_:           Defender's defensive stat (Def or SpD).
        stab:           1.0, 1.5, or 2.0.
        effectiveness:  0.0, 0.25, 0.5, 1.0, 2.0, or 4.0.
        spread_move:    True if move hits multiple targets (0.75× in doubles).
        weather:        Pre-computed weather multiplier (1.5/0.5/1.0).
        crit:           If True, apply 1.5× crit multiplier.
        atk_boost:      Attacker speed stage (−6 … +6).
        def_boost:      Defender speed stage (−6 … +6).
        atk_mod:        Combined ability+item multiplier on attack.
        def_mod:        Combined ability+item multiplier on defense.
        burn:           True if attacker is burned (physical moves ×0.5).
        level:          Battle level (default 50).

    Returns:
        ``(damage_min, damage_max, damage_avg)``
    """
    if power == 0 or effectiveness == 0.0:
        return (0, 0, 0.0)

    # Gen 6+ crit mechanics: negative attacker boosts and positive defender
    # boosts are both ignored on a critical hit.
    if crit:
        atk_boost = max(atk_boost, 0)
        def_boost = min(def_boost, 0)

    # Apply stat boosts
    A = stat_with_boost(atk, atk_boost)
    D = stat_with_boost(def_, def_boost)

    # Apply offensive stat modifier (ability/item)
    A = math.floor(A * atk_mod)
    if D == 0:
        D = 1   # guard against divide-by-zero

    # Base damage (A/D step)
    lv_factor = math.floor(2 * level / 5 + 2)   # = 22 at Lv50 (Gen 5+ formula)
    base = math.floor(math.floor(lv_factor * power * A / D) / 50) + 2
    # The outer /50 + 2 is the standard Gen 5+ level factor step.

    # Chained multipliers (order: spread → weather → crit → STAB → type eff →
    #   def modifier → burn).  def_mod is a *damage* fraction (<1 = less damage,
    #   e.g. Multiscale 0.5, AV 2/3, Filter 0.75) applied here, NOT to the D
    #   stat, so that halving def_mod correctly halves damage.
    if spread_move:
        base = math.floor(base * 0.75)
    base = math.floor(base * weather)
    if crit:
        base = math.floor(base * 1.5)
    base = math.floor(base * stab)
    base = math.floor(base * effectiveness)
    base = math.floor(base * def_mod)
    if burn:
        base = math.floor(base * 0.5)

    # Random roll range (85–100)
    # Random roll range: 16 equally-probable rolls from 85/100 to 100/100.
    # Average roll = (85+86+…+100) / 16 / 100 = 1480/1600 = 0.925.
    damage_min = math.floor(base * 85 / 100)
    damage_max = base
    damage_avg = base * 0.925

    return (damage_min, damage_max, damage_avg)


# Abilities that grant full immunity to an entire move type (damage → 0).
_ABILITY_TYPE_IMMUNITY: dict[str, str] = {
    "Levitate": "Ground", "Earth Eater": "Ground", "Eelevate": "Ground",
    "Flash Fire": "Fire", "Well-Baked Body": "Fire",
    "Water Absorb": "Water", "Dry Skin": "Water", "Storm Drain": "Water",
    "Volt Absorb": "Electric", "Lightning Rod": "Electric", "Motor Drive": "Electric",
    "Sap Sipper": "Grass",
}


def screen_modifier(category: str, screens, crit: bool = False) -> float:
    """Doubles light-screen damage reduction (×2/3).

    Reflect halves physical, Light Screen halves special, Aurora Veil both —
    each reduces damage to 2/3 in doubles (½ in singles; we play doubles).
    Critical hits bypass screens entirely.
    """
    if crit or not screens:
        return 1.0
    if "auroraveil" in screens:
        return 2.0 / 3.0
    if category == "Physical" and "reflect" in screens:
        return 2.0 / 3.0
    if category == "Special" and "lightscreen" in screens:
        return 2.0 / 3.0
    return 1.0


# ── High-level interface ──────────────────────────────────────────────────────

def full_damage_calc(
        move_name: str,
        attacker_species: str,
        defender_species: str,
        attacker_stats: dict[str, int],
        defender_stats: dict[str, int],
        *,
        attacker_ability: str = "",
        defender_ability: str = "",
        attacker_item: Optional[str] = None,
        defender_item: Optional[str] = None,
        defender_has_item: bool = True,
        attacker_boosts: Optional[dict[str, int]] = None,
        defender_boosts: Optional[dict[str, int]] = None,
        weather: Optional[str] = None,
        terrain: Optional[str] = None,
        attacker_types: Optional[list[str]] = None,
        defender_types: Optional[list[str]] = None,
        crit: bool = False,
        defender_is_full_hp: bool = True,
        ally_faint_count: int = 0,
        times_hit: int = 0,
        defender_screens=None,
        attacker_hp_fraction: float = 1.0,
        attacker_status: str = "",
        flash_fire_active: bool = False,
) -> DamageResult:
    """
    Compute a full damage result for *move_name* from *attacker_species*
    against *defender_species*.

    Species names are used to look up types.  Stats are passed explicitly so
    the caller can supply either exact (own team) or estimated (opponent) values.
    """
    boosts_atk = attacker_boosts or {}
    boosts_def = defender_boosts or {}

    # ── Move data ─────────────────────────────────────────────────────────────
    move_data = get_move(move_name)
    if move_data is None:
        return DamageResult(
            move=move_name, power=0, category="Status",
            effective_type="Normal",
            attacker=attacker_species, defender=defender_species,
            stab=1.0, effectiveness=1.0, atk_modifier=1.0, def_modifier=1.0,
            damage_min=0, damage_max=0, damage_avg=0.0,
            hits=1.0, ko_prevented=False,
        )

    power    = move_data.get("power") or 0
    category = move_data.get("category", "Status")
    raw_type = move_data.get("type", "Normal")

    # Personal weather (Champions): abilities whose holder's MOVES are used as
    # if a weather were active — e.g. Mega Sol ("…as if the effects of Sunny
    # Day were active").  Rebinding the local ``weather`` scopes it to exactly
    # this attacker's calc: its Weather Ball becomes Fire 100 BP, its Fire
    # moves get the ×1.5 sun boost, Solar-Power-style attacker mods see sun —
    # while the FIELD weather (and every other mon's calc, incoming or
    # outgoing) is untouched.  Overrides real field weather for this attacker
    # (its moves are "used as if" sunny regardless of what's actually up).
    weather = _PERSONAL_WEATHER_ABILITIES.get(attacker_ability, weather)

    # Weather Ball: in weather it changes to the weather's type and doubles its
    # base power (50 → 100).  Without this it scores as a feeble Normal move —
    # the cause of badly under-predicting rain Politoed/Pelipper incoming.
    if move_name == "Weather Ball" and weather in _WEATHER_BALL_TYPE:
        raw_type = _WEATHER_BALL_TYPE[weather]
        power = 100

    # Terrain-powered moves (grounded-gated below via terrain_modifier for the
    # ×1.3; these change BASE POWER).  Rising Voltage doubles vs a grounded
    # target on Electric Terrain (the 42%→100% Jolteon under-read); Expanding
    # Force is ×1.5 from a grounded user on Psychic Terrain.
    atk_grounded = is_grounded(attacker_species, attacker_ability, attacker_item)
    def_grounded = is_grounded(defender_species, defender_ability, defender_item)
    if move_name == "Rising Voltage" and terrain == "electric" and def_grounded:
        power *= 2
    if move_name == "Expanding Force" and terrain == "psychic" and atk_grounded:
        power = int(power * 1.5)

    # Moves that always land as critical hits regardless of the opponent's
    # stat stages (Gen 6+ rules).  Battle Armor / Shell Armor immunity is not
    # currently tracked; callers that know the defender has one of those
    # abilities can pass crit=False explicitly to override.
    if move_name in _ALWAYS_CRIT_MOVES:
        crit = True

    # Scale power by expected hit count so multi-hit moves (Dual Wingbeat = 2×40)
    # aren't undervalued versus single-hit moves with higher base power (Ice Fang = 65).
    # Round to nearest int to keep the formula operating on integer power.
    if power > 0:
        power = round(power * expected_hits(move_name))

    # Last Respects: base 50 BP + 50 per fainted ally (capped at X=100 per description,
    # but practically capped at team size − 1 in VGC).
    if move_name == "Last Respects" and ally_faint_count > 0:
        power = 50 + min(ally_faint_count, 100) * 50

    # Rage Fist (Annihilape): base 50 BP + 50 per time the user has been hit this
    # field stint, capped at 350 (6 hits).  Stacks reset on switch-out (Reg M-B),
    # which is handled upstream by ``times_hit`` living on the per-stint Pokemon.
    if move_name == "Rage Fist" and times_hit > 0:
        power = 50 + min(times_hit, 6) * 50

    # Weight-based variable-power moves: compute effective BP from species weights.
    # These moves have power=0 in the database; without this block they would be
    # dropped by the early-return below and never scored.
    if move_name in _TARGET_WEIGHT_MOVES:
        target_kg = get_weight(defender_species)
        power = _low_kick_power(target_kg)
    elif move_name in _USER_WEIGHT_MOVES:
        user_kg   = get_weight(attacker_species)
        target_kg = get_weight(defender_species)
        power = _heat_crash_power(user_kg, target_kg)

    # Knock Off: ×1.5 power when the target is holding a removable item (it gets
    # knocked off after the hit).  We don't model the unremovable edge cases
    # (Sticky Hold, a mon's own matching Mega Stone / Z-Crystal) — those are rare
    # and only cause a small over-prediction, not the under-prediction this fixes.
    if move_name == "Knock Off" and defender_item:
        power = round(power * 1.5)

    # Poltergeist fails outright if the target holds no item.  `defender_has_item`
    # is the *belief* the target carries one (True by default / when unknown —
    # VGC mons almost always do); it goes False only on positive evidence the
    # item is gone (consumed berry, Knocked Off, an itemless set).  Distinct from
    # `defender_item` truthiness, which is also None when we merely don't know
    # *which* item it is.  power=0 routes into the early return below → 0 damage.
    if move_name == "Poltergeist" and not defender_has_item:
        power = 0

    if category == "Status" or power == 0:
        return DamageResult(
            move=move_name, power=0, category=category,
            effective_type=raw_type,
            attacker=attacker_species, defender=defender_species,
            stab=1.0, effectiveness=1.0, atk_modifier=1.0, def_modifier=1.0,
            damage_min=0, damage_max=0, damage_avg=0.0,
            hits=1.0, ko_prevented=False,
        )

    # ── Effective type (ability type changes) ─────────────────────────────────
    eff_type = effective_move_type(raw_type, attacker_ability)

    # ── Types ─────────────────────────────────────────────────────────────────
    # *attacker_types* / *defender_types* override the species' base typing —
    # the in-battle current types after a Protean typechange (or Soak etc.),
    # tracked by the parser on ``mon.types_override``.
    atk_types = (attacker_types if attacker_types is not None
                 else types_of(attacker_species) or [])
    def_types = (defender_types if defender_types is not None
                 else types_of(defender_species) or [])
    # Missing types make every matchup neutral (×1.0) — the Aegislash-Blade
    # class of bug.  Flag it so the battle log surfaces the gap.
    if not atk_types:
        note_gap("types", attacker_species)
    if not def_types:
        note_gap("types", defender_species)

    # ── Multipliers ───────────────────────────────────────────────────────────
    stab  = stab_multiplier(eff_type, atk_types, attacker_ability)
    # Protean / Libero (Greninja-Mega): the FIRST move after entering changes
    # the user's type to the move's type — so while the change is unspent
    # (no ``attacker_types`` override recorded yet), EVERY candidate move is
    # effectively STAB: choosing it makes it match.  Once the parser has seen
    # the |-start|typechange| (override passed in), normal STAB vs the new
    # typing applies — a second off-type move gets nothing.
    if (stab == 1.0 and attacker_types is None
            and attacker_ability in _PROTEAN_ABILITIES):
        stab = 1.5
    eff   = type_effectiveness(eff_type, def_types)
    # Freeze-Dry is super-effective (2×) against Water instead of the usual ×0.5.
    # type_effectiveness has no move context, so patch the Water component here:
    # ×4 converts Ice's normal 0.5× contribution into the 2× Freeze-Dry deals
    # (the other type's contribution, if any, is untouched).
    if move_name == "Freeze-Dry" and "Water" in def_types:
        eff *= 4.0
    # Scrappy: the attacker's Normal/Fighting moves hit Ghost-types — ONLY the
    # Ghost component is neutralised (treated as ×1); the other type still
    # applies (Scrappy Close Combat vs Gengar = ×0.5 via Poison, not ×1).
    # Recomputed rather than divided because the Ghost component is ×0.
    if (attacker_ability == "Scrappy" and eff_type in ("Normal", "Fighting")
            and "Ghost" in def_types):
        eff = type_effectiveness(eff_type,
                                 [t for t in def_types if t != "Ghost"])
    # Ability-based type immunity (Levitate→Ground, Dry Skin→Water, Flash Fire→
    # Fire, Volt Absorb→Electric, Sap Sipper→Grass, …): the defender's ability
    # nullifies the move entirely.  (Mould Breaker would bypass this, but our
    # attackers don't carry it, so that exception isn't modelled.)
    if eff > 0 and _ABILITY_TYPE_IMMUNITY.get(defender_ability) == eff_type:
        eff = 0.0
    wthr  = weather_modifier(eff_type, weather)
    wthr *= terrain_modifier(move_name, eff_type, terrain,
                             atk_grounded, def_grounded)
    is_spread = is_spread_move(move_name)

    atk_m = atk_modifier(attacker_ability, attacker_item,
                          move_name, eff_type, power, category,
                          original_type=raw_type,
                          weather=weather,
                          attacker_hp_fraction=attacker_hp_fraction,
                          attacker_status=attacker_status,
                          ally_faint_count=ally_faint_count,
                          flash_fire_active=flash_fire_active)

    # Effectiveness/strike-count abilities — applied here, not in atk_modifier,
    # because they need the resolved type effectiveness (eff) or spread status.
    # Parental Bond (Kangaskhan-Mega): the move strikes twice, the 2nd at 25%
    # power, so single-target damage ≈ ×1.25; it does not apply to spread moves,
    # and its extra strike breaks Focus Sash / Sturdy like a multi-hit.
    parental_bond = (attacker_ability == "Parental Bond"
                     and not is_spread)
    if attacker_ability == "Neuroforce" and eff > 1.0:
        atk_m *= 1.2          # +20% on super-effective hits
    elif attacker_ability == "Tinted Lens" and 0.0 < eff < 1.0:
        atk_m *= 2.0          # not-very-effective hits land at full power
    elif parental_bond:
        atk_m *= 1.25

    def_m = def_modifier(defender_ability, defender_item,
                         eff_type, category, eff, defender_is_full_hp)

    # ── Choose offensive / defensive stats ───────────────────────────────────
    if category == "Physical":
        A  = attacker_stats.get("atk", 100)
        D  = defender_stats.get("def", 100)
        ab = boosts_atk.get("atk", 0)
        db = boosts_def.get("def", 0)
        # Burn halves physical damage — unless the attacker has Guts (which
        # negates the Attack drop; its ×1.5 is applied in the atk-modifier).
        burn = (attacker_status == "brn" and attacker_ability != "Guts")
        # Foul Play hits with the TARGET's Attack stat (and the target's Attack
        # stat stages) — not the user's.  Without this we badly under-predict
        # incoming Foul Play vs our high-Attack mons (Sableye -> Sneasler).
        if move_name == _FOUL_PLAY:
            A  = defender_stats.get("atk", 100)
            ab = boosts_def.get("atk", 0)
        # Body Press deals damage with the USER's Defense stat (and the user's
        # Defense stat stages) in place of Attack.  Without this we use the
        # attacker's (often low) Attack and badly under-predict it — e.g.
        # Corviknight Body Press -> Aerodactyl.
        elif move_name == _BODY_PRESS:
            A  = attacker_stats.get("def", 100)
            ab = boosts_atk.get("def", 0)
    else:  # Special
        A  = attacker_stats.get("spa", 100)
        D  = defender_stats.get("spd", 100)
        ab = boosts_atk.get("spa", 0)
        db = boosts_def.get("spd", 0)
        burn = False

    defender_hp = defender_stats.get("hp", 0)

    # ── Core formula ──────────────────────────────────────────────────────────
    dmg_min, dmg_max, dmg_avg = calc_damage(
        power, A, D,
        stab=stab, effectiveness=eff,
        spread_move=is_spread,
        weather=wthr,
        crit=crit,
        atk_boost=ab, def_boost=db,
        atk_mod=atk_m, def_mod=def_m,
        burn=burn,
    )

    # Opponent screen (Reflect / Light Screen / Aurora Veil) reduces our damage
    # to 2/3 in doubles, unless this hit is a critical (crits bypass screens).
    scr = screen_modifier(category, defender_screens, crit)
    if scr != 1.0:
        dmg_min = math.floor(dmg_min * scr)
        dmg_max = math.floor(dmg_max * scr)
        dmg_avg = dmg_avg * scr

    n_hits = expected_hits(move_name)
    ko_prevented = (
        defender_is_full_hp
        and n_hits == 1.0                       # multi-hit moves break Sash/Sturdy
        and not parental_bond                   # Parental Bond's 2nd strike too
        and (defender_item in _KO_PREVENTING_ITEMS
             or defender_ability in _KO_PREVENTING_ABILITIES)
    )

    return DamageResult(
        move=move_name, power=power, category=category,
        effective_type=eff_type,
        attacker=attacker_species, defender=defender_species,
        stab=stab, effectiveness=eff,
        atk_modifier=atk_m, def_modifier=def_m,
        damage_min=dmg_min, damage_max=dmg_max, damage_avg=dmg_avg,
        defender_hp=defender_hp,
        hits=n_hits, ko_prevented=ko_prevented,
    )


# ── Threat assessment ─────────────────────────────────────────────────────────

_log = __import__("logging").getLogger(__name__)


def _most_common_stats(species: str) -> Optional[dict[str, int]]:
    """
    Return computed stats for *species* using its most common SP spread.
    Falls back to base stats only (0 SP, neutral nature) if no spread data.

    Champions format allows custom mega evolutions for species that have no
    canonical mega form (e.g. "Drampa-Mega").  If the exact species name is
    not in the base-stats database, strip the last "-<suffix>" component and
    retry — this gives a reasonable approximation using the base form's stats.

    Returns None only when no base stats can be found at all.
    """
    bs = get_base_stats(species)
    if bs is None:
        # Try stripping one suffix level: "Drampa-Mega" → "Drampa"
        base = species.rsplit("-", 1)[0]
        if base != species:
            bs = get_base_stats(base)
            if bs is not None:
                _log.debug(
                    "_most_common_stats: '%s' unknown, using base form '%s'",
                    species, base,
                )
    if bs is None:
        # No stats at all: the caller returns [] and the mon scores as
        # harmless / invisible — flag it in the battle log.
        note_gap("stats", species)
        return None

    spreads = spread_distribution(species)
    if not spreads:
        return calc_all_stats(bs, {k: 0 for k in bs}, "Hardy")

    top_spread_str, _ = spreads[0]
    parsed = parse_spread(top_spread_str)
    if parsed is None:
        return calc_all_stats(bs, {k: 0 for k in bs}, "Hardy")

    sp = {k: parsed[k] for k in ("hp", "atk", "def", "spa", "spd", "spe")}
    return calc_all_stats(bs, sp, parsed["nature"])


# Representative ~80–95 BP STAB move per type, used only as a fallback when a
# species has no usage data at all (rare mons / type-shifted formes).  One is
# chosen per STAB type, physical or special by the mon's higher attacking stat,
# so incoming_damage still returns a type-correct threat instead of nothing.
_STAB_PHYS: dict[str, str] = {
    "Normal": "Body Slam",   "Fire": "Flare Blitz",  "Water": "Waterfall",
    "Electric": "Wild Charge","Grass": "Power Whip",  "Ice": "Icicle Crash",
    "Fighting": "Close Combat","Poison": "Poison Jab", "Ground": "Earthquake",
    "Flying": "Brave Bird",  "Psychic": "Zen Headbutt","Bug": "X-Scissor",
    "Rock": "Stone Edge",    "Ghost": "Shadow Claw",  "Dragon": "Dragon Claw",
    "Dark": "Crunch",        "Steel": "Iron Head",    "Fairy": "Play Rough",
}
_STAB_SPEC: dict[str, str] = {
    "Normal": "Hyper Voice", "Fire": "Flamethrower",  "Water": "Surf",
    "Electric": "Thunderbolt","Grass": "Energy Ball", "Ice": "Ice Beam",
    "Fighting": "Aura Sphere","Poison": "Sludge Bomb", "Ground": "Earth Power",
    "Flying": "Air Slash",   "Psychic": "Psychic",    "Bug": "Bug Buzz",
    "Rock": "Power Gem",     "Ghost": "Shadow Ball",  "Dragon": "Dragon Pulse",
    "Dark": "Dark Pulse",    "Steel": "Flash Cannon", "Fairy": "Moonblast",
}


def _synthetic_stab_moves(species: str, stats: dict[str, int]) -> list[str]:
    """Representative STAB moves for a species with no usage data.

    Picks one move per STAB type (physical or special based on the species'
    higher attacking stat) so :func:`incoming_damage` can still estimate a
    type-correct threat rather than returning an empty list (which the decision
    engine would read as "this opponent is harmless").
    """
    types = types_of(species) or []
    if not types or not stats:
        return []
    table = _STAB_PHYS if stats.get("atk", 0) >= stats.get("spa", 0) else _STAB_SPEC
    moves: list[str] = []
    for t in types:
        mv = table.get(t)
        if mv and mv not in moves:
            moves.append(mv)
    return moves


def incoming_damage(
        opp_species: str,
        our_species: str,
        our_stats: dict[str, int],
        *,
        opp_ability: str = "",
        opp_item: Optional[str] = None,
        our_ability: str = "",
        our_item: Optional[str] = None,
        defender_has_item: bool = True,
        weather: Optional[str] = None,
        terrain: Optional[str] = None,
        opp_types: Optional[list[str]] = None,
        our_types: Optional[list[str]] = None,
        our_defender_is_full_hp: bool = True,
        our_current_hp: Optional[int] = None,
        our_hp_percent: Optional[float] = None,
        our_screens=None,
        top_n_moves: int = 6,
        only_moves: Optional[list[str]] = None,
        opp_boosts: Optional[dict[str, int]] = None,
        our_boosts: Optional[dict[str, int]] = None,
        opp_hp_fraction: float = 1.0,
        opp_status: str = "",
        opp_ally_faint_count: int = 0,
        opp_times_hit: int = 0,
        opp_flash_fire_active: bool = False,
) -> list[DamageResult]:
    """
    Estimate the damage our Pokémon (*our_species*) would take from
    *opp_species*'s most-used moves, given the opponent's most common
    SP spread.

    Args:
        opp_species:      Opponent's species name.
        our_species:      Our Pokémon's species name.
        our_stats:        Our Pokémon's final stats (exact, from team.py).
        opp_ability:      Opponent's ability (empty = unknown, no ability mod).
        opp_item:         Opponent's confirmed item (None = unknown).
        our_ability:      Our Pokémon's ability (for defensive mods).
        our_item:         Our Pokémon's held item (for resistance berries etc.).
        weather:          Current weather string or None.
        our_screens:      OUR side's active screens (e.g. {"auroraveil"}) — the
                          incoming hit is halved/thirded just like outgoing into
                          the opponent's screens. None/empty = no reduction.
        our_defender_is_full_hp: Whether our Pokémon is at full HP.
        top_n_moves:      How many of the opponent's top moves to evaluate.
        only_moves:       If given, assess exactly these moves instead of the
                          usage top-N (a Choice-locked opponent's single move).
        opp_boosts:       Opponent's current stat-stage boosts dict (e.g. {"atk": 2}).
        our_boosts:       Our Pokémon's current stat-stage boosts dict (e.g. {"def": -1}).

    Returns:
        List of :class:`DamageResult` sorted by ``damage_avg`` descending.
    """
    from data import move_distribution   # avoid circular at module level

    opp_stats = _most_common_stats(opp_species)
    if opp_stats is None:
        return []

    # Override OUR HP denominator with our observed current HP so that incoming
    # OHKO detection and hp_fraction_* reflect how much HP we actually have right
    # now — mirroring the opp_current_hp override in outgoing_damage.  Without
    # this, a sub-max-HP lethal hit on an already-damaged mon is never flagged as
    # an OHKO (damage < max HP), so is_doomed/is_threatened/escape-switch under-fire.
    # Note: our_defender_is_full_hp still gates Sash/Sturdy independently of this.
    if our_current_hp is not None and our_current_hp > 0:
        our_stats = dict(our_stats)   # don't mutate the caller's dict
        our_stats["hp"] = our_current_hp
    elif our_hp_percent is not None and 0 < our_hp_percent < 100:
        our_stats = dict(our_stats)
        our_stats["hp"] = max(1, round(our_stats["hp"] * our_hp_percent / 100.0))

    if only_moves:
        # Caller knows exactly which move(s) can be used — e.g. a Choice-locked
        # opponent stuck on one move until it switches.  Assess only those.
        moves = list(only_moves)
    else:
        moves = [m for m, _ in move_distribution(opp_species)[:top_n_moves]]
    if not moves:
        # No usage data for this species (rare mon / type-shifted forme) — fall
        # back to representative STAB moves so the opponent still registers a
        # threat instead of being treated as harmless.
        note_gap("moves", opp_species)
        moves = _synthetic_stab_moves(opp_species, opp_stats)

    results: list[DamageResult] = []
    for move_name in moves:
        result = full_damage_calc(
            move_name,
            attacker_species=opp_species,
            defender_species=our_species,
            attacker_stats=opp_stats,
            defender_stats=our_stats,
            attacker_ability=opp_ability,
            defender_ability=our_ability,
            attacker_item=opp_item,
            defender_item=our_item,
            defender_has_item=defender_has_item,
            weather=weather,
            terrain=terrain,
            attacker_types=opp_types, defender_types=our_types,
            defender_screens=our_screens,
            attacker_boosts=opp_boosts,
            defender_boosts=our_boosts,
            defender_is_full_hp=our_defender_is_full_hp,
            ally_faint_count=opp_ally_faint_count,
            times_hit=opp_times_hit,
            attacker_hp_fraction=opp_hp_fraction,
            attacker_status=opp_status,
            flash_fire_active=opp_flash_fire_active,
        )
        if result.power > 0:
            results.append(result)

    if not results and not only_moves:
        # Usage moves exist but are ALL status (pure support mons — Audino,
        # Slurpuff): the listed set deals zero damage, but the mon may still
        # carry an attack in the "Other" bucket.  Fall back to synthetic STAB so
        # no opponent is ever modelled as completely harmless.  (Skipped for
        # only_moves: a Choice-locked mon stuck on a status move genuinely
        # threatens nothing until it switches.)
        for move_name in _synthetic_stab_moves(opp_species, opp_stats):
            result = full_damage_calc(
                move_name,
                attacker_species=opp_species, defender_species=our_species,
                attacker_stats=opp_stats, defender_stats=our_stats,
                attacker_ability=opp_ability, defender_ability=our_ability,
                attacker_item=opp_item, defender_item=our_item,
                defender_has_item=defender_has_item,
                weather=weather,
                terrain=terrain, defender_screens=our_screens,
                attacker_types=opp_types, defender_types=our_types,
                attacker_boosts=opp_boosts, defender_boosts=our_boosts,
                defender_is_full_hp=our_defender_is_full_hp,
                ally_faint_count=opp_ally_faint_count,
                times_hit=opp_times_hit,
                attacker_hp_fraction=opp_hp_fraction,
                attacker_status=opp_status,
                flash_fire_active=opp_flash_fire_active,
            )
            if result.power > 0:
                results.append(result)

    return sorted(results, key=lambda r: -r.damage_avg)


def outgoing_damage(
        our_species: str,
        our_stats: dict[str, int],
        our_moves: list[str],
        opp_species: str,
        *,
        our_ability: str = "",
        our_item: Optional[str] = None,
        opp_ability: str = "",
        opp_item: Optional[str] = None,
        defender_has_item: bool = True,
        weather: Optional[str] = None,
        terrain: Optional[str] = None,
        our_types: Optional[list[str]] = None,
        opp_types: Optional[list[str]] = None,
        opp_is_full_hp: bool = True,
        ally_faint_count: int = 0,
        times_hit: int = 0,
        opp_current_hp: Optional[int] = None,
        opp_hp_percent: Optional[float] = None,
        opp_screens=None,
        attacker_boosts: Optional[dict[str, int]] = None,
        defender_boosts: Optional[dict[str, int]] = None,
        attacker_hp_fraction: float = 1.0,
        attacker_status: str = "",
        flash_fire_active: bool = False,
) -> list[DamageResult]:
    """
    Compute damage our Pokémon's moves would deal to *opp_species* using
    the opponent's most common SP spread for defensive stats.

    Args:
        our_species:      Our attacker's species name.
        our_stats:        Our Pokémon's final stats (exact).
        our_moves:        List of move names to evaluate (typically our 4 moves).
        opp_species:      Opponent's species name.
        ally_faint_count: Number of our allies that have fainted so far this
                          battle — used to scale Last Respects base power.
        opp_current_hp:   Opponent's actual current HP (from battle state).
                          When provided, overrides the typical-spread HP so that
                          ``DamageResult.hp_fraction_*`` and OHKO flags reflect
                          how much HP the opponent actually has right now, not
                          just their full-health estimate.  Pass only when the
                          HP is an absolute value (not a percentage).
        attacker_boosts:  Our Pokémon's current stat-stage boosts (e.g. {"atk": 2}).
        defender_boosts:  Opponent's current stat-stage boosts (e.g. {"def": 1}).

    Returns:
        List of :class:`DamageResult` sorted by ``damage_avg`` descending.
    """
    opp_stats = _most_common_stats(opp_species)
    if opp_stats is None:
        return []

    # Override the HP denominator with the opponent's observed current HP so that
    # OHKO detection and hp_fraction_avg reflect the opponent's actual state.
    # Only use the override when it's an absolute HP value (not a % proxy).
    if opp_current_hp is not None and opp_current_hp > 0:
        opp_stats = dict(opp_stats)   # don't mutate the cached dict
        opp_stats["hp"] = opp_current_hp
    elif opp_hp_percent is not None and 0 < opp_hp_percent < 100:
        # Opponent tracked at a HP percentage (we don't know its true max HP):
        # scale the typical-spread max HP so OHKO detection and hp_fraction_*
        # reflect how much HP it actually has right now — letting the engine
        # recognise and finish a chipped opponent.
        opp_stats = dict(opp_stats)
        opp_stats["hp"] = max(1, round(opp_stats["hp"] * opp_hp_percent / 100.0))

    results: list[DamageResult] = []
    for move_name in our_moves:
        result = full_damage_calc(
            move_name,
            attacker_species=our_species,
            defender_species=opp_species,
            attacker_stats=our_stats,
            defender_stats=opp_stats,
            attacker_ability=our_ability,
            defender_ability=opp_ability,
            attacker_item=our_item,
            defender_item=opp_item,
            defender_has_item=defender_has_item,
            weather=weather,
            terrain=terrain,
            attacker_types=our_types, defender_types=opp_types,
            defender_is_full_hp=opp_is_full_hp,
            ally_faint_count=ally_faint_count,
            times_hit=times_hit,
            defender_screens=opp_screens,
            attacker_boosts=attacker_boosts,
            defender_boosts=defender_boosts,
            attacker_hp_fraction=attacker_hp_fraction,
            attacker_status=attacker_status,
            flash_fire_active=flash_fire_active,
        )
        if result.power > 0:
            results.append(result)

    return sorted(results, key=lambda r: -r.damage_avg)
