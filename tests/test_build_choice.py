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
