"""test_decision_modules.py — Unit tests for decision.py scoring modules.

Each module is exercised in isolation.  Calls to find_member(),
incoming_damage(), outgoing_damage(), and types_of() are patched with
controlled stubs so tests don't depend on team.txt or the data layer.

Fixture helpers (make_state, make_mon, make_action) are at the top.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass, field
from typing import Optional

from battle import BattleState, Pokemon
from decision import (
    Action,
    DecisionEngine,
    _build_actions,
    _PROTECT_MOVES,
    _FAKE_OUT_USERS,
    FakeOutModule,
    FieldConditionModule,
    FieldSetterDisruptionModule,
    OppProtectRecencyModule,
    IncomingOHKOModule,
    ConsecutiveProtectModule,
    ProtectModule,
    DoublingUpModule,
    SwitchModule,
    DamageOutputModule,
    ThreatEliminationModule,
    TurnOrderModule,
    SetterPresenceModule,
    _assumed_ability,
    _effective_ability,
)
from damage import DamageResult


# ══════════════════════════════════════════════════════════════════════════════
# Fixture helpers
# ══════════════════════════════════════════════════════════════════════════════

def make_mon(
    species: str = "Garganacl",
    hp: int = 300,
    max_hp: int = 300,
    *,
    side: str = "p1",
    fainted: bool = False,
    status: Optional[str] = None,
    ability: Optional[str] = None,
    item: Optional[str] = None,
    moves: Optional[list] = None,
    boosts: Optional[dict] = None,
    hp_is_percentage: bool = False,
    item_consumed: bool = False,
) -> Pokemon:
    return Pokemon(
        ident=f"{side}: {species}",
        species=species,
        hp=hp,
        max_hp=max_hp,
        fainted=fainted,
        status=status,
        ability=ability,
        item=item,
        moves=moves or [],
        boosts=boosts or {
            "atk": 0, "def": 0, "spa": 0, "spd": 0,
            "spe": 0, "accuracy": 0, "evasion": 0,
        },
        hp_is_percentage=hp_is_percentage,
        item_consumed=item_consumed,
    )


def make_state(
    *,
    my_actives=None,
    opp_actives=None,
    my_team=None,
    available_switches=None,
    moves_per_slot=None,
    opp_last_moves=None,
    my_last_moves=None,
    my_slot_decisions=None,
    weather=None,
    trick_room=False,
    trick_room_turns_left=0,
    opp_tailwind=False,
    opp_tailwind_turns_left=0,
    my_tailwind=False,
) -> BattleState:
    s = BattleState(battle_id="test", my_side="p1")
    s.my_actives         = my_actives or []
    s.opp_actives        = opp_actives or []
    s.my_team            = my_team or []
    s.available_switches = available_switches or []
    s.moves_per_slot     = moves_per_slot or []
    s.opp_last_moves     = opp_last_moves or []
    s.my_last_moves      = my_last_moves or []
    s.my_slot_decisions  = my_slot_decisions or []
    s.weather            = weather
    s.trick_room         = trick_room
    s.trick_room_turns_left      = trick_room_turns_left
    s.opp_tailwind               = opp_tailwind
    s.opp_tailwind_turns_left    = opp_tailwind_turns_left
    s.my_tailwind                = my_tailwind
    return s


def make_action(
    label: str = "Dragon Claw",
    move_name: str = "",
    switch_target: str = "",
    weight: float = 1.0,
    target_slot: Optional[int] = None,
) -> Action:
    return Action(
        label=label,
        move_name=move_name or label,
        switch_target=switch_target,
        weight=weight,
        target_slot=target_slot,
    )


def make_damage_result(
    *,
    move: str = "Test",
    damage_min: int = 50,
    damage_max: int = 60,
    damage_avg: float = 55.0,
    defender_hp: int = 100,
    category: str = "Physical",
) -> DamageResult:
    return DamageResult(
        move=move, power=80, category=category, effective_type="Normal",
        attacker="Mon", defender="Foe",
        stab=1.0, effectiveness=1.0, atk_modifier=1.0, def_modifier=1.0,
        damage_min=damage_min, damage_max=damage_max, damage_avg=damage_avg,
        defender_hp=defender_hp,
    )


def make_mock_member(
    ability: str = "Swift Swim",
    item: Optional[str] = None,
    atk: int = 150,
    spa: int = 100,
    spe: int = 120,
    hp: int = 300,
) -> MagicMock:
    tm = MagicMock()
    tm.ability    = ability
    tm.item       = item
    tm.mega_name  = None
    tm.mega_stats = None
    tm.stats = {"atk": atk, "def": 80, "spa": spa, "spd": 80, "spe": spe, "hp": hp}
    return tm


# ══════════════════════════════════════════════════════════════════════════════
# Action / _build_actions / DecisionEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestActionProperties:
    def test_move_action(self):
        a = Action(label="Dragon Claw", move_name="Dragon Claw")
        assert a.is_move is True
        assert a.is_switch is False

    def test_switch_action(self):
        a = Action(label="Switch Sylveon", switch_target="Sylveon")
        assert a.is_move is False
        assert a.is_switch is True

    def test_both_empty(self):
        a = Action(label="Struggle")
        assert a.is_move is False
        assert a.is_switch is False


class TestBuildActions:
    def test_builds_move_actions_from_moves_per_slot(self):
        state = make_state(
            moves_per_slot=[[{"move": "Dragon Claw"}, {"move": "Close Combat"}]],
        )
        actions = _build_actions(state, slot=0)
        labels = [a.label for a in actions]
        assert "Dragon Claw" in labels
        assert "Close Combat" in labels

    def test_skips_disabled_moves(self):
        state = make_state(
            moves_per_slot=[[
                {"move": "Dragon Claw"},
                {"move": "Struggle", "disabled": True},
            ]],
        )
        actions = _build_actions(state, slot=0)
        assert not any(a.move_name == "Struggle" for a in actions)

    def test_includes_switch_actions(self):
        bench = make_mon("Sylveon")
        state = make_state(
            moves_per_slot=[[{"move": "Dragon Claw"}]],
            available_switches=[bench],
        )
        actions = _build_actions(state, slot=0)
        assert any(a.switch_target == "Sylveon" for a in actions)

    def test_no_moves_falls_back_to_struggle(self):
        state = make_state(moves_per_slot=[[]])
        actions = _build_actions(state, slot=0)
        assert any(a.move_name == "Struggle" for a in actions)

    def test_out_of_range_slot_returns_struggle(self):
        state = make_state(moves_per_slot=[[{"move": "Dragon Claw"}]])
        actions = _build_actions(state, slot=5)
        # slot 5 doesn't exist → should still return something (Struggle fallback)
        assert len(actions) >= 1


class TestDecisionEngine:
    def test_picks_highest_weight_action(self):
        engine = DecisionEngine()
        state = make_state(moves_per_slot=[[
            {"move": "Dragon Claw"},
            {"move": "Protect"},
        ]])

        class BoostProtect:
            name = "test_boost"
            def score(self, state, slot, actions):
                for a in actions:
                    if a.move_name == "Protect":
                        a.weight *= 10.0

        engine.add_module(BoostProtect())
        winner = engine.decide(state, slot=0)
        assert winner.move_name == "Protect"

    def test_module_exception_does_not_crash_engine(self):
        engine = DecisionEngine()
        state = make_state(moves_per_slot=[[{"move": "Dragon Claw"}]])

        class BrokenModule:
            name = "broken"
            def score(self, state, slot, actions):
                raise RuntimeError("This module always explodes")

        engine.add_module(BrokenModule())
        # Should not raise — broken module is logged and skipped
        result = engine.decide(state, slot=0)
        assert result is not None

    def test_all_zero_weight_returns_first_action(self):
        engine = DecisionEngine()
        state = make_state(moves_per_slot=[[
            {"move": "Dragon Claw"},
            {"move": "Protect"},
        ]])

        class ZeroAll:
            name = "zero"
            def score(self, state, slot, actions):
                for a in actions:
                    a.weight = 0.0

        engine.add_module(ZeroAll())
        result = engine.decide(state, slot=0)
        assert result.label in ("Dragon Claw", "Protect")


# ══════════════════════════════════════════════════════════════════════════════
# FakeOutModule
# ══════════════════════════════════════════════════════════════════════════════

class TestFakeOutModule:
    module = FakeOutModule()

    def _actions(self):
        return [
            make_action("Protect", "Protect"),
            make_action("Dragon Claw", "Dragon Claw"),
            make_action("Switch Sylveon", switch_target="Sylveon"),
        ]

    def test_no_threat_is_noop(self):
        """No Fake Out user in opp_actives → all weights unchanged."""
        state = make_state(
            opp_actives=[make_mon("Garchomp")],
            opp_last_moves=[""],
        )
        actions = self._actions()
        self.module.score(state, 0, actions)
        for a in actions:
            assert a.weight == 1.0

    def test_incineroar_with_no_prior_move_is_threat(self):
        """Fresh Incineroar (opp_last_moves="") → Protect boosted, attacks discounted."""
        state = make_state(
            opp_actives=[make_mon("Incineroar")],
            opp_last_moves=[""],
        )
        actions = self._actions()
        self.module.score(state, 0, actions)

        protect = next(a for a in actions if a.move_name == "Protect")
        attack  = next(a for a in actions if a.move_name == "Dragon Claw")
        switch  = next(a for a in actions if a.is_switch)

        assert protect.weight == pytest.approx(FakeOutModule.PROTECT_BOOST)
        assert attack.weight  == pytest.approx(FakeOutModule.ATTACK_DISCOUNT)
        assert switch.weight  == 1.0   # switches unaffected

    def test_incineroar_after_move_is_no_longer_threat(self):
        """Once opp_last_moves is non-empty, Fake Out can't be used again."""
        state = make_state(
            opp_actives=[make_mon("Incineroar")],
            opp_last_moves=["Fake Out"],  # move already seen
        )
        actions = self._actions()
        self.module.score(state, 0, actions)
        for a in actions:
            assert a.weight == 1.0

    def test_non_fake_out_user_not_threat(self):
        state = make_state(
            opp_actives=[make_mon("Sylveon")],
            opp_last_moves=[""],
        )
        actions = self._actions()
        self.module.score(state, 0, actions)
        for a in actions:
            assert a.weight == 1.0

    def test_weavile_with_no_prior_move_is_threat(self):
        """Weavile was missing from _FAKE_OUT_USERS; now it should trigger protection."""
        state = make_state(
            opp_actives=[make_mon("Weavile")],
            opp_last_moves=[""],
        )
        actions = self._actions()
        self.module.score(state, 0, actions)
        protect = next(a for a in actions if a.move_name == "Protect")
        assert protect.weight == pytest.approx(FakeOutModule.PROTECT_BOOST)

    def test_tinkaton_with_no_prior_move_is_threat(self):
        """Tinkaton should trigger fake-out protection."""
        state = make_state(
            opp_actives=[make_mon("Tinkaton")],
            opp_last_moves=[""],
        )
        actions = self._actions()
        self.module.score(state, 0, actions)
        protect = next(a for a in actions if a.move_name == "Protect")
        assert protect.weight == pytest.approx(FakeOutModule.PROTECT_BOOST)

    def test_skipped_when_partner_not_threatening(self):
        """Module does not fire when the non-FakeOut partner's max damage is below threshold."""
        state = make_state(
            my_actives=[make_mon("Garchomp")],
            opp_actives=[make_mon("Incineroar"), make_mon("Farigiraf")],
            opp_last_moves=["", ""],
        )
        actions = self._actions()
        low_threat = MagicMock()
        low_threat.hp_fraction_max = FakeOutModule.PARTNER_THREAT_THRESHOLD - 0.01
        with patch("decision.modules.incoming_damage", return_value=[low_threat]):
            self.module.score(state, 0, actions)
        for a in actions:
            assert a.weight == 1.0, f"{a.move_name} weight should be unchanged"

    def test_fires_when_partner_is_threatening(self):
        """Module fires normally when the non-FakeOut partner's max damage meets threshold."""
        state = make_state(
            my_actives=[make_mon("Garchomp")],
            opp_actives=[make_mon("Incineroar"), make_mon("Garchomp")],
            opp_last_moves=["", ""],
        )
        actions = self._actions()
        high_threat = MagicMock()
        high_threat.hp_fraction_max = FakeOutModule.PARTNER_THREAT_THRESHOLD
        with patch("decision.modules.incoming_damage", return_value=[high_threat]):
            self.module.score(state, 0, actions)
        protect = next(a for a in actions if a.move_name == "Protect")
        assert protect.weight == pytest.approx(FakeOutModule.PROTECT_BOOST)

    def test_all_known_fake_out_users_present(self):
        """Spot-check that key Champions-legal Fake Out users are in _FAKE_OUT_USERS."""
        for species in ("Incineroar", "Weavile", "Tinkaton", "Kangaskhan",
                        "Lopunny", "Lopunny-Mega", "Sneasler", "Toxicroak"):
            assert species in _FAKE_OUT_USERS, f"{species} missing from _FAKE_OUT_USERS"

    def test_illegal_species_not_in_fake_out_users(self):
        """Species not legal in Champions format should not be in _FAKE_OUT_USERS."""
        for species in ("Hariyama", "Hitmontop", "Ambipom", "Mienshao",
                        "Scream Tail", "Persian", "Persian-Alola"):
            assert species not in _FAKE_OUT_USERS, f"{species} should not be in _FAKE_OUT_USERS"


# ══════════════════════════════════════════════════════════════════════════════
# OppProtectRecencyModule
# ══════════════════════════════════════════════════════════════════════════════

class TestOppProtectRecencyModule:
    module = OppProtectRecencyModule()

    def test_boosts_attack_targeting_recent_protector(self):
        state = make_state(opp_last_moves=["Protect"])
        action = make_action("Dragon Claw", "Dragon Claw", target_slot=0)
        self.module.score(state, 0, [action])
        assert action.weight == pytest.approx(OppProtectRecencyModule.PROTECTED_BOOST)

    def test_no_boost_when_target_did_not_protect(self):
        state = make_state(opp_last_moves=["Earthquake"])
        action = make_action("Dragon Claw", "Dragon Claw", target_slot=0)
        self.module.score(state, 0, [action])
        assert action.weight == 1.0

    def test_no_boost_when_no_target_slot(self):
        state = make_state(opp_last_moves=["Protect"])
        action = make_action("Dragon Claw", "Dragon Claw", target_slot=None)
        self.module.score(state, 0, [action])
        assert action.weight == 1.0

    def test_detect_protect_family_moves(self):
        """Wide Guard and King's Shield should also trigger the boost."""
        for protect_move in ("Wide Guard", "King's Shield", "Detect"):
            state = make_state(opp_last_moves=[protect_move])
            action = make_action("Close Combat", "Close Combat", target_slot=0)
            self.module.score(state, 0, [action])
            assert action.weight > 1.0, f"Expected boost for {protect_move}"


# ══════════════════════════════════════════════════════════════════════════════
# FieldConditionModule
# ══════════════════════════════════════════════════════════════════════════════

class TestFieldConditionModule:
    module = FieldConditionModule()

    def _protect(self):
        return make_action("Protect", "Protect")

    def _attack(self):
        return make_action("Dragon Claw", "Dragon Claw")

    def test_boosts_protect_on_last_tailwind_turn(self):
        state = make_state(opp_tailwind_turns_left=1)
        protect = self._protect()
        attack  = self._attack()
        self.module.score(state, 0, [protect, attack])
        assert protect.weight == pytest.approx(FieldConditionModule.STALL_FACTOR)
        assert attack.weight  == 1.0

    def test_boosts_protect_on_last_trick_room_turn(self):
        state = make_state(trick_room_turns_left=1)
        protect = self._protect()
        self.module.score(state, 0, [protect])
        assert protect.weight == pytest.approx(FieldConditionModule.STALL_FACTOR)

    def test_no_stack_when_both_conditions_active(self):
        """TW and TR expiring together still only applies ×3.0 once."""
        state = make_state(opp_tailwind_turns_left=1, trick_room_turns_left=1)
        protect = self._protect()
        self.module.score(state, 0, [protect])
        assert protect.weight == pytest.approx(FieldConditionModule.STALL_FACTOR)

    def test_boosts_protect_on_third_to_last_tailwind_turn(self):
        state = make_state(opp_tailwind_turns_left=3)
        protect = self._protect()
        attack  = self._attack()
        self.module.score(state, 0, [protect, attack])
        assert protect.weight == pytest.approx(FieldConditionModule.STALL_FACTOR)
        assert attack.weight  == 1.0

    def test_boosts_protect_on_third_to_last_trick_room_turn(self):
        state = make_state(trick_room_turns_left=3)
        protect = self._protect()
        self.module.score(state, 0, [protect])
        assert protect.weight == pytest.approx(FieldConditionModule.STALL_FACTOR)

    def test_noop_on_penultimate_turn(self):
        """turns_left == 2 is the attack turn — no Protect bonus."""
        state = make_state(opp_tailwind_turns_left=2, trick_room_turns_left=0)
        protect = self._protect()
        self.module.score(state, 0, [protect])
        assert protect.weight == 1.0

    def test_noop_when_not_ending(self):
        state = make_state(opp_tailwind_turns_left=4, trick_room_turns_left=0)
        protect = self._protect()
        self.module.score(state, 0, [protect])
        assert protect.weight == 1.0

    def test_does_not_affect_non_protect_moves(self):
        state = make_state(opp_tailwind_turns_left=1)
        attack = self._attack()
        self.module.score(state, 0, [attack])
        assert attack.weight == 1.0


# ══════════════════════════════════════════════════════════════════════════════
# IncomingOHKOModule
# ══════════════════════════════════════════════════════════════════════════════

class TestIncomingOHKOModule:
    module = IncomingOHKOModule()

    def _state_normal(self, hp_fraction: float = 1.0) -> "BattleState":
        max_hp = 300
        hp     = int(max_hp * hp_fraction)
        our_mon = make_mon("Garganacl", hp=hp, max_hp=max_hp)
        partner = make_mon("Sylveon")
        opp0    = make_mon("Garchomp",    side="p2")
        opp1    = make_mon("Incineroar",  side="p2")
        return make_state(
            my_actives=[our_mon, partner],
            opp_actives=[opp0, opp1],
            my_team=[our_mon, partner],
            available_switches=[make_mon("Bench")],
        )

    def _state_1v1(self) -> "BattleState":
        our_mon = make_mon("Garganacl")
        opp_mon = make_mon("Garchomp", side="p2")
        return make_state(
            my_actives=[our_mon],
            opp_actives=[opp_mon],
            my_team=[our_mon],
            available_switches=[],
        )

    def _state_2v1(self) -> "BattleState":
        our_mon = make_mon("Garganacl")
        partner = make_mon("Sylveon")
        opp_mon = make_mon("Garchomp", side="p2")
        return make_state(
            my_actives=[our_mon, partner],
            opp_actives=[opp_mon],
            my_team=[our_mon, partner],
            available_switches=[],
        )

    # ── Core behaviour ────────────────────────────────────────────────────────

    def test_ohko_threat_boosts_protect(self):
        """When an opponent can OHKO us, Protect should receive ×2.5."""
        state   = self._state_normal()
        protect = make_action("Protect", "Protect")
        attack  = make_action("Dragon Claw", "Dragon Claw")

        ohko_threat = MagicMock(ohko_with_max_roll=True)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]):
            self.module.score(state, slot=0, actions=[protect, attack])

        assert protect.weight == pytest.approx(IncomingOHKOModule.THREATENED_FACTOR)

    def test_no_boost_when_no_ohko_threat(self):
        """No OHKO incoming → Protect weight unchanged."""
        state   = self._state_normal()
        protect = make_action("Protect", "Protect")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[]):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    def test_attack_not_affected(self):
        """Attack moves must never be modified by this module."""
        state  = self._state_normal()
        attack = make_action("Dragon Claw", "Dragon Claw")

        ohko_threat = MagicMock(ohko_with_max_roll=True)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]):
            self.module.score(state, slot=0, actions=[attack])

        assert attack.weight == pytest.approx(1.0)

    # ── Speed awareness ───────────────────────────────────────────────────────

    def test_no_boost_when_threat_neutralized_before_acting(self):
        """An OHKO attacker a faster ally is guaranteed to remove this turn dies
        before it acts → it is not a live threat → no Protect boost."""
        state   = self._state_normal()
        protect = make_action("Protect", "Protect")

        ohko_threat = MagicMock(ohko_with_max_roll=True)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=True):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    # ── Suppress states ───────────────────────────────────────────────────────

    def test_suppressed_in_1v1_endgame(self):
        """In a 1v1, no OHKO boost — Protect can't change the outcome."""
        state   = self._state_1v1()
        protect = make_action("Protect", "Protect")

        ohko_threat = MagicMock(ohko_with_max_roll=True)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    def test_suppressed_in_2v1_numerical_advantage(self):
        """In a 2v1, no OHKO boost — Protecting cannot improve the outcome."""
        state   = self._state_2v1()
        protect = make_action("Protect", "Protect")

        ohko_threat = MagicMock(ohko_with_max_roll=True)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    def test_reason_string_appended(self):
        """A reason should be appended when the OHKO boost fires."""
        state   = self._state_normal()
        protect = make_action("Protect", "Protect")

        ohko_threat = MagicMock(ohko_with_max_roll=True)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]):
            self.module.score(state, slot=0, actions=[protect])

        assert any("incoming_ohko" in r for r in protect.reasons)


# ══════════════════════════════════════════════════════════════════════════════
# ConsecutiveProtectModule
# ══════════════════════════════════════════════════════════════════════════════

class TestConsecutiveProtectModule:
    module = ConsecutiveProtectModule()

    def _state(self, last_move: str = "") -> "BattleState":
        our_mon = make_mon("Garganacl")
        partner = make_mon("Sylveon")
        opp     = make_mon("Garchomp", side="p2")
        return make_state(
            my_actives=[our_mon, partner],
            opp_actives=[opp],
            my_team=[our_mon, partner],
            my_last_moves=[last_move, ""],
        )

    def test_penalty_applied_after_protect(self):
        """Protect used last turn → ×0.2 applied to Protect this turn."""
        state   = self._state(last_move="Protect")
        protect = make_action("Protect", "Protect")

        self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(
            ConsecutiveProtectModule.CONSECUTIVE_PENALTY
        )

    def test_penalty_value_is_0_2(self):
        """The penalty constant must be exactly 0.2."""
        assert ConsecutiveProtectModule.CONSECUTIVE_PENALTY == pytest.approx(0.2)

    def test_no_penalty_after_attack(self):
        """Last move was an attack → no penalty on Protect."""
        state   = self._state(last_move="Dragon Claw")
        protect = make_action("Protect", "Protect")

        self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    def test_no_penalty_on_first_turn(self):
        """No last move recorded (turn 1 / fresh switch-in) → no penalty."""
        state   = self._state(last_move="")
        protect = make_action("Protect", "Protect")

        self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    def test_attacks_unaffected(self):
        """Consecutive penalty must never touch attack moves."""
        state  = self._state(last_move="Protect")
        attack = make_action("Dragon Claw", "Dragon Claw")

        self.module.score(state, slot=0, actions=[attack])

        assert attack.weight == pytest.approx(1.0)

    def test_wide_guard_also_penalised(self):
        """Wide Guard is a Protect-family move and should receive the penalty."""
        state      = self._state(last_move="Wide Guard")
        wide_guard = make_action("Wide Guard", "Wide Guard")

        self.module.score(state, slot=0, actions=[wide_guard])

        assert wide_guard.weight == pytest.approx(
            ConsecutiveProtectModule.CONSECUTIVE_PENALTY
        )

    def test_penalty_applies_regardless_of_hp(self):
        """Even at critical HP (< 5%) the penalty fires — no waivers."""
        our_mon = make_mon("Garganacl", hp=3, max_hp=300)   # ~1% HP
        partner = make_mon("Sylveon")
        opp     = make_mon("Garchomp", side="p2")
        state = make_state(
            my_actives=[our_mon, partner],
            opp_actives=[opp],
            my_team=[our_mon, partner],
            my_last_moves=["Protect", ""],
        )
        protect = make_action("Protect", "Protect")

        self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(
            ConsecutiveProtectModule.CONSECUTIVE_PENALTY
        )

    def test_reason_string_appended(self):
        """A reason string should be recorded when the penalty fires."""
        state   = self._state(last_move="Protect")
        protect = make_action("Protect", "Protect")

        self.module.score(state, slot=0, actions=[protect])

        assert any("consecutive_protect" in r for r in protect.reasons)


# ══════════════════════════════════════════════════════════════════════════════
# ProtectModule
# ══════════════════════════════════════════════════════════════════════════════

class TestProtectModule:
    """
    Covers the "Will I get knocked out this turn anyway, and is Protecting
    worth it?" logic.

    All three conditions must hold for Protect ×3.0:
      1. An active opponent can OHKO this slot on its max damage roll.
      2. At least one such OHKO threat actually connects — it is NOT killed
         before it acts (no faster ally guarantees its OHKO).
      3. A partner has a guaranteed OHKO on one of the OHKO threats.

    Suppressed in 1v1 endgame (no partner, no bench, 1 opp) and in 2v1
    numerical advantage (our_active_count > active_opp_count).

    Consecutive-protect penalty lives in TestConsecutiveProtectModule.
    """
    module = ProtectModule()

    def _state_2v2(self) -> "BattleState":
        """Normal 2v2 — not in any suppress state."""
        our_mon = make_mon("Garganacl")
        partner = make_mon("Sylveon")
        opp0    = make_mon("Garchomp",   side="p2", ability="Rough Skin")
        opp1    = make_mon("Incineroar", side="p2", ability="Intimidate")
        return make_state(
            my_actives=[our_mon, partner],
            opp_actives=[opp0, opp1],
            my_team=[our_mon, partner],
            available_switches=[make_mon("Bench")],
            my_last_moves=["", ""],
        )

    def _state_1v1(self) -> "BattleState":
        """Last-mon-vs-last-mon — 1v1 endgame suppress state."""
        our_mon = make_mon("Garganacl")
        opp_mon = make_mon("Garchomp", side="p2", ability="Rough Skin")
        return make_state(
            my_actives=[our_mon],
            opp_actives=[opp_mon],
            my_team=[our_mon],
            available_switches=[],
            my_last_moves=[""],
        )

    def _state_2v1(self) -> "BattleState":
        """Two of ours vs one opponent — numerical-advantage suppress state."""
        our_mon = make_mon("Garganacl")
        partner = make_mon("Sylveon")
        opp_mon = make_mon("Garchomp", side="p2", ability="Rough Skin")
        return make_state(
            my_actives=[our_mon, partner],
            opp_actives=[opp_mon],
            my_team=[our_mon, partner],
            available_switches=[],
            my_last_moves=["", ""],
        )

    def _ohko_threat(self):
        return MagicMock(ohko_with_max_roll=True)

    # ── All three conditions met → ×3.0 ──────────────────────────────────────

    def test_all_conditions_met_boosts_protect(self):
        """OHKO incoming that connects + partner clears a threat → Protect ×3.0."""
        state   = self._state_2v2()
        protect = make_action("Protect", "Protect")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[self._ohko_threat()]), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=False), \
             patch("decision.modules._partner_can_ohko", return_value=True):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(ProtectModule.PARTNER_KO_FACTOR)

    # ── Condition 1 fails — no OHKO threat ───────────────────────────────────

    def test_no_boost_when_no_ohko_incoming(self):
        """Opponent cannot OHKO → Protect unchanged."""
        state   = self._state_2v2()
        protect = make_action("Protect", "Protect")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage",
                   return_value=[MagicMock(ohko_with_max_roll=False)]), \
             patch("decision.modules.will_outspeed", return_value=1.0), \
             patch("decision.modules._partner_can_ohko", return_value=True):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    # ── Condition 2 fails — every OHKO threat dies before it can act ──────────

    def test_no_boost_when_threat_neutralized_before_acting(self):
        """OHKO incoming, but a faster ally is guaranteed to remove the attacker
        before it acts → the hit never lands → no boost."""
        state   = self._state_2v2()
        protect = make_action("Protect", "Protect")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[self._ohko_threat()]), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=True), \
             patch("decision.modules._partner_can_ohko", return_value=True):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    # ── Condition 3 fails — no partner can clear a threat ─────────────────────

    def test_no_boost_when_partner_cannot_ohko_threat(self):
        """OHKO incoming that connects but no partner can clear a threat → no boost."""
        state   = self._state_2v2()
        protect = make_action("Protect", "Protect")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[self._ohko_threat()]), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=False), \
             patch("decision.modules._partner_can_ohko", return_value=False):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    # ── Suppress states ───────────────────────────────────────────────────────

    def test_suppressed_in_1v1_endgame(self):
        """1v1 endgame: no boost even when all other conditions would fire."""
        state   = self._state_1v1()
        protect = make_action("Protect", "Protect")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[self._ohko_threat()]), \
             patch("decision.modules.will_outspeed", return_value=1.0), \
             patch("decision.modules._partner_can_ohko", return_value=True):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    def test_suppressed_in_2v1_numerical_advantage(self):
        """2v1 (numerical advantage): no boost — outcome already decided."""
        state   = self._state_2v1()
        protect = make_action("Protect", "Protect")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[self._ohko_threat()]), \
             patch("decision.modules.will_outspeed", return_value=1.0), \
             patch("decision.modules._partner_can_ohko", return_value=True):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    # ── Attacks unaffected ────────────────────────────────────────────────────

    def test_attacks_unaffected_when_conditions_met(self):
        """ProtectModule never touches attack weights."""
        state  = self._state_2v2()
        attack = make_action("Dragon Claw", "Dragon Claw")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[self._ohko_threat()]), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=False), \
             patch("decision.modules._partner_can_ohko", return_value=True):
            self.module.score(state, slot=0, actions=[attack])

        assert attack.weight == pytest.approx(1.0)

    # ── Reason string ─────────────────────────────────────────────────────────

    def test_reason_string_appended_when_firing(self):
        """A reason string should be appended when the ×3.0 boost fires."""
        state   = self._state_2v2()
        protect = make_action("Protect", "Protect")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[self._ohko_threat()]), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=False), \
             patch("decision.modules._partner_can_ohko", return_value=True):
            self.module.score(state, slot=0, actions=[protect])

        assert any("protect" in r for r in protect.reasons)


# ══════════════════════════════════════════════════════════════════════════════
# DoublingUpModule
# ══════════════════════════════════════════════════════════════════════════════

class TestDoublingUpModule:
    module = DoublingUpModule()

    def test_slot_0_with_no_partner_is_noop(self):
        """Slot 0 has no prior partner decision — module should do nothing."""
        opp0 = make_mon("Garchomp", side="p2")
        opp1 = make_mon("Incineroar", side="p2")
        state = make_state(
            opp_actives=[opp0, opp1],
            my_slot_decisions=[],
        )
        action = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        self.module.score(state, slot=0, actions=[action])
        assert action.weight == 5.0

    def test_doubling_up_applies_penalty(self):
        """Slot 1 targeting same opp as partner → penalty applied.
        Uses Dragon Claw (single-target) to avoid the spread-move bypass."""
        partner = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        opp0 = make_mon("Garchomp", side="p2")
        opp1 = make_mon("Incineroar", side="p2")
        state = make_state(
            my_actives=[make_mon("Garganacl"), make_mon("Sylveon")],
            opp_actives=[opp0, opp1],
            opp_last_moves=["Earthquake", ""],   # slot 0 didn't Protect
            my_slot_decisions=[partner],
        )
        # Dragon Claw is single-target, so it won't be skipped by the spread-move check
        action = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=5.0)

        with patch("decision.modules.find_member", return_value=None):  # _other_opp_is_threatening → True
            self.module.score(state, slot=1, actions=[action])

        # other_threatening=True, target_protected=False → factor=0.40
        assert action.weight < 5.0
        assert action.weight == pytest.approx(5.0 * 0.40)

    def test_redirect_when_partner_has_confirmed_ohko(self):
        """Partner w≥15 on slot 0, alt target (slot 1) exists → redirect.

        DamageOutput fractions are stored on the action.  On redirect the module
        swaps out the old target's damage contribution and inserts the new one,
        preserving TurnOrder and all other non-target-specific factors.

        With no fractions stored (simulating a status move) the weight is
        unchanged after the swap (×1.0 both directions), and the action is
        simply redirected to the surviving opponent.
        """
        partner = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=18.0)
        opp0 = make_mon("Garchomp", side="p2")
        opp1 = make_mon("Incineroar", side="p2")
        state = make_state(
            my_actives=[make_mon("Garganacl"), make_mon("Sylveon")],
            opp_actives=[opp0, opp1],
            opp_last_moves=["", ""],
            my_slot_decisions=[partner],
        )
        # No target_hp_fractions set → old_dmg = new_dmg = 1.0; weight preserved.
        action = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=5.0)

        with patch("decision.modules.find_member", return_value=None):
            self.module.score(state, slot=1, actions=[action])

        assert action.target_slot == 1
        assert action.weight == pytest.approx(5.0)  # weight preserved (no fractions stored)

    def test_redirect_rescores_damage_for_new_target(self):
        """Redirect swaps DamageOutput × ThreatElim for the new target.

        Scenario: partner KOs slot-0 with ThreatElim.  Move A was great vs
        slot-0 (DamageOutput×ThreatElim inflated it) but weak vs the alt target
        (slot-1).  After redirect, the damage-derived component is replaced with
        the alt-target fraction — non-damage factors (TurnOrder etc.) are kept.
        Move B naturally scored for the alt target should win.
        """
        partner = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=18.0)
        opp0 = make_mon("Garchomp", side="p2")
        opp1 = make_mon("Incineroar", side="p2")
        state = make_state(
            my_actives=[make_mon("Garganacl"), make_mon("Sylveon")],
            opp_actives=[opp0, opp1],
            opp_last_moves=["", ""],
            my_slot_decisions=[partner],
        )
        # move_a scored vs Garchomp (slot 0): DamageOutput 80% → ×2.6, ThreatElim ×5.0
        # Non-damage contribution: 25.0 / (2.6 * 5.0) ≈ 1.92
        # vs Incineroar (slot 1): only 10% → new_dmg = ×1.2, no ThreatElim
        # Expected weight after redirect: 1.92 * 1.2 ≈ 2.31
        move_a = make_action("Poison Jab", "Poison Jab", target_slot=0, weight=25.0)
        move_a.reasons = ["threat_elimination: guaranteed OHKO on Garchomp -> x5.0"]
        move_a.target_hp_fractions = {
            0: (0.80, 0.72),   # 80% avg / 72% min vs dying target (Garchomp)
            1: (0.10, 0.09),   # 10% avg / 9% min vs alt target (Incineroar)
        }
        # move_b: naturally scored vs Incineroar (slot 1), moderate weight
        move_b = make_action("Stomping Tantrum", "Stomping Tantrum", target_slot=1, weight=6.0)

        with patch("decision.modules.find_member", return_value=None):
            self.module.score(state, slot=1, actions=[move_a, move_b])

        # move_a redirected to slot 1; damage re-scored: 25 / (2.6*5) * 1.2 ≈ 2.31
        old_dmg = 1.0 + 0.80 * 2.0   # 2.6
        new_dmg = 1.0 + 0.10 * 2.0   # 1.2
        expected_a = 25.0 / (old_dmg * 5.0) * new_dmg
        assert move_a.target_slot == 1
        assert move_a.weight == pytest.approx(expected_a, rel=1e-4)
        assert move_b.weight == pytest.approx(6.0)
        assert move_b.weight > move_a.weight  # naturally-scored move wins

    def test_penalty_reduced_when_target_protected_last_turn(self):
        """target_protected=True reduces the doubling-up penalty."""
        partner = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=5.0)
        opp0 = make_mon("Garchomp", side="p2")
        opp1 = make_mon("Incineroar", side="p2")
        state = make_state(
            my_actives=[make_mon("Garganacl"), make_mon("Sylveon")],
            opp_actives=[opp0, opp1],
            opp_last_moves=["Protect", ""],  # slot 0 used Protect last turn
            my_slot_decisions=[partner],
        )
        action = make_action("Close Combat", "Close Combat", target_slot=0, weight=5.0)

        with patch("decision.modules.find_member", return_value=None):
            self.module.score(state, slot=1, actions=[action])

        # other_threatening=True (no team data), target_protected=True → factor=0.55
        assert action.weight == pytest.approx(5.0 * 0.55)



# ══════════════════════════════════════════════════════════════════════════════
# SwitchModule
# ══════════════════════════════════════════════════════════════════════════════

class TestSwitchModuleInferThreatTypes:
    """Tests for SwitchModule._infer_threat_types() status-move filtering."""
    module = SwitchModule()

    def test_status_moves_excluded_from_threat_types(self):
        """Trick Room (Status/Psychic) should not add an extra Psychic entry.

        Farigiraf is Normal/Psychic, so Psychic DOES appear via the species STAB
        lookup — but it must not appear a second time from the Status move itself.
        """
        farigiraf = make_mon("Farigiraf", side="p2", moves=["Trick Room", "Hyper Voice"])
        state = make_state(opp_actives=[farigiraf])
        threat_types = self.module._infer_threat_types(state)
        # "Hyper Voice" is Special/Normal — its Normal type SHOULD appear.
        assert "Normal" in threat_types
        # Farigiraf's secondary STAB type Psychic appears via species lookup (correct).
        assert "Psychic" in threat_types
        # Trick Room is Status — it must not add a duplicate Psychic entry.
        assert threat_types.count("Psychic") == 1

    def test_damaging_moves_included_in_threat_types(self):
        """A revealed damaging move's type should still appear in the threat list."""
        garchomp = make_mon("Garchomp", side="p2", moves=["Earthquake", "Tailwind"])
        state = make_state(opp_actives=[garchomp])
        threat_types = self.module._infer_threat_types(state)
        # "Earthquake" is Physical/Ground — Ground must appear.
        assert "Ground" in threat_types
        # "Tailwind" is Status/Flying — Flying must NOT appear from this move.
        # (Flying may still appear via species STAB, but Garchomp is Dragon/Ground)
        assert "Flying" not in threat_types

    def test_unknown_move_not_filtered(self):
        """A move not in the move database (None category) should not be filtered out
        — we conservatively assume it could be a damaging move."""
        opp = make_mon("Garchomp", side="p2", moves=["UnknownMoveXYZ"])
        state = make_state(opp_actives=[opp])
        # Should not raise; result may or may not contain a type
        # (move_type returns None for unknown moves, so nothing is added anyway)
        threat_types = self.module._infer_threat_types(state)
        assert isinstance(threat_types, list)


# ══════════════════════════════════════════════════════════════════════════════
# SetterPresenceModule
# ══════════════════════════════════════════════════════════════════════════════

class TestSetterPresenceModule:
    module = SetterPresenceModule()

    def _actions(self):
        return [
            make_action("Protect", "Protect"),
            make_action("Earth Power", "Earth Power"),
            make_action("Sludge Bomb", "Sludge Bomb"),
            make_action("Switch Garchomp", switch_target="Garchomp"),
        ]

    def test_no_setter_is_noop(self):
        """No TR/TW setter on field — all weights unchanged."""
        state = make_state(opp_actives=[make_mon("Incineroar"), make_mon("Sneasler")])
        actions = self._actions()
        self.module.score(state, 0, actions)
        for a in actions:
            assert a.weight == 1.0

    def test_tr_setter_boosts_attacks(self):
        """Farigiraf on field → attack moves get ×2.0, Protect and Switch unchanged."""
        state = make_state(opp_actives=[make_mon("Farigiraf"), make_mon("Incineroar")])
        actions = self._actions()
        self.module.score(state, 0, actions)

        protect = next(a for a in actions if a.move_name == "Protect")
        earth   = next(a for a in actions if a.move_name == "Earth Power")
        sludge  = next(a for a in actions if a.move_name == "Sludge Bomb")
        switch  = next(a for a in actions if a.is_switch)

        assert protect.weight == pytest.approx(1.0)
        assert earth.weight   == pytest.approx(SetterPresenceModule.TR_BOOST)
        assert sludge.weight  == pytest.approx(SetterPresenceModule.TR_BOOST)
        assert switch.weight  == pytest.approx(1.0)

    def test_tw_setter_boosts_attacks(self):
        """Noivern (TW setter) on field → attack moves get ×1.5, Protect and Switch unchanged."""
        state = make_state(opp_actives=[make_mon("Noivern"), make_mon("Garchomp")])
        actions = self._actions()
        self.module.score(state, 0, actions)

        protect = next(a for a in actions if a.move_name == "Protect")
        earth   = next(a for a in actions if a.move_name == "Earth Power")
        switch  = next(a for a in actions if a.is_switch)

        assert protect.weight == pytest.approx(1.0)
        assert earth.weight   == pytest.approx(SetterPresenceModule.TW_BOOST)
        assert switch.weight  == pytest.approx(1.0)

    def test_tr_takes_priority_over_tw(self):
        """When both a TR setter and a TW setter are present, TR boost applies."""
        state = make_state(
            opp_actives=[make_mon("Farigiraf"), make_mon("Noivern")]
        )
        actions = self._actions()
        self.module.score(state, 0, actions)

        earth = next(a for a in actions if a.move_name == "Earth Power")
        # Should get TR boost (2.0), not TW boost (1.5)
        assert earth.weight == pytest.approx(SetterPresenceModule.TR_BOOST)

    def test_fainted_setter_does_not_boost(self):
        """A fainted setter is not active — no boost applied."""
        fainted_setter = make_mon("Farigiraf", fainted=True)
        state = make_state(opp_actives=[fainted_setter, make_mon("Incineroar")])
        actions = self._actions()
        self.module.score(state, 0, actions)
        for a in actions:
            assert a.weight == 1.0

    def test_reason_string_appended(self):
        """Reason string is added to boosted attack actions."""
        state = make_state(opp_actives=[make_mon("Cofagrigus")])
        actions = self._actions()
        self.module.score(state, 0, actions)

        earth = next(a for a in actions if a.move_name == "Earth Power")
        assert any("setter_presence" in r for r in earth.reasons)
        assert any("TR setter on field" in r for r in earth.reasons)
        assert any("TR not active" in r for r in earth.reasons)

    # ── Field-effect gating ───────────────────────────────────────────────────

    def test_tr_setter_no_boost_when_tr_active_with_turns_left(self):
        """TR setter present but TR is already active (≥2 turns left) → no boost."""
        state = make_state(
            opp_actives=[make_mon("Farigiraf"), make_mon("Incineroar")],
            trick_room=True,
            trick_room_turns_left=3,
        )
        actions = self._actions()
        self.module.score(state, 0, actions)
        for a in actions:
            assert a.weight == pytest.approx(1.0), f"{a.label} should be unaffected"

    def test_tr_setter_boost_on_last_turn_of_tr(self):
        """TR setter present and TR is on its last turn → TR boost fires (re-set risk)."""
        state = make_state(
            opp_actives=[make_mon("Farigiraf"), make_mon("Incineroar")],
            trick_room=True,
            trick_room_turns_left=1,
        )
        actions = self._actions()
        self.module.score(state, 0, actions)

        earth = next(a for a in actions if a.move_name == "Earth Power")
        assert earth.weight == pytest.approx(SetterPresenceModule.TR_BOOST)
        assert any("re-set risk" in r for r in earth.reasons)

    def test_tw_setter_no_boost_when_tw_active_with_turns_left(self):
        """TW setter present but Tailwind is already active (≥2 turns left) → no boost."""
        state = make_state(
            opp_actives=[make_mon("Noivern"), make_mon("Garchomp")],
            opp_tailwind=True,
            opp_tailwind_turns_left=3,
        )
        actions = self._actions()
        self.module.score(state, 0, actions)
        for a in actions:
            assert a.weight == pytest.approx(1.0), f"{a.label} should be unaffected"

    def test_tw_setter_boost_on_last_turn_of_tw(self):
        """TW setter present and TW is on its last turn → TW boost fires (re-set risk)."""
        state = make_state(
            opp_actives=[make_mon("Noivern"), make_mon("Garchomp")],
            opp_tailwind=True,
            opp_tailwind_turns_left=1,
        )
        actions = self._actions()
        self.module.score(state, 0, actions)

        earth = next(a for a in actions if a.move_name == "Earth Power")
        assert earth.weight == pytest.approx(SetterPresenceModule.TW_BOOST)
        assert any("re-set risk" in r for r in earth.reasons)

    def test_tw_setter_suppressed_while_tr_active(self):
        """TR is active → TW setter boost is suppressed even if TW is not yet up."""
        state = make_state(
            opp_actives=[make_mon("Farigiraf"), make_mon("Noivern")],
            trick_room=True,
            trick_room_turns_left=3,
            opp_tailwind=False,
        )
        actions = self._actions()
        self.module.score(state, 0, actions)
        for a in actions:
            assert a.weight == pytest.approx(1.0), f"{a.label} should be unaffected"

    def test_tr_setter_suppressed_while_tw_active(self):
        """Opp Tailwind is active → TR setter boost is suppressed even if TR is not yet up."""
        state = make_state(
            opp_actives=[make_mon("Farigiraf"), make_mon("Noivern")],
            trick_room=False,
            opp_tailwind=True,
            opp_tailwind_turns_left=3,
        )
        actions = self._actions()
        self.module.score(state, 0, actions)
        for a in actions:
            assert a.weight == pytest.approx(1.0), f"{a.label} should be unaffected"


class TestFieldSetterDisruptionModule:
    module = FieldSetterDisruptionModule()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _ohko_result():
        return make_damage_result(damage_min=110, damage_max=130,
                                  damage_avg=120.0, defender_hp=100)

    @staticmethod
    def _non_ohko_result():
        return make_damage_result(damage_min=40, damage_max=60,
                                  damage_avg=50.0, defender_hp=100)

    # ── Denial fires when OHKO + outspeed + no priority ability ──────────────

    def test_boosts_attack_already_targeting_tr_setter(self):
        """Guaranteed OHKO on an outspeed TR setter → x2.0 applied."""
        farigiraf = make_mon("Farigiraf", side="p2")
        opp1      = make_mon("Incineroar", side="p2")
        our_mon   = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[farigiraf, opp1],
            my_team=[our_mon],
            trick_room=False,
        )
        action = make_action("Shadow Ball", "Shadow Ball", target_slot=0, weight=3.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(
            3.0 * FieldSetterDisruptionModule.TR_DISRUPTION_FACTOR
        )

    def test_boosts_attack_already_targeting_tailwind_setter(self):
        """Guaranteed OHKO on an outspeed TW setter (Noivern) → x1.5 applied."""
        noivern = make_mon("Noivern", side="p2")
        opp1    = make_mon("Garchomp", side="p2")
        our_mon = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[noivern, opp1],
            my_team=[our_mon],
            opp_tailwind=False,
        )
        action = make_action("Air Slash", "Air Slash", target_slot=0, weight=3.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(
            3.0 * FieldSetterDisruptionModule.TAILWIND_DISRUPTION_FACTOR
        )

    def test_revealed_tailwind_move_triggers_boost(self):
        """Any opponent with 'Tailwind' revealed and no priority ability → deniable."""
        unknown_setter = make_mon("Charizard", side="p2", moves=["Tailwind"])
        our_mon = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[unknown_setter],
            my_team=[our_mon],
            opp_tailwind=False,
        )
        action = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=2.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(
            2.0 * FieldSetterDisruptionModule.TAILWIND_DISRUPTION_FACTOR
        )

    # ── No denial when OHKO is impossible ────────────────────────────────────

    def test_no_boost_when_cannot_ohko_tr_setter(self):
        """Non-OHKO attack on TR setter → no bonus (setter survives and sets TR)."""
        farigiraf = make_mon("Farigiraf", side="p2")
        our_mon   = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[farigiraf],
            my_team=[our_mon],
            trick_room=False,
        )
        action = make_action("Shadow Ball", "Shadow Ball", target_slot=0, weight=3.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._non_ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(3.0)  # unchanged

    def test_no_boost_when_cannot_ohko_tw_setter(self):
        """Non-OHKO attack on TW setter → no bonus."""
        noivern = make_mon("Noivern", side="p2")
        our_mon = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[noivern],
            my_team=[our_mon],
            opp_tailwind=False,
        )
        action = make_action("Air Slash", "Air Slash", target_slot=0, weight=2.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._non_ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(2.0)  # unchanged

    # ── No denial when we are slower than the setter ─────────────────────────

    def test_no_boost_when_slower_than_setter(self):
        """Even a guaranteed OHKO gives no bonus if the setter moves before us."""
        farigiraf = make_mon("Farigiraf", side="p2")
        our_mon   = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[farigiraf],
            my_team=[our_mon],
            trick_room=False,
        )
        action = make_action("Shadow Ball", "Shadow Ball", target_slot=0, weight=3.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=0.0):  # setter faster
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(3.0)  # unchanged

    # ── No denial for priority-ability setters ────────────────────────────────

    def test_whimsicott_tailwind_never_deniable(self):
        """Whimsicott has Prankster — Tailwind always goes first, no bonus."""
        whimsicott = make_mon("Whimsicott", side="p2")
        our_mon    = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[whimsicott],
            my_team=[our_mon],
            opp_tailwind=False,
        )
        action = make_action("Dazzling Gleam", "Dazzling Gleam",
                             target_slot=0, weight=2.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(2.0)  # no bonus

    def test_prankster_revealed_any_species_no_boost(self):
        """Any TW setter with Prankster revealed is treated as undeniable."""
        # Use Noivern (a TW setter) with Prankster explicitly revealed to simulate
        # any species whose ability has been confirmed as Prankster mid-battle.
        noivern = make_mon("Noivern", side="p2", ability="Prankster")
        our_mon = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[noivern],
            my_team=[our_mon],
            opp_tailwind=False,
        )
        action = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=2.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(2.0)  # no bonus

    def test_talonflame_at_full_hp_no_boost(self):
        """Talonflame at 100% HP has Gale Wings active → Tailwind undeniable."""
        talonflame = make_mon("Talonflame", side="p2", hp=300, max_hp=300)
        our_mon    = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[talonflame],
            my_team=[our_mon],
            opp_tailwind=False,
        )
        action = make_action("Rock Tomb", "Rock Tomb", target_slot=0, weight=2.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(2.0)  # no bonus — Gale Wings active

    def test_talonflame_below_full_hp_can_be_denied(self):
        """Talonflame below full HP loses Gale Wings — Tailwind can be denied."""
        talonflame = make_mon("Talonflame", side="p2", hp=250, max_hp=300)
        our_mon    = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[talonflame],
            my_team=[our_mon],
            opp_tailwind=False,
        )
        action = make_action("Rock Tomb", "Rock Tomb", target_slot=0, weight=2.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(
            2.0 * FieldSetterDisruptionModule.TAILWIND_DISRUPTION_FACTOR
        )

    # ── Effect-already-active no-ops ─────────────────────────────────────────

    def test_noop_when_trick_room_already_active(self):
        """No TR disruption when TR is already up — the setter has done its job."""
        farigiraf = make_mon("Farigiraf", side="p2")
        our_mon   = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[farigiraf],
            my_team=[our_mon],
            trick_room=True,
            opp_tailwind=False,
        )
        action = make_action("Shadow Ball", "Shadow Ball", target_slot=0, weight=3.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(3.0)

    def test_noop_when_tailwind_already_active(self):
        """No Tailwind disruption when Tailwind is already up."""
        noivern = make_mon("Noivern", side="p2")
        our_mon = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[noivern],
            my_team=[our_mon],
            trick_room=False,
            opp_tailwind=True,
        )
        action = make_action("Rock Slide", "Rock Slide", target_slot=0, weight=3.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(3.0)

    # ── Protect always excluded ───────────────────────────────────────────────

    def test_protect_not_boosted(self):
        """Protect-family moves should never receive the setter disruption boost."""
        farigiraf = make_mon("Farigiraf", side="p2")
        our_mon   = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[farigiraf],
            my_team=[our_mon],
            trick_room=False,
        )
        protect = make_action("Protect", "Protect", target_slot=0, weight=1.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)


class TestSwitchModule:
    module = SwitchModule()

    def test_vetoes_switch_already_committed_by_partner(self):
        """If partner is already switching to Sylveon, this slot can't also switch there."""
        partner_decision = make_action("Switch Sylveon", switch_target="Sylveon",
                                        weight=3.0)
        state = make_state(
            my_actives=[make_mon("Garganacl"), make_mon("Garganacl")],
            opp_actives=[make_mon("Incineroar", side="p2")],
            my_slot_decisions=[partner_decision],
        )
        switch_action = make_action("Switch Sylveon", switch_target="Sylveon",
                                    weight=2.0)

        with patch("decision.modules.find_member", return_value=None), \
             patch("decision.modules.types_of", return_value=[]):
            self.module.score(state, slot=1, actions=[switch_action])

        assert switch_action.weight == 0.0

    def _board_value_state(self):
        cur     = make_mon("Garganacl")
        partner = make_mon("Garganacl")
        opp     = make_mon("Incineroar", side="p2")
        return make_state(
            my_actives=[cur, partner],
            opp_actives=[opp],
            my_team=[cur, partner],
            available_switches=[make_mon("Sylveon")],
            moves_per_slot=[[{"move": "Atk", "disabled": False}], []],
        )

    def test_escape_pivot_scores_high(self):
        """Current mon OHKO-threatened + switch-in survives → TEMPO×(offense+ESCAPE)."""
        state  = self._board_value_state()
        switch = make_action("Switch Sylveon", switch_target="Sylveon", weight=1.0)
        tm = make_mock_member()
        tm.moves = ["Atk"]

        def incoming(**kw):  # current mon dies; the Sylveon switch-in survives
            return [MagicMock(ohko_with_max_roll=(kw["our_species"] != "Sylveon"))]

        with patch("decision.modules.find_member", return_value=tm), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=False), \
             patch("decision.modules.outgoing_damage",
                   return_value=[make_damage_result(damage_avg=40.0, defender_hp=100)]), \
             patch("decision.modules.incoming_damage", side_effect=incoming):
            self.module.score(state, slot=0, actions=[switch])

        # offense gain 0 (current and switch-in deal the same) → offense_term 1.0;
        # threatened + survives → + ESCAPE_BONUS.
        expected = SwitchModule.TEMPO_FACTOR * (1.0 + SwitchModule.ESCAPE_BONUS)
        assert switch.weight == pytest.approx(expected, abs=0.05)

    def test_switch_into_ohko_is_discouraged(self):
        """Switch-in is itself OHKO'd → DANGER_FACTOR and no escape bonus."""
        state  = self._board_value_state()
        switch = make_action("Switch Sylveon", switch_target="Sylveon", weight=1.0)
        tm = make_mock_member()
        tm.moves = ["Atk"]

        with patch("decision.modules.find_member", return_value=tm), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=False), \
             patch("decision.modules.outgoing_damage",
                   return_value=[make_damage_result(damage_avg=40.0, defender_hp=100)]), \
             patch("decision.modules.incoming_damage",
                   return_value=[MagicMock(ohko_with_max_roll=True)]):  # everything OHKO'd
            self.module.score(state, slot=0, actions=[switch])

        expected = SwitchModule.TEMPO_FACTOR * 1.0 * SwitchModule.DANGER_FACTOR
        assert switch.weight == pytest.approx(expected, abs=0.05)


# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# Integration: DamageOutputModule and ThreatEliminationModule
# ══════════════════════════════════════════════════════════════════════════════

class TestDamageOutputModuleIntegration:
    module = DamageOutputModule()

    def test_high_damage_fraction_increases_weight(self):
        """A move that does 80% HP should weight roughly ×2.6."""
        our_mon = make_mon("Garganacl")
        opp_mon = make_mon("Garchomp", side="p2")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[opp_mon],
            my_team=[our_mon],
        )
        action = make_action("Wave Crash", "Wave Crash")

        # 80% average damage fraction
        result = make_damage_result(damage_min=70, damage_max=90, damage_avg=80.0,
                                    defender_hp=100)
        mock_tm = make_mock_member()

        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[result]):
            self.module.score(state, slot=0, actions=[action])

        expected = 1.0 + 0.80 * 2.0  # = 2.6
        assert action.weight == pytest.approx(expected)

    def test_zero_damage_does_not_change_weight(self):
        """A move that deals 0 damage (type immunity) should stay at 1.0."""
        our_mon = make_mon("Garganacl")
        opp_mon = make_mon("Garchomp", side="p2")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[opp_mon],
            my_team=[our_mon],
        )
        action = make_action("Ghost Move", "Ghost Move")

        zero_result = make_damage_result(damage_min=0, damage_max=0, damage_avg=0.0,
                                          defender_hp=100)
        mock_tm = make_mock_member()

        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[zero_result]):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(1.0)


class TestThreatEliminationModuleIntegration:
    module = ThreatEliminationModule()

    def test_guaranteed_ohko_applies_5x_multiplier(self):
        our_mon = make_mon("Garganacl")
        opp_mon = make_mon("Garchomp", side="p2")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[opp_mon],
            my_team=[our_mon],
        )
        action = make_action("Wave Crash", "Wave Crash")

        ohko_result = make_damage_result(damage_min=110, damage_max=130,
                                          damage_avg=120.0, defender_hp=100)
        mock_tm = make_mock_member()

        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[ohko_result]), \
             patch("decision.modules._ko_before_acting", return_value=False):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(ThreatEliminationModule.GUARANTEED_OHKO)

    def test_ohko_bonus_withheld_when_ko_before_acting(self):
        """Offensive speed gate: if we're guaranteed-KO'd before we can act, the
        guaranteed-OHKO bonus is withheld (the kill is never delivered)."""
        our_mon = make_mon("Garganacl")
        opp_mon = make_mon("Garchomp", side="p2")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[opp_mon],
            my_team=[our_mon],
        )
        action = make_action("Wave Crash", "Wave Crash")

        ohko_result = make_damage_result(damage_min=110, damage_max=130,
                                          damage_avg=120.0, defender_hp=100)
        mock_tm = make_mock_member()

        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[ohko_result]), \
             patch("decision.modules._ko_before_acting", return_value=True):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(1.0)   # no ×5 — kill is undeliverable


# ══════════════════════════════════════════════════════════════════════════════
# _build_actions — Disable / Encore filtering
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildActionsDisableEncore:
    """_build_actions must filter Disabled moves and honour Encore locks."""

    def _make_move_dicts(self, names):
        return [{"move": n, "disabled": False} for n in names]

    def test_disabled_move_is_excluded(self):
        """A move matched by my_disabled_moves[slot] must not appear in actions."""
        state = make_state(
            moves_per_slot=[self._make_move_dicts(["Dragon Claw", "Earthquake", "Protect"])],
        )
        state.my_disabled_moves = ["Earthquake"]
        state.my_encored_moves  = [None]

        actions = _build_actions(state, slot=0)
        names = [a.move_name for a in actions]
        assert "Earthquake" not in names
        assert "Dragon Claw" in names
        assert "Protect" in names

    def test_disabled_move_case_insensitive(self):
        """Disable matching is case-insensitive."""
        state = make_state(
            moves_per_slot=[self._make_move_dicts(["Giga Drain", "Sludge Bomb"])],
        )
        state.my_disabled_moves = ["giga drain"]
        state.my_encored_moves  = [None]

        actions = _build_actions(state, slot=0)
        names = [a.move_name for a in actions]
        assert "Giga Drain" not in names
        assert "Sludge Bomb" in names

    def test_encored_move_only_legal_move(self):
        """When Encored, only the locked move should appear in actions."""
        state = make_state(
            moves_per_slot=[self._make_move_dicts(
                ["Dragon Claw", "Earthquake", "Protect", "Stone Edge"]
            )],
        )
        state.my_disabled_moves = [None]
        state.my_encored_moves  = ["Earthquake"]

        actions = _build_actions(state, slot=0)
        move_actions = [a for a in actions if a.is_move]
        assert len(move_actions) == 1
        assert move_actions[0].move_name == "Earthquake"

    def test_encore_plus_disable_falls_back_to_struggle(self):
        """Encore + Disable with the SERVER marking every move unusable → Struggle.

        The server is authoritative: when it offers nothing usable (all moves
        flagged disabled), Struggle is correct.
        """
        state = make_state(
            moves_per_slot=[[
                {"move": "Dragon Claw", "disabled": True},
                {"move": "Earthquake",  "disabled": True},
                {"move": "Protect",     "disabled": True},
            ]],
        )
        state.my_disabled_moves = ["Earthquake"]
        state.my_encored_moves  = ["Earthquake"]

        actions = _build_actions(state, slot=0)
        move_actions = [a for a in actions if a.is_move]
        assert len(move_actions) == 1
        assert move_actions[0].move_name == "Struggle"

    def test_stale_lock_does_not_force_struggle_when_server_offers_moves(self):
        """If our Disable/Encore tracking would empty the move list but the
        server still offers usable moves, trust the server — do NOT Struggle.

        Guards the false-Struggle from a stale Encore lock (the move-disappearance
        seen in the 0.5.6 battle data): our lock said "only Earthquake" while
        Earthquake was also marked Disabled, which used to wipe every move.
        """
        state = make_state(
            moves_per_slot=[self._make_move_dicts(
                ["Dragon Claw", "Earthquake", "Protect"]   # server: all usable
            )],
        )
        state.my_disabled_moves = ["Earthquake"]   # contradictory / stale tracking
        state.my_encored_moves  = ["Earthquake"]

        actions = _build_actions(state, slot=0)
        names = [a.move_name for a in actions if a.is_move]
        assert "Struggle" not in names
        assert set(names) == {"Dragon Claw", "Earthquake", "Protect"}

    def test_no_disable_no_encore_unchanged(self):
        """When both lists are None/empty, behaviour is identical to before."""
        state = make_state(
            moves_per_slot=[self._make_move_dicts(["Dragon Claw", "Protect"])],
        )
        state.my_disabled_moves = [None]
        state.my_encored_moves  = [None]

        actions = _build_actions(state, slot=0)
        names = [a.move_name for a in actions if a.is_move]
        assert names == ["Dragon Claw", "Protect"]

    def test_slot_out_of_range_is_safe(self):
        """If lists are shorter than the slot index, no crash and no filtering."""
        state = make_state(
            moves_per_slot=[
                [],  # slot 0 placeholder
                self._make_move_dicts(["Close Combat", "Protect"]),
            ],
        )
        state.my_disabled_moves = []   # slot 1 not present
        state.my_encored_moves  = []

        actions = _build_actions(state, slot=1)
        names = [a.move_name for a in actions if a.is_move]
        assert "Close Combat" in names
        assert "Protect" in names


class TestBuildActionsTrapped:
    """_build_actions suppresses switches for a server-flagged trapped slot."""

    def _moves(self, names):
        return [{"move": n, "disabled": False} for n in names]

    def test_trapped_slot_offers_no_switches(self):
        """Trapped (e.g. Shadow Tag) → moves only, no switch actions."""
        state = make_state(
            moves_per_slot=[self._moves(["Dragon Claw", "Protect"])],
            available_switches=[make_mon("Venusaur"), make_mon("Aerodactyl")],
        )
        state.trapped = [True]

        actions = _build_actions(state, slot=0)
        assert not any(a.is_switch for a in actions)
        assert any(a.move_name == "Dragon Claw" for a in actions)

    def test_untrapped_slot_offers_switches(self):
        """Not trapped → switches are listed as usual."""
        state = make_state(
            moves_per_slot=[self._moves(["Dragon Claw"])],
            available_switches=[make_mon("Venusaur")],
        )
        state.trapped = [False]

        actions = _build_actions(state, slot=0)
        assert any(a.switch_target == "Venusaur" for a in actions)

    def test_force_switch_overrides_stale_trapped(self):
        """A mandatory switch must be offered even if a stale trapped flag lingers."""
        state = make_state(
            moves_per_slot=[[]],
            available_switches=[make_mon("Venusaur")],
        )
        state.trapped      = [True]
        state.force_switch = [True]

        actions = _build_actions(state, slot=0)
        assert any(a.switch_target == "Venusaur" for a in actions)

    def test_trapped_with_no_move_returns_struggle_and_no_switch(self):
        """Trapped + no usable move → Struggle only (still no illegal switch)."""
        state = make_state(
            moves_per_slot=[[]],
            available_switches=[make_mon("Venusaur")],
        )
        state.trapped = [True]

        actions = _build_actions(state, slot=0)
        assert [a.move_name for a in actions if a.is_move] == ["Struggle"]
        assert not any(a.is_switch for a in actions)

    def test_trapped_default_empty_is_safe(self):
        """Default empty trapped list (manually-built states) → not trapped."""
        state = make_state(
            moves_per_slot=[self._moves(["Dragon Claw"])],
            available_switches=[make_mon("Venusaur")],
        )
        # state.trapped left at its default []
        actions = _build_actions(state, slot=0)
        assert any(a.switch_target == "Venusaur" for a in actions)


# ══════════════════════════════════════════════════════════════════════════════
# TurnOrderModule
# ══════════════════════════════════════════════════════════════════════════════

class TestTurnOrderModule:
    module = TurnOrderModule()

    def _state(self, num_opps: int = 2, include_partner: bool = True):
        """Standard 2v2 state with opp abilities set to avoid _get_species calls."""
        our_mon   = make_mon("Garchomp")
        partner   = make_mon("Kingambit") if include_partner else None
        opps = [
            make_mon("Incineroar",  side="p2", ability="Intimidate"),
            make_mon("Basculegion", side="p2", ability="Swift Swim"),
        ][:num_opps]
        my_actives = [our_mon, partner] if include_partner else [our_mon]
        return make_state(
            my_actives=my_actives,
            opp_actives=opps,
            my_team=[our_mon] + ([partner] if include_partner else []),
        )

    # ── Position multipliers ──────────────────────────────────────────────────

    def test_position_1_fastest_applies_2x(self):
        """Outspeed all 3 others (both opps + partner) → position 1/4 → ×2.0."""
        state   = self._state()
        actions = [make_action("Dragon Claw", "Dragon Claw")]

        with patch("decision.modules.find_member", return_value=None), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=actions)

        assert actions[0].weight == pytest.approx(TurnOrderModule._MULTIPLIERS[1])

    def test_position_4_slowest_applies_0_75x(self):
        """Outspeed 0 of 3 others → position 4/4 → ×0.75."""
        state   = self._state()
        actions = [make_action("Dragon Claw", "Dragon Claw")]

        with patch("decision.modules.find_member", return_value=None), \
             patch("decision.modules.will_outspeed", return_value=0.0):
            self.module.score(state, slot=0, actions=actions)

        assert actions[0].weight == pytest.approx(TurnOrderModule._MULTIPLIERS[4])

    def test_position_2_applies_1_5x(self):
        """Outspeed 2 of 3 others → position 2/4 → ×1.5."""
        state   = self._state()
        actions = [make_action("Dragon Claw", "Dragon Claw")]

        call_count = [0]

        def side_effect(a, b, **kw):   # tolerate trick_room= kwarg
            call_count[0] += 1
            return 1.0 if call_count[0] <= 2 else 0.0   # beat first 2, lose to 3rd

        with patch("decision.modules.find_member", return_value=None), \
             patch("decision.modules.will_outspeed", side_effect=side_effect):
            self.module.score(state, slot=0, actions=actions)

        assert actions[0].weight == pytest.approx(TurnOrderModule._MULTIPLIERS[2])

    def test_position_3_applies_1_0x(self):
        """Outspeed 1 of 3 others → position 3/4 → ×1.0."""
        state   = self._state()
        actions = [make_action("Dragon Claw", "Dragon Claw")]

        call_count = [0]

        def side_effect(a, b, **kw):   # tolerate trick_room= kwarg
            call_count[0] += 1
            return 1.0 if call_count[0] <= 1 else 0.0   # beat only the first other

        with patch("decision.modules.find_member", return_value=None), \
             patch("decision.modules.will_outspeed", side_effect=side_effect):
            self.module.score(state, slot=0, actions=actions)

        assert actions[0].weight == pytest.approx(TurnOrderModule._MULTIPLIERS[3])

    def test_passes_trick_room_to_will_outspeed(self):
        """Under Trick Room the module must tell will_outspeed so a raw-fast mon
        is correctly read as moving LAST (else it won't stall / plays wrong)."""
        state = self._state()
        state.trick_room = True
        attack  = make_action("Dragon Claw", "Dragon Claw")
        mock_ws = MagicMock(return_value=1.0)
        with patch("decision.modules.find_member", return_value=None), \
             patch("decision.modules.will_outspeed", mock_ws):
            self.module.score(state, slot=0, actions=[attack])
        assert mock_ws.call_args.kwargs.get("trick_room") is True

    # ── Action-type filtering ─────────────────────────────────────────────────

    def test_protect_not_affected(self):
        """Protect-family moves must not receive a turn-order multiplier."""
        state   = self._state()
        protect = make_action("Protect", "Protect")
        attack  = make_action("Dragon Claw", "Dragon Claw")

        with patch("decision.modules.find_member", return_value=None), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[protect, attack])

        assert protect.weight == pytest.approx(1.0)
        assert attack.weight  == pytest.approx(TurnOrderModule._MULTIPLIERS[1])

    def test_switch_not_affected(self):
        """Switch actions must not receive a turn-order multiplier."""
        state  = self._state()
        switch = make_action("Switch Sneasler", switch_target="Sneasler")
        attack = make_action("Dragon Claw", "Dragon Claw")

        with patch("decision.modules.find_member", return_value=None), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[switch, attack])

        assert switch.weight == pytest.approx(1.0)
        assert attack.weight == pytest.approx(TurnOrderModule._MULTIPLIERS[1])

    # ── Edge cases ────────────────────────────────────────────────────────────

    def test_noop_when_no_opponents(self):
        """No other Pokémon active → module is a no-op."""
        state   = make_state(my_actives=[make_mon("Garchomp")], opp_actives=[])
        actions = [make_action("Dragon Claw", "Dragon Claw")]

        with patch("decision.modules.find_member", return_value=None):
            self.module.score(state, slot=0, actions=actions)

        assert actions[0].weight == pytest.approx(1.0)

    def test_reason_string_appended(self):
        """A reason should be added to the action after scoring."""
        state   = self._state()
        actions = [make_action("Dragon Claw", "Dragon Claw")]

        with patch("decision.modules.find_member", return_value=None), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=actions)

        assert any("turn_order" in r for r in actions[0].reasons)


# ══════════════════════════════════════════════════════════════════════════════
# _assumed_ability / _effective_ability
# ══════════════════════════════════════════════════════════════════════════════

class TestEffectiveAbility:
    """Tests for the _assumed_ability and _effective_ability helpers."""

    # ── _assumed_ability ──────────────────────────────────────────────────────

    def test_assumed_ability_known_species_returns_top_rate(self):
        """Incineroar's top ability in the Champions data is Intimidate."""
        result = _assumed_ability("Incineroar")
        assert result == "Intimidate"

    def test_assumed_ability_another_known_species(self):
        """Farigiraf's top ability in the Champions data is Armor Tail."""
        result = _assumed_ability("Farigiraf")
        assert result == "Armor Tail"

    def test_assumed_ability_unknown_species_returns_none(self):
        """Species absent from the usage data return None (no assumption)."""
        with patch("decision.modules._ability_distribution", return_value=[]):
            result = _assumed_ability("UnknownMon")
        assert result is None

    def test_assumed_ability_empty_distribution_returns_none(self):
        """If ability_distribution returns an empty list, return None gracefully."""
        with patch("decision.modules._ability_distribution", return_value=[]):
            result = _assumed_ability("Garganacl")
        assert result is None

    # ── _effective_ability ────────────────────────────────────────────────────

    def test_effective_ability_returns_confirmed_ability(self):
        """When mon.ability is set, return it without touching usage data."""
        mon = make_mon("Incineroar", ability="Mold Breaker")
        with patch("decision.modules._ability_distribution") as mock_dist:
            result = _effective_ability(mon)
        # usage data must NOT be consulted when ability is already confirmed
        mock_dist.assert_not_called()
        assert result == "Mold Breaker"

    def test_effective_ability_falls_back_to_top_rate_when_none(self):
        """When mon.ability is None, fall back to the highest-usage ability."""
        mon = make_mon("Incineroar", ability=None)
        result = _effective_ability(mon)
        assert result == "Intimidate"

    def test_effective_ability_none_for_unknown_species(self):
        """Species not in usage data with no confirmed ability returns None."""
        mon = make_mon("FakeMon", ability=None)
        with patch("decision.modules._ability_distribution", return_value=[]):
            result = _effective_ability(mon)
        assert result is None

    def test_effective_ability_prankster_assumed_for_whimsicott(self):
        """Whimsicott with no confirmed ability is assumed to have Prankster."""
        mon = make_mon("Whimsicott", ability=None)
        result = _effective_ability(mon)
        assert result == "Prankster"

    def test_effective_ability_gale_wings_assumed_for_talonflame(self):
        """Talonflame with no confirmed ability is assumed to have Gale Wings."""
        mon = make_mon("Talonflame", ability=None)
        result = _effective_ability(mon)
        assert result == "Gale Wings"
