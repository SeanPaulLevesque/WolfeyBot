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
-[DONE 0.19.0] Model Rage Fist's hit-count scaling (was treated as flat 50 BP).
 -> Pokemon.times_hit (per-stint, reset on switch); parser increments it on a
 damaging move-hit; power = 50 + 50*min(times_hit,6), threaded via
 incoming_damage/full_damage_calc. Verified Annihilape -> Basculegion lifts from
 50% (flat) to 98% at times_hit=1 (actual 95%).
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
-Aurora Veil (and Reflect / Light Screen) — defensive + setup gaps. The damage
 halving is already modelled ONE direction (VERIFIED 0.27.0): the parser tracks
 screens (`_on_sidestart`/`_on_sideend` → `my_screens`/`opp_screens`, side
 detection correct), and `outgoing_damage` applies the OPPONENT's screens (incl.
 `auroraveil`, both physical+special ×2/3, crits bypass) via `screen_modifier` —
 e.g. Iron Head → Grimmsnarl 91%→60% with Reflect up. So our outgoing damage
 into a screened opponent is correct. Gaps:
   (1) [DONE 0.29.0] OUR screens now reach the incoming-threat facts.
       `incoming_damage` gained an `our_screens` param, passed as
       `defender_screens` into its `full_damage_calc` call; `build_turn_context`
       threads `state.my_screens` at both incoming call sites (active mon +
       bench switch-in candidate — screens are side-wide). So with Aurora Veil /
       Reflect / Light Screen up the doom / is_threatened / Protect facts now see
       the ×2/3 reduction instead of over-estimating. Covered by
       TestIncomingScreens. Snapshot baseline UNCHANGED (turn-1 boards have no
       screens up, so 0 cells moved) — no regeneration review needed after all.
   (2) No value for SETTING UP a screen, and no denial/urgency around the opponent
       setting one (cf. the TR/TW `SetterUrgency`/`SetterDenial` modules) — the
       engine neither rewards clicking Aurora Veil nor reacts to the opponent's.
   (3) Aurora Veil needs Snow to set — not checked (minor; only matters if we
       model setting it).
 (1) touches the incoming-threat facts → a reviewed snapshot regeneration per the
 testing rule.
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
-[OPEN] Make the turn-1 scenario go through the PARSER as if it were a real game,
 instead of building BattleState directly. Today gen_snapshot constructs a clean
 board (100% HP, no field effects, no boosts), so it does NOT model turn-1 entry
 mechanics: opponent Intimidate lowering our Atk, lead weather (Drizzle/Drought/
 etc.), and White Herb -> Unburden (e.g. Incineroar Intimidates our Sneasler ->
 White Herb restores Atk + is spent -> Sneasler is Unburden-fast). So the snapshot
 baseline is unrealistic AND can't catch parser+engine integration bugs (e.g. the
 0.20.0 White-Herb -clearnegativeboost bug would NOT have shown up in a snapshot).
 The catch: Showdown only emits those entry messages during a real game, so we'd
 have to GENERATE the turn-1 entry protocol ourselves (re-encode which abilities
 fire, speed order, weather winner, which White Herbs pop) -- the entry logic has
 to live somewhere. Two options:
   A) Full parser replay: synthesize the |request| JSON for our team + a protocol
      stream (|switch| the 4 leads, emit each lead's entry-ability messages,
      |turn|1) and feed BattleParser -> real BattleState. Exercises the parser
      (would have caught White Herb); bigger build (a mini turn-1 entry simulator
      + request-JSON synthesis), and the generator itself can hide bugs.
   B) Apply entry effects directly onto the synthetic BattleState (Intimidate -1,
      lead weather, White Herb restore+Unburden) before running the engine.
      Realistic board, far less code, but duplicates entry logic and does NOT
      exercise the parser.
 EITHER changes every snapshot baseline (Intimidate/weather/Unburden now in play)
 -> a large reviewed regeneration per the testing rule. Recommendation: B for
 realistic decisions, A if parser+engine integration coverage is the goal.
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
   * [DONE 0.24.0 — opponent side] RedirectionModule (phase-1): scales each of
     our single-target attacks by its damage to an active opp Rage Powder /
     Follow Me user (capped 1.0); immune→x0, KO-the-redirector→x1, and the
     scale-down naturally favours Protect/switch/spread. Data-driven user sets
     (_RAGE_POWDER_USERS / _FOLLOW_ME_USERS via population_move_users).
     Exemptions: spread/status/switch; Stalwart/Propeller Tail (both); Rage
     Powder also exempts Grass / Overcoat / Safety Goggles.
     REMAINING refinements (4/5/6 from the design review):
       (4) blend with intended-target damage instead of assuming redirect ALWAYS
           fires (the pure version over-hedges when the opp won't click it);
           e.g. alpha*(dmg to redirector) + (1-alpha)*(dmg to intended).
       (5) skip the hedge for a move already aimed AT the redirector (currently a
           minor double-count vs DamageOutput's own damage scaling).
       (6) coordinate the second slot so both attacks don't over-commit onto the
           redirector once one covers it (check whether DoublingAdjuster already
           handles this); also Spotlight + Storm Drain/Lightning Rod variants,
           and the multi-redirector (both opp slots) tie-break (v1 uses slot 0).
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
-Scrappy (Normal/Fighting moves hit Ghost-types; also ignores Intimidate): a type-EFFECTIVENESS OVERRIDE, not an atk_modifier — when the attacker has Scrappy, a Ghost defender's ×0 to Normal/Fighting becomes ×1 (so e.g. Lopunny-Mega's Return/Close Combat connects on a Ghost). Needs the attacker's ability threaded into type_effectiveness (the ×0 immunity check), on BOTH sides: our outgoing damage AND incoming-threat facts (a Scrappy opponent's Normal/Fighting now threatens our Ghost-types — Basculegion, Aegislash, etc.). Champions-legal carriers via usage: Lopunny-Mega (and any revealed Scrappy). Touches incoming-threat facts → a reviewed snapshot regeneration per the testing rule. (Second half — ignores Intimidate — is separate: it would gate the -1 Atk we apply when a Scrappy mon switches in.)
-Out of format, revisit only if the legal pool changes (no Champions-legal holder today): Slow Start (Regigigas), Orichalcum Pulse (Koraidon), Hadron Engine (Miraidon; also needs Electric Terrain), Flower Gift (Cherrim). Any of these would also need turns-active and/or terrain tracking that we deliberately skipped.

model calibration:
-Team-preview offense scoring ignores STAB. `_offensive_score` (team_preview.py)
 ranks bring/lead picks by the best type-effectiveness our MOVE types achieve vs
 each opponent's typing — it never adds the same-type bonus, so a mon attacking
 off-STAB scores identically to one with STAB. The forme typing IS resolved on the
 defensive side (`_defensive_types`/`_defensive_ability` correctly use the mega
 form, e.g. Mega Staraptor = Fighting/Flying + Contrary), but offense is move-only
 and forme-independent, so Mega Staraptor turning Fighting-type does NOT lift its
 lead score for Close Combat the way real damage would. Fix: in `_offensive_score`,
 multiply a move type's effectiveness by ~1.5 when that type is in the member's
 ACTIVE-forme typing (`_defensive_types(member)` already gives the mega typing) —
 so STAB coverage outranks equal off-STAB coverage. Pure preview/lead scoring; no
 in-battle damage path, so no snapshot baseline shift. NB this is coverage-shaping
 (which mon leads), still not raw damage — a deliberately coarse pick heuristic. It currently ranks on
 RAW SPEED only (`will_outspeed(ours, other)` called without the moves), so it
 ignores both move priority (Fake Out / Bullet Punch / Aqua Jet) and ability
 priority (Prankster, Gale Wings). On the 0.13.0 accuracy run this was ~65% of all
 turn-order "misses" (17 Prankster/support-status + 11 move-priority of 43) —
 i.e. the speed ranking is actually good; the metric just doesn't model who really
 moves first. Fix: thread the chosen move (and the opponent's likely move) into
 will_outspeed so the position reflects the priority bracket, and add Prankster
 (status moves +1 from Prankster users) / Gale Wings (Flying moves +1 at full HP)
 as ability priority. Improves the pos weighting (e.g. stop over-rating our attack
 when we're about to be Fake-Out'd / Pranksterred); pairs with the FakeOut module.
 The residual genuine speed misreads were ~13, almost all ±1 (conservative >0.5 /
 speed-tie threshold nudging a clearly-faster mon down one slot) — minor.
-Incoming-threat assessment misses low-usage super-effective coverage moves.
 `damage.incoming_damage(top_n_moves=6)` only assesses an opponent's 6 most-used
 moves, so a coverage move outside that window is never scored even when it's the
 hardest hit. Surfaced by tools/accuracy_report.py on the 0.13.0 run: Metagross-Mega
 Ice Punch (7th move, ~23% usage) -> Garchomp is 4x SE and KO'd, but went
 unassessed (predicted nothing, actual 100%). CONFIRMED this is the move-count
 cutoff, NOT a forme/mega-inference bug — the mega is inferred correctly
 (Metagross -> Metagross-Mega, Tough Claws, Metagrossite, mega stats) and its
 top-6 moves ARE assessed. Likely behind a few other defensive under-predictions
 too. Fix options: (1) raise top_n_moves to 8-10; (2) [preferred] replace the
 fixed-N with a usage floor (~15-20%) so 23%-Ice Punch clears it but true off-meta
 tech doesn't; (3) keep top-6 but always add any move >=~10% usage that is
 super-effective vs the defender. NB this changes incoming-threat facts, so it
 shifts the turn-1 snapshot baseline -> land it with a baseline review per the
 testing rule.
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
      assume defensive resist-berries). Candidate follow-up: model defensive
      resist berries (Yache/Occa/Chople/Roseli/etc.). NOT spread, NOT Tera
      (Tera is ILLEGAL in Champions — do not model it; struck 0.27.0). Screens
      are NOT the cause either: the offense path is verified working (parser
      `-sidestart` -> `opp_screens` -> `outgoing_damage` -> `screen_modifier`
      ×2/3; e.g. Iron Head -> Grimmsnarl 91%->60% with Reflect), so a screened
      foe is already discounted on our outgoing side.

   Re-confirmed on the 0.26.0 v6 run (137 games, 62 offense gaps; reports/):
   - 48 OVER (actual ~0.5-0.7x predicted), all into bulky/support mons. Two
     real unmodeled causes on top of the defensive-spread under-rating:
       (a) DEFENSIVE RESIST BERRIES — Sneasler Close Combat -> Archaludon
           93%->38% (x0.41) with NO recorded Def boost and Sneasler NOT
           Intimidated at that turn = a flat halving of a SE Fighting hit =
           a Chople Berry. This is the highest-leverage fixable lever.
       (b) Archaludon's Stamina Def+1/hit IS captured (parser -> boosts ->
           defender_boosts) but we score at turn start, so a 1-2 stage lag
           remains. Intimidate is also wired (parser -unboost -> attacker_boosts).
   - 14 UNDER (actual higher), opponents FRAILER than our (bulky) modal spread:
     Metagross Psychic Fangs -> Dragonite-Mega 28%->54%, Starmie-Mega 13%->33%,
     etc. (verified our Metagross-Mega DOES use Tough Claws + mega Atk, so it's
     the targets). Net: a single modal spread under-rates dedicated walls
     (over-predict) and over-rates glass cannons (under-predict) — a coarse
     "wall vs offensive" spread split is the deeper (lower-priority) lever.

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
