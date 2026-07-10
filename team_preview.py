"""team_preview.py — Team selection for VGC team preview.

Everything here is **engine-grounded** (0.38.0+): the bring-4, the lead pair,
and the designated mega are all chosen by building real turn-1 boards /
matchup calcs and reading the same phase-1 weights and damage facts the
in-battle engine uses.

Two-stage process:

1. :func:`select_team`  — Choose which Pokémon to bring: per-member engine
   damage matchups vs the opponent's six, with native one-mega demotion.
2. :func:`select_leads` — Pick the best lead *pair*: hedged engine board eval
   against the top-K likely opponent pairs, × the empirical pair prior.

Usage::

    from team_preview import select_team, select_leads
    from team import get_team

    slots   = select_team(opp_species, get_team(), n=4)
    ordered = select_leads(slots, get_team(), opp_species)
"""
from __future__ import annotations

import logging
import math
from typing import Optional

from team import TeamMember

log = logging.getLogger(__name__)


# ── Engine-grounded preview evaluation (0.38.0) ──────────────────────────────
# Preview decisions are scored with the same engine that plays the game: build
# the turn-1 board and read the phase-1 weights / damage facts directly.  (The
# old type-chart parallel model — crude multipliers blind to real damage, OHKO
# thresholds, Fake Out and turn order — was deleted in cleanup C; unresolvable
# members now just keep team order.)

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
                      predicted, opp_species_list: list[str],
                      ) -> Optional[dict[tuple[int, int], float]]:
    """Engine-grounded score for every C(n,2) lead pair from *slots*.

    *predicted* is either one opponent pair (``["Swampert", "Pelipper"]``) or
    the **hedged** form: a list of ``(pair, weight)`` from
    ``lead_stats.predict_pairs``.  Each of our candidate pairs is scored
    against every predicted opponent pair and combined as the **weighted
    geometric mean** — board scores are multiplicative kill-stacks spanning
    orders of magnitude, so an arithmetic mean would let a low-probability
    jackpot board outvote a likely disaster (observed: a doubly-doomed pair
    won the argmax on a 0.09-weight blowout).  Log-space averaging keeps the
    likely board decisive while still crediting a lead that's merely doomed
    against one read (correct single-pair predictions were LOSING 43% vs 52%
    over the v9 batch).

    Field variants (per opponent pair): the base board, plus a Trick-Room-on
    board when that pair contains a TR setter and an opponent-Tailwind board
    when it contains a TW setter — averaged, so initiative under the imminent
    game plan is priced by the *real* turn-order model.  Variants are keyed on
    the pair, not the roster: a benched setter's field is turns away, and
    averaging it in let a speculative TR board drown the base reality.
    Returns None when the engine path is unavailable (unresolvable members)."""
    if not _members_resolvable([our_members[i - 1] for i in slots]):
        return None
    try:
        from decision.modules import (
            make_engine, _is_tr_setter, _is_tw_setter,
        )
    except Exception:
        return None

    # Normalize: a flat species pair means "one prediction, full weight".
    if predicted and isinstance(predicted[0], str):
        hedge: list[tuple[list, float]] = [(list(predicted), 1.0)]
    else:
        hedge = list(predicted)
    if not hedge:
        return None

    def _variants_for(opp_pair) -> list[dict]:
        out: list[dict] = [{}]
        if any(_is_tr_setter(_preview_opp_mon(s)) for s in opp_pair):
            out.append({"trick_room": True})
        if any(_is_tw_setter(_preview_opp_mon(s)) for s in opp_pair):
            out.append({"opp_tailwind": True})
        return out

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
        log_score = 0.0
        vals = [0.0, 0.0]
        all_notes: list[str] = []
        for opp_pair, weight in hedge:
            variants = _variants_for(opp_pair)
            total = 0.0
            for field in variants:
                sc, sv, notes = _eval_lead_board(engine, ma, mb, bench,
                                                 opp_pair, mega, **field)
                total += sc
                vals[0] += weight * sv[0]
                vals[1] += weight * sv[1]
                all_notes += notes
            log_score += weight * math.log(max(total / len(variants), 1e-6))
        score = math.exp(log_score)
        if team_spec is not None:
            prior = pair_factor(team_spec, ma.name, mb.name)
            if prior != 1.0:
                score *= prior
                all_notes.append(f"pair prior x{prior:.2f}")
        # Stronger slot value leads first (position is mostly cosmetic, but it
        # keeps the log readable and matches the old score-ordered convention).
        ordered = (a, b) if vals[0] >= vals[1] else (b, a)
        scores[(a, b)] = (score, ordered)
        # De-duplicate notes (the same note can fire on several boards).
        uniq = list(dict.fromkeys(all_notes))
        log.info("  LEAD EVAL  %s+%s  score=%.3f%s",
                 ma.name, mb.name, score,
                 ("  [" + "; ".join(uniq) + "]") if uniq else "")
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
        # offense ×2 + defense ×1 — the weighting the legacy scorer used,
        # kept as the engine combiner's own constants since cleanup C.
        return 2.0 * (off_total / n) + 1.0 * (def_total / n)

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

    # ── No engine scores (unresolvable members — synthetic fixtures only) ─
    # Real teams always resolve via find_member; the old type-chart fallback
    # was deleted with the rest of the legacy scoring (cleanup C).
    log.warning("TEAM SELECT: engine scores unavailable, using team order")
    return list(range(1, len(our_members) + 1))[:n]


def select_mega(
    slots: list[int],
    our_members: list[TeamMember],
    opp_species_list: list[str],
) -> Optional[str]:
    """Choose which brought stone holder mega evolves this battle.

    Engine-grounded (cleanup C, completing task #5): among the brought stone
    holders, designate the one whose **engine matchup value gains the most
    from mega evolving** — ``mega_val − base_val`` from
    :func:`_engine_matchup_scores` (real damage in and out, stat- and
    ability-aware) — with the higher absolute mega value as the tiebreak.
    Replaces the old defensive type-delta ranking, which was ≈0 for most
    stones (a speed/power mega gains nothing defensively).

    Returns the base species name of the designated mega, or ``None`` when
    no brought member carries a Mega Stone.  Falls back to the first stone
    holder in the bring when engine scores are unavailable (no opponent
    data / synthetic fixtures).
    """
    holders = [s for s in slots if our_members[s - 1].mega_name]
    if not holders:
        return None
    if len(holders) > 1 and opp_species_list:
        scores = _engine_matchup_scores(opp_species_list, our_members)
        if scores is not None:
            def _gain(s: int) -> tuple[float, float]:
                mega_val, base_val = scores[s]
                return (mega_val - base_val, mega_val)
            holders.sort(key=_gain, reverse=True)
            log.info(
                "TEAM PREVIEW  designated mega: %s  (candidates: %s)",
                our_members[holders[0] - 1].name,
                [(our_members[s - 1].name,
                  f"gain={scores[s][0] - scores[s][1]:.2f}") for s in holders],
            )
            return our_members[holders[0] - 1].name
    designated = our_members[holders[0] - 1].name
    log.info("TEAM PREVIEW  designated mega: %s", designated)
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
    # switch OUT, that lead pair is self-refuting.  Since 0.40.0 the eval is
    # HEDGED: each candidate is scored against the top-K likely opponent
    # pairs weighted by co-lead evidence (predict_pairs), not a single
    # committed read — over-committing to one pair is how correct predictions
    # were still losing.  TR/TW field variants apply per opponent pair.
    try:
        from data.lead_stats import predict_pairs
        hedge = predict_pairs(opp_species_list)
    except Exception:
        hedge = [(predicted, 1.0)] if len(predicted) == 2 else []
    if hedge:
        log.info("HEDGED OPP PAIRS  %s",
                 [(" + ".join(p), round(w, 2)) for p, w in hedge])
        pair_scores = _score_lead_pairs(slots, our_members, hedge,
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

    # ── No engine eval (unresolvable members — synthetic fixtures only) ───
    # The engine board eval is the one real selector since 0.38.0; the old
    # type-chart + initiative fallback was deleted with the rest of the
    # legacy scoring (cleanup C).  Keep the bring order.
    result = sorted(slots)
    log.info("LEAD ORDER  %s  (engine eval unavailable, keeping bring order)",
             result)
    return result
