"""test_recorder.py — Unit tests for recorder.py.

Tests the pure helper functions (_hp_frac, _compact_action, _select_actions)
and the full BattleRecorder round-trip using a temporary directory.
"""
import json
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from recorder import (
    _hp_frac,
    _compact_action,
    _select_actions,
    BattleRecorder,
    _MAX_ACTIONS,
    _MIN_ACTIONS,
)
from decision import Action


# ── _hp_frac ─────────────────────────────────────────────────────────────────

class TestHpFrac:
    def test_full_hp(self):
        assert _hp_frac(300, 300) == 1.0

    def test_half_hp(self):
        assert _hp_frac(150, 300) == 0.5

    def test_zero_hp(self):
        assert _hp_frac(0, 300) == 0.0

    def test_zero_max_hp_guard(self):
        assert _hp_frac(0, 0) == 0.0

    def test_rounds_to_3_decimal_places(self):
        # 1/3 ≈ 0.333
        result = _hp_frac(1, 3)
        assert result == round(1 / 3, 3)

    def test_output_bounded_0_to_1(self):
        result = _hp_frac(200, 300)
        assert 0.0 <= result <= 1.0


# ── _compact_action ───────────────────────────────────────────────────────────

class TestCompactAction:
    def _make(self, label="Dragon Claw", weight=3.5, target_slot=None,
              switch_target="", reasons=None):
        return Action(
            label=label,
            move_name=label,
            weight=weight,
            target_slot=target_slot,
            switch_target=switch_target,
            reasons=reasons or [],
        )

    def test_basic_keys_always_present(self):
        d = _compact_action(self._make())
        assert "lb" in d
        assert "w" in d

    def test_label_stored_as_lb(self):
        d = _compact_action(self._make(label="Wave Crash"))
        assert d["lb"] == "Wave Crash"

    def test_weight_rounded_to_2dp(self):
        d = _compact_action(self._make(weight=3.14159))
        assert d["w"] == 3.14

    def test_target_slot_included_when_set(self):
        d = _compact_action(self._make(target_slot=1))
        assert d["ts"] == 1

    def test_target_slot_omitted_when_none(self):
        d = _compact_action(self._make(target_slot=None))
        assert "ts" not in d

    def test_target_species_resolved_when_opp_list_given(self):
        d = _compact_action(self._make(target_slot=1),
                            opp_species=["Garchomp", "Incineroar"])
        assert d["ts"] == 1
        assert d["tg"] == "Incineroar"

    def test_target_species_omitted_without_opp_list(self):
        d = _compact_action(self._make(target_slot=0))
        assert d["ts"] == 0
        assert "tg" not in d

    def test_target_species_omitted_when_slot_has_no_opp(self):
        # opp slot 1 fainted/empty -> no species to resolve
        d = _compact_action(self._make(target_slot=1),
                            opp_species=["Garchomp", None])
        assert "tg" not in d

    def test_switch_target_included_when_set(self):
        a = Action(label="Switch Sylveon", move_name="", switch_target="Sylveon",
                   weight=2.0)
        d = _compact_action(a)
        assert d["sw"] == "Sylveon"

    def test_switch_target_omitted_when_empty(self):
        d = _compact_action(self._make())
        assert "sw" not in d

    def test_reasons_included_when_present(self):
        a = self._make(reasons=["damage_output: 50% -> x2.0"])
        d = _compact_action(a)
        assert d["r"] == ["damage_output: 50% -> x2.0"]

    def test_reasons_omitted_when_empty(self):
        d = _compact_action(self._make(reasons=[]))
        assert "r" not in d


# ── _select_actions ───────────────────────────────────────────────────────────

class TestSelectActions:
    def _action(self, label, weight):
        return Action(label=label, move_name=label, weight=weight)

    def test_empty_input_returns_empty(self):
        assert _select_actions([]) == []

    def test_chosen_always_included(self):
        """The highest-weight action (ranked[0]) must always appear in output."""
        chosen = self._action("Dragon Claw", 5.0)
        others = [self._action(f"Move{i}", 0.5) for i in range(6)]
        result = _select_actions([chosen] + others)
        labels = [a.label for a in result]
        assert "Dragon Claw" in labels

    def test_chosen_included_even_if_weight_1_0(self):
        """Chosen action with weight=1.0 must be included despite being ≤1.0."""
        actions = [self._action("Protect", 1.0)] + [
            self._action(f"Move{i}", 0.8) for i in range(5)
        ]
        result = _select_actions(actions)
        labels = [a.label for a in result]
        assert "Protect" in labels

    def test_caps_at_max_actions(self):
        """Should return at most _MAX_ACTIONS (4) actions."""
        actions = [self._action(f"Move{i}", float(10 - i)) for i in range(10)]
        result = _select_actions(actions)
        assert len(result) <= _MAX_ACTIONS

    def test_pads_to_min_actions(self):
        """When fewer than _MIN_ACTIONS qualify, pad with next-best actions."""
        # Only chosen action has weight > 1.0
        chosen = self._action("Dragon Claw", 3.0)
        others = [self._action(f"Move{i}", 0.9) for i in range(5)]
        result = _select_actions([chosen] + others)
        assert len(result) >= _MIN_ACTIONS

    def test_output_sorted_descending_weight(self):
        actions = [
            self._action("A", 5.0),
            self._action("B", 8.0),
            self._action("C", 2.0),
        ]
        result = _select_actions(actions)
        weights = [a.weight for a in result]
        assert weights == sorted(weights, reverse=True)

    def test_filters_weight_1_0_actions(self):
        """Actions at exactly weight=1.0 should be excluded from the main pool
        (they may be padded in but only to meet _MIN_ACTIONS)."""
        high = self._action("Best", 15.0)
        med  = self._action("Mid",   3.0)
        low1 = self._action("L1",    1.0)
        low2 = self._action("L2",    1.0)
        low3 = self._action("L3",    1.0)
        result = _select_actions([high, med, low1, low2, low3])
        # High and Mid both have weight > 1.0; Low ones only pad to MIN_ACTIONS
        labels = [a.label for a in result]
        assert "Best" in labels
        assert "Mid"  in labels


# ── BattleRecorder (full round-trip) ─────────────────────────────────────────

def _make_mock_state(turn=1):
    """Build a minimal mock BattleState-like object."""
    state = MagicMock()
    state.turn = turn
    state.weather = None
    state.terrain = None
    state.trick_room = False
    state.my_actives = [MagicMock(species="Garganacl", hp=300, max_hp=300,
                                   status=None)]
    state.opp_actives = [MagicMock(species="Garchomp", hp=175, max_hp=175,
                                    status=None, fainted=False,
                                    moves=["Earthquake"])]
    state.my_team = [MagicMock(species="Garganacl", hp=300, max_hp=300)]
    state.events_log = {}   # real dict (0.8.1) — MagicMock would break _build_turn
    state.predicted_incoming_log = {}   # real dict (0.8.4) — same reason
    return state


def _make_actions():
    return [
        Action(label="Salt Cure", move_name="Salt Cure", weight=8.5,
               target_slot=0, reasons=["damage_output: 60%"]),
        Action(label="Protect", move_name="Protect", weight=3.0,
               reasons=["protect: low HP"]),
        Action(label="Stealth Rock", move_name="Stealth Rock", weight=1.0),
    ]


class TestDataGapsInLog:
    """The optional top-level "data_gaps" field: present only when a data
    lookup failed during the battle, absent on a clean battle."""

    def test_gaps_written_when_lookup_failed(self):
        from data import note_gap

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-gaps-test", "0.7.6")  # init clears
                note_gap("types", "Fakemon-Forme")
                state = _make_mock_state(turn=1)
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=True)

                path = os.path.join(tmpdir, "Battle Data", "0.7.6",
                                    "battle-gaps-test.json")
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                assert data["data_gaps"] == ["types:Fakemon-Forme"]

    def test_no_gaps_key_on_clean_battle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-clean-test", "0.7.6")
                state = _make_mock_state(turn=1)
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=True)

                path = os.path.join(tmpdir, "Battle Data", "0.7.6",
                                    "battle-clean-test.json")
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                assert "data_gaps" not in data

    def test_init_discards_stale_gaps_from_previous_battle(self):
        from data import note_gap

        note_gap("stats", "Stale-Leftover")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-stale-test", "0.7.6")  # clears it
                state = _make_mock_state(turn=1)
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=True)

                path = os.path.join(tmpdir, "Battle Data", "0.7.6",
                                    "battle-stale-test.json")
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                assert "data_gaps" not in data


class TestMoveEventsInLog:
    """The optional per-turn "ev" field carries actual move order + damage
    (0.8.1), read from state.events_log at save time."""

    def test_events_written_to_turn(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-ev-test", "0.8.1")
                state = _make_mock_state(turn=1)
                state.events_log = {1: [
                    {"o": 0, "sd": "us", "a": "Garchomp", "mv": "Earthquake",
                     "tg": "Incineroar", "_tgt_ident": "p2: Incineroar",
                     "hp0": 1.0, "dmg": 0.6},
                    {"o": 1, "sd": "opp", "a": "Incineroar", "mv": "Flare Blitz",
                     "tg": "Garchomp", "_tgt_ident": "p1: Garchomp",
                     "hp0": 1.0, "dmg": 0.25},
                ]}
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=True)
                with open(os.path.join(tmpdir, "Battle Data", "0.8.1",
                                       "battle-ev-test.json"), encoding="utf-8") as f:
                    data = json.load(f)
                ev = data["turns"][0]["ev"]
                assert [e["o"] for e in ev] == [0, 1]
                assert ev[0] == {"o": 0, "sd": "us", "a": "Garchomp",
                                 "mv": "Earthquake", "tg": "Incineroar",
                                 "h0": 1.0, "d": 0.6}
                # internal linkage key must be stripped (raw hp0 renamed to h0)
                assert "_tgt_ident" not in ev[0] and "hp0" not in ev[0]

    def test_crit_flag_and_predicted_incoming_written(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-pin-test", "0.8.4")
                state = _make_mock_state(turn=1)
                state.events_log = {1: [
                    {"o": 0, "sd": "opp", "a": "Incineroar", "mv": "Flare Blitz",
                     "tg": "Garchomp", "_tgt_ident": "p1: Garchomp",
                     "hp0": 1.0, "dmg": 0.9, "crit": True},
                ]}
                state.predicted_incoming_log = {1: [
                    {"a": "Incineroar", "df": "Garchomp", "p": 0.32, "mv": "Flare Blitz"},
                ]}
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=True)
                with open(os.path.join(tmpdir, "Battle Data", "0.8.4",
                                       "battle-pin-test.json"), encoding="utf-8") as f:
                    data = json.load(f)
                turn = data["turns"][0]
                assert turn["ev"][0]["cr"] is True
                assert turn["pin"] == [{"a": "Incineroar", "df": "Garchomp",
                                        "p": 0.32, "mv": "Flare Blitz"}]

    def test_no_ev_key_when_no_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-noev-test", "0.8.1")
                state = _make_mock_state(turn=1)   # events_log = {}
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=True)
                with open(os.path.join(tmpdir, "Battle Data", "0.8.1",
                                       "battle-noev-test.json"), encoding="utf-8") as f:
                    data = json.load(f)
                assert "ev" not in data["turns"][0]


class TestBattleRecorder:
    def test_save_creates_json_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-test-001", "0.3.5")
                state = _make_mock_state(turn=1)
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=True)

                expected_path = os.path.join(tmpdir, "Battle Data", "0.3.5",
                                              "battle-test-001.json")
                assert os.path.exists(expected_path)

    def test_saved_json_has_correct_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-struct-test", "0.3.5")
                state = _make_mock_state(turn=2)
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=False)

                path = os.path.join(tmpdir, "Battle Data", "0.3.5",
                                    "battle-struct-test.json")
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)

                assert data["id"] == "battle-struct-test"
                assert data["v"] == "0.3.5"
                assert data["outcome"] == "loss"
                assert "turns" in data
                assert len(data["turns"]) == 1

    def test_turn_has_correct_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-keys-test", "0.3.5")
                state = _make_mock_state(turn=1)
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=True)

                path = os.path.join(tmpdir, "Battle Data", "0.3.5",
                                    "battle-keys-test.json")
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)

                turn = data["turns"][0]
                assert turn["n"] == 1
                assert "dec" in turn
                assert "my" in turn
                assert "opp" in turn

    def test_chosen_target_species_recorded_as_ct(self):
        """dec.ct resolves the chosen action's target_slot to the opp species."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-ct-test", "0.3.5")
                state = _make_mock_state(turn=1)
                # _make_actions()[0] (Salt Cure, w=8.5) is chosen, target_slot=0,
                # and opp slot 0 is Garchomp.
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=True)

                path = os.path.join(tmpdir, "Battle Data", "0.3.5",
                                    "battle-ct-test.json")
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)

                dec = data["turns"][0]["dec"][0]
                assert dec["ct"] == "Garchomp"

    def test_ct_omitted_when_chosen_action_has_no_target(self):
        """A chosen Protect / switch (target_slot=None) records no ct field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-ct-none-test", "0.3.5")
                state = _make_mock_state(turn=1)
                # Highest-weight action has no target_slot.
                actions = [
                    Action(label="Protect", move_name="Protect", weight=9.0),
                    Action(label="Salt Cure", move_name="Salt Cure", weight=3.0,
                           target_slot=0),
                ]
                rec.record_decision(state, slot=0, ranked_actions=actions)
                rec.record_outcome(won=True)

                path = os.path.join(tmpdir, "Battle Data", "0.3.5",
                                    "battle-ct-none-test.json")
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)

                dec = data["turns"][0]["dec"][0]
                assert dec["ch"] == "Protect"
                assert "ct" not in dec

    def test_decision_uses_abbreviated_action_keys(self):
        """v2 format uses lb/w not label/weight."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-abbrev-test", "0.3.5")
                state = _make_mock_state(turn=1)
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=True)

                path = os.path.join(tmpdir, "Battle Data", "0.3.5",
                                    "battle-abbrev-test.json")
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)

                first_action = data["turns"][0]["dec"][0]["acts"][0]
                assert "lb" in first_action
                assert "w" in first_action
                assert "label" not in first_action
                assert "weight" not in first_action

    def test_no_whitespace_in_output(self):
        """separators=(',',':') produces compact JSON with no structural whitespace.

        We verify this by round-tripping: load the file and re-dump with the same
        separators.  If the two strings match exactly, the file used compact separators.
        Note: we cannot simply check for ': ' or ', ' because those patterns can
        appear inside string values (e.g. reason text like 'damage_output: 60%').
        """
        import json as _json
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-compact-test", "0.3.5")
                state = _make_mock_state(turn=1)
                rec.record_decision(state, slot=0, ranked_actions=_make_actions())
                rec.record_outcome(won=True)

                path = os.path.join(tmpdir, "Battle Data", "0.3.5",
                                    "battle-compact-test.json")
                with open(path, encoding="utf-8") as f:
                    raw = f.read()

                # The file should be a single line (no pretty-print newlines)
                assert "\n" not in raw

                # Re-serialising the parsed data with the same compact separators
                # must produce an identical string — proves no spaces were added.
                data = _json.loads(raw)
                reserialised = _json.dumps(data, separators=(',', ':'), ensure_ascii=False)
                assert raw == reserialised

    def test_outcome_win_and_loss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                for won, expected in [(True, "win"), (False, "loss")]:
                    rec = BattleRecorder(f"battle-outcome-{expected}", "0.3.5")
                    state = _make_mock_state()
                    rec.record_decision(state, 0, _make_actions())
                    rec.record_outcome(won=won)
                    path = os.path.join(tmpdir, "Battle Data", "0.3.5",
                                        f"battle-outcome-{expected}.json")
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                    assert data["outcome"] == expected

    def test_hp_stored_as_fraction(self):
        """HP must be stored as 0–1 float, not as 'cur/max' string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("recorder._PROJECT_ROOT", tmpdir):
                rec = BattleRecorder("battle-hp-test", "0.3.5")
                state = _make_mock_state(turn=1)
                # Set our active at 150/300 = 0.5
                state.my_actives[0].hp = 150
                state.my_actives[0].max_hp = 300
                rec.record_decision(state, 0, _make_actions())
                rec.record_outcome(won=True)

                path = os.path.join(tmpdir, "Battle Data", "0.3.5",
                                    "battle-hp-test.json")
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)

                hp_val = data["turns"][0]["my"][0]["hp"]
                assert isinstance(hp_val, float)
                assert hp_val == 0.5
