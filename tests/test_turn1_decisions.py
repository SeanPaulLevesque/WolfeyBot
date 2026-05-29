"""test_turn1_decisions.py — Integration tests for all Turn 1 opening decisions.

Each of the 120 test cases corresponds to one row in the current turn1_summary.md.
Expected values — move name, target species, and weight — are taken directly
from that file and treated as ground truth.  Any regression in the scoring
pipeline will cause the corresponding test(s) to fail, giving an immediate
reference point for what changed.  (The summary's engine version comes from
version.__version__; test_summary_header_matches_version guards that it was
regenerated after a version bump.)

Sections mirror the six lead configurations in turn1_summary.md:
  1. Aerodactyl[A] + Venusaur[B]  (mega: Aerodactyl)
  2. Aerodactyl[A] + Venusaur[B]  (mega: Venusaur)
  3. Garchomp[A]   + Kingambit[B] (no mega)
  4. Aerodactyl[A] + Sneasler[B]  (mega: Aerodactyl)
  5. Garchomp[A]   + Venusaur[B]  (mega: Venusaur)
  6. Sneasler[A]   + Kingambit[B] (no mega)

Run:
    .venv\\Scripts\\pytest tests/test_turn1_decisions.py
"""
from __future__ import annotations

import pytest
from battle import BattleState, Pokemon
from decision.modules import (
    make_engine,
    _partner_can_ohko,
    _opp_neutralized_before_acting,
    _opp_has_attacking_priority,
    _ko_before_acting,
)
from team import find_member

# ── Shared engine (stateless — safe to share across all tests) ─────────────────

_ALL_TEAM = ["Aerodactyl", "Kingambit", "Sneasler", "Basculegion", "Venusaur", "Garchomp"]
_ENGINE = make_engine()


# ── State / action builders ────────────────────────────────────────────────────

def _our_mon(sp: str) -> Pokemon:
    tm = find_member(sp)
    hp = tm.stats["hp"]
    return Pokemon(
        ident=f"p1: {sp}", species=sp, hp=hp, max_hp=hp,
        ability=tm.ability, item=tm.item, moves=list(tm.moves),
    )


def _opp_mon(sp: str) -> Pokemon:
    return Pokemon(
        ident=f"p2: {sp}", species=sp,
        hp=100, max_hp=100, hp_is_percentage=True,
    )


def _moves(sp: str) -> list[dict]:
    tm = find_member(sp)
    return [{"move": m} for m in tm.moves] if tm else []


def _make_state(our_a: str, our_b: str, opp_a: str, opp_b: str, mega) -> BattleState:
    """Build a fresh Turn-1 BattleState for the given lead/opponent pairing."""
    bench = [s for s in _ALL_TEAM if s not in (our_a, our_b)]
    s = BattleState(battle_id="test", my_side="p1")
    s.my_actives         = [_our_mon(our_a),  _our_mon(our_b)]
    s.my_team            = list(s.my_actives)
    s.opp_actives        = [_opp_mon(opp_a),  _opp_mon(opp_b)]
    s.available_switches = [_our_mon(b) for b in bench]
    s.moves_per_slot     = [_moves(our_a), _moves(our_b)]
    s.my_last_moves      = ["", ""]
    s.opp_last_moves     = ["", ""]
    s.my_slot_decisions  = [None, None]
    s.opp_tailwind       = False
    s.opp_tailwind_turns_left = 0
    s.trick_room         = False
    s.trick_room_turns_left  = 0
    s.weather            = None
    s.my_tailwind        = False
    s.my_disabled_moves  = [None, None]
    s.my_encored_moves   = [None, None]
    s.designated_mega    = mega
    return s


def _run(our_a: str, our_b: str, opp_a: str, opp_b: str, mega) -> tuple:
    """Build a Turn-1 BattleState; return (best_a, best_b) Action objects."""
    s = _make_state(our_a, our_b, opp_a, opp_b, mega)

    ranked_a = _ENGINE.scored_actions(s, 0)
    best_a   = ranked_a[0]
    s.my_slot_decisions[0] = best_a   # slot B sees slot A's committed action

    ranked_b = _ENGINE.scored_actions(s, 1)
    best_b   = ranked_b[0]
    return best_a, best_b


def _chk(action, dec: str, opp_a: str, opp_b: str, wt: float) -> None:
    """Assert that *action* matches a turn1_summary decision string and weight.

    Decision string formats:
      "MoveName → TargetSpecies"   — attacking move; target_slot is checked
      "Protect → ?"               — Protect; target not checked
      "Switch → BenchSpecies"     — switch action; switch_target is checked
    """
    label, _, target = dec.partition(" → ")
    if label == "Switch":
        assert action.switch_target == target, (
            f"Expected Switch→{target!r}, got Switch→{action.switch_target!r}"
        )
    elif label == "Protect":
        assert action.move_name == "Protect", (
            f"Expected Protect, got {action.move_name!r}"
        )
    else:
        # Attacking move
        assert action.move_name == label, (
            f"Expected move {label!r}, got {action.move_name!r}"
        )
        expected_slot = 0 if target == opp_a else 1
        assert action.target_slot == expected_slot, (
            f"Move {label!r}: expected target_slot {expected_slot} ({target!r}), "
            f"got target_slot {action.target_slot}"
        )
    assert action.weight == pytest.approx(wt, abs=0.05), (
        f"{dec}: expected weight ≈{wt}, got {action.weight:.4f}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — Aerodactyl [A] + Venusaur [B]  (mega: Aerodactyl)
# Bench: Kingambit, Sneasler, Basculegion, Garchomp
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Close Combat → Incineroar", 4.66, "Switch → Basculegion", 3.61),
    ("Incineroar", "Whimsicott", "Dire Claw → Whimsicott", 29.80, "Low Kick → Incineroar", 2.42),
    ("Incineroar", "Garchomp", "Protect → ?", 7.50, "Protect → ?", 3.00),
    ("Incineroar", "Farigiraf", "Protect → ?", 7.50, "Kowtow Cleave → Farigiraf", 4.60),
    ("Incineroar", "Kingambit", "Close Combat → Kingambit", 22.05, "Low Kick → Incineroar", 2.15),
    ("Incineroar", "Aerodactyl", "Protect → ?", 22.50, "Iron Head → Aerodactyl", 21.37),
    ("Farigiraf", "Sneasler", "Protect → ?", 7.50, "Kowtow Cleave → Farigiraf", 4.60),
    ("Farigiraf", "Garchomp", "Close Combat → Farigiraf", 8.73, "Kowtow Cleave → Farigiraf", 2.53),
    ("Whimsicott", "Garchomp", "Dire Claw → Whimsicott", 59.61, "Kowtow Cleave → Garchomp", 2.19),
    ("Whimsicott", "Kingambit", "Dire Claw → Whimsicott", 59.61, "Low Kick → Kingambit", 25.23),
    ("Sneasler", "Garchomp", "Protect → ?", 7.50, "Protect → ?", 7.50),
    ("Sneasler", "Kingambit", "Close Combat → Kingambit", 16.54, "Switch → Garchomp", 2.66),
    ("Aerodactyl", "Garchomp", "Protect → ?", 7.50, "Iron Head → Aerodactyl", 21.37),
    ("Lopunny", "Garchomp", "Close Combat → Lopunny", 20.03, "Kowtow Cleave → Garchomp", 1.46),
    ("Weavile", "Garchomp", "Close Combat → Weavile", 31.31, "Kowtow Cleave → Garchomp", 1.46),
    ("Talonflame", "Garchomp", "Rock Tomb → Talonflame", 7.22, "Iron Head → Garchomp", 2.12),
    ("Charizard", "Incineroar", "Protect → ?", 7.50, "Protect → ?", 7.50),
    ("Rotom-Wash", "Garchomp", "Close Combat → Rotom-Wash", 4.85, "Iron Head → Garchomp", 1.41),
    ("Glimmora", "Incineroar", "Close Combat → Incineroar", 3.11, "Iron Head → Glimmora", 2.37),
    ("Pelipper", "Dragonite", "Rock Tomb → Pelipper", 5.86, "Kowtow Cleave → Pelipper", 1.38),
], ids=[f"6.{i}" for i in range(1, 21)])
def test_section6(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Sneasler", "Kingambit", opp_a, opp_b, None)
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)


# ═══════════════════════════════════════════════════════════════════════════════
# Speed-awareness regression guards (bug fix + turn-order awareness)
# ═══════════════════════════════════════════════════════════════════════════════

def test_partner_can_ohko_respects_percentage_hp():
    """A ~97%-avg hit on a full-HP opponent is NOT a guaranteed OHKO.

    Opponents are tracked at percentage HP with a placeholder ``max_hp`` (100).
    ``_partner_can_ohko`` must treat that as 'unknown' so the damage layer uses
    typical-spread HP — not read the percentage as 100 absolute HP, which made
    every mid-power hit look like a guaranteed OHKO (the bug behind case 4.6).

    Mega Aerodactyl's best single move vs a healthy opposing Aerodactyl is Rock
    Tomb at ~97% average (min roll < 100%), so this must be False.
    """
    s = _make_state("Aerodactyl", "Sneasler", "Incineroar", "Aerodactyl", "Aerodactyl")
    opp_aero = s.opp_actives[1]
    assert _partner_can_ohko(s, 0, opp_aero) is False


def test_neutralized_threat_does_not_force_protect():
    """Case 4.6: opposing Aerodactyl OHKOs our Sneasler and outspeeds it, but our
    Mega Aerodactyl is faster — so Sneasler should attack, not Protect, because
    the threat is (very likely) removed before it can act."""
    best_a, best_b = _run("Aerodactyl", "Sneasler", "Incineroar", "Aerodactyl", "Aerodactyl")
    assert best_b.move_name == "Close Combat"
    assert best_b.move_name not in {"Protect"}


def test_opp_neutralized_before_acting_detects_faster_ally_ko():
    """True when a faster ally guarantees an OHKO on the threat; False otherwise."""
    # Our Sneasler outspeeds opposing Kingambit and guaranteed-OHKOs it (Close Combat).
    s = _make_state("Aerodactyl", "Sneasler", "Incineroar", "Kingambit", "Aerodactyl")
    assert _opp_neutralized_before_acting(s, 1, s.opp_actives[1]) is True

    # Nobody guarantees an OHKO on a healthy opposing Aerodactyl before it acts.
    s2 = _make_state("Aerodactyl", "Sneasler", "Incineroar", "Aerodactyl", "Aerodactyl")
    assert _opp_neutralized_before_acting(s2, 1, s2.opp_actives[1]) is False


def test_gale_wings_talonflame_is_never_neutralized():
    """A full-HP Talonflame is assumed Gale Wings: its +1-priority Brave Bird
    lands before our KO move, so it is never 'neutralized before acting' even
    when our faster Mega Aerodactyl is guaranteed to OHKO it — and Venusaur
    therefore Protects rather than attacking into the priority hit (case 1.16)."""
    s = _make_state("Aerodactyl", "Venusaur", "Talonflame", "Garchomp", "Aerodactyl")
    talonflame = s.opp_actives[0]
    # Our Mega Aero does outspeed and guarantee-OHKO Talonflame on raw speed...
    assert _partner_can_ohko(s, 0, talonflame) is True
    # ...but Gale Wings priority means it still gets its hit off first.
    assert _opp_has_attacking_priority(talonflame) is True
    assert _opp_neutralized_before_acting(s, 0, talonflame) is False


def test_ko_before_acting_blocks_undeliverable_kill():
    """Offensive mirror of the speed gate (battle 2620687657): Garchomp is
    outsped by Weavile, which guaranteed-OHKOs it (Ice ×4), and no ally removes
    Weavile first — so Garchomp is KO'd before acting.  Its 'guaranteed OHKO' on
    the partner opponent (Alakazam) must not be credited, so it Protects instead
    of throwing away the attack."""
    s = _make_state("Venusaur", "Garchomp", "Weavile", "Alakazam", "Venusaur")
    assert _ko_before_acting(s, 1) is True          # Garchomp dies before acting
    assert _ko_before_acting(s, 0) is False         # Venusaur is not guaranteed-OHKO'd
    _best_a, best_b = _run("Venusaur", "Garchomp", "Weavile", "Alakazam", "Venusaur")
    assert best_b.move_name == "Protect"            # not the wasted Stomping Tantrum


def test_outgoing_damage_credits_ko_on_weakened_opponent():
    """A move that only does ~62% to a full-HP opponent must read as a guaranteed
    OHKO once that opponent is chipped (percentage-tracked) — so the engine
    recognises and finishes a weakened target instead of evaluating vs full HP."""
    from damage import outgoing_damage
    v = find_member("Venusaur")
    st = v.mega_stats or v.stats
    full = outgoing_damage("Venusaur", st, ["Sludge Bomb"], "Alakazam",
                           our_ability=v.ability, our_item=v.item)[0]
    chip = outgoing_damage("Venusaur", st, ["Sludge Bomb"], "Alakazam",
                           our_ability=v.ability, our_item=v.item, opp_hp_percent=41)[0]
    assert not full.is_ohko          # 62% of full HP — not a OHKO
    assert chip.is_ohko              # 62% of full ≈ 151% of a 41% bar — guaranteed KO


def test_summary_header_matches_version():
    """turn1_summary.md must be regenerated after a version bump.

    Its header records version.__version__ (the single source of truth); if this
    fails, run `.venv\\Scripts\\python.exe _gen_turn1_summary.py`.
    """
    from pathlib import Path
    from version import __version__

    summary = Path(__file__).resolve().parent.parent / "turn1_summary.md"
    header = summary.read_text(encoding="utf-8").splitlines()[2]  # "Engine vX.Y.Z | ..."
    assert f"Engine v{__version__}" in header, (
        f"turn1_summary.md header {header!r} does not match version "
        f"v{__version__} — regenerate it with _gen_turn1_summary.py."
    )


# ==============================================================================
# Section 1 — Aerodactyl [A] + Venusaur [B]  (mega: Aerodactyl)
# ==============================================================================

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Dual Wingbeat → Sneasler", 37.28, "Switch → Basculegion", 3.69),
    ("Incineroar", "Whimsicott", "Dual Wingbeat → Whimsicott", 25.46, "Earth Power → Incineroar", 2.81),
    ("Incineroar", "Garchomp", "Protect → ?", 3.00, "Protect → ?", 7.50),
    ("Incineroar", "Farigiraf", "Rock Tomb → Incineroar", 4.39, "Sludge Bomb → Farigiraf", 5.53),
    ("Incineroar", "Kingambit", "Protect → ?", 7.50, "Protect → ?", 7.50),
    ("Incineroar", "Aerodactyl", "Rock Tomb → Aerodactyl", 4.42, "Switch → Basculegion", 4.66),
    ("Farigiraf", "Sneasler", "Dual Wingbeat → Sneasler", 37.28, "Sludge Bomb → Farigiraf", 3.68),
    ("Farigiraf", "Garchomp", "Ice Fang → Garchomp", 11.08, "Sludge Bomb → Farigiraf", 3.68),
    ("Whimsicott", "Garchomp", "Dual Wingbeat → Whimsicott", 50.91, "Giga Drain → Garchomp", 1.91),
    ("Whimsicott", "Kingambit", "Dual Wingbeat → Whimsicott", 50.91, "Earth Power → Kingambit", 3.07),
    ("Sneasler", "Garchomp", "Dual Wingbeat → Sneasler", 18.64, "Giga Drain → Garchomp", 1.27),
    ("Sneasler", "Kingambit", "Dual Wingbeat → Sneasler", 18.64, "Earth Power → Kingambit", 2.05),
    ("Aerodactyl", "Garchomp", "Rock Tomb → Aerodactyl", 8.83, "Earth Power → Garchomp", 1.75),
    ("Lopunny", "Garchomp", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Weavile", "Garchomp", "Rock Tomb → Weavile", 3.08, "Switch → Kingambit", 1.20),
    ("Talonflame", "Garchomp", "Rock Tomb → Talonflame", 69.78, "Protect → ?", 7.50),
    ("Charizard", "Incineroar", "Rock Tomb → Charizard", 22.30, "Protect → ?", 7.50),
    ("Rotom-Wash", "Garchomp", "Ice Fang → Garchomp", 5.54, "Giga Drain → Rotom-Wash", 2.01),
    ("Glimmora", "Incineroar", "Protect → ?", 3.00, "Earth Power → Glimmora", 9.13),
    ("Pelipper", "Dragonite", "Rock Tomb → Pelipper", 7.73, "Sludge Bomb → Pelipper", 1.43),
], ids=[f"1.{i}" for i in range(1, 21)])
def test_section1(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Aerodactyl", "Venusaur", opp_a, opp_b, "Aerodactyl")
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)


# ==============================================================================
# Section 2 — Aerodactyl [A] + Venusaur [B]  (mega: Venusaur)
# ==============================================================================

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Dual Wingbeat → Sneasler", 24.58, "Earth Power → Incineroar", 2.01),
    ("Incineroar", "Whimsicott", "Dual Wingbeat → Whimsicott", 4.48, "Sludge Bomb → Whimsicott", 27.92),
    ("Incineroar", "Garchomp", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Incineroar", "Farigiraf", "Rock Tomb → Incineroar", 3.95, "Sludge Bomb → Farigiraf", 5.95),
    ("Incineroar", "Kingambit", "Protect → ?", 7.50, "Protect → ?", 3.00),
    ("Incineroar", "Aerodactyl", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Farigiraf", "Sneasler", "Dual Wingbeat → Sneasler", 24.58, "Sludge Bomb → Farigiraf", 3.96),
    ("Farigiraf", "Garchomp", "Ice Fang → Garchomp", 9.95, "Sludge Bomb → Farigiraf", 3.96),
    ("Whimsicott", "Garchomp", "Dual Wingbeat → Whimsicott", 8.96, "Sludge Bomb → Whimsicott", 20.94),
    ("Whimsicott", "Kingambit", "Dual Wingbeat → Whimsicott", 8.96, "Sludge Bomb → Whimsicott", 27.92),
    ("Sneasler", "Garchomp", "Dual Wingbeat → Sneasler", 12.29, "Giga Drain → Garchomp", 1.36),
    ("Sneasler", "Kingambit", "Dual Wingbeat → Sneasler", 12.29, "Earth Power → Kingambit", 2.24),
    ("Aerodactyl", "Garchomp", "Rock Tomb → Aerodactyl", 5.83, "Earth Power → Garchomp", 1.85),
    ("Lopunny", "Garchomp", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Weavile", "Garchomp", "Protect → ?", 7.50, "Protect → ?", 3.00),
    ("Talonflame", "Garchomp", "Rock Tomb → Talonflame", 45.31, "Giga Drain → Garchomp", 2.04),
    ("Charizard", "Incineroar", "Rock Tomb → Charizard", 18.94, "Earth Power → Incineroar", 2.01),
    ("Rotom-Wash", "Garchomp", "Ice Fang → Garchomp", 4.98, "Giga Drain → Rotom-Wash", 2.23),
    ("Glimmora", "Incineroar", "Protect → ?", 22.50, "Earth Power → Glimmora", 10.30),
    ("Pelipper", "Dragonite", "Rock Tomb → Pelipper", 7.00, "Sludge Bomb → Pelipper", 1.56),
], ids=[f"2.{i}" for i in range(1, 21)])
def test_section2(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Aerodactyl", "Venusaur", opp_a, opp_b, "Venusaur")
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)


# ==============================================================================
# Section 3 — Garchomp [A]   + Kingambit [B]  (no mega)
# ==============================================================================

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Stomping Tantrum → Sneasler", 28.49, "Protect → ?", 7.50),
    ("Incineroar", "Whimsicott", "Poison Jab → Whimsicott", 22.15, "Low Kick → Incineroar", 2.42),
    ("Incineroar", "Garchomp", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Incineroar", "Farigiraf", "Stomping Tantrum → Incineroar", 5.26, "Kowtow Cleave → Farigiraf", 4.60),
    ("Incineroar", "Kingambit", "Protect → ?", 3.00, "Low Kick → Kingambit", 8.41),
    ("Incineroar", "Aerodactyl", "Protect → ?", 3.00, "Iron Head → Aerodactyl", 21.37),
    ("Farigiraf", "Sneasler", "Stomping Tantrum → Sneasler", 28.49, "Protect → ?", 7.50),
    ("Farigiraf", "Garchomp", "Dragon Claw → Garchomp", 7.52, "Kowtow Cleave → Farigiraf", 4.60),
    ("Whimsicott", "Garchomp", "Poison Jab → Whimsicott", 29.54, "Kowtow Cleave → Garchomp", 2.19),
    ("Whimsicott", "Kingambit", "Poison Jab → Whimsicott", 44.31, "Low Kick → Kingambit", 25.23),
    ("Sneasler", "Garchomp", "Stomping Tantrum → Sneasler", 9.50, "Protect → ?", 7.50),
    ("Sneasler", "Kingambit", "Stomping Tantrum → Sneasler", 14.25, "Low Kick → Kingambit", 16.82),
    ("Aerodactyl", "Garchomp", "Dragon Claw → Garchomp", 3.76, "Iron Head → Aerodactyl", 21.37),
    ("Lopunny", "Garchomp", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Weavile", "Garchomp", "Protect → ?", 22.50, "Low Kick → Weavile", 7.58),
    ("Talonflame", "Garchomp", "Dragon Claw → Garchomp", 3.76, "Kowtow Cleave → Talonflame", 2.72),
    ("Charizard", "Incineroar", "Protect → ?", 3.00, "Protect → ?", 7.50),
    ("Rotom-Wash", "Garchomp", "Stomping Tantrum → Rotom-Wash", 24.02, "Kowtow Cleave → Garchomp", 1.46),
    ("Glimmora", "Incineroar", "Stomping Tantrum → Glimmora", 25.25, "Low Kick → Incineroar", 1.62),
    ("Pelipper", "Dragonite", "Dragon Claw → Pelipper", 5.94, "Kowtow Cleave → Pelipper", 1.38),
], ids=[f"3.{i}" for i in range(1, 21)])
def test_section3(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Garchomp", "Kingambit", opp_a, opp_b, None)
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)


# ==============================================================================
# Section 4 — Aerodactyl [A] + Sneasler [B]  (mega: Aerodactyl)
# ==============================================================================

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Dual Wingbeat → Sneasler", 37.28, "Close Combat → Incineroar", 3.11),
    ("Incineroar", "Whimsicott", "Dual Wingbeat → Whimsicott", 25.46, "Close Combat → Incineroar", 4.66),
    ("Incineroar", "Garchomp", "Protect → ?", 3.00, "Protect → ?", 7.50),
    ("Incineroar", "Farigiraf", "Rock Tomb → Incineroar", 4.39, "Dire Claw → Farigiraf", 5.39),
    ("Incineroar", "Kingambit", "Protect → ?", 3.00, "Close Combat → Kingambit", 16.54),
    ("Incineroar", "Aerodactyl", "Rock Tomb → Aerodactyl", 4.42, "Close Combat → Incineroar", 4.66),
    ("Farigiraf", "Sneasler", "Dual Wingbeat → Sneasler", 37.28, "Close Combat → Farigiraf", 4.37),
    ("Farigiraf", "Garchomp", "Ice Fang → Garchomp", 11.08, "Close Combat → Farigiraf", 6.55),
    ("Whimsicott", "Garchomp", "Dual Wingbeat → Whimsicott", 50.91, "Close Combat → Garchomp", 3.13),
    ("Whimsicott", "Kingambit", "Dual Wingbeat → Whimsicott", 50.91, "Close Combat → Kingambit", 33.07),
    ("Sneasler", "Garchomp", "Dual Wingbeat → Sneasler", 18.64, "Switch → Basculegion", 3.85),
    ("Sneasler", "Kingambit", "Dual Wingbeat → Sneasler", 18.64, "Close Combat → Kingambit", 22.05),
    ("Aerodactyl", "Garchomp", "Rock Tomb → Aerodactyl", 8.83, "Switch → Basculegion", 4.16),
    ("Lopunny", "Garchomp", "Protect → ?", 3.00, "Close Combat → Lopunny", 15.02),
    ("Weavile", "Garchomp", "Rock Tomb → Weavile", 3.08, "Close Combat → Weavile", 16.70),
    ("Talonflame", "Garchomp", "Rock Tomb → Talonflame", 69.78, "Protect → ?", 7.50),
    ("Charizard", "Incineroar", "Rock Tomb → Charizard", 22.30, "Close Combat → Incineroar", 4.66),
    ("Rotom-Wash", "Garchomp", "Ice Fang → Garchomp", 5.54, "Close Combat → Rotom-Wash", 3.64),
    ("Glimmora", "Incineroar", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Pelipper", "Dragonite", "Rock Tomb → Pelipper", 7.73, "Switch → Venusaur", 2.61),
], ids=[f"4.{i}" for i in range(1, 21)])
def test_section4(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Aerodactyl", "Sneasler", opp_a, opp_b, "Aerodactyl")
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)


# ==============================================================================
# Section 5 — Garchomp [A]   + Venusaur [B]  (mega: Venusaur)
# ==============================================================================

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Stomping Tantrum → Sneasler", 28.49, "Earth Power → Incineroar", 2.01),
    ("Incineroar", "Whimsicott", "Poison Jab → Whimsicott", 22.15, "Earth Power → Incineroar", 3.02),
    ("Incineroar", "Garchomp", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Incineroar", "Farigiraf", "Stomping Tantrum → Incineroar", 5.26, "Sludge Bomb → Farigiraf", 5.95),
    ("Incineroar", "Kingambit", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Incineroar", "Aerodactyl", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Farigiraf", "Sneasler", "Stomping Tantrum → Sneasler", 28.49, "Sludge Bomb → Farigiraf", 3.96),
    ("Farigiraf", "Garchomp", "Dragon Claw → Garchomp", 7.52, "Sludge Bomb → Farigiraf", 3.96),
    ("Whimsicott", "Garchomp", "Poison Jab → Whimsicott", 29.54, "Giga Drain → Garchomp", 2.04),
    ("Whimsicott", "Kingambit", "Poison Jab → Whimsicott", 44.31, "Earth Power → Kingambit", 3.36),
    ("Sneasler", "Garchomp", "Stomping Tantrum → Sneasler", 9.50, "Giga Drain → Garchomp", 1.36),
    ("Sneasler", "Kingambit", "Stomping Tantrum → Sneasler", 14.25, "Earth Power → Kingambit", 2.24),
    ("Aerodactyl", "Garchomp", "Dragon Claw → Garchomp", 3.76, "Giga Drain → Aerodactyl", 2.30),
    ("Lopunny", "Garchomp", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Weavile", "Garchomp", "Protect → ?", 7.50, "Protect → ?", 3.00),
    ("Talonflame", "Garchomp", "Dragon Claw → Garchomp", 3.76, "Sludge Bomb → Talonflame", 2.64),
    ("Charizard", "Incineroar", "Protect → ?", 3.00, "Protect → ?", 3.00),
    ("Rotom-Wash", "Garchomp", "Stomping Tantrum → Rotom-Wash", 24.02, "Giga Drain → Garchomp", 1.36),
    ("Glimmora", "Incineroar", "Stomping Tantrum → Glimmora", 25.25, "Earth Power → Incineroar", 2.01),
    ("Pelipper", "Dragonite", "Dragon Claw → Pelipper", 5.94, "Sludge Bomb → Pelipper", 1.56),
], ids=[f"5.{i}" for i in range(1, 21)])
def test_section5(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Garchomp", "Venusaur", opp_a, opp_b, "Venusaur")
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)


# ==============================================================================
# Section 6 — Sneasler [A]   + Kingambit [B]  (no mega)
# ==============================================================================

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Close Combat → Incineroar", 4.66, "Switch → Basculegion", 3.61),
    ("Incineroar", "Whimsicott", "Dire Claw → Whimsicott", 29.80, "Low Kick → Incineroar", 2.42),
    ("Incineroar", "Garchomp", "Protect → ?", 7.50, "Protect → ?", 3.00),
    ("Incineroar", "Farigiraf", "Protect → ?", 7.50, "Kowtow Cleave → Farigiraf", 4.60),
    ("Incineroar", "Kingambit", "Close Combat → Kingambit", 22.05, "Low Kick → Incineroar", 2.15),
    ("Incineroar", "Aerodactyl", "Protect → ?", 22.50, "Iron Head → Aerodactyl", 21.37),
    ("Farigiraf", "Sneasler", "Protect → ?", 7.50, "Kowtow Cleave → Farigiraf", 4.60),
    ("Farigiraf", "Garchomp", "Close Combat → Farigiraf", 8.73, "Kowtow Cleave → Farigiraf", 2.53),
    ("Whimsicott", "Garchomp", "Dire Claw → Whimsicott", 59.61, "Kowtow Cleave → Garchomp", 2.19),
    ("Whimsicott", "Kingambit", "Dire Claw → Whimsicott", 59.61, "Low Kick → Kingambit", 25.23),
    ("Sneasler", "Garchomp", "Protect → ?", 7.50, "Protect → ?", 7.50),
    ("Sneasler", "Kingambit", "Close Combat → Kingambit", 16.54, "Switch → Garchomp", 2.66),
    ("Aerodactyl", "Garchomp", "Protect → ?", 7.50, "Iron Head → Aerodactyl", 21.37),
    ("Lopunny", "Garchomp", "Close Combat → Lopunny", 20.03, "Kowtow Cleave → Garchomp", 1.46),
    ("Weavile", "Garchomp", "Close Combat → Weavile", 31.31, "Kowtow Cleave → Garchomp", 1.46),
    ("Talonflame", "Garchomp", "Rock Tomb → Talonflame", 7.22, "Iron Head → Garchomp", 2.12),
    ("Charizard", "Incineroar", "Protect → ?", 7.50, "Protect → ?", 7.50),
    ("Rotom-Wash", "Garchomp", "Close Combat → Rotom-Wash", 4.85, "Iron Head → Garchomp", 1.41),
    ("Glimmora", "Incineroar", "Close Combat → Incineroar", 3.11, "Iron Head → Glimmora", 2.37),
    ("Pelipper", "Dragonite", "Rock Tomb → Pelipper", 5.86, "Kowtow Cleave → Pelipper", 1.38),
], ids=[f"6.{i}" for i in range(1, 21)])
def test_section6(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Sneasler", "Kingambit", opp_a, opp_b, None)
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)



