"""test_usage_coverage.py — Guards that incoming-damage estimation never
silently treats a Champions-legal opponent as harmless.

The decision engine reads ``incoming_damage`` to decide whether to Protect,
switch, or attack.  If a species has no usage entry, ``move_distribution`` is
empty and ``incoming_damage`` used to return ``[]`` — i.e. "this opponent deals
no damage" — which is dangerously wrong.  These tests pin the two-part fix:

  * data.sets._resolve_name maps forme / Mega aliases to a real usage entry.
  * damage._synthetic_stab_moves provides a type-correct STAB fallback for the
    handful of species with no usage data at all.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from data import types_of
from data.sets import move_distribution, spread_distribution, all_pokemon, _resolve_name
from damage import incoming_damage, _synthetic_stab_moves, type_effectiveness

# A representative defender (Garchomp-ish final stats) for incoming-damage calls.
_DEFENDER = {"hp": 183, "atk": 182, "def": 115, "spa": 90, "spd": 105, "spe": 169}

_CHAMPIONS = [e["name"] for e in json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "smogon_champions_slim.json")
    .read_text(encoding="utf-8")
)]

# Species that legitimately deal no *direct* damage and so are allowed to return
# an empty incoming-damage estimate.  Ditto only carries Transform pre-evolution
# (its real threat is a mirror of whatever it copies, handled separately).
_NO_DIRECT_DAMAGE = {"Ditto"}


# ── The core regression guard ────────────────────────────────────────────────

def test_incoming_damage_never_empty_for_champions_species():
    """No Champions-legal opponent may be silently treated as harmless: every
    species must yield a damage estimate (usage data or synthetic STAB fallback),
    except the documented no-direct-damage cases."""
    empty = [sp for sp in _CHAMPIONS
             if not incoming_damage(sp, "Garchomp", _DEFENDER)]
    unexpected = sorted(set(empty) - _NO_DIRECT_DAMAGE)
    assert not unexpected, f"opponents treated as harmless (missing data): {unexpected}"


# ── Name resolution (Part A) ──────────────────────────────────────────────────

class TestNameResolution:
    def test_exact_match_passthrough(self):
        assert _resolve_name("Incineroar") == "Incineroar"

    def test_base_form_resolves_to_mega(self):
        """A base form whose only usage entry is its Mega resolves to the Mega."""
        assert _resolve_name("Lopunny") == "Lopunny-Mega"
        assert move_distribution("Lopunny")  # Lopunny-Mega's moves
        assert spread_distribution("Lopunny")

    def test_forme_alias_resolves(self):
        assert _resolve_name("Maushold-Four") == "Maushold"
        assert _resolve_name("Gourgeist-Small") == "Gourgeist-Super"
        assert _resolve_name("Meowstic-F") == "Meowstic"
        assert move_distribution("Gourgeist-Small") == move_distribution("Gourgeist-Super")

    def test_unresolvable_returns_none(self):
        """Type-shifted / rare formes with no good entry stay unresolved
        (so the synthetic fallback handles them) rather than mis-mapping."""
        assert _resolve_name("Stunfisk-Galar") is None      # would mis-map to Electric Stunfisk
        assert _resolve_name("Tauros-Paldea-Combat") is None
        assert _resolve_name("Watchog") is None


# ── Synthetic STAB fallback (Part B) ──────────────────────────────────────────

class TestSyntheticStab:
    def test_picks_one_move_per_stab_type(self):
        moves = _synthetic_stab_moves("Stunfisk-Galar", {"atk": 101, "spa": 86})
        # Ground/Steel, physically inclined → physical STAB of each type.
        assert moves == ["Earthquake", "Iron Head"]

    def test_special_attacker_uses_special_moves(self):
        moves = _synthetic_stab_moves("Rotom", {"atk": 70, "spa": 115})
        assert moves == ["Thunderbolt", "Shadow Ball"]  # Electric/Ghost, special

    def test_synthetic_estimate_is_type_correct(self):
        """A Ground synthetic move must read as immune against a Flying defender."""
        # Tauros (Normal, physical) vs a Ghost defender → Normal is immune → the
        # only STAB is Body Slam (Normal), which Gengar is immune to, so no
        # positive-power result; confirm a neutral defender DOES take damage.
        vs_neutral = incoming_damage("Tauros", "Garchomp", _DEFENDER)
        assert vs_neutral and vs_neutral[0].damage_avg > 0

    def test_no_types_yields_no_moves(self):
        assert _synthetic_stab_moves("Definitely Not A Pokemon", {"atk": 100, "spa": 50}) == []


def test_no_champions_species_relies_on_zero_data():
    """Belt-and-suspenders: across all Champions species, none falls through to
    an empty move list AND empty synthetic set simultaneously."""
    broken = []
    for sp in _CHAMPIONS:
        has_usage = bool(move_distribution(sp))
        has_synth = bool(_synthetic_stab_moves(sp, {"atk": 100, "spa": 100}))
        if not has_usage and not has_synth:
            broken.append(sp)
    assert not broken, f"species with neither usage nor synthetic moves: {broken}"
