"""decision/modules.py — Concrete scoring modules and factory for WolfeyBot.

All thirteen built-in ScoringModule implementations plus :func:`make_engine`.

Adding a module::

    class MyModule(ScoringModule):
        name = "my_module"
        def score(self, state, slot, actions):
            for a in actions:
                if a.move_name == "Protect":
                    a.weight *= 3.0
                    a.reasons.append("MyModule: always protect")

    engine.add_module(MyModule())
"""
from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from data import (
    types_of, move_type as get_move_type, move_category as get_move_category,
    get_species as _get_species,
    WEATHER_SPEED_ABILITIES as _WEATHER_SPEED_ABILITIES,
    ability_distribution as _ability_distribution,
)
from team import find_member
from damage import outgoing_damage, incoming_damage, type_effectiveness
from turn_order import Combatant, will_outspeed

from decision.engine import (
    Action, ScoringModule, DecisionEngine,
    _PROTECT_MOVES, _FAKE_OUT_USERS,
)

if TYPE_CHECKING:
    from battle import BattleState

_log = logging.getLogger(__name__)


# ── Internal helpers (used by scoring modules) ────────────────────────────────

def _our_combatant(state: "BattleState", slot: int) -> Optional[Combatant]:
    """Build a Combatant for our active Pokemon at *slot*."""
    if slot >= len(state.my_actives):
        return None
    mon = state.my_actives[slot]
    if mon is None:
        return None
    tm = find_member(mon.species)
    is_mega   = tm is not None and mon.species == tm.mega_name
    will_mega = (
        tm is not None and not is_mega and tm.mega_stats is not None
        and getattr(state, "designated_mega", None) == tm.name
    )
    exact_spd: Optional[int] = None
    if tm:
        exact_spd = (
            tm.mega_stats["spe"] if (is_mega or will_mega) and tm.mega_stats
            else tm.stats.get("spe")
        )
    return Combatant(
        name=mon.species, side="own", slot=slot,
        exact_speed=exact_spd,
        item=mon.item or (tm.item if tm else None),
        ability=mon.ability or (tm.ability if tm else None),
        speed_stage=mon.boosts.get("spe", 0),
        tailwind=state.my_tailwind,
        paralyzed=(mon.status == "par"),
        weather=state.weather,
        item_consumed=mon.item_consumed,
    )


def _opp_combatant(state: "BattleState", opp_slot: int) -> Optional[Combatant]:
    """Build a Combatant for the opponent's active Pokemon at *opp_slot*."""
    if opp_slot >= len(state.opp_actives):
        return None
    mon = state.opp_actives[opp_slot]
    if mon is None or mon.fainted:
        return None
    # Start from the best known/assumed ability for this species.  If the
    # opponent's ability has been revealed in battle, use that; otherwise
    # fall back to the highest-usage-rate ability from the sets data.
    # Additionally, if weather is active and the species carries a matching
    # weather-speed ability that differs from the assumed ability, that
    # weather-speed ability takes precedence to avoid overconfident speed
    # estimates (e.g. Excadrill in sandstorm assumed Sand Rush even if no
    # ability has been revealed).
    inferred_ability = _effective_ability(mon)
    if inferred_ability is None and state.weather:
        sp_data = _get_species(mon.species)
        if sp_data:
            for ab in sp_data.get("abilities", []):
                if _WEATHER_SPEED_ABILITIES.get(ab) == state.weather:
                    inferred_ability = ab
                    break
    return Combatant(
        name=mon.species, side="opp", slot=opp_slot,
        exact_speed=None,
        item=mon.item, ability=inferred_ability,
        speed_stage=mon.boosts.get("spe", 0),
        tailwind=state.opp_tailwind,
        paralyzed=(mon.status == "par"),
        weather=state.weather,
        item_consumed=mon.item_consumed,
    )


def _our_stats(state: "BattleState", slot: int) -> Optional[dict[str, int]]:
    """Return exact stats for our active Pokemon at *slot* (mega-aware).

    Active mons that hold a mega stone but haven't yet evolved will mega-evolve
    at the start of the turn before any damage is dealt, so mega stats are used
    for all active mega-stone holders regardless of whether evolution has been
    registered by the battle client.
    """
    if slot >= len(state.my_actives):
        return None
    mon = state.my_actives[slot]
    if mon is None:
        return None
    tm = find_member(mon.species)
    if tm is None:
        return None
    is_mega   = mon.species == tm.mega_name
    will_mega = (
        not is_mega and tm.mega_stats is not None
        and getattr(state, "designated_mega", None) == tm.name
    )
    return (tm.mega_stats if (is_mega or will_mega) and tm.mega_stats else tm.stats) or None


def _our_ability_for_damage(
    tm: "TeamMember",
    mon: "Pokemon",
    designated_mega: Optional[str] = None,
) -> str:
    """Return the defensive ability to use for incoming-damage calculations.

    In VGC, mega evolution occurs at the start of the turn before any moves,
    so an active mon's defensive ability is its *mega* ability even on the very
    first turn — regardless of whether the battle client has registered the
    evolution yet.  This applies to both pre-mega and already-mega forms.

    Only the Pokémon named in *designated_mega* (``state.designated_mega``)
    will mega-evolve this battle — a second mega-stone holder on the same team
    stays in base form.  Already-evolved forms (``mon.species == tm.mega_name``)
    are always treated as mega regardless of *designated_mega*.

    ``TeamMember`` stores no dedicated ``mega_ability`` field; the mega ability
    is resolved via ``_assumed_ability(tm.mega_name)``.  Falls back to
    ``tm.ability`` (base ability) when the mon has no mega form, or when the
    mega species has no data in the sets file.
    """
    is_mega   = mon.species == tm.mega_name
    will_mega = (
        not is_mega and tm.mega_stats is not None
        and designated_mega == tm.name
    )
    if (is_mega or will_mega) and tm.mega_name:
        mega_ab = _assumed_ability(tm.mega_name)
        if mega_ab:
            return mega_ab
    return tm.ability or ""


def _assumed_ability(species: str) -> Optional[str]:
    """Return the highest-usage-rate ability for *species*, or None if unknown.

    Data comes from the Champions sets file via ``ability_distribution``.
    Returns None when the species has no usage data (e.g. obscure/illegal mon).
    """
    dist = _ability_distribution(species)
    return dist[0][0] if dist else None


def _effective_ability(mon: "Pokemon") -> Optional[str]:
    """Return the ability to assume for *mon*.

    If the ability has been revealed in battle (``mon.ability is not None``),
    return it directly.  Otherwise fall back to the highest-usage-rate ability
    from the Champions sets data so that modules make informed decisions even
    before the ability is explicitly confirmed.

    Returns None only for species not present in the usage data.
    """
    if mon.ability is not None:
        return mon.ability
    return _assumed_ability(mon.species)


# ══════════════════════════════════════════════════════════════════════════════
# Built-in scoring modules
# ══════════════════════════════════════════════════════════════════════════════


class DamageOutputModule(ScoringModule):
    """
    Up-weights moves proportional to the damage they deal.

    For each move action the expected damage fraction (avg damage / opponent HP)
    is computed against every active opponent; the best value across all targets
    is used.

    Weight multiplier: 1.0 + fraction * 2.0

    Examples:
      100% avg damage (OHKO)  ->  x3.0
      50%                     ->  x2.0
      25%                     ->  x1.5
       0% (status / immune)   ->  x1.0  (unchanged)
    """

    name = "damage_output"

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        mon = state.my_actives[slot] if slot < len(state.my_actives) else None
        if mon is None:
            return
        tm = find_member(mon.species)
        stats = _our_stats(state, slot)
        if tm is None or stats is None:
            return

        if not any(o is not None for o in state.opp_actives):
            return

        ally_faints = sum(1 for p in state.my_team if p.fainted)

        for action in actions:
            if not action.is_move:
                continue

            best_fraction = 0.0
            best_opp_slot: Optional[int] = None

            for opp_slot, opp in enumerate(state.opp_actives):
                if opp is None or opp.fainted:
                    continue
                # Pass the observed current HP so KO thresholds use actual HP,
                # not the typical-spread max HP estimate.  Skip the override when
                # HP is stored as a percentage (hp_is_percentage=True) because
                # opp.hp would then be e.g. 60 meaning "60%", not 60 absolute HP.
                cur_hp = (opp.hp
                          if (not opp.hp_is_percentage and opp.hp > 0)
                          else None)
                results = outgoing_damage(
                    our_species=mon.species,
                    our_stats=stats,
                    our_moves=[action.move_name],
                    opp_species=opp.species,
                    our_ability=tm.ability,
                    our_item=tm.item,
                    opp_ability=_effective_ability(opp) or "",
                    opp_item=opp.item,
                    weather=state.weather,
                    ally_faint_count=ally_faints,
                    opp_current_hp=cur_hp,
                    opp_hp_percent=(opp.hp if (opp.hp_is_percentage and 0 < opp.hp < 100) else None),
                    opp_screens=getattr(state, "opp_screens", None),
                    attacker_boosts=mon.boosts,
                    defender_boosts=opp.boosts,
                )
                if results:
                    frac_avg = results[0].hp_fraction_avg
                    frac_min = results[0].hp_fraction_min
                    action.target_hp_fractions[opp_slot] = (frac_avg, frac_min)
                    if frac_avg > best_fraction:
                        best_fraction = frac_avg
                        best_opp_slot = opp_slot

            if best_fraction > 0:
                factor = 1.0 + best_fraction * 2.0
                action.weight *= factor
                action.reasons.append(
                    f"{self.name}: {best_fraction:.0%} HP -> x{factor:.2f}"
                )
                if best_opp_slot is not None:
                    action.target_slot = best_opp_slot


class ThreatEliminationModule(ScoringModule):
    """
    Large bonus for moves that guarantee a KO this turn.

    Applied on top of DamageOutputModule's score:

      Guaranteed OHKO (min roll >= defender HP)  ->  x5.0

    Only fires when the KO is certain on every damage roll.  Partial KO
    signals (max-roll OHKO, 2HKO) are intentionally excluded — damage
    output alone already rewards high-damage moves via DamageOutputModule.

    **Offensive speed gate:** the bonus is withheld entirely when this slot will
    be KO'd before it can act (a faster opponent OHKOs us first — see
    :func:`_ko_before_acting`).  A "guaranteed" kill we never live to deliver is
    not guaranteed, and crediting it makes a doomed attack out-score Protect /
    switching.  This is the offensive mirror of the defensive
    :func:`_opp_neutralized_before_acting` check.
    """

    name = "threat_elimination"

    GUARANTEED_OHKO = 5.0

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        mon = state.my_actives[slot] if slot < len(state.my_actives) else None
        if mon is None:
            return
        tm = find_member(mon.species)
        stats = _our_stats(state, slot)
        if tm is None or stats is None:
            return

        if not any(o is not None for o in state.opp_actives):
            return

        # If we are KO'd before we can act, no kill we line up is deliverable —
        # withhold the guaranteed-OHKO bonus so a wasted attack stops out-scoring
        # Protect / switching.
        if _ko_before_acting(state, slot):
            return

        ally_faints = sum(1 for p in state.my_team if p.fainted)

        for action in actions:
            if not action.is_move:
                continue

            best_factor = 1.0
            best_reason = ""
            best_opp_slot: Optional[int] = None

            for opp_slot, opp in enumerate(state.opp_actives):
                if opp is None or opp.fainted:
                    continue
                cur_hp = (opp.hp
                          if (not opp.hp_is_percentage and opp.hp > 0)
                          else None)
                results = outgoing_damage(
                    our_species=mon.species,
                    our_stats=stats,
                    our_moves=[action.move_name],
                    opp_species=opp.species,
                    our_ability=tm.ability,
                    our_item=tm.item,
                    opp_ability=_effective_ability(opp) or "",
                    opp_item=opp.item,
                    weather=state.weather,
                    ally_faint_count=ally_faints,
                    opp_current_hp=cur_hp,
                    opp_hp_percent=(opp.hp if (opp.hp_is_percentage and 0 < opp.hp < 100) else None),
                    opp_screens=getattr(state, "opp_screens", None),
                    attacker_boosts=mon.boosts,
                    defender_boosts=opp.boosts,
                )
                if not results:
                    continue
                r = results[0]

                if r.is_ohko and self.GUARANTEED_OHKO > best_factor:
                    best_factor = self.GUARANTEED_OHKO
                    best_reason = f"guaranteed OHKO on {opp.species}"
                    best_opp_slot = opp_slot

            if best_factor > 1.0:
                action.weight *= best_factor
                action.reasons.append(
                    f"{self.name}: {best_reason} -> x{best_factor}"
                )
                if best_opp_slot is not None:
                    # KO target takes priority over the damage-output target
                    action.target_slot = best_opp_slot




class IncomingOHKOModule(ScoringModule):
    """
    Boosts Protect-family moves when an opponent can one-hit KO this slot.

    "Can they knock me out this turn?"

    When any active opponent's **maximum** damage roll exceeds our current HP,
    Protect-family moves gain ×2.5.  Protecting guarantees survival for this
    turn while the partner continues to act freely.

    Suppressed (no boost) when Protect cannot improve the outcome:
    * 1v1 endgame — our last mon vs their last mon; Protect only delays.
    * Numerical advantage (2v1) — Protecting cannot improve either outcome.
    """

    name = "incoming_ohko"

    THREATENED_FACTOR = 2.5

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        mon = state.my_actives[slot] if slot < len(state.my_actives) else None
        if mon is None:
            return
        tm    = find_member(mon.species)
        stats = _our_stats(state, slot)
        if tm is None or stats is None:
            return

        # Suppress in 1v1 endgame and 2v1 — Protect can't help.
        bench_alive   = len(state.available_switches)
        partner_alive = any(
            p is not None and not p.fainted
            for i, p in enumerate(state.my_actives)
            if i != slot
        )
        our_active_count = sum(
            1 for p in state.my_actives if p is not None and not p.fainted
        )
        active_opp_count = sum(
            1 for o in state.opp_actives if o is not None and not o.fainted
        )
        is_1v1_endgame      = (bench_alive == 0 and not partner_alive and active_opp_count == 1)
        numerical_advantage = (our_active_count > active_opp_count > 0)
        if is_1v1_endgame or numerical_advantage:
            return

        # Check if any opponent can OHKO us on their max damage roll AND will
        # survive to land that hit.  Speed awareness: an attacker that a faster
        # ally is guaranteed to OHKO this turn dies before it can act, so it is
        # not a real OHKO threat and should not push us toward Protect.
        at_full    = (mon.hp >= mon.max_hp) or (mon.hp_is_percentage and mon.hp >= 99)
        threatened = False
        for opp_slot, opp in enumerate(state.opp_actives):
            if opp is None or opp.fainted:
                continue
            threats = incoming_damage(
                opp_species=opp.species,
                our_species=mon.species,
                our_stats=stats,
                opp_ability=_effective_ability(opp) or "",
                opp_item=opp.item,
                our_ability=_our_ability_for_damage(tm, mon, state.designated_mega),
                our_item=tm.item,
                weather=state.weather,
                our_defender_is_full_hp=at_full,
                opp_boosts=opp.boosts,
                our_boosts=mon.boosts,
            )
            if not any(t.ohko_with_max_roll for t in threats):
                continue
            if _opp_neutralized_before_acting(state, opp_slot, opp):
                continue  # dies before acting → not a live OHKO threat this turn
            threatened = True
            break

        if not threatened:
            return

        for action in actions:
            if action.move_name not in _PROTECT_MOVES:
                continue
            action.weight *= self.THREATENED_FACTOR
            action.reasons.append(
                f"{self.name}: OHKO threat -> x{self.THREATENED_FACTOR}"
            )


class TurnOrderModule(ScoringModule):
    """
    Scales attack weights by estimated turn-order position in the 4-mon field.

    Turn order is estimated by counting how many of the three other active
    Pokémon (two opponents + our partner) we are likely to outspeed using
    ``will_outspeed`` (probability > 0.5).

    Position multipliers:
      1st (fastest):  ×2.0
      2nd:            ×1.5
      3rd:            ×1.0
      4th (slowest):  ×0.75

    Only applies to attack moves — Protect-family and switch actions are
    unaffected.
    """

    name = "turn_order"

    _MULTIPLIERS: dict[int, float] = {1: 2.0, 2: 1.5, 3: 1.0, 4: 0.75}

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        ours = _our_combatant(state, slot)
        if ours is None:
            return

        # Gather all other active Pokémon: opponents first, then partner.
        others: list[Combatant] = []
        for opp_slot in range(len(state.opp_actives)):
            c = _opp_combatant(state, opp_slot)
            if c is not None:
                others.append(c)
        for partner_slot in range(len(state.my_actives)):
            if partner_slot == slot:
                continue
            c = _our_combatant(state, partner_slot)
            if c is not None:
                others.append(c)

        if not others:
            return  # No other active Pokémon — nothing to estimate.

        num_beat = sum(1 for other in others
                       if will_outspeed(ours, other, trick_room=state.trick_room) > 0.5)
        # Position 1 = fastest; position len(others)+1 = slowest.
        position = len(others) - num_beat + 1
        # Clamp to [1, 4] for the multiplier table.
        position = max(1, min(4, position))

        factor = self._MULTIPLIERS[position]

        for action in actions:
            if not action.is_move or action.is_switch or action.move_name in _PROTECT_MOVES:
                continue
            action.weight *= factor
            action.reasons.append(
                f"{self.name}: turn order pos {position}/{len(others) + 1}"
                f" (beat {num_beat}/{len(others)}) -> x{factor}"
            )


class ConsecutiveProtectModule(ScoringModule):
    """
    Penalises repeated Protect use with a flat multiplier.

    In Gen 9 VGC, using a Protect-family move on consecutive turns has a
    greatly reduced success chance — the second attempt usually fails.  This
    module applies ×0.2 to all Protect-family actions whenever this slot used
    a Protect-family move last turn.

    No exceptions or waivers.  The penalty applies regardless of HP, threat
    level, field conditions, or any other context.  The expected value of a
    consecutive Protect is simply too low to justify in almost any situation.
    """

    name = "consecutive_protect"

    CONSECUTIVE_PENALTY = 0.2

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        last_move = (
            state.my_last_moves[slot]
            if slot < len(state.my_last_moves) else ""
        )
        if last_move not in _PROTECT_MOVES:
            return  # No penalty — did not use Protect last turn.

        for action in actions:
            if action.move_name not in _PROTECT_MOVES:
                continue
            action.weight *= self.CONSECUTIVE_PENALTY
            action.reasons.append(
                f"{self.name}: used Protect last turn -> x{self.CONSECUTIVE_PENALTY}"
            )


def _partner_can_ohko(
    state: "BattleState",
    partner_slot: int,
    opp: "Pokemon",
) -> bool:
    """Return True if any available partner move guarantees an OHKO on *opp*.

    Used by :class:`ProtectModule` to verify that surviving via Protect
    leads to the threat being eliminated this turn by the partner.
    A move is skipped if it is flagged disabled in ``moves_per_slot`` or
    listed in ``my_disabled_moves``.
    """
    partner = (
        state.my_actives[partner_slot]
        if partner_slot < len(state.my_actives) else None
    )
    if partner is None or partner.fainted:
        return False
    partner_tm    = find_member(partner.species)
    partner_stats = _our_stats(state, partner_slot)
    if partner_tm is None or partner_stats is None:
        return False
    if partner_slot >= len(state.moves_per_slot):
        return False

    disabled_list = getattr(state, "my_disabled_moves", [])
    disabled = (
        disabled_list[partner_slot]
        if partner_slot < len(disabled_list) else None
    )
    # For a percentage-HP opponent we do NOT know its true max HP (``max_hp`` is
    # a placeholder, typically 100), so passing ``max_hp * pct / 100`` as an
    # absolute current-HP value makes every move look like a guaranteed OHKO
    # (e.g. a 97%-avg hit "OHKOs" a phantom 100-HP bar).  Mirror
    # DamageOutputModule/ThreatEliminationModule: pass None and let the damage
    # layer use typical-spread stats so KO detection matches the rest of the engine.
    opp_hp = (opp.hp if (not opp.hp_is_percentage and opp.hp > 0) else None)
    ally_faints = sum(1 for p in state.my_team if p is not None and p.fainted)

    for move in state.moves_per_slot[partner_slot]:
        move_name = move.get("move", "")
        if not move_name or move.get("disabled"):
            continue
        if disabled and move_name == disabled:
            continue
        results = outgoing_damage(
            our_species=partner.species,
            our_stats=partner_stats,
            our_moves=[move_name],
            our_ability=partner_tm.ability or "",
            our_item=partner_tm.item,
            opp_species=opp.species,
            opp_ability=_effective_ability(opp) or "",
            opp_item=opp.item,
            weather=state.weather,
            ally_faint_count=ally_faints,
            opp_current_hp=opp_hp,
            attacker_boosts=partner.boosts,
            defender_boosts=opp.boosts,
        )
        if results and results[0].is_ohko:
            return True
    return False


def _opp_has_attacking_priority(opp: "Pokemon") -> bool:
    """Return True if *opp* lands a damaging move before any normal-priority
    attack of ours, regardless of Speed.

    Currently this is the **Gale Wings** case: Talonflame's Flying-type moves
    (notably Brave Bird) gain +1 priority while it is at full HP.  Talonflame in
    the Champions format is assumed to run Gale Wings, so an unrevealed ability
    is treated as Gale Wings (consistent with ``_tw_setter_has_priority``); a
    contradicting revealed ability disables it.  Gale Wings only grants priority
    at full HP, so a chipped Talonflame is excluded.

    New ability- or item-based priority attackers can be added here as the
    metagame requires.
    """
    if opp.species == "Talonflame":
        at_full = (opp.hp >= opp.max_hp) or (opp.hp_is_percentage and opp.hp >= 100)
        if at_full and _effective_ability(opp) in ("Gale Wings", None):
            return True
    return False


def _opp_neutralized_before_acting(
    state: "BattleState",
    opp_slot: int,
    opp: "Pokemon",
) -> bool:
    """Return True if *opp* will be KO'd before it can act this turn.

    This holds when one of our active Pokémon both (a) outspeeds *opp* and
    (b) has a move that guarantees an OHKO on it.  In that case *opp* faints
    before landing its hit, so Protecting in order to survive that hit buys
    nothing — we (or our partner) should simply attack.

    Exception — **priority attackers** (see ``_opp_has_attacking_priority``):
    a Gale Wings Talonflame's Brave Bird strikes before our normal-priority KO
    move, so it gets its hit off even when we are faster.  Such an attacker is
    never treated as neutralised.  Other move-based priority (Prankster status,
    Fake Out, Sucker Punch, etc.) is still not modelled.
    """
    if _opp_has_attacking_priority(opp):
        return False
    opp_c = _opp_combatant(state, opp_slot)
    if opp_c is None:
        return False
    for our_slot, mon in enumerate(state.my_actives):
        if mon is None or mon.fainted:
            continue
        our_c = _our_combatant(state, our_slot)
        if our_c is None:
            continue
        if will_outspeed(our_c, opp_c, trick_room=state.trick_room) <= 0.5:
            continue  # we don't move first → can't remove it before it acts
        if _partner_can_ohko(state, our_slot, opp):
            return True
    return False


def _ko_before_acting(state: "BattleState", slot: int) -> bool:
    """Return True if our slot will (very likely) be KO'd before it can act.

    Offensive mirror of :func:`_opp_neutralized_before_acting`: an active
    opponent (a) moves before us — it outspeeds us, or has move-based attacking
    priority — (b) can OHKO us on its max roll, and (c) is *not* itself removed
    before it acts (so a partner that kills the threat first cancels this).

    When this holds, any "guaranteed OHKO" we line up is not actually
    deliverable — we faint first — so ThreatEliminationModule must not credit
    the kill.  Used to gate the ×5.0 KO bonus, the same way the defensive
    modules gate their threat checks on whether a hit will connect.
    """
    mon = state.my_actives[slot] if slot < len(state.my_actives) else None
    if mon is None:
        return False
    tm    = find_member(mon.species)
    stats = _our_stats(state, slot)
    our_c = _our_combatant(state, slot)
    if tm is None or stats is None or our_c is None:
        return False

    at_full = (mon.hp >= mon.max_hp) or (mon.hp_is_percentage and mon.hp >= 99)
    for opp_slot, opp in enumerate(state.opp_actives):
        if opp is None or opp.fainted:
            continue
        opp_c = _opp_combatant(state, opp_slot)
        if opp_c is None:
            continue
        # Does this opponent act before us?  (Speed, or Gale-Wings-style
        # attacking priority.)
        moves_first = (
            will_outspeed(opp_c, our_c, trick_room=state.trick_room) > 0.5
            or _opp_has_attacking_priority(opp)
        )
        if not moves_first:
            continue
        # If a faster ally removes this opponent first, it never lands its hit.
        if _opp_neutralized_before_acting(state, opp_slot, opp):
            continue
        threats = incoming_damage(
            opp_species=opp.species,
            our_species=mon.species,
            our_stats=stats,
            opp_ability=_effective_ability(opp) or "",
            opp_item=opp.item,
            our_ability=_our_ability_for_damage(tm, mon, state.designated_mega),
            our_item=tm.item,
            weather=state.weather,
            our_defender_is_full_hp=at_full,
            opp_boosts=opp.boosts,
            our_boosts=mon.boosts,
        )
        # Require a *guaranteed* OHKO (min roll), not just a max-roll one: only
        # cancel our kill credit when we are certain to faint first.  If we might
        # survive the roll, attacking for the kill is a legitimate gamble — this
        # mirrors _opp_neutralized_before_acting requiring a guaranteed ally KO.
        if any(t.is_ohko for t in threats):
            return True
    return False


class ProtectModule(ScoringModule):
    """
    Boosts Protect when an unavoidable OHKO is coming in this turn AND a
    partner clears one of the threats the same turn.

    "Will I get knocked out this turn anyway, and is Protecting worth it?"

    The ×3.0 boost fires only when ALL of the following hold:

    1. At least one active opponent can OHKO this slot on its max damage roll.
    2. **Speed awareness** — at least one of those OHKO threats will actually
       connect: it is NOT killed before it can act.  A threat that a faster
       ally is guaranteed to OHKO this turn dies first, so Protecting to
       survive *that* hit is pointless.  This covers both faster attackers and
       slower attackers we cannot remove — either way the hit lands unless we
       Protect.
    3. A partner has a non-disabled move that guarantees an OHKO on one of the
       OHKO threats, so Protecting resolves the board: we survive the
       unavoidable hit and a threat falls the same turn, leaving us ahead and
       free to act next turn.

    Condition 2's "killed before acting" test is mostly Speed-based, but a Gale
    Wings Talonflame (priority Brave Bird at full HP) is treated as always
    connecting — see ``_opp_has_attacking_priority``.  Other move-based priority
    (Prankster status, Fake Out, Sucker Punch) is still not modelled.

    Suppressed (no boost) in 1v1 endgame (no partner) and 2v1 numerical
    advantage (battle outcome is already decided this turn by the partner).
    """

    name = "protect"

    PARTNER_KO_FACTOR = 3.0

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        mon = state.my_actives[slot] if slot < len(state.my_actives) else None
        if mon is None:
            return
        tm    = find_member(mon.species)
        stats = _our_stats(state, slot)
        if tm is None or stats is None:
            return

        # ── Suppress states ───────────────────────────────────────────────────
        bench_alive   = len(state.available_switches)
        partner_alive = any(
            p is not None and not p.fainted
            for i, p in enumerate(state.my_actives)
            if i != slot
        )
        our_active_count = sum(
            1 for p in state.my_actives if p is not None and not p.fainted
        )
        active_opp_count = sum(
            1 for o in state.opp_actives if o is not None and not o.fainted
        )
        is_1v1_endgame      = (bench_alive == 0 and not partner_alive and active_opp_count == 1)
        numerical_advantage = (our_active_count > active_opp_count > 0)
        if is_1v1_endgame or numerical_advantage:
            return

        at_full = (mon.hp >= mon.max_hp) or (mon.hp_is_percentage and mon.hp >= 99)

        # ── Every opponent that can OHKO us this turn (max roll) ──────────────
        ohko_threats: list[tuple[int, "Pokemon"]] = []
        for opp_slot, opp in enumerate(state.opp_actives):
            if opp is None or opp.fainted:
                continue
            threats = incoming_damage(
                opp_species=opp.species,
                our_species=mon.species,
                our_stats=stats,
                opp_ability=_effective_ability(opp) or "",
                opp_item=opp.item,
                our_ability=_our_ability_for_damage(tm, mon, state.designated_mega),
                our_item=tm.item,
                weather=state.weather,
                our_defender_is_full_hp=at_full,
                opp_boosts=opp.boosts,
                our_boosts=mon.boosts,
            )
            if any(t.ohko_with_max_roll for t in threats):
                ohko_threats.append((opp_slot, opp))

        if not ohko_threats:
            return

        # ── Speed awareness: at least one threat must actually connect ────────
        # A threat a faster ally is guaranteed to OHKO dies before it acts, so
        # Protecting to survive *that* hit is pointless.  Only Protect when a
        # threat will still land its OHKO on us this turn.
        threats_that_connect = [
            (os, op) for (os, op) in ohko_threats
            if not _opp_neutralized_before_acting(state, os, op)
        ]
        if not threats_that_connect:
            return

        # ── A partner must clear one of those threats this turn ───────────────
        # The ×3.0 is for the case where Protecting resolves the board: we
        # survive the unavoidable hit and a partner removes a threat the same
        # turn, so we enter next turn ahead and at full freedom.
        partner_slots = [
            i for i, p in enumerate(state.my_actives)
            if i != slot and p is not None and not p.fainted
        ]
        if not any(
            _partner_can_ohko(state, ps, opp)
            for ps in partner_slots
            for (_, opp) in ohko_threats
        ):
            return

        for action in actions:
            if action.move_name not in _PROTECT_MOVES:
                continue
            action.weight *= self.PARTNER_KO_FACTOR
            action.reasons.append(
                f"{self.name}: unavoidable OHKO incoming + partner clears a threat"
                f" -> x{self.PARTNER_KO_FACTOR}"
            )


class SwitchModule(ScoringModule):
    """
    Scores switches by the value of the resulting board — a cheap 1-ply
    lookahead — so a switch competes on the same scale as an attack instead of a
    type-matchup multiplier capped at ×4.0.

    For each legal switch, weight = TEMPO × (offense_term + avoided) × safety:

      * offense_term = 1.0 + max(0, switch_in_offense − current_offense) × 2.0.
        Uses the *gain* in best-damage from pivoting (same 0..2 scale
        DamageOutputModule uses for moves), so a switch is only rewarded when the
        incoming mon threatens meaningfully more than staying does.  The current
        mon's Struggle is ignored when measuring "staying" offense, so a mon that
        can only Struggle is correctly seen as contributing nothing.
      * avoided = ESCAPE_BONUS when the current mon is OHKO-threatened (by a
        threat that will actually connect — speed-aware) and the switch-in
        survives every active opponent's max roll: the value of not losing the
        current mon for free.
      * safety = 1.0 if the switch-in survives, else DANGER_FACTOR (don't pivot
        into another OHKO).
      * TEMPO discounts for giving up this turn's action and conceding a free
        hit on the switch-in.

    A switch the partner already committed to (same bench target) is vetoed (×0).

    Net effect: a switch wins only when the incoming mon is meaningfully better
    than staying — escaping a KO into a healthy threat, or pivoting a walled /
    Struggling mon — and loses to a current-mon attack that does real work.
    """

    name = "switch_eval"

    TEMPO_FACTOR    = 0.6   # switching forfeits this turn + concedes a free hit
    ESCAPE_BONUS    = 3.0   # value of dodging an otherwise-certain KO
    DANGER_FACTOR   = 0.3   # switching into a mon that is itself OHKO'd
    UNFORCED_PIVOT  = 0.5   # extra discount on a pure-offense pivot (not escaping):
                            # an unforced switch concedes initiative — the opponent
                            # gets a free turn and need not stay in.

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        mon = state.my_actives[slot] if slot < len(state.my_actives) else None
        if mon is None:
            return

        # ── Cross-slot coordination: veto switches already committed by a partner ─
        already_switching: set[str] = set()
        for prior in state.my_slot_decisions:
            if prior is not None and prior.is_switch:
                already_switching.add(prior.switch_target)
        for action in actions:
            if action.is_switch and action.switch_target in already_switching:
                action.weight = 0.0
                action.reasons.append(
                    f"{self.name}: partner already switching to"
                    f" {action.switch_target} -> x0"
                )

        live_switches = [
            a for a in actions
            if a.is_switch and a.switch_target not in already_switching
        ]
        if not live_switches:
            return

        # ── Current-mon offense (what "staying" threatens) and OHKO threat ────
        # Struggle is excluded — it is never a real reason to stay.
        tm    = find_member(mon.species)
        stats = _our_stats(state, slot)
        cur_moves = [
            md.get("move", "")
            for md in (state.moves_per_slot[slot]
                       if slot < len(state.moves_per_slot) else [])
            if md.get("move") and not md.get("disabled", False)
            and md.get("move", "").lower() != "struggle"
            and md.get("move", "") not in _PROTECT_MOVES
        ]
        cur_offense = self._best_offense(
            state, mon.species, stats,
            tm.ability if tm else None, tm.item if tm else None, cur_moves,
        )

        cur_threatened = False
        if tm and stats:
            at_full = (mon.hp >= mon.max_hp) or (mon.hp_is_percentage and mon.hp >= 99)
            for opp_slot, opp in enumerate(state.opp_actives):
                if opp is None or opp.fainted:
                    continue
                threats = incoming_damage(
                    opp_species=opp.species,
                    our_species=mon.species,
                    our_stats=stats,
                    opp_ability=_effective_ability(opp) or "",
                    opp_item=opp.item,
                    our_ability=_our_ability_for_damage(tm, mon, state.designated_mega),
                    our_item=tm.item,
                    weather=state.weather,
                    our_defender_is_full_hp=at_full,
                    opp_boosts=opp.boosts,
                    our_boosts=mon.boosts,
                )
                if not any(t.ohko_with_max_roll for t in threats):
                    continue
                if _opp_neutralized_before_acting(state, opp_slot, opp):
                    continue
                cur_threatened = True
                break

        # ── Score each live switch by resulting board value ───────────────────
        for action in live_switches:
            bench_tm = find_member(action.switch_target)
            if bench_tm is None or not getattr(bench_tm, "stats", None):
                continue  # unknown bench mon — leave neutral (×1.0)

            bench_moves = [m for m in bench_tm.moves if m not in _PROTECT_MOVES]
            offense  = self._best_offense(
                state, action.switch_target, bench_tm.stats,
                bench_tm.ability, bench_tm.item, bench_moves,
            )
            survives = self._switch_in_survives(state, action.switch_target, bench_tm)

            gain        = max(0.0, offense - cur_offense)
            gain_term   = gain * 2.0
            # An unforced pivot (we are not escaping a KO) concedes initiative,
            # so its offensive upside is worth less than a forced/escape pivot.
            if not (cur_threatened and survives):
                gain_term *= self.UNFORCED_PIVOT
            offense_term = 1.0 + gain_term
            avoided_term = self.ESCAPE_BONUS if (cur_threatened and survives) else 0.0
            safety       = 1.0 if survives else self.DANGER_FACTOR
            value        = self.TEMPO_FACTOR * (offense_term + avoided_term) * safety

            action.weight *= value
            notes = [f"+{gain:.0%} offense vs staying"]
            if cur_threatened and survives:
                notes.append("escapes OHKO")
            if not survives:
                notes.append("switch-in OHKO'd")
            action.reasons.append(
                f"{self.name}: board value ({', '.join(notes)}) -> x{value:.2f}"
            )

    def _best_offense(
        self, state: "BattleState", species: str,
        stats: Optional[dict], ability: Optional[str],
        item: Optional[str], move_names: list[str],
    ) -> float:
        """Best average damage fraction *species* deals to any active opponent."""
        if not stats or not move_names:
            return 0.0
        ally_faints = sum(1 for p in state.my_team if p is not None and p.fainted)
        best = 0.0
        for opp in state.opp_actives:
            if opp is None or opp.fainted:
                continue
            cur_hp = (opp.hp if (not opp.hp_is_percentage and opp.hp > 0) else None)
            for mv in move_names:
                results = outgoing_damage(
                    our_species=species, our_stats=stats, our_moves=[mv],
                    our_ability=ability or "", our_item=item,
                    opp_species=opp.species, opp_ability=_effective_ability(opp) or "",
                    opp_item=opp.item, weather=state.weather,
                    ally_faint_count=ally_faints, opp_current_hp=cur_hp,
                )
                if results:
                    best = max(best, results[0].hp_fraction_avg)
        return best

    def _switch_in_survives(
        self, state: "BattleState", species: str, bench_tm,
    ) -> bool:
        """True if no active opponent OHKOs the switch-in on its max roll."""
        for opp in state.opp_actives:
            if opp is None or opp.fainted:
                continue
            threats = incoming_damage(
                opp_species=opp.species, our_species=species,
                our_stats=bench_tm.stats, opp_ability=_effective_ability(opp) or "",
                opp_item=opp.item, our_ability=bench_tm.ability or "",
                our_item=bench_tm.item, weather=state.weather,
                our_defender_is_full_hp=True,
            )
            if any(t.ohko_with_max_roll for t in threats):
                return False
        return True

    @staticmethod
    def _infer_threat_types(state: "BattleState") -> list[str]:
        """Revealed *damaging* move types + all STAB types of each active opponent.

        Both types of a dual-type opponent are included — a Whimsicott threatens
        with both Grass and Fairy moves, and a Garchomp threatens with both Dragon
        and Ground moves.  Using only the primary type causes systematic errors:
        e.g. Garchomp's secondary Ground type is super-effective vs Steel, so
        treating it as Dragon-only makes Steel-type switch-ins look safer than they
        are.

        Status moves (Trick Room, Tailwind, Follow Me, Helping Hand, etc.) are
        excluded — they don't deal damage and should not influence which switch-in
        types are considered safe or dangerous.
        """
        result: list[str] = []
        for opp in state.opp_actives:
            if opp is None or opp.fainted:
                continue
            for move_name in opp.moves:
                if get_move_category(move_name) == "Status":
                    continue   # non-damaging: no type-matchup threat
                t = get_move_type(move_name)
                if t:
                    result.append(t)
            result.extend(types_of(opp.species) or [])
        return result

    @staticmethod
    def _worst_effectiveness(threat_types: list[str], defender_types: list[str]) -> float:
        """Highest type-effectiveness multiplier any threat achieves vs the defender."""
        worst = 0.0
        for att_type in threat_types:
            eff = type_effectiveness(att_type, defender_types)
            if eff > worst:
                worst = eff
        return worst


class DoublingUpModule(ScoringModule):
    """
    Adjusts weights when both active Pokémon would target the same opponent.

    Doubling up is costly if the target uses Protect — both moves are wasted.
    The penalty is reduced in two situations:

    * The target used Protect last turn — they are unlikely to spam it again,
      so doubling up carries less risk.
    * The OTHER opponent is not threatening — since we are not giving up much
      by ignoring them, the opportunity cost of doubling up is low.

    Only fires for slot 1+ (slot 0 has no prior partner decision to compare).

    Penalty schedule (multiplicative, applied to the doubling-up move):
        Both conditions favour doubling up:        ×0.70
        One condition favours doubling up:         ×0.55
        Neither condition — riskiest double up:    ×0.40
    """

    name = "doubling_up"

    # (target_protected_last_turn, other_not_threatening) → weight multiplier
    _FACTORS = {
        (True,  True):  0.70,
        (True,  False): 0.55,
        (False, True):  0.55,
        (False, False): 0.40,
    }

    # Extra redirect when the partner slot already has a near-certain KO on the
    # same target — attacking there too wastes the action if the target dies.
    _PARTNER_KILLS_THRESHOLD          = 10.0  # near-certain KO → moderate redirect
    _PARTNER_CONFIRMED_OHKO_THRESHOLD = 15.0  # guaranteed OHKO  → near-veto
    PARTNER_KILLS_FACTOR              = 0.65  # multiplied on top of the normal _FACTORS value
    PARTNER_CONFIRMED_OHKO_FACTOR     = 0.05  # near-veto: target is already dead

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        # Need at least two opponents for doubling-up to be meaningful.
        active_opps = [i for i, o in enumerate(state.opp_actives) if o is not None and not o.fainted]
        if len(active_opps) < 2:
            return

        # Find what an earlier slot already committed to targeting.
        partner_target: Optional[int] = None
        partner_action: Optional[Action] = None
        for other_slot, prior in enumerate(state.my_slot_decisions):
            if other_slot == slot:
                continue
            if prior is not None and prior.target_slot is not None:
                partner_target = prior.target_slot
                partner_action = prior
                break

        if partner_target is None:
            return  # No prior slot committed yet — nothing to coordinate against.

        # Is partner's committed action a near-certain KO on that target?
        # Also check reasons for threat_elimination: FakeOut ×0.5 can push a
        # genuine OHKO weight below the numeric threshold, but the kill is still
        # guaranteed if ThreatElimination fired.
        _partner_has_threat_elim = (
            partner_action is not None
            and any(r.startswith("threat_elimination:")
                    for r in (partner_action.reasons or []))
        )
        partner_kills = (
            partner_action is not None
            and (partner_action.weight >= self._PARTNER_KILLS_THRESHOLD
                 or _partner_has_threat_elim)
        )

        # Did the target Pokémon use a Protect move last turn?
        opp_last = state.opp_last_moves
        target_protected = (
            partner_target < len(opp_last) and
            opp_last[partner_target] in _PROTECT_MOVES
        )

        # Is the OTHER opponent threatening either of our active Pokémon?
        other_threatening = self._other_opp_is_threatening(state, slot, partner_target)

        factor = self._FACTORS[(target_protected, not other_threatening)]

        for action in actions:
            if not action.is_move:
                continue
            if action.target_slot != partner_target:
                continue   # Not doubling up on this action.

            # ── Confirmed-OHKO redirect ────────────────────────────────────────
            # When the partner already has a confirmed OHKO on this target the
            # target is effectively dead — attacking there too wastes the action.
            # If another opponent is still active, redirect this move there so
            # the bot attacks the surviving threat rather than defaulting to
            # Protect.  Only fall back to the near-veto when no alt target exists.
            # A confirmed OHKO is signalled either by weight ≥ threshold OR by
            # ThreatElimination having fired (FakeOut ×0.5 can depress weight
            # below the numeric threshold even on a guaranteed kill).
            _partner_confirmed_ohko = (
                partner_kills
                and partner_action is not None
                and (partner_action.weight >= self._PARTNER_CONFIRMED_OHKO_THRESHOLD
                     or _partner_has_threat_elim)
            )
            if _partner_confirmed_ohko:
                alt_targets = [i for i in active_opps if i != partner_target]
                if alt_targets:
                    new_slot = alt_targets[0]
                    new_opp  = (state.opp_actives[new_slot]
                                if new_slot < len(state.opp_actives) else None)

                    # Swap the DamageOutput + ThreatElimination contribution from
                    # the dying target to the surviving one, preserving TurnOrder
                    # and all other non-target-specific factors.
                    old_frac_avg, _   = action.target_hp_fractions.get(partner_target, (0.0, 0.0))
                    new_frac_avg, new_frac_min = action.target_hp_fractions.get(new_slot, (0.0, 0.0))

                    had_threat_elim = any(
                        r.startswith("threat_elimination:") for r in action.reasons
                    )
                    old_dmg = 1.0 + old_frac_avg * 2.0
                    if had_threat_elim:
                        old_dmg *= ThreatEliminationModule.GUARANTEED_OHKO

                    new_dmg = 1.0 + new_frac_avg * 2.0
                    new_threat = (ThreatEliminationModule.GUARANTEED_OHKO
                                  if new_frac_min >= 1.0 else 1.0)

                    action.weight /= old_dmg
                    action.weight *= new_dmg * new_threat
                    action.target_slot = new_slot

                    action.reasons = [
                        r for r in action.reasons
                        if not r.startswith((
                            "damage_output:", "threat_elimination:",
                            "field_setter:", "opp_protect_recency:",
                        ))
                    ]
                    # Prepend the new damage/threat reasons so the log reads
                    # in the same order as a naturally-scored action.
                    new_reasons_prefix = []
                    if new_frac_avg > 0:
                        new_reasons_prefix.append(
                            f"damage_output: {new_frac_avg:.0%} HP"
                            f" -> x{new_dmg:.2f}"
                        )
                    if new_threat > 1.0:
                        opp_name = new_opp.species if new_opp else f"slot {new_slot}"
                        new_reasons_prefix.append(
                            f"threat_elimination: guaranteed OHKO on {opp_name}"
                            f" -> x{new_threat:.0f}.0"
                        )
                    action.reasons = new_reasons_prefix + action.reasons
                    action.reasons.append(
                        f"{self.name}: partner confirmed OHKO"
                        f" (w={partner_action.weight:.1f})"
                        f" -> redirect to slot {new_slot}, damage re-scored"
                    )
                    continue  # No doubling-up penalty — we are no longer doubling up.

            action.weight *= factor
            why_parts = []
            if target_protected:
                why_parts.append("protected last turn")
            if not other_threatening:
                why_parts.append("other opp not threatening")
            if not why_parts:
                why_parts.append("Protect risk, other opp threatening")
            action.reasons.append(
                f"{self.name}: doubling up ({', '.join(why_parts)}) -> x{factor}"
            )
            if partner_kills:
                partner_wt = partner_action.weight
                if _partner_confirmed_ohko:
                    # Only reached when there is no alternative target.
                    # Near-veto: only a massive damage opportunity on the same
                    # target should overcome this.
                    kfactor = self.PARTNER_CONFIRMED_OHKO_FACTOR
                    klabel  = f"partner confirmed OHKO (w={partner_wt:.1f}), no alt target"
                else:
                    kfactor = self.PARTNER_KILLS_FACTOR
                    klabel  = f"partner near-KO (w={partner_wt:.1f})"
                action.weight *= kfactor
                action.reasons.append(
                    f"{self.name}: {klabel} -> x{kfactor}"
                )

    @staticmethod
    def _other_opp_is_threatening(
        state: "BattleState", our_slot: int, ignored_opp_slot: int
    ) -> bool:
        """
        Return True if any opponent OTHER than *ignored_opp_slot* threatens a
        max-roll OHKO on our active Pokémon at *our_slot*.
        """
        mon = state.my_actives[our_slot] if our_slot < len(state.my_actives) else None
        if mon is None:
            return True   # Unknown — assume threatening.
        tm    = find_member(mon.species)
        stats = _our_stats(state, our_slot)
        if tm is None or stats is None:
            return True

        at_full = (mon.hp >= mon.max_hp) or (mon.hp_is_percentage and mon.hp >= 99)

        for opp_slot, opp in enumerate(state.opp_actives):
            if opp is None or opp.fainted or opp_slot == ignored_opp_slot:
                continue
            threats = incoming_damage(
                opp_species=opp.species,
                our_species=mon.species,
                our_stats=stats,
                opp_ability=_effective_ability(opp) or "",
                opp_item=opp.item,
                our_ability=_our_ability_for_damage(tm, mon, state.designated_mega),
                our_item=tm.item,
                weather=state.weather,
                our_defender_is_full_hp=at_full,
                opp_boosts=opp.boosts,
                our_boosts=mon.boosts,
            )
            if any(t.ohko_with_max_roll for t in threats):
                return True
        return False


class OppProtectRecencyModule(ScoringModule):
    """
    Boosts attacks that target an opponent who used Protect last turn.

    Consecutive Protect almost always fails in Gen 9 (second use in a row has
    a drastically reduced success rate).  When the committed target_slot points
    at a mon that just Protected, the attack is highly unlikely to be wasted —
    reward that targeting reliability with a small multiplier.

    This stacks naturally with DoublingUpModule's existing ``target_protected``
    logic (which already reduces the doubling-up penalty for the same reason).

    Boost schedule:
      Target used a Protect-family move last turn:  ×1.3
    """

    name = "opp_protect_recency"
    PROTECTED_BOOST = 1.3

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        opp_last = state.opp_last_moves
        for action in actions:
            if not action.is_move or action.target_slot is None:
                continue
            ts = action.target_slot
            if ts < len(opp_last) and opp_last[ts] in _PROTECT_MOVES:
                action.weight *= self.PROTECTED_BOOST
                action.reasons.append(
                    f"{self.name}: target used Protect last turn"
                    f" -> x{self.PROTECTED_BOOST}"
                )


def _fake_out_threatened(state: "BattleState") -> bool:
    """
    Return True if any active, non-fainted opponent is a known Fake Out user
    whose last observed move for that slot is unknown (empty string).

    An empty last-move means either:
      (a) the mon just switched into this slot (opp_last_moves reset on switch), or
      (b) turn 1 of the battle before any moves have been seen.

    In both cases Fake Out is available — it can only be used on the mon's
    first turn in play.  Once any move has been recorded for that slot the
    threat is consumed until the next switch-in.
    """
    for slot, opp in enumerate(state.opp_actives):
        if opp is None or opp.fainted:
            continue
        if opp.species not in _FAKE_OUT_USERS:
            continue
        last_move = (state.opp_last_moves[slot]
                     if slot < len(state.opp_last_moves) else "")
        if last_move == "":
            return True
    return False


class FakeOutModule(ScoringModule):
    """
    Adjusts scores when an opponent Fake Out user is active and has not yet
    revealed a move this field-entry (i.e. Fake Out is still available).

    In VGC doubles, Fake Out will hit exactly one of our two active mons —
    flinching it and wasting its turn.  The real cost of being flinched is
    *what the non-Fake-Out partner deals while we are stunned*.  If the partner
    cannot deal meaningful damage, losing one turn's attack is a minor cost and
    the standard Protect/attack split has little value.

    The module therefore only fires when the non-Fake-Out partner can deal
    at least ``PARTNER_THREAT_THRESHOLD`` of this slot's HP on their max
    damage roll.  When the partner is not threatening (e.g. a Trick Room setter
    with weak attacks), the module is skipped entirely and the engine scores
    moves on raw damage merit.

    Scoring adjustments (applied when the partner-threat gate passes):

    * Protect-family moves:  ×3.0  (strong encouragement to shield at least one mon)
    * Non-switch attacks:    ×0.5  (expected-value discount: ~50% chance this slot
                                    is the flinch target, halving the move's value)
    * Switch actions:        no change (switching out sidesteps Fake Out entirely)

    The ×0.5 attack discount is calibrated so that a guaranteed OHKO attack
    sits well below Protect's combined weight from FakeOutModule + ProtectModule.
    Below OHKO level, Protect clearly wins; at OHKO level it is a genuine
    toss-up, which reflects real-game decision complexity.
    """

    name = "fake_out"

    PROTECT_BOOST            = 3.0
    ATTACK_DISCOUNT          = 0.5
    PARTNER_THREAT_THRESHOLD = 0.30  # non-FakeOut partner must threaten ≥30% on max roll

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        if not _fake_out_threatened(state):
            return
        if not self._partner_is_threatening(state, slot):
            return

        # If our partner (slot A) has already committed to an attack, the Fake
        # Out user will almost certainly target them to disrupt that attack —
        # not us.  Slot B can attack freely; penalising it here would be wrong.
        if slot == 1:
            partner = state.my_slot_decisions[0]
            if (partner is not None
                    and partner.move_name is not None
                    and partner.move_name not in _PROTECT_MOVES):
                return

        for action in actions:
            if action.move_name in _PROTECT_MOVES:
                action.weight *= self.PROTECT_BOOST
                action.reasons.append(
                    f"{self.name}: Fake Out threat -> x{self.PROTECT_BOOST}"
                )
            elif not action.is_switch:
                action.weight *= self.ATTACK_DISCOUNT
                action.reasons.append(
                    f"{self.name}: Fake Out may flinch -> x{self.ATTACK_DISCOUNT}"
                )

    def _partner_is_threatening(self, state: "BattleState", slot: int) -> bool:
        """Return True if any non-Fake-Out active opponent can deal
        >= PARTNER_THREAT_THRESHOLD of this slot's HP on their max damage roll.
        """
        mon = state.my_actives[slot] if slot < len(state.my_actives) else None
        if mon is None:
            return True  # Unknown state — be conservative, assume threatening.
        tm    = find_member(mon.species)
        stats = _our_stats(state, slot)
        if tm is None or stats is None:
            return True  # Unknown — assume threatening.

        at_full = (mon.hp >= mon.max_hp) or (mon.hp_is_percentage and mon.hp >= 99)

        for opp_slot, opp in enumerate(state.opp_actives):
            if opp is None or opp.fainted:
                continue
            # Skip the Fake Out user itself.
            last = (state.opp_last_moves[opp_slot]
                    if opp_slot < len(state.opp_last_moves) else "")
            if opp.species in _FAKE_OUT_USERS and last == "":
                continue
            threats = incoming_damage(
                opp_species=opp.species,
                our_species=mon.species,
                our_stats=stats,
                opp_ability=_effective_ability(opp) or "",
                opp_item=opp.item,
                our_ability=_our_ability_for_damage(tm, mon, state.designated_mega),
                our_item=tm.item,
                weather=state.weather,
                our_defender_is_full_hp=at_full,
                opp_boosts=opp.boosts,
                our_boosts=mon.boosts,
            )
            if any(t.hp_fraction_max >= self.PARTNER_THREAT_THRESHOLD for t in threats):
                return True
        return False


# Species that commonly run Trick Room in the Champions format (≥40% TR usage
# in the gen9championsvgc2026regma usage stats).  Both pre-mega and mega forms
# are included so the check works regardless of whether mega-evolution has fired.
_TR_SETTER_SPECIES: frozenset[str] = frozenset({
    "Armarouge",
    "Aromatisse",
    "Audino", "Audino-Mega",
    "Chandelure", "Chandelure-Mega",
    "Chimecho", "Chimecho-Mega",
    "Cofagrigus",
    "Espeon",
    "Farigiraf",
    "Gallade", "Gallade-Mega",
    "Gardevoir", "Gardevoir-Mega",
    "Gengar",
    "Gourgeist-Super",
    "Hatterene",
    "Mimikyu",
    "Mr. Rime",
    "Oranguru",
    "Reuniclus",
    "Runerigus",
    "Sinistcha",
    "Slowbro", "Slowbro-Galar", "Slowbro-Mega",
    "Slowking", "Slowking-Galar",
    "Spiritomb",
    "Trevenant",
    "Wyrdeer",
})

# Species that commonly run Tailwind in the Champions format (≥20% TW usage
# in the gen9championsvgc2026regma usage stats).  Both pre-mega and mega forms
# are included.  Whimsicott and Talonflame are listed here AND filtered out by
# _tw_setter_has_priority because their Tailwind always has +1 priority and
# cannot be denied.
_TAILWIND_SETTER_SPECIES: frozenset[str] = frozenset({
    "Aerodactyl", "Aerodactyl-Mega",
    "Altaria", "Altaria-Mega",
    "Corviknight",
    "Decidueye",
    "Dragonite", "Dragonite-Mega",
    "Gliscor",
    "Hydreigon",
    "Kleavor",
    "Noivern",
    "Pelipper",
    "Pidgeot", "Pidgeot-Mega",
    "Skarmory", "Skarmory-Mega",
    "Talonflame",        # Gale Wings at full HP → filtered by _tw_setter_has_priority
    "Toucannon",
    "Vivillon", "Vivillon-Fancy", "Vivillon-Pokeball",
    "Volcarona",
    "Whimsicott",        # Prankster → filtered by _tw_setter_has_priority
})


def _tw_setter_has_priority(opp: "Pokemon") -> bool:
    """
    Return True when this Tailwind setter's Tailwind move carries +1 priority,
    meaning no attack of ours can land before the effect is established.

    Two sources of priority among Champions-legal Tailwind setters:

    * **Prankster** — gives all Status moves +1 priority.
      Whimsicott virtually always runs Prankster and is assumed to have it
      unconditionally.  Any Pokémon whose ability has been revealed as
      Prankster is also caught.

    * **Gale Wings** (Talonflame) — gives Flying-type moves (including
      Tailwind) +1 priority when at full HP.  If Talonflame's ability is
      still unrevealed it is assumed to be Gale Wings (conservative).
    """
    eff_ab = _effective_ability(opp)
    # Prankster: catches Whimsicott (always), any species with Prankster
    # revealed, and any species whose highest-usage-rate ability is Prankster.
    if eff_ab == "Prankster" or opp.species == "Whimsicott":
        return True
    # Gale Wings: Talonflame at full HP — assumed Gale Wings when not in data
    # (eff_ab may be None for species absent from the usage file).
    if opp.species == "Talonflame":
        at_full = (opp.hp >= opp.max_hp) or (opp.hp_is_percentage and opp.hp >= 100)
        gale    = eff_ab in ("Gale Wings", None)
        if at_full and gale:
            return True
    return False


class SetterPresenceModule(ScoringModule):
    """
    Boosts non-Protect attack moves whenever an opponent Trick Room or
    Tailwind setter is on the field **and the effect is still stoppable**.

    The boost only applies when killing the setter now is actually worth the
    urgency — two situations qualify:

    1. **Effect not yet active** — the setter hasn't established the field
       condition yet; every turn it survives is a chance it sets it up.
    2. **Effect on its last turn** (turns_left == 1) — the setter may try to
       re-set the effect this turn; attacking it now prevents the refresh.

    When the effect is already active with more than one turn remaining there
    is no additional urgency specific to the setter — normal damage scoring
    already handles targeting priority.

    TR and TW conditions are evaluated independently:
      * If TR is active (≥2 turns left) but TW is not up, the TW setter
        boost fires even if TR setter boost does not.
      * TR takes priority when both would fire simultaneously.

    Boost schedule (applied to all non-switch, non-Protect attacks):
      Trick Room setter:  ×2.0 — reversal of speed tiers is critical.
      Tailwind setter:    ×1.5 — +1 speed tier for opponent is serious.

    Protect-family moves and switch actions are not affected.
    """

    name = "setter_presence"

    TR_BOOST = 2.0
    TW_BOOST = 1.5

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        active_opps = [o for o in state.opp_actives if o is not None and not o.fainted]
        if not active_opps:
            return

        # TR setter boost: TR must be stoppable (not active, or last turn for
        # re-set prevention) AND opp Tailwind must not already be up — no point
        # urgently targeting a TR setter while TW is already running.
        tr_relevant = (
            (not state.trick_room or state.trick_room_turns_left == 1)
            and not state.opp_tailwind
        )
        tr_setter_present = any(o.species in _TR_SETTER_SPECIES for o in active_opps)

        # TW setter boost: TW must be stoppable AND TR must not already be up —
        # no point urgently targeting a TW setter while TR is already running.
        tw_relevant = (
            (not state.opp_tailwind or state.opp_tailwind_turns_left == 1)
            and not state.trick_room
        )
        tw_setter_present = any(o.species in _TAILWIND_SETTER_SPECIES for o in active_opps)

        if tr_setter_present and tr_relevant:
            factor = self.TR_BOOST
            if state.trick_room:
                label = "TR setter on field (TR last turn, re-set risk)"
            else:
                label = "TR setter on field (TR not active)"
        elif tw_setter_present and tw_relevant:
            factor = self.TW_BOOST
            if state.opp_tailwind:
                label = "TW setter on field (TW last turn, re-set risk)"
            else:
                label = "TW setter on field (TW not active)"
        else:
            return

        for action in actions:
            if action.is_switch or action.move_name in _PROTECT_MOVES:
                continue
            action.weight *= factor
            action.reasons.append(f"{self.name}: {label} -> x{factor}")


class FieldSetterDisruptionModule(ScoringModule):
    """
    Boosts attacks that can *deny* an opponent field-effect setter — i.e.
    knock it out before it gets the effect up this turn.

    A denial is only possible when ALL of the following hold:

    1. **Guaranteed OHKO** — the move's minimum damage roll exceeds the
       setter's current HP.  A non-lethal hit still lets the setter move
       and establish the effect.

    2. **We outspeed the setter** (``will_outspeed`` > 0.5) — our attack
       must land before the setter's turn.

    3. **No priority ability** — some setters use Tailwind with +1 priority
       and will ALWAYS act before us regardless of Speed:

       * **Prankster** (Whimsicott, and any Pokémon with Prankster revealed):
         Status moves gain +1 priority → Tailwind cannot be denied.
       * **Gale Wings** (Talonflame at full HP, ability unknown assumed to be
         Gale Wings): Flying-type moves gain +1 priority → Tailwind cannot
         be denied until Talonflame takes damage.

    Disruption factors (applied when denial is confirmed):
      Trick Room setter: ×2.0 — reversing the speed tier is high priority.
      Tailwind setter:   ×1.5 — doubling speed for 4 turns is meaningful.

    For actions already targeting a deniable setter, the factor is applied
    directly on top of the existing score.  For actions targeting a different
    opponent, the module computes a fresh deny-score (DamageOutput × ThreatElim
    × factor) and redirects the action if that score exceeds the current
    action weight.  TR setters are evaluated first.
    """

    name = "field_setter"

    TR_DISRUPTION_FACTOR       = 2.0
    TAILWIND_DISRUPTION_FACTOR = 1.5

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        mon = state.my_actives[slot] if slot < len(state.my_actives) else None
        if mon is None:
            return
        tm    = find_member(mon.species)
        stats = _our_stats(state, slot)
        if tm is None or stats is None:
            return

        ally_faints = sum(1 for p in state.my_team if p.fainted)

        # Build the list of (opp_slot, factor, label) setters that we can
        # plausibly deny: effect not yet active, no priority ability, and we
        # outspeed the setter.  TR setters come first so redirects prefer
        # denying TR over Tailwind.
        deniable: list[tuple[int, float, str]] = []
        ours_cbt = _our_combatant(state, slot)

        if not state.trick_room:
            for opp_slot, opp in enumerate(state.opp_actives):
                if opp is None or opp.fainted:
                    continue
                if opp.species not in _TR_SETTER_SPECIES and "Trick Room" not in opp.moves:
                    continue
                # If the (assumed or revealed) ability is Prankster, TR has
                # +1 priority and cannot be denied.
                if _effective_ability(opp) == "Prankster":
                    continue
                # Speed check: we must outspeed to attack before they set TR.
                if ours_cbt is None:
                    continue
                setter_cbt = _opp_combatant(state, opp_slot)
                if setter_cbt is None or will_outspeed(ours_cbt, setter_cbt, trick_room=state.trick_room) <= 0.5:
                    continue
                deniable.append((opp_slot, self.TR_DISRUPTION_FACTOR, "TR setter"))

        if not state.opp_tailwind:
            listed = {s for s, _, _ in deniable}
            for opp_slot, opp in enumerate(state.opp_actives):
                if opp_slot in listed or opp is None or opp.fainted:
                    continue
                if opp.species not in _TAILWIND_SETTER_SPECIES and "Tailwind" not in opp.moves:
                    continue
                # Prankster / Gale Wings → Tailwind has +1 priority → undeniable.
                if _tw_setter_has_priority(opp):
                    continue
                # Speed check: we must outspeed to attack before they set TW.
                if ours_cbt is None:
                    continue
                setter_cbt = _opp_combatant(state, opp_slot)
                if setter_cbt is None or will_outspeed(ours_cbt, setter_cbt, trick_room=state.trick_room) <= 0.5:
                    continue
                deniable.append((opp_slot, self.TAILWIND_DISRUPTION_FACTOR, "Tailwind setter"))

        if not deniable:
            return

        for action in actions:
            if not action.is_move or action.move_name in _PROTECT_MOVES:
                continue
            for setter_slot, factor, label in deniable:
                opp = state.opp_actives[setter_slot]
                if opp is None:
                    continue

                cur_hp = (
                    opp.hp if not opp.hp_is_percentage and opp.hp > 0 else None
                )
                results = outgoing_damage(
                    our_species=mon.species,
                    our_stats=stats,
                    our_moves=[action.move_name],
                    opp_species=opp.species,
                    our_ability=tm.ability,
                    our_item=tm.item,
                    opp_ability=_effective_ability(opp) or "",
                    opp_item=opp.item,
                    weather=state.weather,
                    ally_faint_count=ally_faints,
                    opp_current_hp=cur_hp,
                    opp_hp_percent=(opp.hp if (opp.hp_is_percentage and 0 < opp.hp < 100) else None),
                    opp_screens=getattr(state, "opp_screens", None),
                    attacker_boosts=mon.boosts,
                    defender_boosts=opp.boosts,
                )
                if not results:
                    continue
                r = results[0]

                # Require a guaranteed OHKO — if the setter survives it will
                # still set up the effect on the same turn.
                if not r.is_ohko:
                    continue

                if action.target_slot == setter_slot:
                    # Already aiming here — apply the denial bonus.
                    action.weight *= factor
                    action.reasons.append(
                        f"{self.name}: deny {opp.species} ({label},"
                        f" guaranteed OHKO) -> x{factor}"
                    )
                    break
                else:
                    # Compute the deny-score and redirect if it beats the
                    # current action weight.
                    deny_score = (1.0 + r.hp_fraction_avg * 2.0) * 5.0 * factor
                    if deny_score > action.weight:
                        action.weight      = deny_score
                        action.target_slot = setter_slot
                        action.reasons = [
                            s for s in action.reasons
                            if not s.startswith(("damage_output:", "threat_elimination:"))
                        ]
                        action.reasons.append(
                            f"{self.name}: redirect to deny {opp.species}"
                            f" ({label}, guaranteed OHKO,"
                            f" score={deny_score:.1f}) -> x{factor}"
                        )
                    break  # one setter per action


class FieldConditionModule(ScoringModule):
    """
    Boosts Protect-family moves to stall out the final turns of opponent
    Tailwind or active Trick Room using an every-other-turn pattern.

    Target pattern (3 turns remaining):
      Turn 3 (turns_left == 3): Protect  → wait out one turn
      Turn 2 (turns_left == 2): Attack   → no bonus, field expires next turn anyway
      Turn 1 (turns_left == 1): Protect  → waste the last active turn

    Triggers when either Tailwind or Trick Room is on turn 1 or turn 3:
    * Last turn          (turns_left == 1): x3.0
    * Third-to-last turn (turns_left == 3): x3.0

    The bonus is applied once regardless of how many conditions qualify —
    TW and TR do not stack with each other.

    x3.0 beats a typical attack score but is weaker than a confirmed OHKO
    (x5.0 from ThreatEliminationModule), so the bot will still finish a kill.

    Note: turns_left counts remaining turns INCLUDING the current one.
    A value of 1 means "this is the last turn the effect is active."
    """

    name = "field_condition"

    STALL_FACTOR = 3.0

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        # Boost Protect on the last turn and the third-to-last turn so the bot
        # naturally Protects → attacks → Protects across the final 3 turns.
        opp_tailwind_stall = (state.opp_tailwind_turns_left in (1, 3))
        trick_room_stall   = (state.trick_room_turns_left   in (1, 3))

        if not (opp_tailwind_stall or trick_room_stall):
            return

        for action in actions:
            if action.move_name not in _PROTECT_MOVES:
                continue

            # Apply once — TW and TR do not stack with each other.
            action.weight *= self.STALL_FACTOR
            if opp_tailwind_stall:
                turn_label = "last" if state.opp_tailwind_turns_left == 1 else "3rd-to-last"
                action.reasons.append(
                    f"{self.name}: {turn_label} turn of opp Tailwind"
                    f" -> x{self.STALL_FACTOR}"
                )
            else:
                turn_label = "last" if state.trick_room_turns_left == 1 else "3rd-to-last"
                action.reasons.append(
                    f"{self.name}: {turn_label} turn of Trick Room"
                    f" -> x{self.STALL_FACTOR}"
                )


# ── Factory ───────────────────────────────────────────────────────────────────

def make_engine() -> DecisionEngine:
    """
    Return a DecisionEngine pre-loaded with all default modules.

    Order: DamageOutput -> ThreatElimination -> IncomingOHKO -> TurnOrder ->
           SetterPresence -> FieldSetterDisruption -> OppProtectRecency ->
           ConsecutiveProtect -> Protect -> FakeOut -> FieldCondition ->
           Switch -> DoublingUp

    Damage runs first so KO multipliers compound on the raw damage signal
    before safety considerations are layered on top.
    IncomingOHKOModule runs at Q3 — "can they OHKO me?" is a fundamental
    threat assessment that should be visible early in the pipeline.
    TurnOrderModule follows so faster attackers are rewarded before
    redirect/disruption bonuses are applied.
    SetterPresenceModule at Q5 raises attack urgency whenever a TR/TW setter
    is present; FieldSetterDisruptionModule at Q6 then handles the special case
    where a guaranteed OHKO is available and redirects if needed.
    ConsecutiveProtectModule runs immediately before ProtectModule so the
    consecutive penalty is visible as its own question in the pipeline.
    FieldConditionModule runs after ProtectModule so its stall bonus stacks
    on top of any existing Protect weight rather than being applied blind.
    """
    return DecisionEngine([
        DamageOutputModule(),             # 1: sets action.target_slot to best opponent
        ThreatEliminationModule(),        # 2: may override target_slot for KO opportunities
        IncomingOHKOModule(),             # 3: boost Protect when opponent can OHKO this slot
        TurnOrderModule(),                # 4: scale attacks by turn-order position
        SetterPresenceModule(),           # 5: boost attacks when TR/TW setter is on field
        FieldSetterDisruptionModule(),    # 6: redirect/boost attacks vs setters (OHKO + outspeed only)
        OppProtectRecencyModule(),        # 7: reward attacking a mon that can't Protect again
        ConsecutiveProtectModule(),       # 8: penalise back-to-back Protect (×0.2)
        ProtectModule(),                  # 9: HP-based Protect bonuses + suppress states
        FakeOutModule(),                  # 10: discount attacks / boost Protect vs fresh Fake Out users
        FieldConditionModule(),           # 11: stall on last turn of opp Tailwind / Trick Room
        SwitchModule(),                   # 12: evaluate switch options
        DoublingUpModule(),               # 13: runs last — reads partner's committed target_slot
    ])
