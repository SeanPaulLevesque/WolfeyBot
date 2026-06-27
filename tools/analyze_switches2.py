"""Ground-truth switch analysis: cross-reference each 'escape' non-switch with the
NEXT turn to see if the mon that stayed actually fainted and whether its attack
accomplished anything.

Usage:  .venv\\Scripts\\python.exe tools/analyze_switches2.py 0.6.7
"""
import json, sys, glob, os, collections

version = sys.argv[1] if len(sys.argv) > 1 else "0.6.7"
files = sorted(glob.glob(os.path.join("Battle Data", version, "*.json")))
games = []
for fp in files:
    try:
        with open(fp, encoding="utf-8") as f:
            games.append((os.path.basename(fp), json.load(f)))
    except Exception:
        pass

def is_switch_act(a): return bool(a.get("sw"))   # switch action (robust across log versions)
PROTECTS = {"Protect","Detect","Spiky Shield","King's Shield","Baneful Bunker",
            "Silk Trap","Burning Bulwark","Wide Guard","Quick Guard"}

def hp_of(turn, species, side="team"):
    for p in turn.get(side, []):
        if p.get("s") == species:
            return p.get("hp")
    return None

# Categorise every 'escape-flagged' non-switch by ground-truth outcome.
cats = collections.Counter()
real_misses = []          # non-KO attack, our mon fainted next turn
protect_dodges = 0

for fname, g in games:
    turns = g.get("turns", [])
    outcome = g.get("outcome")
    for ti, turn in enumerate(turns):
        nxt = turns[ti+1] if ti+1 < len(turns) else None
        my_actives = [p.get("s") for p in turn.get("my", [])]
        for dec in turn.get("dec", []):
            sl = dec.get("sl")
            chosen = dec.get("ch", "")
            acts = dec.get("acts", [])
            switch_acts = [a for a in acts if is_switch_act(a)]
            if not switch_acts:
                continue
            best_sw = max(switch_acts, key=lambda a: a.get("w", 0))
            sw_escape = any("escapes OHKO" in r for r in best_sw.get("r", []))
            if not sw_escape:
                continue
            chosen_act = next((a for a in acts if a.get("lb") == chosen), None)
            if chosen_act is None:
                continue
            if is_switch_act(chosen_act):
                cats["switched (took escape)"] += 1
                continue
            # Our mon in this slot
            our_species = my_actives[sl] if sl < len(my_actives) else None
            if chosen in PROTECTS:
                cats["protected (dodge+stay)"] += 1
                protect_dodges += 1
                continue
            # It's an attack. Was it a guaranteed KO? Check target HP next turn / weight.
            cw = chosen_act.get("w", 0)
            ts = chosen_act.get("ts")
            # KO heuristic A: damage_output reason >= 100%
            dmg_pct = 0
            for r in chosen_act.get("r", []):
                if r.startswith("damage_output:"):
                    import re
                    m = re.search(r"(\d+)% HP", r)
                    if m: dmg_pct = int(m.group(1))
            killed_target = dmg_pct >= 100
            # Ground truth: did our mon faint by next turn?
            our_fainted = False
            if nxt is not None and our_species:
                hp_next = hp_of(nxt, our_species, "team")
                if hp_next is not None and hp_next <= 0:
                    our_fainted = True
            if killed_target:
                cats["attack KO'd (stay correct)"] += 1
            elif our_fainted:
                cats["NON-KO attack + our mon FAINTED"] += 1
                real_misses.append((fname, turn.get("n"), sl, our_species, chosen,
                                    round(cw,2), dmg_pct, best_sw.get("lb"),
                                    round(best_sw.get("w",0),2), outcome))
            else:
                cats["NON-KO attack, mon survived"] += 1

print(f"=== {version}: ground-truth on {sum(cats.values())} 'escape-flagged' decisions ===")
for k, v in cats.most_common():
    print(f"  {v:4d}  {k}")

print(f"\n=== REAL MISSES (non-KO attack, our mon fainted next turn) — "
      f"switch likely better: {len(real_misses)} ===")
loss_misses = [m for m in real_misses if m[9] == "loss"]
print(f"   of which in LOSSES: {len(loss_misses)}")
for (fname, tn, sl, sp, ch, cw, dpct, swl, sww, oc) in real_misses:
    print(f"  [{oc[:4]}] {fname[-12:]} t{tn} sl{sl} {sp}: {ch}({dpct}%,w={cw}) "
          f"-> faint; switch {swl}(w={sww})")
