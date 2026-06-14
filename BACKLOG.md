Data analysis tasks:
-on my team, what are the moves which saw the least usage? Should they be changed?
-what are the team archetypes that give us the most trouble?

process / regression:
-Separate big changes for regression testing. Sweeping correctness changes (e.g. the 0.8.0 SP->stat formula fix) silently invalidate every prior win-rate baseline, so they must land in ISOLATION with their own before/after sample, not stacked with team/tuning edits — otherwise win-rate effects can't be attributed. Lesson from 0.8.0: the SP fix and the Scarf-Garchomp team change went out together, so the next ladder run measures both at once. Going forward: land one big lever at a time, re-baseline, then the next.
-Verify the engine uses champions_moves.json's `championsChanges` field (modified PP/power vs base game) rather than base-game move power anywhere. The authoritative move-change data + other reference files live in the "VGC Champions" Claude project's /mnt/project/ directory — NOT accessible from the WolfeyBot dev environment (path does not exist here). Need the user to surface those files (copy into the repo, or paste) before this can be checked. Other files in that directory should be cross-checked against the engine's data layer too.

feature modules:
-I am thinking about a switch module that switches based on the move type a slot is weak against. For instance it would switch in aerodactyl when opp garchomp is threatening a ground type. Right now it looks at all available moves, but doesn't think about likely moves.
Add more complete weather and field effects to the engine. ie damage from sandstorm, blizzard accuracy from snow, +fire damage from sun
-I like the way that turn1_summary works, can we create an arbitrary turn test. Collections of various board states and what the bot would yield. This could maybe just be pulled from battle logs to use real examples rather than infer. It should be a mix of popular pokemon, various weather states, different hp, different benches.
-[DONE 0.7.6] it sounds like pokemon on the bench are assumed to have their items even if they are spent and then switch out. This needs to be tracked.
  -> SwitchModule now evaluates bench mons with the live tracked item (None once consumed); see CHANGELOG 0.7.6.
-[ANSWERED] Does sneasler's unburden ability get accounted for?
  -> Yes: turn_order applies the x2 once item_consumed is set (White Herb popped); order is stages -> Scarf -> weather ability -> Unburden -> Tailwind -> paralysis.
-Take Choice items locking in moves into account. An opponent with a revealed/assumed Choice Scarf/Band/Specs that has already attacked is locked into that one move until it switches: incoming threat should collapse to just the locked move (not their full movepool), Protect/switch value changes when we resist the locked move, and a locked-in opponent that switches out resets the lock. Pairs with the likely-moves switch module idea above and the existing item inference (_effective_item already assumes Choice items at >=40% usage; the lock itself is the unmodeled part).


offensive abilities — deferred (need facts atk_modifier/build_turn_context don't yet thread):
The 0.8.5 batches wired every ability that keys off move flags, move type, category, attacker HP/status/weather, ally-faint count, effectiveness, or the Flash Fire flag. These remain, grouped by the missing fact:
-Doubles / ally context (need the PARTNER slot's ability/type, read across both active slots): Battery (ally's special moves x1.3), Power Spot (ally's moves x1.3), Plus/Minus (SpA x1.5 if partner has Plus/Minus), Steely Spirit ally-half (ally's Steel x1.5 — the self-half is done), Fairy Aura / Dark Aura both-sides (currently modelled per-attacker only; should boost BOTH sides' Fairy/Dark moves).
-Analytic (x1.33 if the user moves last, incl. when the target switches): needs the "do I move last" turn-order fact threaded into the damage calc — build_turn_context already computes the 4-mon order, just not passed down.
-Merciless (auto-crit = x1.5 vs a POISONED target): needs DEFENDER status into the calc. Relevant — this is Toxapex, a common wall.
-Stakeout (x2.0 if the target switches in this turn): needs opponent switch prediction — the hardest of the set.
-Sniper (x1.5 on a crit): low value — random crits are excluded from the yes/no facts, so it would only ever fire on always-crit moves (Flower Trick etc.).
-Out of format, revisit only if the legal pool changes (no Champions-legal holder today): Slow Start (Regigigas), Orichalcum Pulse (Koraidon), Hadron Engine (Miraidon; also needs Electric Terrain), Flower Gift (Cherrim). Any of these would also need turns-active and/or terrain tracking that we deliberately skipped.

model calibration:
-Opponent spread calibration (DECISION NEEDED — pick an approach below). We
 systematically OVER-predict our damage into bulky walls.

 ROOT CAUSE: `_most_common_stats` (damage.py) returns `spread_distribution(sp)[0]`
 — the single MODAL spread — and uses it for BOTH the opponent's offense AND its
 defense. But a mon's modal spread is often an *attacker* set even when the mon
 is overwhelmingly played as a *wall*, so the one modal pick is the frailest-on-
 defense option. Conflating offense and defense in one spread is the structural
 bug.

 WORKED EXAMPLE — Corviknight (assumed base forme, no mega):
   * base stats HP98/Def105/SpD85; the engine uses modal spread
     `Adamant: 32/13/0/0/13/8` -> Def 125 (a physical ATTACKER set, 0 Def EVs).
   * that spread is only 4.6% usage; ~73% of Corviknight usage is bulk-invested
     (Impish/Careful walls): Def up to 172, usage-weighted-mean Def ~145.
   * so we calc Kowtow Cleave into a Def-125 attacker; the real Corviknight is a
     Def-160+ wall -> predicted 92%, actual 20%.

 EVIDENCE (50-game 0.8.7 ladder sample, accuracy report): the offense
 over-predictions are dominated by bulky walls — Kowtow Cleave -> Corviknight x5
 (92->20%, 60->19%, ...), Earth Power -> Archaludon x3, Dragon Claw -> Rotom-Wash
 x2, plus Sinistcha, Milotic, Pelipper, Skarmory. (Earlier samples: Delphox-Mega
 100->41%, Sinistcha 73->19%.) Defense is NOT similarly biased — the model only
 had 6 [known] under-predictions in 50 games — so the fix should target the
 OPPONENT-DEFENSE spread used by outgoing_damage, and likely leave the offensive
 (incoming) spread alone.

 OPTIONS for the opponent-DEFENSE spread:
   (a) usage-weighted AVERAGE of defensive stats across the mon's spreads
       (Corviknight -> Def ~145) — data-driven, but a synthetic stat line.
   (b) the most-used BULK-INVESTED spread (Corviknight -> Def 172) — assumes the
       common wall set; principled but ignores the attacker minority.
   (c) a Def/SpD PERCENTILE (e.g. median) across spreads.
 Key design point: split the spread choice — defensive spread for OUR outgoing
 damage into them, offensive/modal spread for THEIR incoming damage into us.

 CAVEAT: the usage file lists only each mon's top ~6 spreads (~17% of its total
 usage), so any aggregate is over a partial sample; direction is unambiguous but
 magnitudes are approximate.

 (Supersedes the earlier loose "Milotic over-prediction" note — direction is: we
 assume FRAILER than reality.) Land in ISOLATION per the regression note so the
 win-rate delta is attributable.

-In-battle forme modeling — remaining cases after 0.8.10. 0.8.10 fixed the
 STAT-changing transformers (Palafin-Hero stats; Aegislash Blade-offense /
 Shield-defense). Still unmodeled, lower impact:
   * Mimikyu (Disguise): the first hit is blocked entirely — effectively a free
     Focus Sash. We OVER-predict our first hit removing it; should gate like
     `ko_prevented` (one free hit) until Disguise is busted. Most useful of the
     leftovers (affects our offense planning vs a common mon).
   * Morpeko-Hangry: stats are identical to base; only Aura Wheel's type flips
     Electric→Dark. A per-move type override, not a stat fix. Minor.
   * Castform-Sunny/Rainy/Snowy: weather forms change TYPE (Normal→Fire/Water/
     Ice), stats unchanged — affects type effectiveness only in weather. Rare.
 (Wishiwashi/Eiscue/Cramorant/Cherrim aren't Champions-legal.)


bugs:
-[FIXED 0.7.6] I saw a bug when there was a double ko against my team and the bot tried to pick the last remaining mon twice and error'd out
  -> force-switch loop now dedupes claimed targets; with one bench mon left the second slot passes. Regression tests in TestDoubleKoForceSwitch.
-[FIXED 0.7.6] we keep running into instances where data is not returning for certain pokemon and their forms. The common way that is found is when it returns "none". Instead can we create some flags in the battlelog that will point out problems like this. I don't want it to always fire, just when something doesn't work right
  -> battle logs now carry an optional "data_gaps" field, present only when a lookup actually failed, plus a WARNING at save; see BATTLE_LOG_SCHEMA.md.
-[AUDITED 0.7.6] gengar-mega is not in TR Setter Species, are there other megas and forms which don't get accounted for as TR, Fake Out, or Tailwind users?
  -> Full re-derivation against usage data: Gengar-Mega's absence is CORRECT (Mega runs 0% TR vs base 47%). One real gap fixed: plain "Meowstic" (62% Fake Out) was missing from _FAKE_OUT_USERS (only -M/-F variants were listed). Open design question: membership checks use the raw species name, not the population-weighted forme — e.g. "Gardevoir" qualifies only because 81% of its population are Mega-holders (55% TR); base-forme usage is 15%.
