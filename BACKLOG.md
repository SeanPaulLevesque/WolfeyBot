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


bugs:
-[FIXED 0.7.6] I saw a bug when there was a double ko against my team and the bot tried to pick the last remaining mon twice and error'd out
  -> force-switch loop now dedupes claimed targets; with one bench mon left the second slot passes. Regression tests in TestDoubleKoForceSwitch.
-[FIXED 0.7.6] we keep running into instances where data is not returning for certain pokemon and their forms. The common way that is found is when it returns "none". Instead can we create some flags in the battlelog that will point out problems like this. I don't want it to always fire, just when something doesn't work right
  -> battle logs now carry an optional "data_gaps" field, present only when a lookup actually failed, plus a WARNING at save; see BATTLE_LOG_SCHEMA.md.
-[AUDITED 0.7.6] gengar-mega is not in TR Setter Species, are there other megas and forms which don't get accounted for as TR, Fake Out, or Tailwind users?
  -> Full re-derivation against usage data: Gengar-Mega's absence is CORRECT (Mega runs 0% TR vs base 47%). One real gap fixed: plain "Meowstic" (62% Fake Out) was missing from _FAKE_OUT_USERS (only -M/-F variants were listed). Open design question: membership checks use the raw species name, not the population-weighted forme — e.g. "Gardevoir" qualifies only because 81% of its population are Mega-holders (55% TR); base-forme usage is 15%.
