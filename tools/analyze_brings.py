"""Drill into team-composition (bring-4) win rates, esp. the double-mega-stone
pattern, and opponent-lead matchup win rates."""
import json, sys, glob, os, collections

version = sys.argv[1] if len(sys.argv) > 1 else "0.6.8"
files = sorted(glob.glob(os.path.join("Battle Data", version, "*.json")))
games = []
for fp in files:
    try:
        with open(fp, encoding="utf-8") as f: games.append(json.load(f))
    except Exception: pass

STONES = {"Aerodactyl", "Venusaur"}   # the two mega-stone holders on the team

def norm(sp): return sp.replace("-M","").replace("-Mega","")

by_stonecount = collections.defaultdict(lambda:[0,0])   # n_stones -> [W,L]
both_by_mega = collections.defaultdict(lambda:[0,0])    # designated mega when both brought
member_wl = collections.defaultdict(lambda:[0,0])       # species in bring -> [W,L]
opp_lead_wl = collections.defaultdict(lambda:[0,0])     # opp lead species -> [W,L] (their actual 2 leads)

for g in games:
    oc = g.get("outcome")
    if oc not in ("win","loss"): continue
    win = oc=="win"
    prev = g.get("preview", {})
    bring = [norm(s) for s in prev.get("bring",[])]
    if not bring: continue
    stones = [s for s in bring if s in STONES]
    by_stonecount[len(stones)][0 if win else 1]+=1
    for s in set(bring): member_wl[s][0 if win else 1]+=1
    if len(stones)==2:
        both_by_mega[prev.get("mega","?")][0 if win else 1]+=1
    # opp's actual leads = first turn opp actives
    turns = g.get("turns",[])
    if turns:
        for p in turns[0].get("opp",[]):
            if p: opp_lead_wl[norm(p["s"])][0 if win else 1]+=1

def pct(w,l): return f"{w/(w+l):.1%}" if w+l else "-"

print(f"==== {version}: composition analysis ({len(games)} games) ====")
print("\n── Win rate by # of mega-stone holders (Aerodactyl/Venusaur) in the bring ──")
for n in sorted(by_stonecount):
    w,l=by_stonecount[n]
    print(f"   {n} stone(s): {pct(w,l)}  ({w}-{l}, {w+l} games)")

print("\n── When BOTH stones brought, win rate by which mega was designated ──")
for m,(w,l) in sorted(both_by_mega.items(), key=lambda kv:-(kv[1][0]+kv[1][1])):
    print(f"   mega={m:12s} {pct(w,l)}  ({w}-{l}, {w+l} games)")

print("\n── Win rate by team member present in bring ──")
for s,(w,l) in sorted(member_wl.items(), key=lambda kv:-(kv[1][0]/max(1,kv[1][0]+kv[1][1]))):
    print(f"   {s:14s} {pct(w,l)}  ({w}-{l}, {w+l} games)")

print("\n── Win rate vs opponent lead species (their turn-1 actives, >=40 games) ──")
rows=[(s,w,l) for s,(w,l) in opp_lead_wl.items() if w+l>=40]
for s,w,l in sorted(rows, key=lambda r:(r[1]/(r[1]+r[2]))):
    print(f"   {pct(w,l)}  ({w:3d}-{l:3d})  vs {s}")
