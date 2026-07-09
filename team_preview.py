"""team_preview.py — Team selection for VGC team preview.

Two-stage process:

1. :func:`select_team`  — Choose which Pokémon to bring, scored by type matchups.
2. :func:`select_leads` — Pick the best lead *pair*: type matchups vs the
   predicted opponent leads × initiative rows (slow leads without priority
   are demoted unless Trick Room is expected; see the 0.7.7 changelog).

Usage::

    from team_preview import select_team, select_leads
    from team import get_team

    slots   = select_team(opp_species, get_team(), n=4)
    ordered = select_leads(slots, get_team(), opp_species)

Scoring overview
----------------
Each of our Pokémon is given two sub-scores against the opponent's revealed
team, then combined into one final score:

* **Offensive coverage** (weight 2) — for each opponent, how hard can we hit
  them?  We take the best type-effectiveness our move types can achieve
  against that opponent's typing, then sum across all opponents.  A mon with
  super-effective coverage against several opponents scores high; one limited
  to neutral or resisted hits scores low.

* **Defensive durability** (weight 1) — for each opponent, how badly can they
  hit us with their STAB types?  We invert the worst incoming multiplier so
  that resists and immunities reward the score and weaknesses penalise it.

Mons are ranked by combined score; the top *n* are brought to the battle, in
score order so that the two highest-scoring mons occupy the lead slots.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from data import (
    types_of, move_type, move_category, ability_of, all_pokemon, get_sets,
    move_priority, most_likely_speed, base_forme,
)
from damage import type_effectiveness
from team import TeamMember

log = logging.getLogger(__name__)

# ── Tuning constants ──────────────────────────────────────────────────────────

_OFFENSE_WEIGHT = 2.0   # multiplier for offensive coverage in the combined score
_DEFENSE_WEIGHT = 1.0   # multiplier for defensive durability in the combined score
_IMMUNITY_BONUS = 4.0   # defensive contribution when completely immune to a type

# select_leads pair rows (0.7.7).  Magnitudes grounded in the 0.7.6
# hundred-game sample: Kingambit won 41.3% when led vs 50.9% from the back
# (ratio ≈ 0.81), and Tailwind rosters were the worst archetype at 45.9%.
_SLOW_LEAD_FACTOR  = 0.85  # per lead slower than both predicted opp leads with
                           # no attacking priority move (waived when opp has a
                           # Trick Room setter — slow IS fast under TR)
_TW_EXPOSED_FACTOR = 0.85  # extra penalty on a DOUBLE-slow pair when the opp
                           # roster has an undeniable (priority) Tailwind setter

# ── Ability-based incoming damage modifiers ───────────────────────────────────
# Maps ability name → {attacking_type: multiplier applied to incoming damage}.
# Only abilities that modify type-based damage are listed; all others default
# to ×1.0.  Used by _defense_from_types to adjust the worst-hit calculation.
_ABILITY_DEFENSE_MODS: dict[str, dict[str, float]] = {
    "Thick Fat":     {"Fire": 0.5, "Ice": 0.5},
    "Heatproof":     {"Fire": 0.5},
    "Levitate":      {"Ground": 0.0},
    "Flash Fire":    {"Fire": 0.0},
    "Water Absorb":  {"Water": 0.0},
    "Storm Drain":   {"Water": 0.0},
    "Volt Absorb":   {"Electric": 0.0},
    "Lightning Rod": {"Electric": 0.0},
    "Motor Drive":   {"Electric": 0.0},
    "Sap Sipper":    {"Grass": 0.0},
    "Purifying Salt":{"Ghost": 0.5},
    "Dry Skin":      {"Water": 0.0, "Fire": 1.25},
}


# ── Opponent mega assumptions ─────────────────────────────────────────────────

def _mega_base_name(mega_name: str) -> str:
    """Extract the base species name from a mega form name.

    ``"Charizard-Mega-Y"`` → ``"Charizard"``,
    ``"Venusaur-Mega"``   → ``"Venusaur"``,
    ``"Floette-Eternal"`` → ``"Floette"``.

    Mega-suffix stripping goes through the canonical ``data.base_forme``; the
    ``-Eternal`` case (not a mega) stays a local special case.
    """
    base = base_forme(mega_name)
    if base != mega_name:
        return base
    if mega_name.endswith("-Eternal"):
        return mega_name[: -len("-Eternal")]
    return mega_name


def _build_opp_mega_forms(n: int = 8) -> dict[str, str]:
    """Return ``{base_species: assumed_mega_form}`` for the top-*n* megas by
    raw usage count.

    Iterates the sets data, identifies mega-form entries (names containing
    ``-Mega`` or ending in ``-Eternal``), and keeps only the highest-usage
    form per base species (so Charizard-Mega-Y beats Charizard-Mega-X
    automatically).  The top *n* base species by that count are returned.

    Computed once at module import time.
    """
    best: dict[str, tuple[int, str]] = {}   # base → (raw_count, mega_name)
    for species in all_pokemon():
        if "-Mega" not in species and not species.endswith("-Eternal"):
            continue
        d = get_sets(species)
        if not d:
            continue
        base  = _mega_base_name(species)
        count = d["raw_count"]
        if base not in best or count > best[base][0]:
            best[base] = (count, species)

    ranked = sorted(best.values(), key=lambda x: -x[0])[:n]
    result = {_mega_base_name(mega): mega for _, mega in ranked}
    log.debug("OPP MEGA ASSUMPTIONS (%d)  %s", n, result)
    return result


# Computed once at import: maps base preview species → assumed battle form.
# Any opponent species in this dict is treated as its mega form for scoring.
_OPP_MEGA_FORMS: dict[str, str] = _build_opp_mega_forms()


def _opp_assumed_form(name: str) -> str:
    """Return the assumed battle form for an opponent preview species.

    Top-usage megas are mapped to their mega form so that offensive and
    defensive scoring uses the correct typing.  All other species are returned
    unchanged.
    """
    return _OPP_MEGA_FORMS.get(name, name)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _move_types(member: TeamMember) -> frozenset[str]:
    """Return the set of attacking types available in *member*'s moveset.

    Only moves whose type can be looked up in the move database are included;
    moves with unknown types (e.g. status moves that deal no damage but happen
    not to have a type entry) are silently skipped.
    """
    types: set[str] = set()
    for move in member.moves:
        if move_category(move) == "Status":
            continue   # status moves deal no damage; don't count as offensive coverage
        t = move_type(move)
        if t:
            types.add(t)
    return frozenset(types)


def _defensive_types(member: TeamMember) -> list[str]:
    """Return the defensive typing used for incoming damage calculations.

    Uses the mega form's typing when the member carries a Mega Stone, since
    that is what will be active once the mon mega evolves in battle.  Falls
    back to the base form — and ultimately to ``["Normal"]`` if the species
    is not in the database.
    """
    if member.mega_name:
        mega_t = types_of(member.mega_name)
        if mega_t:
            return mega_t
    return types_of(member.name) or ["Normal"]


def _offensive_score(member: TeamMember, opp_species_list: list[str]) -> float:
    """Sum of the best type-effectiveness our member can deal to each opponent.

    For each opponent we take ``max(type_effectiveness(t, opp_types) * ability_mod for t in
    our_move_types)``, then sum across all opponents.  Opponent abilities that grant
    full immunity (e.g. Dry Skin → Water, Levitate → Ground, Flash Fire → Fire)
    are respected so we don't over-rate Pokémon whose STAB or coverage is blocked.

    Example — Water + Normal vs [Heliolisk (Electric/Normal, Dry Skin)]:
      Water: type chart ×1.0 vs Electric, ×1.0 vs Normal → raw 1.0
             but Dry Skin makes Water ×0.0 → 0.0 (immune)
      Normal: ×1.0 (no ability modifier) → 1.0
      Best = 1.0 (instead of the inflated 1.0 that ignores the immunity)

    A member with no recognised move types is treated as having neutral (×1.0)
    coverage across the board.
    """
    atk_types = _move_types(member)
    if not atk_types:
        return len(opp_species_list) * 1.0

    total = 0.0
    for opp in opp_species_list:
        opp_form   = _opp_assumed_form(opp)
        opp_types  = types_of(opp_form) or ["Normal"]
        opp_abil   = ability_of(opp_form)
        abil_mods  = _ABILITY_DEFENSE_MODS.get(opp_abil, {}) if opp_abil else {}
        best = 0.0
        for mt in atk_types:
            eff = type_effectiveness(mt, opp_types) * abil_mods.get(mt, 1.0)
            if eff > best:
                best = eff
        total += best
    return total


def _defense_from_types(
    our_types: list[str],
    opp_species_list: list[str],
    ability: Optional[str] = None,
) -> float:
    """Defensive resilience score given an explicit type list and optional ability.

    Shared by :func:`_defensive_score` (which reads the type list and ability
    from a TeamMember) and :func:`select_mega` (which needs to score both the
    base and mega form of the same member without constructing a fake TeamMember).

    The *ability* parameter adjusts incoming damage for abilities like Thick Fat
    (Fire/Ice ×0.5) and Levitate (Ground ×0.0) before the inversion is applied.
    """
    mods = _ABILITY_DEFENSE_MODS.get(ability, {}) if ability else {}
    total = 0.0
    for opp in opp_species_list:
        opp_types = types_of(_opp_assumed_form(opp)) or ["Normal"]
        worst = max(
            type_effectiveness(ot, our_types) * mods.get(ot, 1.0)
            for ot in opp_types
        )
        total += _IMMUNITY_BONUS if worst == 0.0 else 1.0 / worst
    return total


def _defensive_ability(member: TeamMember) -> Optional[str]:
    """Return the ability used for incoming damage calculations.

    Uses the mega form's ability when the member carries a Mega Stone (since
    that is what will be active in battle), otherwise the base ability stored
    in the team paste.
    """
    if member.mega_name:
        return ability_of(member.mega_name)
    return member.ability or None


def _defensive_score(member: TeamMember, opp_species_list: list[str]) -> float:
    """Sum of defensive resilience against each opponent's STAB attacking types.

    For each opponent we find the *worst* (highest) effective damage multiplier
    their STAB types achieve against us (type chart × ability modifier), then
    invert it:

    * immunity  (×0.0 incoming) → ``+_IMMUNITY_BONUS`` (default 4.0)
    * resist    (×0.5)          → +2.0
    * neutral   (×1.0)          → +1.0
    * weak      (×2.0)          → +0.5
    * quad-weak (×4.0)          → +0.25

    Higher total = more defensively sound against this opponent team.
    """
    return _defense_from_types(
        _defensive_types(member), opp_species_list, _defensive_ability(member)
    )


def _base_form_defensive_score(member: TeamMember, opp_species_list: list[str]) -> float:
    """Defensive score for *member*'s **base** (un-mega'd) form.

    Used by :func:`select_team` when a Mega-Stone holder is considered for the
    bring but cannot actually mega evolve — only one mega is allowed per battle,
    so any second stone holder would play with a dead item.  Scoring it with its
    base typing and base ability (instead of the mega form) stops the selector
    from over-valuing a second mega it can never use.

    For a member with no mega stone this is identical to :func:`_defensive_score`.
    """
    base_types = types_of(member.name) or ["Normal"]
    return _defense_from_types(base_types, opp_species_list, member.ability or None)


# ── Public score container ────────────────────────────────────────────────────

@dataclass
class MemberScore:
    """Per-member scoring breakdown returned by :func:`score_members`.

    Exposed so callers can log or analyse the scoring without re-running the
    pipeline.
    """
    index:   int         # 1-based slot in the team list
    member:  TeamMember
    offense: float       # raw offensive coverage score
    defense: float       # raw defensive resilience score

    @property
    def combined(self) -> float:
        """Weighted combination of offense and defense scores."""
        return _OFFENSE_WEIGHT * self.offense + _DEFENSE_WEIGHT * self.defense


# ── Engine-grounded preview evaluation (0.38.0) ──────────────────────────────
# The type-chart arithmetic above is a crude parallel model: it can't see real
# damage (stats/spreads/items/BP), OHKO thresholds, Fake Out pressure, or true
# turn order — which is how a lead that *looks* good by type multipliers loses
# on the actual board.  These helpers score preview decisions with the same
# engine that plays the game: build the turn-1 board and read the phase-1
# weights / damage facts directly.  The type-chart path below remains as the
# fallback when a member can't be resolved by the data layer (synthetic test
# fixtures, missing data).

_SWITCH_WANT_FACTOR = 0.5   # lead slot whose best phase-1 action is a SWITCH:
                            # the engine itself says this mon shouldn't be here
                            # (observed live: correct lead reads followed by
                            # turn-1 switches), so the pair is self-refuting
_DOOMED_LEAD_FACTOR = 0.25  # lead slot the board facts say is KO'd before it
                            # acts (ctx.doomed): in battle that's a ×0.2 move
                            # discount, but at preview we can simply not START
                            # the mon — a doomed lead concedes the slot.  (v9
                            # audit: Chandelure led into rain on a ×0.2-doomed
                            # overkill read and went 3-15 vs Swampert+Pelipper.)
_ATK_FLOOR = 0.05           # slot with no usable attack still scores something


def _members_resolvable(members: list[TeamMember]) -> bool:
    """True when every member resolves through team.find_member — the engine
    scoring path pulls stats through the data layer, so synthetic fixtures
    (tests) or a stale roster must fall back to the type-chart path."""
    from team import find_member
    return all(find_member(m.name) is not None for m in members)


def _preview_our_mon(member: TeamMember):
    """Our mon at full HP for a preview board (pre-mega species — the engine
    resolves designated-mega stats itself, exactly like a live turn 1)."""
    from battle import Pokemon
    hp = (member.stats or {}).get("hp", 100)
    return Pokemon(
        ident=f"p1: {member.name}", species=member.name, hp=hp, max_hp=hp,
        ability=member.ability, item=member.item, moves=list(member.moves),
    )


def _preview_opp_mon(species: str):
    """Opponent preview mon at 100% — the engine uses typical-spread stats and
    its usage-based forme/ability/item inference, same as an unrevealed foe."""
    from battle import Pokemon
    return Pokemon(
        ident=f"p2: {species}", species=species,
        hp=100, max_hp=100, hp_is_percentage=True,
    )


def _preview_state(lead_a: TeamMember, lead_b: TeamMember,
                   bench: list[TeamMember], opp_pair: list[str],
                   designated_mega: Optional[str],
                   *, trick_room: bool = False, opp_tailwind: bool = False):
    """A turn-1 BattleState for one candidate lead pair vs the predicted
    opponent leads — the same construction the snapshot scenario uses."""
    from battle import BattleState
    s = BattleState(battle_id="preview", my_side="p1")
    s.my_actives = [_preview_our_mon(lead_a), _preview_our_mon(lead_b)]
    s.my_team = list(s.my_actives)
    s.opp_actives = [_preview_opp_mon(o) for o in opp_pair]
    s.available_switches = [_preview_our_mon(m) for m in bench]
    s.moves_per_slot = [[{"move": mv} for mv in lead_a.moves],
                        [{"move": mv} for mv in lead_b.moves]]
    s.my_last_moves = ["", ""]
    s.opp_last_moves = ["", ""]
    s.my_slot_decisions = [None, None]
    s.my_disabled_moves = [None, None]
    s.my_encored_moves = [None, None]
    s.weather = None
    s.trick_room = trick_room
    s.trick_room_turns_left = 3 if trick_room else 0
    s.my_tailwind = False
    s.opp_tailwind = opp_tailwind
    s.opp_tailwind_turns_left = 3 if opp_tailwind else 0
    s.designated_mega = designated_mega
    return s


def _eval_lead_board(engine, lead_a: TeamMember, lead_b: TeamMember,
                     bench: list[TeamMember], opp_pair: list[str],
                     designated_mega: Optional[str],
                     **field) -> tuple[float, list[str]]:
    """Score one candidate lead pair on one field variant.

    Per slot, from the engine's phase-1 ranked actions:

    * slot value = the best **attack** weight — this already folds in real
      damage (capped at lethal), guaranteed-kill bonuses, true turn order
      (item/ability/TR-aware), dying-before-acting, and Fake Out pressure.
    * ``×_DOOMED_LEAD_FACTOR`` when the board facts say the slot is **KO'd
      before it acts** (``ctx.doomed``) — the in-battle ×0.2 move discount
      still lets a big kill-stack win the pair argmax, but a lead that dies
      before moving concedes the slot, so preview punishes it much harder.
    * ``×_SWITCH_WANT_FACTOR`` when a **switch outweighs every stay action** —
      the engine's own verdict that this mon doesn't want to be on this board.

    Pair score = slot values multiplied (mirrors the joint engine: one dead
    slot should sink the pair, not average out).
    Returns (score, per_slot_values, notes)."""
    from decision.engine import _PROTECT_MOVES
    from decision.modules import _ensure_turn_ctx
    state = _preview_state(lead_a, lead_b, bench, opp_pair,
                           designated_mega, **field)
    slot_vals: list[float] = []
    notes: list[str] = []
    for slot, member in ((0, lead_a), (1, lead_b)):
        ranked = engine.scored_actions(state, slot)
        atk = max((a.weight for a in ranked
                   if a.is_move and a.move_name not in _PROTECT_MOVES),
                  default=0.0)
        stay = max((a.weight for a in ranked if not a.is_switch), default=0.0)
        sw = max((a.weight for a in ranked if a.is_switch), default=0.0)
        val = max(atk, _ATK_FLOOR)
        if _ensure_turn_ctx(state).is_doomed(slot):
            val *= _DOOMED_LEAD_FACTOR
            notes.append(f"{member.name}: doomed on this board "
                         f"(KO'd before acting)")
        if sw > stay:
            val *= _SWITCH_WANT_FACTOR
            notes.append(f"{member.name}: engine prefers switching out "
                         f"(sw {sw:.2f} > stay {stay:.2f})")
        slot_vals.append(val)
    return slot_vals[0] * slot_vals[1], slot_vals, notes


def _preview_mega_for(pair: tuple[TeamMember, TeamMember],
                      bench: list[TeamMember]) -> Optional[str]:
    """Which member the eval assumes megas: a stone holder in the lead pair
    first (it acts turn 1), else the first stone holder on the bench."""
    for m in (*pair, *bench):
        if m.mega_name:
            return m.name
    return None


def _score_lead_pairs(slots: list[int], our_members: list[TeamMember],
                      predicted: list[str], opp_species_list: list[str],
                      ) -> Optional[dict[tuple[int, int], float]]:
    """Engine-grounded score for every C(n,2) lead pair from *slots*.

    Field variants: the base (no-field) board, plus a Trick-Room-on board when
    the **predicted lead pair** contains a TR setter and an opponent-Tailwind
    board when it contains a TW setter — averaged, so initiative under the
    opponent's imminent game plan is priced by the *real* turn-order model
    instead of hand-tuned rows.  Variants are keyed on the predicted PAIR, not
    the whole roster: a benched setter's field is turns away — long after our
    leads have acted — and averaging it in let a speculative TR board drown
    the base reality (a doubly-doomed pair scored 2401 because "under TR
    they'd act first").  Returns None when the engine path is unavailable
    (unresolvable members)."""
    if not _members_resolvable([our_members[i - 1] for i in slots]):
        return None
    try:
        from decision.modules import (
            make_engine, _is_tr_setter, _is_tw_setter,
        )
    except Exception:
        return None

    tr_imminent = any(_is_tr_setter(_preview_opp_mon(s)) for s in predicted)
    tw_imminent = any(_is_tw_setter(_preview_opp_mon(s)) for s in predicted)
    variants: list[dict] = [{}]
    if tr_imminent:
        variants.append({"trick_room": True})
    if tw_imminent:
        variants.append({"opp_tailwind": True})

    engine = make_engine()
    # Empirical pair prior: the board eval is a turn-1 model and can favour
    # pairs that don't convert; multiply in each pair's smoothed observed win
    # rate for THIS team version (unseen pair = ×1.0 — see data/our_leads.py).
    try:
        from data.our_leads import pair_factor
        from team import active_team, active_team_version
        _t, _v = active_team(), active_team_version()
        team_spec = f"{_t}@{_v}" if _t and _v else None
    except Exception:
        team_spec = None

    from itertools import combinations
    scores: dict[tuple[int, int], tuple[float, tuple[int, int]]] = {}
    for a, b in combinations(sorted(slots), 2):
        ma, mb = our_members[a - 1], our_members[b - 1]
        bench = [our_members[i - 1] for i in slots if i not in (a, b)]
        mega = _preview_mega_for((ma, mb), bench)
        total = 0.0
        vals = [0.0, 0.0]
        all_notes: list[str] = []
        for field in variants:
            sc, sv, notes = _eval_lead_board(engine, ma, mb, bench, predicted,
                                             mega, **field)
            total += sc
            vals[0] += sv[0]
            vals[1] += sv[1]
            all_notes += notes
        score = total / len(variants)
        if team_spec is not None:
            prior = pair_factor(team_spec, ma.name, mb.name)
            if prior != 1.0:
                score *= prior
                all_notes.append(f"pair prior x{prior:.2f}")
        # Stronger slot value leads first (position is mostly cosmetic, but it
        # keeps the log readable and matches the old score-ordered convention).
        ordered = (a, b) if vals[0] >= vals[1] else (b, a)
        scores[(a, b)] = (score, ordered)
        log.info("  LEAD EVAL  %s+%s  score=%.3f%s",
                 ma.name, mb.name, score,
                 ("  [" + "; ".join(all_notes) + "]") if all_notes else "")
    return scores


def _engine_matchup_scores(opp_species_list: list[str],
                           our_members: list[TeamMember],
                           ) -> Optional[dict[int, tuple[float, float]]]:
    """Engine-computed (mega_combined, base_combined) per 1-based member slot.

    Per member × opponent: offense = the best damage fraction we deal (capped
    at 1.0 — an OHKO maxes it), defense = 1 − the worst fraction we take
    (floored at 0 — being OHKO'd zeroes it), averaged over the opponent's six
    and combined with the existing offense×2 + defense×1 weights.  A stone
    holder is scored twice — as its mega and as its base form — so the
    one-mega-per-battle demotion is *native* (re-evaluated as base, replacing
    the old BST-scaling approximation).  None → caller falls back."""
    if not _members_resolvable(our_members):
        return None
    try:
        from damage import outgoing_damage, incoming_damage
        from data import assumed_forme, ability_of
        from decision.modules import _assumed_ability, _assumed_item
    except Exception:
        return None

    def _one_form(species: str, stats: dict, ability: str, item,
                  moves: list[str]) -> float:
        off_total = def_total = 0.0
        for opp in opp_species_list:
            opp_form = assumed_forme(opp)
            opp_ab = _assumed_ability(opp_form) or ""
            opp_it = _assumed_item(opp_form, frozenset())
            res = outgoing_damage(
                our_species=species, our_stats=stats, our_moves=moves,
                opp_species=opp_form, our_ability=ability or "",
                our_item=item, opp_ability=opp_ab, opp_item=opp_it,
            )
            off_total += min(res[0].hp_fraction_avg, 1.0) if res else 0.0
            thr = incoming_damage(
                opp_species=opp_form, our_species=species, our_stats=stats,
                opp_ability=opp_ab, opp_item=opp_it,
                our_ability=ability or "", our_item=item,
            )
            worst = max((t.hp_fraction_avg for t in thr), default=0.0)
            def_total += max(0.0, 1.0 - min(worst, 1.0))
        n = max(len(opp_species_list), 1)
        return _OFFENSE_WEIGHT * (off_total / n) + _DEFENSE_WEIGHT * (def_total / n)

    out: dict[int, tuple[float, float]] = {}
    for i, m in enumerate(our_members, start=1):
        base_stats = m.stats or {}
        base_val = _one_form(m.name, base_stats, m.ability, m.item, m.moves)
        if m.mega_name and m.mega_stats:
            mega_val = _one_form(m.mega_name, m.mega_stats,
                                 ability_of(m.mega_name) or m.ability,
                                 m.item, m.moves)
        else:
            mega_val = base_val
        out[i] = (mega_val, base_val)
    return out


# ── Public API ────────────────────────────────────────────────────────────────

def score_members(
    opp_species_list: list[str],
    our_members: list[TeamMember],
) -> list[MemberScore]:
    """Score and rank all our members against the opponent's revealed team.

    Returns a list of :class:`MemberScore` sorted best-first by combined score.
    When *opp_species_list* is empty (no opponent data yet) the list is
    returned in original team order with zero scores.

    This function is the numerical core; production code calls
    :func:`select_team` instead.
    """
    if not opp_species_list:
        return [MemberScore(i + 1, m, 0.0, 0.0) for i, m in enumerate(our_members)]

    scores = [
        MemberScore(
            index=i + 1,
            member=m,
            offense=_offensive_score(m, opp_species_list),
            defense=_defensive_score(m, opp_species_list),
        )
        for i, m in enumerate(our_members)
    ]
    scores.sort(key=lambda s: s.combined, reverse=True)

    for s in scores:
        log.debug(
            "  PREVIEW  %-20s  off=%.2f  def=%.2f  total=%.2f",
            s.member.name, s.offense, s.defense, s.combined,
        )

    return scores


def select_team(
    opp_species_list: list[str],
    our_members: list[TeamMember],
    n: int = 4,
) -> list[int]:
    """Choose which *n* Pokémon to bring to a battle.

    Returns a list of 1-based slot indices into *our_members*, ordered by
    descending combined score so that the two best-scoring members occupy the
    lead positions (indices 0 and 1).

    Falls back to the first *n* slots in team order when *opp_species_list* is
    empty (no opponent data available at preview time).

    **One mega per battle.**  Only one Pokémon can mega evolve in a game, so a
    second Mega-Stone holder would play with a dead item (a mega stone confers
    nothing un-evolved).  ``score_members`` values every stone holder at its
    *mega* strength, which over-brings the pair.  Selection therefore proceeds
    greedily: the first stone holder taken keeps its mega value, but any further
    stone holder is re-valued at its **base** form — base typing/ability *and*
    base stats (scaled by its own ``base_BST / mega_BST``) — which usually lets a
    non-stone member take the slot instead.  Scaling by stats matters because a
    Pokémon whose typing is unchanged on mega (e.g. a speed/power mega) wouldn't
    be demoted by type scoring alone.  This is fully generic — it keys off
    ``member.mega_name`` (truthy iff the member carries a Mega Stone) and the
    member's own stat sheet, never specific species — so it still holds if the
    team changes.

    Args:
        opp_species_list: Species names of the opponent's revealed preview team.
        our_members:      Full six-member team (from :func:`team.get_team`).
        n:                Number of Pokémon to bring (default 4 for VGC).

    Returns:
        List of *n* 1-based slot indices, leads-first.
    """
    if not opp_species_list:
        # No opponent data — preserve the team-order fallback.
        return list(range(1, len(our_members) + 1))[:n]

    # ── Engine path (0.38.0): real damage matchups, native mega demotion ──
    engine_scores = _engine_matchup_scores(opp_species_list, our_members)
    if engine_scores is not None:
        remaining = list(engine_scores.keys())
        picked: list[int] = []
        mega_claimed = False

        def _value(i: int) -> float:
            mega_val, base_val = engine_scores[i]
            holder = bool(our_members[i - 1].mega_name)
            return base_val if (holder and mega_claimed) else mega_val

        while remaining and len(picked) < n:
            best = max(remaining, key=_value)
            picked.append(best)
            remaining.remove(best)
            if our_members[best - 1].mega_name and not mega_claimed:
                mega_claimed = True
        log.info("TEAM SELECT (engine)  %s",
                 [(our_members[i - 1].name,
                   f"{engine_scores[i][0]:.2f}/{engine_scores[i][1]:.2f}")
                  for i in picked])
        return picked

    # ── Fallback: type-chart scoring (unresolvable members / no data) ─────
    scored = score_members(opp_species_list, our_members)

    def _base_combined(ms: MemberScore) -> float:
        """Combined score for a stone holder that *cannot* mega this battle.

        It plays as its true form: base typing/ability **and base stats**.  The
        type-matchup score is taken from the base form, then scaled by the
        member's own ``base_BST / mega_BST`` so the lost mega stat jump is
        reflected (a Pokémon whose typing is unchanged on mega — so base-form
        type scoring alone wouldn't demote it — is still correctly devalued).
        Fully generic: reads only the member's own stat sheet, no species names.
        """
        base_def = _base_form_defensive_score(ms.member, opp_species_list)
        val = _OFFENSE_WEIGHT * ms.offense + _DEFENSE_WEIGHT * base_def
        m = ms.member
        if m.mega_stats and m.stats:
            mega_bst = sum(m.mega_stats.values())
            if mega_bst > 0:
                val *= sum(m.stats.values()) / mega_bst
        return val

    def _effective(ms: MemberScore, mega_claimed: bool) -> float:
        # A stone holder is only worth its mega value if no mega is spoken for;
        # otherwise it can't evolve, so value it as its (itemless) base form.
        if ms.member.mega_name and mega_claimed:
            return _base_combined(ms)
        return ms.combined

    remaining = list(scored)
    selected: list[MemberScore] = []
    mega_claimed = False
    while remaining and len(selected) < n:
        best = max(remaining, key=lambda ms: _effective(ms, mega_claimed))
        selected.append(best)
        remaining.remove(best)
        if best.member.mega_name and not mega_claimed:
            mega_claimed = True   # this slot consumes the battle's single mega

    return [s.index for s in selected]


def select_mega(
    slots: list[int],
    our_members: list[TeamMember],
    opp_species_list: list[str],
) -> Optional[str]:
    """Choose which selected Pokémon should mega evolve this battle.

    Returns the base species name (``TeamMember.name``) of the designated
    mega, or ``None`` if none of the selected members carry a Mega Stone.

    When exactly one mega is selected the answer is trivial.  When two are
    selected, the one whose mega form provides the greatest *defensive* type
    improvement over its base form is preferred; the combined score from
    :func:`score_members` breaks ties (i.e. the more offensively valuable
    mega wins when both improve defensively by the same amount).

    Args:
        slots:        1-based indices from :func:`select_team`.
        our_members:  Full six-member team.
        opp_species_list: Opponent's preview team.

    Returns:
        Base species name of the designated mega, or ``None``.
    """
    # Build a map from slot index → combined score so we can use it as a
    # tiebreaker without re-running the full scoring pipeline.
    score_map: dict[int, float] = {}
    if opp_species_list:
        for s in score_members(opp_species_list, our_members):
            score_map[s.index] = s.combined

    candidates: list[tuple[float, float, str]] = []  # (delta, combined, name)
    for slot in slots:
        member = our_members[slot - 1]
        if not member.mega_name:
            continue

        if opp_species_list:
            mega_types   = types_of(member.mega_name) or _defensive_types(member)
            mega_ability = ability_of(member.mega_name)
            base_types   = types_of(member.name) or ["Normal"]
            base_ability = member.ability or None
            delta = (
                _defense_from_types(mega_types, opp_species_list, mega_ability)
                - _defense_from_types(base_types, opp_species_list, base_ability)
            )
        else:
            delta = 0.0

        candidates.append((delta, score_map.get(slot, 0.0), member.name))

    if not candidates:
        return None

    # Sort: highest defensive delta first, highest combined score as tiebreaker.
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    designated = candidates[0][2]

    log.info(
        "TEAM PREVIEW  designated mega: %s  (candidates: %s)",
        designated,
        [(name, f"Δdef={d:.2f} score={sc:.2f}") for d, sc, name in candidates],
    )
    return designated


def select_leads(
    slots: list[int],
    our_members: list[TeamMember],
    opp_species_list: list[str],
) -> list[int]:
    """Determine lead order from the already-selected bring list.

    Uses historical opponent-lead frequency data (accumulated from v0.5.0
    battles onward) to predict which two Pokémon from *opp_species_list* are
    most likely to be led, then picks the best lead *pair* (all C(n,2)
    combinations): the pair's combined type-matchup score against the
    predicted leads, multiplied by initiative rows —

    * ``_SLOW_LEAD_FACTOR`` (×0.85) per pair member that is slower than both
      predicted leads and has no attacking priority move.  Waived entirely
      when the opponent roster contains a Trick Room setter (slow IS fast
      under TR).
    * ``_TW_EXPOSED_FACTOR`` (extra ×0.85) when BOTH pair members are slow
      and the opponent roster has an undeniable priority Tailwind setter
      (Gale Wings Talonflame / Prankster).

    With no rows firing the argmax pair equals the top-2 individual matchup
    scores (the pre-0.7.7 behaviour).

    Falls back to ascending team-slot order when:

    * *opp_species_list* is empty (no opponent data at preview time), or
    * *slots* is empty, or
    * no lead-frequency data has been recorded yet (``total_battles() == 0``).

    Args:
        slots:            1-based indices into *our_members* from
                          :func:`select_team`, length *n*.
        our_members:      Full six-member team.
        opp_species_list: Opponent's preview team.

    Returns:
        *slots* reordered so the two best counters to the predicted opponent
        leads occupy positions 0 and 1; the remaining slots keep their
        original relative order.
    """
    if not opp_species_list or not slots:
        return sorted(slots)

    # ── Check whether we have usable lead frequency data ─────────────────
    try:
        from data.lead_stats import predict_pair, total_battles as _total
        has_data = _total() > 0
    except Exception:
        has_data = False

    if not has_data:
        log.info("LEAD ORDER  %s  (no lead data, using original order)", sorted(slots))
        return sorted(slots)

    # ── Predict the most likely opponent lead PAIR ────────────────────────
    # Co-occurrence-aware: prefer the duo actually led together over the two
    # highest individual leads (which can be two supports rarely paired).
    predicted = predict_pair(opp_species_list)
    log.info("PREDICTED OPP LEADS  %s", predicted)

    # ── Engine path (0.38.0): score each lead pair on the real board ──────
    # Build the turn-1 BattleState per candidate pair and read the phase-1
    # weights (real damage, kills, true turn order, Fake Out, doomed) — plus
    # the switch-want penalty: if the engine's best action for a lead is to
    # switch OUT, that lead pair is self-refuting.  TR / undeniable-TW rosters
    # add field variants instead of hand-tuned rows.
    if len(predicted) == 2:
        pair_scores = _score_lead_pairs(slots, our_members, predicted,
                                        opp_species_list)
        if pair_scores:
            (_, ordered) = max(pair_scores.values(), key=lambda v: v[0])
            leads = list(ordered)
            back = [s for s in slots if s not in ordered]
            result = leads + back
            log.info(
                "LEAD ORDER  %s  (engine eval: %s vs predicted %s)",
                result, [our_members[i - 1].name for i in leads], predicted,
            )
            return result

    # ── Fallback: type-chart scoring + initiative rows ────────────────────
    all_scores    = score_members(predicted, our_members)
    score_by_slot = {s.index: s.combined for s in all_scores}

    # ── Initiative / speed-control context (pair rows, 0.7.7) ─────────────
    # Imported lazily (matching the lead_stats import above) to keep
    # team_preview importable without the full decision package.
    try:
        from decision.modules import (
            _TR_SETTER_SPECIES, _TAILWIND_SETTER_SPECIES, _assumed_ability,
        )
        tr_expected = any(s in _TR_SETTER_SPECIES for s in opp_species_list)
        tw_undeniable = any(
            s in _TAILWIND_SETTER_SPECIES
            and (s == "Talonflame" or _assumed_ability(s) == "Prankster")
            for s in opp_species_list
        )
    except Exception:
        tr_expected = tw_undeniable = False

    opp_lead_speeds = [
        spd for spd in (most_likely_speed(s) for s in predicted) if spd
    ]

    def _lead_liability(slot: int) -> bool:
        """Leading this member concedes initiative: slower than every predicted
        opponent lead, with no attacking priority move — and no Trick Room
        expected to invert the speed order (slow IS fast under TR)."""
        if tr_expected or not opp_lead_speeds:
            return False
        m = our_members[slot - 1]
        has_priority = any(
            (move_priority(mv) or 0) > 0 and move_category(mv) != "Status"
            for mv in m.moves
        )
        if has_priority:
            return False
        spe = (m.stats or {}).get("spe", 0)
        return all(spe <= opp_spd for opp_spd in opp_lead_speeds)

    # ── Pick the best lead PAIR over all C(n,2) combinations ──────────────
    # Pair score = (matchup_a + matchup_b) × initiative rows.  With no rows
    # firing the argmax pair is exactly the top-2 individual scores, so the
    # rows only move the choice when initiative is genuinely conceded.
    from itertools import combinations

    best_pair: tuple[int, ...] = tuple(sorted(slots)[:2])
    best_score = float("-inf")
    for a, b in combinations(sorted(slots), 2):
        # Floor the base so the multiplicative penalty cannot *reward* a
        # (rare) negative matchup total.
        base = max(score_by_slot.get(a, 0.0) + score_by_slot.get(b, 0.0), 0.1)
        liabilities = _lead_liability(a) + _lead_liability(b)
        factor = _SLOW_LEAD_FACTOR ** liabilities
        if liabilities == 2 and tw_undeniable:
            factor *= _TW_EXPOSED_FACTOR
        score = base * factor
        if score > best_score:
            best_score, best_pair = score, (a, b)

    leads = sorted(best_pair,
                   key=lambda i: score_by_slot.get(i, 0.0), reverse=True)
    # Preserve the original relative ordering for the back-line so that
    # support/setup mons don't shift unexpectedly.
    back = [s for s in slots if s not in best_pair]

    result = leads + back
    log.info(
        "LEAD ORDER  %s  (leads: %s vs predicted %s%s%s)",
        result,
        [our_members[i - 1].name for i in leads],
        predicted,
        "  [TR expected: slow-lead row waived]" if tr_expected else "",
        "  [undeniable TW on roster]" if tw_undeniable else "",
    )
    return result
