"""
_gen_turn1_summary.py  —  Generate turn1_summary.md
Run: .venv/Scripts/python.exe _gen_turn1_summary.py
"""
from battle import BattleState, Pokemon
from decision.modules import make_engine
from team import find_member
from version import __version__

ALL_TEAM = ["Aerodactyl", "Kingambit", "Sneasler", "Basculegion", "Venusaur", "Garchomp"]

# (slot_a, slot_b, designated_mega)
# designated_mega = None means neither mon on this lead has a mega stone.
# When both lead mons hold mega stones, list the lead twice — once for each
# possible mega selection, since the choice is made at team preview.
OUR_LEADS = [
    ("Aerodactyl",  "Venusaur",  "Aerodactyl"),   # variant 1: Aero mega
    ("Aerodactyl",  "Venusaur",  "Venusaur"),      # variant 2: Venu mega
    ("Garchomp",    "Kingambit", None),
    ("Aerodactyl",  "Sneasler",  "Aerodactyl"),
    ("Garchomp",    "Venusaur",  "Venusaur"),
    ("Sneasler",    "Kingambit", None),
]

# 20 opponent lead pairs — all species legal in Champions format
OPP_LEADS = [
    ("Incineroar",      "Sneasler"),
    ("Incineroar",      "Whimsicott"),
    ("Incineroar",      "Garchomp"),
    ("Incineroar",      "Farigiraf"),
    ("Incineroar",      "Kingambit"),
    ("Incineroar",      "Aerodactyl"),
    ("Farigiraf",       "Sneasler"),
    ("Farigiraf",       "Garchomp"),
    ("Whimsicott",      "Garchomp"),
    ("Whimsicott",      "Kingambit"),
    ("Sneasler",        "Garchomp"),
    ("Sneasler",        "Kingambit"),
    ("Aerodactyl",      "Garchomp"),
    ("Lopunny",         "Garchomp"),
    ("Weavile",         "Garchomp"),
    ("Talonflame",      "Garchomp"),
    ("Charizard",       "Incineroar"),
    ("Rotom-Wash",      "Garchomp"),
    ("Glimmora",        "Incineroar"),
    ("Pelipper",        "Dragonite"),
]

engine = make_engine()


def make_our_mon(sp):
    tm = find_member(sp)
    hp = tm.stats["hp"]
    return Pokemon(
        ident=f"p1: {sp}", species=sp, hp=hp, max_hp=hp,
        ability=tm.ability, item=tm.item, moves=list(tm.moves),
    )


def make_opp_mon(sp):
    # hp_is_percentage=True + hp=100 → engine uses typical-spread HP for all calcs
    return Pokemon(
        ident=f"p2: {sp}", species=sp,
        hp=100, max_hp=100, hp_is_percentage=True,
    )


def moves_for(sp):
    tm = find_member(sp)
    return [{"move": m} for m in tm.moves] if tm else []


def run_lead(our_a, our_b, opp_a, opp_b, designated_mega):
    bench = [s for s in ALL_TEAM if s not in (our_a, our_b)]

    s = BattleState(battle_id="test", my_side="p1")
    s.my_actives = [make_our_mon(our_a), make_our_mon(our_b)]
    s.my_team = list(s.my_actives)
    s.opp_actives = [make_opp_mon(opp_a), make_opp_mon(opp_b)]
    s.available_switches = [make_our_mon(b) for b in bench]
    s.moves_per_slot = [moves_for(our_a), moves_for(our_b)]
    s.my_last_moves = ["", ""]
    s.opp_last_moves = ["", ""]
    s.my_slot_decisions = [None, None]
    s.opp_tailwind = False
    s.opp_tailwind_turns_left = 0
    s.trick_room = False
    s.trick_room_turns_left = 0
    s.weather = None
    s.my_tailwind = False
    s.my_disabled_moves = [None, None]
    s.my_encored_moves = [None, None]
    s.designated_mega = designated_mega

    # Mirror main.py's turn flow exactly: phase-1 scores each slot's (move,target)
    # candidates in isolation, then coordinate() picks the best joint pair (the
    # only place doubling / overkill / gratuitous-Protect / fake-out effects act).
    chosen, _ = engine.coordinate(s)
    best_a = chosen.get(0)
    best_b = chosen.get(1)

    def fmt(act, opp_a, opp_b):
        if act.move_name:
            if act.target_slot == 0:
                tgt = opp_a
            elif act.target_slot == 1:
                tgt = opp_b
            else:
                tgt = "?"
            return f"{act.move_name} → {tgt} `{act.weight:.2f}`"
        else:
            return f"Switch → {act.switch_target} `{act.weight:.2f}`"

    return fmt(best_a, opp_a, opp_b), fmt(best_b, opp_a, opp_b)


lines = []
lines.append("# Turn 1 First-Turn Decision Summary")
lines.append("")
lines.append(f"Engine v{__version__} | Turn 1 opening, 100% HP, no field effects, no revealed moves")
lines.append("")
lines.append("> **Joint selection.** Each slot's `(move, target)` candidates are scored")
lines.append("> independently (phase 1); `DecisionEngine.coordinate` then picks the")
lines.append("> highest-value **pair** of actions (phase 2).")
lines.append("> All opponent HP treated as percentage (engine uses typical-spread stats for damage calcs).")
lines.append("> Mega evolution is resolved at turn start — the designated mega uses mega stats/ability.")
lines.append(">")
lines.append("> The phase-2 **joint adjusters** are the only cross-slot effects: *doubling* "
             "(both attack the same target → ×0.40–0.70, or ×0.05 overkill when one slot "
             "already confirms the OHKO, so the pair that spreads wins); *coordination* "
             "(a gratuitous lone Protect beside an attacking partner → ×0.5, favouring "
             "double-attack); *fake-out* (the slot absorbing a Fake Out frees its partner); "
             "and *switch-collision* (both switching to the same mon → ×0). These cells "
             "reflect actual in-game behaviour.")
lines.append("")

for section, (our_a, our_b, designated_mega) in enumerate(OUR_LEADS, start=1):
    bench_str = ", ".join(s for s in ALL_TEAM if s not in (our_a, our_b))
    mega_label = f" *(mega: {designated_mega})*" if designated_mega else ""
    lines.append("---")
    lines.append("")
    lines.append(f"## {section}. My Lead: **{our_a}** [A]  +  **{our_b}** [B]{mega_label}")
    lines.append(f"Bench: {bench_str}")
    lines.append("")
    lines.append(f"| # | Opp [A] | Opp [B] | {our_a} [A] | {our_b} [B] |")
    lines.append("|---|---|---|---|---|")
    for row, (opp_a, opp_b) in enumerate(OPP_LEADS, start=1):
        try:
            dec_a, dec_b = run_lead(our_a, our_b, opp_a, opp_b, designated_mega)
        except Exception as e:
            dec_a = f"ERROR: {e}"
            dec_b = "—"
        lines.append(f"| {section}.{row} | {opp_a} | {opp_b} | {dec_a} | {dec_b} |")
    lines.append("")

with open("turn1_summary.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Written turn1_summary.md")
