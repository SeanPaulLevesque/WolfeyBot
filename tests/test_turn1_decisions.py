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
    _PROTECT_MOVES,
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
    """Build a Turn-1 BattleState; return (best_a, best_b) Action objects.

    Mirrors main.py's turn flow exactly: phase-1 scores each slot's (move,target)
    candidates in isolation, then DecisionEngine.coordinate picks the best joint
    pair (doubling / overkill / gratuitous-Protect / fake-out / switch-collision
    handled jointly) — so these decisions match actual in-game play.
    """
    s = _make_state(our_a, our_b, opp_a, opp_b, mega)
    chosen, _ = _ENGINE.coordinate(s)
    return chosen[0], chosen[1]


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
    """Opposing Aerodactyl OHKOs our Sneasler and outspeeds it, but our Mega
    Aerodactyl is faster and removes it first — so Sneasler should NOT cower
    behind Protect, because the threat is (very likely) gone before it can act.
    (It may attack or pivot; the point is it doesn't Protect.)

    The partner here is Farigiraf (not a Fake Out user), isolating the
    'neutralized threat' principle.  (With a Fake Out lead like Incineroar the
    joint pass now legitimately prefers the safe double-Protect — the remover
    itself could be Fake-Out-flinched — which is why the old Incineroar board no
    longer asserts this; the principle itself is still guarded here and by
    test_opp_neutralized_before_acting_detects_faster_ally_ko.)"""
    best_a, best_b = _run("Aerodactyl", "Sneasler", "Farigiraf", "Aerodactyl", "Aerodactyl")
    # Aero removes the opposing Aerodactyl (slot 1); Sneasler does not Protect.
    assert best_a.target_slot == 1
    assert best_b.move_name not in _PROTECT_MOVES


def test_opp_neutralized_before_acting_detects_faster_ally_ko():
    """True when a faster ally guarantees an OHKO on the threat; False otherwise."""
    # Our Sneasler outspeeds opposing Kingambit and guaranteed-OHKOs it (Close Combat).
    # The item is pinned to a revealed non-berry: an *unrevealed* Kingambit is
    # assumed to hold Chople Berry (51.9% usage), which halves Close Combat and
    # correctly suppresses the guaranteed-OHKO fact (0.7.6 item inference).
    s = _make_state("Aerodactyl", "Sneasler", "Incineroar", "Kingambit", "Aerodactyl")
    s.opp_actives[1].item = "Black Glasses"
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
    # This guard tests the doom-gate mechanic via a slow, OHKO'd Garchomp.  Since
    # 0.8.0 the team runs a Choice Scarf Garchomp (211 spe) that OUTSPEEDS
    # Weavile — which would invalidate the scenario — so we pin a non-Scarf item
    # here to keep Garchomp slow and exercise the mechanic as intended.
    s.my_actives[1].item = "Soft Sand"
    assert _ko_before_acting(s, 1) is True          # Garchomp dies before acting
    assert _ko_before_acting(s, 0) is False         # Venusaur is not guaranteed-OHKO'd
    _best_a, best_b = _run("Venusaur", "Garchomp", "Weavile", "Alakazam", "Venusaur")
    assert best_b.move_name not in {"Stomping Tantrum", "Dragon Claw", "Poison Jab"}  # doomed → no wasted attack


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


def test_ability_type_immunity_zeroes_damage():
    """Ability-based immunities (Levitate→Ground, Dry Skin→Water) zero the move
    so the engine never picks it into an immune target."""
    from damage import outgoing_damage
    v = find_member("Venusaur"); vs = v.mega_stats or v.stats
    ep = outgoing_damage("Venusaur", vs, ["Earth Power"], "Chimecho",
                         our_ability=v.ability, our_item=v.item, opp_ability="Levitate")[0]
    assert ep.damage_avg == 0 and ep.effectiveness == 0   # Levitate → Ground immune
    b = find_member("Basculegion")
    wc = outgoing_damage("Basculegion", b.stats, ["Wave Crash"], "Heliolisk",
                         our_ability=b.ability, our_item=b.item, opp_ability="Dry Skin")[0]
    assert wc.damage_avg == 0                              # Dry Skin → Water immune


def test_opponent_screen_reduces_outgoing_damage():
    """An opponent's Aurora Veil cuts our damage to 2/3 (doubles); crits bypass
    screens, and Light Screen doesn't touch physical damage."""
    from damage import outgoing_damage, screen_modifier
    b = find_member("Basculegion")
    plain = outgoing_damage("Basculegion", b.stats, ["Wave Crash"], "Garchomp",
                            our_ability=b.ability, our_item=b.item)[0]
    veil  = outgoing_damage("Basculegion", b.stats, ["Wave Crash"], "Garchomp",
                            our_ability=b.ability, our_item=b.item,
                            opp_screens={"auroraveil"})[0]
    assert veil.damage_avg == pytest.approx(plain.damage_avg * 2 / 3, rel=0.02)
    assert screen_modifier("Special", {"auroraveil"}, crit=True) == 1.0   # crit bypasses
    assert screen_modifier("Physical", {"lightscreen"}) == 1.0            # wrong category


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
    ("Incineroar", "Sneasler", "Dual Wingbeat → Sneasler", 28.48, "Switch → Basculegion", 6.78),
    ("Incineroar", "Whimsicott", "Dual Wingbeat → Whimsicott", 37.78, "Switch → Kingambit", 3.20),
    ("Incineroar", "Garchomp", "Ice Fang → Garchomp", 3.86, "Switch → Basculegion", 6.10),
    ("Incineroar", "Farigiraf", "Rock Tomb → Incineroar", 4.91, "Switch → Basculegion", 6.03),
    ("Incineroar", "Kingambit", "Protect → ?", 5.00, "Protect → ?", 5.00),
    ("Incineroar", "Aerodactyl", "Rock Tomb → Aerodactyl", 4.74, "Switch → Basculegion", 9.44),
    ("Farigiraf", "Sneasler", "Dual Wingbeat → Sneasler", 56.96, "Sludge Bomb → Farigiraf", 3.91),
    ("Farigiraf", "Garchomp", "Ice Fang → Garchomp", 15.44, "Sludge Bomb → Farigiraf", 3.91),
    ("Whimsicott", "Garchomp", "Dual Wingbeat → Whimsicott", 75.56, "Giga Drain → Garchomp", 2.00),
    ("Whimsicott", "Kingambit", "Dual Wingbeat → Whimsicott", 75.56, "Earth Power → Kingambit", 3.42),
    ("Sneasler", "Garchomp", "Dual Wingbeat → Sneasler", 28.48, "Switch → Basculegion", 1.70),
    ("Sneasler", "Kingambit", "Dual Wingbeat → Sneasler", 28.48, "Earth Power → Kingambit", 2.28),
    ("Aerodactyl", "Garchomp", "Rock Tomb → Aerodactyl", 9.48, "Switch → Basculegion", 2.36),
    ("Lopunny", "Garchomp", "Dual Wingbeat → Lopunny", 16.25, "Giga Drain → Garchomp", 1.33),
    ("Weavile", "Garchomp", "Rock Tomb → Weavile", 3.35, "Switch → Kingambit", 1.67),
    ("Talonflame", "Garchomp", "Rock Tomb → Talonflame", 84.58, "Switch → Basculegion", 8.57),
    ("Charizard", "Incineroar", "Rock Tomb → Charizard", 26.31, "Protect → ?", 7.50),
    ("Rotom-Wash", "Garchomp", "Ice Fang → Garchomp", 7.72, "Giga Drain → Rotom-Wash", 2.71),
    ("Glimmora", "Incineroar", "Protect → ?", 7.50, "Earth Power → Glimmora", 11.97),
    ("Pelipper", "Dragonite", "Rock Tomb → Pelipper", 10.57, "Switch → Basculegion", 3.35),
], ids=[f"1.{i}" for i in range(1, 21)])
def test_section1(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Aerodactyl", "Venusaur", opp_a, opp_b, "Aerodactyl")
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)


# ==============================================================================
# Section 2 — Aerodactyl [A] + Venusaur [B]  (mega: Venusaur)
# ==============================================================================

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Dual Wingbeat → Sneasler", 18.27, "Earth Power → Incineroar", 2.10),
    ("Incineroar", "Whimsicott", "Dual Wingbeat → Whimsicott", 24.35, "Earth Power → Incineroar", 3.15),
    ("Incineroar", "Garchomp", "Ice Fang → Garchomp", 3.37, "Earth Power → Incineroar", 2.10),
    ("Incineroar", "Farigiraf", "Rock Tomb → Incineroar", 4.33, "Sludge Bomb → Farigiraf", 6.55),
    ("Incineroar", "Kingambit", "Protect → ?", 5.00, "Protect → ?", 2.00),
    ("Incineroar", "Aerodactyl", "Rock Tomb → Aerodactyl", 4.04, "Earth Power → Incineroar", 3.15),
    ("Farigiraf", "Sneasler", "Dual Wingbeat → Sneasler", 36.54, "Sludge Bomb → Farigiraf", 4.37),
    ("Farigiraf", "Garchomp", "Ice Fang → Garchomp", 13.48, "Sludge Bomb → Farigiraf", 4.37),
    ("Whimsicott", "Garchomp", "Dual Wingbeat → Whimsicott", 48.69, "Giga Drain → Garchomp", 2.24),
    ("Whimsicott", "Kingambit", "Dual Wingbeat → Whimsicott", 48.69, "Earth Power → Kingambit", 3.89),
    ("Sneasler", "Garchomp", "Dual Wingbeat → Sneasler", 18.27, "Switch → Basculegion", 1.60),
    ("Sneasler", "Kingambit", "Dual Wingbeat → Sneasler", 18.27, "Earth Power → Kingambit", 2.60),
    ("Aerodactyl", "Garchomp", "Ice Fang → Garchomp", 7.58, "Giga Drain → Aerodactyl", 2.74),
    ("Lopunny", "Garchomp", "Ice Fang → Garchomp", 2.53, "Sludge Bomb → Lopunny", 1.91),
    ("Weavile", "Garchomp", "Switch → Kingambit", 5.41, "Protect → ?", 2.00),
    ("Talonflame", "Garchomp", "Rock Tomb → Talonflame", 71.42, "Giga Drain → Garchomp", 2.24),
    ("Charizard", "Incineroar", "Rock Tomb → Charizard", 22.55, "Earth Power → Incineroar", 4.21),
    ("Rotom-Wash", "Garchomp", "Ice Fang → Garchomp", 6.74, "Giga Drain → Rotom-Wash", 3.05),
    ("Glimmora", "Incineroar", "Switch → Garchomp", 7.67, "Earth Power → Glimmora", 13.80),
    ("Pelipper", "Dragonite", "Rock Tomb → Pelipper", 9.16, "Switch → Kingambit", 3.20),
], ids=[f"2.{i}" for i in range(1, 21)])
def test_section2(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Aerodactyl", "Venusaur", opp_a, opp_b, "Venusaur")
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)


# ==============================================================================
# Section 3 — Garchomp [A]   + Kingambit [B]  (no mega)
# ==============================================================================

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Stomping Tantrum → Sneasler", 28.48, "Low Kick → Incineroar", 1.82),
    ("Incineroar", "Whimsicott", "Poison Jab → Whimsicott", 10.53, "Iron Head → Whimsicott", 3.38),
    ("Incineroar", "Garchomp", "Dragon Claw → Garchomp", 3.79, "Low Kick → Incineroar", 1.82),
    ("Incineroar", "Farigiraf", "Stomping Tantrum → Incineroar", 6.26, "Kowtow Cleave → Farigiraf", 8.25),
    ("Incineroar", "Kingambit", "Stomping Tantrum → Incineroar", 3.13, "Low Kick → Kingambit", 2.56),
    ("Incineroar", "Aerodactyl", "Stomping Tantrum → Incineroar", 4.69, "Iron Head → Aerodactyl", 6.55),
    ("Farigiraf", "Sneasler", "Stomping Tantrum → Sneasler", 56.96, "Kowtow Cleave → Farigiraf", 8.25),
    ("Farigiraf", "Garchomp", "Dragon Claw → Garchomp", 15.16, "Kowtow Cleave → Farigiraf", 8.25),
    ("Whimsicott", "Garchomp", "Poison Jab → Whimsicott", 21.07, "Iron Head → Whimsicott", 3.38),
    ("Whimsicott", "Kingambit", "Poison Jab → Whimsicott", 21.07, "Iron Head → Whimsicott", 4.51),
    ("Sneasler", "Garchomp", "Stomping Tantrum → Sneasler", 28.48, "Kowtow Cleave → Garchomp", 1.71),
    ("Sneasler", "Kingambit", "Stomping Tantrum → Sneasler", 28.48, "Low Kick → Kingambit", 2.56),
    ("Aerodactyl", "Garchomp", "Dragon Claw → Garchomp", 11.37, "Iron Head → Aerodactyl", 6.55),
    ("Lopunny", "Garchomp", "Dragon Claw → Garchomp", 3.79, "Switch → Basculegion", 4.33),
    ("Weavile", "Garchomp", "Dragon Claw → Garchomp", 3.79, "Low Kick → Weavile", 4.67),
    ("Talonflame", "Garchomp", "Rock Tomb → Talonflame", 82.69, "Kowtow Cleave → Garchomp", 2.57),
    ("Charizard", "Incineroar", "Rock Tomb → Charizard", 25.48, "Protect → ?", 7.50),
    ("Rotom-Wash", "Garchomp", "Dragon Claw → Garchomp", 7.58, "Kowtow Cleave → Rotom-Wash", 2.15),
    ("Glimmora", "Incineroar", "Stomping Tantrum → Glimmora", 35.28, "Low Kick → Incineroar", 1.82),
    ("Pelipper", "Dragonite", "Dragon Claw → Dragonite", 6.18, "Kowtow Cleave → Pelipper", 3.14),
], ids=[f"3.{i}" for i in range(1, 21)])
def test_section3(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Garchomp", "Kingambit", opp_a, opp_b, None)
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)


# ==============================================================================
# Section 4 — Aerodactyl [A] + Sneasler [B]  (mega: Aerodactyl)
# ==============================================================================

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Dual Wingbeat → Sneasler", 28.48, "Close Combat → Incineroar", 3.77),
    ("Incineroar", "Whimsicott", "Dual Wingbeat → Whimsicott", 37.78, "Close Combat → Incineroar", 5.65),
    ("Incineroar", "Garchomp", "Ice Fang → Garchomp", 3.86, "Switch → Basculegion", 4.37),
    ("Incineroar", "Farigiraf", "Dual Wingbeat → Farigiraf", 4.11, "Close Combat → Incineroar", 11.31),
    ("Incineroar", "Kingambit", "Rock Tomb → Incineroar", 2.46, "Close Combat → Kingambit", 4.97),
    ("Incineroar", "Aerodactyl", "Rock Tomb → Aerodactyl", 4.74, "Close Combat → Incineroar", 5.65),
    ("Farigiraf", "Sneasler", "Dual Wingbeat → Sneasler", 56.96, "Switch → Basculegion", 7.32),
    ("Farigiraf", "Garchomp", "Ice Fang → Garchomp", 15.44, "Close Combat → Farigiraf", 4.85),
    ("Whimsicott", "Garchomp", "Dual Wingbeat → Whimsicott", 75.56, "Switch → Venusaur", 4.67),
    ("Whimsicott", "Kingambit", "Dual Wingbeat → Whimsicott", 75.56, "Close Combat → Kingambit", 4.97),
    ("Sneasler", "Garchomp", "Dual Wingbeat → Sneasler", 28.48, "Switch → Basculegion", 7.34),
    ("Sneasler", "Kingambit", "Dual Wingbeat → Sneasler", 28.48, "Close Combat → Kingambit", 3.32),
    ("Aerodactyl", "Garchomp", "Rock Tomb → Aerodactyl", 9.48, "Switch → Basculegion", 8.20),
    ("Lopunny", "Garchomp", "Ice Fang → Garchomp", 2.90, "Close Combat → Lopunny", 19.71),
    ("Weavile", "Garchomp", "Ice Fang → Garchomp", 2.90, "Close Combat → Weavile", 10.09),
    ("Talonflame", "Garchomp", "Rock Tomb → Talonflame", 84.58, "Protect → ?", 7.50),
    ("Charizard", "Incineroar", "Rock Tomb → Charizard", 35.08, "Close Combat → Incineroar", 5.65),
    ("Rotom-Wash", "Garchomp", "Ice Fang → Garchomp", 7.72, "Switch → Garchomp", 3.90),
    ("Glimmora", "Incineroar", "Switch → Garchomp", 7.41, "Close Combat → Incineroar", 2.83),
    ("Pelipper", "Dragonite", "Rock Tomb → Pelipper", 10.57, "Switch → Basculegion", 4.00),
], ids=[f"4.{i}" for i in range(1, 21)])
def test_section4(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Aerodactyl", "Sneasler", opp_a, opp_b, "Aerodactyl")
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)


# ==============================================================================
# Section 5 — Garchomp [A]   + Venusaur [B]  (mega: Venusaur)
# ==============================================================================

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Stomping Tantrum → Sneasler", 28.48, "Earth Power → Incineroar", 2.10),
    ("Incineroar", "Whimsicott", "Poison Jab → Whimsicott", 10.53, "Sludge Bomb → Whimsicott", 9.15),
    ("Incineroar", "Garchomp", "Dragon Claw → Garchomp", 3.79, "Earth Power → Incineroar", 2.10),
    ("Incineroar", "Farigiraf", "Stomping Tantrum → Incineroar", 6.26, "Sludge Bomb → Farigiraf", 6.55),
    ("Incineroar", "Kingambit", "Stomping Tantrum → Incineroar", 3.13, "Earth Power → Kingambit", 3.89),
    ("Incineroar", "Aerodactyl", "Stomping Tantrum → Incineroar", 4.69, "Giga Drain → Aerodactyl", 3.66),
    ("Farigiraf", "Sneasler", "Stomping Tantrum → Sneasler", 56.96, "Sludge Bomb → Farigiraf", 4.37),
    ("Farigiraf", "Garchomp", "Dragon Claw → Garchomp", 15.16, "Sludge Bomb → Farigiraf", 4.37),
    ("Whimsicott", "Garchomp", "Poison Jab → Whimsicott", 21.07, "Sludge Bomb → Whimsicott", 6.86),
    ("Whimsicott", "Kingambit", "Poison Jab → Whimsicott", 21.07, "Sludge Bomb → Whimsicott", 9.15),
    ("Sneasler", "Garchomp", "Stomping Tantrum → Sneasler", 28.48, "Switch → Basculegion", 1.60),
    ("Sneasler", "Kingambit", "Stomping Tantrum → Sneasler", 28.48, "Earth Power → Kingambit", 2.60),
    ("Aerodactyl", "Garchomp", "Dragon Claw → Garchomp", 11.37, "Giga Drain → Aerodactyl", 2.74),
    ("Lopunny", "Garchomp", "Dragon Claw → Garchomp", 3.79, "Sludge Bomb → Lopunny", 1.91),
    ("Weavile", "Garchomp", "Switch → Kingambit", 5.43, "Protect → ?", 2.00),
    ("Talonflame", "Garchomp", "Rock Tomb → Talonflame", 82.69, "Giga Drain → Garchomp", 2.24),
    ("Charizard", "Incineroar", "Rock Tomb → Charizard", 25.48, "Earth Power → Incineroar", 3.15),
    ("Rotom-Wash", "Garchomp", "Dragon Claw → Garchomp", 7.58, "Giga Drain → Rotom-Wash", 3.05),
    ("Glimmora", "Incineroar", "Stomping Tantrum → Incineroar", 3.13, "Earth Power → Glimmora", 27.59),
    ("Pelipper", "Dragonite", "Rock Tomb → Pelipper", 8.02, "Switch → Kingambit", 3.20),
], ids=[f"5.{i}" for i in range(1, 21)])
def test_section5(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Garchomp", "Venusaur", opp_a, opp_b, "Venusaur")
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)


# ==============================================================================
# Section 6 — Sneasler [A]   + Kingambit [B]  (no mega)
# ==============================================================================

@pytest.mark.parametrize("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b", [
    ("Incineroar", "Sneasler", "Close Combat → Incineroar", 2.83, "Switch → Basculegion", 6.48),
    ("Incineroar", "Whimsicott", "Dire Claw → Whimsicott", 8.96, "Iron Head → Whimsicott", 3.38),
    ("Incineroar", "Garchomp", "Protect → ?", 5.00, "Protect → ?", 2.00),
    ("Incineroar", "Farigiraf", "Close Combat → Incineroar", 7.54, "Kowtow Cleave → Farigiraf", 8.25),
    ("Incineroar", "Kingambit", "Close Combat → Incineroar", 3.77, "Low Kick → Kingambit", 2.56),
    ("Incineroar", "Aerodactyl", "Close Combat → Incineroar", 4.24, "Iron Head → Aerodactyl", 6.55),
    ("Farigiraf", "Sneasler", "Switch → Basculegion", 7.32, "Protect → ?", 5.00),
    ("Farigiraf", "Garchomp", "Close Combat → Garchomp", 7.22, "Kowtow Cleave → Farigiraf", 8.25),
    ("Whimsicott", "Garchomp", "Dire Claw → Whimsicott", 11.95, "Kowtow Cleave → Garchomp", 2.57),
    ("Whimsicott", "Kingambit", "Dire Claw → Whimsicott", 17.93, "Iron Head → Whimsicott", 4.51),
    ("Sneasler", "Garchomp", "Switch → Garchomp", 6.21, "Switch → Basculegion", 6.48),
    ("Sneasler", "Kingambit", "Close Combat → Kingambit", 2.49, "Switch → Garchomp", 5.35),
    ("Aerodactyl", "Garchomp", "Switch → Basculegion", 8.20, "Iron Head → Aerodactyl", 6.55),
    ("Lopunny", "Garchomp", "Close Combat → Lopunny", 13.14, "Protect → ?", 7.50),
    ("Weavile", "Garchomp", "Close Combat → Weavile", 6.72, "Low Kick → Weavile", 1.87),
    ("Talonflame", "Garchomp", "Switch → Basculegion", 7.02, "Kowtow Cleave → Talonflame", 3.59),
    ("Charizard", "Incineroar", "Protect → ?", 5.00, "Switch → Aerodactyl", 5.95),
    ("Rotom-Wash", "Garchomp", "Switch → Garchomp", 3.90, "Kowtow Cleave → Rotom-Wash", 2.15),
    ("Glimmora", "Incineroar", "Close Combat → Incineroar", 3.77, "Iron Head → Glimmora", 3.05),
    ("Pelipper", "Dragonite", "Switch → Basculegion", 4.00, "Kowtow Cleave → Pelipper", 3.14),
], ids=[f"6.{i}" for i in range(1, 21)])
def test_section6(opp_a, opp_b, dec_a, wt_a, dec_b, wt_b):
    best_a, best_b = _run("Sneasler", "Kingambit", opp_a, opp_b, None)
    _chk(best_a, dec_a, opp_a, opp_b, wt_a)
    _chk(best_b, dec_b, opp_a, opp_b, wt_b)



