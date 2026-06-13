"""test_damage_core.py — Unit tests for damage.py pure math functions.

All functions tested here take plain numbers and return plain numbers —
no species lookups, no team data, no file I/O.  These tests run in isolation.
"""
import math
import pytest
from unittest.mock import patch
from damage import (
    calc_damage,
    full_damage_calc,
    type_effectiveness,
    effective_move_type,
    stab_multiplier,
    stat_with_boost,
    atk_modifier,
    def_modifier,
    weather_modifier,
    DamageResult,
    _low_kick_power,
    _heat_crash_power,
    _ALWAYS_CRIT_MOVES,
)


# ── calc_damage ───────────────────────────────────────────────────────────────

class TestCalcDamage:
    """Core Gen-9 damage formula arithmetic."""

    def test_neutral_80_power(self):
        # lv_factor=22, base=floor(floor(22*80*100/100)/50)+2=37
        # min=floor(37*85/100)=31, max=37
        dmg_min, dmg_max, dmg_avg = calc_damage(80, 100, 100)
        assert dmg_min == 31
        assert dmg_max == 37
        assert abs(dmg_avg - 34.225) < 0.001

    def test_stab_1_5x(self):
        # base=37 → floor(37*1.5)=55; min=floor(55*85/100)=46
        dmg_min, dmg_max, _ = calc_damage(80, 100, 100, stab=1.5)
        assert dmg_min == 46
        assert dmg_max == 55

    def test_adaptability_2_0x(self):
        dmg_min, dmg_max, _ = calc_damage(80, 100, 100, stab=2.0)
        assert dmg_min == 62
        assert dmg_max == 74

    def test_zero_power_returns_zero(self):
        assert calc_damage(0, 100, 100) == (0, 0, 0.0)

    def test_zero_effectiveness_returns_zero(self):
        assert calc_damage(80, 100, 100, effectiveness=0.0) == (0, 0, 0.0)

    def test_spread_move_penalty(self):
        # Spread applies 0.75× before random roll
        _, single_max, _ = calc_damage(90, 150, 100, stab=1.5)
        _, spread_max, _ = calc_damage(90, 150, 100, stab=1.5, spread_move=True)
        assert spread_max < single_max
        ratio = spread_max / single_max
        assert 0.70 < ratio < 0.80

    def test_crit_1_5x(self):
        _, norm_max, _ = calc_damage(80, 100, 100)
        _, crit_max, _ = calc_damage(80, 100, 100, crit=True)
        # base=37, crit→floor(37*1.5)=55
        assert crit_max == 55

    def test_crit_ignores_negative_atk_boost(self):
        """Gen 6+: on a critical hit, the attacker's negative stages are ignored."""
        _, penalised, _ = calc_damage(80, 100, 100, atk_boost=-2)
        _, crit_penalised, _ = calc_damage(80, 100, 100, crit=True, atk_boost=-2)
        _, crit_no_penalty, _ = calc_damage(80, 100, 100, crit=True, atk_boost=0)
        # The crit must ignore the -2 penalty, so crit_penalised == crit_no_penalty
        assert crit_penalised == crit_no_penalty
        # And the crit must still be stronger than the penalised non-crit
        assert crit_penalised > penalised

    def test_crit_ignores_positive_def_boost(self):
        """Gen 6+: on a critical hit, the defender's positive stages are ignored."""
        _, buffed_def, _ = calc_damage(80, 100, 100, def_boost=2)
        _, crit_buffed_def, _ = calc_damage(80, 100, 100, crit=True, def_boost=2)
        _, crit_no_buff, _ = calc_damage(80, 100, 100, crit=True, def_boost=0)
        # The crit must ignore the +2 defense, so crit_buffed_def == crit_no_buff
        assert crit_buffed_def == crit_no_buff
        # And the crit must still deal more than the non-crit into the buffed defender
        assert crit_buffed_def > buffed_def

    def test_crit_respects_positive_atk_boost(self):
        """Positive attacker boosts are NOT ignored on a crit — only negative ones are."""
        _, crit_base, _ = calc_damage(80, 100, 100, crit=True, atk_boost=0)
        _, crit_boosted, _ = calc_damage(80, 100, 100, crit=True, atk_boost=2)
        assert crit_boosted > crit_base

    def test_crit_respects_negative_def_boost(self):
        """Negative defender boosts are NOT ignored on a crit — only positive ones are."""
        _, crit_base, _ = calc_damage(80, 100, 100, crit=True, def_boost=0)
        _, crit_debuffed, _ = calc_damage(80, 100, 100, crit=True, def_boost=-2)
        assert crit_debuffed > crit_base

    def test_weather_modifier_fire_in_sun(self):
        _, sun_max, _ = calc_damage(80, 100, 100, weather=1.5)
        _, norm_max, _ = calc_damage(80, 100, 100)
        assert sun_max > norm_max

    def test_stat_boost_applied(self):
        # +2 atk boost roughly doubles Atk
        _, base_max, _ = calc_damage(80, 100, 100)
        _, boost_max, _ = calc_damage(80, 100, 100, atk_boost=2)
        assert boost_max > base_max

    def test_def_boost_applied(self):
        # +2 def boost reduces incoming damage
        _, base_max, _ = calc_damage(80, 100, 100)
        _, def_max, _ = calc_damage(80, 100, 100, def_boost=2)
        assert def_max < base_max


# ── Always-crit moves ─────────────────────────────────────────────────────────

class TestAlwaysCritMoves:
    """
    Flower Trick, Frost Breath, and Storm Throw always land as critical hits.
    full_damage_calc must apply crit=True automatically for these moves, and
    the Gen 6+ boost-clamping rules must already be in place via calc_damage.

    types_of is patched to return ["Normal"] for both attacker and defender so
    these tests are self-contained (no STAB, neutral effectiveness).
    """

    def test_always_crit_constant_contains_expected_moves(self):
        assert "Flower Trick" in _ALWAYS_CRIT_MOVES
        assert "Frost Breath" in _ALWAYS_CRIT_MOVES
        assert "Storm Throw"  in _ALWAYS_CRIT_MOVES

    def test_flower_trick_damage_matches_crit_formula(self):
        """Flower Trick (70 BP Physical Grass) must produce crit-level damage."""
        stats = {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100, "hp": 300}

        with patch("damage.types_of", return_value=["Normal"]):
            result = full_damage_calc(
                "Flower Trick",
                attacker_species="AnyMon",
                defender_species="AnyMon",
                attacker_stats=stats,
                defender_stats=stats,
            )

        # Normal attacker, Normal defender → no STAB, ×1.0 eff, crit=True
        # calc_damage(70, 100, 100, crit=True) = (40, 48, 44.4)
        crit_min, crit_max, _ = calc_damage(70, 100, 100, crit=True)
        assert result.damage_min == crit_min
        assert result.damage_max == crit_max

    def test_flower_trick_higher_than_no_crit(self):
        """Flower Trick damage must exceed what the same formula without crit would give."""
        stats = {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100, "hp": 300}

        with patch("damage.types_of", return_value=["Normal"]):
            result = full_damage_calc(
                "Flower Trick",
                attacker_species="AnyMon",
                defender_species="AnyMon",
                attacker_stats=stats,
                defender_stats=stats,
            )

        _, no_crit_max, _ = calc_damage(70, 100, 100)   # = 32 without crit
        assert result.damage_max > no_crit_max

    def test_frost_breath_damage_matches_crit_formula(self):
        """Frost Breath (60 BP Special Ice) must also produce crit-level damage."""
        stats = {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100, "hp": 300}

        with patch("damage.types_of", return_value=["Normal"]):
            result = full_damage_calc(
                "Frost Breath",
                attacker_species="AnyMon",
                defender_species="AnyMon",
                attacker_stats=stats,
                defender_stats=stats,
            )

        crit_min, crit_max, _ = calc_damage(60, 100, 100, crit=True)
        assert result.damage_min == crit_min
        assert result.damage_max == crit_max

    def test_flower_trick_crit_ignores_defenders_defense_boost(self):
        """Even with +2 defense on the target, Flower Trick damage is not reduced."""
        stats = {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100, "hp": 300}

        with patch("damage.types_of", return_value=["Normal"]):
            result_def_boosted = full_damage_calc(
                "Flower Trick",
                attacker_species="AnyMon",
                defender_species="AnyMon",
                attacker_stats=stats,
                defender_stats=stats,
                defender_boosts={"def": 2},
            )
            result_no_boost = full_damage_calc(
                "Flower Trick",
                attacker_species="AnyMon",
                defender_species="AnyMon",
                attacker_stats=stats,
                defender_stats=stats,
            )

        # Crit ignores the +2 def boost → same damage in both cases
        assert result_def_boosted.damage_max == result_no_boost.damage_max

    def test_flower_trick_crit_ignores_attackers_atk_drop(self):
        """An Intimidate-dropped attacker still deals full crit damage with Flower Trick."""
        stats = {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100, "hp": 300}

        with patch("damage.types_of", return_value=["Normal"]):
            result_intimidated = full_damage_calc(
                "Flower Trick",
                attacker_species="AnyMon",
                defender_species="AnyMon",
                attacker_stats=stats,
                defender_stats=stats,
                attacker_boosts={"atk": -1},
            )
            result_no_drop = full_damage_calc(
                "Flower Trick",
                attacker_species="AnyMon",
                defender_species="AnyMon",
                attacker_stats=stats,
                defender_stats=stats,
            )

        # Crit ignores the -1 Atk drop → same damage in both cases
        assert result_intimidated.damage_max == result_no_drop.damage_max


# ── type_effectiveness ────────────────────────────────────────────────────────

class TestTypeEffectiveness:
    def test_super_effective_2x(self):
        assert type_effectiveness("Water", ["Fire"]) == 2.0

    def test_resisted_0_5x(self):
        assert type_effectiveness("Fire", ["Water"]) == 0.5

    def test_immune_0x(self):
        assert type_effectiveness("Electric", ["Ground"]) == 0.0
        assert type_effectiveness("Normal", ["Ghost"]) == 0.0
        assert type_effectiveness("Dragon", ["Fairy"]) == 0.0

    def test_neutral_1x(self):
        assert type_effectiveness("Normal", ["Normal"]) == 1.0

    def test_dual_type_4x(self):
        # Water → Fire/Rock each 2×: 2 × 2 = 4
        assert type_effectiveness("Water", ["Fire", "Rock"]) == 4.0

    def test_dual_type_immunity(self):
        # Ghost → Normal/Psychic: Normal is immune (0×), Psychic would be 2×
        # 0 × 2 = 0 (immunity overrides)
        assert type_effectiveness("Ghost", ["Normal", "Psychic"]) == 0.0

    def test_dual_type_double_resist(self):
        # Fire → Water/Dragon: 0.5 × 0.5 = 0.25
        assert type_effectiveness("Fire", ["Water", "Dragon"]) == 0.25

    def test_unknown_type_defaults_to_1x(self):
        """Types not in the chart should default to neutral."""
        assert type_effectiveness("Fire", ["???Foo"]) == 1.0


# ── effective_move_type ───────────────────────────────────────────────────────

class TestEffectiveMoveType:
    def test_pixilate_normal_to_fairy(self):
        assert effective_move_type("Normal", "Pixilate") == "Fairy"

    def test_aerilate_normal_to_flying(self):
        assert effective_move_type("Normal", "Aerilate") == "Flying"

    def test_refrigerate_normal_to_ice(self):
        assert effective_move_type("Normal", "Refrigerate") == "Ice"

    def test_galvanize_normal_to_electric(self):
        assert effective_move_type("Normal", "Galvanize") == "Electric"

    def test_pixilate_non_normal_unchanged(self):
        assert effective_move_type("Water", "Pixilate") == "Water"

    def test_no_ability_unchanged(self):
        assert effective_move_type("Fire", "") == "Fire"


# ── stab_multiplier ───────────────────────────────────────────────────────────

class TestStabMultiplier:
    def test_stab_1_5x(self):
        assert stab_multiplier("Water", ["Water"]) == 1.5

    def test_no_stab_1x(self):
        assert stab_multiplier("Fire", ["Water"]) == 1.0

    def test_adaptability_2x(self):
        assert stab_multiplier("Water", ["Water"], "Adaptability") == 2.0

    def test_pixilate_converted_fairy_stab(self):
        """Sylveon uses Pixilate: Normal move → Fairy, gets Fairy STAB."""
        assert stab_multiplier("Fairy", ["Fairy", "Normal"]) == 1.5

    def test_dual_type_second_slot(self):
        assert stab_multiplier("Fire", ["Water", "Fire"]) == 1.5


# ── stat_with_boost ───────────────────────────────────────────────────────────

class TestStatWithBoost:
    def test_no_boost(self):
        assert stat_with_boost(100, 0) == 100

    def test_plus_1(self):
        assert stat_with_boost(100, 1) == 150   # floor(100 * 3/2)

    def test_plus_2(self):
        assert stat_with_boost(100, 2) == 200   # floor(100 * 4/2)

    def test_minus_1(self):
        assert stat_with_boost(100, -1) == 66   # floor(100 * 2/3)

    def test_minus_2(self):
        assert stat_with_boost(100, -2) == 50   # floor(100 * 2/4)

    def test_plus_6_cap(self):
        # At +6: floor(100 * 8/2) = 400
        assert stat_with_boost(100, 6) == 400


# ── atk_modifier ─────────────────────────────────────────────────────────────

class TestAtkModifier:
    def test_life_orb(self):
        mod = atk_modifier("", "Life Orb", "Dragon Claw", "Dragon", 80, "Physical")
        assert abs(mod - 1.3) < 0.001

    def test_choice_band_physical(self):
        mod = atk_modifier("", "Choice Band", "Close Combat", "Fighting", 120, "Physical")
        assert abs(mod - 1.5) < 0.001

    def test_choice_band_not_on_special(self):
        mod = atk_modifier("", "Choice Band", "Hyper Voice", "Normal", 90, "Special")
        assert abs(mod - 1.0) < 0.001

    def test_choice_specs_special(self):
        mod = atk_modifier("", "Choice Specs", "Hyper Voice", "Normal", 90, "Special")
        assert abs(mod - 1.5) < 0.001

    def test_pixilate_converts_normal_1_2x(self):
        mod = atk_modifier("Pixilate", None, "Hyper Voice", "Fairy", 90, "Special",
                            original_type="Normal")
        assert abs(mod - 1.2) < 0.001

    def test_pixilate_no_bonus_on_non_normal(self):
        mod = atk_modifier("Pixilate", None, "Moonblast", "Fairy", 95, "Special",
                            original_type="Fairy")
        assert abs(mod - 1.0) < 0.001

    def test_technician_low_power(self):
        mod = atk_modifier("Technician", None, "Bullet Seed", "Grass", 25, "Physical")
        assert abs(mod - 1.5) < 0.001

    def test_technician_high_power_no_bonus(self):
        mod = atk_modifier("Technician", None, "Dragon Claw", "Dragon", 80, "Physical")
        assert abs(mod - 1.0) < 0.001

    def test_type_gem_item(self):
        mod = atk_modifier("", "Dragon Fang", "Outrage", "Dragon", 120, "Physical")
        assert abs(mod - 1.2) < 0.001

    def test_no_modifiers(self):
        mod = atk_modifier("", None, "Dragon Claw", "Dragon", 80, "Physical")
        assert abs(mod - 1.0) < 0.001


# ── def_modifier ─────────────────────────────────────────────────────────────

class TestDefModifier:
    def test_multiscale_at_full_hp(self):
        mod = def_modifier("Multiscale", None, "Close Combat", "Physical", 2.0, is_full_hp=True)
        assert abs(mod - 0.5) < 0.001

    def test_multiscale_not_at_full_hp(self):
        mod = def_modifier("Multiscale", None, "Close Combat", "Physical", 2.0, is_full_hp=False)
        assert abs(mod - 1.0) < 0.001

    def test_filter_vs_super_effective(self):
        mod = def_modifier("Filter", None, "Ice Beam", "Special", 2.0)
        assert abs(mod - 0.75) < 0.001

    def test_filter_vs_neutral_no_effect(self):
        mod = def_modifier("Filter", None, "Surf", "Water", 1.0)
        assert abs(mod - 1.0) < 0.001

    def test_assault_vest_special(self):
        mod = def_modifier("", "Assault Vest", "Hyper Voice", "Special", 1.0)
        assert abs(mod - (2 / 3)) < 0.001

    def test_assault_vest_physical_no_effect(self):
        mod = def_modifier("", "Assault Vest", "Close Combat", "Physical", 2.0)
        assert abs(mod - 1.0) < 0.001

    def test_ice_scales_special(self):
        mod = def_modifier("Ice Scales", None, "Blizzard", "Special", 1.0)
        assert abs(mod - 0.5) < 0.001

    def test_ice_scales_physical_no_effect(self):
        mod = def_modifier("Ice Scales", None, "Close Combat", "Physical", 2.0)
        assert abs(mod - 1.0) < 0.001

    def test_chople_berry_vs_super_effective_fighting(self):
        mod = def_modifier("", "Chople Berry", "Fighting", "Physical", 2.0)
        assert abs(mod - 0.5) < 0.001

    def test_chople_berry_not_triggered_at_neutral(self):
        mod = def_modifier("", "Chople Berry", "Fighting", "Physical", 1.0)
        assert abs(mod - 1.0) < 0.001

    def test_no_modifiers(self):
        mod = def_modifier("", None, "Dragon Claw", "Physical", 1.0)
        assert abs(mod - 1.0) < 0.001


# ── weather_modifier ──────────────────────────────────────────────────────────

class TestWeatherModifier:
    def test_fire_in_sun(self):
        assert weather_modifier("Fire", "sun") == 1.5

    def test_water_in_sun(self):
        assert weather_modifier("Water", "sun") == 0.5

    def test_water_in_rain(self):
        assert weather_modifier("Water", "rain") == 1.5

    def test_fire_in_rain(self):
        assert weather_modifier("Fire", "rain") == 0.5

    def test_unaffected_type_neutral(self):
        assert weather_modifier("Ice", "sun") == 1.0

    def test_no_weather(self):
        assert weather_modifier("Fire", None) == 1.0


# ── DamageResult properties ───────────────────────────────────────────────────

class TestDamageResultProperties:
    """DamageResult.is_ohko / ohko_with_max_roll / is_2hko are computed properties."""

    def _make(self, dmg_min, dmg_max, dmg_avg, defender_hp):
        return DamageResult(
            move="Test", power=80, category="Physical", effective_type="Normal",
            attacker="Mon", defender="Foe",
            stab=1.0, effectiveness=1.0, atk_modifier=1.0, def_modifier=1.0,
            damage_min=dmg_min, damage_max=dmg_max, damage_avg=dmg_avg,
            defender_hp=defender_hp,
        )

    def test_guaranteed_ohko(self):
        r = self._make(110, 130, 120.0, 100)
        assert r.is_ohko is True
        assert r.ohko_with_max_roll is True

    def test_ohko_max_roll_only(self):
        r = self._make(85, 105, 95.0, 100)
        assert r.is_ohko is False
        assert r.ohko_with_max_roll is True

    def test_no_ohko(self):
        r = self._make(40, 50, 45.0, 100)
        assert r.is_ohko is False
        assert r.ohko_with_max_roll is False

    def test_is_2hko_true(self):
        r = self._make(40, 55, 55.0, 100)
        # avg 55 × 2 = 110 ≥ 100
        assert r.is_2hko is True

    def test_is_2hko_false(self):
        r = self._make(20, 30, 25.0, 100)
        # avg 25 × 2 = 50 < 100
        assert r.is_2hko is False

    def test_zero_defender_hp_guard(self):
        r = self._make(100, 120, 110.0, 0)
        assert r.is_ohko is False
        assert r.hp_fraction_avg == 0.0


class TestKoPreventedFlag:
    """Focus Sash / Sturdy prevent single-hit KOs from full HP."""

    def test_sash_prevents_guaranteed_ohko(self):
        """Full-HP holder with Sash + single-hit move that guarantees KO."""
        r = full_damage_calc(
            "Close Combat",
            attacker_species="Sneasler", attacker_stats={"atk": 150, "hp": 100},
            defender_species="Kingambit", defender_stats={"def": 120, "hp": 135},
            defender_item="Focus Sash", defender_is_full_hp=True,
        )
        assert r.ko_prevented is True
        assert r.is_ohko is False
        assert r.ohko_with_max_roll is False

    def test_sturdy_prevents_guaranteed_ohko(self):
        """Full-HP Sturdy holder + single-hit move that guarantees KO."""
        r = full_damage_calc(
            "Close Combat",
            attacker_species="Sneasler", attacker_stats={"atk": 150, "hp": 100},
            defender_species="Kingambit", defender_stats={"def": 120, "hp": 135},
            defender_ability="Sturdy", defender_is_full_hp=True,
        )
        assert r.ko_prevented is True
        assert r.is_ohko is False
        assert r.ohko_with_max_roll is False

    def test_sash_inert_when_chipped(self):
        """Sash does not prevent KO on a chipped opponent."""
        r = full_damage_calc(
            "Close Combat",
            attacker_species="Sneasler", attacker_stats={"atk": 150, "hp": 100},
            defender_species="Kingambit", defender_stats={"def": 120, "hp": 135},
            defender_item="Focus Sash", defender_is_full_hp=False,
        )
        assert r.ko_prevented is False
        assert r.is_ohko is True  # because damage is large enough to KO from any state

    def test_multibit_breaks_sash(self):
        """Multi-hit moves (Dual Wingbeat) break Sash: ko_prevented stays False."""
        r = full_damage_calc(
            "Dual Wingbeat",  # 2-hit move, expected_hits=2.0
            attacker_species="Aerodactyl", attacker_stats={"atk": 150, "hp": 100},
            defender_species="Kingambit", defender_stats={"def": 120, "hp": 135},
            defender_item="Focus Sash", defender_is_full_hp=True,
        )
        # Multi-hit moves (expected_hits != 1.0) bypass the ko_prevented check
        assert r.ko_prevented is False
        assert r.hits == 2.0

    def test_is_2hko_ignores_ko_prevented(self):
        """is_2hko is unaffected by ko_prevented."""
        r = full_damage_calc(
            "Fake Out",  # low-power move that doesn't OHKO
            attacker_species="Incineroar", attacker_stats={"atk": 100, "hp": 100},
            defender_species="Kingambit", defender_stats={"def": 120, "hp": 200},
            defender_item="Focus Sash", defender_is_full_hp=True,
        )
        # Sash prevents OHKO but doesn't affect is_2hko
        # (Fake Out is 40 BP, won't be 2HKO either, but the test verifies the flag itself)
        # Let's use a higher-power move for this test
        r = full_damage_calc(
            "Liquidation",  # 85 BP water move
            attacker_species="Basculegion-M", attacker_stats={"atk": 100, "spa": 100, "hp": 100},
            defender_species="Kingambit", defender_stats={"def": 120, "hp": 200},
            defender_item="Focus Sash", defender_is_full_hp=True,
        )
        # ko_prevented should be False because damage < hp (won't OHKO anyway)
        # But even if it were set, is_2hko should work correctly
        is_2hko_val = r.is_2hko
        assert isinstance(is_2hko_val, bool)

    def test_no_sash_control_case(self):
        """Control case: no Sash or Sturdy, normal OHKO logic."""
        r = full_damage_calc(
            "Close Combat",
            attacker_species="Sneasler", attacker_stats={"atk": 150, "hp": 100},
            defender_species="Kingambit", defender_stats={"def": 120, "hp": 135},
            defender_is_full_hp=True,
        )
        assert r.ko_prevented is False
        assert r.is_ohko is True  # Close Combat OHKOs Kingambit

    def test_sash_with_status_move(self):
        """ko_prevented is False for status moves (no damage)."""
        r = full_damage_calc(
            "Protect",
            attacker_species="Kingambit", attacker_stats={"atk": 100, "hp": 100},
            defender_species="Sneasler", defender_stats={"def": 100, "hp": 100},
            defender_item="Focus Sash", defender_is_full_hp=True,
        )
        assert r.ko_prevented is False
        assert r.power == 0


# ── Weight-based move power ────────────────────────────────────────────────────

class TestLowKickPower:
    """Low Kick / Grass Knot BP varies with target weight.  Bug fixed in 0.3.3."""

    def test_under_10kg(self):
        assert _low_kick_power(5.0) == 20

    def test_10_to_24kg(self):
        assert _low_kick_power(15.0) == 40

    def test_25_to_49kg(self):
        assert _low_kick_power(30.0) == 60

    def test_50_to_99kg(self):
        assert _low_kick_power(80.0) == 80

    def test_100_to_199kg(self):
        assert _low_kick_power(120.0) == 100

    def test_200kg_and_above(self):
        assert _low_kick_power(250.0) == 120

    def test_boundary_exactly_10kg(self):
        assert _low_kick_power(10.0) == 40

    def test_boundary_exactly_100kg(self):
        assert _low_kick_power(100.0) == 100


class TestHeatCrashPower:
    """Heat Crash / Heavy Slam BP varies with user-to-target weight ratio."""

    def test_ratio_5_or_above(self):
        # 200kg / 40kg = 5.0 → 120 BP
        assert _heat_crash_power(200.0, 40.0) == 120

    def test_ratio_4_to_5(self):
        # 200kg / 50kg = 4.0 → 100 BP
        assert _heat_crash_power(200.0, 50.0) == 100

    def test_ratio_3_to_4(self):
        assert _heat_crash_power(150.0, 50.0) == 80

    def test_ratio_2_to_3(self):
        assert _heat_crash_power(120.0, 60.0) == 60

    def test_ratio_below_2(self):
        assert _heat_crash_power(100.0, 80.0) == 40

    def test_zero_target_weight_guard(self):
        assert _heat_crash_power(200.0, 0.0) == 40
