"""team_preview.py — Team selection for VGC team preview.

Two-stage process:

1. :func:`select_team`  — Choose which Pokémon to bring, scored by type matchups.
2. :func:`select_leads` — Determine lead order (stub; not yet implemented).

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

from data import types_of, move_type, move_category, ability_of, all_pokemon, get_sets
from damage import type_effectiveness
from team import TeamMember

log = logging.getLogger(__name__)

# ── Tuning constants ──────────────────────────────────────────────────────────

_OFFENSE_WEIGHT = 2.0   # multiplier for offensive coverage in the combined score
_DEFENSE_WEIGHT = 1.0   # multiplier for defensive durability in the combined score
_IMMUNITY_BONUS = 4.0   # defensive contribution when completely immune to a type

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
    """
    if "-Mega" in mega_name:
        return mega_name.split("-Mega")[0]
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

    Args:
        opp_species_list: Species names of the opponent's revealed preview team.
        our_members:      Full six-member team (from :func:`team.get_team`).
        n:                Number of Pokémon to bring (default 4 for VGC).

    Returns:
        List of *n* 1-based slot indices, leads-first.
    """
    scored = score_members(opp_species_list, our_members)
    top = scored[:n]
    return [s.index for s in top]


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
    most likely to be led, then reorders *slots* so that our best type-matchup
    counters to those two predicted leads go first.

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
        from data.lead_stats import lead_frequency, total_battles as _total
        has_data = _total() > 0
    except Exception:
        has_data = False

    if not has_data:
        log.info("LEAD ORDER  %s  (no lead data, using original order)", sorted(slots))
        return sorted(slots)

    # ── Predict the 2 most likely opponent leads ──────────────────────────
    predicted = sorted(
        opp_species_list,
        key=lambda s: lead_frequency(s),
        reverse=True,
    )[:2]
    log.info("PREDICTED OPP LEADS  %s", predicted)

    # ── Score our bring list against the predicted leads ──────────────────
    all_scores    = score_members(predicted, our_members)
    score_by_slot = {s.index: s.combined for s in all_scores}

    # Sort by matchup score vs predicted leads, best first.
    slots_ranked = sorted(
        slots,
        key=lambda i: score_by_slot.get(i, 0.0),
        reverse=True,
    )
    leads = slots_ranked[:2]
    back  = slots_ranked[2:]

    # Preserve the original relative ordering for the back-line so that
    # support/setup mons don't shift unexpectedly.
    original_order = {s: i for i, s in enumerate(slots)}
    back.sort(key=lambda s: original_order[s])

    result = leads + back
    log.info(
        "LEAD ORDER  %s  (leads: %s vs predicted %s)",
        result,
        [our_members[i - 1].name for i in leads],
        predicted,
    )
    return result
