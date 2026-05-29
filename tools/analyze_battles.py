"""
tools/analyze_battles.py — Battle data analysis script for WolfeyBot.

Compatible with compact log format v2 (recorder.py 0.3.5+).

Key format differences from v1
-------------------------------
Top-level keys:
  "id"      (was "battle_id")
  "turns"   (was "decisions" — flat list of per-slot entries)

Per-turn entry (new grouping level):
  "n"    turn number
  "w"    weather
  "te"   terrain
  "tr"   trick room (True when active)
  "my"   our actives list — index == slot  [{s, hp, sts?}, ...]
  "opp"  opponent actives — index == slot  [{s, hp, sts?, mv?}, ...]
  "team" full team                          [{s, hp}, ...]
  "dec"  per-slot decisions                 [{sl, ch, acts}, ...]

Per-slot-decision:
  "sl"   slot index (0 or 1)
  "ch"   chosen action label
  "acts" ranked actions (top _MAX_ACTIONS, w > 1.0 or min 3, always chosen)

Per-action:
  "lb"   label
  "w"    weight (float, 2 dp)
  "ts"   target_slot  (omitted if null)
  "sw"   switch_target (omitted if falsy)
  "r"    reasons list  (omitted if empty)

HP is a 0.0–1.0 fraction (was "cur/max" string — parse_hp() is no longer needed).
"""
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Optional

DATA_DIR = Path(r"C:\Users\Sean\PycharmProjects\WolfeyBot\Battle Data\0.5.0")


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_battles() -> list[dict]:
    battles = []
    for p in DATA_DIR.glob("*.json"):
        with open(p, encoding="utf-8") as f:
            battles.append(json.load(f))
    return battles


def is_protect(label: str) -> bool:
    protect_names = {
        "protect", "wide guard", "quick guard", "detect", "mat block",
        "baneful bunker", "spiky shield", "king's shield", "obstruct",
        "silk trap", "burning bulwark", "crafty shield",
    }
    return label.strip().lower() in protect_names


def is_switch(action: dict) -> bool:
    return bool(action.get("sw"))


def get_mon(turn: dict, sl: int) -> dict:
    """Return our-team entry for slot *sl* from *turn*, or {} if missing / null."""
    my = turn.get("my", [])
    if sl < len(my) and my[sl] is not None:
        return my[sl]
    return {}


def all_slot_decisions(battles: list[dict]):
    """Yield (bid, turn_num, dec_entry, turn_entry) for every slot decision."""
    for b in battles:
        bid = b.get("id", "unknown")
        for turn in b.get("turns", []):
            for dec in turn.get("dec", []):
                yield bid, turn.get("n", 0), dec, turn


def decisions_per_turn(battles: list[dict]):
    """Yield (bid, turn_num, [dec_entries], turn_entry)."""
    for b in battles:
        bid = b.get("id", "unknown")
        for turn in b.get("turns", []):
            yield bid, turn.get("n", 0), turn.get("dec", []), turn


def chosen_action(dec: dict) -> Optional[dict]:
    """Return the action entry whose label matches dec['ch'], or None."""
    ch = dec.get("ch", "")
    for a in dec.get("acts", []):
        if a.get("lb") == ch:
            return a
    return None


SEPARATOR = "=" * 70


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    battles = load_battles()
    print(f"Loaded {len(battles)} battles from {DATA_DIR}\n")

    # ── 1. Win/loss record ────────────────────────────────────────────────────
    print(SEPARATOR)
    print("SECTION 1: WIN/LOSS RECORD")
    print(SEPARATOR)
    total    = len(battles)
    wins     = sum(1 for b in battles if b.get("outcome") == "win")
    losses   = sum(1 for b in battles if b.get("outcome") == "loss")
    other    = total - wins - losses
    win_rate = wins / total * 100 if total else 0
    print(f"  Total battles : {total}")
    print(f"  Wins          : {wins}")
    print(f"  Losses        : {losses}")
    if other:
        print(f"  Other/Unknown : {other}")
    print(f"  Win rate      : {win_rate:.1f}%")
    print()

    # ── 2. Turn count distribution ────────────────────────────────────────────
    print(SEPARATOR)
    print("SECTION 2: TURN COUNT DISTRIBUTION")
    print(SEPARATOR)
    turn_counts       = []
    high_turn_battles = []
    for b in battles:
        turns = b.get("turns", [])
        n = max((t.get("n", 0) for t in turns), default=0)
        turn_counts.append(n)
        bid = b.get("id", "unknown")
        if n >= 10:
            high_turn_battles.append((bid, n, b.get("outcome", "?")))
    if turn_counts:
        print(f"  Min turns    : {min(turn_counts)}")
        print(f"  Max turns    : {max(turn_counts)}")
        print(f"  Median turns : {statistics.median(turn_counts):.1f}")
        print(f"  Mean turns   : {statistics.mean(turn_counts):.2f}")
    print(f"\n  Battles with >= 10 turns ({len(high_turn_battles)}):")
    if high_turn_battles:
        for bid, n, outcome in sorted(high_turn_battles, key=lambda x: -x[1]):
            print(f"    {bid}  turns={n}  outcome={outcome}")
    else:
        print("    (none)")
    print()

    # ── 3. Fake Out module firing rate ────────────────────────────────────────
    print(SEPARATOR)
    print("SECTION 3: FAKE OUT MODULE FIRING RATE")
    print(SEPARATOR)
    fake_out_count   = 0
    fake_out_battles = set()
    protect_top      = 0
    non_protect_top  = 0
    for bid, turn_num, dec, turn in all_slot_decisions(battles):
        acts  = dec.get("acts", [])
        fired = any(
            "fake_out" in r.lower()
            for a in acts
            for r in a.get("r", [])
        )
        if fired:
            fake_out_count += 1
            fake_out_battles.add(bid)
            if is_protect(dec.get("ch", "")):
                protect_top += 1
            else:
                non_protect_top += 1
    print(f"  Turns with fake_out reason          : {fake_out_count}")
    print(f"  Unique battles fake_out fired in    : {len(fake_out_battles)}")
    print(f"  Of those turns, chose Protect       : {protect_top}")
    print(f"  Of those turns, chose non-Protect   : {non_protect_top}")
    print()

    # ── 4. Double-targeting rate ──────────────────────────────────────────────
    print(SEPARATOR)
    print("SECTION 4: DOUBLE-TARGETING RATE")
    print(SEPARATOR)
    two_slot_turns      = 0
    double_target_turns = 0
    for bid, turn_num, dec_list, turn in decisions_per_turn(battles):
        if len(dec_list) != 2:
            continue
        two_slot_turns += 1
        a0 = chosen_action(dec_list[0])
        a1 = chosen_action(dec_list[1])
        if a0 and a1:
            t0, t1 = a0.get("ts"), a1.get("ts")
            if (t0 is not None and t1 is not None
                    and t0 == t1
                    and not is_switch(a0)
                    and not is_switch(a1)):
                double_target_turns += 1
    pct = double_target_turns / two_slot_turns * 100 if two_slot_turns else 0
    print(f"  2-slot turns total    : {two_slot_turns}")
    print(f"  Same-target turns     : {double_target_turns}")
    print(f"  Double-targeting rate : {pct:.1f}%")
    print()

    # ── 5. Low-HP attacks ─────────────────────────────────────────────────────
    print(SEPARATOR)
    print("SECTION 5: LOW-HP ATTACKS (HP < 15%)")
    print(SEPARATOR)
    low_hp_entries = []
    for bid, turn_num, dec, turn in all_slot_decisions(battles):
        sl  = dec.get("sl", 0)
        mon = get_mon(turn, sl)
        hp  = mon.get("hp", 1.0)
        if hp is None or hp >= 0.15:
            continue
        ch = dec.get("ch", "")
        if not ch or is_protect(ch):
            continue
        ca = chosen_action(dec)
        if ca is None or is_switch(ca):
            continue
        low_hp_entries.append({
            "battle_id": bid,
            "turn":      turn_num,
            "slot":      sl,
            "species":   mon.get("s", "?"),
            "hp_pct":    hp * 100,
            "move":      ch,
        })
    print(f"  Total low-HP attack decisions: {len(low_hp_entries)}")
    print(f"  (showing up to 20)\n")
    for e in low_hp_entries[:20]:
        print(f"  {e['battle_id']}  T{e['turn']} slot{e['slot']}  "
              f"{e['species']}  HP={e['hp_pct']:.1f}%  move={e['move']}")
    print()

    # ── 6. Flat scoring detection ─────────────────────────────────────────────
    print(SEPARATOR)
    print("SECTION 6: FLAT SCORING BUG (all stored actions weight ~1.0)")
    print(SEPARATOR)
    flat_score_all = []
    for bid, turn_num, dec, turn in all_slot_decisions(battles):
        acts = dec.get("acts", [])
        if not acts:
            continue
        if all(abs(a.get("w", 0) - 1.0) <= 0.01 for a in acts):
            sl = dec.get("sl", 0)
            flat_score_all.append({
                "battle_id": bid,
                "turn":      turn_num,
                "slot":      sl,
                "species":   get_mon(turn, sl).get("s", "?"),
                "weights":   [round(a.get("w", 0), 2) for a in acts],
                "chosen":    dec.get("ch", "?"),
            })
    print(f"  Decisions where ALL stored actions weight ~1.0: {len(flat_score_all)}")
    for e in flat_score_all:
        print(f"  {e['battle_id']}  T{e['turn']} slot{e['slot']}  "
              f"{e['species']}  chosen={e['chosen']}  weights={e['weights']}")
    print()

    # ── 7. Consecutive Protect ────────────────────────────────────────────────
    # Cross-turn comparison: same slot chose Protect on T(N-1) AND T(N).
    # Note: the old approach searched reason strings for "used protect last turn"
    # which matched opp_protect_recency (OPPONENT's Protect) — all false positives.
    # The penalised Protect action (weight x0.1) is too low to appear in stored
    # acts, so cross-turn comparison is the only reliable signal.
    print(SEPARATOR)
    print("SECTION 7: CONSECUTIVE PROTECT (same slot used Protect two turns in a row)")
    print(SEPARATOR)

    # Build a (battle_id, turn_num, slot) -> chosen_move lookup for fast comparison.
    chosen_lookup: dict = {}
    for bid, turn_num, dec, _turn in all_slot_decisions(battles):
        chosen_lookup[(bid, turn_num, dec.get("sl", 0))] = dec.get("ch", "")

    consecutive_protects = []
    for bid, turn_num, dec, turn in all_slot_decisions(battles):
        slot = dec.get("sl", 0)
        prev = chosen_lookup.get((bid, turn_num - 1, slot), "")
        if not is_protect(prev):
            continue
        # Both cases: Protect chosen again (penalty fired or waived) OR penalty
        # fired and an attack was chosen (now visible via recorder fix).
        ch   = dec.get("ch", "")
        ca   = chosen_action(dec)
        penalty_in_acts = any(
            "used Protect last turn" in r
            for a in dec.get("acts", [])
            for r in a.get("r", [])
        )
        if not is_protect(ch) and not penalty_in_acts:
            continue
        weight  = ca.get("w") if ca else None
        note    = "" if is_protect(ch) else " (penalty fired, attack chosen)"
        consecutive_protects.append({
            "battle_id": bid,
            "turn":      turn_num,
            "slot":      slot,
            "chosen":    ch,
            "weight":    weight,
            "note":      note,
        })
    print(f"  Consecutive Protect decisions: {len(consecutive_protects)}")
    for e in consecutive_protects:
        print(f"  {e['battle_id']}  T{e['turn']} slot{e['slot']}  "
              f"move={e['chosen']}  weight={e['weight']}{e['note']}")
    print()

    # ── 8. Targeting 0 HP opponent ────────────────────────────────────────────
    print(SEPARATOR)
    print("SECTION 8: TARGETING A 0 HP OPPONENT")
    print(SEPARATOR)
    zero_hp_targets = []
    for bid, turn_num, dec, turn in all_slot_decisions(battles):
        ca = chosen_action(dec)
        if ca is None:
            continue
        ts = ca.get("ts")
        if ts is None:
            continue
        opp_list = turn.get("opp", [])
        if ts < len(opp_list) and opp_list[ts] is not None:
            opp = opp_list[ts]
            if opp.get("hp", 1.0) == 0.0:
                zero_hp_targets.append({
                    "battle_id":   bid,
                    "turn":        turn_num,
                    "slot":        dec.get("sl", 0),
                    "move":        dec.get("ch", "?"),
                    "target_slot": ts,
                    "opp_species": opp.get("s", "?"),
                })
    print(f"  Decisions targeting 0 HP opponent: {len(zero_hp_targets)}")
    for e in zero_hp_targets:
        print(f"  {e['battle_id']}  T{e['turn']} slot{e['slot']}  "
              f"move={e['move']}  target_slot={e['target_slot']}  opp={e['opp_species']}")
    print()

    # ── 9. Move weight distribution anomalies ─────────────────────────────────
    print(SEPARATOR)
    print("SECTION 9: MOVE WEIGHT ANOMALIES (top action weight <= 1.05)")
    print(SEPARATOR)
    flat_score_decisions = []
    for bid, turn_num, dec, turn in all_slot_decisions(battles):
        acts = dec.get("acts", [])
        if not acts:
            continue
        top = acts[0]   # sorted weight-desc; acts[0] == chosen action
        if top.get("w", 0) <= 1.05:
            sl = dec.get("sl", 0)
            flat_score_decisions.append({
                "battle_id":  bid,
                "turn":       turn_num,
                "slot":       sl,
                "species":    get_mon(turn, sl).get("s", "?"),
                "top_label":  top.get("lb", "?"),
                "top_weight": top.get("w"),
            })
    print(f"  Decisions with top weight <= 1.05: {len(flat_score_decisions)}")
    print(f"  (showing up to 30)\n")
    for e in flat_score_decisions[:30]:
        print(f"  {e['battle_id']}  T{e['turn']} slot{e['slot']}  "
              f"{e['species']}  top={e['top_label']}  weight={e['top_weight']}")
    if len(flat_score_decisions) > 30:
        print(f"  ... and {len(flat_score_decisions) - 30} more")
    print()

    # ── 10. Switch chosen despite no OHKO threat ──────────────────────────────
    print(SEPARATOR)
    print("SECTION 10: SWITCH CHOSEN DESPITE NO OHKO THREAT")
    print(SEPARATOR)
    ohko_keywords  = ["ohko", "one-hit", "one hit ko", "faints", "will faint", "ohko threat"]
    no_ohko_switches = []
    for bid, turn_num, dec, turn in all_slot_decisions(battles):
        ca = chosen_action(dec)
        if ca is None or not is_switch(ca):
            continue
        all_reasons = [
            r.lower()
            for a in dec.get("acts", [])
            for r in a.get("r", [])
        ]
        has_ohko = any(any(kw in r for kw in ohko_keywords) for r in all_reasons)
        if not has_ohko:
            sl = dec.get("sl", 0)
            no_ohko_switches.append({
                "battle_id": bid,
                "turn":      turn_num,
                "slot":      sl,
                "species":   get_mon(turn, sl).get("s", "?"),
                "switch_to": ca.get("sw", "?"),
                "reasons":   ca.get("r", []),
            })
    print(f"  Switches with no OHKO threat reason: {len(no_ohko_switches)}")
    print(f"  (showing up to 5 examples)\n")
    for e in no_ohko_switches[:5]:
        print(f"  {e['battle_id']}  T{e['turn']} slot{e['slot']}  "
              f"{e['species']} -> {e['switch_to']}")
        print(f"    reasons on chosen: {e['reasons']}")
    print()

    # ── 11. Opponent lead frequency ───────────────────────────────────────────
    print(SEPARATOR)
    print("SECTION 11: OPPONENT LEAD FREQUENCY (turn 1 actives)")
    print(SEPARATOR)
    individual_leads: Counter = Counter()
    pair_leads:       Counter = Counter()
    leads_seen = 0
    for b in battles:
        turns = b.get("turns", [])
        turn1 = next((t for t in turns if t.get("n") == 1), None)
        if turn1 is None:
            continue
        opp = turn1.get("opp", [])
        species = [m["s"] for m in opp if m is not None and "s" in m]
        if not species:
            continue
        leads_seen += 1
        for s in species:
            individual_leads[s] += 1
        if len(species) >= 2:
            # Canonical pair: alphabetically sorted so slot order doesn't matter
            pair_leads[tuple(sorted(species))] += 1

    print(f"  Battles with turn-1 opponent data: {leads_seen}\n")

    print(f"  Individual lead frequency (top 20):")
    for species, count in individual_leads.most_common(20):
        pct = count / leads_seen * 100 if leads_seen else 0
        print(f"    {species:<25s}  {count:>4d}  ({pct:5.1f}%)")

    print(f"\n  Lead pair frequency (top 20):")
    for pair, count in pair_leads.most_common(20):
        pct = count / leads_seen * 100 if leads_seen else 0
        print(f"    {pair[0]} + {pair[1]:<20s}  {count:>4d}  ({pct:5.1f}%)")
    print()

    # ── Priority summary ──────────────────────────────────────────────────────
    print(SEPARATOR)
    print("PRIORITY SUMMARY OF BUGS / ANOMALIES FOUND")
    print(SEPARATOR)

    summary_items: list[tuple[str, str]] = []

    if flat_score_all:
        summary_items.append((
            "CRITICAL",
            f"Flat scoring bug: {len(flat_score_all)} decisions where ALL stored actions "
            "weight ~1.0 -- no module applied a multiplier (bot making blind choices).",
        ))

    if consecutive_protects:
        summary_items.append((
            "HIGH",
            f"Consecutive Protect: {len(consecutive_protects)} decisions where the same slot "
            "chose Protect two turns in a row -- penalty may be too weak or waived.",
        ))

    flat_non_basc = [e for e in flat_score_decisions
                     if "basculegion" not in e["species"].lower()]
    if flat_non_basc:
        summary_items.append((
            "HIGH",
            f"Flat/near-flat scoring (top weight <= 1.05) on non-Basculegion mons: "
            f"{len(flat_non_basc)} decisions.",
        ))
    elif flat_score_decisions:
        summary_items.append((
            "MEDIUM",
            f"Flat/near-flat scoring (top weight <= 1.05): {len(flat_score_decisions)} decisions "
            "(all Basculegion — already counted above).",
        ))

    if zero_hp_targets:
        summary_items.append((
            "HIGH",
            f"Targeting 0 HP opponent: {len(zero_hp_targets)} decisions — bot picking "
            "moves against already-fainted opponents.",
        ))

    if low_hp_entries:
        sev = "MEDIUM" if len(low_hp_entries) > 5 else "LOW"
        summary_items.append((
            sev,
            f"Low-HP attacks: {len(low_hp_entries)} decisions where a mon at <15 % HP "
            "chose an attack instead of Protect / switch.",
        ))

    if double_target_turns > 0:
        pct2 = double_target_turns / two_slot_turns * 100 if two_slot_turns else 0
        sev  = "MEDIUM" if pct2 > 30 else "INFO"
        summary_items.append((
            sev,
            f"Double-targeting: {double_target_turns}/{two_slot_turns} ({pct2:.1f} %) "
            "of 2-slot turns both aimed at the same opponent.",
        ))

    if no_ohko_switches:
        sev = "MEDIUM" if len(no_ohko_switches) > 10 else "LOW"
        summary_items.append((
            sev,
            f"Switches with no OHKO threat reason: {len(no_ohko_switches)} decisions — "
            "switch module may be triggering without clear survival justification.",
        ))

    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    summary_items.sort(key=lambda x: order.get(x[0], 99))
    for sev, msg in summary_items:
        print(f"  [{sev}] {msg}")
        print()

    if not summary_items:
        print("  No significant anomalies detected.")

    print(SEPARATOR)
    print("Analysis complete.")


if __name__ == "__main__":
    main()
