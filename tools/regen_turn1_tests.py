"""tools/regen_turn1_tests.py — regenerate the 6 expectation tables in
tests/test_turn1_decisions.py from the CURRENT engine output, in place.

Only the 20-row parametrize data blocks are rewritten; everything else (imports,
helpers, section test bodies, the speed-regression tests, the `ids=` lists) is
left untouched.

WHEN TO USE: only after an *approved* turn-1 behavior change — the table is the
version-controlled regression reference, so per CLAUDE.md you must have reviewed
and approved the decision diff first.  After running this, run `pytest` to
confirm the engine matches, and spot-check that the new values are actually
correct (don't blind-trust the engine).

Run from anywhere:
    .venv\\Scripts\\python.exe tools/regen_turn1_tests.py
then regenerate the human summary too:
    .venv\\Scripts\\python.exe _gen_turn1_summary.py
"""
import os
import re
import sys

# Allow running as `python tools/regen_turn1_tests.py` from the repo root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from battle import BattleState, Pokemon
from decision.modules import make_engine
from team import find_member

# Lead configs — kept in sync with _gen_turn1_summary.py (which can't be imported
# without triggering its summary generation at import time).
ALL_TEAM = ["Aerodactyl", "Kingambit", "Sneasler", "Basculegion", "Venusaur", "Garchomp"]
OUR_LEADS = [
    ("Aerodactyl", "Venusaur", "Aerodactyl"), ("Aerodactyl", "Venusaur", "Venusaur"),
    ("Garchomp", "Kingambit", None), ("Aerodactyl", "Sneasler", "Aerodactyl"),
    ("Garchomp", "Venusaur", "Venusaur"), ("Sneasler", "Kingambit", None),
]
OPP_LEADS = [
    ("Incineroar", "Sneasler"), ("Incineroar", "Whimsicott"), ("Incineroar", "Garchomp"),
    ("Incineroar", "Farigiraf"), ("Incineroar", "Kingambit"), ("Incineroar", "Aerodactyl"),
    ("Farigiraf", "Sneasler"), ("Farigiraf", "Garchomp"), ("Whimsicott", "Garchomp"),
    ("Whimsicott", "Kingambit"), ("Sneasler", "Garchomp"), ("Sneasler", "Kingambit"),
    ("Aerodactyl", "Garchomp"), ("Lopunny", "Garchomp"), ("Weavile", "Garchomp"),
    ("Talonflame", "Garchomp"), ("Charizard", "Incineroar"), ("Rotom-Wash", "Garchomp"),
    ("Glimmora", "Incineroar"), ("Pelipper", "Dragonite"),
]
ENGINE = make_engine()
ARROW = "→"   # → matches the decision-string separator the test parses on


def _our(sp):
    tm = find_member(sp); hp = tm.stats["hp"]
    return Pokemon(ident=f"p1: {sp}", species=sp, hp=hp, max_hp=hp,
                   ability=tm.ability, item=tm.item, moves=list(tm.moves))


def _opp(sp):
    return Pokemon(ident=f"p2: {sp}", species=sp, hp=100, max_hp=100, hp_is_percentage=True)


def _moves(sp):
    tm = find_member(sp); return [{"move": m} for m in tm.moves] if tm else []


def _state(a, b, oa, ob, mega):
    bench = [s for s in ALL_TEAM if s not in (a, b)]
    s = BattleState(battle_id="test", my_side="p1")
    s.my_actives = [_our(a), _our(b)]; s.my_team = list(s.my_actives)
    s.opp_actives = [_opp(oa), _opp(ob)]
    s.available_switches = [_our(x) for x in bench]
    s.moves_per_slot = [_moves(a), _moves(b)]
    s.my_last_moves = ["", ""]; s.opp_last_moves = ["", ""]; s.my_slot_decisions = [None, None]
    s.opp_tailwind = False; s.opp_tailwind_turns_left = 0
    s.trick_room = False; s.trick_room_turns_left = 0; s.weather = None; s.my_tailwind = False
    s.my_disabled_moves = [None, None]; s.my_encored_moves = [None, None]; s.designated_mega = mega
    return s


def _dec(act, oa, ob):
    if act.move_name:
        if act.move_name == "Protect":
            return f"Protect {ARROW} ?"
        tgt = oa if act.target_slot == 0 else ob if act.target_slot == 1 else "?"
        return f"{act.move_name} {ARROW} {tgt}"
    return f"Switch {ARROW} {act.switch_target}"


def _rows_for(a, b, mega):
    rows = []
    for oa, ob in OPP_LEADS:
        chosen, _ = ENGINE.coordinate(_state(a, b, oa, ob, mega))
        da, db = _dec(chosen[0], oa, ob), _dec(chosen[1], oa, ob)
        rows.append(f'    ("{oa}", "{ob}", "{da}", {chosen[0].weight:.2f}, '
                    f'"{db}", {chosen[1].weight:.2f}),')
    return rows


def main():
    path = os.path.join(os.path.dirname(__file__), "..", "tests", "test_turn1_decisions.py")
    lines = open(path, encoding="utf-8").read().splitlines()
    deco = re.compile(r'@pytest\.mark\.parametrize\("opp_a,opp_b,dec_a,wt_a,dec_b,wt_b"')

    blocks = []   # (first_row_idx, closing_idx) per parametrize table
    i = 0
    while i < len(lines):
        if deco.search(lines[i]):
            j = i + 1
            while not lines[j].lstrip().startswith("]"):   # closing "], ids=[...])"
                j += 1
            blocks.append((i + 1, j))
            i = j
        i += 1
    if len(blocks) != len(OUR_LEADS):
        raise SystemExit(f"expected {len(OUR_LEADS)} tables, found {len(blocks)}")

    out, prev = [], 0
    for sec, (start, end) in enumerate(blocks):
        out.extend(lines[prev:start])
        out.extend(_rows_for(*OUR_LEADS[sec]))
        prev = end
    out.extend(lines[prev:])
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"Rewrote {len(blocks)} tables, {len(OPP_LEADS)} rows each.")


if __name__ == "__main__":
    main()
