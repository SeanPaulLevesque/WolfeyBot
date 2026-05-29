"""tests/test_team_preview.py — Unit tests for team_preview.py

Covers the scoring helpers, score_members, select_team, and select_leads stub.

All data-layer calls (types_of, move_type) are patched so tests are fully
deterministic and require no database files.  type_effectiveness is NOT
patched — it's a pure dict lookup with no I/O, so letting it run for real
keeps the assertions meaningful.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch
from typing import Optional

from team import TeamMember
from team_preview import (
    MemberScore,
    _IMMUNITY_BONUS,
    _OFFENSE_WEIGHT,
    _DEFENSE_WEIGHT,
    _move_types,
    _defensive_types,
    _offensive_score,
    _defensive_score,
    score_members,
    select_team,
    select_leads,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

_BLANK_SP = {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}


def make_member(
    name: str,
    moves: list[str],
    item: str = "",
    mega_name: Optional[str] = None,
) -> TeamMember:
    """Minimal TeamMember for testing — stats/nature/ability don't matter here."""
    return TeamMember(
        name=name, item=item, ability="", nature="Hardy",
        sp=_BLANK_SP, moves=moves,
        mega_name=mega_name,
    )


# ══════════════════════════════════════════════════════════════════════════════
# _move_types
# ══════════════════════════════════════════════════════════════════════════════

class TestMoveTypes:
    def test_returns_frozenset_of_move_types(self):
        lookup = {"Flamethrower": "Fire", "Earthquake": "Ground"}
        with patch("team_preview.move_type", side_effect=lookup.get):
            member = make_member("Arcanine", ["Flamethrower", "Earthquake"])
            result = _move_types(member)
        assert result == frozenset({"Fire", "Ground"})

    def test_unknown_move_types_excluded(self):
        """Moves not in the database return None and must be silently skipped."""
        with patch("team_preview.move_type", return_value=None):
            member = make_member("Garganacl", ["Salt Cure"])
            result = _move_types(member)
        assert result == frozenset()

    def test_duplicate_types_deduplicated(self):
        """Two moves of the same type should appear only once in the frozenset."""
        with patch("team_preview.move_type", return_value="Fire"):
            member = make_member("Arcanine", ["Flamethrower", "Fire Fang", "Heat Wave"])
            result = _move_types(member)
        assert result == frozenset({"Fire"})

    def test_empty_moveset_returns_empty(self):
        member = make_member("Garganacl", [])
        result = _move_types(member)
        assert result == frozenset()


# ══════════════════════════════════════════════════════════════════════════════
# _defensive_types
# ══════════════════════════════════════════════════════════════════════════════

class TestDefensiveTypes:
    def test_base_form_returns_own_types(self):
        with patch("team_preview.types_of", return_value=["Rock"]):
            member = make_member("Garganacl", [])
            result = _defensive_types(member)
        assert result == ["Rock"]

    def test_mega_form_preferred_over_base(self):
        """A mon with a Mega Stone should use the mega form's typing."""
        def fake_types(name):
            return {"Lopunny-Mega": ["Normal", "Fighting"], "Lopunny": ["Normal"]}.get(name)

        with patch("team_preview.types_of", side_effect=fake_types):
            member = make_member("Lopunny", [], mega_name="Lopunny-Mega")
            result = _defensive_types(member)
        assert result == ["Normal", "Fighting"]

    def test_falls_back_to_base_when_mega_unknown(self):
        """If the mega form isn't in the database, fall back to base typing."""
        def fake_types(name):
            return None if "Mega" in name else ["Normal"]

        with patch("team_preview.types_of", side_effect=fake_types):
            member = make_member("Lopunny", [], mega_name="Lopunny-Mega")
            result = _defensive_types(member)
        assert result == ["Normal"]

    def test_falls_back_to_normal_when_species_unknown(self):
        """Species not in the database should default to ['Normal']."""
        with patch("team_preview.types_of", return_value=None):
            member = make_member("MadeUpMon", [])
            result = _defensive_types(member)
        assert result == ["Normal"]


# ══════════════════════════════════════════════════════════════════════════════
# _offensive_score
# ══════════════════════════════════════════════════════════════════════════════

class TestOffensiveScore:
    def test_se_moves_score_higher_than_resisted(self):
        """Fire moves vs Grass/Steel should score much higher than Normal moves."""
        fire_member   = make_member("Arcanine",  ["Flamethrower"])
        normal_member = make_member("Garganacl", ["Tackle"])

        def fake_move_type(m):
            return {"Flamethrower": "Fire", "Tackle": "Normal"}.get(m)
        def fake_types_of(s):
            return {"Ferrothorn": ["Grass", "Steel"]}.get(s, ["Normal"])

        with patch("team_preview.move_type",  side_effect=fake_move_type), \
             patch("team_preview.types_of",   side_effect=fake_types_of):
            fire_score   = _offensive_score(fire_member,   ["Ferrothorn"])
            normal_score = _offensive_score(normal_member, ["Ferrothorn"])

        # Fire vs Grass/Steel = ×4.0; Normal vs Grass/Steel = ×0.5
        assert fire_score > normal_score

    def test_best_coverage_used_per_opponent(self):
        """Takes max effectiveness across all move types, not the first match."""
        member = make_member("Excadrill", ["Earthquake", "Rock Slide"])
        # Rock/Dark: Ground ×2.0 (best), Rock ×1.0 (neutral to Dark, neutral to Rock is ×1.0? let me verify)
        # Actually: Ground vs Rock = ×2.0, Ground vs Dark = ×1.0 → combined ×2.0
        #           Rock vs Rock = ×1.0, Rock vs Dark = ×1.0 → combined ×1.0
        # Best = Ground = ×2.0

        def fake_move_type(m):
            return {"Earthquake": "Ground", "Rock Slide": "Rock"}.get(m)
        def fake_types_of(s):
            return ["Rock", "Dark"]  # Tyranitar

        with patch("team_preview.move_type", side_effect=fake_move_type), \
             patch("team_preview.types_of",  side_effect=fake_types_of):
            score = _offensive_score(member, ["Tyranitar"])

        assert score == pytest.approx(2.0)

    def test_no_recognised_move_types_returns_neutral(self):
        """A mon with no moves in the database gets 1.0 per opponent (neutral floor)."""
        with patch("team_preview.move_type", return_value=None):
            member = make_member("Garganacl", ["Salt Cure", "Recover"])
            score  = _offensive_score(member, ["OppA", "OppB"])
        assert score == pytest.approx(2.0)

    def test_empty_opponent_list_returns_zero(self):
        with patch("team_preview.move_type", return_value="Fire"):
            member = make_member("Arcanine", ["Flamethrower"])
            score  = _offensive_score(member, [])
        assert score == pytest.approx(0.0)

    def test_summed_across_multiple_opponents(self):
        """Scores are summed across all opponents, not just the first."""
        member = make_member("Charizard", ["Flamethrower"])

        def fake_move_type(m): return "Fire"
        def fake_types_of(s):
            # Ferrothorn: Fire ×4.0; Rotom-Wash: Fire ×0.5
            return {"Ferrothorn": ["Grass", "Steel"], "Rotom-Wash": ["Electric", "Water"]}.get(s, ["Normal"])

        with patch("team_preview.move_type", side_effect=fake_move_type), \
             patch("team_preview.types_of",  side_effect=fake_types_of):
            score = _offensive_score(member, ["Ferrothorn", "Rotom-Wash"])

        # Fire vs Grass/Steel = ×4.0 + Fire vs Electric/Water = ×0.5 = 4.5
        assert score == pytest.approx(4.5)


# ══════════════════════════════════════════════════════════════════════════════
# _defensive_score
# ══════════════════════════════════════════════════════════════════════════════

class TestDefensiveScore:
    def test_immunity_gives_maximum_contribution(self):
        """Ground-type immunity to Electric → _IMMUNITY_BONUS contribution."""
        def fake_types_of(s):
            return {"Garchomp": ["Dragon", "Ground"], "Raichu": ["Electric"]}.get(s, ["Normal"])

        with patch("team_preview.types_of", side_effect=fake_types_of):
            member = make_member("Garchomp", [])
            score  = _defensive_score(member, ["Raichu"])

        assert score == pytest.approx(_IMMUNITY_BONUS)

    def test_weakness_scores_lower_than_immunity(self):
        """A Water-type weak to Electric scores lower than a Ground-type (immune)."""
        def fake_types_of(s):
            return {
                "Gyarados":  ["Water", "Flying"],   # Electric ×2.0 (via Flying)
                "Garchomp":  ["Dragon", "Ground"],  # Electric ×0.0 (immune)
                "Raichu":    ["Electric"],
            }.get(s, ["Normal"])

        with patch("team_preview.types_of", side_effect=fake_types_of):
            gyarados_score = _defensive_score(make_member("Gyarados", []),  ["Raichu"])
            garchomp_score = _defensive_score(make_member("Garchomp", []), ["Raichu"])

        assert garchomp_score > gyarados_score

    def test_resist_scores_higher_than_neutral(self):
        """A resist (×0.5) gives contribution 2.0, neutral (×1.0) gives 1.0."""
        # Grass resists Water (Water vs Grass = ×0.5); Normal is neutral to Water.
        def fake_types_of(s):
            if s == "Resister": return ["Grass"]   # Water vs Grass = ×0.5 (resist)
            if s == "Neutral":  return ["Normal"]  # Water vs Normal = ×1.0 (neutral)
            return ["Water"]  # opponent STAB type

        with patch("team_preview.types_of", side_effect=fake_types_of):
            resister_score = _defensive_score(make_member("Resister", []), ["WaterOpp"])
            neutral_score  = _defensive_score(make_member("Neutral",  []), ["WaterOpp"])

        assert resister_score > neutral_score
        assert resister_score == pytest.approx(2.0)  # 1 / 0.5
        assert neutral_score  == pytest.approx(1.0)  # 1 / 1.0

    def test_summed_across_multiple_opponents(self):
        """Defensive score sums contributions from every opponent."""
        def fake_types_of(s):
            return {
                "Defender": ["Dragon", "Ground"],
                "OppA":     ["Electric"],   # Electric vs Dragon/Ground = ×0.0 (immune) → +4.0
                "OppB":     ["Ice"],        # Ice vs Dragon = ×2.0, Ice vs Ground = ×2.0 → ×4.0 → +0.25
            }.get(s, ["Normal"])

        with patch("team_preview.types_of", side_effect=fake_types_of):
            score = _defensive_score(make_member("Defender", []), ["OppA", "OppB"])

        assert score == pytest.approx(_IMMUNITY_BONUS + 0.25)  # 4.0 + 0.25 = 4.25


# ══════════════════════════════════════════════════════════════════════════════
# MemberScore
# ══════════════════════════════════════════════════════════════════════════════

class TestMemberScore:
    def test_combined_uses_correct_weights(self):
        s = MemberScore(index=1, member=make_member("X", []), offense=3.0, defense=2.0)
        expected = _OFFENSE_WEIGHT * 3.0 + _DEFENSE_WEIGHT * 2.0
        assert s.combined == pytest.approx(expected)

    def test_combined_zero_when_both_zero(self):
        s = MemberScore(index=1, member=make_member("X", []), offense=0.0, defense=0.0)
        assert s.combined == pytest.approx(0.0)


# ══════════════════════════════════════════════════════════════════════════════
# score_members
# ══════════════════════════════════════════════════════════════════════════════

class TestScoreMembers:
    def test_returns_entry_for_every_member(self):
        members = [make_member(f"Mon{i}", []) for i in range(6)]
        with patch("team_preview.move_type", return_value=None), \
             patch("team_preview.types_of",  return_value=["Normal"]):
            scores = score_members(["Opp"], members)
        assert len(scores) == 6

    def test_empty_opponents_preserves_team_order_with_zero_scores(self):
        members = [make_member(f"Mon{i}", []) for i in range(4)]
        scores  = score_members([], members)
        assert [s.index for s in scores] == [1, 2, 3, 4]
        assert all(s.offense == 0.0 and s.defense == 0.0 for s in scores)

    def test_sorted_best_first(self):
        """The member with the highest combined score must appear first."""
        fire_member   = make_member("Arcanine",  ["Flamethrower"])
        normal_member = make_member("Garganacl", ["Tackle"])

        def fake_move_type(m):
            return {"Flamethrower": "Fire", "Tackle": "Normal"}.get(m)
        def fake_types_of(s):
            return ["Grass", "Steel"]   # all species share the same types for simplicity

        with patch("team_preview.move_type", side_effect=fake_move_type), \
             patch("team_preview.types_of",  side_effect=fake_types_of):
            scores = score_members(["Ferrothorn"], [normal_member, fire_member])

        # Fire vs Grass/Steel = ×4.0 >> Normal ×0.5; Arcanine must be first
        assert scores[0].member.name == "Arcanine"

    def test_indices_are_1_based(self):
        members = [make_member(f"Mon{i}", []) for i in range(3)]
        with patch("team_preview.move_type", return_value=None), \
             patch("team_preview.types_of",  return_value=["Normal"]):
            scores = score_members(["Opp"], members)
        assert all(s.index >= 1 for s in scores)


# ══════════════════════════════════════════════════════════════════════════════
# select_team
# ══════════════════════════════════════════════════════════════════════════════

class TestSelectTeam:
    def test_returns_n_slots(self):
        members = [make_member(f"Mon{i}", []) for i in range(6)]
        with patch("team_preview.move_type", return_value=None), \
             patch("team_preview.types_of",  return_value=["Normal"]):
            result = select_team(["Opp"], members, n=4)
        assert len(result) == 4

    def test_returns_1_based_indices(self):
        members = [make_member(f"Mon{i}", []) for i in range(6)]
        with patch("team_preview.move_type", return_value=None), \
             patch("team_preview.types_of",  return_value=["Normal"]):
            result = select_team(["Opp"], members, n=4)
        assert all(1 <= idx <= 6 for idx in result)

    def test_no_opponents_returns_first_n_in_order(self):
        """Empty opponent list → no scoring → first n slots by team order."""
        members = [make_member(f"Mon{i}", []) for i in range(6)]
        result  = select_team([], members, n=4)
        assert result == [1, 2, 3, 4]

    def test_best_scorer_is_first_lead(self):
        """Highest combined-score member should occupy slot 0 (lead position)."""
        weak   = make_member("Weak",   ["Tackle"])        # index 1 — Normal moves
        strong = make_member("Strong", ["Flamethrower"])  # index 2 — Fire moves, SE coverage

        def fake_move_type(m):
            return {"Tackle": "Normal", "Flamethrower": "Fire"}.get(m)
        def fake_types_of(s):
            return ["Grass", "Steel"]   # Fire ×4.0, Normal ×0.5

        with patch("team_preview.move_type", side_effect=fake_move_type), \
             patch("team_preview.types_of",  side_effect=fake_types_of):
            result = select_team(["Ferrothorn"], [weak, strong], n=2)

        assert result[0] == 2   # strong is 1-based index 2

    def test_n_larger_than_team_returns_all(self):
        """Requesting more slots than the team has should not crash."""
        members = [make_member(f"Mon{i}", []) for i in range(3)]
        with patch("team_preview.move_type", return_value=None), \
             patch("team_preview.types_of",  return_value=["Normal"]):
            result = select_team(["Opp"], members, n=6)
        assert len(result) == 3

    def test_all_indices_unique(self):
        """No duplicate slots should appear in the output."""
        members = [make_member(f"Mon{i}", []) for i in range(6)]
        with patch("team_preview.move_type", return_value=None), \
             patch("team_preview.types_of",  return_value=["Normal"]):
            result = select_team(["Opp"], members, n=4)
        assert len(result) == len(set(result))

    def test_offense_is_primary_over_defense(self):
        """A mon with stronger offense beats one with stronger defense when their
        offense difference outweighs the defense difference."""
        # offensive_A = 4.0, defensive_A = 1.0  → combined = 2*4 + 1*1 = 9.0
        # offensive_B = 1.0, defensive_B = 3.0  → combined = 2*1 + 1*3 = 5.0
        # A should win despite B having better defense.

        mon_a = make_member("MonA", ["Flamethrower"])   # Fire = ×4.0 vs Grass/Steel
        mon_b = make_member("MonB", ["Tackle"])          # Normal = ×0.5 vs Grass/Steel

        def fake_move_type(m):
            return {"Flamethrower": "Fire", "Tackle": "Normal"}.get(m)
        def fake_types_of(s):
            # MonA: Steel typing → resists most things; MonB: Grass/Steel too
            # but we just care that A has better offense
            if s == "Ferrothorn": return ["Grass", "Steel"]
            return ["Normal"]

        with patch("team_preview.move_type", side_effect=fake_move_type), \
             patch("team_preview.types_of",  side_effect=fake_types_of):
            result = select_team(["Ferrothorn"], [mon_b, mon_a], n=2)

        assert result[0] == 2   # mon_a is slot 2


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
# select_leads — with lead frequency data
# ══════════════════════════════════════════════════════════════════════════════

class TestSelectLeadsWithData:
    """select_leads reorders leads by predicted matchup when data is available."""

    @staticmethod
    def _patch_lead_data(frequencies: dict[str, int], total: int = 10):
        """Return a context-manager that mocks lead_frequency and total_battles."""
        from unittest.mock import patch as _patch

        def fake_frequency(species):
            return frequencies.get(species, 0)

        return (
            _patch("data.lead_stats.lead_frequency", side_effect=fake_frequency),
            _patch("data.lead_stats.total_battles", return_value=total),
        )

    def test_best_counter_placed_first(self):
        """The slot with the best matchup vs predicted leads goes to position 0."""
        # Mon1 (slot 1): Fire moves — great vs Grass/Steel
        # Mon2 (slot 2): Normal moves — bad vs Grass/Steel
        mon1 = make_member("FireMon",   ["Flamethrower"])
        mon2 = make_member("NormalMon", ["Tackle"])
        members = [mon1, mon2]  # team slots 1 and 2

        def fake_move_type(m):
            return {"Flamethrower": "Fire", "Tackle": "Normal"}.get(m)
        def fake_types_of(s):
            return ["Grass", "Steel"]   # Ferrothorn typing for all lookups

        # OppA is seen most often as a lead (freq=8), OppB less (freq=2)
        freqs = {"OppA": 8, "OppB": 2}

        p1, p2, p3 = (
            patch("data.lead_stats.lead_frequency",
                  side_effect=lambda s: freqs.get(s, 0)),
            patch("data.lead_stats.total_battles", return_value=10),
            patch("team_preview.move_type", side_effect=fake_move_type),
        )
        with p1, p2, p3, patch("team_preview.types_of", side_effect=fake_types_of):
            result = select_leads([1, 2], members, ["OppA", "OppB"])

        # FireMon (slot 1) should lead because it counters Grass/Steel better
        assert result[0] == 1

    def test_predicted_leads_use_highest_frequency_pair(self):
        """Exactly the top-2 by frequency are used as the prediction targets."""
        # Three opp species — only the top 2 by frequency should be predicted
        # OppA=5, OppB=3, OppC=1 → predicted = [OppA, OppB]
        freqs = {"OppA": 5, "OppB": 3, "OppC": 1}
        predicted_used: list[list[str]] = []

        original_score = __import__("team_preview").score_members

        def capture_score(opp_list, members):
            predicted_used.append(list(opp_list))
            return original_score(opp_list, members)

        members = [make_member(f"Mon{i}", []) for i in range(4)]
        slots   = [1, 2, 3, 4]

        with patch("data.lead_stats.lead_frequency",
                   side_effect=lambda s: freqs.get(s, 0)), \
             patch("data.lead_stats.total_battles", return_value=10), \
             patch("team_preview.score_members", side_effect=capture_score), \
             patch("team_preview.move_type", return_value=None), \
             patch("team_preview.types_of",  return_value=["Normal"]):
            select_leads(slots, members, ["OppC", "OppA", "OppB"])

        # score_members should have been called with [OppA, OppB] (top 2 by freq)
        assert predicted_used, "score_members was never called"
        assert set(predicted_used[0]) == {"OppA", "OppB"}

    def test_back_line_preserves_original_relative_order(self):
        """After picking the 2 leads, back-line slots keep their original order."""
        # All members score equally (flat) so lead selection is effectively
        # arbitrary — we only care that the back-line stays in original order.
        members = [make_member(f"Mon{i}", []) for i in range(4)]
        original_slots = [3, 1, 4, 2]   # original order

        with patch("data.lead_stats.lead_frequency", return_value=1), \
             patch("data.lead_stats.total_battles", return_value=10), \
             patch("team_preview.move_type", return_value=None), \
             patch("team_preview.types_of",  return_value=["Normal"]):
            result = select_leads(list(original_slots), members, ["OppA"])

        # Positions 2+ (back-line) should respect the original relative order
        leads_set = set(result[:2])
        back      = result[2:]
        # Build the expected back order: slots not in leads, in original slot order
        expected_back = [s for s in original_slots if s not in leads_set]
        assert back == expected_back

    def test_result_contains_all_original_slots(self):
        """No slot should be added or dropped."""
        members = [make_member(f"Mon{i}", []) for i in range(4)]
        slots   = [2, 4, 1, 3]

        with patch("data.lead_stats.lead_frequency", return_value=1), \
             patch("data.lead_stats.total_battles", return_value=10), \
             patch("team_preview.move_type", return_value=None), \
             patch("team_preview.types_of",  return_value=["Normal"]):
            result = select_leads(list(slots), members, ["OppA"])

        assert sorted(result) == sorted(slots)
