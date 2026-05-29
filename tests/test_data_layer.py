"""test_data_layer.py — Pytest tests for data-layer functions not covered elsewhere.

These cases were originally scattered across data/_smoke_test.py and
data/_extended_test.py as manually-run scripts.  They are collected here so
pytest can run them automatically alongside the rest of the test suite.

Covered APIs:
  speed_distribution, prob_faster_than, update_speed_belief,
  update_speed_belief_slower, prob_outspeeds,
  archetype_usage, all_archetypes,
  teammate_distribution, WEATHER_SPEED_ABILITIES,
  types_of / get_species (form aliases)
"""
from __future__ import annotations

import pytest
from data import (
    speed_distribution,
    prob_faster_than,
    prob_outspeeds,
    update_speed_belief,
    update_speed_belief_slower,
    archetype_usage,
    all_archetypes,
    teammate_distribution,
    WEATHER_SPEED_ABILITIES,
    types_of,
    get_species,
)
from damage import type_effectiveness


# ── speed_distribution ────────────────────────────────────────────────────────

class TestSpeedDistribution:
    def test_returns_nonempty_list_for_known_species(self):
        dist = speed_distribution("Garchomp")
        assert len(dist) > 0

    def test_probabilities_sum_to_approximately_one(self):
        dist = speed_distribution("Garchomp")
        total = sum(o.probability for o in dist)
        assert abs(total - 1.0) < 0.01, f"Expected ~1.0, got {total:.4f}"

    def test_each_outcome_has_positive_probability(self):
        dist = speed_distribution("Garchomp")
        assert all(o.probability > 0 for o in dist)

    def test_each_outcome_has_positive_speed(self):
        dist = speed_distribution("Garchomp")
        assert all(o.speed > 0 for o in dist)


# ── prob_faster_than ──────────────────────────────────────────────────────────

class TestProbFasterThan:
    def test_returns_float_between_0_and_1(self):
        p = prob_faster_than("Garchomp", 130)
        assert 0.0 <= p <= 1.0

    def test_very_low_speed_threshold_gives_high_probability(self):
        # Almost all Garchomp spreads are faster than 50
        p = prob_faster_than("Garchomp", 50)
        assert p > 0.95

    def test_very_high_speed_threshold_gives_low_probability(self):
        # Very few Garchomp spreads exceed speed 300
        p = prob_faster_than("Garchomp", 300)
        assert p < 0.05


# ── update_speed_belief (faster-than observation) ────────────────────────────

class TestUpdateSpeedBelief:
    def test_all_retained_outcomes_are_faster_than_observed(self):
        dist = speed_distribution("Garchomp")
        updated = update_speed_belief(dist, observed_faster_than=130)
        assert all(o.speed > 130 for o in updated)

    def test_filtered_distribution_sums_to_1(self):
        dist = speed_distribution("Garchomp")
        updated = update_speed_belief(dist, observed_faster_than=130)
        total = sum(o.probability for o in updated)
        assert abs(total - 1.0) < 0.01

    def test_observation_reduces_number_of_outcomes(self):
        dist = speed_distribution("Garchomp")
        # Use a threshold above Garchomp's minimum spread (≥135) to ensure
        # at least some outcomes are filtered out.
        updated = update_speed_belief(dist, observed_faster_than=140)
        assert len(updated) < len(dist)


# ── update_speed_belief_slower (slower-than observation) ─────────────────────

class TestUpdateSpeedBeliefSlower:
    def test_all_retained_outcomes_are_slower_than_observed(self):
        dist = speed_distribution("Garchomp")
        updated = update_speed_belief_slower(dist, observed_slower_than=200)
        assert all(o.speed < 200 for o in updated)

    def test_filtered_distribution_sums_to_1(self):
        dist = speed_distribution("Garchomp")
        updated = update_speed_belief_slower(dist, observed_slower_than=200)
        total = sum(o.probability for o in updated)
        assert abs(total - 1.0) < 0.01


# ── prob_outspeeds ────────────────────────────────────────────────────────────

class TestProbOutspeeds:
    def test_returns_float_between_0_and_1(self):
        p = prob_outspeeds("Sneasler", "Garchomp")
        assert 0.0 <= p <= 1.0

    def test_faster_species_has_higher_outspeed_probability(self):
        # Sneasler (high base spe) should outspeed Garchomp more often
        # than a slow species like Farigiraf
        p_fast = prob_outspeeds("Sneasler", "Garchomp")
        p_slow = prob_outspeeds("Farigiraf", "Garchomp")
        assert p_fast > p_slow


# ── archetype_usage ───────────────────────────────────────────────────────────

class TestArchetypeUsage:
    def test_trickroom_archetype_is_positive(self):
        tr = archetype_usage("trickroom")
        assert tr >= 0

    def test_returns_float(self):
        tr = archetype_usage("trickroom")
        assert isinstance(tr, float)


# ── all_archetypes ────────────────────────────────────────────────────────────

class TestAllArchetypes:
    def test_returns_nonempty_dict(self):
        arcs = all_archetypes()
        assert isinstance(arcs, dict)
        assert len(arcs) > 0

    def test_all_values_are_numeric(self):
        arcs = all_archetypes()
        for k, v in arcs.items():
            assert isinstance(v, (int, float)), f"Archetype {k!r} has non-numeric value {v!r}"


# ── teammate_distribution ─────────────────────────────────────────────────────

class TestTeammateDistribution:
    def test_returns_list_for_popular_species(self):
        mates = teammate_distribution("Garchomp")
        assert isinstance(mates, list)

    def test_entries_are_tuples_of_species_and_probability(self):
        mates = teammate_distribution("Garchomp")
        if mates:  # may be empty for species with no data
            name, prob = mates[0]
            assert isinstance(name, str)
            assert isinstance(prob, float)


# ── WEATHER_SPEED_ABILITIES ───────────────────────────────────────────────────

class TestWeatherSpeedAbilities:
    def test_is_nonempty_dict(self):
        assert isinstance(WEATHER_SPEED_ABILITIES, dict)
        assert len(WEATHER_SPEED_ABILITIES) > 0

    def test_contains_swift_swim(self):
        assert "Swift Swim" in WEATHER_SPEED_ABILITIES

    def test_swift_swim_maps_to_rain(self):
        assert WEATHER_SPEED_ABILITIES["Swift Swim"] == "rain"

    def test_contains_sand_rush(self):
        assert "Sand Rush" in WEATHER_SPEED_ABILITIES

    def test_contains_chlorophyll(self):
        assert "Chlorophyll" in WEATHER_SPEED_ABILITIES


# ── Form aliases ──────────────────────────────────────────────────────────────

class TestFormAliases:
    """Alternate battle-form names resolve to their base species' typing.

    Showdown reports mid-battle form changes (e.g. Aegislash switching to
    Blade forme) using the form-specific species name.  The alias table in
    data/species.py must map these back to the canonical entry so damage
    calculations use the correct types.
    """

    def test_aegislash_blade_resolves_to_steel_ghost(self):
        assert types_of("Aegislash-Blade") == ["Steel", "Ghost"]

    def test_aegislash_shield_resolves_to_steel_ghost(self):
        assert types_of("Aegislash-Shield") == ["Steel", "Ghost"]

    def test_mimikyu_busted_resolves_to_ghost_fairy(self):
        assert types_of("Mimikyu-Busted") == ["Ghost", "Fairy"]

    def test_palafin_hero_resolves_to_water(self):
        assert types_of("Palafin-Hero") == ["Water"]

    def test_morpeko_hangry_resolves_to_electric_dark(self):
        assert types_of("Morpeko-Hangry") == ["Electric", "Dark"]

    def test_greninja_ash_resolves_to_water_dark(self):
        assert types_of("Greninja-Ash") == ["Water", "Dark"]

    def test_base_form_unaffected(self):
        """The canonical entry is still accessible under its own name."""
        assert types_of("Aegislash") == ["Steel", "Ghost"]

    def test_unknown_form_returns_none(self):
        assert types_of("Fakemon-Busted") is None

    def test_get_species_alias_returns_entry(self):
        """get_species should resolve aliases so callers get a full data dict."""
        entry = get_species("Aegislash-Blade")
        assert entry is not None
        assert entry["types"] == ["Steel", "Ghost"]


# ── Aegislash-Blade immunity regression ──────────────────────────────────────

class TestAegislashBladeImmunity:
    """Regression for battle-gen9championsvgc2026regma-2617643457.

    Aegislash-Blade was absent from the species DB so types_of() returned None,
    causing the damage engine to fall back to ["Normal"].  This made Fighting
    look ×2 effective (Sneasler chose Close Combat) and Poison look ×1 effective
    (Venusaur chose Sludge Bomb) when both should be ×0 (immune).
    """

    def test_fighting_is_immune_vs_aegislash_blade(self):
        opp_types = types_of("Aegislash-Blade")
        assert opp_types is not None
        assert type_effectiveness("Fighting", opp_types) == 0.0

    def test_poison_is_immune_vs_aegislash_blade(self):
        opp_types = types_of("Aegislash-Blade")
        assert opp_types is not None
        assert type_effectiveness("Poison", opp_types) == 0.0

    def test_ground_is_supereffective_vs_aegislash(self):
        """Earth Power (Ground) is ×2 vs Steel, ×1 vs Ghost → net ×2."""
        opp_types = types_of("Aegislash-Blade")
        assert type_effectiveness("Ground", opp_types) == 2.0

    def test_dark_is_supereffective_vs_aegislash(self):
        """Dark is ×2 vs Ghost, ×1 vs Steel (Gen 6+ removed Steel resist) → net ×2."""
        opp_types = types_of("Aegislash-Blade")
        assert type_effectiveness("Dark", opp_types) == 2.0
