"""tools/replay_turn.py — re-run the CURRENT engine on a board from a battle log.

The "would the fix have changed this decision?" tool: rebuilds the decision-time
board of one logged turn and scores it with the engine as it exists in the
working tree — phase-1 ranked actions per slot plus the coordinate() pair —
side by side with what the game actually chose.

    .venv\\Scripts\\python.exe tools/replay_turn.py 2640366837 7

Reconstruction fidelity (what the log does/doesn't carry):
  * our side: species/HP/boosts/status/item-consumed from the turn snapshot;
    stats/items/moves from the team file the game was played with (auto-selected
    from the log's team/team_version).
  * opponent: species/HP/boosts/status at percentage HP (typical-spread stats).
  * field: weather / Trick Room / Tailwind flags. Turns-left aren't logged —
    both are set to 2 so the "last turn / 3 turns left" Protect row can't fire.
  * last moves (Protect recency / consecutive-Protect) are derived from the
    previous turn's dec/ev when available.
  * NOT reconstructable: opponent item/choice evidence (consumed berries,
    inferred scarves), Disable/Encore, revealed-move history. The engine falls
    back to its usage-stats priors, which may differ from the live game.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.inspect_battle import load_log  # noqa: E402
import team as team_mod                    # noqa: E402
from team import find_member               # noqa: E402
from battle import BattleState, Pokemon    # noqa: E402
from data import base_forme                # noqa: E402
from decision.modules import make_engine   # noqa: E402

_ZERO_BOOSTS = {"atk": 0, "def": 0, "spa": 0, "spd": 0,
                "spe": 0, "accuracy": 0, "evasion": 0}


def _our_mon(m: dict) -> Pokemon:
    sp = m["s"]
    tm = find_member(sp) or find_member(base_forme(sp))
    if tm is None:
        raise SystemExit(f"find_member failed for our '{sp}' — wrong team selected?")
    max_hp = tm.stats["hp"]
    frac = m.get("hp", 1.0)
    hp = 0 if frac <= 0 else max(1, round(frac * max_hp))
    ic = bool(m.get("ic"))
    return Pokemon(
        ident=f"p1: {base_forme(sp)}", species=sp,
        hp=hp, max_hp=max_hp, fainted=(hp <= 0),
        ability=tm.ability, item=(None if ic else tm.item), item_consumed=ic,
        moves=list(tm.moves), status=m.get("sts"),
        boosts={**_ZERO_BOOSTS, **(m.get("b") or {})},
    )


def _opp_mon(m: dict) -> Pokemon:
    frac = m.get("hp", 1.0)
    return Pokemon(
        ident=f"p2: {m['s']}", species=m["s"],
        hp=max(1, round(frac * 100)) if frac > 0 else 0, max_hp=100,
        hp_is_percentage=True, fainted=(frac <= 0), status=m.get("sts"),
        boosts={**_ZERO_BOOSTS, **(m.get("b") or {})},
    )


def _last_moves(prev: dict | None, turn: dict) -> tuple[list[str], list[str]]:
    """(my_last_moves, opp_last_moves) per slot, derived from the previous turn."""
    my = ["", ""]
    opp = ["", ""]
    if not prev:
        return my, opp
    for dec in prev.get("dec", []):
        sl, ch = dec.get("sl"), dec.get("ch", "")
        if sl in (0, 1) and ch and not ch.startswith("Switch"):
            my[sl] = ch
    # map prev-turn opp move events onto the CURRENT turn's opp slots by species
    slot_of = {base_forme(o["s"]): i
               for i, o in enumerate(turn.get("opp", [])) if o}
    for e in prev.get("ev", []):
        if e.get("sd") == "opp" and e.get("mv"):
            sl = slot_of.get(base_forme(e.get("a", "")))
            if sl is not None:
                opp[sl] = e["mv"]
    return my, opp


def build_state(d: dict, turn: dict, prev: dict | None) -> BattleState:
    s = BattleState(battle_id=d.get("id", "replay"), my_side="p1")
    s.turn = turn.get("n", 1)
    s.my_actives = [_our_mon(m) for m in turn.get("my", []) if m]
    s.opp_actives = [_opp_mon(m) for m in turn.get("opp", []) if m]

    active_bases = {base_forme(p.species) for p in s.my_actives}
    bench = [m for m in turn.get("team", [])
             if m and base_forme(m["s"]) not in active_bases]
    s.available_switches = [_our_mon(m) for m in bench if m.get("hp", 0) > 0]
    s.my_team = list(s.my_actives) + [_our_mon(m) for m in bench]

    s.moves_per_slot = [[{"move": mv} for mv in p.moves] if not p.fainted else []
                        for p in s.my_actives]
    s.my_slot_decisions = [None, None]
    s.my_disabled_moves = [None, None]
    s.my_encored_moves = [None, None]

    s.weather = turn.get("w")
    s.trick_room = bool(turn.get("tr"))
    s.trick_room_turns_left = 2 if s.trick_room else 0   # not logged; avoid ==1/3 rows
    tw = turn.get("tw") or {}
    s.my_tailwind = bool(tw.get("us"))
    s.opp_tailwind = bool(tw.get("opp"))
    s.opp_tailwind_turns_left = 2 if s.opp_tailwind else 0

    s.my_last_moves, s.opp_last_moves = _last_moves(prev, turn)
    s.designated_mega = (d.get("preview") or {}).get("mega")
    return s


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Replay one logged turn through the current engine.")
    ap.add_argument("fragment", help="battle-id fragment")
    ap.add_argument("turn", type=int, help="turn number to replay")
    ap.add_argument("--top", type=int, default=5, help="ranked actions shown per slot")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    d, path = load_log(args.fragment)
    turns = d.get("turns", [])
    turn = next((t for t in turns if t.get("n") == args.turn), None)
    if turn is None:
        raise SystemExit(f"turn {args.turn} not in log (has {[t.get('n') for t in turns]})")
    prev = next((t for t in turns if t.get("n") == args.turn - 1), None)

    spec = f"{d.get('team')}@{d.get('team_version')}" if d.get("team") else None
    try:
        team_mod.set_active_team(spec)
    except Exception as e:
        print(f"WARNING: couldn't select team '{spec}' ({e}); using default")
        team_mod.set_active_team(None)
    team_mod.get_team(reload=True)

    state = build_state(d, turn, prev)
    engine = make_engine()
    chosen, ranked = engine.coordinate(state)

    print(f"replay {os.path.basename(path)}  T{args.turn}  (log engine v{d.get('v')} "
          f"-> current working tree)")
    print(f"team: {spec}  mega: {state.designated_mega}")
    my = ", ".join(f"{p.species} {round(p.hp_fraction*100)}%" for p in state.my_actives)
    op = ", ".join(f"{p.species} {round(p.hp_fraction*100)}%" + ("†" if p.fainted else "")
                   for p in state.opp_actives)
    print(f"board: my {my}  |  opp {op}")
    print(f"field: weather={state.weather} TR={state.trick_room} "
          f"TW us/opp={state.my_tailwind}/{state.opp_tailwind}")
    print(f"last moves: my={state.my_last_moves} opp={state.opp_last_moves}")
    print("caveats: TR/TW turns-left assumed 2; opp item/choice evidence + "
          "Disable/Encore not in log (usage priors used)\n")

    def fmt(a):
        if a.switch_target:
            return f"Switch -> {a.switch_target}"
        tgt = ""
        if a.target_slot is not None and a.target_slot < len(state.opp_actives):
            tgt = f" -> {state.opp_actives[a.target_slot].species}"
        return f"{a.move_name}{tgt}"

    for sl in sorted(ranked):
        p = state.my_actives[sl] if sl < len(state.my_actives) else None
        print(f"slot {sl} ({p.species if p else '?'}):")
        for i, a in enumerate(ranked[sl][:args.top], 1):
            print(f"  {i}. {fmt(a)}  w={a.weight:.2f}")
            if i <= 3:
                for r in a.reasons:
                    print(f"        {r}")

    print("\ncoordinate() ->", "  |  ".join(
        f"s{sl}: {fmt(a)} (w={a.weight:.2f})" for sl, a in sorted(chosen.items())))
    game = ["?"] * 2
    for dec in turn.get("dec", []):
        sl = dec.get("sl")
        if sl in (0, 1):
            act = next((a for a in dec.get("acts", []) if a.get("lb") == dec.get("ch")), None)
            tgt = ""
            if act and act.get("ts") is not None:
                olist = turn.get("opp", [])
                if act["ts"] < len(olist) and olist[act["ts"]]:
                    tgt = f" -> {olist[act['ts']]['s']}"
            game[sl] = f"s{sl}: {dec.get('ch')}{tgt}"
    print("game chose    ->", "  |  ".join(g for g in game if g != "?"))


if __name__ == "__main__":
    main()
