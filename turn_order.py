"""turn_order.py — Estimates which Pokémon moves first.

Combines exact stats for our own team (from team.py) with probabilistic
speed distributions for opponents (from data/speed_tiers.py) to answer:

  * Will our Pokémon outspeed a given opponent?
  * Does our priority move land before the opponent can respond?

Key concepts
------------
- Priority brackets: higher priority always moves before lower priority.
  Trick Room only reverses speed within the same bracket.
- Speed modifiers applied in order: stages → item → weather ability
  → Unburden → Tailwind → Paralysis.  The item multiplier comes from the single
  modal assumed item (data.items.speed_multiplier), not a per-item branch.
- Opponent speed comes from the spread distribution (probabilistic), with the
  modal assumed item applied as a flat multiplier.  Own team speed is computed
  exactly from team.txt.

The decision engine builds :class:`Combatant` objects per slot (see
``decision.modules._our_combatant`` / ``_opp_combatant``) and asks
:func:`will_outspeed` — P(attacker acts before defender) integrated over the
opponent's speed distribution.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from data import (
    move_priority as _data_move_priority,
    speed_distribution as _build_dist,
    speed_multiplier as _item_speed_multiplier,
    WEATHER_SPEED_ABILITIES,
    SpeedOutcome,
)


# ── Data containers ───────────────────────────────────────────────────────────

@dataclass
class Combatant:
    """
    Speed profile for one active Pokémon.

    Set ``exact_speed`` for your own team (exact stat known).
    Leave it ``None`` for opponents — the module will use the data-layer
    speed distribution instead.
    """
    name:        str
    side:        str            # "own" | "opp"
    slot:        int            # 0 = slot-a, 1 = slot-b

    # Speed source — set exactly ONE
    exact_speed: Optional[int] = None   # own team: pre-computed stat

    # Confirmed modifiers (None = unknown for opponents)
    item:        Optional[str] = None
    ability:     Optional[str] = None

    # Stage & field modifiers
    speed_stage: int  = 0               # from Pokemon.boosts["spe"], −6…+6
    tailwind:    bool = False
    paralyzed:   bool = False
    weather:     Optional[str] = None   # 'sun','rain','sand','hail', None

    # Whether this mon has already Mega Evolved this battle
    is_mega:     bool = False
    # True once the held item was consumed this field stint (drives Unburden ×2).
    # Cleared when the Pokémon switches out (new Pokemon object resets the flag).
    item_consumed: bool = False


# ── Speed calculation ─────────────────────────────────────────────────────────

def _apply_modifiers(
        raw: int,
        speed_stage: int = 0,
        item: Optional[str] = None,    # modal assumed item (or our exact item)
        ability: Optional[str] = None,
        weather: Optional[str] = None,
        tailwind: bool = False,
        paralyzed: bool = False,
        item_consumed: bool = False,   # Unburden: item was lost this field stint
) -> int:
    """
    Apply all speed modifiers in game order to a raw speed value.

    Order: stat stages → item → weather ability → Unburden → Tailwind → Paralysis.

    The item multiplier (Choice Scarf ×1.5, Iron Ball / Macho Brace ×0.5) comes
    from the single modal assumed item via ``data.items.speed_multiplier`` — no
    per-item special-casing here.
    """
    spd = raw

    # 1. Speed stages  (formula: stat × (2+max(stage,0)) / (2+max(-stage,0)))
    if speed_stage > 0:
        spd = math.floor(spd * (2 + speed_stage) / 2)
    elif speed_stage < 0:
        spd = math.floor(spd * 2 / (2 - speed_stage))

    # 2. Item (modal): Choice Scarf ×1.5, Iron Ball / Macho Brace ×0.5, else ×1.0
    spd = math.floor(spd * _item_speed_multiplier(item))

    # 3. Weather-boosted ability (Swift Swim, Chlorophyll, Sand Rush, Slush Rush…)
    if ability and weather:
        req = WEATHER_SPEED_ABILITIES.get(ability)
        if req == weather:
            spd *= 2

    # 4. Unburden: doubles speed after the held item is lost
    if ability == "Unburden" and item_consumed:
        spd *= 2

    # 5. Tailwind
    if tailwind:
        spd *= 2

    # 6. Paralysis
    if paralyzed:
        spd = math.floor(spd * 0.5)

    return spd


def _speed_outcomes(c: Combatant) -> list[tuple[int, float]]:
    """
    Return [(effective_speed, probability), …] for a Combatant.

    Own team (exact_speed set): one outcome with probability 1.0.
    Opponent: drawn from the data-layer *spread* distribution, with all
    modifiers — including the modal assumed item (``c.item``) — applied.
    """
    def _mod(raw: int) -> int:
        return _apply_modifiers(
            raw,
            speed_stage=c.speed_stage,
            item=c.item,
            ability=c.ability,
            weather=c.weather,
            tailwind=c.tailwind,
            paralyzed=c.paralyzed,
            item_consumed=c.item_consumed,
        )

    # ── Own team: exact ───────────────────────────────────────────────────────
    if c.exact_speed is not None:
        return [(_mod(c.exact_speed), 1.0)]

    # ── Opponent: probabilistic over spreads ──────────────────────────────────
    dist: list[SpeedOutcome] = _build_dist(c.name)
    if not dist:
        return [(100, 1.0)]   # unknown species fallback

    total_p = sum(o.probability for o in dist)
    if total_p == 0:
        return [(100, 1.0)]

    # Build (eff_speed, prob) list, applying modifiers from raw_speed
    raw_outcomes: list[tuple[int, float]] = [
        (_mod(o.raw_speed), o.probability / total_p)
        for o in dist
    ]

    # Merge identical effective speeds
    merged: dict[int, float] = {}
    for spd, p in raw_outcomes:
        merged[spd] = merged.get(spd, 0.0) + p
    return sorted(merged.items(), key=lambda x: -x[1])   # sort by probability


# ── Public API ────────────────────────────────────────────────────────────────

def will_outspeed(
        attacker: Combatant,
        defender: Combatant,
        atk_move: str = "",
        def_move: str = "",
        trick_room: bool = False,
) -> float:
    """
    Return P(attacker moves strictly before defender) ∈ [0, 1].

    * Priority differences resolve deterministically.
    * Within the same priority bracket, integrates over speed distributions.
    * Speed ties are treated as 50 / 50.
    """
    atk_prio = _data_move_priority(atk_move) if atk_move else 0
    def_prio = _data_move_priority(def_move) if def_move else 0

    # Different priority brackets → certain
    if atk_prio > def_prio:
        return 1.0
    if atk_prio < def_prio:
        return 0.0

    # Same bracket — integrate speed distributions
    atk_outcomes = _speed_outcomes(attacker)
    def_outcomes = _speed_outcomes(defender)

    atk_total = sum(p for _, p in atk_outcomes)
    def_total = sum(p for _, p in def_outcomes)
    if atk_total == 0 or def_total == 0:
        return 0.5

    faster_p = tie_p = 0.0
    for atk_spd, atk_p in atk_outcomes:
        for def_spd, def_p in def_outcomes:
            joint = (atk_p / atk_total) * (def_p / def_total)
            if not trick_room:
                if atk_spd > def_spd:
                    faster_p += joint
                elif atk_spd == def_spd:
                    tie_p += joint
            else:
                if atk_spd < def_spd:
                    faster_p += joint
                elif atk_spd == def_spd:
                    tie_p += joint

    return faster_p + tie_p * 0.5


def priority_bracket(move: str) -> int:
    """Return the priority value for *move* (0 for normal moves)."""
    return _data_move_priority(move) if move else 0
