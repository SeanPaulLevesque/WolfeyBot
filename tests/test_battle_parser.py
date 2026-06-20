"""test_battle_parser.py — Integration tests for BattleParser.feed().

Tests that specific Showdown protocol messages update BattleState correctly.
All tests are synchronous wrappers around async coroutines via asyncio.run().
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock

from battle import BattleParser, BattleState, Pokemon


# ── helpers ───────────────────────────────────────────────────────────────────

def make_parser(username="TestBot"):
    """Return a fresh BattleParser with a no-op decision callback."""
    on_decide = AsyncMock()
    parser = BattleParser(
        battle_id="battle-gen9-test-123",
        my_username=username,
        on_decision_needed=on_decide,
    )
    return parser, on_decide


def run(coro):
    return asyncio.run(coro)


# ── Player / side detection ───────────────────────────────────────────────────

class TestPlayerMessage:
    def test_recognises_our_side(self):
        parser, _ = make_parser("TestBot")
        run(parser.feed("|player|p2|TestBot||1400"))
        assert parser.state.my_side == "p2"

    def test_parses_elo(self):
        parser, _ = make_parser("TestBot")
        run(parser.feed("|player|p1|TestBot||1523"))
        assert parser.state.my_elo == 1523

    def test_ignores_opponent_player_message(self):
        parser, _ = make_parser("TestBot")
        run(parser.feed("|player|p2|TestBot||"))  # our side, no elo
        run(parser.feed("|player|p1|Opponent||1600"))
        assert parser.state.my_side == "p2"   # unchanged by opponent line
        assert parser.state.my_elo is None    # no elo set for us


# ── Gametype ─────────────────────────────────────────────────────────────────

class TestGametypeMessage:
    def test_sets_doubles_flag(self):
        parser, _ = make_parser()
        run(parser.feed("|gametype|doubles"))
        assert parser.state.is_doubles is True

    def test_singles_does_not_set_flag(self):
        parser, _ = make_parser()
        run(parser.feed("|gametype|singles"))
        assert parser.state.is_doubles is False


# ── Switch / drag ─────────────────────────────────────────────────────────────

class TestSwitchMessage:
    def test_adds_opponent_to_actives(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        assert len(parser.state.opp_actives) == 1
        assert parser.state.opp_actives[0].species == "Garchomp"
        assert parser.state.opp_actives[0].hp == 175

    def test_adds_opponent_to_correct_slot(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2b: Incineroar|Incineroar, L50, M|301/301"))
        assert len(parser.state.opp_actives) >= 2
        assert parser.state.opp_actives[1].species == "Incineroar"

    def test_resets_opp_last_move_on_switch_in(self):
        """Switching in resets the last-move tracker so FakeOutModule
        treats the new arrival as a fresh Fake Out threat."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        parser.state.opp_last_moves = ["Fake Out"]
        run(parser.feed("|switch|p2a: Incineroar|Incineroar, L50, M|301/301"))
        assert parser.state.opp_last_moves[0] == ""

    def test_detects_own_mon_switched_in(self):
        parser, _ = make_parser()
        parser.state.my_side = "p2"
        run(parser.feed("|switch|p2a: Garganacl|Garganacl, L50|301/301"))
        assert len(parser.state.my_actives) == 1
        assert parser.state.my_actives[0].species == "Garganacl"


# ── Damage / heal ─────────────────────────────────────────────────────────────

class TestDamageHeal:
    def _setup(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        return parser

    def test_damage_reduces_hp(self):
        parser = self._setup()
        run(parser.feed("|-damage|p2a: Garchomp|100/175"))
        assert parser.state.opp_actives[0].hp == 100

    def test_heal_increases_hp(self):
        parser = self._setup()
        run(parser.feed("|-damage|p2a: Garchomp|100/175"))
        run(parser.feed("|-heal|p2a: Garchomp|150/175"))
        assert parser.state.opp_actives[0].hp == 150

    def test_faint_via_damage_message(self):
        parser = self._setup()
        run(parser.feed("|-damage|p2a: Garchomp|0 fnt"))
        mon = parser.state.opp_actives[0]
        assert mon.fainted is True
        assert mon.hp == 0


# ── Flash Fire activation ──────────────────────────────────────────────────────

class TestFlashFireActivation:
    """|-start|IDENT|ability: Flash Fire sets the holder's flash_fire_active flag
    (either side); other -start effects leave it alone, and it resets on switch."""

    def _setup(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Heatran|Heatran, L50|175/175"))
        return parser

    def test_flag_starts_false(self):
        parser = self._setup()
        assert parser.state.opp_actives[0].flash_fire_active is False

    def test_flash_fire_sets_flag(self):
        parser = self._setup()
        run(parser.feed("|-start|p2a: Heatran|ability: Flash Fire"))
        assert parser.state.opp_actives[0].flash_fire_active is True

    def test_other_start_effect_does_not_set_flag(self):
        parser = self._setup()
        run(parser.feed("|-start|p2a: Heatran|Encore"))
        assert parser.state.opp_actives[0].flash_fire_active is False

    def test_flag_cleared_on_switch_out(self):
        parser = self._setup()
        run(parser.feed("|-start|p2a: Heatran|ability: Flash Fire"))
        # A different mon switching into the slot is a fresh object → flag reset.
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        assert parser.state.opp_actives[0].flash_fire_active is False


# ── Zero-damage reason (immune / miss / protect) ───────────────────────────────

class TestZeroDamageReason:
    """A move that deals 0 is tagged with WHY (immune/miss/protect/sub) so an
    ability immunity isn't confused with a Protect or a miss — and an immunity
    that names the ability reveals it on the target."""

    def _battle(self, opp="Bronzong"):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p1a: Garchomp|Garchomp, L50, M|200/200"))
        run(parser.feed(f"|switch|p2a: {opp}|{opp}, L50|150/150"))
        run(parser.feed("|turn|1"))
        return parser

    def _last_event(self, parser):
        return parser.state.turn_events[-1]

    def test_immune_with_ability_tags_and_reveals(self):
        parser = self._battle("Bronzong")
        run(parser.feed("|move|p1a: Garchomp|Earthquake|p2a: Bronzong"))
        run(parser.feed("|-immune|p2a: Bronzong|[from] ability: Levitate"))
        ev = self._last_event(parser)
        assert ev["z"] == "immune"
        assert ev["za"] == "Levitate"
        # The immunity reveals the ability so later turns stop targeting it.
        assert parser.state.opp_actives[0].ability == "Levitate"

    def test_immune_by_type_has_no_ability(self):
        parser = self._battle("Pelipper")
        run(parser.feed("|move|p1a: Garchomp|Earthquake|p2a: Pelipper"))
        run(parser.feed("|-immune|p2a: Pelipper"))   # Flying — type immunity, no ability
        ev = self._last_event(parser)
        assert ev["z"] == "immune"
        assert "za" not in ev

    def test_miss_tagged(self):
        parser = self._battle("Pelipper")
        run(parser.feed("|move|p1a: Garchomp|Stone Edge|p2a: Pelipper"))
        run(parser.feed("|-miss|p1a: Garchomp|p2a: Pelipper"))
        assert self._last_event(parser)["z"] == "miss"

    def test_protect_tagged(self):
        parser = self._battle("Kommo-o")
        run(parser.feed("|move|p1a: Garchomp|Dragon Claw|p2a: Kommo-o"))
        run(parser.feed("|-activate|p2a: Kommo-o|move: Protect"))
        assert self._last_event(parser)["z"] == "protect"

    def test_substitute_tagged(self):
        parser = self._battle("Kommo-o")
        run(parser.feed("|move|p1a: Garchomp|Dragon Claw|p2a: Kommo-o"))
        run(parser.feed("|-activate|p2a: Kommo-o|move: Substitute"))
        assert self._last_event(parser)["z"] == "sub"

    def test_real_hit_has_no_reason_tag(self):
        parser = self._battle("Kommo-o")
        run(parser.feed("|move|p1a: Garchomp|Dragon Claw|p2a: Kommo-o"))
        run(parser.feed("|-damage|p2a: Kommo-o|90/150"))
        ev = self._last_event(parser)
        assert "z" not in ev
        assert ev["dmg"] is not None and ev["dmg"] > 0


# ── Actual move-resolution instrumentation (0.8.1) ───────────────────────────

class TestMoveInstrumentation:
    """|move| + |-damage| events are captured in resolution order with actual
    damage, then flushed into events_log[turn] for the recorder."""

    def _battle(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p1a: Garchomp|Garchomp, L50, M|200/200"))
        run(parser.feed("|switch|p2a: Incineroar|Incineroar, L50, M|100/100"))
        run(parser.feed("|turn|1"))
        run(parser.feed("|move|p1a: Garchomp|Earthquake|p2a: Incineroar"))
        run(parser.feed("|-damage|p2a: Incineroar|40/100"))
        run(parser.feed("|move|p2a: Incineroar|Flare Blitz|p1a: Garchomp"))
        run(parser.feed("|-damage|p1a: Garchomp|150/200"))
        return parser

    def test_events_captured_in_order_with_damage(self):
        parser = self._battle()
        run(parser.feed("|turn|2"))   # flush turn 1
        ev = parser.state.events_log[1]
        assert [e["o"] for e in ev] == [0, 1]
        assert ev[0]["sd"] == "us" and ev[0]["a"] == "Garchomp"
        assert ev[0]["mv"] == "Earthquake" and ev[0]["tg"] == "Incineroar"
        assert ev[0]["dmg"] == pytest.approx(0.6, abs=0.01)   # 100% -> 40%
        assert ev[1]["sd"] == "opp" and ev[1]["a"] == "Incineroar"
        assert ev[1]["dmg"] == pytest.approx(0.25, abs=0.01)  # 200 -> 150

    def test_turn_events_cleared_after_flush(self):
        parser = self._battle()
        run(parser.feed("|turn|2"))
        assert parser.state.turn_events == []
        assert 2 not in parser.state.events_log

    def test_win_flushes_final_turn(self):
        parser = self._battle()
        run(parser.feed("|win|TestBot"))   # no |turn| follows the last turn
        assert 1 in parser.state.events_log
        assert len(parser.state.events_log[1]) == 2

    def test_crit_flag_captured_on_event(self):
        """|-crit| flags the resolving move so accuracy analysis can skip crits."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p1a: Garchomp|Garchomp, L50, M|200/200"))
        run(parser.feed("|switch|p2a: Incineroar|Incineroar, L50, M|100/100"))
        run(parser.feed("|turn|1"))
        run(parser.feed("|move|p2a: Incineroar|Flare Blitz|p1a: Garchomp"))
        run(parser.feed("|-crit|p1a: Garchomp"))
        run(parser.feed("|-damage|p1a: Garchomp|80/200"))
        run(parser.feed("|turn|2"))
        ev = parser.state.events_log[1][0]
        assert ev.get("crit") is True
        assert ev["dmg"] == pytest.approx(0.6, abs=0.01)

    def test_no_crit_flag_on_normal_hit(self):
        parser = self._battle()
        run(parser.feed("|turn|2"))
        assert all("crit" not in e for e in parser.state.events_log[1])

    def test_residual_damage_not_attributed_to_a_move(self):
        """A second -damage on the same target (e.g. recoil/residual) must not
        overwrite the move's recorded damage — the link clears after one hit."""
        parser = self._battle()
        run(parser.feed("|-damage|p1a: Garchomp|130/200"))  # extra hit, no preceding move
        run(parser.feed("|turn|2"))
        ev = parser.state.events_log[1]
        # Flare Blitz's recorded damage stays the original 200->150 = 0.25
        assert ev[1]["dmg"] == pytest.approx(0.25, abs=0.01)


# ── Status ───────────────────────────────────────────────────────────────────

class TestStatusMessages:
    def test_status_applied(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garganacl|Garganacl, L50|300/300"))
        run(parser.feed("|-status|p2a: Garganacl|brn"))
        assert parser.state.opp_actives[0].status == "brn"

    def test_curestatus_clears_status(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garganacl|Garganacl, L50|300/300"))
        run(parser.feed("|-status|p2a: Garganacl|par"))
        run(parser.feed("|-curestatus|p2a: Garganacl|par"))
        assert parser.state.opp_actives[0].status is None


# ── Boost / unboost ───────────────────────────────────────────────────────────

class TestBoostUnboost:
    def test_boost_increments(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-boost|p2a: Garchomp|atk|2"))
        assert parser.state.opp_actives[0].boosts["atk"] == 2

    def test_unboost_decrements(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-unboost|p2a: Garchomp|spe|1"))
        assert parser.state.opp_actives[0].boosts["spe"] == -1

    def test_clearnegativeboost_clears_only_negatives(self):
        """White Herb (|-clearnegativeboost|) restores stat drops but leaves any
        positive stages — a stale -1 otherwise under-predicts our own offense."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-unboost|p2a: Garchomp|atk|1"))
        run(parser.feed("|-boost|p2a: Garchomp|spe|1"))
        run(parser.feed("|-clearnegativeboost|p2a: Garchomp|[from] item: White Herb"))
        mon = parser.state.opp_actives[0]
        assert mon.boosts["atk"] == 0    # negative restored
        assert mon.boosts["spe"] == 1    # positive untouched
        assert mon.item_consumed is True  # White Herb spent -> triggers Unburden

    def test_clearnegativeboost_without_item_does_not_consume(self):
        """A non-item clear (e.g. a move) restores drops but consumes no item."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-unboost|p2a: Garchomp|atk|1"))
        run(parser.feed("|-clearnegativeboost|p2a: Garchomp"))
        mon = parser.state.opp_actives[0]
        assert mon.boosts["atk"] == 0
        assert mon.item_consumed is False

    def test_our_boosts_survive_request_rebuild(self):
        """Regression (0.17.0): a per-turn |request| rebuilds my_team from JSON,
        which carries no stat stages.  An Intimidate −1 Atk on our mon (and any
        other opponent-inflicted drop) must be carried forward, or the engine
        models our offense un-Intimidated and over-predicts our damage."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        # Our Garchomp is on our team and gets Intimidated to −1 Atk.
        parser.state.my_team = [
            Pokemon(ident="p1: Garchomp", species="Garchomp", hp=175, max_hp=175)
        ]
        run(parser.feed("|-unboost|p1a: Garchomp|atk|1"))
        assert parser.state.my_team[0].boosts["atk"] == -1
        # A fresh request arrives (no boosts in the JSON) — the drop must persist.
        req_mon = {"ident": "p1: Garchomp", "details": "Garchomp, L50, M",
                   "condition": "175/175", "active": True,
                   "moves": [{"move": "Dragon Claw"}]}
        parser._rebuild_team([req_mon], "p1")
        assert parser.state.my_team[0].boosts.get("atk") == -1


# ── Move tracking ─────────────────────────────────────────────────────────────

class TestMoveTracking:
    def test_opponent_move_recorded_in_revealed_moves(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|move|p2a: Garchomp|Earthquake|p1a: Garganacl"))
        assert "Earthquake" in parser.state.opp_actives[0].moves

    def test_opponent_last_move_updated(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Incineroar|Incineroar, L50, M|301/301"))
        run(parser.feed("|move|p2a: Incineroar|Fake Out|p1a: TestMon"))
        assert parser.state.opp_last_moves[0] == "Fake Out"

    def test_same_move_not_added_twice(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|move|p2a: Garchomp|Earthquake|p1a: Garganacl"))
        run(parser.feed("|move|p2a: Garchomp|Earthquake|p1a: Garganacl"))
        assert parser.state.opp_actives[0].moves.count("Earthquake") == 1


# ── Observation-driven item evidence ──────────────────────────────────────────

from data import CHOICE_ITEMS


class TestItemEvidence:
    """Parser signals that refute / confirm an opponent's assumed item."""

    def test_two_distinct_moves_rule_out_choice(self):
        """Two distinct moves in one field stint prove no Choice lock."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|move|p2a: Garchomp|Dragon Claw|p1a: X"))
        run(parser.feed("|move|p2a: Garchomp|Earthquake|p1a: X"))
        ev = parser.state.opp_item_evidence["p2: Garchomp"]
        assert CHOICE_ITEMS <= ev.ruled_out

    def test_repeated_same_move_keeps_choice_possible(self):
        """Using the same move twice is consistent with a Choice lock."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|move|p2a: Garchomp|Dragon Claw|p1a: X"))
        run(parser.feed("|move|p2a: Garchomp|Dragon Claw|p1a: X"))
        ev = parser.state.opp_item_evidence["p2: Garchomp"]
        assert not (CHOICE_ITEMS & ev.ruled_out)

    def test_distinct_moves_across_a_switch_dont_rule_out_choice(self):
        """A Choice lock frees on switch, so two distinct moves in *different*
        stints are not a contradiction — stint_moves resets on switch-in."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|move|p2a: Garchomp|Dragon Claw|p1a: X"))
        run(parser.feed("|switch|p2a: Landorus|Landorus, L50, M|175/175"))
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|move|p2a: Garchomp|Earthquake|p1a: X"))
        ev = parser.state.opp_item_evidence["p2: Garchomp"]
        assert not (CHOICE_ITEMS & ev.ruled_out)

    def test_struggle_does_not_count_toward_choice_ruleout(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|move|p2a: Garchomp|Dragon Claw|p1a: X"))
        run(parser.feed("|move|p2a: Garchomp|Struggle|p1a: X"))
        ev = parser.state.opp_item_evidence["p2: Garchomp"]
        assert not (CHOICE_ITEMS & ev.ruled_out)

    def test_enditem_marks_consumed(self):
        """A popped berry / Sash is recorded as game-scoped consumed."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-enditem|p2a: Garchomp|Sitrus Berry"))
        assert parser.state.opp_item_evidence["p2: Garchomp"].consumed is True

    def test_item_reveal_confirms_item(self):
        """A |-item| reveal (Trick / Frisk / Knock Off) confirms the held item."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-item|p2a: Garchomp|Choice Scarf|[from] move: Trick"))
        ev = parser.state.opp_item_evidence["p2: Garchomp"]
        assert ev.confirmed == "Choice Scarf"
        assert parser.state.opp_actives[0].item == "Choice Scarf"

    def test_life_orb_recoil_reveals_item(self):
        """Life Orb recoil (|-damage| … [from] item: Life Orb) confirms Life Orb."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-damage|p2a: Garchomp|160/175|[from] item: Life Orb"))
        ev = parser.state.opp_item_evidence["p2: Garchomp"]
        assert ev.confirmed == "Life Orb"
        assert parser.state.opp_actives[0].item == "Life Orb"

    def test_from_item_with_of_attributes_to_holder(self):
        """Rocky Helmet damages the attacker; the [of] source is the holder, so
        the item is attributed to the opponent, not to our damaged mon."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed(
            "|-damage|p1a: Us|200/250|[from] item: Rocky Helmet|[of] p2a: Garchomp"))
        ev = parser.state.opp_item_evidence["p2: Garchomp"]
        assert ev.confirmed == "Rocky Helmet"

    def test_our_side_item_events_ignored(self):
        """We never infer our own items — own-side events create no evidence."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|-enditem|p1a: Sneasler|White Herb"))
        run(parser.feed("|-item|p1a: Garchomp|Choice Scarf"))
        assert parser.state.opp_item_evidence == {}


# ── Field conditions ─────────────────────────────────────────────────────────

class TestTrickRoom:
    def test_fieldstart_trick_room_sets_flag(self):
        """The fix in 0.3.3 — Showdown sends 'move: Trick Room' with a space."""
        parser, _ = make_parser()
        run(parser.feed("|-fieldstart|move: Trick Room"))
        assert parser.state.trick_room is True
        assert parser.state.trick_room_turns_left == 5

    def test_fieldend_trick_room_clears_flag(self):
        parser, _ = make_parser()
        run(parser.feed("|-fieldstart|move: Trick Room"))
        run(parser.feed("|-fieldend|move: Trick Room"))
        assert parser.state.trick_room is False
        assert parser.state.trick_room_turns_left == 0

    def test_fieldstart_terrain_does_not_set_trick_room(self):
        parser, _ = make_parser()
        run(parser.feed("|-fieldstart|move: Electric Terrain"))
        assert parser.state.trick_room is False
        assert parser.state.terrain == "Electric Terrain"


# ── Tailwind ─────────────────────────────────────────────────────────────────

class TestTailwind:
    # Format A (older PS logs): condition name embedded in args[0]
    def test_sidestart_tailwind_sets_our_flag_format_a(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|-sidestart|p1: Tailwind|move: Tailwind"))
        assert parser.state.my_tailwind is True
        assert parser.state.my_tailwind_turns_left == 4

    def test_sidestart_tailwind_sets_opp_flag_format_a(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|-sidestart|p2: Tailwind|move: Tailwind"))
        assert parser.state.opp_tailwind is True
        assert parser.state.opp_tailwind_turns_left == 4

    # Format B (real PS live battles): player name in args[0], condition in args[1]
    def test_sidestart_tailwind_sets_opp_flag_format_b(self):
        """Real PS live format: side arg is 'p2: PlayerName', condition is args[1]."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|-sidestart|p2: WolfeyRocks|Tailwind"))
        assert parser.state.opp_tailwind is True
        assert parser.state.opp_tailwind_turns_left == 4

    def test_sidestart_tailwind_sets_our_flag_format_b(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|-sidestart|p1: PlayerOne|Tailwind"))
        assert parser.state.my_tailwind is True
        assert parser.state.my_tailwind_turns_left == 4

    def test_sideend_tailwind_clears_flag(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|-sidestart|p1: Tailwind|move: Tailwind"))
        run(parser.feed("|-sideend|p1: Tailwind|move: Tailwind"))
        assert parser.state.my_tailwind is False
        assert parser.state.my_tailwind_turns_left == 0

    def test_sideend_tailwind_clears_flag_format_b(self):
        """Real PS live format for sideend."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|-sidestart|p2: WolfeyRocks|Tailwind"))
        run(parser.feed("|-sideend|p2: WolfeyRocks|Tailwind"))
        assert parser.state.opp_tailwind is False
        assert parser.state.opp_tailwind_turns_left == 0

    def test_sidestart_tailwind_does_not_set_flag_for_other_condition(self):
        """An unrelated sidestart message must not affect Tailwind flags."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|-sidestart|p2: PlayerTwo|Reflect"))
        assert parser.state.opp_tailwind is False
        assert parser.state.opp_tailwind_turns_left == 0


# ── Turn counter ──────────────────────────────────────────────────────────────

class TestTurnCounter:
    def test_turn_message_updates_turn_number(self):
        parser, _ = make_parser()
        run(parser.feed("|turn|3"))
        assert parser.state.turn == 3

    def test_turn_decrements_tailwind_counter(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        parser.state.my_tailwind_turns_left = 3
        run(parser.feed("|turn|2"))
        assert parser.state.my_tailwind_turns_left == 2

    def test_turn_decrements_trick_room_counter(self):
        parser, _ = make_parser()
        parser.state.trick_room_turns_left = 4
        run(parser.feed("|turn|2"))
        assert parser.state.trick_room_turns_left == 3


# ── Faint ─────────────────────────────────────────────────────────────────────

class TestFaint:
    def test_faint_sets_fainted_flag(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|faint|p2a: Garchomp"))
        assert parser.state.opp_actives[0].fainted is True
        assert parser.state.opp_actives[0].hp == 0


# ── Win ───────────────────────────────────────────────────────────────────────

class TestWin:
    def test_win_fires_callback_with_true(self):
        on_end = AsyncMock()
        parser = BattleParser(
            battle_id="battle-test",
            my_username="TestBot",
            on_decision_needed=AsyncMock(),
            on_battle_end=on_end,
        )
        run(parser.feed("|win|TestBot"))
        on_end.assert_called_once_with(True)

    def test_loss_fires_callback_with_false(self):
        on_end = AsyncMock()
        parser = BattleParser(
            battle_id="battle-test",
            my_username="TestBot",
            on_decision_needed=AsyncMock(),
            on_battle_end=on_end,
        )
        run(parser.feed("|win|Opponent"))
        on_end.assert_called_once_with(False)

    def test_no_callback_set_does_not_raise(self):
        """on_battle_end=None should not raise when win arrives."""
        parser = BattleParser(
            battle_id="battle-test",
            my_username="TestBot",
            on_decision_needed=AsyncMock(),
            on_battle_end=None,
        )
        run(parser.feed("|win|Opponent"))  # should not raise


# ── Item / Ability ────────────────────────────────────────────────────────────

class TestItemAbility:
    def test_item_revealed(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50|175/175"))
        run(parser.feed("|-item|p2a: Garchomp|Choice Scarf"))
        assert parser.state.opp_actives[0].item == "Choice Scarf"

    def test_enditem_clears_item_and_sets_consumed(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50|175/175"))
        run(parser.feed("|-item|p2a: Garchomp|Choice Scarf"))
        run(parser.feed("|-enditem|p2a: Garchomp|Choice Scarf"))
        mon = parser.state.opp_actives[0]
        assert mon.item is None
        assert mon.item_consumed is True

    def test_times_hit_increments_on_move_damage(self):
        """A damaging move on a mon increments its times_hit (drives Rage Fist)."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Annihilape|Annihilape, L50, M|200/200"))
        run(parser.feed("|move|p1a: Garchomp|Dragon Claw|p2a: Annihilape"))
        run(parser.feed("|-damage|p2a: Annihilape|150/200"))
        assert parser.state.opp_actives[0].times_hit == 1

    def test_times_hit_resets_on_switch(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Annihilape|Annihilape, L50, M|200/200"))
        run(parser.feed("|move|p1a: Garchomp|Dragon Claw|p2a: Annihilape"))
        run(parser.feed("|-damage|p2a: Annihilape|150/200"))
        # Switches out and a new mon comes in — stacks gone (fresh object).
        run(parser.feed("|switch|p2a: Pelipper|Pelipper, L50, M|160/160"))
        run(parser.feed("|switch|p2a: Annihilape|Annihilape, L50, M|150/200"))
        assert parser.state.opp_actives[0].times_hit == 0

    def test_ability_revealed(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50|175/175"))
        run(parser.feed("|-ability|p2a: Garchomp|Rough Skin"))
        assert parser.state.opp_actives[0].ability == "Rough Skin"


# ── Error recovery ────────────────────────────────────────────────────────────

class TestErrorMessage:
    def test_error_resets_rqid_for_retry(self):
        """After '[Invalid choice]' the server sends a new |request|.
        We must allow it through by clearing last_rqid_handled."""
        parser, _ = make_parser()
        parser.state.rqid = 5
        parser.state.last_rqid_handled = 5
        run(parser.feed("|error|[Invalid choice] Can't move: your Mon is trapped!"))
        assert parser.state.last_rqid_handled is None


# ── Trapped (Shadow Tag / Arena Trap / trapping move) ────────────────────────

class TestTrapped:
    def test_normal_turn_populates_trapped_per_slot(self):
        """active[].trapped from the |request| is recorded per slot."""
        parser, _ = make_parser()
        data = {"active": [
            {"moves": [{"move": "Dragon Claw"}], "trapped": True},
            {"moves": [{"move": "Protect"}]},
        ]}
        parser._handle_normal_turn(data, [])
        assert parser.state.trapped == [True, False]

    def test_maybe_trapped_is_not_treated_as_trapped(self):
        """`maybeTrapped` is only a hint — switching is still legal."""
        parser, _ = make_parser()
        data = {"active": [{"moves": [{"move": "Dragon Claw"}], "maybeTrapped": True}]}
        parser._handle_normal_turn(data, [])
        assert parser.state.trapped == [False]

    def test_force_switch_clears_trapped(self):
        """A force-switch phase must clear any lingering trapped flags."""
        parser, _ = make_parser()
        parser.state.trapped = [True, True]
        parser._handle_force_switch({"forceSwitch": [True, False]})
        assert parser.state.trapped == [False, False]


# ── Terastallize ─────────────────────────────────────────────────────────────

class TestTerastallize:
    def test_opponent_tera_sets_flag_and_type(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-terastallize|p2a: Garchomp|Dragon"))
        mon = parser.state.opp_actives[0]
        assert mon.terastallized is True
        assert mon.tera_type == "Dragon"

    def test_our_mon_tera_sets_flag_and_type(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p1a: Garganacl|Garganacl, L50|301/301"))
        run(parser.feed("|-terastallize|p1a: Garganacl|Water"))
        mon = parser.state.my_actives[0]
        assert mon.terastallized is True
        assert mon.tera_type == "Water"

    def test_tera_type_overrides_previous(self):
        """A second terastallize message (shouldn't happen in practice, but be safe)."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-terastallize|p2a: Garchomp|Dragon"))
        run(parser.feed("|-terastallize|p2a: Garchomp|Steel"))
        assert parser.state.opp_actives[0].tera_type == "Steel"


# ── Cant ─────────────────────────────────────────────────────────────────────

class TestCant:
    def test_cant_clears_opponent_last_move(self):
        """Flinch/paralysis clears stale last-move so Protect-spam detection stays clean."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        parser.state.opp_last_moves = ["Earthquake"]
        run(parser.feed("|cant|p2a: Garchomp|par"))
        assert parser.state.opp_last_moves[0] == ""

    def test_cant_clears_our_last_move(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        parser.state.my_last_moves = ["Protect"]
        run(parser.feed("|cant|p1a: Garganacl|flinch"))
        assert parser.state.my_last_moves[0] == ""

    def test_cant_works_when_last_moves_list_empty(self):
        """Should not raise when last_moves list is shorter than the slot index."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|cant|p2a: Garchomp|slp"))  # should not raise
        assert parser.state.opp_last_moves[0] == ""

    def test_cant_slot_b_clears_correct_slot(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        parser.state.opp_last_moves = ["Earthquake", "Protect"]
        run(parser.feed("|cant|p2b: Incineroar|flinch"))
        assert parser.state.opp_last_moves[0] == "Earthquake"  # slot-a unchanged
        assert parser.state.opp_last_moves[1] == ""            # slot-b cleared


# ── Clear boost ───────────────────────────────────────────────────────────────

class TestClearBoost:
    def test_clearboost_zeros_all_stat_stages(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-boost|p2a: Garchomp|atk|2"))
        run(parser.feed("|-boost|p2a: Garchomp|spe|1"))
        run(parser.feed("|-clearboost|p2a: Garchomp"))
        mon = parser.state.opp_actives[0]
        assert mon.boosts["atk"] == 0
        assert mon.boosts["spe"] == 0

    def test_clearboost_only_affects_target(self):
        """A second active mon's boosts must not be disturbed."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|switch|p2b: Incineroar|Incineroar, L50, M|301/301"))
        run(parser.feed("|-boost|p2a: Garchomp|atk|2"))
        run(parser.feed("|-boost|p2b: Incineroar|atk|1"))
        run(parser.feed("|-clearboost|p2a: Garchomp"))
        assert parser.state.opp_actives[0].boosts["atk"] == 0
        assert parser.state.opp_actives[1].boosts["atk"] == 1  # untouched


# ── Clear all boosts ──────────────────────────────────────────────────────────

class TestClearAllBoost:
    def test_clearallboost_zeros_all_active_mons(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|switch|p2b: Incineroar|Incineroar, L50, M|301/301"))
        run(parser.feed("|-boost|p2a: Garchomp|atk|2"))
        run(parser.feed("|-boost|p2b: Incineroar|spe|1"))
        run(parser.feed("|-clearallboost"))
        assert parser.state.opp_actives[0].boosts["atk"] == 0
        assert parser.state.opp_actives[1].boosts["spe"] == 0


# ── Invert boost ──────────────────────────────────────────────────────────────

class TestInvertBoost:
    def test_invertboost_negates_positive_stages(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-boost|p2a: Garchomp|atk|3"))
        run(parser.feed("|-invertboost|p2a: Garchomp"))
        assert parser.state.opp_actives[0].boosts["atk"] == -3

    def test_invertboost_negates_negative_stages(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-unboost|p2a: Garchomp|def|2"))
        run(parser.feed("|-invertboost|p2a: Garchomp"))
        assert parser.state.opp_actives[0].boosts["def"] == 2


# ── Set boost ─────────────────────────────────────────────────────────────────

class TestSetBoost:
    def test_setboost_overrides_current_stage(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-boost|p2a: Garchomp|atk|1"))
        run(parser.feed("|-setboost|p2a: Garchomp|atk|3"))
        assert parser.state.opp_actives[0].boosts["atk"] == 3


# ── Transform ─────────────────────────────────────────────────────────────────

class TestTransform:
    def test_transform_copies_species(self):
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p2a: Ditto|Ditto, L50|155/155"))
        run(parser.feed("|switch|p1a: Garchomp|Garchomp, L50, M|175/175"))
        run(parser.feed("|-transform|p2a: Ditto|p1a: Garchomp"))
        assert parser.state.opp_actives[0].species == "Garchomp"

    def test_transform_copies_revealed_moves(self):
        """Our Ditto transforms into an opponent who has already revealed moves.

        _on_move only appends to mon.moves for *opponent* mons (our moves are
        known from request JSON).  So we test: opp Garchomp reveals a move,
        then our Ditto transforms into it and inherits that move list.
        """
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p1a: Ditto|Ditto, L50|155/155"))          # our Ditto
        run(parser.feed("|switch|p2a: Garchomp|Garchomp, L50, M|175/175")) # opp Garchomp
        run(parser.feed("|move|p2a: Garchomp|Earthquake|p1a: Ditto"))      # opp reveals move
        run(parser.feed("|-transform|p1a: Ditto|p2a: Garchomp"))           # our Ditto copies
        assert "Earthquake" in parser.state.my_actives[0].moves


# ── Disable / Encore tracking ─────────────────────────────────────────────────

class TestDisableEncore:
    """Parser correctly sets/clears my_disabled_moves and my_encored_moves."""

    def _setup(self):
        """Return a parser with our Venusaur already on the field."""
        parser, _ = make_parser()
        parser.state.my_side = "p1"
        run(parser.feed("|switch|p1a: Venusaur|Venusaur, L50|180/180"))
        # Seed last_moves so Encore can read it
        parser.state.my_last_moves = ["Giga Drain"]
        return parser

    # ── Disable ───────────────────────────────────────────────────────────────

    def test_activate_disable_sets_disabled_move(self):
        parser = self._setup()
        run(parser.feed("|-activate|p1a: Venusaur|move: Disable|Giga Drain"))
        assert parser.state.my_disabled_moves[0] == "Giga Drain"

    def test_activate_disable_opponent_ignored(self):
        """Disable on the opponent's mon must not touch our state."""
        parser = self._setup()
        parser.state.my_side = "p1"
        run(parser.feed("|-activate|p2a: Incineroar|move: Disable|Flare Blitz"))
        # Our list should still be empty/default
        assert not parser.state.my_disabled_moves or parser.state.my_disabled_moves[0] is None

    def test_end_disable_clears_disabled_move(self):
        parser = self._setup()
        run(parser.feed("|-activate|p1a: Venusaur|move: Disable|Giga Drain"))
        assert parser.state.my_disabled_moves[0] == "Giga Drain"
        run(parser.feed("|-end|p1a: Venusaur|Disable"))
        assert parser.state.my_disabled_moves[0] is None

    def test_switch_clears_disabled_move(self):
        parser = self._setup()
        run(parser.feed("|-activate|p1a: Venusaur|move: Disable|Giga Drain"))
        assert parser.state.my_disabled_moves[0] == "Giga Drain"
        run(parser.feed("|switch|p1a: Garchomp|Garchomp, L50|175/175"))
        assert parser.state.my_disabled_moves[0] is None

    # ── Encore ────────────────────────────────────────────────────────────────

    def test_start_encore_locks_last_move(self):
        parser = self._setup()
        run(parser.feed("|-start|p1a: Venusaur|Encore"))
        assert parser.state.my_encored_moves[0] == "Giga Drain"

    def test_start_encore_opponent_ignored(self):
        """Encore on the opponent's mon must not touch our state."""
        parser = self._setup()
        run(parser.feed("|-start|p2a: Incineroar|Encore"))
        assert not parser.state.my_encored_moves or parser.state.my_encored_moves[0] is None

    def test_end_encore_clears_encored_move(self):
        parser = self._setup()
        run(parser.feed("|-start|p1a: Venusaur|Encore"))
        assert parser.state.my_encored_moves[0] == "Giga Drain"
        run(parser.feed("|-end|p1a: Venusaur|Encore"))
        assert parser.state.my_encored_moves[0] is None

    def test_switch_clears_encored_move(self):
        parser = self._setup()
        run(parser.feed("|-start|p1a: Venusaur|Encore"))
        assert parser.state.my_encored_moves[0] == "Giga Drain"
        run(parser.feed("|switch|p1a: Kingambit|Kingambit, L50|165/165"))
        assert parser.state.my_encored_moves[0] is None

