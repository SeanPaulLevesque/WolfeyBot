"""test_battle_utils.py — Unit tests for battle.py utility functions.

Covers the pure helper functions at the bottom of battle.py as well as
the Pokemon dataclass.  These functions are stateless and have no I/O,
so every test here runs in isolation with zero mocking.
"""
import pytest
from battle import (
    Pokemon,
    _parse_hp,
    _parse_status,
    _side_from_ident,
    _slot_from_ident,
    _normalize_ident,
    _update_or_add,
)


# ── _parse_hp ────────────────────────────────────────────────────────────────

class TestParseHp:
    def test_normal_condition(self):
        assert _parse_hp("281/281") == (281, 281)

    def test_with_status(self):
        assert _parse_hp("150/281 brn") == (150, 281)

    def test_fainted(self):
        assert _parse_hp("0 fnt") == (0, 0)

    def test_empty_string(self):
        assert _parse_hp("") == (0, 0)

    def test_percentage_hp(self):
        """Showdown sends opponents as x/100 percentages."""
        assert _parse_hp("72/100") == (72, 100)

    def test_full_hp_with_tox(self):
        assert _parse_hp("300/300 tox") == (300, 300)


# ── _parse_status ────────────────────────────────────────────────────────────

class TestParseStatus:
    def test_burn(self):
        assert _parse_status("281/281 brn") == "brn"

    def test_paralysis(self):
        assert _parse_status("281/281 par") == "par"

    def test_toxic(self):
        assert _parse_status("281/281 tox") == "tox"

    def test_no_status(self):
        assert _parse_status("281/281") is None

    def test_fainted_returns_none(self):
        assert _parse_status("0 fnt") is None

    def test_empty_string_returns_none(self):
        assert _parse_status("") is None


# ── _side_from_ident ─────────────────────────────────────────────────────────

class TestSideFromIdent:
    def test_p1_slot_a(self):
        assert _side_from_ident("p1a: Garganacl") == "p1"

    def test_p2_slot_b(self):
        assert _side_from_ident("p2b: Garchomp") == "p2"

    def test_short_ident(self):
        assert _side_from_ident("p1: Garganacl") == "p1"


# ── _slot_from_ident ─────────────────────────────────────────────────────────

class TestSlotFromIdent:
    def test_slot_a_is_0(self):
        assert _slot_from_ident("p1a: Garganacl") == 0

    def test_slot_b_is_1(self):
        assert _slot_from_ident("p1b: Clefable") == 1

    def test_no_slot_letter_defaults_to_0(self):
        """'p1: Garganacl' has no slot letter — should default to slot 0."""
        assert _slot_from_ident("p1: Garganacl") == 0

    def test_p2_slot_b(self):
        assert _slot_from_ident("p2b: Incineroar") == 1


# ── _normalize_ident ─────────────────────────────────────────────────────────

class TestNormalizeIdent:
    def test_removes_slot_letter(self):
        assert _normalize_ident("p1a: Garganacl") == "p1: Garganacl"

    def test_slot_b_removed(self):
        assert _normalize_ident("p2b: Garchomp") == "p2: Garchomp"

    def test_already_normalized(self):
        """Idents without a slot letter should pass through unchanged."""
        assert _normalize_ident("p1: Garganacl") == "p1: Garganacl"


# ── Pokemon dataclass ────────────────────────────────────────────────────────

class TestPokemonHpFraction:
    def make_mon(self, hp, max_hp):
        return Pokemon(
            ident="p1: TestMon",
            species="TestMon",
            hp=hp,
            max_hp=max_hp,
        )

    def test_full_hp(self):
        assert self.make_mon(300, 300).hp_fraction == 1.0

    def test_half_hp(self):
        assert self.make_mon(150, 300).hp_fraction == 0.5

    def test_zero_max_hp_guard(self):
        """Guard against division by zero when max_hp is 0."""
        assert self.make_mon(0, 0).hp_fraction == 0.0

    def test_zero_hp(self):
        assert self.make_mon(0, 300).hp_fraction == 0.0


# ── _update_or_add ───────────────────────────────────────────────────────────

class TestUpdateOrAdd:
    def _make(self, species, hp=300, side="p1"):
        return Pokemon(
            ident=f"{side}: {species}",
            species=species,
            hp=hp,
            max_hp=300,
        )

    def test_updates_existing_entry(self):
        original = self._make("Garchomp", hp=300)
        team = [original]
        updated_mon = self._make("Garchomp", hp=150)
        result = _update_or_add(team, updated_mon)
        assert result.hp == 150
        assert len(team) == 1  # no duplicate added

    def test_appends_new_entry(self):
        team = [self._make("Garchomp")]
        new_mon = self._make("Incineroar")
        _update_or_add(team, new_mon)
        assert len(team) == 2
        assert team[1].species == "Incineroar"

    def test_returns_the_stored_instance(self):
        team = []
        mon = self._make("Sylveon")
        returned = _update_or_add(team, mon)
        assert returned is team[0]
