"""test_turn_order.py — Unit tests for turn_order.py.

Tests the speed-modifier arithmetic, priority bracket lookup, and the
`will_outspeed` probability function using Combatant objects with exact
speeds (no data-layer lookups needed for the own-team path).
"""
import pytest
from turn_order import (
    _apply_modifiers,
    priority_bracket,
    will_outspeed,
    _speed_outcomes,
    Combatant,
)
from team import find_member


# ── _apply_modifiers ──────────────────────────────────────────────────────────

class TestApplyModifiers:
    def test_no_modifiers(self):
        assert _apply_modifiers(100) == 100

    def test_tailwind_doubles_speed(self):
        assert _apply_modifiers(100, tailwind=True) == 200

    def test_paralysis_halves_speed(self):
        assert _apply_modifiers(100, paralyzed=True) == 50

    def test_tailwind_and_paralysis(self):
        # Tailwind (×2) then paralysis (×0.5) → net ×1.0
        assert _apply_modifiers(100, tailwind=True, paralyzed=True) == 100

    def test_speed_stage_plus_1(self):
        # floor(100 * (2+1)/2) = floor(150) = 150
        assert _apply_modifiers(100, speed_stage=1) == 150

    def test_speed_stage_plus_2(self):
        assert _apply_modifiers(100, speed_stage=2) == 200

    def test_speed_stage_minus_1(self):
        # floor(100 * 2/(2+1)) = floor(66.67) = 66
        assert _apply_modifiers(100, speed_stage=-1) == 66

    def test_scarf_1_5x(self):
        assert _apply_modifiers(100, item="Choice Scarf") == 150

    def test_slow_item_halves(self):
        assert _apply_modifiers(100, item="Iron Ball") == 50

    def test_unburden_doubles(self):
        assert _apply_modifiers(100, ability="Unburden", item_consumed=True) == 200

    def test_unburden_no_item_no_boost(self):
        # Unburden only triggers when item was consumed
        assert _apply_modifiers(100, ability="Unburden", item_consumed=False) == 100


# ── priority_bracket ──────────────────────────────────────────────────────────

class TestPriorityBracket:
    def test_protect_priority_4(self):
        assert priority_bracket("Protect") == 4

    def test_fake_out_priority_3(self):
        assert priority_bracket("Fake Out") == 3

    def test_aqua_jet_priority_1(self):
        assert priority_bracket("Aqua Jet") == 1

    def test_normal_move_priority_0(self):
        assert priority_bracket("Dragon Claw") == 0
        assert priority_bracket("Earthquake") == 0

    def test_empty_string_priority_0(self):
        assert priority_bracket("") == 0

    def test_trick_room_negative_priority(self):
        assert priority_bracket("Trick Room") < 0


# ── Combatant helpers ─────────────────────────────────────────────────────────

def make_own(speed: int, **kwargs) -> Combatant:
    """Create an own-team Combatant with an exact speed."""
    return Combatant(
        name="OwnMon", side="own", slot=0,
        exact_speed=speed,
        **kwargs,
    )


def make_opp(speed: int, **kwargs) -> Combatant:
    """Create an opponent Combatant with an exact speed (for deterministic tests)."""
    return Combatant(
        name="OppMon", side="opp", slot=0,
        exact_speed=speed,
        **kwargs,
    )


# ── will_outspeed ─────────────────────────────────────────────────────────────

class TestWillOutspeed:
    def test_faster_mon_returns_1(self):
        faster = make_own(200)
        slower = make_opp(100)
        assert will_outspeed(faster, slower) == 1.0

    def test_slower_mon_returns_0(self):
        slower = make_own(100)
        faster = make_opp(200)
        assert will_outspeed(slower, faster) == 0.0

    def test_speed_tie_returns_0_5(self):
        tied = make_own(150)
        also_tied = make_opp(150)
        assert will_outspeed(tied, also_tied) == 0.5

    def test_higher_priority_wins(self):
        """Priority always beats speed regardless of stat."""
        slow = make_own(50)
        fast = make_opp(300)
        result = will_outspeed(slow, fast, atk_move="Fake Out", def_move="Dragon Claw")
        assert result == 1.0

    def test_lower_priority_loses(self):
        fast = make_own(300)
        slow = make_opp(50)
        result = will_outspeed(fast, slow, atk_move="Dragon Claw", def_move="Fake Out")
        assert result == 0.0

    def test_trick_room_inverts_slower_wins(self):
        slower = make_own(50)
        faster = make_opp(200)
        # Under Trick Room, slower moves first
        assert will_outspeed(slower, faster, trick_room=True) == 1.0

    def test_trick_room_does_not_affect_priority(self):
        """Priority brackets still resolve normally even under Trick Room."""
        slow = make_own(50)
        fast = make_opp(300)
        result = will_outspeed(slow, fast, atk_move="Fake Out", def_move="Dragon Claw",
                               trick_room=True)
        assert result == 1.0

    def test_tailwind_boosts_own_speed(self):
        own = make_own(100, tailwind=True)   # 100 × 2 = 200 effective
        opp = make_opp(150)
        assert will_outspeed(own, opp) == 1.0

    def test_paralysis_halves_speed(self):
        own = make_own(100, paralyzed=True)  # 100 × 0.5 = 50 effective
        opp = make_opp(60)
        assert will_outspeed(own, opp) == 0.0


# ── Scarf-Garchomp turn-order regression (0.14.0) ─────────────────────────────

class TestScarfGarchompOutspeed:
    """Regression for the turn-order misread surfaced by the 0.12.0/0.13.0
    battle logs: our Choice Scarf Garchomp was modelled at its *raw* 151 speed
    (predicted pos 2-4) because the scarf wasn't feeding the speed pipeline, so
    it "lost" to Raichu-Mega-X (178), Sceptile-Mega (216), Staraptor-Mega (178)
    and Metagross-Mega (162) — yet in-game it moved first every time.

    With the scarf applied Garchomp is 151 × 1.5 = 226, which beats all of them.
    These assertions pin both the team spread (raw 151) and the scarf ×1.5
    application against the *real* opponent speed distributions, so the bucket
    can't silently regress again.
    """

    def _garchomp(self) -> Combatant:
        tm = find_member("Garchomp")
        assert tm is not None and tm.item == "Choice Scarf"
        return Combatant(
            name="Garchomp", side="own", slot=0,
            exact_speed=tm.stats.get("spe"), item=tm.item, ability=tm.ability,
        )

    def test_scarf_garchomp_effective_speed_is_226(self):
        outcomes = _speed_outcomes(self._garchomp())
        assert outcomes == [(226, 1.0)]

    @pytest.mark.parametrize("opp", [
        "Raichu-Mega-X", "Sceptile-Mega", "Staraptor-Mega", "Metagross-Mega",
    ])
    def test_scarf_garchomp_outspeeds_fast_threats(self, opp):
        gc = self._garchomp()
        oc = Combatant(name=opp, side="opp", slot=0, exact_speed=None)
        assert will_outspeed(gc, oc) == pytest.approx(1.0)
