Data analysis tasks:
-on my team, what are the moves which saw the least usage? Should they be changed?
-what are the team archetypes that give us the most trouble?

process / regression:
-Separate big changes for regression testing. Sweeping correctness changes (e.g. the 0.8.0 SP->stat formula fix) silently invalidate every prior win-rate baseline, so they must land in ISOLATION with their own before/after sample, not stacked with team/tuning edits — otherwise win-rate effects can't be attributed. Lesson from 0.8.0: the SP fix and the Scarf-Garchomp team change went out together, so the next ladder run measures both at once. Going forward: land one big lever at a time, re-baseline, then the next.
-Verify the engine uses champions_moves.json's `championsChanges` field (modified PP/power vs base game) rather than base-game move power anywhere. The authoritative move-change data + other reference files live in the "VGC Champions" Claude project's /mnt/project/ directory — NOT accessible from the WolfeyBot dev environment (path does not exist here). Need the user to surface those files (copy into the repo, or paste) before this can be checked. Other files in that directory should be cross-checked against the engine's data layer too.

Regulation M-B follow-ups (data folded in 2026-06-17):
-Hand-compile usage data for the 38 new mons once available (Smogon M-B stats land
 ~July). Run `tools/move_coverage.py` to see the current no-usage set. Until then
 the new mons have no assumable opponent moveset, and the mega stone->forme mapping
 (usage-derived in data/sets.py) needs an explicit override for the new megas.
-Scrape the Serebii Champions Pokédex (serebii.net/pokedex-champions/<name>/) for
 the new mons' FULL movepools and diff against champions_moves.json — we only added
 their signature moves (Make It Rain/Rage Fist/Barb Barrage/Spirit Break/No Retreat),
 so a new mon could use a TM move we still lack. Fold any misses in via the same CSV
 spot-check flow.
-Model Rage Fist's hit-count scaling (currently treated as flat 50 BP). M-B behavior:
 power +50 per hit taken, and stacks now reset on switch-out. Model it if it proves
 to matter in practice.
-Turn-order -> speed estimation (prereq DONE 0.13.0: recorder now logs per-turn
 tailwind `tw` + active boosts `b`). Mine observed move order from battle logs to
 estimate opponents' raw speed: for same-priority-bracket attack-vs-attack pairs
 with no Trick Room, normalise our known speed by tailwind/boosts/paralysis, derive
 a bound on the opponent's effective speed, then back out raw speed (divide out the
 opp's tailwind / assumed Scarf). Aggregate bounds across games -> seed `spreads`
 in sets_supplement.json for the gap mons, and consider wiring the dormant
 `data.speed_tiers.update_speed_belief` to refine speed beliefs live mid-game.
 Re-run tools/seed_supplement_from_logs.py after the next batch (logs from 0.13.0+
 carry the needed fields; pre-0.13.0 logs lack tw/boosts and can't be normalised).
 NB the confounder that motivated this: our own team sets Tailwind (Aerodactyl), so
 without the logged `tw` the bounds are systematically corrupted.
-Accept + record Open Team Sheets (OTS). The M-B ladder offers OTS at team preview
 (the bot currently ignores the `|uhtml|otsrequest|` accept/deny prompt). Accepting
 reveals each opponent mon's item / ability / moves / Tera type up front; recording
 the revealed sheet would close the items/abilities/spreads gaps that the move/
 teammate log-mine can't (the logs don't capture opp items/abilities). Needs: parser
 handling for the OTS reveal (`|showteam|` / equivalent) + a recorder field, then a
 seeder pass. Highest-leverage path to real M-B opponent data before Smogon stats land.

feature modules:
-I am thinking about a switch module that switches based on the move type a slot is weak against. For instance it would switch in aerodactyl when opp garchomp is threatening a ground type. Right now it looks at all available moves, but doesn't think about likely moves.
Add more complete weather and field effects to the engine. ie damage from sandstorm, blizzard accuracy from snow, +fire damage from sun
-[OPEN — Phase 3 of the scenario/snapshot system] Arbitrary mid-game scenarios.
 Infrastructure is DONE (0.9.x): scenarios/ (board-state templates) + snapshots/
 (generated tables per scenario × team) + tools/gen_snapshot.py, with an
 auto-discovering regression test (tests/test_turn1_decisions.py parses every
 snapshots/<scenario>/<team>.md) and per-team generation (gen_snapshot --team
 <name>@<vN>).  turn1_openings is the only scenario so far.
 REMAINING: add arbitrary mid-game scenarios — collections of board states (mix
 of popular Pokémon, various weather, different HP, different benches), ideally
 EXTRACTED FROM REAL BATTLE LOGS rather than hand-specified, each runnable
 against any team.  Needs: a log → scenario extractor (pull a board state out of
 a Battle Data turn) + a scenarios/<name>.py that replays it.  The snapshot +
 auto-test machinery then guards them for free.
-[DONE 0.7.6] it sounds like pokemon on the bench are assumed to have their items even if they are spent and then switch out. This needs to be tracked.
  -> SwitchModule now evaluates bench mons with the live tracked item (None once consumed); see CHANGELOG 0.7.6.
-[ANSWERED] Does sneasler's unburden ability get accounted for?
  -> Yes: turn_order applies the x2 once item_consumed is set (White Herb popped); order is stages -> Scarf -> weather ability -> Unburden -> Tailwind -> paralysis.
-Take Choice items locking in moves into account. An opponent with a revealed/assumed Choice Scarf/Band/Specs that has already attacked is locked into that one move until it switches: incoming threat should collapse to just the locked move (not their full movepool), Protect/switch value changes when we resist the locked move, and a locked-in opponent that switches out resets the lock. Pairs with the likely-moves switch module idea above and the existing item inference (_effective_item already assumes Choice items at >=40% usage; the lock itself is the unmodeled part).
-Model redirection: Rage Powder / Follow Me (and the siblings Spotlight, plus the
 Storm Drain/Lightning Rod ability variants). In doubles these pull ALL of the
 opponents' single-target moves onto the user for the turn (Follow Me/Rage Powder
 are +2 priority). The engine doesn't know this: _build_actions emits one
 (move,target) per live opponent and scores each target independently, so it has
 no concept that a redirector forces a target.
   * OPPONENT redirects: when an opp redirector is active, our single-target
     attacks get pulled onto it, so a damage/KO calc against the *intended*
     target is invalid that turn — the action should be re-pointed at the
     redirector (or the slot should play around it: Protect, spread move, or
     switch). Immunities to respect: Rage Powder does NOT redirect Grass-types,
     Overcoat holders, or Safety Goggles holders (Follow Me redirects all).
     Spread moves and self/ally-target moves ignore redirection.
   * OUR redirects: a support-value signal for using Rage Powder/Follow Me to
     soak a predicted attack off a threatened/setup partner (pairs with the
     anti-setup item, Task #20, and the likely-moves switch module above).
   * Champions-legal redirect users to derive from usage (Amoonguss = Rage
     Powder; Togekiss/Clefable/Indeedee-F etc. = Follow Me; Storm Drain Gastrodon,
     Lightning Rod users). Build the user set the same way as _FAKE_OUT_USERS /
     the setter frozensets.


offensive abilities — deferred (need facts atk_modifier/build_turn_context don't yet thread):
The 0.8.5 batches wired every ability that keys off move flags, move type, category, attacker HP/status/weather, ally-faint count, effectiveness, or the Flash Fire flag. These remain, grouped by the missing fact:
-Doubles / ally context (need the PARTNER slot's ability/type, read across both active slots): Battery (ally's special moves x1.3), Power Spot (ally's moves x1.3), Plus/Minus (SpA x1.5 if partner has Plus/Minus), Steely Spirit ally-half (ally's Steel x1.5 — the self-half is done), Fairy Aura / Dark Aura both-sides (currently modelled per-attacker only; should boost BOTH sides' Fairy/Dark moves).
-Analytic (x1.33 if the user moves last, incl. when the target switches): needs the "do I move last" turn-order fact threaded into the damage calc — build_turn_context already computes the 4-mon order, just not passed down.
-Merciless (auto-crit = x1.5 vs a POISONED target): needs DEFENDER status into the calc. Relevant — this is Toxapex, a common wall.
-Stakeout (x2.0 if the target switches in this turn): needs opponent switch prediction — the hardest of the set.
-Sniper (x1.5 on a crit): low value — random crits are excluded from the yes/no facts, so it would only ever fire on always-crit moves (Flower Trick etc.).
-Out of format, revisit only if the legal pool changes (no Champions-legal holder today): Slow Start (Regigigas), Orichalcum Pulse (Koraidon), Hadron Engine (Miraidon; also needs Electric Terrain), Flower Gift (Cherrim). Any of these would also need turns-active and/or terrain tracking that we deliberately skipped.

model calibration:
-[RULED OUT 0.8.12] Opponent spread calibration was suspected as the cause of
 offense over-prediction into bulky walls (Corviknight/Sinistcha/Milotic). It is
 NOT. Pulled the full chaos JSON (2026-05, the complete untruncated spread
 distribution — the moveset .txt is capped at 6 spreads + ~76% "Other", same in
 bo1 and bo3) and computed the full-distribution defensive stats. Even the
 p90-bulk Corviknight (Def 161 over 8119 spreads) predicts ~34% to our Kowtow
 Cleave, while the observed actual is ~14% — a 2-3x gap NO spread explains. The
 weighted-average barely moves the modal (Corviknight 43%->39%) and can even
 lower a SpD-wall's Def (Incineroar 124->119). So a spread-calibration re-derive
 would not fix the headline cases; do not chase it.

 ACTUAL causes of the offense over-predictions, in order:
   1. Opponent DEFENSIVE SETUP — Corviknight runs Bulk Up/Iron Defense, Sinistcha
      Calm Mind + Strength Sap, Milotic Coil/Recover. These ARE modeled
      end-to-end (parser |-boost|/|-unboost| -> mon.boosts -> build_turn_context
      -> full_damage_calc; opp Def +4 correctly gives ~15%). The residual is an
      INHERENT ~1-2 stage prediction lag: we score at turn start, before the
      opponent's same-turn Bulk Up, and a Roost-staller caps at +6 while we track
      ~+4. Can't be fully fixed (we don't predict the opponent's move).
   2. Accuracy-report HP-denominator artifact — FIXED in 0.8.12 (bea2e1f):
      damage_output is % of CURRENT HP, logged actual d is % of MAX HP, so a
      Roosting target looked ~3x worse than reality. Now scaled to % of max.
   3. Residual tail (a real but separate, smaller item): some over-predictions
      aren't boosts — e.g. Ice Fang -> Garchomp 90->32% (Yache Berry? we don't
      assume defensive resist-berries), Dual Wingbeat -> Venusaur 100->18%
      (bulky-mega / Tera / screen?). Candidate follow-up: model defensive items
      (Yache/Occa/etc. resist berries) and Tera typing. NOT spread.

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
