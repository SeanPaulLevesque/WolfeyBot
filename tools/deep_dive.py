"""Deeper 0.6.8 analysis: passivity/Protect efficiency, opponent setup we fail to
stop, lead survival / first-faint positioning, and coin-flip decisions.

Usage:  .venv\\Scripts\\python.exe tools/deep_dive.py 0.6.8
"""
import json, sys, glob, os, collections, re, statistics as st

version = sys.argv[1] if len(sys.argv) > 1 else "0.6.8"
games = []
for fp in glob.glob(os.path.join("Battle Data", version, "*.json")):
    try: games.append(json.load(open(fp, encoding="utf-8")))
    except Exception: pass

PROTECTS = {"Protect","Detect","Spiky Shield","King's Shield","Baneful Bunker",
            "Silk Trap","Burning Bulwark","Wide Guard","Quick Guard","Obstruct"}
SETUP = {"Trick Room","Tailwind","Shell Smash","Dragon Dance","Swords Dance",
         "Calm Mind","Nasty Plot","Quiver Dance","Geomancy","Tidy Up","Bulk Up",
         "Aurora Veil","Iron Defense","Acid Armor","Agility","Rock Polish",
         "Belly Drum","Clangorous Soul","Victory Dance","Coil","Work Up","Growth"}
def is_switch(a): return any("switch_eval" in r for r in a.get("r", []))
def threat_just(a):  # protect justified by a threat/field reason?
    R=" ".join(a.get("r",[]))
    return any(k in R for k in ("incoming_ohko","field_condition","fake_out","protect:","setter_presence"))

W=L=0
dbl_protect={"win":0,"loss":0}; tot_turns={"win":0,"loss":0}
protect_unjust=0; protect_total=0
zero_dmg_turns={"win":0,"loss":0}
coinflip={"win":0,"loss":0}; dec_total={"win":0,"loss":0}
setup_games={"win":0,"loss":0}; setup_move_loss=collections.Counter(); setup_move_all=collections.Counter()
first_faint_sp=collections.Counter(); first_faint_loss=collections.Counter()
first_faint_turn=[]
lead_survive3={"win":0,"loss":0}; lead_games={"win":0,"loss":0}
opp_tr_active_games={"win":0,"loss":0}

for g in games:
    oc=g.get("outcome")
    if oc not in("win","loss"): continue
    if oc=="win": W+=1
    else: L+=1
    turns=g.get("turns",[])
    # opponent setup moves revealed anywhere
    revealed=set()
    tr_seen=False
    for t in turns:
        if t.get("tr"): tr_seen=True
        for o in t.get("opp",[]):
            if o:
                for m in o.get("mv",[]): revealed.add(m)
    su=revealed & SETUP
    if su:
        setup_games[oc]+=1
        for m in su:
            setup_move_all[m]+=1
            if oc=="loss": setup_move_loss[m]+=1
    if tr_seen: opp_tr_active_games[oc]+=1

    # per-turn passivity + decisions
    for t in turns:
        decs=t.get("dec",[])
        if not decs: continue
        tot_turns[oc]+=1
        kinds=[]
        for d in decs:
            ch=d.get("ch",""); acts=d.get("acts",[])
            ca=next((a for a in acts if a.get("lb")==ch),None)
            dec_total[oc]+=1
            # coin-flip: chosen vs 2nd-best weight within 12%
            if len(acts)>=2 and acts[0].get("w",0)>0:
                if acts[1].get("w",0)/acts[0].get("w",1) >= 0.88:
                    coinflip[oc]+=1
            if ch in PROTECTS:
                protect_total+=1
                if ca and not threat_just(ca): protect_unjust+=1
                kinds.append("protect")
            elif ca and is_switch(ca): kinds.append("switch")
            else: kinds.append("attack")
        if len(kinds)>=2 and all(k=="protect" for k in kinds):
            dbl_protect[oc]+=1
        if kinds and all(k in("protect","switch") for k in kinds):
            zero_dmg_turns[oc]+=1

    # first faint among OUR mons + lead survival
    team0={p["s"] for p in turns[0].get("team",[])} if turns else set()
    alive_prev={p["s"]:1.0 for p in turns[0].get("team",[])} if turns else {}
    leads={p.get("s") for p in (turns[0].get("my",[]) if turns else [])}
    first=None
    for ti,t in enumerate(turns):
        for p in t.get("team",[]):
            if (p.get("hp") or 0)<=0 and alive_prev.get(p["s"],1)>0 and first is None:
                first=(p["s"],ti+1)
            alive_prev[p["s"]]=p.get("hp") or 0
        if first: break
    if first:
        first_faint_sp[first[0]]+=1; first_faint_turn.append(first[1])
        if oc=="loss": first_faint_loss[first[0]]+=1
    # lead survival to >=turn 3 (both leads still alive at start of turn 3)
    if len(turns)>=3 and leads:
        t3team={p["s"]:(p.get("hp") or 0) for p in turns[2].get("team",[])}
        if all(t3team.get(s,0)>0 for s in leads):
            lead_survive3[oc]+=1
        lead_games[oc]+=1

tot=W+L
print(f"==== {version} deep dive: {tot} games ({W}W-{L}L = {W/tot:.1%}) ====")

print("\n── Passivity / Protect ──")
for oc in("win","loss"):
    tt=tot_turns[oc]
    print(f"  {oc}: double-Protect turns {dbl_protect[oc]} ({dbl_protect[oc]/tt:.1%}), "
          f"zero-damage turns {zero_dmg_turns[oc]} ({zero_dmg_turns[oc]/tt:.1%})  [of {tt} turns]")
print(f"  Protects with NO threat/field justification: {protect_unjust}/{protect_total} "
      f"({protect_unjust/max(1,protect_total):.1%})")

print("\n── Coin-flip decisions (chosen within 12% of 2nd-best) ──")
for oc in("win","loss"):
    print(f"  {oc}: {coinflip[oc]}/{dec_total[oc]} = {coinflip[oc]/max(1,dec_total[oc]):.1%}")

print("\n── Opponent setup ──")
for oc in("win","loss"):
    print(f"  {oc}: games where opp used a setup/field move: {setup_games[oc]} "
          f"({setup_games[oc]/(W if oc=='win' else L):.1%})")
print(f"  opp Trick Room ACTIVE in game: win {opp_tr_active_games['win']/W:.1%}, "
      f"loss {opp_tr_active_games['loss']/L:.1%}")
print("  setup-move loss rate (move: losses/total, >=30):")
for m,n in setup_move_all.most_common():
    if n>=30:
        print(f"     {m:16s} {setup_move_loss[m]}/{n} = {setup_move_loss[m]/n:.0%} loss")

print("\n── Lead survival / first faint ──")
for oc in("win","loss"):
    lg=lead_games[oc]
    print(f"  {oc}: both leads alive into turn 3: {lead_survive3[oc]}/{lg} = {lead_survive3[oc]/max(1,lg):.0%}")
if first_faint_turn:
    print(f"  first faint avg turn: {st.mean(first_faint_turn):.1f} (median {st.median(first_faint_turn)})")
print("  which of OUR mons faints FIRST (count, loss% when it does):")
for sp,n in first_faint_sp.most_common():
    print(f"     {sp:14s} first-faint in {n:4d} games, {first_faint_loss[sp]/n:.0%} of those are losses")
