"""tests/test_team_preview.py — Unit tests for team_preview.py

Covers the engine-grounded preview pipeline: select_team / select_leads /
select_mega fallbacks (synthetic members can't resolve through the data
layer, so they exercise the team-order fallbacks), the lead-board eval, the
doomed-lead penalty, and the field-variant gating.  The old type-chart
scoring path (and its tests) was deleted in cleanup C.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch
from typing import Optional

from team import TeamMember
from team_preview import (
    select_team,
    select_leads,
    select_mega,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

_BLANK_SP = {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}


def make_member(
    name: str,
    moves: list[str],
    item: str = "",
    mega_name: Optional[str] = None,
    stats: Optional[dict] = None,
    mega_stats: Optional[dict] = None,
) -> TeamMember:
    """Minimal TeamMember for testing — stats/nature/ability default to blank.

    *stats* / *mega_stats* may be supplied to exercise the stat-ratio demotion
    used when a second Mega-Stone holder cannot mega evolve.
    """
    return TeamMember(
        name=name, item=item, ability="", nature="Hardy",
        sp=_BLANK_SP, moves=moves,
        mega_name=mega_name, stats=stats, mega_stats=mega_stats,
    )


# ══════════════════════════════════════════════════════════════════════════════
# select_team / select_mega — fallbacks (synthetic members can't resolve)
# ══════════════════════════════════════════════════════════════════════════════

class TestSelectTeamFallback:
    """Synthetic members don't resolve through find_member, so the engine
    scores are unavailable and select_team keeps team order (the only
    fallback since the legacy type-chart path was deleted)."""

    def test_no_opponents_returns_first_n_in_order(self):
        members = [make_member(f"Mon{i}", []) for i in range(6)]
        assert select_team([], members, n=4) == [1, 2, 3, 4]

    def test_unresolvable_members_keep_team_order(self):
        members = [make_member(f"Mon{i}", []) for i in range(6)]
        assert select_team(["Opp"], members, n=4) == [1, 2, 3, 4]

    def test_n_larger_than_team_returns_all(self):
        members = [make_member(f"Mon{i}", []) for i in range(3)]
        assert select_team(["Opp"], members, n=6) == [1, 2, 3]


class TestSelectMega:
    """Engine-grounded designation (cleanup C, task #5): the stone holder
    whose engine matchup value gains the most from mega evolving.  Synthetic
    fixtures exercise the fallbacks."""

    def test_no_stone_holder_returns_none(self):
        members = [make_member("A", []), make_member("B", [])]
        assert select_mega([1, 2], members, ["Opp"]) is None

    def test_single_holder_is_trivial(self):
        members = [make_member("A", [], mega_name="A-Mega"), make_member("B", [])]
        assert select_mega([1, 2], members, ["Opp"]) == "A"

    def test_two_holders_unresolvable_falls_back_to_first(self):
        members = [make_member("A", [], mega_name="A-Mega"),
                   make_member("B", [], mega_name="B-Mega")]
        assert select_mega([1, 2], members, ["Opp"]) == "A"

    def test_two_holders_engine_gain_decides(self):
        members = [make_member("A", [], mega_name="A-Mega"),
                   make_member("B", [], mega_name="B-Mega")]
        # B gains 2.0 from its mega; A gains 0.5 → B designated.
        scores = {1: (2.5, 2.0), 2: (3.0, 1.0)}
        with patch("team_preview._engine_matchup_scores", return_value=scores):
            assert select_mega([1, 2], members, ["Opp"]) == "B"


# ══════════════════════════════════════════════════════════════════════════════
# select_leads — fallbacks (no data)
# ══════════════════════════════════════════════════════════════════════════════

class TestSelectLeadsFallback:
    """select_leads falls back to ascending slot order when there is no usable
    lead-frequency data or when the input lists are empty."""

    def test_handles_empty_slots(self):
        result = select_leads([], [], [])
        assert result == []

    def test_handles_empty_opponents(self):
        """No opponent list → early return, ascending slot order."""
        members = [make_member(f"Mon{i}", []) for i in range(2)]
        result  = select_leads([2, 1], members, [])
        assert result == [1, 2]

    def test_no_data_returns_ascending_order(self):
        """When total_battles() == 0 the function should return sorted(slots)."""
        members = [make_member(f"Mon{i}", []) for i in range(4)]
        slots   = [2, 4, 1, 3]
        with patch("data.lead_stats.total_battles", return_value=0):
            result = select_leads(slots, members, ["OppA", "OppB"])
        assert result == sorted(slots)

    def test_data_module_error_returns_ascending_order(self):
        """If the lead_stats import itself raises, fall back gracefully."""
        members = [make_member(f"Mon{i}", []) for i in range(4)]
        slots   = [2, 4, 1, 3]
        # Simulate an ImportError from data.lead_stats
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "data.lead_stats":
                raise ImportError("simulated")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = select_leads(slots, members, ["OppA"])
        assert result == sorted(slots)


# ══════════════════════════════════════════════════════════════════════════════
# Engine-grounded preview evaluation (0.38.0)
# ══════════════════════════════════════════════════════════════════════════════

from team_preview import (
    _eval_lead_board, _score_lead_pairs, _engine_matchup_scores,
    _members_resolvable, _SWITCH_WANT_FACTOR, _ATK_FLOOR,
    _assumed_weather_for_six,
)
from decision.engine import Action


class TestAssumedWeatherForSix:
    """The team-level weather assumption for the bring score — mega-aware via
    assumed_forme, so a weather mega (Char-Y, Froslass-Mega) is caught even
    though its ability lives on the mega forme."""

    def test_base_ability_setters(self):
        assert _assumed_weather_for_six(["Pelipper"]) == "rain"
        assert _assumed_weather_for_six(["Torkoal"]) == "sun"

    def test_mega_ability_setters(self):
        # ability is on the mega forme; assumed_forme resolves to it
        assert _assumed_weather_for_six(["Charizard"]) == "sun"    # Mega-Y Drought
        assert _assumed_weather_for_six(["Froslass"]) == "snow"    # Mega Snow Warning
        assert _assumed_weather_for_six(["Tyranitar"]) == "sand"

    def test_no_setter_is_none(self):
        assert _assumed_weather_for_six(["Incineroar", "Sneasler", "Garchomp"]) is None

    def test_weather_moves_the_bring_score(self):
        from unittest.mock import patch
        from team import get_team
        members = get_team()
        opp = ["Pelipper", "Basculegion", "Archaludon",
               "Rillaboom", "Amoonguss", "Kingambit"]
        rain = _engine_matchup_scores(opp, members)
        with patch("team_preview._assumed_weather_for_six", return_value=None):
            dry = _engine_matchup_scores(opp, members)
        assert rain is not None and dry is not None
        assert rain != dry   # rain-boosted Water changes at least one matchup


class TestExperimentKnobs:
    """The preview experiment knobs (tools/preview_ab.py) — defaults must be
    behavior-neutral; non-defaults must actually move the scores."""

    _OPP = ["Charizard", "Sneasler", "Incineroar",
            "Farigiraf", "Kingambit", "Garchomp"]   # Charizard → Mega-Y assumed

    def test_default_knobs_are_neutral(self):
        """All knobs at their shipped defaults — sanity: they ARE the defaults.
        (_OPP_MEGA_WEIGHT shipped at 1.5 in 0.45.3 after the A/B eyeball.)"""
        import team_preview as tp
        assert tp._OPP_MEGA_WEIGHT == 1.5
        assert (tp._OFF_WEIGHT, tp._DEF_WEIGHT) == (2.0, 1.0)
        assert tp._LEAD_COVERAGE_FACTOR == 1.0
        assert tp._PAIR_PRIOR_POWER == 1.0

    def test_opp_mega_weight_moves_the_bring_score(self):
        from unittest.mock import patch
        from team import get_team
        members = get_team()
        base = _engine_matchup_scores(self._OPP, members)
        with patch("team_preview._OPP_MEGA_WEIGHT", 2.0):
            weighted = _engine_matchup_scores(self._OPP, members)
        assert base is not None and weighted is not None
        assert base != weighted   # the assumed Mega-Y matchup counts double

    def test_off_def_weights_move_the_bring_score(self):
        from unittest.mock import patch
        from team import get_team
        members = get_team()
        base = _engine_matchup_scores(self._OPP, members)
        with patch("team_preview._OFF_WEIGHT", 1.0):
            even = _engine_matchup_scores(self._OPP, members)
        assert base != even

    def test_coverage_factor_fires_on_same_target(self):
        """Both slots' best attack aimed at the same opponent → pair scaled by
        the knob (stub-engine path, mirroring TestEvalLeadBoard)."""
        from unittest.mock import patch
        a0 = Action(label="Hit", move_name="Hit", weight=5.0, target_slot=0)
        b0 = Action(label="Hit", move_name="Hit", weight=4.0, target_slot=0)
        engine = _StubEngine({0: [a0], 1: [b0]})
        lead_a = make_member("MonA", ["Hit"], stats={"hp": 100})
        lead_b = make_member("MonB", ["Hit"], stats={"hp": 100})
        base, _, _ = _eval_lead_board(engine, lead_a, lead_b, [],
                                      ["OppA", "OppB"], None)
        with patch("team_preview._LEAD_COVERAGE_FACTOR", 0.5):
            halved, _, notes = _eval_lead_board(engine, lead_a, lead_b, [],
                                                ["OppA", "OppB"], None)
        assert base == pytest.approx(20.0)          # 5 × 4, no penalty at default
        assert halved == pytest.approx(base * 0.5)
        assert any("same mon" in n for n in notes)


class _StubEngine:
    """scored_actions stub: returns a fixed ranked list per slot."""
    def __init__(self, per_slot: dict[int, list[Action]]):
        self.per_slot = per_slot

    def scored_actions(self, state, slot):
        return self.per_slot.get(slot, [])


def _act(move: str = "", weight: float = 1.0, switch: str = "") -> Action:
    return Action(label=move or f"Switch {switch}", move_name=move,
                  switch_target=switch, weight=weight)


class TestEvalLeadBoard:
    """The per-board scoring mechanism, with a stubbed engine so the ranked
    lists (and therefore the math) are fully controlled."""

    def _members(self):
        a = make_member("MonA", ["Tackle"], stats={"hp": 100})
        b = make_member("MonB", ["Tackle"], stats={"hp": 100})
        return a, b

    def test_pair_score_is_product_of_best_attack_weights(self):
        a, b = self._members()
        eng = _StubEngine({
            0: [_act("Tackle", 4.0), _act("Protect", 9.0)],   # Protect ignored for atk
            1: [_act("Tackle", 3.0)],
        })
        score, vals, notes = _eval_lead_board(eng, a, b, [], ["OppA", "OppB"], None)
        assert score == pytest.approx(12.0)
        assert vals == [4.0, 3.0]
        assert notes == []

    def test_switch_want_penalty_applied_when_switch_outranks_stay(self):
        """The user-observed pathology: correct lead read, engine switches turn
        1.  A slot whose best action is a SWITCH gets ×_SWITCH_WANT_FACTOR."""
        a, b = self._members()
        eng = _StubEngine({
            0: [_act(switch="Backup", weight=8.0), _act("Tackle", 4.0)],
            1: [_act("Tackle", 3.0)],
        })
        score, vals, notes = _eval_lead_board(eng, a, b, [], ["OppA", "OppB"], None)
        assert vals[0] == pytest.approx(4.0 * _SWITCH_WANT_FACTOR)
        assert score == pytest.approx(4.0 * _SWITCH_WANT_FACTOR * 3.0)
        assert any("prefers switching out" in n for n in notes)

    def test_no_penalty_when_stay_action_beats_switch(self):
        a, b = self._members()
        eng = _StubEngine({
            0: [_act("Protect", 9.0), _act(switch="Backup", weight=8.0),
                _act("Tackle", 4.0)],   # Protect (stay) outranks the switch
            1: [_act("Tackle", 3.0)],
        })
        score, vals, notes = _eval_lead_board(eng, a, b, [], ["OppA", "OppB"], None)
        assert vals[0] == pytest.approx(4.0)     # no penalty; atk value used
        assert notes == []

    def test_attackless_slot_floors_not_zeroes(self):
        """A slot with no usable attack must not zero the whole pair."""
        a, b = self._members()
        eng = _StubEngine({
            0: [_act("Protect", 2.0)],
            1: [_act("Tackle", 3.0)],
        })
        score, vals, _ = _eval_lead_board(eng, a, b, [], ["OppA", "OppB"], None)
        assert vals[0] == pytest.approx(_ATK_FLOOR)
        assert score == pytest.approx(_ATK_FLOOR * 3.0)


class TestEnginePreviewIntegration:
    """The engine path end-to-end on the real (baseline) roster — real data,
    structural assertions only (decisions move with usage stats)."""

    _OPP = ["Garchomp", "Whimsicott", "Incineroar", "Farigiraf",
            "Sneasler", "Pelipper"]

    def test_members_resolvable_gates_the_paths(self):
        from team import get_team
        assert _members_resolvable(get_team()) is True
        assert _members_resolvable([make_member("NotARealMon", [])]) is False

    def test_engine_matchup_scores_cover_all_members(self):
        from team import get_team
        members = get_team()
        scores = _engine_matchup_scores(self._OPP, members)
        assert scores is not None and set(scores) == set(range(1, len(members) + 1))
        for i, (mega_val, base_val) in scores.items():
            assert mega_val > 0 and base_val > 0
            if not members[i - 1].mega_name:
                assert mega_val == base_val   # non-holders have one form

    def test_select_team_and_leads_run_engine_path(self):
        from team import get_team
        members = get_team()
        slots = select_team(self._OPP, members, n=4)
        assert len(slots) == 4 and len(set(slots)) == 4
        ordered = select_leads(slots, members, self._OPP)
        assert sorted(ordered) == sorted(slots)   # a permutation of the bring

    def test_score_lead_pairs_scores_every_combination(self):
        from team import get_team
        members = get_team()
        slots = select_team(self._OPP, members, n=4)
        pairs = _score_lead_pairs(slots, members, ["Garchomp", "Whimsicott"],
                                  self._OPP)
        assert pairs is not None and len(pairs) == 6   # C(4,2)
        for (a, b), (score, ordered) in pairs.items():
            assert score > 0
            assert set(ordered) == {a, b}


class TestDoomedLeadPenalty:
    """A lead slot the board facts say is KO'd before acting takes
    ×_DOOMED_LEAD_FACTOR — at preview we can simply not start that mon.
    (v9 audit: Chandelure led into rain on a ×0.2-doomed overkill, 3-15.)"""

    def _members(self):
        a = make_member("MonA", ["Tackle"], stats={"hp": 100})
        b = make_member("MonB", ["Tackle"], stats={"hp": 100})
        return a, b

    def test_doomed_slot_penalised(self):
        from team_preview import _DOOMED_LEAD_FACTOR
        from decision.modules import TurnContext
        a, b = self._members()
        eng = _StubEngine({0: [_act("Tackle", 8.0)], 1: [_act("Tackle", 4.0)]})
        ctx = TurnContext(doomed={0: True, 1: False})
        with patch("decision.modules._ensure_turn_ctx", return_value=ctx):
            score, vals, notes = _eval_lead_board(eng, a, b, [], ["OppA", "OppB"], None)
        assert vals[0] == pytest.approx(8.0 * _DOOMED_LEAD_FACTOR)
        assert vals[1] == pytest.approx(4.0)
        assert any("doomed" in n for n in notes)

    def test_undoomed_board_unpenalised(self):
        from decision.modules import TurnContext
        a, b = self._members()
        eng = _StubEngine({0: [_act("Tackle", 8.0)], 1: [_act("Tackle", 4.0)]})
        ctx = TurnContext(doomed={0: False, 1: False})
        with patch("decision.modules._ensure_turn_ctx", return_value=ctx):
            score, vals, notes = _eval_lead_board(eng, a, b, [], ["OppA", "OppB"], None)
        assert vals == [8.0, 4.0] and notes == []


class TestFieldVariantGating:
    """TR/TW field variants apply only when the PREDICTED PAIR contains the
    setter — a benched setter's field is turns away, and averaging it in let a
    speculative TR board drown the base reality (2401-score doomed pair)."""

    _OPP6 = ["Garchomp", "Whimsicott", "Incineroar", "Farigiraf",
             "Sneasler", "Pelipper"]

    def _count_variants(self, predicted):
        from team import get_team
        import team_preview as tp
        members = get_team()
        slots = [1, 2, 3, 4]
        calls = []
        real = tp._eval_lead_board
        def spy(engine, a, b, bench, opp_pair, mega, **field):
            calls.append(dict(field))
            return real(engine, a, b, bench, opp_pair, mega, **field)
        with patch("team_preview._eval_lead_board", side_effect=spy):
            tp._score_lead_pairs(slots, members, predicted, self._OPP6)
        # variants per pair = total calls / C(4,2)
        return len(calls) // 6, calls

    def test_no_setter_in_predicted_pair_base_board_only(self):
        n, calls = self._count_variants(["Garchomp", "Incineroar"])
        assert n == 1
        assert all(c == {} for c in calls)

    def test_tw_setter_in_predicted_pair_adds_tailwind_variant(self):
        n, calls = self._count_variants(["Garchomp", "Pelipper"])
        assert n == 2
        assert any(c.get("opp_tailwind") for c in calls)

    def test_tr_setter_in_predicted_pair_adds_tr_variant(self):
        n, calls = self._count_variants(["Garchomp", "Farigiraf"])
        assert n == 2
        assert any(c.get("trick_room") for c in calls)
