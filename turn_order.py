"""turn_order.py — Estimates which Pokémon moves when.

Combines exact stats for our own team (from team.py) with probabilistic
speed distributions for opponents (from data/speed_tiers.py) to answer:

  * What is the most likely move order this turn?
  * Will our Pokémon outspeed a given opponent?
  * Does our priority move land before the opponent can respond?

Key concepts
------------
- Priority brackets: higher priority always moves before lower priority.
  Trick Room only reverses speed within the same bracket.
- Speed modifiers applied in order: stages → Choice Scarf → weather ability
  → Tailwind → Paralysis.
- Opponent speed comes from spread + item usage distributions (probabilistic).
  Own team speed is computed exactly from team.txt.

Usage::

    from turn_order import build_combatants, estimate_turn_order, will_outspeed
    from battle import BattleState

    combatants = build_combatants(state)
    order = estimate_turn_order(
        combatants,
        moves=["Fake Out", "Hyper Voice", None, None],  # None = unknown (opp)
        trick_room=state.trick_room,
    )
    for entry in order:
        print(f"  [{entry.rank}] {entry.name} ({entry.side}) "
              f"prio={entry.priority} spd={entry.eff_speed}")
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from data import (
    move_priority as _data_move_priority,
    speed_distribution as _build_dist,
    WEATHER_SPEED_ABILITIES,
    SpeedOutcome,
)

if TYPE_CHECKING:
    from battle import BattleState, Pokemon


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


@dataclass
class TurnEntry:
    """One slot's position in the estimated turn order."""
    name:            str
    side:            str
    slot:            int
    move:            str
    priority:        int
    eff_speed:       int              # most-likely effective speed
    eff_speed_min:   int              # lower bound (from distribution)
    eff_speed_max:   int              # upper bound (from distribution)
    rank:            int = 0          # 1 = moves first, filled by estimate_turn_order

    @property
    def is_priority_move(self) -> bool:
        return self.priority > 0

    @property
    def speed_is_exact(self) -> bool:
        return self.eff_speed_min == self.eff_speed_max


# ── Speed calculation ─────────────────────────────────────────────────────────

def _apply_modifiers(
        raw: int,
        speed_stage: int = 0,
        scarfed: bool = False,
        slow_item: bool = False,       # Iron Ball / Macho Brace
        ability: Optional[str] = None,
        weather: Optional[str] = None,
        tailwind: bool = False,
        paralyzed: bool = False,
        item_consumed: bool = False,   # Unburden: item was lost this field stint
) -> int:
    """
    Apply all speed modifiers in game order to a raw speed value.

    Order: stat stages → item → weather ability → Unburden → Tailwind → Paralysis.
    """
    spd = raw

    # 1. Speed stages  (formula: stat × (2+max(stage,0)) / (2+max(-stage,0)))
    if speed_stage > 0:
        spd = math.floor(spd * (2 + speed_stage) / 2)
    elif speed_stage < 0:
        spd = math.floor(spd * 2 / (2 - speed_stage))

    # 2. Item
    if scarfed:
        spd = math.floor(spd * 1.5)
    elif slow_item:
        spd = math.floor(spd * 0.5)

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


_SLOW_ITEMS = frozenset({"Iron Ball", "Macho Brace"})


def _speed_outcomes(c: Combatant) -> list[tuple[int, float]]:
    """
    Return [(effective_speed, probability), …] for a Combatant.

    Own team (exact_speed set): one outcome with probability 1.0.
    Opponent: drawn from the data-layer speed distribution, filtered by any
    confirmed item knowledge, with all non-item modifiers applied.
    """
    def _mod(raw: int, scarfed: bool = False) -> int:
        return _apply_modifiers(
            raw,
            speed_stage=c.speed_stage,
            scarfed=scarfed,
            slow_item=(c.item in _SLOW_ITEMS),
            ability=c.ability,
            weather=c.weather,
            tailwind=c.tailwind,
            paralyzed=c.paralyzed,
            item_consumed=c.item_consumed,
        )

    # ── Own team: exact ───────────────────────────────────────────────────────
    if c.exact_speed is not None:
        scarfed = (c.item == "Choice Scarf")
        eff = _mod(c.exact_speed, scarfed)
        return [(eff, 1.0)]

    # ── Opponent: probabilistic ───────────────────────────────────────────────
    dist: list[SpeedOutcome] = _build_dist(c.name)
    if not dist:
        return [(100, 1.0)]   # unknown species fallback

    # Filter by confirmed item if we know it
    if c.item is not None:
        scarf_confirmed = (c.item == "Choice Scarf")
        filtered = [o for o in dist if o.scarfed == scarf_confirmed]
        if not filtered:
            filtered = dist   # shouldn't happen; fall back to full dist
    else:
        filtered = dist

    total_p = sum(o.probability for o in filtered)
    if total_p == 0:
        filtered = dist
        total_p  = sum(o.probability for o in filtered)

    # Build (eff_speed, prob) list, applying modifiers from raw_speed
    raw_outcomes: list[tuple[int, float]] = [
        (_mod(o.raw_speed, o.scarfed), o.probability / total_p)
        for o in filtered
    ]

    # Merge identical effective speeds
    merged: dict[int, float] = {}
    for spd, p in raw_outcomes:
        merged[spd] = merged.get(spd, 0.0) + p
    return sorted(merged.items(), key=lambda x: -x[1])   # sort by probability


# ── Public API ────────────────────────────────────────────────────────────────

def estimate_turn_order(
        combatants: list[Combatant],
        moves: list[Optional[str]],
        trick_room: bool = False,
) -> list[TurnEntry]:
    """
    Return *combatants* sorted from first-to-move to last-to-move.

    Args:
        combatants:  Active Pokémon (up to 4 in doubles).
        moves:       Parallel list of move names (``None`` = unknown).
        trick_room:  If True, slower Pokémon move first within each priority
                     bracket.

    The ranking uses the *most-likely* effective speed for each slot;
    ``eff_speed_min`` / ``eff_speed_max`` indicate the uncertainty range.
    """
    entries: list[TurnEntry] = []

    for c, move in zip(combatants, moves):
        move_name = move or ""
        prio = _data_move_priority(move_name) if move_name else 0

        outcomes = _speed_outcomes(c)
        mode_speed = outcomes[0][0]                       # most probable
        all_speeds = [s for s, _ in outcomes]
        spd_min, spd_max = min(all_speeds), max(all_speeds)

        entries.append(TurnEntry(
            name=c.name, side=c.side, slot=c.slot,
            move=move_name, priority=prio,
            eff_speed=mode_speed,
            eff_speed_min=spd_min,
            eff_speed_max=spd_max,
        ))

    # Sort: descending priority; within bracket, descending speed (or ascending
    # under Trick Room).
    def _key(e: TurnEntry) -> tuple:
        speed_key = -e.eff_speed if not trick_room else e.eff_speed
        return (-e.priority, speed_key)

    ranked = sorted(entries, key=_key)
    for i, e in enumerate(ranked):
        e.rank = i + 1

    return ranked


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


# ── Battle-state integration ──────────────────────────────────────────────────

def build_combatants(
        state: "BattleState",
        team_members: Optional[list] = None,
) -> list[Combatant]:
    """
    Build a :class:`Combatant` list from the current :class:`BattleState`.

    Own team slots use exact speeds from *team_members* (loaded via
    :func:`team.get_team`).  Opponent slots use speed distributions.

    If *team_members* is omitted, imports and calls :func:`team.get_team`
    automatically.
    """
    if team_members is None:
        from team import get_team
        team_members = get_team()

    result: list[Combatant] = []

    # ── Own active slots ──────────────────────────────────────────────────────
    for slot, mon in enumerate(state.my_actives):
        if mon is None:
            continue

        # Match against team data; handle mega form names
        tm = next(
            (t for t in team_members
             if mon.species == t.name
             or mon.species == t.mega_name
             or mon.species.startswith(t.name)),
            None,
        )

        # Choose correct speed: post-mega if species changed
        exact_spd: Optional[int] = None
        if tm is not None:
            is_mega = (mon.species == tm.mega_name)
            if is_mega and tm.mega_stats:
                exact_spd = tm.mega_stats["spe"]
            elif tm.stats:
                exact_spd = tm.stats["spe"]

        result.append(Combatant(
            name          = mon.species,
            side          = "own",
            slot          = slot,
            exact_speed   = exact_spd,
            item          = mon.item   or (tm.item    if tm else None),
            ability       = mon.ability or (tm.ability if tm else None),
            speed_stage   = mon.boosts.get("spe", 0),
            tailwind      = state.my_tailwind,
            paralyzed     = (mon.status == "par"),
            weather       = state.weather,
            is_mega       = (mon.species == (tm.mega_name if tm else None)),
            item_consumed = mon.item_consumed,
        ))

    # ── Opponent active slots ─────────────────────────────────────────────────
    for slot, mon in enumerate(state.opp_actives):
        if mon is None or mon.fainted:
            continue

        result.append(Combatant(
            name          = mon.species,
            side          = "opp",
            slot          = slot,
            exact_speed   = None,          # opponent speed is unknown
            item          = mon.item,      # None until revealed in battle
            ability       = mon.ability,   # None until revealed
            speed_stage   = mon.boosts.get("spe", 0),
            tailwind      = state.opp_tailwind,
            paralyzed     = (mon.status == "par"),
            weather       = state.weather,
            item_consumed = mon.item_consumed,
        ))

    return result
