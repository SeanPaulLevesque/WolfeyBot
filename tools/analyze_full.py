"""Comprehensive single-pass analysis of a Battle Data/<version> folder.

Usage:  .venv\\Scripts\\python.exe tools/analyze_full.py 0.6.8
"""
import json, sys, glob, os, collections, re, statistics as st

version = sys.argv[1] if len(sys.argv) > 1 else "0.6.8"
files = sorted(glob.glob(os.path.join("Battle Data", version, "*.json")))
games = []
bad = 0
for fp in files:
    try:
        with open(fp, encoding="utf-8") as f:
            games.append((os.path.basename(fp), json.load(f)))
    except Exception:
        bad += 1

# ── helpers ──────────────────────────────────────────────────────────────
PROTECTS = {"Protect","Detect","Spiky Shield","King's Shield","Baneful Bunker",
            "Silk Trap","Burning Bulwark","Wide Guard","Quick Guard","Obstruct"}
def is_switch(a): return bool(a.get("sw"))   # switch action (robust across log versions)
def is_ohko(a):   return any("threat_elimination: guaranteed OHKO" in r for r in a.get("r", []))
def kind(label, a):
    if a and is_switch(a): return "switch"
    if label in PROTECTS:  return "protect"
    return "attack"
def dpct(a):
    for r in a.get("r", []):
        m = re.match(r"damage_output: (\d+)% HP", r)
        if m: return int(m.group(1))
    return 0
def hp_of(turn, sp, side="team"):
    for p in turn.get(side, []):
        if p and p.get("s")==sp: return p.get("hp")
    return None

# ── accumulators ─────────────────────────────────────────────────────────
outcomes = collections.Counter()
total_dec = 0
chosen_kind = collections.Counter()
turn_counts = {"win":[], "loss":[]}
ours_alive_end = collections.Counter()
# overkill
ok = {"win":collections.Counter(), "loss":collections.Counter()}
true_err = {"win":0,"loss":0}; true_err_games = {"win":set(),"loss":set()}
# switch ground truth
sw_taken=0; sw_in_died=0
escape_cat = collections.Counter()
# leads / megas
mega_pick = collections.Counter()
opp_lead_freq = collections.Counter()
our_bring = collections.Counter()
# low-confidence / struggle
struggle=0; lowconf=0
# per-version winrate by lead pair
lead_results = collections.defaultdict(lambda: [0,0])  # bring-tuple -> [W,L]

for fname, g in games:
    oc = g.get("outcome")
    outcomes[oc]+=1
    turns = g.get("turns", [])
    if oc in turn_counts and turns:
        turn_counts[oc].append(len(turns))
    prev = g.get("preview", {})
    if prev.get("mega"): mega_pick[prev["mega"]]+=1
    for o in prev.get("opp", []): opp_lead_freq[o]+=1
    bring = tuple(sorted(prev.get("bring", [])))
    if bring and oc in ("win","loss"):
        our_bring[bring]+=1
        lead_results[bring][0 if oc=="win" else 1]+=1
    if turns and oc=="loss":
        ours_alive_end[sum(1 for p in turns[-1].get("team",[]) if (p.get("hp") or 0)>0)]+=1

    for ti, turn in enumerate(turns):
        nxt = turns[ti+1] if ti+1<len(turns) else None
        my_act = [p.get("s") for p in turn.get("my",[])]
        opp_alive = [i for i,p in enumerate(turn.get("opp",[])) if (p.get("hp") or 0)>0]
        decs = turn.get("dec", [])
        # chosen-kind tally + struggle/lowconf
        chosen_by_slot = []
        for dec in decs:
            total_dec+=1
            ch = dec.get("ch",""); acts = dec.get("acts",[])
            ca = next((a for a in acts if a.get("lb")==ch), None)
            k = kind(ch, ca)
            chosen_kind[k]+=1
            chosen_by_slot.append((dec.get("sl"), ch, ca))
            if ch.lower()=="struggle": struggle+=1
            if ca and k=="attack" and ca.get("w",9)<1.0: lowconf+=1
            # switch ground truth: escape-flagged stays
            sws = [a for a in acts if is_switch(a)]
            if sws:
                best=max(sws,key=lambda a:a.get("w",0))
                if any("escapes OHKO" in r for r in best.get("r",[])):
                    if ca and is_switch(ca): escape_cat["switched"]+=1
                    elif ch in PROTECTS: escape_cat["protected"]+=1
                    else:
                        sp = my_act[dec.get("sl")] if dec.get("sl")<len(my_act) else None
                        killed = dpct(ca)>=100 if ca else False
                        fainted = nxt and sp and (hp_of(nxt,sp,"team") or 1)<=0
                        if killed: escape_cat["attack KO'd (correct)"]+=1
                        elif fainted: escape_cat["NON-KO attack + FAINTED"]+=1
                        else: escape_cat["NON-KO attack, survived"]+=1
            if ca and is_switch(ca):
                sw_taken+=1
                tgt = ch.replace("Switch ","")
                if nxt and (hp_of(nxt,tgt,"team") or 1)<=0: sw_in_died+=1
        # overkill (2v2, both attack)
        if len(decs)>=2 and len(opp_alive)>=2:
            atks=[(sl,ch,ca) for sl,ch,ca in chosen_by_slot
                  if ca and not is_switch(ca) and ch not in PROTECTS and ca.get("ts") is not None]
            if len(atks)>=2 and oc in ("win","loss"):
                ts={ca.get("ts") for _,_,ca in atks}
                if len(ts)==1:
                    shared=next(iter(ts))
                    if any(is_ohko(ca) for _,_,ca in atks):
                        ok[oc]["overkill_double"]+=1
                        # true error: wasted slot >=40% with >=30% alt on other opp
                        wasted=[t for t in atks if not is_ohko(t[2]) and dpct(t[2])>=40]
                        ohkos=[t for t in atks if is_ohko(t[2])]
                        if len(ohkos)>=2: wasted+=ohkos[1:]
                        found=False
                        for sl,ch,ca in wasted:
                            others=[s for s in opp_alive if s!=shared]
                            for alt in ca and []: pass
                            for alt in next((d.get("acts",[]) for d in decs if d.get("sl")==sl),[]):
                                if is_switch(alt) or alt.get("lb") in PROTECTS: continue
                                if alt.get("ts") in others and dpct(alt)>=30:
                                    found=True; break
                            if found: break
                        if found:
                            true_err[oc]+=1; true_err_games[oc].add(fname)
                    else:
                        ok[oc]["focus_double_noKO"]+=1
                else:
                    ok[oc]["spread"]+=1

# ── report ───────────────────────────────────────────────────────────────
W,L = outcomes.get("win",0), outcomes.get("loss",0)
print(f"================ {version}: {len(games)} games ({bad} unreadable) ================")
print(f"Outcomes: {dict(outcomes)}")
print(f"WINRATE: {W}W-{L}L = {W/(W+L):.1%}" if W+L else "no W/L")
print(f"\nDecisions: {total_dec}")
for k,v in chosen_kind.most_common():
    print(f"   {k:8s} {v:5d}  {v/total_dec:.1%}")
print(f"   struggle={struggle}  low-conf attacks={lowconf}")

print("\n── Game length ──")
for oc in ("win","loss"):
    tc=turn_counts[oc]
    if tc: print(f"   {oc}: n={len(tc)} avg={st.mean(tc):.1f} median={st.median(tc)} max={max(tc)}")
print("   our mons alive on final turn of a LOSS:",
      {k:ours_alive_end[k] for k in sorted(ours_alive_end)})

print("\n── Overkill doubling (2v2, both attack) — KEY 0.6.8 fix metric ──")
for oc in ("win","loss"):
    tot=sum(ok[oc].values())
    if not tot: continue
    od=ok[oc]["overkill_double"]; fd=ok[oc]["focus_double_noKO"]; sp=ok[oc]["spread"]
    print(f"   {oc}: n={tot}  spread={sp/tot:.1%}  overkill_double={od/tot:.1%}  focus_noKO={fd/tot:.1%}")
print(f"   TRUE coordination errors: win={true_err['win']} ({len(true_err_games['win'])} games), "
      f"loss={true_err['loss']} ({len(true_err_games['loss'])} games)")

print("\n── Switch behaviour ──")
print(f"   switches taken={sw_taken}  switched-in died next turn={sw_in_died}"
      f" ({sw_in_died/max(1,sw_taken):.0%})")
print(f"   escape-flagged stays: {dict(escape_cat)}")

print("\n── Mega selection ──", dict(mega_pick))
print("\n── Top opponent lead species ──")
for sp,c in opp_lead_freq.most_common(12): print(f"   {sp:16s} {c}")

print("\n── Win rate by our bring (>=15 games) ──")
rows=[(b,w,l) for b,(w,l) in lead_results.items() if w+l>=15]
for b,w,l in sorted(rows, key=lambda r:-(r[1]/(r[1]+r[2]))):
    print(f"   {w/(w+l):4.0%}  ({w:3d}-{l:3d})  {'/'.join(b)}")
