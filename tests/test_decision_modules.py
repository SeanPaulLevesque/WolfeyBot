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
    JointAdjuster,
    _build_actions,
    _PROTECT_MOVES,
    _FAKE_OUT_USERS,
    FakeOutModule,
    FieldConditionModule,
    OppProtectRecencyModule,
    ProtectValueModule,
    ConsecutiveProtectModule,
    DoublingAdjuster,
    CoordinationAdjuster,
    FakeOutAdjuster,
    SwitchCollisionAdjuster,
    SwitchModule,
    DamageOutputModule,
    ThreatEliminationModule,
    TurnOrderModule,
    SetterUrgencyModule,
    SetterDenialModule,
    _assumed_ability,
    _effective_ability,
    _assumed_item,
    _effective_item,
    _assumed_species,
    _offense_species,
    _defense_species,
)
from decision.modules import (
    _TR_SETTER_SPECIES,
    _TAILWIND_SETTER_SPECIES,
    _tw_setter_has_priority,
    build_turn_context,
    TurnContext,
    make_engine,
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

    def test_fires_unconditionally_with_weak_partner(self):
        """Gate removed (0.7.4): module fires whenever a fresh FO user is on field,
        regardless of what the partner threatens."""
        state = make_state(
            my_actives=[make_mon("Garchomp")],
            opp_actives=[make_mon("Incineroar"), make_mon("Farigiraf")],
            opp_last_moves=["", ""],
        )
        actions = self._actions()
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
# ProtectValueModule  (merged IncomingOHKOModule + ProtectModule)
# ══════════════════════════════════════════════════════════════════════════════

class TestProtectValueModule:
    """
    Tests for the merged ProtectValueModule (four multiplicative rows):
      ×2.5 when threatened; ×3.0 when partner clears a threat;
      ×0.4 in 1v1 endgame; ×0.4 in 2v1 numerical advantage.

    Key behavioral change vs old two-module design: in a 2v1 where the partner
    clears the threat, old code suppressed ×3.0 entirely (net 2.5×0.4=1.0);
    merged rows give 2.5×3.0×0.4=3.0.
    """
    module = ProtectValueModule()

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

    def _state_2v2(self) -> "BattleState":
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

    def _ohko_threat(self):
        return MagicMock(ohko_with_max_roll=True, is_ohko=True, hp_fraction_max=1.2)

    # ── Row 1: ×2.5 on OHKO threat ───────────────────────────────────────────

    def test_ohko_threat_boosts_protect(self):
        """When an opponent can OHKO us, Protect should receive ×2.5."""
        state   = self._state_normal()
        protect = make_action("Protect", "Protect")
        attack  = make_action("Dragon Claw", "Dragon Claw")

        ohko_threat = MagicMock(ohko_with_max_roll=True, is_ohko=True, hp_fraction_max=1.2)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]):
            self.module.score(state, slot=0, actions=[protect, attack])

        assert protect.weight == pytest.approx(ProtectValueModule.THREATENED_FACTOR)

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

        ohko_threat = MagicMock(ohko_with_max_roll=True, is_ohko=True, hp_fraction_max=1.2)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]):
            self.module.score(state, slot=0, actions=[attack])

        assert attack.weight == pytest.approx(1.0)

    def test_no_boost_when_threat_neutralized_before_acting(self):
        """OHKO threat dies before acting → not a live threat → no boost."""
        state   = self._state_normal()
        protect = make_action("Protect", "Protect")

        ohko_threat = MagicMock(ohko_with_max_roll=True, is_ohko=True, hp_fraction_max=1.2)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=True):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    # ── Row 2: ×3.0 when partner clears a threat ─────────────────────────────

    def test_partner_clears_threat_stacks_on_top_of_x25(self):
        """OHKO incoming + partner clears a threat → Protect ×2.5×3.0 = 7.5."""
        state   = self._state_2v2()
        protect = make_action("Protect", "Protect")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[self._ohko_threat()]), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=False), \
             patch("decision.modules._partner_can_ohko", return_value=True):
            self.module.score(state, slot=0, actions=[protect])

        expected = ProtectValueModule.THREATENED_FACTOR * ProtectValueModule.PARTNER_KO_FACTOR
        assert protect.weight == pytest.approx(expected)

    def test_no_partner_ko_boost_when_partner_cannot_ohko(self):
        """OHKO incoming but no partner can clear a threat → only ×2.5."""
        state   = self._state_2v2()
        protect = make_action("Protect", "Protect")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[self._ohko_threat()]), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=False), \
             patch("decision.modules._partner_can_ohko", return_value=False):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(ProtectValueModule.THREATENED_FACTOR)

    # ── Rows 3/4: ×0.4 cancelling rows ───────────────────────────────────────

    def test_1v1_endgame_cancels_x25(self):
        """In a 1v1, ×2.5×0.4=1.0 — Protect only delays."""
        state   = self._state_1v1()
        protect = make_action("Protect", "Protect")

        ohko_threat = MagicMock(ohko_with_max_roll=True, is_ohko=True, hp_fraction_max=1.2)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    def test_2v1_cancels_x25(self):
        """In a 2v1, ×2.5×0.4=1.0 — Protecting can't improve the outcome."""
        state   = self._state_2v1()
        protect = make_action("Protect", "Protect")

        ohko_threat = MagicMock(ohko_with_max_roll=True, is_ohko=True, hp_fraction_max=1.2)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]):
            self.module.score(state, slot=0, actions=[protect])

        assert protect.weight == pytest.approx(1.0)

    def test_2v1_with_partner_clearing_threat_gives_3(self):
        """2v1 + partner clears threat: new behavior is 2.5×3.0×0.4=3.0.
        (Old design suppressed ×3.0 in 2v1, giving only 2.5×0.4=1.0.)"""
        state   = self._state_2v1()
        protect = make_action("Protect", "Protect")

        ohko_threat = MagicMock(ohko_with_max_roll=True, is_ohko=True, hp_fraction_max=1.2)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=False), \
             patch("decision.modules._partner_can_ohko", return_value=True):
            self.module.score(state, slot=0, actions=[protect])

        expected = (ProtectValueModule.THREATENED_FACTOR
                    * ProtectValueModule.PARTNER_KO_FACTOR
                    * ProtectValueModule.ADVANTAGE_2V1_FACTOR)
        assert protect.weight == pytest.approx(expected)  # 2.5 × 3.0 × 0.4 = 3.0

    # ── Reason strings ────────────────────────────────────────────────────────

    def test_reason_incoming_ohko_prefix(self):
        """Row 1 reason must start with 'incoming_ohko:' (used by _protect_is_justified)."""
        state   = self._state_normal()
        protect = make_action("Protect", "Protect")

        ohko_threat = MagicMock(ohko_with_max_roll=True, is_ohko=True, hp_fraction_max=1.2)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[ohko_threat]):
            self.module.score(state, slot=0, actions=[protect])

        assert any(r.startswith("incoming_ohko:") for r in protect.reasons)

    def test_reason_protect_prefix_on_partner_clear(self):
        """Row 2 reason must start with 'protect:' (used by _protect_is_justified)."""
        state   = self._state_2v2()
        protect = make_action("Protect", "Protect")

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.incoming_damage", return_value=[self._ohko_threat()]), \
             patch("decision.modules._opp_neutralized_before_acting", return_value=False), \
             patch("decision.modules._partner_can_ohko", return_value=True):
            self.module.score(state, slot=0, actions=[protect])

        assert any(r.startswith("protect:") for r in protect.reasons)


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
# DoublingUpModule
# ══════════════════════════════════════════════════════════════════════════════

class TestDoublingAdjuster:
    """Phase-2 doubling penalty over an ordered candidate pair (slot_a, slot_b).
    Returns per-slot multipliers; the base penalty falls on the higher slot, the
    overkill near-veto on the *non*-killer."""
    adj = DoublingAdjuster()

    def _state(self, opp_last):
        return make_state(
            my_actives=[make_mon("Garganacl"), make_mon("Sylveon")],
            opp_actives=[make_mon("Garchomp", side="p2"),
                         make_mon("Incineroar", side="p2")],
            opp_last_moves=opp_last,
        )

    def test_both_attack_same_target_base_penalty_on_higher_slot(self):
        state = self._state(["Earthquake", ""])   # slot 0 didn't Protect
        a0 = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        a1 = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=5.0)
        with patch("decision.modules.find_member", return_value=None):  # other opp threatening
            fa, fb, reason = self.adj.factor(state, 0, a0, 1, a1)
        assert fa == 1.0
        assert fb == pytest.approx(0.40)   # not protected + other threatening
        assert reason and "doubling_up" in reason

    def test_different_targets_no_penalty(self):
        state = self._state(["", ""])
        a0 = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        a1 = make_action("Dragon Claw", "Dragon Claw", target_slot=1, weight=5.0)
        with patch("decision.modules.find_member", return_value=None):
            assert self.adj.factor(state, 0, a0, 1, a1) == (1.0, 1.0, None)

    def test_protected_last_turn_reduces_penalty(self):
        state = self._state(["Protect", ""])   # target used Protect last turn
        a0 = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        a1 = make_action("Close Combat", "Close Combat", target_slot=0, weight=5.0)
        with patch("decision.modules.find_member", return_value=None):
            fa, fb, _ = self.adj.factor(state, 0, a0, 1, a1)
        assert fb == pytest.approx(0.55)

    def test_confirmed_ohko_near_veto_on_non_killer(self):
        """When slot A already confirms the OHKO, slot B is the wasteful doubler
        → the near-veto (×0.05) falls on slot B, so the spread pair wins."""
        state = self._state(["Earthquake", ""])
        a0 = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=25.0)
        a1 = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=5.0)
        ctx = TurnContext(doomed={0: False, 1: False}, ohko={(0, "Wave Crash", 0)})
        with patch("decision.modules.find_member", return_value=None), \
             patch("decision.modules._ensure_turn_ctx", return_value=ctx):
            fa, fb, reason = self.adj.factor(state, 0, a0, 1, a1)
        assert fa == 1.0
        assert fb == pytest.approx(0.40 * DoublingAdjuster.CONFIRMED_OHKO_FACTOR)
        assert "overkill" in reason

    def test_confirmed_ohko_by_higher_slot_penalises_lower(self):
        """Symmetric: slot B confirms the kill → slot A is the wasteful doubler."""
        state = self._state(["Earthquake", ""])
        a0 = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=5.0)
        a1 = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=25.0)
        ctx = TurnContext(doomed={0: False, 1: False}, ohko={(1, "Wave Crash", 0)})
        with patch("decision.modules.find_member", return_value=None), \
             patch("decision.modules._ensure_turn_ctx", return_value=ctx):
            fa, fb, _ = self.adj.factor(state, 0, a0, 1, a1)
        assert fa == pytest.approx(0.40 * DoublingAdjuster.CONFIRMED_OHKO_FACTOR)
        assert fb == 1.0

    def test_only_one_live_opp_no_penalty(self):
        """2v1 — nowhere to spread, so doubling is forced and unpenalised."""
        opp0 = make_mon("Garchomp", side="p2")
        opp1 = make_mon("Incineroar", side="p2", fainted=True)
        state = make_state(
            my_actives=[make_mon("Garganacl"), make_mon("Sylveon")],
            opp_actives=[opp0, opp1], opp_last_moves=["", ""],
        )
        a0 = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        a1 = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=5.0)
        with patch("decision.modules.find_member", return_value=None):
            assert self.adj.factor(state, 0, a0, 1, a1) == (1.0, 1.0, None)

    def test_non_attack_pair_no_penalty(self):
        state = self._state(["", ""])
        a0 = make_action("Protect", "Protect", weight=3.0)
        a1 = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=5.0)
        assert self.adj.factor(state, 0, a0, 1, a1) == (1.0, 1.0, None)


class TestCoordinationAdjuster:
    """Penalise the uncoordinated split: a *gratuitous* lone Protect beside an
    attacking partner.  Justified Protects and double-Protects are untouched.
    Checks both orderings (the Protect may be slot a or slot b)."""
    adj = CoordinationAdjuster()

    def test_penalises_gratuitous_lone_protect_on_higher_slot(self):
        atk = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        protect = make_action("Protect", "Protect", weight=3.0)   # no justification
        fa, fb, reason = self.adj.factor(None, 0, atk, 1, protect)
        assert fa == 1.0
        assert fb == pytest.approx(CoordinationAdjuster.SPLIT_PENALTY)
        assert reason and "coordination" in reason

    def test_penalises_gratuitous_lone_protect_on_lower_slot(self):
        protect = make_action("Protect", "Protect", weight=3.0)
        atk = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        fa, fb, _ = self.adj.factor(None, 0, protect, 1, atk)
        assert fa == pytest.approx(CoordinationAdjuster.SPLIT_PENALTY)
        assert fb == 1.0

    def test_justified_protect_not_penalised(self):
        atk = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        protect = make_action("Protect", "Protect", weight=7.5)
        protect.reasons = ["incoming_ohko: OHKO threat -> x2.5"]
        assert self.adj.factor(None, 0, atk, 1, protect) == (1.0, 1.0, None)

    def test_double_protect_not_penalised(self):
        p0 = make_action("Protect", "Protect", weight=3.0)
        p1 = make_action("Protect", "Protect", weight=3.0)
        assert self.adj.factor(None, 0, p0, 1, p1) == (1.0, 1.0, None)

    def test_double_attack_not_penalised(self):
        a0 = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        a1 = make_action("Dragon Claw", "Dragon Claw", target_slot=1, weight=5.0)
        assert self.adj.factor(None, 0, a0, 1, a1) == (1.0, 1.0, None)


class TestFakeOutAdjuster:
    """A pair pays the Fake-Out adjustment exactly once: when a slot attacks,
    the partner's Fake-Out multiplier (known from ``ctx.fake_out`` plus the
    action itself) is divided back out — symmetric, so mirror pairs score the
    same regardless of slot order."""
    adj = FakeOutAdjuster()

    @staticmethod
    def _fo_state():
        """A fresh Incineroar makes Fake Out live; our species are unknown to
        find_member, so the partner-threat check stays conservative (fires)."""
        return make_state(
            my_actives=[make_mon(), make_mon()],
            opp_actives=[make_mon("Incineroar", side="p2"),
                         make_mon("Garchomp", side="p2")],
            my_team=[make_mon(), make_mon()],
            opp_last_moves=["", ""],
        )

    @staticmethod
    def _no_fo_state():
        """No Fake Out user on the field — the adjuster must stay inert."""
        return make_state(
            my_actives=[make_mon(), make_mon()],
            opp_actives=[make_mon("Garchomp", side="p2")],
            my_team=[make_mon(), make_mon()],
            opp_last_moves=[""],
        )

    def test_frees_partner_when_lower_slot_attacks(self):
        atk = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        freed = make_action("Close Combat", "Close Combat", target_slot=0, weight=2.5)
        fa, fb, reason = self.adj.factor(self._fo_state(), 0, atk, 1, freed)
        assert fa == 1.0
        assert fb == pytest.approx(2.0)   # 1 / 0.5 — discount undone
        assert reason and "fake_out" in reason

    def test_frees_partner_when_higher_slot_attacks(self):
        protect = make_action("Protect", "Protect", weight=9.0)
        atk = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        fa, fb, reason = self.adj.factor(self._fo_state(), 0, protect, 1, atk)
        assert fa == pytest.approx(1.0 / 2.0)   # boost divided back out
        assert fb == 1.0
        assert reason and "fake_out" in reason

    def test_noop_without_fake_out_threat(self):
        protect = make_action("Protect", "Protect", weight=3.0)
        atk = make_action("Close Combat", "Close Combat", target_slot=0, weight=2.5)
        assert self.adj.factor(self._no_fo_state(), 0, protect, 1, atk) == (1.0, 1.0, None)

    def test_noop_for_attacks_without_fake_out_threat(self):
        a0 = make_action("Wave Crash", "Wave Crash", target_slot=0, weight=5.0)
        a1 = make_action("Dragon Claw", "Dragon Claw", target_slot=1, weight=5.0)
        assert self.adj.factor(self._no_fo_state(), 0, a0, 1, a1) == (1.0, 1.0, None)


class TestSwitchCollisionAdjuster:
    adj = SwitchCollisionAdjuster()

    def test_vetoes_same_switch(self):
        s0 = make_action("Switch Garchomp", switch_target="Garchomp", weight=4.0)
        s1 = make_action("Switch Garchomp", switch_target="Garchomp", weight=4.0)
        fa, fb, reason = self.adj.factor(None, 0, s0, 1, s1)
        assert fa == 1.0 and fb == 0.0
        assert reason and "switch_collision" in reason

    def test_allows_different_switches(self):
        s0 = make_action("Switch Garchomp", switch_target="Garchomp", weight=4.0)
        s1 = make_action("Switch Venusaur", switch_target="Venusaur", weight=4.0)
        assert self.adj.factor(None, 0, s0, 1, s1) == (1.0, 1.0, None)

    def test_allows_switch_plus_move(self):
        s0 = make_action("Switch Garchomp", switch_target="Garchomp", weight=4.0)
        a1 = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=5.0)
        assert self.adj.factor(None, 0, s0, 1, a1) == (1.0, 1.0, None)


class TestCoordinate:
    """The joint phase-2 selector picks the best *pair*.  With the joint adjusters
    inert it reduces to each slot's independent best; otherwise a real cross-slot
    effect can move a slot off its per-slot optimum (the old recoordinate
    repairs, now emergent from choosing the highest-value pair)."""

    def _state(self):
        return make_state(
            my_actives=[make_mon("Venusaur"), make_mon("Kingambit")],
            opp_actives=[make_mon("Basculegion", side="p2"),
                         make_mon("Talonflame", side="p2")],
            moves_per_slot=[[{"move": "x"}], [{"move": "y"}]],   # two decided slots
            opp_last_moves=["", ""],
        )

    def test_no_joint_effect_picks_independent_best(self):
        """All adjusters inert → argmax of w0×w1 = each slot's own best."""
        a0a = make_action("Sludge Bomb", "Sludge Bomb", target_slot=1, weight=6.0)
        a0b = make_action("Giga Drain", "Giga Drain", target_slot=1, weight=3.0)
        a1a = make_action("Iron Head", "Iron Head", target_slot=1, weight=7.0)
        a1b = make_action("Low Kick", "Low Kick", target_slot=1, weight=2.0)
        eng = make_engine()
        eng.scored_actions = lambda st, sl: ([a0a, a0b] if sl == 0 else [a1a, a1b])
        with patch("decision.modules._ensure_turn_ctx", return_value=TurnContext()), \
             patch("decision.modules.find_member", return_value=None):
            chosen, ranked = eng.coordinate(self._state())
        assert chosen[0].label == "Sludge Bomb"   # slot 0's best
        assert chosen[1].label == "Iron Head"     # slot 1's best

    def test_overkill_spreads_onto_survivor(self):
        """Slot 1 confirm-OHKOs opp 0 → slot 0 should hit the survivor (opp 1)
        rather than double the dying target — the emergent focus-fire 'redirect'."""
        a0_double = make_action("Giga Drain", "Giga Drain", target_slot=0, weight=5.0)
        a0_spread = make_action("Sludge Bomb", "Sludge Bomb", target_slot=1, weight=4.0)
        a1_kill = make_action("Kowtow Cleave", "Kowtow Cleave", target_slot=0, weight=25.0)
        ctx = TurnContext(doomed={0: False, 1: False}, ohko={(1, "Kowtow Cleave", 0)})
        eng = make_engine()
        eng.scored_actions = lambda st, sl: ([a0_double, a0_spread] if sl == 0 else [a1_kill])
        with patch("decision.modules._ensure_turn_ctx", return_value=ctx), \
             patch("decision.modules.find_member", return_value=None):
            chosen, _ = eng.coordinate(self._state())
        assert chosen[0].target_slot == 1   # spread to the survivor
        assert chosen[1].target_slot == 0   # killer keeps its kill

    def test_decoordination_prefers_double_attack(self):
        """A gratuitous lone Protect beside an attacking partner loses to the
        double-attack pair."""
        p0 = make_action("Protect", "Protect", weight=3.0)        # gratuitous
        atk0 = make_action("Rock Tomb", "Rock Tomb", target_slot=0, weight=4.0)
        atk1 = make_action("Iron Head", "Iron Head", target_slot=1, weight=5.0)
        eng = make_engine()
        eng.scored_actions = lambda st, sl: ([p0, atk0] if sl == 0 else [atk1])
        with patch("decision.modules._ensure_turn_ctx", return_value=TurnContext()), \
             patch("decision.modules.find_member", return_value=None):
            chosen, _ = eng.coordinate(self._state())
        assert chosen[0].move_name == "Rock Tomb"   # attacks alongside the partner

    def test_switch_collision_avoided(self):
        """Both slots' top pick is the same switch → the pair is vetoed, so one
        slot takes its next-best (a different switch)."""
        s0g = make_action("Switch Garchomp", switch_target="Garchomp", weight=5.0)
        s0b = make_action("Switch Basculegion", switch_target="Basculegion", weight=4.0)
        s1g = make_action("Switch Garchomp", switch_target="Garchomp", weight=5.0)
        eng = make_engine()
        eng.scored_actions = lambda st, sl: ([s0g, s0b] if sl == 0 else [s1g])
        with patch("decision.modules._ensure_turn_ctx", return_value=TurnContext()), \
             patch("decision.modules.find_member", return_value=None):
            chosen, _ = eng.coordinate(self._state())
        assert not (chosen[0].switch_target == "Garchomp"
                    and chosen[1].switch_target == "Garchomp")
        assert chosen[0].switch_target == "Basculegion"


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
# Setter urgency  (SetterUrgencyModule)
# ══════════════════════════════════════════════════════════════════════════════

class TestSetterUrgency:
    """One module, one boost per turn: Trick Room ×2.0 first, else Tailwind
    ×1.5.  It boosts *every* attack on a preventable-setter board (any target),
    biasing the slot toward attacking over going passive."""
    urgency = SetterUrgencyModule()

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
        self.urgency.score(state, 0, actions)
        for a in actions:
            assert a.weight == 1.0

    def test_tr_setter_boosts_attacks(self):
        """Farigiraf on field → attack moves get ×2.0, Protect and Switch unchanged."""
        state = make_state(opp_actives=[make_mon("Farigiraf"), make_mon("Incineroar")])
        actions = self._actions()
        self.urgency.score(state, 0, actions)

        protect = next(a for a in actions if a.move_name == "Protect")
        earth   = next(a for a in actions if a.move_name == "Earth Power")
        sludge  = next(a for a in actions if a.move_name == "Sludge Bomb")
        switch  = next(a for a in actions if a.is_switch)

        assert protect.weight == pytest.approx(1.0)
        assert earth.weight   == pytest.approx(SetterUrgencyModule.TR_URGENCY)
        assert sludge.weight  == pytest.approx(SetterUrgencyModule.TR_URGENCY)
        assert switch.weight  == pytest.approx(1.0)

    def test_tw_setter_boosts_attacks(self):
        """Noivern (TW setter) on field → attack moves get ×1.5, Protect and Switch unchanged."""
        state = make_state(opp_actives=[make_mon("Noivern"), make_mon("Garchomp")])
        actions = self._actions()
        self.urgency.score(state, 0, actions)

        protect = next(a for a in actions if a.move_name == "Protect")
        earth   = next(a for a in actions if a.move_name == "Earth Power")
        switch  = next(a for a in actions if a.is_switch)

        assert protect.weight == pytest.approx(1.0)
        assert earth.weight   == pytest.approx(SetterUrgencyModule.TW_URGENCY)
        assert switch.weight  == pytest.approx(1.0)

    def test_tr_takes_priority_over_tw(self):
        """Both a TR setter and a TW setter present → only the TR urgency applies
        (the module's if/elif structure makes the two mutually exclusive)."""
        state = make_state(
            opp_actives=[make_mon("Farigiraf"), make_mon("Noivern")]
        )
        actions = self._actions()
        self.urgency.score(state, 0, actions)

        earth = next(a for a in actions if a.move_name == "Earth Power")
        # TR urgency (2.0) only — not TR×TW (3.0).
        assert earth.weight == pytest.approx(SetterUrgencyModule.TR_URGENCY)

    def test_fainted_setter_does_not_boost(self):
        """A fainted setter is not active — no boost applied."""
        fainted_setter = make_mon("Farigiraf", fainted=True)
        state = make_state(opp_actives=[fainted_setter, make_mon("Incineroar")])
        actions = self._actions()
        self.urgency.score(state, 0, actions)
        for a in actions:
            assert a.weight == 1.0

    def test_reason_string_appended(self):
        """Reason string is added to boosted attack actions."""
        state = make_state(opp_actives=[make_mon("Cofagrigus")])
        actions = self._actions()
        self.urgency.score(state, 0, actions)

        earth = next(a for a in actions if a.move_name == "Earth Power")
        assert any("trick_room" in r for r in earth.reasons)
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
        self.urgency.score(state, 0, actions)
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
        self.urgency.score(state, 0, actions)

        earth = next(a for a in actions if a.move_name == "Earth Power")
        assert earth.weight == pytest.approx(SetterUrgencyModule.TR_URGENCY)
        assert any("re-set risk" in r for r in earth.reasons)

    def test_tw_setter_no_boost_when_tw_active_with_turns_left(self):
        """TW setter present but Tailwind is already active (≥2 turns left) → no boost."""
        state = make_state(
            opp_actives=[make_mon("Noivern"), make_mon("Garchomp")],
            opp_tailwind=True,
            opp_tailwind_turns_left=3,
        )
        actions = self._actions()
        self.urgency.score(state, 0, actions)
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
        self.urgency.score(state, 0, actions)

        earth = next(a for a in actions if a.move_name == "Earth Power")
        assert earth.weight == pytest.approx(SetterUrgencyModule.TW_URGENCY)
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
        self.urgency.score(state, 0, actions)
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
        self.urgency.score(state, 0, actions)
        for a in actions:
            assert a.weight == pytest.approx(1.0), f"{a.label} should be unaffected"


class TestSetterDenial:
    module = SetterDenialModule()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _ohko_result():
        return make_damage_result(damage_min=110, damage_max=130,
                                  damage_avg=120.0, defender_hp=100)

    @staticmethod
    def _non_ohko_result():
        return make_damage_result(damage_min=40, damage_max=60,
                                  damage_avg=50.0, defender_hp=100)

    # Denial reads the TurnContext OHKO matrix, which is built from
    # moves_per_slot — so each state must declare the move its action uses
    # (outgoing_damage itself is patched per-test).
    _SLOT_MOVES = [[
        {"move": "Shadow Ball"}, {"move": "Air Slash"}, {"move": "Dragon Claw"},
        {"move": "Dazzling Gleam"}, {"move": "Rock Tomb"},
    ]]

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
            moves_per_slot=self._SLOT_MOVES,
            trick_room=False,
        )
        action = make_action("Shadow Ball", "Shadow Ball", target_slot=0, weight=3.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(
            3.0 * SetterDenialModule.TR_DENIAL
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
            moves_per_slot=self._SLOT_MOVES,
            opp_tailwind=False,
        )
        action = make_action("Air Slash", "Air Slash", target_slot=0, weight=3.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(
            3.0 * SetterDenialModule.TW_DENIAL
        )

    def test_revealed_tailwind_move_triggers_boost(self):
        """Any opponent with 'Tailwind' revealed and no priority ability → deniable."""
        unknown_setter = make_mon("Charizard", side="p2", moves=["Tailwind"])
        our_mon = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[unknown_setter],
            my_team=[our_mon],
            moves_per_slot=self._SLOT_MOVES,
            opp_tailwind=False,
        )
        action = make_action("Dragon Claw", "Dragon Claw", target_slot=0, weight=2.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(
            2.0 * SetterDenialModule.TW_DENIAL
        )

    def test_tr_denial_claims_action_over_tw(self):
        """Both a TR and a TW setter deniable + an OHKO targeting the TR setter →
        Trick Room denial claims the action (×2.0, stays on the TR setter); the
        Tailwind denial does not also fire on it (TR priority preserved via the
        per-action claim)."""
        farigiraf = make_mon("Farigiraf", side="p2")   # TR setter, slot 0
        noivern   = make_mon("Noivern", side="p2")     # TW setter, slot 1
        our_mon   = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[farigiraf, noivern],
            my_team=[our_mon],
            moves_per_slot=self._SLOT_MOVES,
            trick_room=False,
            opp_tailwind=False,
        )
        action = make_action("Shadow Ball", "Shadow Ball", target_slot=0, weight=3.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.target_slot == 0                                  # stayed on the TR setter
        assert action.weight == pytest.approx(3.0 * SetterDenialModule.TR_DENIAL)

    # ── No denial when OHKO is impossible ────────────────────────────────────

    def test_no_boost_when_cannot_ohko_tr_setter(self):
        """Non-OHKO attack on TR setter → no bonus (setter survives and sets TR)."""
        farigiraf = make_mon("Farigiraf", side="p2")
        our_mon   = make_mon("Garganacl")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[farigiraf],
            my_team=[our_mon],
            moves_per_slot=self._SLOT_MOVES,
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
            moves_per_slot=self._SLOT_MOVES,
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
            moves_per_slot=self._SLOT_MOVES,
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
            moves_per_slot=self._SLOT_MOVES,
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
            moves_per_slot=self._SLOT_MOVES,
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
            moves_per_slot=self._SLOT_MOVES,
            opp_tailwind=False,
        )
        action = make_action("Rock Tomb", "Rock Tomb", target_slot=0, weight=2.0)

        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[self._ohko_result()]), \
             patch("decision.modules.will_outspeed", return_value=1.0):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(
            2.0 * SetterDenialModule.TW_DENIAL
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
            moves_per_slot=self._SLOT_MOVES,
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

    def test_does_not_veto_partner_switch_collision(self):
        """SwitchModule is partner-blind now: the two-slots-switch-to-the-same-mon
        veto moved to the joint phase (SwitchCollisionAdjuster, see
        TestSwitchCollisionAdjuster).  Scoring a slot here must NOT zero a switch
        just because a partner decision targets the same bench mon."""
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

        assert switch_action.weight != 0.0   # not vetoed by the per-slot module

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

        # offense gain 0 (current and switch-in deal the same) → (1+g)=1.0;
        # threatened + survives → × ESCAPE_FACTOR.
        expected = SwitchModule.TEMPO_FACTOR * 1.0 * SwitchModule.ESCAPE_FACTOR
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
                   return_value=[MagicMock(ohko_with_max_roll=True, is_ohko=True, hp_fraction_max=1.2)]):  # everything OHKO'd
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
        """A move that does 80% HP should weight ×(0.5 + 3.5·0.80) = 3.3."""
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

        expected = 0.5 + 3.5 * 0.80  # = 3.3
        assert action.weight == pytest.approx(expected)

    def test_neutralized_damaging_move_floors_at_half(self):
        """A DAMAGING move that deals 0 (type immunity / dead matchup) floors at
        ×0.5 — below a healthy switch (so we leave a useless matchup) but above
        sacking into an OHKO.  ("Ghost Move" is unknown → treated as damaging.)"""
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

        assert action.weight == pytest.approx(0.5)

    def test_status_move_keeps_baseline(self):
        """A STATUS move deals 0 by design, not by failure, so DamageOutput
        leaves it at the ×1.0 baseline (ProtectValue / SetterUrgency score it) —
        it must NOT get the damaging-move floor."""
        our_mon = make_mon("Garganacl")
        opp_mon = make_mon("Garchomp", side="p2")
        state = make_state(
            my_actives=[our_mon],
            opp_actives=[opp_mon],
            my_team=[our_mon],
        )
        action = make_action("Protect", "Protect")   # category Status

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
            moves_per_slot=[[{"move": "Wave Crash"}]],
        )
        # Targets are first-class now: the candidate is already aimed at opp 0.
        action = make_action("Wave Crash", "Wave Crash", target_slot=0)

        ohko_result = make_damage_result(damage_min=110, damage_max=130,
                                          damage_avg=120.0, defender_hp=100)
        mock_tm = make_mock_member()

        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[ohko_result]), \
             patch("decision.modules._ko_before_acting", return_value=False):
            self.module.score(state, slot=0, actions=[action])

        assert action.weight == pytest.approx(ThreatEliminationModule.GUARANTEED_OHKO)
        assert action.target_slot == 0   # unchanged — fixed at build time

    def test_no_kill_credit_when_doomed(self):
        """'Will I die before I act?' cancels the kill credit: ×5 is applied and
        the ×0.2 doom row multiplies it back to net ×1.0."""
        our_mon = make_mon("Garganacl")
        opp_mon = make_mon("Garchomp", side="p2")
        state = make_state(
            my_actives=[our_mon], opp_actives=[opp_mon], my_team=[our_mon],
            moves_per_slot=[[{"move": "Wave Crash"}]],
        )
        action = make_action("Wave Crash", "Wave Crash")
        ohko_result = make_damage_result(damage_min=110, damage_max=130,
                                          damage_avg=120.0, defender_hp=100)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[ohko_result]), \
             patch("decision.modules._ko_before_acting", return_value=True):
            self.module.score(state, slot=0, actions=[action])
        assert action.weight == pytest.approx(1.0)   # gated off — undeliverable kill


class TestTurnContext:
    """build_turn_context precomputes the doomed + guaranteed-OHKO facts that
    replace the threat_elimination reason as the kill control-signal."""

    def _state(self):
        return make_state(
            my_actives=[make_mon("Garganacl")],
            opp_actives=[make_mon("Garchomp", side="p2"),
                         make_mon("Incineroar", side="p2")],
            my_team=[make_mon("Garganacl")],
            moves_per_slot=[[{"move": "Wave Crash"}, {"move": "Rock Tomb"}]],
        )

    def test_records_guaranteed_ohko_and_not_doomed(self):
        ohko = make_damage_result(damage_min=110, damage_max=130,
                                  damage_avg=120.0, defender_hp=100)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[ohko]), \
             patch("decision.modules._ko_before_acting", return_value=False):
            ctx = build_turn_context(self._state())
        assert ctx.is_doomed(0) is False
        assert ctx.guarantees_ohko(0, "Wave Crash", 0) is True
        assert ctx.guarantees_ohko(0, "Rock Tomb", 1) is True
        assert ctx.guarantees_ohko(0, "Wave Crash", 5) is False   # no such opp slot

    def test_records_doomed_and_no_ohko_on_survivor(self):
        non_ohko = make_damage_result(damage_min=40, damage_max=60,
                                      damage_avg=50.0, defender_hp=100)
        mock_tm = make_mock_member()
        with patch("decision.modules.find_member", return_value=mock_tm), \
             patch("decision.modules.outgoing_damage", return_value=[non_ohko]), \
             patch("decision.modules._ko_before_acting", return_value=True):
            ctx = build_turn_context(self._state())
        assert ctx.is_doomed(0) is True
        assert ctx.guarantees_ohko(0, "Wave Crash", 0) is False   # not a guaranteed OHKO


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

    def test_effective_ability_mega_forme_assumed_for_charizard(self):
        """Unrevealed Charizard resolves to Mega-Y (99% mega) → Drought,
        not the base forme's Solar Power."""
        mon = make_mon("Charizard", ability=None)
        result = _effective_ability(mon)
        assert result == "Drought"


# ══════════════════════════════════════════════════════════════════════════════
# _assumed_species (forme inference)
# ══════════════════════════════════════════════════════════════════════════════

class TestAssumedSpecies:
    """Population-weighted forme inference for unrevealed opponents."""

    def test_revealed_mega_passes_through(self):
        """|detailschange| already rewrote species — no inference needed."""
        mon = make_mon("Charizard-Mega-X")
        assert _assumed_species(mon) == "Charizard-Mega-X"

    def test_unrevealed_majority_mega_resolves_to_mega(self):
        """99% of Charizards hold a stone; Mega-Y dominates (81%)."""
        mon = make_mon("Charizard", item=None)
        assert _assumed_species(mon) == "Charizard-Mega-Y"

    def test_revealed_non_stone_item_demotes_to_base(self):
        """A revealed berry means it cannot mega — model the base forme."""
        mon = make_mon("Charizard", item="Sitrus Berry")
        assert _assumed_species(mon) == "Charizard"

    def test_revealed_stone_keeps_mega_assumption(self):
        """A revealed mega stone confirms the mega path."""
        mon = make_mon("Charizard", item="Charizardite Y")
        assert _assumed_species(mon) == "Charizard-Mega-Y"

    def test_revealed_stone_forces_mega_for_base_dominant_species(self):
        """Venusaur is base-dominant by population (resolves to base when its
        item is unknown), but a REVEALED Venusaurite means it WILL mega-evolve —
        so it must resolve straight to Venusaur-Mega, not fall back to base."""
        from data.sets import item_distribution
        stone = item_distribution("Venusaur-Mega")[0][0]   # the actual stone string
        assert _assumed_species(make_mon("Venusaur", item=None)) == "Venusaur"
        assert _assumed_species(make_mon("Venusaur", item=stone)) == "Venusaur-Mega"

    def test_minority_mega_stays_base(self):
        """Aerodactyl is only 21.9% mega — stays base."""
        mon = make_mon("Aerodactyl", item=None)
        assert _assumed_species(mon) == "Aerodactyl"

    def test_no_mega_entries_stays_base(self):
        """Kingambit has no mega forme in the data."""
        mon = make_mon("Kingambit", item=None)
        assert _assumed_species(mon) == "Kingambit"

    def test_lopunny_resolves_to_mega(self):
        """Base Lopunny has no data entry — population is 100% mega."""
        mon = make_mon("Lopunny", item=None)
        assert _assumed_species(mon) == "Lopunny-Mega"


class TestStanceForme:
    """Aegislash uses Blade (140/50) for the damage it DEALS and Shield (50/140)
    for the damage it RECEIVES — the safe/simple fixed rule, regardless of its
    currently-revealed stance.  Other species pass straight through."""

    def test_aegislash_offense_is_blade_defense_is_shield(self):
        ae = make_mon("Aegislash")
        assert _offense_species(ae) == "Aegislash-Blade"
        assert _defense_species(ae) == "Aegislash"

    def test_revealed_blade_still_resolves_both_ways(self):
        ae = make_mon("Aegislash-Blade")
        assert _offense_species(ae) == "Aegislash-Blade"   # deals → Blade
        assert _defense_species(ae) == "Aegislash"         # receives → Shield

    def test_non_stance_species_pass_through(self):
        gar = make_mon("Garchomp")
        assert _offense_species(gar) == _defense_species(gar) == "Garchomp"
        # passthrough still honours the mega forme inference
        chari = make_mon("Charizard", item=None)
        assert _offense_species(chari) == "Charizard-Mega-Y"
        assert _defense_species(chari) == "Charizard-Mega-Y"


class TestMegaAbilityRefresh:
    """Mega-evolution replaces the base ability; a base ability revealed BEFORE
    a mon megas is stale, so any assumed -Mega forme uses the mega's ability
    (systematic — no per-species list)."""

    def test_stale_base_ability_overridden_on_mega(self):
        # Altaria reveals Cloud Nine pre-mega; post-mega it's Pixilate.
        mon = make_mon("Altaria-Mega"); mon.ability = "Cloud Nine"
        assert _effective_ability(mon) == "Pixilate"

    def test_unrevealed_assumed_mega_uses_mega_ability(self):
        mon = make_mon("Altaria"); mon.ability = None   # population -> Altaria-Mega
        assert _effective_ability(mon) == "Pixilate"

    def test_non_mega_revealed_ability_unchanged(self):
        mon = make_mon("Garchomp"); mon.ability = "Sand Veil"
        assert _effective_ability(mon) == "Sand Veil"


# ══════════════════════════════════════════════════════════════════════════════
# _assumed_item / _effective_item
# ══════════════════════════════════════════════════════════════════════════════

class TestEffectiveItem:
    """Item inference: revealed > consumed(None) > usage-stats guess."""

    # ── _assumed_item ─────────────────────────────────────────────────────────

    def test_assumed_item_above_threshold(self):
        """Whimsicott's top item (Focus Sash, 74.9%) clears the 40% threshold."""
        assert _assumed_item("Whimsicott") == "Focus Sash"

    def test_assumed_item_below_threshold_returns_none(self):
        """Garchomp's top item (Choice Scarf, 27.9%) is under 40% → None."""
        assert _assumed_item("Garchomp") is None

    def test_assumed_item_no_data_returns_none(self):
        with patch("decision.modules._item_distribution", return_value=[]):
            assert _assumed_item("FakeMon") is None

    # ── _effective_item ───────────────────────────────────────────────────────

    def test_effective_item_revealed_wins(self):
        """A revealed item is used as-is, no usage-data lookup."""
        mon = make_mon("Whimsicott", item="Covert Cloak")
        with patch("decision.modules._item_distribution") as mock_dist:
            result = _effective_item(mon)
        mock_dist.assert_not_called()
        assert result == "Covert Cloak"

    def test_effective_item_consumed_returns_none(self):
        """A popped Sash / eaten berry is never re-assumed."""
        mon = make_mon("Whimsicott", item=None, item_consumed=True)
        assert _effective_item(mon) is None

    def test_effective_item_falls_back_to_assumed(self):
        """Unrevealed Whimsicott is assumed to hold Focus Sash."""
        mon = make_mon("Whimsicott", item=None)
        assert _effective_item(mon) == "Focus Sash"

    def test_effective_item_mega_holder_assumed_stone_not_sash(self):
        """Glimmora is 75.5% mega: the assumed item is its stone (damage-inert,
        not KO-preventing) — NOT the base forme's Focus Sash."""
        mon = make_mon("Glimmora", item=None)
        assert _effective_item(mon) == "Glimmoranite"

    # ── integration: forme + item inference feed the OHKO facts ─────────────

    @staticmethod
    def _single_slot_state(our_species, opp_species, *, designated_mega=None,
                           opp_boosts=None):
        """Minimal 1v1 BattleState for fact-loop integration tests."""
        from battle import BattleState

        s = BattleState(battle_id="test", my_side="p1")
        s.turn = 1
        ours = make_mon(our_species, side="p1")
        s.my_actives = [ours]
        s.my_team = [ours]
        opp = make_mon(opp_species, hp=100, max_hp=100, side="p2",
                       hp_is_percentage=True)
        if opp_boosts:
            opp.boosts.update(opp_boosts)
        s.opp_actives = [opp]
        s.available_switches = []
        from team import find_member
        tm = find_member(our_species)
        s.moves_per_slot = [[{"move": m} for m in tm.moves]]
        s.my_last_moves = [""]
        s.opp_last_moves = [""]
        s.my_slot_decisions = [None]
        s.my_disabled_moves = [None]
        s.my_encored_moves = [None]
        s.opp_tailwind = False
        s.opp_tailwind_turns_left = 0
        s.trick_room = False
        s.trick_room_turns_left = 0
        s.weather = None
        s.my_tailwind = False
        s.designated_mega = designated_mega
        return s

    def test_sash_assumption_blocks_single_hit_ohko_fact(self):
        """An unrevealed Whimsicott (assumed Focus Sash) at full HP must not
        register a single-hit guaranteed-OHKO triple in ctx.ohko, while a
        multi-hit kill (Dual Wingbeat breaks Sash) still does."""
        from battle import BattleState

        s = BattleState(battle_id="test", my_side="p1")
        s.turn = 1
        aero = make_mon("Aerodactyl", side="p1")
        s.my_actives = [aero]
        s.my_team = [aero]
        # Mega stats needed: base Aerodactyl's Dual Wingbeat min roll (124)
        # misses Whimsicott's 136 HP; the designated mega's (149) connects.
        s.designated_mega = "Aerodactyl"
        s.opp_actives = [make_mon("Whimsicott", hp=100, max_hp=100,
                                  side="p2", hp_is_percentage=True)]
        s.available_switches = []
        s.moves_per_slot = [[{"move": "Dual Wingbeat"}, {"move": "Ice Fang"}]]
        s.my_last_moves = [""]
        s.opp_last_moves = [""]
        s.my_slot_decisions = [None]
        s.my_disabled_moves = [None]
        s.my_encored_moves = [None]
        s.opp_tailwind = False
        s.opp_tailwind_turns_left = 0
        s.trick_room = False
        s.trick_room_turns_left = 0
        s.weather = None
        s.my_tailwind = False

        ctx = build_turn_context(s)
        single_hit_kills = {(slot, mv, t) for (slot, mv, t) in ctx.ohko
                            if mv == "Ice Fang"}
        multi_hit_kills = {(slot, mv, t) for (slot, mv, t) in ctx.ohko
                           if mv == "Dual Wingbeat"}
        # Ice Fang would OHKO a frail Whimsicott, but the assumed Sash blocks
        # the fact; Dual Wingbeat (2 hits) breaks Sash and keeps it.
        assert not single_hit_kills
        assert (0, "Dual Wingbeat", 0) in multi_hit_kills


# ══════════════════════════════════════════════════════════════════════════════
# Opponent stat boosts feed the TurnContext facts
# ══════════════════════════════════════════════════════════════════════════════

class TestPredictedIncomingLog:
    """build_turn_context records predicted worst-case incoming damage per
    (opponent -> our mon) for offline defensive-accuracy analysis (0.8.4)."""

    def test_predicted_incoming_populated(self):
        s = TestEffectiveItem._single_slot_state("Garchomp", "Incineroar")
        s.turn = 3
        build_turn_context(s)
        pred = s.predicted_incoming_log.get(3)
        assert pred, "predicted_incoming_log should be populated"
        e = pred[0]
        assert e["a"] == "Incineroar" and e["df"] == "Garchomp"
        # per-assessed-move map: {move: predicted_frac}
        assert isinstance(e["mvs"], dict) and e["mvs"]
        assert all(isinstance(k, str) and 0.0 <= v <= 2.0 for k, v in e["mvs"].items())


class TestOpponentBoostFacts:
    """Visible opponent boosts (Swords Dance, Calm Mind, …) must flow into the
    incoming-threat and kill-credit facts.

    These pin the *plumbing*, not the strategy: how the engine should respond
    to a setup sweeper (it currently Protects harder, then switches — never
    attacks the boosted threat down) is a known gap tracked separately.
    """

    def test_attack_boost_creates_incoming_ohko_fact(self):
        """Unboosted Kingambit cannot OHKO Sneasler (Iron Head 97-115 vs 171);
        at +2 Atk (Swords Dance) it guarantees the KO (193-228) — the boost
        must surface in incoming_ohko AND incoming_certain."""
        helper = TestEffectiveItem._single_slot_state

        unboosted = build_turn_context(helper("Sneasler", "Kingambit"))
        assert 0 not in unboosted.incoming_ohko[0]
        assert 0 not in unboosted.incoming_certain[0]

        boosted = build_turn_context(
            helper("Sneasler", "Kingambit", opp_boosts={"atk": 2}))
        assert 0 in boosted.incoming_ohko[0]
        assert 0 in boosted.incoming_certain[0]

    def test_defense_boost_removes_our_kill_credit(self):
        """Mega Aerodactyl's Dual Wingbeat guarantees the KO on Whimsicott
        (min 149 vs 136 HP); at +2 Def the min roll halves (76) — the boost
        must remove the ctx.ohko triple."""
        helper = TestEffectiveItem._single_slot_state

        unboosted = build_turn_context(
            helper("Aerodactyl", "Whimsicott", designated_mega="Aerodactyl"))
        assert (0, "Dual Wingbeat", 0) in unboosted.ohko

        boosted = build_turn_context(
            helper("Aerodactyl", "Whimsicott", designated_mega="Aerodactyl",
                   opp_boosts={"def": 2}))
        assert (0, "Dual Wingbeat", 0) not in boosted.ohko


class TestConditionalAbilityPlumbing:
    """Conditional-fact abilities (status / Flash Fire) must reach
    build_turn_context's incoming-threat predictions, not just the damage layer.

    Pins the plumbing at the call site: the opponent's HP / status / flash-fire
    state has to be forwarded into incoming_damage."""

    @staticmethod
    def _worst_incoming(state) -> float:
        """Largest predicted incoming damage fraction over all assessed moves."""
        build_turn_context(state)
        preds = state.predicted_incoming_log[state.turn]
        return max((max(p["mvs"].values()) for p in preds if p["mvs"]),
                   default=0.0)

    def _opp(self, opp_species, *, ability, status=None, flash_fire=False):
        s = TestEffectiveItem._single_slot_state("Venusaur", opp_species)
        opp = s.opp_actives[0]
        opp.ability = ability          # revealed → _effective_ability honours it
        opp.status = status
        opp.flash_fire_active = flash_fire
        return s

    def test_guts_status_raises_incoming(self):
        """A statused Guts attacker hits ~1.5× harder with physical moves —
        the status must flow through to the incoming prediction."""
        clean = self._worst_incoming(self._opp("Conkeldurr", ability="Guts"))
        statused = self._worst_incoming(
            self._opp("Conkeldurr", ability="Guts", status="par"))
        assert clean > 0
        assert statused == pytest.approx(clean * 1.5, rel=0.1)

    def test_flash_fire_flag_raises_fire_incoming(self):
        """An active Flash Fire flag (parser-tracked) boosts the opponent's Fire
        moves by 50% in the incoming facts.  Arcanine leads with Flare Blitz."""
        cold = self._worst_incoming(self._opp("Arcanine", ability="Flash Fire"))
        hot = self._worst_incoming(
            self._opp("Arcanine", ability="Flash Fire", flash_fire=True))
        assert cold > 0
        assert hot == pytest.approx(cold * 1.5, rel=0.1)


class TestBenchConsumedItem:
    """SwitchModule must evaluate bench mons with their LIVE item state
    (backlog: 'pokemon on the bench are assumed to have their items even if
    they are spent and then switch out').  A Chople eaten during an earlier
    field stint must not soak hits for the switch-in evaluation."""

    def _score_bench_kingambit(self, *, item=None, item_consumed=False):
        """Run SwitchModule.score over one switch action to a live bench
        Kingambit; return the bench_item passed to _switch_in_survives."""
        state = TestEffectiveItem._single_slot_state("Venusaur", "Sneasler")
        bench = make_mon("Kingambit", item=item, item_consumed=item_consumed)
        state.available_switches = [bench]

        action = Action(label="Switch Kingambit", switch_target="Kingambit")
        with patch.object(SwitchModule, "_switch_in_survives",
                          return_value=True) as survives_spy, \
             patch.object(SwitchModule, "_best_offense", return_value=0.0):
            SwitchModule().score(state, 0, [action])
        # call signature: (state, species, bench_tm, bench_item)
        return survives_spy.call_args[0][3]

    def test_consumed_bench_item_evaluated_as_none(self):
        assert self._score_bench_kingambit(item_consumed=True) is None

    def test_intact_bench_falls_back_to_team_item(self):
        """No live item tracked (fresh battle) → team.txt Chople Berry."""
        assert self._score_bench_kingambit() == "Chople Berry"

    def test_live_tracked_item_wins(self):
        assert self._score_bench_kingambit(item="Sitrus Berry") == "Sitrus Berry"


class TestOurConsumedItem:
    """Our own consumed items must stop shielding us in the incoming facts.

    Our Kingambit's Chople Berry halves an opposing Sneasler's Close Combat
    (163-192 vs HP 191: survives all but the max roll).  Once the berry pops
    (``item_consumed``), the full hit (326-384) is a guaranteed OHKO — the
    fact loop must read the live battle state, not the static team.txt item.
    """

    def _state(self, item_consumed: bool):
        s = TestEffectiveItem._single_slot_state("Kingambit", "Sneasler")
        s.my_actives[0].item_consumed = item_consumed
        return s

    def test_intact_chople_downgrades_threat_to_max_roll_only(self):
        ctx = build_turn_context(self._state(item_consumed=False))
        assert 0 in ctx.incoming_ohko[0]          # max roll connects
        assert 0 not in ctx.incoming_certain[0]   # min roll does not

    def test_consumed_chople_restores_guaranteed_ohko(self):
        ctx = build_turn_context(self._state(item_consumed=True))
        assert 0 in ctx.incoming_ohko[0]
        assert 0 in ctx.incoming_certain[0]       # berry gone: certain kill
