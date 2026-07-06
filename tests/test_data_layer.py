"""test_data_layer.py — Pytest tests for data-layer functions not covered elsewhere.

These cases were originally scattered across data/_smoke_test.py and
data/_extended_test.py as manually-run scripts.  They are collected here so
pytest can run them automatically alongside the rest of the test suite.

Covered APIs:
  speed_distribution, prob_faster_than, update_speed_belief,
  update_speed_belief_slower, prob_outspeeds,
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
    teammate_distribution,
    WEATHER_SPEED_ABILITIES,
    types_of,
    get_species,
    assumed_forme,
    mega_stones,
    mega_forme_for_stone,
    note_gap,
    drain_gaps,
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
        # Threshold must sit above Garchomp's slowest outcome so the filter
        # removes at least one.  The M-B usage file (0.37.0) lists only
        # max-speed spreads — two outcomes, Adamant 154 and Jolly 169 — so the
        # threshold sits between them.  (Same maintenance as 0.8.0, when the
        # corrected SP→stat mapping moved the outcomes past the old value.)
        updated = update_speed_belief(dist, observed_faster_than=160)
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

    def test_bare_meowstic_resolves_to_male_entry(self):
        """Showdown's species string for male Meowstic is the bare name; the
        slim DB only has gendered entries.  Caught live by data_gaps (0.7.6
        run): an opposing Meowstic had no stats/types — invisible to the
        engine in both damage directions."""
        assert types_of("Meowstic") == ["Psychic"]
        from data import base_stats
        assert base_stats("Meowstic") is not None


class TestCosmeticFormeFallback:
    """Progressive suffix stripping resolves decoration formes Showdown
    reports verbatim (caught live: stats:/sets:Alcremie-Rainbow-Swirl made an
    opposing Alcremie invisible during the 0.7.7 run)."""

    def test_two_level_cosmetic_forme_resolves_in_species_db(self):
        from data import base_stats
        assert types_of("Alcremie-Rainbow-Swirl") == ["Fairy"]
        assert base_stats("Alcremie-Rainbow-Swirl") is not None

    def test_two_level_cosmetic_forme_resolves_in_sets_db(self):
        from data import move_distribution, get_sets
        assert get_sets("Alcremie-Rainbow-Swirl") is not None
        assert move_distribution("Alcremie-Rainbow-Swirl") == move_distribution("Alcremie")

    def test_unknown_species_still_fails_and_flags(self):
        """The fallback must not invent data: a fully unknown dashed name
        resolves nowhere and still records a stats gap."""
        from data import base_stats, get_sets
        from damage import _most_common_stats
        drain_gaps()
        assert base_stats("Fakemon-Foo-Bar") is None
        assert get_sets("Fakemon-Foo-Bar") is None
        assert _most_common_stats("Fakemon-Foo-Bar") is None
        assert any(g.startswith("stats:Fakemon") for g in drain_gaps())

    def test_exact_and_mega_resolution_unchanged(self):
        """The strip is a LAST resort — exact entries and the Lopunny-Mega
        fallback keep winning first."""
        assert assumed_forme("Charizard") == "Charizard-Mega-Y"
        from data import get_sets
        assert get_sets("Lopunny")["items"][0][0] == "Lopunnite"

    def test_distinct_forme_suffixes_never_stripped(self):
        """Type-shifted formes must NOT resolve to their base entry.
        Stunfisk-Galar has its own species entry (Ground/Steel — must not
        collapse to base Stunfisk's Ground/Electric), and in the sets layer,
        where it has no entry, it must stay unresolved (synthetic fallback +
        data_gaps) rather than inherit base Stunfisk's moveset."""
        from data import get_sets
        assert types_of("Stunfisk-Galar") == ["Ground", "Steel"]
        assert get_sets("Stunfisk-Galar") is None


class TestSetsFormeAliases:
    """Mid-battle forme changes must keep their usage data (sets layer).

    The species DB already aliased these for types/stats, but the sets layer
    did not — the engine lost move/set data the moment a |detailschange|
    fired (data_gaps caught Mimikyu-Busted, Aegislash-Blade and Palafin-Hero
    live during the 0.7.6 hundred-game run)."""

    @pytest.mark.parametrize("forme,base", [
        ("Aegislash-Blade", "Aegislash"),
        ("Aegislash-Shield", "Aegislash"),
        ("Mimikyu-Busted", "Mimikyu"),
        ("Palafin-Hero", "Palafin"),
        ("Morpeko-Hangry", "Morpeko"),
        ("Greninja-Ash", "Greninja"),
    ])
    def test_forme_resolves_to_base_usage_data(self, forme, base):
        from data import move_distribution, get_sets
        assert get_sets(forme) is not None, f"{forme} has no sets data"
        assert move_distribution(forme) == move_distribution(base)
        assert len(move_distribution(forme)) > 0


# ── assumed_forme / mega_stones (population-weighted forme inference) ─────────

class TestAssumedForme:
    """assumed_forme picks the most-likely forme by usage raw counts.

    The usage stats file mega formes as separate entries; if the mega entries
    together outnumber the base entry, the highest-count mega forme wins.
    """

    def test_majority_mega_with_xy_split_picks_dominant(self):
        """Charizard is 99% mega; Mega-Y (81%) outnumbers Mega-X (18%)."""
        assert assumed_forme("Charizard") == "Charizard-Mega-Y"

    def test_minority_mega_stays_base(self):
        """Aerodactyl is only ~22% mega — base forme wins."""
        assert assumed_forme("Aerodactyl") == "Aerodactyl"

    def test_marginal_majority_goes_mega(self):
        """Altaria megas at 50.1% of its M-B population — just over the line.
        (Was Medicham at 51% in the M-A data; Medicham is base-majority now.)"""
        assert assumed_forme("Altaria") == "Altaria-Mega"

    def test_marginal_minority_stays_base(self):
        """Gyarados megas at 49.0% — just under the line."""
        assert assumed_forme("Gyarados") == "Gyarados"

    def test_no_base_entry_resolves_to_mega(self):
        """Base Lopunny has no usage entry at all (100% mega population)."""
        assert assumed_forme("Lopunny") == "Lopunny-Mega"

    def test_no_mega_entries_resolves_to_self(self):
        assert assumed_forme("Kingambit") == "Kingambit"

    def test_unknown_species_resolves_to_self(self):
        assert assumed_forme("Fakemon") == "Fakemon"


class TestMegaStones:
    """mega_stones() is derived from the data (every -Mega entry's top item),
    not from a name-suffix heuristic."""

    def test_contains_real_stones(self):
        stones = mega_stones()
        for stone in ("Charizardite Y", "Charizardite X", "Lopunnite",
                      "Glimmoranite", "Dragoninite"):
            assert stone in stones

    def test_no_suffix_false_positives(self):
        """Eviolite ends in -ite but is not a mega stone; Focus Sash obviously
        isn't either.  (Guards against regressing to a suffix check.)"""
        stones = mega_stones()
        assert "Eviolite" not in stones
        assert "Focus Sash" not in stones

    def test_nonempty_and_frozen(self):
        stones = mega_stones()
        assert len(stones) > 30
        assert isinstance(stones, frozenset)


class TestMegaFormeForStone:
    """mega_forme_for_stone() maps a revealed stone back to its -Mega forme."""

    def test_known_stone_maps_to_forme(self):
        assert mega_forme_for_stone("Charizardite Y") == "Charizard-Mega-Y"
        assert mega_forme_for_stone("Charizardite X") == "Charizard-Mega-X"
        assert mega_forme_for_stone("Lopunnite") == "Lopunny-Mega"

    def test_non_stone_returns_none(self):
        assert mega_forme_for_stone("Focus Sash") is None
        assert mega_forme_for_stone("Eviolite") is None

    def test_every_stone_round_trips(self):
        """Every stone in mega_stones() resolves to a -Mega forme."""
        for stone in mega_stones():
            forme = mega_forme_for_stone(stone)
            assert forme is not None and "-Mega" in forme


class TestBattleFormeStats:
    """In-battle transform formes carry their own base stats, not the base
    entry's (which the suffix-strip fallback would otherwise return)."""

    def test_palafin_hero_uses_hero_attack(self):
        from data import base_stats
        assert base_stats("Palafin-Hero")["atk"] == 160      # Hero, not Zero's 70
        assert base_stats("Palafin")["atk"] == 70            # base unchanged

    def test_aegislash_blade_is_offensive_not_shield(self):
        from data import base_stats
        blade = base_stats("Aegislash-Blade")
        assert blade["atk"] == 140 and blade["def"] == 50    # Blade, not 50/140
        shield = base_stats("Aegislash")
        assert shield["atk"] == 50 and shield["def"] == 140  # Shield base unchanged


# ── Data-gap diagnostics (battle-log "data_gaps" flags) ──────────────────────

class TestDataGapDiagnostics:
    """note_gap/drain_gaps collect failed data lookups, deduped, for the
    battle log — they fire only when a lookup actually failed."""

    def test_note_drain_dedupes_and_clears(self):
        drain_gaps()  # isolate from other tests
        note_gap("types", "Fakemon")
        note_gap("types", "Fakemon")          # duplicate — collapsed
        note_gap("stats", "Othermon")
        assert drain_gaps() == ["stats:Othermon", "types:Fakemon"]
        assert drain_gaps() == []             # drained = cleared

    def test_unknown_species_stats_lookup_records_gap(self):
        from damage import _most_common_stats
        drain_gaps()
        assert _most_common_stats("Fakemon123") is None
        assert "stats:Fakemon123" in drain_gaps()

    def test_missing_types_in_damage_calc_records_gap(self):
        from damage import full_damage_calc
        drain_gaps()
        full_damage_calc(
            "Close Combat",
            attacker_species="Fakemon123", defender_species="Kingambit",
            attacker_stats={"atk": 100, "hp": 100},
            defender_stats={"def": 100, "hp": 100},
        )
        gaps = drain_gaps()
        assert "types:Fakemon123" in gaps          # attacker unknown
        assert "types:Kingambit" not in gaps       # defender fine

    def test_known_species_record_nothing(self):
        from damage import full_damage_calc, _most_common_stats
        drain_gaps()
        _most_common_stats("Kingambit")
        full_damage_calc(
            "Close Combat",
            attacker_species="Sneasler", defender_species="Kingambit",
            attacker_stats={"atk": 100, "hp": 100},
            defender_stats={"def": 100, "hp": 100},
        )
        assert drain_gaps() == []


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


# ── Hand-entered usage supplement (sets_supplement.json) ───────────────────────

class TestSetsSupplement:
    """The hand-entry supplement merges into the usage data and feeds every
    accessor.  The shipped file carries documentation (_*) keys plus any seeded
    prelim entries (battle-log-derived M-B movesets)."""

    def test_shipped_supplement_is_valid_and_well_formed(self):
        """The committed file parses, and every real (non-underscore) entry is a
        well-formed dict whose distribution sub-fields are {name: number} maps."""
        import json
        import data.sets as S
        data = json.loads(S._SUPPLEMENT_FILE.read_text(encoding="utf-8"))
        for name, entry in data.items():
            if name.startswith("_"):
                continue
            assert isinstance(entry, dict), f"{name} entry must be an object"
            for field in ("abilities", "items", "spreads", "moves",
                          "teammates", "tera_types"):
                dist = entry.get(field)
                if dist is None:
                    continue
                assert isinstance(dist, dict), f"{name}.{field} must be an object"
                assert all(isinstance(v, (int, float)) for v in dist.values()), \
                    f"{name}.{field} values must be numeric percentages"

    def _reload_with(self, monkeypatch, tmp_path, payload: dict):
        """Force data.sets to reload against a temp supplement file."""
        import json
        import data.sets as S
        f = tmp_path / "supp.json"
        f.write_text(json.dumps(payload), encoding="utf-8")
        monkeypatch.setattr(S, "_SUPPLEMENT_FILE", f)
        monkeypatch.setattr(S, "_SETS", {})          # force a full reparse + merge
        monkeypatch.setattr(S, "_MEGA_STONES", None)
        monkeypatch.setattr(S, "_STONE_TO_FORME", None)
        S._load()
        return S

    def test_supplement_fills_gap_and_feeds_accessors(self, monkeypatch, tmp_path):
        """A gap-fill entry feeds item/ability/spread distributions, and a
        '-Mega' entry whose top item is its stone wires the stone↔forme maps.
        Uses a fictional species so the fixture can never collide with the real
        usage file (Scolipede-Mega, the old fixture, is in the M-B data now)."""
        S = self._reload_with(monkeypatch, tmp_path, {
            "_README": "ignored",
            "Testmon-Mega": {
                "abilities": {"Speed Boost": 100.0},
                "items": {"Testmonite": 100.0},
                "spreads": {"Jolly:0/32/0/0/4/28": 60.0},
                "moves": {"Megahorn": 97.0, "Protect": 80.0},
                "raw_count": 1500,
            },
        })
        assert S.item_distribution("Testmon-Mega")[0] == ("Testmonite", 100.0)
        assert S.ability_distribution("Testmon-Mega")[0] == ("Speed Boost", 100.0)
        assert S.spread_distribution("Testmon-Mega")[0][0] == "Jolly:0/32/0/0/4/28"
        assert S.mega_forme_for_stone("Testmonite") == "Testmon-Mega"
        assert "Testmonite" in S.mega_stones()
        assert "_README" not in S._SETS          # documentation keys are skipped

    def test_supplement_does_not_override_main_file(self, monkeypatch, tmp_path):
        """Gap-fill only: a species already in the main sets file is untouched."""
        S = self._reload_with(monkeypatch, tmp_path, {
            "Garchomp": {"items": {"Bogus Item": 99.0}},
        })
        items = dict(S.item_distribution("Garchomp"))
        assert "Bogus Item" not in items          # main file wins
        assert "Choice Scarf" in items            # real usage data preserved
