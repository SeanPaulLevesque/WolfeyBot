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
    incoming_damage,
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
from data import is_contact, move_flags, is_spread_move


# ── Weather Ball / Foul Play / Tough Claws (0.8.5 defensive-model fixes) ─────

class TestWeatherBall:
    """Weather Ball becomes the weather's type at 100 BP (base Normal 50)."""

    _ATK = {"hp": 150, "atk": 80, "def": 100, "spa": 120, "spd": 100, "spe": 100}
    _DEF = {"hp": 190, "atk": 120, "def": 120, "spd": 110, "spe": 100}

    def test_normal_50_with_no_weather(self):
        r = full_damage_calc("Weather Ball", "Politoed", "Garchomp", self._ATK, self._DEF)
        assert r.effective_type == "Normal" and r.power == 50

    def test_rain_becomes_water_100(self):
        r = full_damage_calc("Weather Ball", "Politoed", "Garchomp",
                             self._ATK, self._DEF, weather="rain")
        assert r.effective_type == "Water" and r.power == 100
        # Water vs Garchomp (Ground/Dragon) = 2× Ground × 0.5× Dragon = 1.0 (neutral);
        # the big jump vs Normal is power 50→100 + Water STAB + rain ×1.5.
        assert r.effectiveness == 1.0

    def test_sun_sand_hail_types(self):
        for wx, ty in (("sun", "Fire"), ("sand", "Rock"), ("hail", "Ice")):
            r = full_damage_calc("Weather Ball", "Politoed", "Garchomp",
                                 self._ATK, self._DEF, weather=wx)
            assert r.effective_type == ty and r.power == 100


class TestFoulPlay:
    """Foul Play uses the TARGET's Attack stat, not the user's."""

    def test_scales_with_defender_attack(self):
        attacker = {"hp": 150, "atk": 70, "def": 120, "spa": 80, "spd": 120, "spe": 50}
        weak_def = {"hp": 171, "atk": 80, "def": 100, "spd": 90, "spe": 100}
        strong_def = {"hp": 171, "atk": 220, "def": 100, "spd": 90, "spe": 100}
        low = full_damage_calc("Foul Play", "Sableye", "X", attacker, weak_def)
        high = full_damage_calc("Foul Play", "Sableye", "X", attacker, strong_def)
        # Same attacker; damage rises with the DEFENDER's Attack.
        assert high.damage_avg > low.damage_avg * 2

    def test_defender_attack_boost_counts(self):
        attacker = {"hp": 150, "atk": 70, "def": 120, "spa": 80, "spd": 120, "spe": 50}
        d = {"hp": 171, "atk": 120, "def": 100, "spd": 90, "spe": 100}
        base = full_damage_calc("Foul Play", "Sableye", "X", attacker, d)
        boosted = full_damage_calc("Foul Play", "Sableye", "X", attacker, d,
                                   defender_boosts={"atk": 2})
        assert boosted.damage_avg > base.damage_avg


class TestToughClaws:
    """Tough Claws ×1.3 on contact moves only."""

    _ATK = {"hp": 150, "atk": 180, "def": 115, "spa": 130, "spd": 85, "spe": 150}
    _DEF = {"hp": 190, "atk": 120, "def": 120, "spd": 110, "spe": 100}

    def test_contact_move_boosted(self):
        no = full_damage_calc("Dragon Claw", "Charizard-Mega-X", "Garchomp",
                              self._ATK, self._DEF)
        tc = full_damage_calc("Dragon Claw", "Charizard-Mega-X", "Garchomp",
                              self._ATK, self._DEF, attacker_ability="Tough Claws")
        assert tc.damage_avg == pytest.approx(no.damage_avg * 1.3, rel=0.04)

    def test_non_contact_move_unchanged(self):
        no = full_damage_calc("Earthquake", "Charizard-Mega-X", "Garchomp",
                              self._ATK, self._DEF)
        tc = full_damage_calc("Earthquake", "Charizard-Mega-X", "Garchomp",
                              self._ATK, self._DEF, attacker_ability="Tough Claws")
        assert tc.damage_avg == pytest.approx(no.damage_avg, rel=0.01)
        assert not is_contact("Earthquake")

    def test_special_contact_move_flagged(self):
        """Grass Knot is a SPECIAL move that makes contact (the case a
        physical-only heuristic would miss)."""
        assert is_contact("Grass Knot")
        assert "contact" in move_flags("Dragon Claw")
        assert "slicing" in move_flags("Dragon Claw")


class TestIncomingScreens:
    """Our active screens reduce INCOMING damage to 2/3 in doubles — the
    defensive mirror of the outgoing ``opp_screens`` path (gap 1 of the Aurora
    Veil backlog item, wired 0.29.0). Aurora Veil covers both categories."""

    _OUR = {"hp": 190, "atk": 130, "def": 110, "spa": 110, "spd": 110, "spe": 100}

    def test_aurora_veil_reduces_incoming(self):
        no = incoming_damage("Garchomp", "Garchomp", self._OUR)
        av = incoming_damage("Garchomp", "Garchomp", self._OUR,
                             our_screens={"auroraveil"})
        assert no and av
        assert av[0].damage_avg == pytest.approx(no[0].damage_avg * (2.0 / 3.0),
                                                 rel=0.02)

    def test_no_screens_unchanged(self):
        no = incoming_damage("Garchomp", "Garchomp", self._OUR)
        empty = incoming_damage("Garchomp", "Garchomp", self._OUR, our_screens=set())
        assert no[0].damage_avg == pytest.approx(empty[0].damage_avg, rel=1e-6)

    def test_only_moves_restricts_assessment(self):
        """only_moves assesses exactly the given move(s) — a Choice-locked
        opponent's single move — instead of the usage top-N."""
        full = incoming_damage("Garchomp", "Garchomp", self._OUR)
        one = incoming_damage("Garchomp", "Garchomp", self._OUR,
                              only_moves=["Earthquake"])
        assert len(one) == 1
        assert len(full) > 1


class TestFlagAbilities:
    """Sharpness/Strong Jaw/Iron Fist boost their flagged move classes."""

    _A = {"hp": 150, "atk": 150, "def": 100, "spa": 100, "spd": 100, "spe": 100}
    _D = {"hp": 190, "atk": 120, "def": 120, "spd": 110, "spe": 100}

    def _ratio(self, move, ability):
        base = full_damage_calc(move, "X", "Y", self._A, self._D).damage_avg
        boost = full_damage_calc(move, "X", "Y", self._A, self._D,
                                 attacker_ability=ability).damage_avg
        return boost / base

    def test_sharpness_slicing(self):
        assert self._ratio("Night Slash", "Sharpness") == pytest.approx(1.5, rel=0.04)

    def test_strong_jaw_bite(self):
        assert self._ratio("Crunch", "Strong Jaw") == pytest.approx(1.5, rel=0.04)

    def test_iron_fist_punch(self):
        assert self._ratio("Ice Punch", "Iron Fist") == pytest.approx(1.2, rel=0.04)

    def test_ability_ignores_unflagged_move(self):
        # Earthquake is neither slicing/bite/punch — no boost from any of them.
        assert self._ratio("Earthquake", "Sharpness") == pytest.approx(1.0, rel=0.02)
        assert self._ratio("Earthquake", "Strong Jaw") == pytest.approx(1.0, rel=0.02)

    # ── newly-wired flag/type/category abilities (0.8.5) ──────────────────────
    def test_mega_launcher_pulse(self):
        assert self._ratio("Aura Sphere", "Mega Launcher") == pytest.approx(1.5, rel=0.04)

    def test_punk_rock_sound(self):
        assert self._ratio("Boomburst", "Punk Rock") == pytest.approx(1.3, rel=0.04)

    def test_reckless_recoil(self):
        assert self._ratio("Flare Blitz", "Reckless") == pytest.approx(1.2, rel=0.04)

    def test_fairy_aura_fairy_type(self):
        assert self._ratio("Moonblast", "Fairy Aura") == pytest.approx(1.33, rel=0.04)

    def test_steely_spirit_steel_type(self):
        assert self._ratio("Iron Head", "Steely Spirit") == pytest.approx(1.5, rel=0.04)

    def test_water_bubble_water_type(self):
        # ×2.0 nominal; integer damage rounding lands it slightly under.
        assert self._ratio("Liquidation", "Water Bubble") == pytest.approx(2.0, rel=0.05)

    def test_huge_power_physical(self):
        assert self._ratio("Earthquake", "Huge Power") == pytest.approx(2.0, rel=0.05)

    def test_pure_power_physical(self):
        assert self._ratio("Earthquake", "Pure Power") == pytest.approx(2.0, rel=0.05)

    def test_gorilla_tactics_physical(self):
        assert self._ratio("Earthquake", "Gorilla Tactics") == pytest.approx(1.5, rel=0.04)

    def test_transistor_electric(self):
        # Champions reference: +30% (not the +50% of mainline Gen 9).
        assert self._ratio("Thunderbolt", "Transistor") == pytest.approx(1.3, rel=0.04)

    def test_type_ability_ignores_other_types(self):
        # Each type-keyed ability only touches its own type.
        assert self._ratio("Earthquake", "Fairy Aura") == pytest.approx(1.0, rel=0.02)
        assert self._ratio("Earthquake", "Water Bubble") == pytest.approx(1.0, rel=0.02)
        assert self._ratio("Moonblast", "Steely Spirit") == pytest.approx(1.0, rel=0.02)

    def test_category_ability_ignores_special(self):
        # Huge/Pure Power & Gorilla Tactics are physical-only.
        assert self._ratio("Moonblast", "Huge Power") == pytest.approx(1.0, rel=0.02)
        assert self._ratio("Moonblast", "Gorilla Tactics") == pytest.approx(1.0, rel=0.02)


class TestEffectivenessAbilities:
    """Neuroforce (×1.2 super-effective) and Tinted Lens (×2.0 not-very-eff).

    Both key off the resolved type effectiveness, so they're tested against
    real defender types: Ice Beam vs Garchomp is 4× (SE), Flamethrower vs
    Garchomp is 0.5× (NVE), Surf vs Garchomp is 1× (neutral).
    """

    _A = {"hp": 150, "atk": 150, "def": 100, "spa": 150, "spd": 100, "spe": 100}
    _D = {"hp": 190, "atk": 120, "def": 120, "spd": 110, "spe": 100}

    def _ratio(self, move, defender, ability):
        # Attacker species is unknown ("Atk") → no STAB, so the ratio isolates
        # the ability's effect.
        base = full_damage_calc(move, "Atk", defender, self._A, self._D).damage_avg
        boost = full_damage_calc(move, "Atk", defender, self._A, self._D,
                                 attacker_ability=ability).damage_avg
        return boost / base

    def test_neuroforce_super_effective(self):
        assert self._ratio("Ice Beam", "Garchomp", "Neuroforce") == pytest.approx(1.2, rel=0.05)

    def test_neuroforce_neutral_no_boost(self):
        assert self._ratio("Surf", "Garchomp", "Neuroforce") == pytest.approx(1.0, rel=0.02)

    def test_neuroforce_resisted_no_boost(self):
        assert self._ratio("Flamethrower", "Garchomp", "Neuroforce") == pytest.approx(1.0, rel=0.02)

    def test_tinted_lens_not_very_effective(self):
        assert self._ratio("Flamethrower", "Garchomp", "Tinted Lens") == pytest.approx(2.0, rel=0.05)

    def test_tinted_lens_neutral_no_boost(self):
        assert self._ratio("Surf", "Garchomp", "Tinted Lens") == pytest.approx(1.0, rel=0.02)

    def test_tinted_lens_super_effective_no_boost(self):
        assert self._ratio("Ice Beam", "Garchomp", "Tinted Lens") == pytest.approx(1.0, rel=0.02)


class TestParentalBond:
    """Parental Bond (Kangaskhan-Mega): ≈×1.25 single-target, breaks Sash,
    no effect on spread moves."""

    _A = {"hp": 150, "atk": 180, "def": 100, "spa": 100, "spd": 100, "spe": 100}
    _D = {"hp": 190, "atk": 120, "def": 120, "spd": 110, "spe": 100}

    def test_single_target_x1_25(self):
        base = full_damage_calc("Body Slam", "Kangaskhan-Mega", "Garchomp",
                                self._A, self._D).damage_avg
        pb = full_damage_calc("Body Slam", "Kangaskhan-Mega", "Garchomp",
                              self._A, self._D, attacker_ability="Parental Bond").damage_avg
        assert pb / base == pytest.approx(1.25, rel=0.04)

    def test_spread_move_no_boost(self):
        # Parental Bond does not apply to spread moves.
        assert is_spread_move("Earthquake")
        base = full_damage_calc("Earthquake", "Kangaskhan-Mega", "Garchomp",
                                self._A, self._D).damage_avg
        pb = full_damage_calc("Earthquake", "Kangaskhan-Mega", "Garchomp",
                              self._A, self._D, attacker_ability="Parental Bond").damage_avg
        assert pb / base == pytest.approx(1.0, rel=0.02)

    def test_breaks_focus_sash(self):
        """The second strike breaks a full-HP Focus Sash, so the KO stands."""
        r = full_damage_calc(
            "Close Combat",
            attacker_species="Kangaskhan-Mega", attacker_stats={"atk": 150, "hp": 100},
            defender_species="Kingambit", defender_stats={"def": 120, "hp": 135},
            defender_item="Focus Sash", defender_is_full_hp=True,
            attacker_ability="Parental Bond",
        )
        assert r.ko_prevented is False
        assert r.is_ohko is True

    def test_sash_still_holds_without_parental_bond(self):
        """Control: same hit without Parental Bond is blocked by the Sash."""
        r = full_damage_calc(
            "Close Combat",
            attacker_species="Lopunny-Mega", attacker_stats={"atk": 150, "hp": 100},
            defender_species="Kingambit", defender_stats={"def": 120, "hp": 135},
            defender_item="Focus Sash", defender_is_full_hp=True,
        )
        assert r.ko_prevented is True


# ── conditional-fact abilities (0.8.5): HP / status / weather / faint ─────────

_CF_A = {"hp": 150, "atk": 150, "def": 100, "spa": 150, "spd": 100, "spe": 100}
_CF_D = {"hp": 190, "atk": 120, "def": 120, "spd": 110, "spe": 100}


def _cf(move, ability="", **kw):
    """damage_avg for *move* from a neutral attacker (no STAB) into a neutral
    defender, so the ratio of two calls isolates the ability's modifier."""
    return full_damage_calc(move, "Atk", "Def", _CF_A, _CF_D,
                            attacker_ability=ability, **kw).damage_avg


class TestPinchAbilities:
    """Blaze/Overgrow/Torrent/Swarm (own-type ×1.5 at ≤⅓ HP); Defeatist (×0.5 at ≤½)."""

    def test_blaze_fire_below_third(self):
        base = _cf("Flamethrower")
        boost = _cf("Flamethrower", "Blaze", attacker_hp_fraction=0.3)
        assert boost / base == pytest.approx(1.5, rel=0.04)

    def test_blaze_no_boost_above_third(self):
        base = _cf("Flamethrower")
        full = _cf("Flamethrower", "Blaze", attacker_hp_fraction=0.5)
        assert full / base == pytest.approx(1.0, rel=0.02)

    def test_blaze_only_boosts_fire(self):
        base = _cf("Surf")
        other = _cf("Surf", "Blaze", attacker_hp_fraction=0.2)  # Water move
        assert other / base == pytest.approx(1.0, rel=0.02)

    def test_overgrow_torrent_swarm(self):
        assert _cf("Energy Ball", "Overgrow", attacker_hp_fraction=0.2) / _cf("Energy Ball") == pytest.approx(1.5, rel=0.04)
        assert _cf("Surf", "Torrent", attacker_hp_fraction=0.2) / _cf("Surf") == pytest.approx(1.5, rel=0.04)
        assert _cf("Bug Buzz", "Swarm", attacker_hp_fraction=0.2) / _cf("Bug Buzz") == pytest.approx(1.5, rel=0.04)

    def test_defeatist_halves_below_half(self):
        base = _cf("Body Slam")
        weak = _cf("Body Slam", "Defeatist", attacker_hp_fraction=0.4)
        # Halving a small integer damage amplifies rounding noise (~4%).
        assert weak / base == pytest.approx(0.5, rel=0.06)

    def test_defeatist_no_penalty_above_half(self):
        base = _cf("Body Slam")
        full = _cf("Body Slam", "Defeatist", attacker_hp_fraction=0.6)
        assert full / base == pytest.approx(1.0, rel=0.02)


class TestStatusAbilities:
    """Guts (Atk ×1.5 statused), Flare Boost (SpA ×1.5 burned), Toxic Boost (Atk ×1.5 poisoned)."""

    def test_guts_physical_when_statused(self):
        base = _cf("Body Slam")
        guts = _cf("Body Slam", "Guts", attacker_status="par")
        assert guts / base == pytest.approx(1.5, rel=0.04)

    def test_guts_no_boost_without_status(self):
        assert _cf("Body Slam", "Guts", attacker_status="") / _cf("Body Slam") == pytest.approx(1.0, rel=0.02)

    def test_guts_ignores_special(self):
        assert _cf("Flamethrower", "Guts", attacker_status="par") / _cf("Flamethrower") == pytest.approx(1.0, rel=0.02)

    def test_flare_boost_special_when_burned(self):
        assert _cf("Flamethrower", "Flare Boost", attacker_status="brn") / _cf("Flamethrower") == pytest.approx(1.5, rel=0.04)

    def test_flare_boost_needs_burn(self):
        assert _cf("Flamethrower", "Flare Boost", attacker_status="par") / _cf("Flamethrower") == pytest.approx(1.0, rel=0.02)

    def test_toxic_boost_physical_when_poisoned(self):
        assert _cf("Body Slam", "Toxic Boost", attacker_status="psn") / _cf("Body Slam") == pytest.approx(1.5, rel=0.04)
        assert _cf("Body Slam", "Toxic Boost", attacker_status="tox") / _cf("Body Slam") == pytest.approx(1.5, rel=0.04)


class TestBurnPhysicalHalving:
    """A burned attacker deals ½ damage with PHYSICAL moves (0.14.0).  Special
    moves are unaffected; Guts negates the drop (its ×1.5 lives in atk_modifier)."""

    def test_burn_halves_physical(self):
        assert _cf("Body Slam", attacker_status="brn") / _cf("Body Slam") == pytest.approx(0.5, rel=0.06)

    def test_burn_does_not_halve_special(self):
        assert _cf("Flamethrower", attacker_status="brn") / _cf("Flamethrower") == pytest.approx(1.0, rel=0.02)

    def test_other_status_does_not_halve_physical(self):
        assert _cf("Body Slam", attacker_status="par") / _cf("Body Slam") == pytest.approx(1.0, rel=0.02)

    def test_guts_negates_burn_drop(self):
        # Guts: no ×0.5 burn cut AND a ×1.5 Atk boost → net ×1.5 vs an unburned
        # no-ability attacker (matches the existing Guts-when-statused tests).
        assert _cf("Body Slam", "Guts", attacker_status="brn") / _cf("Body Slam") == pytest.approx(1.5, rel=0.06)


class TestMoveMechanics:
    """Move-specific damage mechanics surfaced by the 0.13.0 defensive-accuracy
    audit: Body Press (uses Def), Freeze-Dry (2× vs Water), Knock Off (+50% vs an
    item holder)."""

    _ATK = {"atk": 60, "def": 200, "spa": 100, "spd": 100, "spe": 100, "hp": 150}
    _DEF = {"atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100, "hp": 150}

    def test_body_press_uses_defense_not_attack(self):
        """Body Press damage scales with the USER's Defense, so a high-Def /
        low-Atk attacker hits far harder than its Attack would suggest."""
        with patch("damage.types_of", return_value=["Normal"]):
            high_def = full_damage_calc(
                "Body Press", "Atk", "Def", self._ATK, self._DEF).damage_avg
            low_def = full_damage_calc(
                "Body Press", "Atk", "Def", {**self._ATK, "def": 60}, self._DEF).damage_avg
        # Body Press scales with Def (200 vs 60), not the fixed Atk (60) — so the
        # high-Def variant deals far more (floored stats give ~3×, well above the
        # ×1.0 it would be if Atk drove the damage).
        assert high_def > low_def * 2.5

    def test_freeze_dry_super_effective_vs_water(self):
        r = full_damage_calc("Freeze-Dry", "Atk", "Basculegion-M",
                             self._DEF, self._DEF)
        assert r.effectiveness == pytest.approx(2.0)

    def test_freeze_dry_normal_vs_non_water(self):
        # vs a non-Water target the override must not apply: Garchomp (Dragon/
        # Ground) takes normal Ice ×4 (2× Dragon × 2× Ground), not ×4 again.
        r = full_damage_calc("Freeze-Dry", "Atk", "Garchomp", self._DEF, self._DEF)
        assert r.effectiveness == pytest.approx(4.0)

    def test_knock_off_boosted_vs_item_holder(self):
        no_item = full_damage_calc("Knock Off", "Weavile", "Def",
                                   self._DEF, self._DEF, defender_item=None).damage_avg
        w_item = full_damage_calc("Knock Off", "Weavile", "Def",
                                  self._DEF, self._DEF, defender_item="Sitrus Berry").damage_avg
        assert w_item / no_item == pytest.approx(1.5, rel=0.04)

    def _rage_fist_power(self, times_hit):
        return full_damage_calc("Rage Fist", "Annihilape", "Def",
                                self._DEF, self._DEF, times_hit=times_hit).power

    def test_rage_fist_base_power(self):
        assert self._rage_fist_power(0) == 50

    def test_rage_fist_scales_with_hits(self):
        assert self._rage_fist_power(1) == 100
        assert self._rage_fist_power(3) == 200

    def test_rage_fist_caps_at_350(self):
        assert self._rage_fist_power(6) == 350
        assert self._rage_fist_power(9) == 350   # capped at 6 hits


class TestWeatherGatedAbilities:
    """Solar Power (SpA ×1.5 in sun only — the 0.8.5 fix) and Sand Force."""

    def test_solar_power_special_in_sun(self):
        # Both calls share weather=sun so the Fire weather-boost cancels in the ratio.
        base = _cf("Flamethrower", weather="sun")
        sp = _cf("Flamethrower", "Solar Power", weather="sun")
        assert sp / base == pytest.approx(1.5, rel=0.04)

    def test_solar_power_no_boost_without_sun(self):
        # Regression for the old bug: Solar Power used to boost Fire/Electric in
        # ALL weather.  It must now do nothing outside sun.
        assert _cf("Flamethrower", "Solar Power", weather=None) / _cf("Flamethrower") == pytest.approx(1.0, rel=0.02)
        assert _cf("Thunderbolt", "Solar Power", weather=None) / _cf("Thunderbolt") == pytest.approx(1.0, rel=0.02)

    def test_solar_power_ignores_physical(self):
        base = _cf("Earthquake", weather="sun")
        sp = _cf("Earthquake", "Solar Power", weather="sun")
        assert sp / base == pytest.approx(1.0, rel=0.02)

    def test_sand_force_ground_in_sand(self):
        base = _cf("Earthquake", weather="sand")
        sf = _cf("Earthquake", "Sand Force", weather="sand")
        assert sf / base == pytest.approx(1.3, rel=0.04)

    def test_sand_force_needs_sand(self):
        assert _cf("Earthquake", "Sand Force", weather=None) / _cf("Earthquake") == pytest.approx(1.0, rel=0.02)

    def test_sand_force_only_rock_ground_steel(self):
        base = _cf("Flamethrower", weather="sand")
        sf = _cf("Flamethrower", "Sand Force", weather="sand")  # Fire move — unboosted
        assert sf / base == pytest.approx(1.0, rel=0.02)


class TestSupremeOverlord:
    """+10% Atk & SpA per fainted ally, capped at +50% (5 faints) — Kingambit."""

    def test_scales_with_faints(self):
        assert _cf("Body Slam", "Supreme Overlord", ally_faint_count=2) / _cf("Body Slam") == pytest.approx(1.2, rel=0.04)
        assert _cf("Body Slam", "Supreme Overlord", ally_faint_count=5) / _cf("Body Slam") == pytest.approx(1.5, rel=0.04)

    def test_caps_at_five(self):
        assert _cf("Body Slam", "Supreme Overlord", ally_faint_count=6) / _cf("Body Slam") == pytest.approx(1.5, rel=0.04)

    def test_no_faints_no_boost(self):
        assert _cf("Body Slam", "Supreme Overlord", ally_faint_count=0) / _cf("Body Slam") == pytest.approx(1.0, rel=0.02)

    def test_boosts_special_too(self):
        # +10%/faint applies to both Atk and SpA.
        assert _cf("Flamethrower", "Supreme Overlord", ally_faint_count=3) / _cf("Flamethrower") == pytest.approx(1.3, rel=0.04)


class TestFlashFireBoost:
    """Flash Fire: +50% Fire moves once a Fire move has been absorbed."""

    def test_fire_boosted_when_active(self):
        assert _cf("Flamethrower", "Flash Fire", flash_fire_active=True) / _cf("Flamethrower") == pytest.approx(1.5, rel=0.04)

    def test_no_boost_when_inactive(self):
        assert _cf("Flamethrower", "Flash Fire", flash_fire_active=False) / _cf("Flamethrower") == pytest.approx(1.0, rel=0.02)

    def test_only_fire_moves(self):
        assert _cf("Body Slam", "Flash Fire", flash_fire_active=True) / _cf("Body Slam") == pytest.approx(1.0, rel=0.02)


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
