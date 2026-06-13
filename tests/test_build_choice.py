"""test_build_choice.py — Tests for _build_choice() in main.py.

Covers the force-switch path specifically: verifies that the decision engine
is consulted for type-matchup scoring rather than defaulting to the first
available bench slot in team order.

NOTE: importing main triggers PACKED_TEAM = to_packed() at module level.
That reads team.txt — if the file is absent the import will fail.  All
test functions use deferred imports (inside the function body) so that the
test *collection* phase still works even in environments without team.txt;
only the running of these tests requires it.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch
from typing import Optional

from battle import BattleState, Pokemon
from decision import Action


# ── Fixture helpers ───────────────────────────────────────────────────────────

def _pokemon(
    species: str,
    hp: int = 300,
    max_hp: int = 300,
    fainted: bool = False,
    side: str = "p1",
) -> Pokemon:
    return Pokemon(
        ident=f"{side}: {species}",
        species=species,
        hp=hp,
        max_hp=max_hp,
        fainted=fainted,
        boosts={
            "atk": 0, "def": 0, "spa": 0, "spd": 0,
            "spe": 0, "accuracy": 0, "evasion": 0,
        },
    )


def _switch(species: str, weight: float = 1.0) -> Action:
    return Action(
        label=f"Switch {species}",
        switch_target=species,
        weight=weight,
    )


def _base_state(doubles: bool = False) -> BattleState:
    s = BattleState(battle_id="test", my_side="p1")
    s.is_doubles        = doubles
    s.rqid              = None
    s.my_slot_decisions = []
    s.opp_last_moves    = []
    s.my_last_moves     = []
    return s


# ══════════════════════════════════════════════════════════════════════════════
# Force-switch path
# ══════════════════════════════════════════════════════════════════════════════

class TestForceSwitchUsesEngine:
    """
    After the fix, force-switch must route through _engine.scored_actions()
    so SwitchModule type-matchup scoring picks the switch-in, not team order.
    """

    def test_engine_scored_actions_is_called(self):
        """_engine.scored_actions must be called during a force-switch turn."""
        from main import _build_choice

        fainted    = _pokemon("Garganacl", hp=0, fainted=True)
        incineroar = _pokemon("Incineroar")
        sylveon    = _pokemon("Sylveon")

        state = _base_state()
        state.force_switch       = [True]
        state.my_team            = [fainted, incineroar, sylveon]
        state.my_actives         = [fainted]
        state.available_switches = [incineroar, sylveon]
        state.moves_per_slot     = [[]]
        state.opp_actives        = [_pokemon("Garchomp", side="p2")]
        state.can_mega_evo       = [False]

        calls: list[int] = []

        def spy(s, slot):
            calls.append(slot)
            return [_switch("Incineroar", 1.5), _switch("Sylveon", 1.0)]

        with patch("main._engine.scored_actions", side_effect=spy):
            _build_choice(state)

        assert 0 in calls, "Engine must be consulted for slot 0 during force switch"

    def test_engine_best_switch_chosen_over_team_order(self):
        """When engine ranks Sylveon highest, 'switch 3' must be chosen even
        though Incineroar appears first in available_switches (old code would
        have picked it)."""
        from main import _build_choice

        fainted    = _pokemon("Garganacl", hp=0, fainted=True)
        incineroar = _pokemon("Incineroar")
        sylveon    = _pokemon("Sylveon")

        state = _base_state()
        state.force_switch       = [True]
        # my_team order: fainted(slot1), Incineroar(slot2), Sylveon(slot3)
        state.my_team            = [fainted, incineroar, sylveon]
        state.my_actives         = [fainted]
        # available_switches puts Incineroar first — old code would pick it
        state.available_switches = [incineroar, sylveon]
        state.moves_per_slot     = [[]]
        state.opp_actives        = [_pokemon("Garchomp", side="p2")]
        state.can_mega_evo       = [False]

        # Engine prefers Sylveon
        with patch("main._engine.scored_actions",
                   return_value=[_switch("Sylveon", 3.5), _switch("Incineroar", 0.8)]):
            choice = _build_choice(state)

        # Sylveon is my_team[2] → team slot 3
        assert "switch 3" in choice, f"Expected Sylveon (switch 3), got: {choice!r}"
        # Incineroar is my_team[1] → team slot 2 — old code would have picked this
        assert "switch 2" not in choice

    def test_force_switch_pass_when_no_switches_available(self):
        """With no bench mons the choice for that slot must be 'pass'."""
        from main import _build_choice

        fainted = _pokemon("Garganacl", hp=0, fainted=True)

        state = _base_state()
        state.force_switch       = [True]
        state.my_team            = [fainted]
        state.my_actives         = [fainted]
        state.available_switches = []
        state.moves_per_slot     = [[]]
        state.opp_actives        = [_pokemon("Garchomp", side="p2")]
        state.can_mega_evo       = [False]

        with patch("main._engine.scored_actions", return_value=[]):
            choice = _build_choice(state)

        assert "pass" in choice

    def test_force_switch_populates_my_slot_decisions(self):
        """After picking a force-switch the action must be appended to
        my_slot_decisions so later-slot modules (DoublingUpModule,
        SwitchModule partner-veto) can see the commitment."""
        from main import _build_choice

        fainted    = _pokemon("Garganacl", hp=0, fainted=True)
        incineroar = _pokemon("Incineroar")

        state = _base_state()
        state.force_switch       = [True]
        state.my_team            = [fainted, incineroar]
        state.my_actives         = [fainted]
        state.available_switches = [incineroar]
        state.moves_per_slot     = [[]]
        state.opp_actives        = [_pokemon("Garchomp", side="p2")]
        state.can_mega_evo       = [False]

        with patch("main._engine.scored_actions",
                   return_value=[_switch("Incineroar", 2.0)]):
            _build_choice(state)

        assert len(state.my_slot_decisions) == 1
        assert state.my_slot_decisions[0].switch_target == "Incineroar"

    def test_doubles_force_switch_engine_called_per_slot(self):
        """In doubles with both slots needing a force switch, the engine must
        be called once per slot — so SwitchModule sees the growing
        my_slot_decisions list and can veto duplicate picks."""
        from main import _build_choice

        fainted_a    = _pokemon("Garganacl", hp=0, fainted=True)
        fainted_b    = _pokemon("Sylveon",   hp=0, fainted=True)
        flutter_mane = _pokemon("Flutter Mane")
        incineroar   = _pokemon("Incineroar")

        state = _base_state(doubles=True)
        state.force_switch       = [True, True]
        state.my_team            = [fainted_a, fainted_b, flutter_mane, incineroar]
        state.my_actives         = [fainted_a, fainted_b]
        state.available_switches = [flutter_mane, incineroar]
        state.moves_per_slot     = [[], []]
        state.opp_actives        = [_pokemon("Garchomp",           side="p2"),
                                     _pokemon("Landorus-Therian",   side="p2")]
        state.can_mega_evo       = [False, False]

        calls: list[int] = []

        def spy(s, slot):
            calls.append(slot)
            if slot == 0:
                return [_switch("Flutter Mane", 3.0), _switch("Incineroar", 1.5)]
            else:
                # Simulate SwitchModule having zeroed Flutter Mane for slot 1
                return [_switch("Incineroar", 1.8), _switch("Flutter Mane", 0.0)]

        with patch("main._engine.scored_actions", side_effect=spy):
            choice = _build_choice(state)

        assert calls == [0, 1], "Engine must be called for slot 0 then slot 1"

        # Flutter Mane → my_team[2] = team slot 3
        # Incineroar  → my_team[3] = team slot 4
        assert "switch 3" in choice, f"Expected Flutter Mane (switch 3) in: {choice!r}"
        assert "switch 4" in choice, f"Expected Incineroar (switch 4) in: {choice!r}"

    def test_only_nonfainted_switch_slots_are_eligible(self):
        """A zeroed (weight=0.0) switch action must not be chosen even if
        it appears first in the engine's ranked list."""
        from main import _build_choice

        fainted_a  = _pokemon("Garganacl", hp=0, fainted=True)
        incineroar = _pokemon("Incineroar")
        sylveon    = _pokemon("Sylveon")

        state = _base_state()
        state.force_switch       = [True]
        state.my_team            = [fainted_a, incineroar, sylveon]
        state.my_actives         = [fainted_a]
        state.available_switches = [incineroar, sylveon]
        state.moves_per_slot     = [[]]
        state.opp_actives        = [_pokemon("Garchomp", side="p2")]
        state.can_mega_evo       = [False]

        # Engine zeroed Incineroar (e.g. SwitchModule veto); Sylveon is second
        with patch("main._engine.scored_actions",
                   return_value=[_switch("Incineroar", 0.0), _switch("Sylveon", 1.2)]):
            choice = _build_choice(state)

        # Sylveon should be chosen, not the zeroed Incineroar
        assert "switch 3" in choice, f"Expected Sylveon (switch 3), got: {choice!r}"


class TestStruggleNoTarget:
    """Regression for the live 0.7.6 ladder bug: Struggle was emitted with a
    target slot and the server rejected it ("You can't choose a target for
    Struggle"), leaving the slot timer-controlled for the rest of the battle.
    Struggle's request target type is "randomNormal" — the server picks the
    target, so the choice token must be bare."""

    def test_struggle_emits_no_target_in_doubles(self):
        from main import _action_to_choice

        state = _base_state(doubles=True)
        state.my_actives     = [_pokemon("Garchomp"), _pokemon("Sneasler")]
        state.my_team        = list(state.my_actives)
        state.moves_per_slot = [
            [{"move": "Struggle", "id": "struggle", "target": "randomNormal"}],
            [],
        ]
        action = Action(label="Struggle", move_name="Struggle", weight=1.0)

        choice = _action_to_choice(action, state, 0, False, True)
        assert choice == "move 1", f"Struggle must carry no target, got: {choice!r}"


class TestDoubleKoForceSwitch:
    """Regression for the double-KO crash (backlog): both forced slots picked
    the SAME bench mon ("/choose switch 3, switch 3") and the server rejected
    the choice.

    The per-slot rankings during a force switch are independent — the old
    phase-1 partner-veto moved into coordinate()'s SwitchCollisionAdjuster in
    0.7.0, and coordinate() never runs on a force switch — so _build_choice
    itself must exclude targets an earlier forced slot already claimed.
    These tests run the REAL engine (no scored_actions mock: a mocked ranking
    is exactly what hid this regression).
    """

    @staticmethod
    def _real_mon(sp: str, fainted: bool = False) -> Pokemon:
        from team import find_member
        tm = find_member(sp)
        hp = 0 if fainted else tm.stats["hp"]
        return Pokemon(ident=f"p1: {sp}", species=sp, hp=hp,
                       max_hp=tm.stats["hp"], fainted=fainted,
                       ability=tm.ability, item=tm.item, moves=list(tm.moves))

    def _double_ko_state(self, bench: list[str]) -> BattleState:
        dead_a = self._real_mon("Garchomp", fainted=True)
        dead_b = self._real_mon("Kingambit", fainted=True)
        bench_mons = [self._real_mon(b) for b in bench]

        state = _base_state(doubles=True)
        state.rqid               = 7
        state.turn               = 5
        state.force_switch       = [True, True]
        state.my_team            = [dead_a, dead_b] + bench_mons
        state.my_actives         = [dead_a, dead_b]
        state.available_switches = bench_mons
        state.moves_per_slot     = [[], []]
        state.opp_actives        = [
            Pokemon(ident="p2: Incineroar", species="Incineroar",
                    hp=100, max_hp=100, hp_is_percentage=True),
            Pokemon(ident="p2: Farigiraf", species="Farigiraf",
                    hp=100, max_hp=100, hp_is_percentage=True),
        ]
        state.my_last_moves      = ["", ""]
        state.opp_last_moves     = ["", ""]
        state.my_disabled_moves  = [None, None]
        state.my_encored_moves   = [None, None]
        state.opp_tailwind       = False
        state.opp_tailwind_turns_left = 0
        state.trick_room         = False
        state.trick_room_turns_left = 0
        state.weather            = None
        state.my_tailwind        = False
        state.can_mega_evo       = [False, False]
        state.can_terastallize   = [False, False]
        state.trapped            = [False, False]
        return state

    def test_two_bench_mons_get_distinct_switches(self):
        """Double KO with two bench mons: each forced slot must bring a
        different one, never the same mon twice."""
        from main import _build_choice

        choice = _build_choice(self._double_ko_state(["Sneasler", "Basculegion-M"]))
        # Sneasler = my_team[2] → switch 3; Basculegion = my_team[3] → switch 4
        assert "switch 3" in choice and "switch 4" in choice, (
            f"Expected both bench mons brought in, got: {choice!r}"
        )

    def test_single_bench_mon_switches_once_then_passes(self):
        """Double KO with ONE bench mon left (the reported crash): the first
        forced slot brings it, the second must pass — not pick it again."""
        from main import _build_choice

        choice = _build_choice(self._double_ko_state(["Sneasler"]))
        body = choice.split("|")[0]          # strip rqid suffix
        tokens = [t.strip() for t in body.replace("/choose ", "").split(",")]
        assert tokens.count("switch 3") == 1, f"Duplicate switch in: {choice!r}"
        assert "pass" in tokens, f"Second forced slot must pass: {choice!r}"
