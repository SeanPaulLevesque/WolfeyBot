"""Refine overkill-doubling to TRUE coordination errors: the non-OHKO ('wasted')
slot did real damage (>=40%) to a target its partner guaranteed-OHKO'd, AND it had
an alternative move in its acts list hitting the OTHER (alive) opponent for >=30%.
That proves spreading was both possible and meaningfully better.

Usage:  .venv\\Scripts\\python.exe tools/analyze_overkill2.py 0.6.7
"""
import json, sys, glob, os, collections, re

version = sys.argv[1] if len(sys.argv) > 1 else "0.6.7"
files = sorted(glob.glob(os.path.join("Battle Data", version, "*.json")))
games = []
for fp in files:
    try:
        with open(fp, encoding="utf-8") as f: games.append((os.path.basename(fp), json.load(f)))
    except Exception: pass

def is_switch(a): return any("switch_eval" in r for r in a.get("r", []))
def is_ohko(a):   return any("threat_elimination: guaranteed OHKO" in r for r in a.get("r", []))
def dmg_pct(a):
    for r in a.get("r", []):
        m = re.match(r"damage_output: (\d+)% HP", r)
        if m: return int(m.group(1))
    return 0
PROTECTS = {"Protect","Detect","Spiky Shield","King's Shield","Baneful Bunker",
            "Silk Trap","Burning Bulwark","Wide Guard","Quick Guard"}

true_errors = {"win": 0, "loss": 0}
games_with_error = {"win": set(), "loss": set()}
examples = []

for fname, g in games:
    oc = g.get("outcome")
    if oc not in ("win", "loss"): continue
    for turn in g.get("turns", []):
        decs = turn.get("dec", [])
        opp_alive_slots = [i for i,p in enumerate(turn.get("opp", [])) if (p.get("hp") or 0) > 0]
        if len(decs) < 2 or len(opp_alive_slots) < 2:
            continue
        chosen = []
        for dec in decs:
            ca = next((a for a in dec.get("acts", []) if a.get("lb") == dec.get("ch")), None)
            chosen.append((dec.get("sl"), dec.get("ch"), ca, dec.get("acts", [])))
        if any(c[2] is None for c in chosen):
            continue
        atks = [(sl, lb, ca, acts) for sl, lb, ca, acts in chosen
                if not is_switch(ca) and lb not in PROTECTS and ca.get("ts") is not None]
        if len(atks) < 2:
            continue
        ts_set = {ca.get("ts") for _,_,ca,_ in atks}
        if len(ts_set) != 1:
            continue
        shared_ts = next(iter(ts_set))
        ohko_slots = [t for t in atks if is_ohko(t[2])]
        if not ohko_slots:
            continue
        # the 'wasted' slots are those that are NOT the (first) OHKO and did real dmg
        wasted = [t for t in atks if not is_ohko(t[2]) and dmg_pct(t[2]) >= 40]
        # if BOTH are OHKO, the 2nd is wasted too
        if len(ohko_slots) >= 2:
            wasted += ohko_slots[1:]
        if not wasted:
            continue
        # for a wasted slot, did it have an alt move on the OTHER opp >=30%?
        found = False
        for sl, lb, ca, acts in wasted:
            other_targets = [s for s in opp_alive_slots if s != shared_ts]
            for alt in acts:
                if is_switch(alt) or alt.get("lb") in PROTECTS: continue
                if alt.get("ts") in other_targets and dmg_pct(alt) >= 30:
                    found = True
                    break
            if found:
                examples.append((oc, fname[-12:], turn.get("n"), lb, dmg_pct(ca),
                                 alt.get("lb"), dmg_pct(alt)))
                break
        if found:
            true_errors[oc] += 1
            games_with_error[oc].add(fname)

# Overall W/L across the folder
import collections as _c
_oc = _c.Counter(g.get("outcome") for _, g in games)
W, L = _oc.get("win", 0), _oc.get("loss", 0)

print(f"=== {version}: TRUE focus-fire coordination errors ===")
print("(both slots hit same target, 1 already OHKOs, wasted slot had >=30% option on other opp)")
print(f"   error TURNS  -> win:{true_errors['win']}  loss:{true_errors['loss']}")
print(f"   error GAMES  -> win:{len(games_with_error['win'])}  "
      f"loss:{len(games_with_error['loss'])}")

n_loss_games = len(games_with_error["loss"])
print(f"\nActual record: {W}W-{L}L = {W/(W+L):.1%}")
print(f"Distinct LOSS games with >=1 true coordination error: {n_loss_games}")
new_W = W + n_loss_games
new_L = L - n_loss_games
print(f"Optimistic ceiling (ALL affected losses flip to wins): "
      f"{new_W}W-{new_L}L = {new_W/(new_W+new_L):.1%}")
print(f"\nExamples (loss):")
for e in [x for x in examples if x[0]=="loss"][:35]:
    oc, fn, n, wl, wd, al, ad = e
    print(f"  {fn} t{n}: wasted {wl}({wd}% on shared) -- could've used {al}({ad}% on other opp)")
print(f"\nExamples (win):")
for e in [x for x in examples if x[0]=="win"][:10]:
    oc, fn, n, wl, wd, al, ad = e
    print(f"  {fn} t{n}: wasted {wl}({wd}%) -- alt {al}({ad}% other)")
