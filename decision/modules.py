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
from dataclasses import dataclass, field, replace
from typing import Optional, TYPE_CHECKING

from data import (
    move_category as get_move_category,
    get_species as _get_species, base_spe as _base_spe,
    WEATHER_SPEED_ABILITIES as _WEATHER_SPEED_ABILITIES,
    ability_distribution as _ability_distribution,
    item_distribution as _item_distribution,
    assumed_forme as _assumed_forme,
    base_forme as _base_forme,
    mega_stones as _mega_stones,
    mega_forme_for_stone as _mega_forme_for_stone,
    population_move_users as _population_move_users,
    SPEED_BOOST_ITEMS as _SPEED_BOOST_ITEMS,
    note_gap as _note_gap,
)
from team import find_member
from damage import outgoing_damage, incoming_damage
from turn_order import Combatant, will_outspeed, priority_bracket

from decision.engine import (
    Action, ScoringModule, JointAdjuster, DecisionEngine,
    _PROTECT_MOVES, _FAKE_OUT_USERS,
    _protect_is_justified, _is_attack,
)

if TYPE_CHECKING:
    from battle import BattleState

_log = logging.getLogger(__name__)


# ── Internal helpers (used by scoring modules) ────────────────────────────────

def _our_item(mon) -> Optional[str]:
    """The consumption-aware held item for one of *our* Pokemon.

    Single source of truth for reading an own-side item.  ``mon.item`` is the
    authoritative live value — the parser populates it from every ``|request|``
    (display form via ``_normalize_member_ids``) before any decision is made, so
    it is always set at decision time.  A consumed item (``item_consumed``) reads
    as ``None`` so every consumer — speed pipeline, offense damage, switch
    board-value — sees the same belief.  Prefer this over ad-hoc ``mon.item`` /
    ``tm.item`` reads, which disagreed on consumption (the 0.21.0 scarf-speed
    bug class).

    No ``tm`` fallback: it was a v0.6.6 scar from when ``_update_or_add`` wiped
    ``mon.item`` on switch-in with no request rebuild to restore it.  Today the
    per-request ``_rebuild_team`` heals that before the next decision, so the
    fallback is unreachable live (proven by a tripwire across the suite).
    """
    if mon is None or getattr(mon, "item_consumed", False):
        return None
    return mon.item


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
        item=_our_item(mon),
        ability=mon.ability or (tm.ability if tm else None),
        speed_stage=mon.boosts.get("spe", 0),
        tailwind=state.my_tailwind,
        paralyzed=(mon.status == "par"),
        weather=_assumed_weather(state),
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
    weather = _assumed_weather(state)
    inferred_ability = _effective_ability(mon)
    if inferred_ability is None and weather:
        sp_data = _get_species(mon.species)
        if sp_data:
            for ab in sp_data.get("abilities", []):
                if _WEATHER_SPEED_ABILITIES.get(ab) == weather:
                    inferred_ability = ab
                    break
    return Combatant(
        name=_assumed_species(mon), side="opp", slot=opp_slot,
        exact_speed=None,
        item=_opp_item(state, mon), ability=inferred_ability,
        speed_stage=mon.boosts.get("spe", 0),
        tailwind=state.opp_tailwind,
        paralyzed=(mon.status == "par"),
        weather=weather,
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
    species: str,
    designated_mega: Optional[str] = None,
) -> str:
    """Our mon's ACTIVE ability for damage calcs — both offense and defense.

    **Single source of truth**: every our-side ability read that feeds a damage
    calc goes through this, so a mega ability applies symmetrically to our
    *outgoing* and *incoming* damage (e.g. Metagross-Mega's Tough Claws boosts
    the moves it throws, not just the hits it takes).  Prefer this over raw
    ``tm.ability``, which is the *base* ability and silently drops the mega's.

    In VGC, mega evolution occurs at the start of the turn before any moves, so a
    designated- or already-mega mon uses its *mega* ability on the very first
    turn — regardless of whether the client has registered the evolution yet.
    Only ``designated_mega`` (``state.designated_mega``) evolves this battle (a
    second stone holder stays base); an already-evolved form (``species ==
    tm.mega_name``) is always mega.  The mega ability is resolved via
    ``_assumed_ability(tm.mega_name)``; falls back to ``tm.ability`` (base) when
    there is no mega form or the mega species has no sets data.
    """
    is_mega   = species == tm.mega_name
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
    if not dist:
        # No usage sets at all — ability/item/spread inference is flying blind
        # for this species; flag it in the battle log.
        _note_gap("sets", species)
        return None
    return dist[0][0]


# Assume a species' top-usage item only if it's at least this common.  A clear
# plurality (≥25%) is committed to; below that the distribution is too flat to
# pick one item, so we assume None (no item-based effect) rather than guess.
# 25% captures the common Choice Scarf / Focus Sash / type-boost pluralities
# (which otherwise bias us optimistically — "not scarfed", "no Sash"); only the
# flattest distributions fall through to None.
_ASSUMED_ITEM_MIN_PCT = 25.0


def _assumed_item(species: str,
                  ruled_out: "frozenset[str] | set[str]" = frozenset()) -> Optional[str]:
    """Most-likely held item for *species*, given items *ruled_out* by observation.

    Walks the usage list (sorted by usage desc), skipping ruled-out items.  The
    25% confidence bar (`_ASSUMED_ITEM_MIN_PCT`) gates **only the literal top
    item** — the pure-prior case, where a too-flat distribution yields None.
    The moment we've had to skip a higher-usage item (i.e. evidence eliminated
    what we'd otherwise have assumed), we commit to the next-most-likely
    candidate **unconditionally** — observation has narrowed the field, so the
    runner-up is now our best point estimate even below the bar.
    """
    skipped = False
    for name, pct in _item_distribution(species):
        if name in ruled_out:
            skipped = True
            continue
        return name if (skipped or pct >= _ASSUMED_ITEM_MIN_PCT) else None
    return None


def _assumed_species(mon: "Pokemon") -> str:
    """Forme to assume for *mon* in all damage / data inference.

    Resolution order:
      1. Revealed mega (``|detailschange|`` already rewrote ``mon.species``).
      2. Revealed mega *stone* → that stone's mega forme directly: we know it
         will evolve, so commit to the mega's stats now rather than guessing
         (the population rule can land on the base forme for swing species like
         Venusaur).
      3. Revealed non-stone item → it cannot mega → base forme.
      4. No item known → the population-weighted likely forme
         (``assumed_forme``): the usage data files megas as separate entries,
         so a pre-mega "Charizard" is ~99% a stone holder and is modelled as
         Charizard-Mega-Y.

    (``item_consumed`` needs no special case: a consumed item leaves
    ``mon.item is None``, and a mon that popped a berry/Sash was never a
    stone holder — its forme assumption simply stays population-weighted,
    an acceptable approximation.)
    """
    if "-Mega" in mon.species:
        return mon.species
    if mon.item:
        if mon.item in _mega_stones():
            forme = _mega_forme_for_stone(mon.item)
            if forme:
                return forme
        else:
            return mon.species
    return _assumed_forme(mon.species)


def _modeled_forme(mon: "Pokemon") -> str:
    """Canonical species name for **set-membership / identity** checks.

    Infers the forme first (so a pre-mega Lopunny is recognised as the Mega Fake
    Out user it will become), then mega-normalises via ``base_forme`` so the
    species sets only need the base name once.  This is the single funnel every
    name-set lookup goes through — it keeps the mega *inference* while removing
    the per-set base/-Mega duplication that used to drift out of sync.
    """
    return _base_forme(_assumed_species(mon))


def _is_fake_out_user(mon: "Pokemon") -> bool:
    """True if *mon*'s modelled forme is a Fake Out user."""
    return _modeled_forme(mon) in _FAKE_OUT_USERS


def _is_tr_setter(mon: "Pokemon") -> bool:
    """True if *mon*'s modelled forme is a Trick Room setter."""
    return _modeled_forme(mon) in _TR_SETTER_SPECIES


def _is_tw_setter(mon: "Pokemon") -> bool:
    """True if *mon*'s modelled forme is a Tailwind setter."""
    return _modeled_forme(mon) in _TAILWIND_SETTER_SPECIES


# Stance-changing formes: (offensive forme, defensive forme).  Aegislash is
# Blade (140/50) when it attacks and Shield (50/140) when it defends.  We can't
# know which stance it's in on a given turn, so use the safe/simple rule —
# always Shield for the damage it RECEIVES, always Blade for the damage it
# DEALS — keyed off the base name (so a revealed Aegislash-Blade still resolves
# both ways).  Other species pass through unchanged.
_STANCE_FORME = {
    "Aegislash":       ("Aegislash-Blade", "Aegislash"),
    "Aegislash-Blade": ("Aegislash-Blade", "Aegislash"),
}


def _offense_species(mon: "Pokemon") -> str:
    """Assumed species for computing the damage *mon* DEALS (Aegislash → Blade)."""
    sp = _assumed_species(mon)
    return _STANCE_FORME.get(sp, (sp, sp))[0]


def _defense_species(mon: "Pokemon") -> str:
    """Assumed species for computing the damage *mon* RECEIVES (Aegislash → Shield)."""
    sp = _assumed_species(mon)
    return _STANCE_FORME.get(sp, (sp, sp))[1]


def _effective_item(mon: "Pokemon", evidence: "ItemEvidence | None" = None) -> Optional[str]:
    """Item to assume for *mon*, resolving the usage-stats prior against any
    observed *evidence* (``ItemEvidence`` keyed by ident; None = pure prior).

    Resolution order:
      1. ``mon.item`` — held right now (revealed this field stint).
      2. ``evidence.consumed`` — we watched it use up / lose its item (game-scoped).
      3. ``evidence.confirmed`` — revealed in an earlier stint (survives switches).
      4. ``mon.item_consumed`` — field-stint consumed (Sash popped / berry eaten).
      5. usage-stats prior, with ``evidence.ruled_out`` items removed.
    """
    if mon.item:
        return mon.item
    if evidence is not None:
        if evidence.consumed:
            return None
        if evidence.confirmed:
            return evidence.confirmed
    if mon.item_consumed:          # Sash popped / berry eaten / Knocked Off
        return None
    ruled = evidence.ruled_out if evidence is not None else frozenset()
    return _assumed_item(_assumed_species(mon), ruled)


def _item_evidence(state: "BattleState", mon: "Pokemon") -> "ItemEvidence | None":
    """Observed item evidence for opponent *mon* (None if state has none yet)."""
    store = getattr(state, "opp_item_evidence", None)
    if not store or mon is None:
        return None
    return store.get(mon.ident)


def _opp_item(state: "BattleState", mon: "Pokemon") -> Optional[str]:
    """Effective item for an opponent *mon*, resolving the prior against the
    observed evidence on *state*.  The standard opponent-item lookup — prefer
    this over bare ``_effective_item(mon)`` wherever ``state`` is in scope."""
    return _effective_item(mon, _item_evidence(state, mon))


def _effective_ability(mon: "Pokemon") -> Optional[str]:
    """Return the ability to assume for *mon*.

    A revealed ability (``mon.ability``) is normally used directly; otherwise we
    fall back to the highest-usage-rate ability of the *assumed forme*
    (mega-holders are assumed pre-mega, so an unrevealed Charizard is Drought,
    not Solar Power).

    **Mega exception (systematic, no per-species list):** mega-evolution
    *replaces* the base ability (Altaria's Natural Cure/Cloud Nine → Pixilate,
    Charizard's Blaze → Drought, …).  An ability revealed *before* a mon megas
    is therefore stale, so for any assumed ``-Mega`` forme we use the mega
    forme's ability regardless of what was revealed (megas have exactly one).
    """
    species = _assumed_species(mon)
    if "-Mega" in species:
        return _assumed_ability(species) or mon.ability
    if mon.ability is not None:
        return mon.ability
    return _assumed_ability(species)


# Weather-setting abilities → the weather they put up on switch-in / mega-evolve.
_WEATHER_SETTING_ABILITIES = {
    "Drought": "sun", "Drizzle": "rain",
    "Sand Stream": "sand", "Snow Warning": "snow",
}


def _assumed_weather(state: "BattleState") -> Optional[str]:
    """Effective weather for the turn's facts.

    Observed weather always wins.  Otherwise we *assume* the weather an **active**
    weather-setting ability will bring — keyed off the assumed forme via
    ``_effective_ability``, so a pre-mega Charizard (→ Mega-Y → Drought) implies
    sun before its ``|detailschange|`` even arrives.  This drives Weather Ball's
    type/power, the Fire/Water damage modifiers, and weather-speed abilities
    (Chlorophyll/Swift Swim/…) on **both** sides.

    When several active mons would set weather on the *same* turn, entry abilities
    fire fastest-first, so the **slowest** setter writes last and its weather
    sticks (ranked by base Speed — a rough but adequate tiebreak for the rare
    double-setter case; a lone setter needs no tiebreak).
    """
    if state.weather:
        return state.weather
    setters: list[tuple[int, str]] = []
    for actives, ours in ((state.my_actives, True), (state.opp_actives, False)):
        for mon in actives:
            if mon is None or mon.fainted:
                continue
            ability = (mon.ability if ours else _effective_ability(mon)) or ""
            w = _WEATHER_SETTING_ABILITIES.get(ability)
            if w:
                species = mon.species if ours else _assumed_species(mon)
                setters.append((_base_spe(species) or 0, w))
    if not setters:
        return None
    return min(setters, key=lambda t: t[0])[1]   # slowest writes last → its weather wins


# ══════════════════════════════════════════════════════════════════════════════
# Built-in scoring modules
# ══════════════════════════════════════════════════════════════════════════════


class DamageOutputModule(ScoringModule):
    """
    Up-weights moves proportional to the damage they deal.

    For each move action the expected damage fraction (avg damage / opponent HP)
    is computed against every active opponent; the best value across all targets
    is used.

    Weight multiplier (damaging moves): DAMAGE_INTERCEPT + DAMAGE_SLOPE * fraction
    — a single line that floors at 0.5 (a move threatening ~nothing) and passes
    through the old 1+2f curve at 25% damage (both = 1.5).  Below 25% it devalues
    weak moves (switch-prone — a move that does ~nothing loses to a switch but
    still beats sacking into an OHKO); above 25% it climbs past the old curve,
    sharpening "attack with the big move".

    Examples (INTERCEPT=0.5, SLOPE=4.0):
      100% avg damage (OHKO)  ->  x4.5
      50%                     ->  x2.5
      25%                     ->  x1.5   (matches the old 1+2f here)
      12.5%                   ->  x1.0
       5%                     ->  x0.7
       0% (immune / dead)     ->  x0.5   (floor)

    Status moves are left at the x1.0 baseline (they deal no damage by design,
    not by failure) so ProtectValue / SetterUrgency / FakeOut can score them.
    """

    name = "damage_output"

    DAMAGE_INTERCEPT = 0.5   # a damaging move that threatens ~nothing -> x0.5:
                             # below a healthy switch (leave a useless matchup),
                             # above a suicidal one (don't sack into an OHKO)
    DAMAGE_SLOPE     = 3.5   # crosses the old 1+2f curve at ~33% damage

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

        def _frac(move_name: str, opp_slot: int) -> float:
            """Average damage fraction of *move_name* against opponent *opp_slot*."""
            opp = (state.opp_actives[opp_slot]
                   if 0 <= opp_slot < len(state.opp_actives) else None)
            if opp is None or opp.fainted:
                return 0.0
            # Pass the observed current HP so KO thresholds use actual HP, not the
            # typical-spread max HP estimate.  Skip the override when HP is a
            # percentage (opp.hp would then be e.g. 60 meaning "60%", not absolute).
            cur_hp = (opp.hp if (not opp.hp_is_percentage and opp.hp > 0) else None)
            results = outgoing_damage(
                our_species=mon.species, our_stats=stats, our_moves=[move_name],
                opp_species=_defense_species(opp), our_ability=_our_ability_for_damage(tm, mon.species, state.designated_mega), our_item=_our_item(mon),
                opp_ability=_effective_ability(opp) or "", opp_item=_opp_item(state, opp),
                weather=_assumed_weather(state), ally_faint_count=ally_faints, opp_current_hp=cur_hp,
                opp_hp_percent=(opp.hp if (opp.hp_is_percentage and 0 < opp.hp < 100) else None),
                opp_screens=getattr(state, "opp_screens", None),
                attacker_boosts=mon.boosts, defender_boosts=opp.boosts,
                attacker_hp_fraction=mon.hp_fraction,
                attacker_status=mon.status or "",
                flash_fire_active=mon.flash_fire_active,
            )
            return results[0].hp_fraction_avg if results else 0.0

        live = [i for i, o in enumerate(state.opp_actives)
                if o is not None and not o.fainted]

        for action in actions:
            if not action.is_move:
                continue
            # Status moves keep the x1.0 baseline — they deal no damage by
            # design, not by failure — so the modules that value them
            # (ProtectValue / SetterUrgency / FakeOut) score from there.
            if get_move_category(action.move_name) == "Status":
                continue
            ts = action.target_slot
            if ts is not None:
                # Fixed-target candidate — score against its own target only.
                fraction = _frac(action.move_name, ts)
            else:
                # Spread move (no chosen target): credit the best foe it can hit.
                fraction = max((_frac(action.move_name, i) for i in live), default=0.0)

            # Single line: floors at DAMAGE_INTERCEPT (a move threatening
            # ~nothing — immune / fully resisted / a dead Choice-locked move —
            # loses to a healthy switch but still beats sacking into an OHKO)
            # and matches the old 1+2f curve at 25% damage.
            factor = self.DAMAGE_INTERCEPT + self.DAMAGE_SLOPE * fraction
            action.weight *= factor
            action.reasons.append(
                f"{self.name}: {fraction:.0%} HP -> x{factor:.2f}"
            )


class ThreatEliminationModule(ScoringModule):
    """
    Large bonus for moves that guarantee a KO this turn.

    Applied on top of DamageOutputModule's score:

      Guaranteed OHKO (min roll >= defender HP)  ->  x5.0

    Only fires when the KO is certain on every damage roll.  Partial KO
    signals (max-roll OHKO, 2HKO) are intentionally excluded — damage
    output alone already rewards high-damage moves via DamageOutputModule.

    Two rows, both answered from the precomputed :class:`TurnContext`:

    * *"Can I guarantee a kill?"* — any move that ``ctx`` flags as a guaranteed
      OHKO on its target gets ×5.0.
    * *"Will I die before I act?"* — if ``ctx.is_doomed(slot)`` (a faster/priority
      opponent min-roll-OHKOs us first, not removed before it acts) the kill is
      undeliverable: the same candidate gets ×0.2, cancelling the credit
      (5.0 × 0.2 = 1.0).  Non-kill attacks are untouched.
    """

    name = "threat_elimination"

    GUARANTEED_OHKO = 5.0
    DOOMED_CANCEL   = 0.2   # cancels the kill credit (5.0 × 0.2 = 1.0)

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        mon = state.my_actives[slot] if slot < len(state.my_actives) else None
        if mon is None:
            return
        if not any(o is not None for o in state.opp_actives):
            return

        ctx = _ensure_turn_ctx(state)
        doomed = ctx.is_doomed(slot)

        live = [i for i, o in enumerate(state.opp_actives)
                if o is not None and not o.fainted]

        for action in actions:
            if not action.is_move:
                continue
            # A fixed-target candidate checks only its own target; a spread/status
            # move (target_slot=None) counts if it OHKOs any live foe.
            targets = [action.target_slot] if action.target_slot is not None else live
            for opp_slot in targets:
                opp = (state.opp_actives[opp_slot]
                       if 0 <= opp_slot < len(state.opp_actives) else None)
                if opp is None or opp.fainted:
                    continue
                if ctx.guarantees_ohko(slot, action.move_name, opp_slot):
                    action.weight *= self.GUARANTEED_OHKO
                    action.reasons.append(
                        f"{self.name}: guaranteed OHKO on {opp.species}"
                        f" -> x{self.GUARANTEED_OHKO}"
                    )
                    if doomed:
                        action.weight *= self.DOOMED_CANCEL
                        action.reasons.append(
                            f"{self.name}: KO'd before acting — undeliverable"
                            f" kill -> x{self.DOOMED_CANCEL}"
                        )
                    break   # first guaranteed-OHKO target


class ProtectValueModule(ScoringModule):
    """
    Scores Protect-family moves when a connecting OHKO threat is present.

    Four multiplicative rows, applied only when `ctx.is_threatened(slot)`:

    1. ×2.5 — a connecting OHKO exists (basic incoming-threat boost).
       reason: ``"incoming_ohko: OHKO threat -> x2.5"``
    2. ×3.0 — a live partner can guarantee an OHKO on one of the threats
       (Protecting resolves the board: we survive while the partner removes
       a threat this same turn).
       reason: ``"protect: unavoidable OHKO incoming + partner clears a threat -> x3.0"``
    3. ×0.4 — 1v1 endgame (cancels the ×2.5; Protect only delays).
    4. ×0.4 — 2v1 numerical advantage (cancels the ×2.5; Protecting can't
       improve the outcome).  Rows 3 and 4 are mutually exclusive.

    The two reason prefixes (``"incoming_ohko:"`` and ``"protect:"``) are
    consumed by ``_protect_is_justified`` in the phase-2 CoordinationAdjuster
    to distinguish justified Protects from gratuitous ones — keep them exact.
    """

    name = "protect"

    THREATENED_FACTOR    = 2.5
    PARTNER_KO_FACTOR    = 3.0
    ENDGAME_1V1_FACTOR   = 0.4
    ADVANTAGE_2V1_FACTOR = 0.4

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        ctx = _ensure_turn_ctx(state)
        if not ctx.is_threatened(slot):
            return

        is_1v1_endgame      = ctx.is_1v1_endgame(slot)
        numerical_advantage = ctx.has_numerical_advantage()

        ohko_threats = [(os, state.opp_actives[os]) for os in ctx.ohko_threats(slot)]
        partner_slots = [
            i for i, p in enumerate(state.my_actives)
            if i != slot and p is not None and not p.fainted
        ]
        partner_clears = bool(ohko_threats) and any(
            _partner_can_ohko(state, ps, opp)
            for ps in partner_slots
            for (_, opp) in ohko_threats
        )

        for action in actions:
            if action.move_name not in _PROTECT_MOVES:
                continue
            action.weight *= self.THREATENED_FACTOR
            action.reasons.append(
                f"incoming_ohko: OHKO threat -> x{self.THREATENED_FACTOR}"
            )
            if partner_clears:
                action.weight *= self.PARTNER_KO_FACTOR
                action.reasons.append(
                    f"protect: unavoidable OHKO incoming + partner clears a threat"
                    f" -> x{self.PARTNER_KO_FACTOR}"
                )
            if is_1v1_endgame:
                action.weight *= self.ENDGAME_1V1_FACTOR
                action.reasons.append(
                    f"incoming_ohko: 1v1 endgame, Protect only delays"
                    f" -> x{self.ENDGAME_1V1_FACTOR}"
                )
            if numerical_advantage:
                action.weight *= self.ADVANTAGE_2V1_FACTOR
                action.reasons.append(
                    f"incoming_ohko: 2v1 advantage, Protect can't improve the outcome"
                    f" -> x{self.ADVANTAGE_2V1_FACTOR}"
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
    ctx: Optional["TurnContext"] = None,
) -> bool:
    """Return True if any available partner move guarantees an OHKO on *opp*.

    A pure read of the :class:`TurnContext` OHKO matrix — the single damage
    computation lives in :func:`build_turn_context`, so this always agrees with
    ThreatEliminationModule and the setter-denial check.  *ctx* is passed
    explicitly while the context is being built; otherwise the cached turn
    context is used.
    """
    ctx = ctx if ctx is not None else _ensure_turn_ctx(state)
    opp_slot = next(
        (i for i, o in enumerate(state.opp_actives) if o is opp), None
    )
    if opp_slot is None:
        return False
    return any(
        s == partner_slot and os == opp_slot for (s, _m, os) in ctx.ohko
    )


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
    ctx: Optional["TurnContext"] = None,
) -> bool:
    """Return True if *opp* will be KO'd before it can act this turn.

    This holds when one of our active Pokémon both (a) outspeeds *opp* and
    (b) has a move that guarantees an OHKO on it (read from the
    :class:`TurnContext` OHKO matrix).  In that case *opp* faints before
    landing its hit, so Protecting in order to survive that hit buys nothing —
    we (or our partner) should simply attack.

    Exception — **priority attackers** (see ``_opp_has_attacking_priority``):
    a Gale Wings Talonflame's Brave Bird strikes before our normal-priority KO
    move, so it gets its hit off even when we are faster.  Such an attacker is
    never treated as neutralised.  Other move-based priority (Prankster status,
    Fake Out, Sucker Punch, etc.) is still not modelled.

    Without an explicit *ctx* this reads the cached per-turn fact; *ctx* is
    passed explicitly only while :func:`build_turn_context` computes that fact.
    """
    if ctx is None:
        return _ensure_turn_ctx(state).neutralized.get(opp_slot, False)
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
        if _partner_can_ohko(state, our_slot, opp, ctx):
            return True
    return False


def _ko_before_acting(
    state: "BattleState", slot: int, ctx: Optional["TurnContext"] = None,
) -> bool:
    """Return True if our slot will (very likely) be KO'd before it can act.

    Offensive mirror of :func:`_opp_neutralized_before_acting`: an active
    opponent (a) moves before us — it outspeeds us, or has move-based attacking
    priority — (b) **guarantees** an OHKO on us (min roll — if we might survive,
    attacking for the kill is a legitimate gamble), and (c) is *not* itself
    removed before it acts.  The damage fact comes from the
    :class:`TurnContext` ``incoming_certain`` matrix.

    When this holds, any "guaranteed OHKO" we line up is not actually
    deliverable — we faint first — so ThreatEliminationModule must not credit
    the kill.

    Without an explicit *ctx* this reads the cached per-turn fact; *ctx* is
    passed explicitly only while :func:`build_turn_context` computes that fact.
    """
    if ctx is None:
        return _ensure_turn_ctx(state).is_doomed(slot)
    mon = state.my_actives[slot] if slot < len(state.my_actives) else None
    if mon is None:
        return False
    our_c = _our_combatant(state, slot)
    if our_c is None:
        return False

    for opp_slot in ctx.incoming_certain.get(slot, []):
        opp = (state.opp_actives[opp_slot]
               if opp_slot < len(state.opp_actives) else None)
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
        if ctx.neutralized.get(opp_slot, False):
            continue
        return True
    return False


# ── Turn context (precomputed facts) ──────────────────────────────────────────

@dataclass
class TurnContext:
    """Board facts computed once per turn, so modules read *facts* instead of
    re-deriving them or sniffing each other's reason strings.

    * ``doomed[slot]`` — this slot will be KO'd before it can act
      (:func:`_ko_before_acting`).  Gates the guaranteed-kill credit.
    * ``ohko`` — set of ``(slot, move_name, opp_slot)`` triples that are a
      *guaranteed* OHKO (every damage roll ≥ the target's HP).  The single source
      of truth for "is this a confirmed kill?", read by ThreatEliminationModule,
      the setter-denial check, :func:`_partner_can_ohko` and the
      DoublingAdjuster.
    * ``incoming_ohko[slot]`` — opponent slots whose **max** damage roll OHKOs
      our *slot*.  Single source of truth for "can they kill me this turn?",
      read by IncomingOHKOModule, ProtectModule, SwitchModule and the
      DoublingAdjuster.
    * ``incoming_certain[slot]`` — the stricter min-roll subset: opponents whose
      *every* roll OHKOs us.  Feeds the doomed computation.
    * ``neutralized[opp_slot]`` — that opponent is KO'd before it can act this
      turn (:func:`_opp_neutralized_before_acting`), so its threats never land.
    * ``fake_out[slot]`` — a fresh Fake Out user threatens the field *and* its
      non-Fake-Out partner meaningfully threatens our *slot* — the condition
      under which FakeOutModule adjusts that slot (and the FakeOutAdjuster
      knows the multiplier it applied).
    * ``bench_alive`` / ``alive_slots`` / ``opp_alive`` — board-state counts
      behind the 1v1-endgame and 2v1-advantage rows.
    """
    doomed: dict[int, bool] = field(default_factory=dict)
    ohko:   set = field(default_factory=set)
    incoming_ohko:    dict[int, list[int]] = field(default_factory=dict)
    incoming_certain: dict[int, list[int]] = field(default_factory=dict)
    neutralized:   dict[int, bool] = field(default_factory=dict)
    fake_out:      dict[int, bool] = field(default_factory=dict)
    fake_out_live: bool = False   # a fresh Fake Out user is on the field
    bench_alive: int = 0
    alive_slots: frozenset = frozenset()   # our active slots that are alive
    opp_alive:   int = 0

    def is_doomed(self, slot: int) -> bool:
        return self.doomed.get(slot, False)

    def guarantees_ohko(self, slot: int, move_name: str, opp_slot: int) -> bool:
        return (slot, move_name, opp_slot) in self.ohko

    def ohko_threats(self, slot: int) -> list[int]:
        """Opponent slots whose max roll OHKOs *slot* (neutralized ones included)."""
        return self.incoming_ohko.get(slot, [])

    def connecting_threats(self, slot: int) -> list[int]:
        """The subset of :meth:`ohko_threats` not KO'd before they act."""
        return [os for os in self.ohko_threats(slot)
                if not self.neutralized.get(os, False)]

    def is_threatened(self, slot: int) -> bool:
        """True when at least one OHKO threat on *slot* actually connects."""
        return bool(self.connecting_threats(slot))

    def fake_out_fired(self, slot: int) -> bool:
        """True when the Fake-Out adjustment applies to *slot* this turn.

        A slot with no computed entry (unknown mon) falls back to "is a fresh
        Fake Out user on the field at all" — conservative, like the partner-
        threat check it feeds."""
        return self.fake_out.get(slot, self.fake_out_live)

    def is_1v1_endgame(self, slot: int) -> bool:
        """Our last mon vs their last mon (no bench, no partner, one foe)."""
        partner_alive = any(s != slot for s in self.alive_slots)
        return self.bench_alive == 0 and not partner_alive and self.opp_alive == 1

    def has_numerical_advantage(self) -> bool:
        """We have strictly more live actives than the opponent (2v1)."""
        return len(self.alive_slots) > self.opp_alive > 0


def _observe_speed_from_history(state: "BattleState") -> None:
    """Refute a Choice Scarf assumption from observed move order.

    Reads the most recently completed turn's move events: if one of our actives
    (exact speed) moved before an opponent in the **same priority bracket** and
    not under Trick Room, and even the *slowest scarfed* spread of that opponent
    would still have outsped us (``will_outspeed`` of us vs a forced-Scarf copy
    == 0), then the opponent cannot be holding Choice Scarf — we observed it move
    slower than that.  Rules Choice Scarf out on its evidence record.

    Heuristic and deliberately conservative: it only fires on an undistorted
    same-bracket comparison, and never wrongly clears Scarf (it requires that no
    scarfed spread could have been outsped).  Idempotent (set union)."""
    log = getattr(state, "events_log", None)
    if not log or state.trick_room:
        return
    events = log.get(max(log)) or []
    ours = [e for e in events if e.get("sd") == "us"]
    opps = [e for e in events if e.get("sd") == "opp"]
    if not ours or not opps:
        return
    for oe in opps:
        opp_slot = next((i for i, m in enumerate(state.opp_actives)
                         if m is not None and not m.fainted
                         and _base_forme(m.species) == _base_forme(oe.get("a"))), None)
        if opp_slot is None:
            continue
        opp_mon = state.opp_actives[opp_slot]
        ev = state.opp_item_evidence.get(opp_mon.ident)
        if opp_mon.item or (ev and (ev.confirmed or ev.consumed)):
            continue                       # item already known — nothing to infer
        if ev and _SPEED_BOOST_ITEMS <= ev.ruled_out:
            continue                       # already ruled out
        opp_prio = priority_bracket(oe.get("mv") or "")
        yc = _opp_combatant(state, opp_slot)
        if yc is None:
            continue
        yc_scarf = replace(yc, item="Choice Scarf")
        for ue in ours:
            if ue.get("o", 0) >= oe.get("o", 0):
                continue                   # our mon did not move first
            if priority_bracket(ue.get("mv") or "") != opp_prio:
                continue                   # different bracket → order not by speed
            our_slot = next((i for i, m in enumerate(state.my_actives)
                             if m is not None and not m.fainted
                             and _base_forme(m.species) == _base_forme(ue.get("a"))), None)
            if our_slot is None:
                continue
            xc = _our_combatant(state, our_slot)
            if xc is None or xc.exact_speed is None:
                continue
            if will_outspeed(xc, yc_scarf, trick_room=False) == 0.0:
                state.evidence_for(opp_mon.ident).ruled_out |= _SPEED_BOOST_ITEMS
                break


def build_turn_context(state: "BattleState") -> TurnContext:
    """Compute the per-turn fact context once — the **only** place the engine
    runs damage calculations for yes/no facts.

    Build order matters: the OHKO matrix first (pure damage), then
    ``neutralized`` (matrix + speed), then the incoming-threat matrices (pure
    damage), then ``doomed`` (incoming + neutralized + speed).  Each later fact
    is computed by its public helper with this partially-built context passed
    explicitly, so tests can still patch the helper functions as seams.

    The OHKO matrix mirrors :class:`ThreatEliminationModule`'s damage call exactly
    (same species/stats/ability/item/weather/boosts/screens/HP-percent), so the
    fact and the kill credit it gates always agree.  Disabled moves are excluded
    (matching ``_build_actions``), so a Disabled kill move never counts as a
    partner-clear or a neutralizer.
    """
    # Refresh observation-driven item evidence (e.g. refute Choice Scarf from
    # observed turn order) before any fact uses _effective_item this turn.
    _observe_speed_from_history(state)

    ctx = TurnContext()
    ally_faints = sum(1 for p in state.my_team if p is not None and p.fainted)
    opp_faints  = sum(1 for p in state.opp_team if p is not None and p.fainted)

    # ── Board-state counts (1v1 endgame / 2v1 advantage rows) ─────────────────
    ctx.bench_alive = len(state.available_switches)
    ctx.alive_slots = frozenset(
        i for i, p in enumerate(state.my_actives)
        if p is not None and not p.fainted
    )
    ctx.opp_alive = sum(
        1 for o in state.opp_actives if o is not None and not o.fainted
    )

    disabled_list = getattr(state, "my_disabled_moves", [])

    # ── 1. Guaranteed-OHKO matrix (the one outgoing_damage fact loop) ─────────
    for slot in ctx.alive_slots:
        mon   = state.my_actives[slot]
        tm    = find_member(mon.species)
        stats = _our_stats(state, slot)
        if tm is None or stats is None:
            # Our own mon missing from team data: the whole slot is skipped —
            # no kill facts, no threat facts.  Flag it in the battle log.
            _note_gap("team_member", mon.species)
            continue
        disabled = disabled_list[slot] if slot < len(disabled_list) else None
        moves = [
            md.get("move", "")
            for md in (state.moves_per_slot[slot]
                       if slot < len(state.moves_per_slot) else [])
            if md.get("move") and not md.get("disabled", False)
            and md.get("move", "") != disabled
        ]
        for move in moves:
            for opp_slot, opp in enumerate(state.opp_actives):
                if opp is None or opp.fainted:
                    continue
                cur_hp = (opp.hp if (not opp.hp_is_percentage and opp.hp > 0) else None)
                opp_at_full = (opp.hp >= opp.max_hp) or (opp.hp_is_percentage and opp.hp >= 100)
                results = outgoing_damage(
                    our_species=mon.species, our_stats=stats, our_moves=[move],
                    opp_species=_defense_species(opp), our_ability=_our_ability_for_damage(tm, mon.species, state.designated_mega), our_item=_our_item(mon),
                    opp_ability=_effective_ability(opp) or "", opp_item=_opp_item(state, opp),
                    weather=_assumed_weather(state), ally_faint_count=ally_faints, opp_current_hp=cur_hp,
                    opp_hp_percent=(opp.hp if (opp.hp_is_percentage and 0 < opp.hp < 100) else None),
                    opp_is_full_hp=opp_at_full,
                    opp_screens=getattr(state, "opp_screens", None),
                    attacker_boosts=mon.boosts, defender_boosts=opp.boosts,
                    attacker_hp_fraction=mon.hp_fraction,
                    attacker_status=mon.status or "",
                    flash_fire_active=mon.flash_fire_active,
                )
                if results and results[0].is_ohko:
                    ctx.ohko.add((slot, move, opp_slot))

    # ── 2. Opponents removed before they act (matrix + speed) ─────────────────
    for opp_slot, opp in enumerate(state.opp_actives):
        if opp is None or opp.fainted:
            continue
        ctx.neutralized[opp_slot] = _opp_neutralized_before_acting(
            state, opp_slot, opp, ctx)

    # ── 3. Incoming threats (the one incoming_damage fact loop) ───────────────
    fo_live = _fake_out_threatened(state)
    ctx.fake_out_live = fo_live
    _pred: list = []   # predicted worst-case incoming per (opp -> our mon)
    for slot in ctx.alive_slots:
        mon   = state.my_actives[slot]
        tm    = find_member(mon.species)
        stats = _our_stats(state, slot)
        ctx.fake_out[slot] = fo_live
        if tm is None or stats is None:
            _note_gap("team_member", mon.species)
            continue
        at_full = (mon.hp >= mon.max_hp) or (mon.hp_is_percentage and mon.hp >= 99)
        # Consumption-aware defender item: a popped Chople/Sitrus must not keep
        # halving incoming damage in the facts.  Falls back to the team.txt item
        # when the battle state hasn't tracked one (tests, fresh leads).
        our_item = _our_item(mon)
        max_roll_kills: list[int] = []
        min_roll_kills: list[int] = []
        for opp_slot, opp in enumerate(state.opp_actives):
            if opp is None or opp.fainted:
                continue
            threats = incoming_damage(
                opp_species=_offense_species(opp),
                our_species=mon.species,
                our_stats=stats,
                opp_ability=_effective_ability(opp) or "",
                opp_item=_opp_item(state, opp),
                our_ability=_our_ability_for_damage(tm, mon.species, state.designated_mega),
                our_item=our_item,
                weather=_assumed_weather(state),
                our_defender_is_full_hp=at_full,
                opp_boosts=opp.boosts,
                our_boosts=mon.boosts,
                opp_hp_fraction=opp.hp_fraction,
                opp_status=opp.status or "",
                opp_ally_faint_count=opp_faints,
                opp_times_hit=getattr(opp, "times_hit", 0),
                opp_flash_fire_active=opp.flash_fire_active,
            )
            if any(t.ohko_with_max_roll for t in threats):
                max_roll_kills.append(opp_slot)
            if any(t.is_ohko for t in threats):
                min_roll_kills.append(opp_slot)
            # Record predicted incoming damage per ASSESSED move (expected,
            # non-crit) for offline defensive-accuracy analysis.  Storing the
            # whole assessed movepool — not just the scariest — lets the report
            # tell a genuine model mis-calc (a move we assessed but under-rated)
            # from an off-meta tech move we never considered.
            if threats:
                # Key by the forme we actually assessed (``_offense_species``),
                # not the raw on-field name — so the prediction log is
                # self-consistent and matches the (post-mega) actual-event actor
                # under ``base_forme`` normalisation at analysis time.
                _pred.append({"a": _offense_species(opp), "df": mon.species,
                              "mvs": {t.move: round(t.hp_fraction_avg, 3)
                                      for t in threats}})
        ctx.incoming_ohko[slot]    = max_roll_kills
        ctx.incoming_certain[slot] = min_roll_kills
    # Persist the predicted-incoming snapshot for this turn (defensive accuracy).
    state.predicted_incoming_log[state.turn] = _pred

    # ── 4. Doomed (incoming_certain + neutralized + speed) ────────────────────
    for slot in ctx.alive_slots:
        ctx.doomed[slot] = _ko_before_acting(state, slot, ctx)

    return ctx


def _ensure_turn_ctx(state: "BattleState") -> TurnContext:
    """Return the turn's :class:`TurnContext`, building and caching it on *state*
    once per turn (board facts don't change between phase-1 scoring and the
    phase-2 coordinate pass within a turn)."""
    if (getattr(state, "_turn_ctx", None) is None
            or getattr(state, "_turn_ctx_turn", None) != getattr(state, "turn", None)):
        state._turn_ctx = build_turn_context(state)
        state._turn_ctx_turn = getattr(state, "turn", None)
    return state._turn_ctx


class SwitchModule(ScoringModule):
    """
    Scores switches by the value of the resulting board — a cheap 1-ply
    lookahead — so a switch competes on the same scale as an attack instead of a
    type-matchup multiplier capped at ×4.0.

    Four multiplicative rows:

      1. TEMPO_FACTOR (0.8) — forfeiting this turn + conceding a free hit.
         Softened from 0.6 → 0.8 in 0.8.3: the old tax made the bot too
         reluctant to pivot out of a low-value position (it would grind a 15%
         attack into walls rather than switch), so the cost is now a gentle
         nudge rather than a near-veto.
      2. (1 + g) where g = max(0, bench_offense − cur_offense) — offense gain.
      3. ESCAPE_FACTOR (4.0) — escaping a connecting OHKO into a surviving switch-in.
      4. DANGER_FACTOR (0.3) — the switch-in is itself OHKO'd by an active opponent.

    A switch the partner already committed to (same bench target) is vetoed (×0).

    Net effect: a switch wins when the incoming mon is meaningfully better than
    staying — escaping a KO into a healthy threat, or pivoting a walled /
    Struggling mon.
    """

    name = "switch_eval"

    TEMPO_FACTOR  = 0.8   # switching forfeits this turn + concedes a free hit
    ESCAPE_FACTOR = 4.0   # escaping a connecting OHKO into a surviving switch-in
    DANGER_FACTOR = 0.3   # switching into a mon that is itself OHKO'd

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        mon = state.my_actives[slot] if slot < len(state.my_actives) else None
        if mon is None:
            return

        # Cross-slot coordination (two slots switching to the *same* bench mon)
        # is no longer handled here — it is resolved jointly by
        # DecisionEngine.coordinate (the switch-same-mon veto), which sees both
        # slots' candidate lists at once rather than relying on scoring order.
        live_switches = [a for a in actions if a.is_switch]
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
            _our_ability_for_damage(tm, mon.species, state.designated_mega) if tm else None,
            _our_item(mon), cur_moves,
        )

        # Is the current mon OHKO-threatened by a threat that actually connects?
        # Precomputed once per turn in TurnContext (shared with IncomingOHKO /
        # Protect).
        cur_threatened = _ensure_turn_ctx(state).is_threatened(slot)

        # ── Score each live switch by resulting board value ───────────────────
        for action in live_switches:
            bench_tm = find_member(action.switch_target)
            if bench_tm is None or not getattr(bench_tm, "stats", None):
                continue  # unknown bench mon — leave neutral (×1.0)

            # Live bench item, consumption-aware: a berry eaten during an
            # earlier field stint must not keep shielding (or arming) the
            # switch-in — same rule as the actives' incoming fact loop.
            bench_mon = next(
                (p for p in state.available_switches
                 if p is not None and p.species == action.switch_target), None)
            bench_item = _our_item(bench_mon)

            bench_moves = [m for m in bench_tm.moves if m not in _PROTECT_MOVES]
            offense  = self._best_offense(
                state, action.switch_target, bench_tm.stats,
                bench_tm.ability, bench_item, bench_moves,
            )
            survives = self._switch_in_survives(
                state, action.switch_target, bench_tm, bench_item)

            g      = max(0.0, offense - cur_offense)
            escape = cur_threatened and survives

            action.weight *= self.TEMPO_FACTOR
            action.reasons.append(
                f"{self.name}: tempo -> x{self.TEMPO_FACTOR}"
            )
            action.weight *= (1.0 + g)
            action.reasons.append(
                f"{self.name}: +{g:.0%} offense gain -> x{1.0 + g:.2f}"
            )
            if escape:
                action.weight *= self.ESCAPE_FACTOR
                action.reasons.append(
                    f"{self.name}: escapes OHKO -> x{self.ESCAPE_FACTOR}"
                )
            if not survives:
                action.weight *= self.DANGER_FACTOR
                action.reasons.append(
                    f"{self.name}: switch-in OHKO'd -> x{self.DANGER_FACTOR}"
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
                    opp_species=_defense_species(opp), opp_ability=_effective_ability(opp) or "",
                    opp_item=_opp_item(state, opp), weather=_assumed_weather(state),
                    ally_faint_count=ally_faints, opp_current_hp=cur_hp,
                )
                if results:
                    best = max(best, results[0].hp_fraction_avg)
        return best

    def _switch_in_survives(
        self, state: "BattleState", species: str, bench_tm,
        bench_item: Optional[str],
    ) -> bool:
        """True if no active opponent OHKOs the switch-in on its max roll.

        *bench_item* is the consumption-aware item (None once consumed), not
        the static team.txt item — a spent Chople must not soak the hit.
        """
        opp_faints = sum(1 for p in state.opp_team if p is not None and p.fainted)
        for opp in state.opp_actives:
            if opp is None or opp.fainted:
                continue
            threats = incoming_damage(
                opp_species=_offense_species(opp), our_species=species,
                our_stats=bench_tm.stats, opp_ability=_effective_ability(opp) or "",
                opp_item=_opp_item(state, opp),
                our_ability=_our_ability_for_damage(bench_tm, species, state.designated_mega),
                our_item=bench_item, weather=_assumed_weather(state),
                our_defender_is_full_hp=True,
                opp_hp_fraction=opp.hp_fraction,
                opp_status=opp.status or "",
                opp_ally_faint_count=opp_faints,
                opp_times_hit=getattr(opp, "times_hit", 0),
                opp_flash_fire_active=opp.flash_fire_active,
            )
            if any(t.ohko_with_max_roll for t in threats):
                return False
        return True


def _other_opp_threatens(
    state: "BattleState", our_slots: list[int], ignored_opp_slot: int
) -> bool:
    """True if any opponent other than *ignored_opp_slot* max-roll-OHKOs any of
    our active mons at *our_slots* — a read of ``ctx.incoming_ohko``.

    If no slot has a computed threat entry, conservatively assume the other
    opponent *is* threatening, which makes doubling-up more costly (biasing
    toward spreading damage)."""
    ctx = _ensure_turn_ctx(state)
    known = [s for s in our_slots if s in ctx.incoming_ohko]
    if not known:
        return True   # nothing computable → assume the other opp is threatening
    return any(
        os != ignored_opp_slot
        for s in known
        for os in ctx.incoming_ohko[s]
    )


class DoublingAdjuster(JointAdjuster):
    """
    Penalises a pair where **both slots attack the same opponent** — doubling up.

    Doubling is costly when the target Protects (both moves wasted) or is already
    dead (the partner confirm-OHKOs it).  The base penalty is *reduced* when:

    * the target used Protect last turn (unlikely to spam it again), or
    * the OTHER opponent is not threatening (low opportunity cost of ignoring it).

    When one slot already **guarantees** the OHKO on the shared target, the
    other's attack there is wasted, so a near-veto factor (×0.05) stacks on the
    base — which is what makes the joint argmax pick the pair that **spreads**
    onto the survivor (the old explicit "redirect", now emergent).  With only one
    live foe there is nothing to spread to, so no penalty applies (forced double).

    Base schedule — (target_protected_last_turn, other_not_threatening):
        (True,  True):  ×0.70
        (True,  False) / (False, True): ×0.55
        (False, False): ×0.40   (riskiest)
    """

    name = "doubling_up"

    _FACTORS = {
        (True,  True):  0.70,
        (True,  False): 0.55,
        (False, True):  0.55,
        (False, False): 0.40,
    }
    CONFIRMED_OHKO_FACTOR = 0.05   # one slot already guarantees the kill (overkill)

    def factor(self, state, slot_a, a0, slot_b, a1):
        if not (_is_attack(a0) and _is_attack(a1)):
            return 1.0, 1.0, None
        target = a0.target_slot
        if target is None or target != a1.target_slot:
            return 1.0, 1.0, None   # not the same target → not doubling up

        active_opps = [i for i, o in enumerate(state.opp_actives)
                       if o is not None and not o.fainted]
        if len(active_opps) < 2:
            return 1.0, 1.0, None   # only one foe — doubling is forced, nothing to spread to

        opp_last = state.opp_last_moves
        target_protected = (target < len(opp_last)
                            and opp_last[target] in _PROTECT_MOVES)
        other_threatening = _other_opp_threatens(state, [slot_a, slot_b], target)
        base = self._FACTORS[(target_protected, not other_threatening)]

        ctx = _ensure_turn_ctx(state)
        a0_kills = (ctx.guarantees_ohko(slot_a, a0.move_name, target)
                    and not ctx.is_doomed(slot_a))
        a1_kills = (ctx.guarantees_ohko(slot_b, a1.move_name, target)
                    and not ctx.is_doomed(slot_b))
        if a0_kills or a1_kills:
            # One slot already confirms the kill → the *other's* attack here is
            # wasted (overkill).  Penalise the non-killer so the pair that spreads
            # onto the survivor wins (the emergent focus-fire "redirect").
            f = base * self.CONFIRMED_OHKO_FACTOR
            reason = (f"{self.name}: both attack slot {target}, partner confirms"
                      f" the OHKO (overkill) -> x{f:.3f}")
            if a1_kills and not a0_kills:
                return f, 1.0, reason   # slot_a is the wasteful doubler
            return 1.0, f, reason       # slot_b is the wasteful doubler (default)
        # Base doubling penalty falls on the higher slot (the conventional
        # "doubling-up" partner), matching the old per-slot DoublingUpModule.
        return 1.0, base, f"{self.name}: both attack slot {target} -> x{base}"


class CoordinationAdjuster(JointAdjuster):
    """
    Favours *coordinated* turns — both slots attacking, or both Protecting — by
    penalising the uncoordinated **split** where one slot throws away a turn on a
    **gratuitous** Protect while its partner attacks.

    Rationale: in VGC doubles a double-attack (apply full pressure) or a double-
    Protect (a deliberate stall) is usually the right play; a lone Protect
    alongside an attacking partner is the exception — only correct when that mon
    genuinely must shield (a real OHKO incoming, partner-clears, or a TR/TW stall
    turn).  Those Protects carry a "justified" reason and are left untouched.  A
    Protect with no such reason (e.g. only the FakeOut nudge) is gratuitous: the
    pair is penalised so the slot attacks alongside its partner instead, biasing
    the engine toward double-attack (protect less).

    A double-Protect (neither slot attacking) is never penalised; switches are
    untouched.  Checks both orderings so it fires whichever slot holds the Protect.
    """

    name = "coordination"
    SPLIT_PENALTY = 0.5

    def factor(self, state, slot_a, a0, slot_b, a1):
        if (_is_attack(a0) and a1.move_name in _PROTECT_MOVES
                and not _protect_is_justified(a1)):
            return 1.0, self.SPLIT_PENALTY, (
                f"{self.name}: gratuitous lone Protect (slot {slot_b}) beside an"
                f" attacking partner -> x{self.SPLIT_PENALTY}")
        if (_is_attack(a1) and a0.move_name in _PROTECT_MOVES
                and not _protect_is_justified(a0)):
            return self.SPLIT_PENALTY, 1.0, (
                f"{self.name}: gratuitous lone Protect (slot {slot_a}) beside an"
                f" attacking partner -> x{self.SPLIT_PENALTY}")
        return 1.0, 1.0, None


class FakeOutAdjuster(JointAdjuster):
    """
    Ensures a pair pays the Fake-Out adjustment exactly **once**.

    A live Fake Out flinches exactly one of our mons.  :class:`FakeOutModule`
    (phase 1) scores each slot in isolation, so it pessimistically discounts
    every slot's attacks (×0.5) and boosts its Protect (×3).  Pair-wise that
    counts the single Fake Out twice, so when a slot attacks, the *partner's*
    multiplier is divided back out: the attacker is the one assumed to eat the
    flinch, so the partner's attack is no longer discounted and its Protect no
    longer earns the Fake-Out boost.  Which multiplier the partner carries
    follows from ``ctx.fake_out_fired`` and the action itself (Protect ×3,
    other move ×0.5) — the same rule FakeOutModule applied.

    Symmetric: either slot's attack frees the other (mirror pairs score the
    same regardless of slot order).  When both attack, one discount is kept —
    the pair eats one flinch.  A double-Protect is untouched.
    """

    name = "fake_out"

    @staticmethod
    def _applied_mult(ctx: "TurnContext", action, slot: int) -> Optional[float]:
        """The Fake-Out multiplier FakeOutModule applied to *action* (or None)."""
        if not ctx.fake_out_fired(slot) or not action.is_move or action.is_switch:
            return None
        return (FakeOutModule.PROTECT_BOOST
                if action.move_name in _PROTECT_MOVES
                else FakeOutModule.ATTACK_DISCOUNT)

    def factor(self, state, slot_a, a0, slot_b, a1):
        ctx = _ensure_turn_ctx(state)
        if _is_attack(a0):
            mult = self._applied_mult(ctx, a1, slot_b)
            if mult:
                return 1.0, 1.0 / mult, (
                    f"{self.name}: partner (slot {slot_a}) absorbs Fake Out,"
                    f" slot {slot_b} freed -> x{1.0 / mult:.2f}")
        elif _is_attack(a1):
            mult = self._applied_mult(ctx, a0, slot_a)
            if mult:
                return 1.0 / mult, 1.0, (
                    f"{self.name}: partner (slot {slot_b}) absorbs Fake Out,"
                    f" slot {slot_a} freed -> x{1.0 / mult:.2f}")
        return 1.0, 1.0, None


class SwitchCollisionAdjuster(JointAdjuster):
    """Veto a pair where both slots switch to the **same** bench Pokémon — only
    one of them can, so the combination is illegal/wasteful."""

    name = "switch_collision"

    def factor(self, state, slot_a, a0, slot_b, a1):
        if a0.is_switch and a1.is_switch and a0.switch_target == a1.switch_target:
            return 1.0, 0.0, f"{self.name}: both slots switch to {a0.switch_target} -> x0"
        return 1.0, 1.0, None


class OppProtectRecencyModule(ScoringModule):
    """
    Boosts attacks that target an opponent who used Protect last turn.

    Consecutive Protect almost always fails in Gen 9 (second use in a row has
    a drastically reduced success rate).  When the committed target_slot points
    at a mon that just Protected, the attack is highly unlikely to be wasted —
    reward that targeting reliability with a small multiplier.

    This stacks naturally with the phase-2 DoublingAdjuster's ``target_protected``
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
        if not _is_fake_out_user(opp):
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
    flinching it and wasting its turn.

    Scoring adjustments (applied when ``ctx.fake_out_fired(slot)``):

    * Protect-family moves:  ×3.0  (strong encouragement to shield at least one mon)
    * Non-switch attacks:    ×0.5  (expected-value discount: ~50% chance this slot
                                    is the flinch target, halving the move's value)
    * Switch actions:        no change (switching out sidesteps Fake Out entirely)

    The ×0.5 attack discount is calibrated so that a guaranteed OHKO attack
    sits well below Protect's combined weight from FakeOutModule + ProtectModule.
    Below OHKO level, Protect clearly wins; at OHKO level it is a genuine
    toss-up, which reflects real-game decision complexity.

    These self-only adjustments run for *every* slot (each slot is scored in
    isolation); the joint :class:`FakeOutAdjuster` divides the partner's
    multiplier back out so a pair pays the Fake-Out adjustment exactly once.
    """

    name = "fake_out"

    PROTECT_BOOST   = 2.0
    ATTACK_DISCOUNT = 0.5

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        if not _ensure_turn_ctx(state).fake_out_fired(slot):
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


# Trick Room / Tailwind setters — derived from Champions usage data
# (population-weighted ≥ threshold of a base forme's population), not hand lists,
# so they stay complete and self-update with the stats.  Base names only
# (population_move_users keys by base_forme); membership is checked via
# _is_tr_setter / _is_tw_setter → _modeled_forme (infer forme, then
# base_forme-normalise), so mega forms match without a "-Mega" duplicate.
# Guarded by test_no_mega_entries_in_species_sets.
#
# TW note: priority-Tailwind setters (Talonflame's Gale Wings, Whimsicott's
# Prankster) remain in the derived set and are filtered downstream by
# _tw_setter_has_priority, which is where the "cannot be denied" logic lives.
_TR_SETTER_MIN_PCT = 40.0
_TAILWIND_SETTER_MIN_PCT = 20.0
_TR_SETTER_SPECIES: frozenset[str] = _population_move_users("Trick Room", _TR_SETTER_MIN_PCT)
_TAILWIND_SETTER_SPECIES: frozenset[str] = _population_move_users("Tailwind", _TAILWIND_SETTER_MIN_PCT)

# Redirection users — same data-driven derivation (base names; membership via
# _modeled_forme).  Kept as two sets because the two moves differ on immunities
# (see RedirectionModule): Rage Powder does NOT redirect Grass-types / Overcoat /
# Safety Goggles holders; Follow Me redirects everything.
_RAGE_POWDER_MIN_PCT = 30.0
_FOLLOW_ME_MIN_PCT   = 30.0
_RAGE_POWDER_USERS: frozenset[str] = _population_move_users("Rage Powder", _RAGE_POWDER_MIN_PCT)
_FOLLOW_ME_USERS:   frozenset[str] = _population_move_users("Follow Me", _FOLLOW_ME_MIN_PCT)

# Attacker abilities that make a move IGNORE redirection entirely (both Rage
# Powder and Follow Me).  Not modal on any current Champions mon, so this only
# matters when an attacker is actually confirmed to carry one — but then we must
# not apply the hedge.
_REDIRECT_IGNORE_ABILITIES: frozenset[str] = frozenset({"Stalwart", "Propeller Tail"})


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


class SetterUrgencyModule(ScoringModule):
    """
    "A speed-control setter is on the field and its effect is still stoppable —
    attack, don't stall."

    Exactly one urgency boost applies per turn, Trick Room first (the two are
    mutually exclusive by structure, not by cross-checking):

      * **Trick Room** — a TR setter is up, TR not active (or on its last turn,
        a re-set risk), and no opposing Tailwind → every attack ×2.0.
      * **Tailwind** — otherwise: a TW setter is up, TW not active (or last
        turn), and no Trick Room → every attack ×1.5.

    Target-agnostic: it rewards *attacking at all* over going passive while the
    speed tier is about to flip (swinging into the Fake-Out partner is fine).
    Protect and switches are untouched, so it biases the slot away from a
    stall.  (Urgency was briefly folded into denial; that lost the only weight
    keeping attacks ahead of a double-Protect on a Fake-Out + setter lead.)
    """

    name = "setter_urgency"

    TR_URGENCY = 2.0
    TW_URGENCY = 1.5

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        active_opps = [o for o in state.opp_actives if o is not None and not o.fainted]
        if not active_opps:
            return

        tr_relevant = (
            (not state.trick_room or state.trick_room_turns_left == 1)
            and not state.opp_tailwind
        )
        tw_relevant = (
            (not state.opp_tailwind or state.opp_tailwind_turns_left == 1)
            and not state.trick_room
        )

        if any(_is_tr_setter(o) for o in active_opps) and tr_relevant:
            factor = self.TR_URGENCY
            label  = ("trick_room: TR setter on field (TR last turn, re-set risk)"
                      if state.trick_room
                      else "trick_room: TR setter on field (TR not active)")
        elif (any(_is_tw_setter(o) for o in active_opps)
                and tw_relevant):
            factor = self.TW_URGENCY
            label  = ("tailwind: TW setter on field (TW last turn, re-set risk)"
                      if state.opp_tailwind
                      else "tailwind: TW setter on field (TW not active)")
        else:
            return

        for action in actions:
            if action.is_switch or action.move_name in _PROTECT_MOVES:
                continue
            action.weight *= factor
            action.reasons.append(f"{label} -> x{factor}")


class SetterDenialModule(ScoringModule):
    """
    "Can I kill the setter before its effect lands?"

    A candidate already aimed at a speed-control setter earns the denial boost
    when the kill is confirmed (``ctx.guarantees_ohko``), we outspeed the
    setter, and its setup move carries no +1 priority (Prankster / Gale Wings):

      * Trick Room setter:  ×2.0
      * Tailwind setter:    ×1.5

    Effects already active can't be denied.  An action denies at most one
    setter — Trick Room is tried first, so its claim wins when one target sets
    both.  Choosing the setter as target is emergent: the move→setter candidate
    accumulates DamageOutput + ThreatElimination + this boost and wins on its
    own merit, no target overwrite needed.
    """

    name = "setter_denial"

    TR_DENIAL = 2.0
    TW_DENIAL = 1.5

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        mon = state.my_actives[slot] if slot < len(state.my_actives) else None
        if mon is None:
            return
        ours_cbt = _our_combatant(state, slot)
        if ours_cbt is None:
            return

        # Deniable setter slots per effect, in priority order (Trick Room first).
        configs = [
            ("trick_room", _TR_SETTER_SPECIES, "Trick Room",
             lambda opp: _effective_ability(opp) == "Prankster",
             self.TR_DENIAL, state.trick_room),
            ("tailwind", _TAILWIND_SETTER_SPECIES, "Tailwind",
             _tw_setter_has_priority, self.TW_DENIAL, state.opp_tailwind),
        ]
        deniable: list[tuple[str, float, set[int]]] = []
        for (label, species, setter_move, has_priority, factor, active) in configs:
            if active:
                continue   # effect already up — it can't be denied
            slots: set[int] = set()
            for opp_slot, opp in enumerate(state.opp_actives):
                if opp is None or opp.fainted:
                    continue
                if _modeled_forme(opp) not in species and setter_move not in opp.moves:
                    continue
                if has_priority(opp):
                    continue
                setter_cbt = _opp_combatant(state, opp_slot)
                if (setter_cbt is None or will_outspeed(
                        ours_cbt, setter_cbt, trick_room=state.trick_room) <= 0.5):
                    continue
                slots.add(opp_slot)
            if slots:
                deniable.append((label, factor, slots))
        if not deniable:
            return

        ctx = _ensure_turn_ctx(state)
        for action in actions:
            if not action.is_move or action.move_name in _PROTECT_MOVES:
                continue
            ts = action.target_slot
            if ts is None:
                continue
            for (label, factor, slots) in deniable:
                if ts not in slots:
                    continue
                if not ctx.guarantees_ohko(slot, action.move_name, ts):
                    continue   # setter survives — it still sets the effect
                action.weight *= factor
                action.reasons.append(
                    f"{label}: deny {state.opp_actives[ts].species}"
                    f" (guaranteed OHKO) -> x{factor}"
                )
                break   # at most one denial per action — the TR claim wins


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


class RedirectionModule(ScoringModule):
    """Hedge our single-target attacks against an active opponent redirector
    (Rage Powder / Follow Me).

    When a redirector is on the field, our single-target moves get pulled onto
    it, so each such attack is only as useful as the damage it does **to the
    redirector**: scale its weight by that fraction (capped at 1.0).  This gives
    the two anchor cases for free — a move the redirector is immune to → ×0
    (don't feed it), a move that KOs the redirector → ×1 (removing the redirector
    ends the redirection) — and, by scaling attacks down, automatically raises
    the relative value of Protect / switching / spread moves (the "play around
    it" answer) without touching them directly.

    Exemptions (the move is NOT redirected, so we skip the hedge):
      * Spread / status / switch candidates — only single-target attacks
        (``target_slot is not None`` and a damaging move) are redirected.
      * Stalwart / Propeller Tail on our attacker — ignore redirection entirely
        (both moves).
      * Rage Powder only: a Grass-type attacker, or one with Overcoat, or holding
        Safety Goggles.  Follow Me has no such immunity.

    Backlog (not handled here): blend with intended-target damage instead of
    assuming redirection always fires; skip the hedge for a move already aimed at
    the redirector (minor double-count vs DamageOutput); coordinate the second
    slot so it doesn't over-commit onto the redirector once it's covered.
    """

    name = "redirection"

    def score(self, state: "BattleState", slot: int, actions: list[Action]) -> None:
        mon = state.my_actives[slot] if slot < len(state.my_actives) else None
        if mon is None:
            return
        tm = find_member(mon.species)
        stats = _our_stats(state, slot)
        if tm is None or stats is None:
            return

        # Active opponent redirectors, tagged by which move (immunities differ).
        redirectors: list[tuple[int, bool]] = []   # (opp_slot, is_rage_powder)
        for os, opp in enumerate(state.opp_actives):
            if opp is None or opp.fainted:
                continue
            forme = _modeled_forme(opp)
            if forme in _RAGE_POWDER_USERS:
                redirectors.append((os, True))
            elif forme in _FOLLOW_ME_USERS:
                redirectors.append((os, False))
        if not redirectors:
            return

        # Our attacker's active-forme type/ability/item (mega-aware) decide which
        # redirectors actually pull our moves.
        is_mega   = mon.species == tm.mega_name
        will_mega = (not is_mega and tm.mega_stats is not None
                     and state.designated_mega == tm.name)
        forme_name = tm.mega_name if ((is_mega or will_mega) and tm.mega_name) else mon.species
        sp_data = _get_species(forme_name)
        our_types = sp_data.get("types", []) if sp_data else []
        our_ability = _our_ability_for_damage(tm, mon.species, state.designated_mega)
        our_item = _our_item(mon)

        def _redirects_us(is_rage_powder: bool) -> bool:
            if our_ability in _REDIRECT_IGNORE_ABILITIES:
                return False                       # Stalwart / Propeller Tail
            if is_rage_powder:
                if "Grass" in our_types:           return False
                if our_ability == "Overcoat":      return False
                if our_item == "Safety Goggles":   return False
            return True

        pullers = [os for os, rp in redirectors if _redirects_us(rp)]
        if not pullers:
            return
        redir_slot = pullers[0]                    # one redirector is the norm
        redir = state.opp_actives[redir_slot]
        ally_faints = sum(1 for p in state.my_team if p.fainted)

        def _frac(move_name: str) -> float:
            """Avg damage fraction of *move_name* against the redirector."""
            cur_hp = (redir.hp if (not redir.hp_is_percentage and redir.hp > 0) else None)
            results = outgoing_damage(
                our_species=mon.species, our_stats=stats, our_moves=[move_name],
                opp_species=_defense_species(redir),
                our_ability=our_ability, our_item=our_item,
                opp_ability=_effective_ability(redir) or "", opp_item=_opp_item(state, redir),
                weather=_assumed_weather(state), ally_faint_count=ally_faints,
                opp_current_hp=cur_hp,
                opp_hp_percent=(redir.hp if (redir.hp_is_percentage and 0 < redir.hp < 100) else None),
                opp_screens=getattr(state, "opp_screens", None),
                attacker_boosts=mon.boosts, defender_boosts=redir.boosts,
                attacker_hp_fraction=mon.hp_fraction, attacker_status=mon.status or "",
                flash_fire_active=mon.flash_fire_active,
            )
            return results[0].hp_fraction_avg if results else 0.0

        for action in actions:
            # Only single-target damaging attacks are redirected; spread (target
            # None) / status / switches are not.
            if not action.is_move or action.target_slot is None:
                continue
            if get_move_category(action.move_name) == "Status":
                continue
            frac = min(_frac(action.move_name), 1.0)
            action.weight *= frac
            action.reasons.append(
                f"{self.name}: pulled to redirector -> {frac:.0%} dmg -> x{frac:.2f}"
            )


# ── Factory ───────────────────────────────────────────────────────────────────

def make_engine() -> DecisionEngine:
    """
    Return a DecisionEngine pre-loaded with all default modules.

    **Phase 1** — per-slot scoring modules, run for each slot in isolation
    (blind to the partner) over its ``(move, target)`` candidates:

      DamageOutput -> ThreatElimination -> IncomingOHKO -> TurnOrder ->
      SetterUrgency -> SetterDenial -> OppProtectRecency ->
      ConsecutiveProtect -> Protect -> FakeOut -> FieldCondition -> Switch

    **Phase 2** — joint adjusters, applied by :meth:`DecisionEngine.coordinate`
    over *pairs* of candidates (the only place cross-slot effects live):

      Doubling -> Coordination -> FakeOut(free) -> SwitchCollision

    Damage runs first so KO multipliers compound on the raw damage signal before
    safety considerations are layered on top.  ThreatEliminationModule answers
    both kill questions from the precomputed TurnContext: "will I die before I
    act?" gates the credit off, and otherwise "can I guarantee a kill?" applies
    ×5 (on the candidate already aimed at the OHKO'd target).  IncomingOHKOModule
    then asks "can they OHKO me?".  TurnOrderModule rewards faster attackers
    before disruption bonuses.  SetterUrgency asks "is a stoppable speed-control
    setter up?" (one boost, Trick Room first); SetterDenial asks "can I kill the
    setter first?" (per-candidate, Trick Room claim wins).  ConsecutiveProtect
    precedes Protect; FieldCondition follows Protect so its stall bonus stacks
    on existing weight.

    The phase-2 adjusters subsume what the old greedy + ``recoordinate`` re-pass
    did by hand: the doubling adjuster's confirmed-OHKO near-veto makes the
    spread pair win (emergent focus-fire "redirect"); the coordination adjuster
    squeezes out a gratuitous lone Protect beside an attacker; the fake-out
    adjuster frees the partner of the slot absorbing a Fake Out; the switch-
    collision adjuster vetoes both slots switching to the same mon.
    """
    return DecisionEngine(
        modules=[
            DamageOutputModule(),         # 1: ×(1+dmg) on each (move,target) candidate
            ThreatEliminationModule(),    # 2: guarantee a kill? (×5) — gated off when doomed (ctx)
            ProtectValueModule(),         # 3: boost Protect on OHKO threat + partner-clears rows
            TurnOrderModule(),            # 4: scale attacks by turn-order position
            SetterUrgencyModule(),        # 5: stoppable TR/TW setter up? attack, don't stall
            SetterDenialModule(),         # 6: confirmed kill on a setter we outspeed?
            OppProtectRecencyModule(),    # 7: reward attacking a mon that can't Protect again
            ConsecutiveProtectModule(),   # 8: penalise back-to-back Protect (×0.2)
            FakeOutModule(),              # 9: discount attacks / boost Protect vs fresh Fake Out users
            FieldConditionModule(),       # 10: stall on last turn of opp Tailwind / Trick Room
            RedirectionModule(),          # 11: hedge single-target attacks vs an active redirector
            SwitchModule(),               # 12: evaluate switch options
        ],
        joint=[
            DoublingAdjuster(),           # both attack same target: ×0.40–0.70, ×0.05 if overkill
            CoordinationAdjuster(),       # gratuitous lone Protect beside an attacker: ×0.5
            FakeOutAdjuster(),            # lower slot absorbs Fake Out → free the partner
            SwitchCollisionAdjuster(),    # both switch to the same mon: ×0
        ],
    )
