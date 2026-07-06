# WolfeyBot Changelog

## 0.38.1 — 2026-07-06

### Modeling
- **Mega Sol (Meganium-Mega) — personal sun.** "This Pokemon's moves are used
  as if the effects of Sunny Day were active": implemented as a table-driven
  attacker-side weather rebind inside `full_damage_calc`
  (`_PERSONAL_WEATHER_ABILITIES`), so the holder's Weather Ball becomes Fire
  100 BP with the ×1.5 sun boost and its calc overrides real field weather —
  while the field itself (and every move aimed AT the holder, and every other
  mon's calc) is untouched. The whole inference chain now bites: an unrevealed
  Meganium resolves to Meganium-Mega/Mega Sol, and its Weather Ball reads as a
  Fire OHKO threat (111% on Kingambit) instead of a Normal 50 BP poke. Turn-1
  snapshots unchanged (no Meganium in the fixed opponent leads). +4 tests.

## 0.38.0 — 2026-07-06

### Team preview — engine-grounded selection
- **Why:** the v8 report showed correct lead predictions *losing* (36% win,
  18% ahead-rate over n=11) and the selector's favourite pair (Decidueye-Hisui
  + Lycanroc-Dusk, 23 games) at 43% while Aerodactyl + Lycanroc-Dusk sat at
  92% — the type-chart arithmetic can't see real damage, OHKOs, bulk, Fake Out,
  or true turn order. Several correct-read games also opened with a turn-1
  switch: the in-battle engine immediately disagreed with the preview layer.
- **`select_leads`:** every C(n,2) lead pair is scored on a real turn-1
  `BattleState` vs the predicted opponent pair — slot value = best phase-1
  **attack** weight (real damage capped at lethal, kill bonuses, true
  item/ability/TR-aware turn order, doomed, Fake Out), pair = product. A slot
  whose best action is a **switch** takes ×0.5 (`_SWITCH_WANT_FACTOR`) — the
  engine's own verdict that the lead is self-refuting. TR / undeniable-TW
  rosters add field variants (TR-on / opp-TW-on boards, averaged), replacing
  the hand-tuned ×0.85 initiative rows.
- **`select_team`:** per-member engine matchups vs the opponent's six (best
  damage fraction dealt, worst taken; offense×2 + defense×1) replace type
  multipliers. The one-mega demotion is now *native*: a second stone holder is
  re-evaluated as its base form (replacing the BST-scaling approximation).
- The type-chart path remains as the fallback for unresolvable members
  (synthetic fixtures / missing data). `tools/preview_backtest.py` replays
  logged previews through the current selector: over the 88 v8 games the
  DH+LD pick collapses 23 → 2; lead-pair agreement with the old selector is
  17/88.

### Modeling
- **Scrappy.** A Scrappy attacker's Normal/Fighting moves hit Ghost-types: the
  Ghost component of the type product is neutralised (×1) — only that
  component, so Scrappy Close Combat vs Gengar is ×0.5 via Poison, not ×1.
  Flows through both outgoing damage and the incoming-threat facts, so a
  Scrappy Lopunny-Mega now threatens our Ghosts (4 reviewed snapshot cells:
  e.g. Aegislash King's-Shields the 2× Scrappy High Jump Kick it previously
  ignored as immune). Scrappy was already in `INTIMIDATE_IMMUNE_ABILITIES`.

## 0.37.0 — 2026-07-05

### Data: real Reg M-B usage stats (consolidation)
- **`sets.py` now reads the Smogon M-B moveset dump**
  (`moves-gen9championsvgc2026regmb-1760.txt`, 275 species) — the M-A file and
  every stopgap layered on top of it are retired: `sets-…regma-1760.txt`,
  `pikalytics_regmb_raw.json` + both `seed_supplement_*` tools, and the
  hand-entered `sets_supplement.json` entries (now slimmed to Watchog, the one
  M-B-legal species the 1760 file lacks; the gap-fill mechanism stays for the
  next reg roll). Also deleted: `data/usage.py` + `metagame-…regma` (archetype
  priors — dead code, never called) and the unwired 1630/stats dumps.
- **"No Ability" artifact filtered at parse.** 11 new megas had "No Ability" as
  their top ability (the sim logged them that way until the custom megas were
  implemented mid-month) — it would have poisoned `_effective_ability`
  (Pyroar-Mega → Fire Mane and Eelektross-Mega → Eelevate now resolve).
- **Pure-support mons are no longer "harmless".** Audino/Slurpuff usage
  movepools are 100% status, so `incoming_damage` returned empty; it now falls
  back to synthetic STAB when usage moves exist but none deal damage (skipped
  for a Choice-locked status move, which genuinely threatens nothing).
- **Ladder lead prior.** `leads-gen9championsvgc2026regmb-1760.txt` feeds
  `lead_stats.ladder_lead_pct` (megas folded into base names); `predict_pair`
  tiers 2–3 rank singles by observed count + ladder%/100 — a sub-observation
  tiebreak, so one real observation still outranks any ladder rate and our
  observed pair data stays king.
- **Snapshots: 116 decision changes, 238 weight-only** — coherent new beliefs
  (M-B Kingambit runs Black Glasses > Chople → Fighting OHKO reads; Glimmora is
  base-majority now, was 75% mega; new spreads/items throughout). Reviewed and
  approved. Five M-A-keyed test fixtures updated to M-B equivalents
  (Medicham→Altaria marginal-mega, Glimmora→Staraptor stone, Garchomp speed
  threshold, Raichu-mega-aware type fixtures, fictional supplement species).

## 0.36.0 — 2026-06-28

### Fixes
- **Consumed items no longer re-armed by their own heal.** Eating a Sitrus sends
  `-enditem` (item nulled, consumed) then a `-heal … [from] item: Sitrus Berry`
  naming what it ate; the heal handler re-set `mon.item`, so a spent berry looked
  held again and Poltergeist was modelled as connecting against an itemless
  target (battle 2640366837 T7). Guarded with `item_consumed`; recurring-item
  heals (Leftovers) still reveal correctly.
- **Poltergeist removed from `_CONTACT_MOVES`** (data fix, non-contact in canon).

### Team
- **meta-team v8** — new roster (`teams/meta-team/v8.txt`), `current` → v8.

### Dev automation (fewer approvals, fewer tokens)
- All of `tools/` is now allowlisted (`.claude/settings.json`) — prefer `tools/`
  scripts over inline Python heredocs.
- New investigation trio: `inspect_battle.py` (compact turn-by-turn log summary),
  `replay_turn.py` (re-run the current engine on a logged board vs what the game
  chose), `regen_snapshots.py` (regen all turn-1 snapshots + decision-vs-weight
  diff triage against HEAD).

### Docs
- The per-action weight table is now a generated SVG
  (`tools/gen_decision_table_svg.py` → `docs/decision_weights.svg`) — GitHub
  strips CSS from markdown, so the 12-column HTML table couldn't be kept from
  horizontally scrolling; the SVG has pixel-exact width/font and honours dark
  mode. Edit the data in the script and re-run to update.

## 0.35.0 — 2026-06-27

### Lead prediction — measuring payoff
- **Record the predicted opponent leads at decision time.** The battle log's
  `preview` gains a `pred` field (the `predict_pair` result). We never recompute
  predictions after the fact — the `lead_stats` prior drifts as games accrue, so
  a recompute would be anachronistic — hence this is forward-only.
- **`team_report.py` → new "Prediction → advantage" section** (in the generated
  report) via `lead_prediction_outcomes`: of games with a recorded prediction,
  the win rate **and** opening-exchange ahead-rate (KOs−faints over the first 3
  turns) split by whether our predicted opponent leads were **correct** — the
  confirmation that a correct read converts to an advantage — plus a per-our-
  lead-pair breakdown restricted to correct-prediction games. Older logs (no
  `pred`) are skipped; the section shows a placeholder until new games accrue.

## 0.34.0 — 2026-06-27

### Lead prediction
- **Co-occurrence-aware opponent lead prediction.** `select_leads` predicted the
  opponent's lead pair as the two highest *individual* lead frequencies — which
  pairs two independently-popular leads that are rarely led *together*
  (Whimsicott led 428×, Farigiraf 361×, but **co-led only 5×**).
- `lead_stats.json` gains a `pairs` map (per-battle co-occurrence, sorted key);
  `record_leads` bumps it, and `lead_pair_frequency` / `pair_partner_counts` /
  `all_lead_pairs` read it. `build_lead_stats.py` backfills `pairs` from existing
  logs; `seed_lead_stats.py` gets it for free via `record_leads`.
- New `predict_pair(species_list)` — three tiers: (1) the previewed pair seen
  co-led most, if it clears `PAIR_MIN_SUPPORT` (2); (2) else anchor on the
  strongest single + its most-co-led real partner; (3) else the old top-2
  singles. Facing {Whimsicott, Farigiraf, Garchomp, …} it now predicts
  Whimsicott+Garchomp (62) over Whimsicott+Farigiraf (5).
- Inert (graceful fallback to singles) until `lead_stats.json` is rebuilt with
  `pairs`; no turn-1 snapshot impact (that scenario uses fixed opponent leads).

## 0.33.0 — 2026-06-27

### Modeling
- **Poltergeist needs a target item.** Poltergeist fails outright (0 power, no
  OHKO) against a target holding no item. `damage.py` gains a `defender_has_item`
  flag (default True); `full_damage_calc` zeroes Poltergeist when it's False.
- **Belief, not just the named item.** New `_opp_has_item(state, mon)`: True
  unless we have *positive evidence* the item is gone (`ItemEvidence.consumed` or
  `Pokemon.item_consumed`). An *unknown* item is assumed held (VGC mons almost
  always carry one) — distinct from `_opp_item` returning None when it merely
  can't name the item, so Poltergeist isn't wrongly failed against unknowns.
- Wired through both damage paths: the shared `_outgoing_defender_mods` /
  `_incoming_defender_mods` helpers and the manual OHKO-fact loop in
  `build_turn_context`, so `ctx.ohko` / threat / doom all respect it. An
  opponent's Poltergeist into our itemless mon is likewise read as a non-threat.
- Turn-1 snapshots unchanged (opening items are unknown → assumed held).

## 0.32.0 — 2026-06-27

### Decision engine
- **DamageOutput saturates at lethal.** The damage term now caps the damage
  fraction at 1.0 (`min(d, 1.0)`) — overkill earns nothing, because a move can't
  benefit from dealing more than the target's remaining HP (and `d` is already
  current-HP-relative, so the cap is "remaining HP" at any HP).
- **Why: correct focus-fire routing.** When two of our mons can each OHKO a foe,
  both kills now score equally, so the joint `coordinate` pairing falls to the
  *chip damage that actually differs* — the weaker-on-the-survivor mon lands the
  kill and the stronger-on-the-survivor mon redirects — instead of being decided
  by whichever foe an attacker happens to overkill hardest. This is the routing a
  pairwise overkill adjuster structurally *cannot* do (a per-pair penalty is
  symmetric within a double and over-fires on capability), so the fix belongs in
  the value, not an adjuster.
- **Turn-1 snapshots:** 101 decision cells changed (audited via the cap-
  independent `ctx.ohko` facts): 0 gain/lose net guaranteed kills in 99 of them;
  8 swap *which* foe is killed (same count); 2 give up a guaranteed KO made by an
  overkill move (Head Smash / Wave Crash) to a switch / Protect — reviewed and
  accepted (threat-priority is a separate concern from raw damage).

## 0.31.0 — 2026-06-27

### Decision engine
- **Doubling adjuster split + flattened.** The single `DoublingAdjuster` was
  doing two jobs: the spread-your-damage tax *and* the overkill near-veto. Split
  into two phase-2 adjusters — `DoublingAdjuster` (J1) and `OverkillAdjuster`
  (J2) — over a shared `_doubling_target` gate.
- **Flat ×0.4 doubling penalty.** The base tax dropped its `_FACTORS` 2×2 table
  (0.40–0.70, softened when the target Protected last turn or the other foe
  wasn't threatening) for a single flat ×0.4. The softeners were redundant:
  target-Protect recency is already `OppProtectRecencyModule` (#11), and the
  other foe's threat is already priced into the per-slot threat weights. Removed
  the now-dead `_other_opp_threatens` helper.
- **Turn-1 snapshots: 57 cells moved** — every changed cell flips from doubling
  onto one foe to **spreading** across both (the harsher flat penalty tips
  marginal doubles toward the survivor). Approved behavior change; spot-checked.

## 0.30.0 — 2026-06-26

A batch of small, mostly behavior-preserving fixes + modeling and logging
upgrades. Turn-1 snapshots unchanged throughout (the new behaviors only bite
mid-game), so 0 cells moved.

### Modeling
- **Choice lock + Scarf rule-in.** `_choice_locked_move`: a believed-Choice
  opponent (confirmed / inferred / usage-prior) that has used one move this
  stint is locked into it — `build_turn_context` and `_switch_in_survives` pass
  `incoming_damage(only_moves=[locked])`, collapsing its threat to that move
  (resets on switch). `_infer_scarf_from_speed` rules Choice Scarf **in** as
  `ItemEvidence.inferred` when a foe outspeeds a mon it couldn't without it
  (same bracket, no TR/TW/weather) — the complement of the existing rule-out.
- **Rage Fist multi-hit fix.** The parser now counts `times_hit` **per strike**
  (Beat Up etc.), not once per move, so the persistent Rage-Fist power is right.
  `accuracy_report` dispositions a Rage Fist under-prediction whose user was hit
  earlier that turn as `accepted: Rage Fist same-turn hit count` (inherent lag),
  not a gap.
- **Full damage-modifier awareness, both directions.** New shared helpers
  `_outgoing_{attacker,defender}_mods` / `_incoming_{attacker,defender}_mods` are
  the single source of truth for boosts / status (burn) / HP / Flash Fire /
  times_hit / screens. Every `outgoing_damage` / `incoming_damage` caller splats
  them in, so switch-offense (#17) now sees a debuffed attacker into a +Def wall,
  and switch-survival (#18) now sees a +Atk foe — both previously ignored these.

### Engine structure
- **Modules renumbered 1–16** to match `docs/DECISION_ARCHITECTURE.md` top-to-
  bottom; `make_engine` reordered to suit. Phase 1 commutes (audited: no module
  reads the running weight or another's reasons), so this is purely cosmetic.
- **SwitchModule decomposed into #16 SwitchTempo / #17 SwitchOffense /
  #18 SwitchSafety**, each independently tunable. Behavior-preserving.

### Battle logs (schema 0.30.0)
- **`wall`** — every scored candidate's weight per slot decision (complete map,
  self-describing keys), alongside the existing reason-bearing `acts`. Read via
  `recorder.action_weights(dec)` (falls back to the partial `acts` map on old
  logs).
- **Turn results** — per-turn `res` (faints, per side, incl. move-less ones) and
  `sw` (switches in/out), plus a top-level `final` post-battle board snapshot.

### Tooling
- `tools/seed_lead_stats.py --dir <folder>` to reseed the opponent-lead prior
  from one team-version's games; lead stats reseeded from the v7 folder.
- `analyze_*` scripts detect switches via the `sw` key (robust across versions).

## 0.29.0 — 2026-06-26

### Urgency / Setup Denial — merged into registry-driven modules, flat ×2

`SetterUrgencyModule` and `SetterDenialModule` are now `UrgencyModule` (#5) and
`SetupDenialModule` (#6), both iterating one shared `_SETUP_TYPES` registry
(Trick Room, Tailwind, + future screens/etc.). Adding a new urgent/deniable
opponent setup is a single new registry row — no module edits — and the setter
species come from usage data (`population_move_users`), so they self-update for
new regulations and never flag a mon that doesn't actually run the move.

- **All setup urgency and denial factors are now a flat ×2** (`SETUP_URGENCY` /
  `SETUP_DENIAL`), replacing the old TR ×2.0 / TW ×1.5 split — for simplicity.
- Behavior change: Tailwind urgency/denial went ×1.5→×2.0 (TR unchanged). Turn-1
  snapshots: 371 cells shift, all on boards with a Tailwind setter present —
  mostly weight rescales (same move chosen) plus a few intended switch/Protect →
  attack flips. Reviewed and approved; snapshots regenerated.
- Urgency still fires one boost per turn (registry order, TR first); Setup Denial
  is still per-target on a guaranteed-OHKO of a setter we outspeed.

### PriorityBlock module (#16) — don't throw priority into a priority wall

Counterpart to PriorityKill (#15). Armor Tail (Farigiraf) and Queenly Majesty
(Tsareena) block incoming priority moves against the holder **and its ally**, so
our Aqua Jet / Extreme Speed / etc. simply fail to connect against either of the
opponent's actives while such an ability is up.

- New `PriorityBlockModule` (phase-1 #16, after PriorityKill): ×0 on a candidate
  whose move is in a positive priority bracket (`priority_bracket > 0`) when any
  live opponent's `_effective_ability` is in `_PRIORITY_BLOCK_ABILITIES`
  (`Armor Tail`, `Queenly Majesty`). Protect (self-target, +4), switches, and
  non-priority moves are untouched.
- Composes with #15: a priority move that would otherwise KO is still nullified
  (`3.0 × 0 = 0`) — it can't land, so it shouldn't win the slot.
- Reads `_effective_ability` (revealed > top-usage assumed), so an unrevealed
  Farigiraf is assumed to carry Armor Tail — the cautious default (wasting a
  priority move into a priority wall is the failure we're avoiding).
- Registered in `make_engine` after `DoomedModule`/`PriorityKillModule`;
  exported from `decision/__init__`; covered by `TestPriorityBlockModule`.

Turn-1 snapshots unchanged: no baseline/snapshot lead currently puts a priority
move at the top of its slot against a Farigiraf / Tsareena lead, so nothing
flips. The module acts mid-game (priority users vs a revealed priority wall).

### Aurora Veil / screens on defense — incoming damage now respects our screens

Gap 1 of the Aurora Veil backlog item. Outgoing damage already discounted hits
into a screened *opponent*; the incoming side was unwired, so with our own
Aurora Veil / Reflect / Light Screen up the threat facts (`is_threatened` /
`doomed` / Protect value) over-estimated incoming damage and we played too
cautiously.

- `incoming_damage` gained an `our_screens` param, passed as `defender_screens`
  into its `full_damage_calc` call (the `screen_modifier` ×2/3, crit-bypass
  logic is shared, so this covers all three screens at once).
- `build_turn_context` threads `state.my_screens` at both incoming call sites —
  the active mon and the bench switch-in candidate (screens are side-wide, so a
  switch-in is protected too).
- Covered by `TestIncomingScreens`. Snapshot baseline unchanged (turn-1 boards
  have no screens up). Setting-value / opponent-screen urgency-denial (gaps 2-3)
  remain backlogged.

## 0.28.0 — 2026-06-26

### PriorityKill module (#15) — prefer a priority KO over a slower one

0.27.0 made `DoomedModule` per-candidate so a doomed mon's priority revenge-KO
survives the ×0.2 cut. This goes one step further: a priority move that gets a
kill should be *preferred*, not merely un-penalised — it removes the foe before
it can act, even when we aren't doomed.

- New `PriorityKillModule` (phase-1 #15, after Doomed): ×3.0 on a candidate
  whose move is in a positive priority bracket (`priority_bracket > 0`) **and**
  `ctx.guarantees_ohko`s its target. Gated on the guaranteed OHKO, so a weak
  non-KO priority move (chip Aqua Jet, Quick Attack) gets nothing — the old
  over-valuation of priority-as-position can't return.
- Registered in `make_engine` after `DoomedModule`; exported from
  `decision/__init__`; covered by `TestPriorityKillModule`.

Turn-1 snapshots: 1 off-meta-team@v1 cell shifts (Basculegion vs Talonflame —
`Wave Crash → Aqua Jet`). Both KO frail Talonflame, but the super-effective
Adaptability Aqua Jet is a priority KO, so the ×3 edges it past Wave Crash —
and as a bonus it avoids Wave Crash's recoil. Reviewed and approved. The real
payoff is mid-game (revenge KOs on chipped foes), which a full-HP turn-1
snapshot can't surface.

## 0.27.0 — 2026-06-26

### Doomed is now per-candidate — priority moves can revenge-KO

`DoomedModule` was a per-slot all-attacks ×0.2: if a faster foe would OHKO us,
*every* attack got cut — including a priority move that would actually strike
first. Over a 136-game v6 sample our priority moves (Arcanine-Hisui Extreme
Speed, Basculegion Aqua Jet) were chosen **zero** times: the per-slot doom (and
the per-foe `neutralized` flag) sank the priority move along with everything
else, so the higher-damage non-priority move always won even when it was the
slow, undeliverable one.

- New `_move_undeliverable(slot, move)`: an attack is undeliverable iff a
  certain killer acts before *that move* (per its priority bracket) and isn't
  removed first (by the move's own priority KO, or by a faster ally).
  `DoomedModule` applies ×0.2 **per candidate**, so a doomed mon's priority
  revenge-KO keeps full weight while its slower moves are cut — it picks the
  priority KO (or escapes/shields when it has no priority answer).
- `DoublingAdjuster` (J1) now counts a slot's kill as confirmed only if that
  move is deliverable (same check), so a doomed slow "kill" no longer redirects
  the partner off the survivor.
- The per-slot `ctx.doomed` / `_ko_before_acting` remain as a summary fact.

Turn-1 snapshots: 10 off-meta-team@v1 cells shift, all vs opponent Kingambit —
its super-effective Sucker Punch (+1) OHKOs Ghost-type Basculegion, so
Basculegion's Wave Crash is undeliverable and it now switches/Protects instead
of swinging into the priority KO. Reviewed and approved.

## 0.26.0 — 2026-06-25

### Module decomposition — one concern per module (no embedded "unless")

Refactored the kill/threat scoring so every module is a single unconditional
rule; conditions that were embedded as "do X *unless* Y", or re-checked across
modules, are now their own modules reading shared `TurnContext` facts. Turn-1
snapshots reviewed and approved (the diffs are the intended behaviour below).

- **ThreatElimination → pure ×5** ("Score A Guaranteed Kill"). The "die before
  acting" ×0.2 cancel is now a standalone **`DoomedModule` (#14)** that applies
  ×0.2 to **all** of a doomed slot's attacks (not just the kill) — Protect and
  switch untouched. A doomed mon now escapes/shields instead of swinging into a
  likely death.
- **ProtectValue → pure ×2.5** (threatened shield). Its other rows split out:
  the 1v1/2v1 "Protect only delays" cancel is **`EndgameStallModule` (#13)**, and
  the partner-clears ×3.0 is now a **phase-2 adjuster `PartnerClearsAdjuster`
  (J5)** — because whether a threat is cleared depends on the *partner's chosen
  action*, a genuinely cross-slot question. It now fires only when the partner's
  actual attack guaranteed-OHKOs the threatener (was: mere capability).
- **DoublingAdjuster (J1)** no longer re-checks doom; it reads only the OHKO fact.

### Opponent priority moves — modelled, lethality-gated

The engine now recognises an opponent acting first via a priority move (Sucker
Punch, Bullet Punch, Aqua Jet, Extreme Speed, …), in addition to the Gale Wings
special case — but **only when that priority move is itself lethal** to the
target (`ctx.priority_ohko` / `priority_certain`, computed in `build_turn_context`).
A non-lethal priority move (an Aqua Jet that can't KO us) is ignored, so we don't
play cautious around it. Our own higher-priority move still out-brackets theirs
(`_strike_first_with`), so offense is unaffected. Prankster status and Grassy
Glide are intentionally not modelled (we only model damage; Grassy Glide is off-meta).

### SetterUrgency — TR↔TW cross-guard removed

Dropped the "no opposing Tailwind" / "no Trick Room" clauses: they only mattered
on a mixed TR+TW board, which the metagame doesn't run. The if/elif (TR first)
already fires exactly one boost.

## 0.25.0 — 2026-06-25

### Incoming damage is now % of our CURRENT HP (HP-convention fix)

Outgoing damage already overrides the HP denominator with the opponent's
**current** HP (`opp_current_hp`/`opp_hp_percent`), so offensive OHKO detection
correctly recognises a chipped target.  Incoming damage did not: it always used
our **max** HP, so the incoming KO facts meant *"can the opponent OHKO us from
full?"* — not *"can it kill us at the HP we actually have right now?"*  A
sub-max-HP lethal hit on an already-damaged mon (e.g. a 30%-of-max hit on a
17%-HP Garchomp) was never flagged.

Consequence of the asymmetry: `ctx.incoming_ohko` / `incoming_certain` —
and therefore `is_threatened` / `is_doomed`, ProtectValue's OHKO-threat boost,
and SwitchModule's escape-OHKO ×4 bonus — all under-fired for damaged mons.
This is the mechanism behind the observed "won't Protect/switch a low-HP mon out
of a lethal hit" misplays.

- `incoming_damage` gains `our_current_hp` / `our_hp_percent` (mirroring the
  outgoing override), scaling the defender HP denominator so incoming
  `is_ohko` / `hp_fraction_*` are relative to current HP.  `our_defender_is_full_hp`
  still gates Sash/Sturdy independently.
- `build_turn_context`'s incoming-fact loop and `SwitchModule._switch_in_survives`
  pass the live HP **fraction** (`mon.hp_fraction × 100`), which naturally no-ops
  at full HP — so full-HP scenarios (all turn-1 snapshots) are byte-identical.
- Tests: `test_chipped_defender_registers_sub_max_lethal_hit`. Turn-1 snapshot
  unchanged.

## 0.24.0 — 2026-06-24

### Model opponent redirection (Rage Powder / Follow Me)

Redirection was unmodeled — the engine scored each single-target attack against
its intended target, oblivious that an active Rage Powder / Follow Me user pulls
those moves onto itself.  Log analysis: opponents use redirection in ~16% of
games (530-game M-B sample) and we win only 39% of those vs 47% overall.

- Data-driven user sets via `population_move_users`: `_RAGE_POWDER_USERS`
  (Ariados, Scovillain, Sinistcha, Vivillon, Volcarona), `_FOLLOW_ME_USERS`
  (Clefable, Maushold) — self-updating with usage stats; two sets because the
  immunities differ.
- New phase-1 `RedirectionModule`: when an active opponent redirector would pull
  our move, scale each single-target attack by its damage **to the redirector**
  (capped at 1.0).  Immune move → ×0 (don't feed it); a move that KOs the
  redirector → ×1 (removing it ends the redirection); and scaling attacks down
  naturally favours Protect / switch / spread (the "play around it" answer).
- Exemptions: spread/status/switch aren't redirected; Stalwart / Propeller Tail
  on our attacker ignore both moves; Rage Powder additionally doesn't redirect a
  Grass-type attacker, or one with Overcoat / Safety Goggles (Follow Me has no
  such immunity).
- Backlog: blend with intended-target damage (don't assume redirect always
  fires); skip the hedge for a move already aimed at the redirector; coordinate
  the second slot off the redirector once covered.

Turn-1 snapshots unchanged (no redirector flips a turn-1 lead decision). Tests:
`TestRedirectionModule`.

## 0.23.0 — 2026-06-23

Re-baseline release — **no new functional changes** beyond 0.22.0. The version is
bumped purely to open a fresh battle-log epoch (`Battle Data/0.23.0/`) so the
session's gameplay-affecting fixes can be validated on a clean sample,
un-comingled with the pre-fix 0.22.0 games:

- Ally Switch `|swap|` handling (opponent active-slot desync),
- our mega ability applied to **offense**, not just incoming (Tough Claws etc.),
- corrected Champions mega data (5 typings) + de-hardcoded `champions_megas.json`,
- Garchomp Life-Orb item prior (M-B stopgap),
- M-B opponent-lead-stat reseed,
- explicit `opp_formes` recording + report fixes (forfeit filter, mega detection).

## 0.22.0 — 2026-06-20

### Resolve two-mega species by the held stone (Raichu-Mega-Y bug)

Adding Raichu @ Raichunite Y (meta-team v4) surfaced a latent gap: `team.py`'s
`_mega_form_name` keyed the mega forme off the **base species name** only, so a
two-mega species couldn't be disambiguated — for Raichu it built the
non-existent `"Raichu-Mega"`, returned `None`, and the mon played as **base
Raichu** (Static, base stats) instead of Mega-Y (No Guard, SpA 233 / Spe 182).
Zap Cannon's No-Guard accuracy and the mega stat jump were both silently lost.
`_MEGA_NAMES` also hard-coded X/Y defaults (Charizard→Y, Mewtwo→Y) regardless of
the stone actually held — so a Charizardite **X** holder was mis-resolved to -Y.

- `_mega_form_name(base_name, item=None)` now consults `mega_forme_for_stone`
  first — the held stone is authoritative for X/Y (Raichunite Y →
  Raichu-Mega-Y, Charizardite X → Charizard-Mega-X).
- The no-stone fallback is now **data-driven**: the hardcoded `_MEGA_NAMES`
  dict (Charizard→Y, Mewtwo→Y) is replaced by `data.default_mega_forme`, which
  returns the highest-usage mega forme for the base (Charizard → -Mega-Y while
  Y leads X in usage, flipping automatically if X ever overtakes). The opponent
  assumption paths (`data.assumed_forme`, `team_preview._build_opp_mega_forms`)
  were already usage-driven; this brings our-side resolution in line.
- Regression tests in `TestMegaFormResolution`.

### Fix Pikalytics seeder multi-mega usage split (Raichu forme assumption)

`tools/seed_supplement_from_pikalytics.py` mis-split every **two-mega** species:
it weighted *all* mega formes by `max()` of the stone usages and subtracted only
that max from the base, so Raichu (`Raichunite Y 60.5%`, `Raichunite X 18.2%`)
got 605 for **both** formes and base 395 — and `assumed_forme` kept Raichu base
anyway because the stale M-A base count (94720, from before Raichunite existed)
shadowed the gap-filled supplement.

- Seeder: each mega is weighted by **its own** stone's usage (Raichu-Mega-Y 605,
  -Mega-X 182), the base subtracts the **sum** of own-stone pcts (base 213), and
  foreign-contamination stones scraped onto a page (e.g. Scovillainite on
  Sceptile) are excluded from both the count math and the base item list.
- `_merge_supplement` now honours an `"override": true` flag (emitted by the
  seeder on every mega-capable base) so M-B Pikalytics data wins over a stale
  pre-mega M-A base count. Of the 15 flagged mons only **Raichu** is actually in
  the M-A file — the rest are no-ops (new M-B mons added either way).
- Result: `assumed_forme("Raichu") → Raichu-Mega-Y`, data-driven (flips if the
  X/Y shares ever reverse). Turn-1 snapshot baseline **unchanged**; full suite green.

### De-hardcode Champions mega data + fix 5 mangled typings

The mega formes' types/stats/abilities lived in two hand-maintained Python
dicts in `species.py` (`_MEGA_SUPPLEMENTS`, `_MEGA_ABILITY_SUPPLEMENTS`), and
several typings were wrong (surfaced while chasing a Basculegion→Crabominable
under-prediction: the data said Crabominable-Mega was Normal/Dragon).

- New data file `data/champions_megas.json` (76 megas, same schema as the slim
  species file: types/stats/`abilities`). `species.py` loads it in `_load`
  alongside the slim file; the two hardcoded dicts and the `ability_of`
  mega special-case are **deleted** — megas now resolve through the same
  `get_species`/`types_of`/`base_stats`/`ability_of` path as every base species.
- Typings corrected against the authoritative Smogon/Serebii Champions dex:
  Crabominable-Mega Normal/Dragon→**Ice/Fighting**, Hawlucha-Mega
  Fighting/Ice→**Fighting/Flying**, Drampa-Mega Grass/Fire→**Normal/Dragon**,
  Meowstic-F-Mega Fighting/Flying→**Psychic**, Scovillain-Mega
  Rock/Poison→**Fire/Grass**. Stats/abilities were already correct.
- `tools/move_coverage.py` updated to enumerate megas via `all_species()`.
- Turn-1 snapshot unchanged (none of the 5 retyped megas alter a turn-1
  decision); full suite green.

### De-hardcode Fake-Out / TR / Tailwind setter sets (data-derived)

The three species frozensets (`_FAKE_OUT_USERS` in engine.py, `_TR_SETTER_SPECIES`
/ `_TAILWIND_SETTER_SPECIES` in modules.py) were hand-maintained and had drifted
out of date (e.g. Fake Out was missing Scrafty). Replaced with a single data-layer
helper `data.population_move_users(move, min_pct)` — the **population-weighted**
(by `raw_count`, aggregated per `base_forme`) set of species running a move ≥ a
threshold — so the sets are complete and self-update with the usage stats.

- `_FAKE_OUT_USERS = population_move_users("Fake Out", 30.0)`,
  `_TR_SETTER_SPECIES = (… "Trick Room", 40.0)`,
  `_TAILWIND_SETTER_SPECIES = (… "Tailwind", 20.0)`. Thresholds are the only
  remaining tuning knobs.
- Behavior deltas vs the old hand lists, all correct: **+Scrafty** (Fake Out, was
  missing); **−Gengar** (TR, pop-weighted <40% — Gengar-Mega ~0% TR, per the
  0.7.6 audit); **−Vivillon-Fancy/-Pokeball** (TW cosmetic formes with no
  qualifying usage; base Vivillon still qualifies).
- Turn-1 snapshot byte-identical; full suite green (incl.
  test_no_mega_entries_in_species_sets — derived sets are base-name keyed).

### Apply our mega ability to OUTGOING damage (offense), not just incoming

Our offense damage calcs read the **base-paste** ability (`tm.ability`), so a
mega attacker's mega ability never boosted its own moves — Metagross-Mega's
Tough Claws (+30% contact) was applied to the hits it *took* (incoming used the
mega-aware helper) but not the hits it *threw*. Surfaced by a cluster of
Metagross Psychic Fangs **under**-predictions (Toxapex 60→92, Annihilape
72→100, …) — the live calc used Clear Body.

Systematic fix (not site-by-site): generalised `_our_ability_for_damage(tm,
species, designated_mega)` into the **single source of truth** for our-side
damage-calc abilities, and routed *every* such read through it — both offense
loops, the incoming loop, the SwitchModule current-mon offense, and the bench
calc. Eliminates raw `tm.ability` reads in damage contexts (mirrors the
`_our_item` unification). The turn-order *speed* combatant is intentionally
separate (it prefers the live revealed `mon.ability`).

Turn-1 snapshots regenerated: baseline & meta-team@v1 shift (Aerodactyl-Mega
Tough Claws now boosts Dual Wingbeat / Ice Fang — Ice Fang→Garchomp becomes the
4×+Tough-Claws OHKO it actually is); meta-team@v2 / off-meta-team@v1 unchanged
(no offensive mega ability). 1836 pass.

### Record opponent formes explicitly (durable fix for snapshot unreliability)

Root-cause fix for the recurring "opponent snapshots are unreliable" issue
(stale formes / transient formes missed because snapshots are decision-time
only). The parser now accumulates every opponent forme that appears —
switch-ins and mega/forme changes (`|detailschange|`) — into
`BattleState.opp_formes_seen`, and the recorder writes it as `opp_formes` on the
game log. This is a reliable record independent of the decision-time snapshots
(which can miss e.g. a mega that evolves and is KO'd the same turn).

`opp_mega_breakdown` now prefers `opp_formes` when present, falling back to the
snapshot/event/target triangulation for pre-0.22.0 logs. Tests:
`TestOppFormesSeen` (parser), `test_prefers_explicit_opp_formes_field` (report).

### Report: fix defensive forme-reconciliation + disposition labels

Two `tools/accuracy_report.py` defensive-accuracy fixes (report-only):
- **Forme reconciliation** (`_same_line`): an event was matched to its
  prediction (pin) via `base_forme`, which strips only `-Mega` — so a move we
  *did* assess under one inferred forme was falsely flagged "unassessed" when
  the mon turned out to be a different same-species forme (assessed
  Floette-Eternal, actual Floette-Mega). `_same_line` reconciles same-species
  formes (now correctly a small *gap* from the Eternal-vs-Mega stat mismatch,
  not a phantom coverage hole) while keeping competitively-distinct formes
  (regionals, Rotom-Wash vs -Heat) separate.
- **Disposition labels**: split the "unassessed" accept into *attacker not
  active at our decision (switched in)* vs *move below usage cutoff* — the
  former (e.g. the Aerodactyl case, an opponent switch-in we can't predict) was
  previously mislabeled as off-meta tech.

### Handle `|swap|` (Ally Switch) — fix opponent active-slot desync

The parser had **no `|swap|` handler**, so Ally Switch (which exchanges a side's
two active slots) was silently ignored: `opp_actives` kept the stale slot order
for the rest of the game. Surfaced by a defensive-accuracy "unassessed move"
(opp Aerodactyl's Dual Wingbeat) that traced to the parser tracking Aerodactyl
in the wrong slot — showing a stale Raichu-Mega-Y where Aerodactyl actually was
— after a Cofagrigus Ally Switch. Every downstream slot read (targeting,
incoming-threat assessment, the recorded pin) then tracked the wrong Pokémon,
and the bot was making live decisions against a wrong board.

- `BattleParser._on_swap` exchanges the side's two active slots (and the
  parallel per-slot arrays — last-moves, and disabled/encored for our side).
  Idents are stored slot-letter-stripped, so a slot is a list position; the swap
  is a positional exchange. Registered `"swap"` in `_HANDLERS`.
- Regression tests in `TestAllySwitch`.

### Unify own-side item reads behind `_our_item`

Folds in the 0.21.x follow-ups (no version bump until now): a single
consumption-aware `_our_item(mon)` replaces three inconsistent item-read
patterns (the speed path's missing consumed-check was the 0.21.0 scarf-speed
bug class), and the dead team-paste fallback was removed after a tripwire proved
it unreachable live (the parser repopulates `mon.item` from every `|request|`
before any decision). Test fixtures now populate `mon.item` like `from_request`
does, exercising the live read path. No behavior change for the current roster.

## 0.21.0 — 2026-06-20

### Normalize our own item/ability IDs from the request (scarf-speed bug)

Root-caused by pulling **all 26** Garchomp turn-order under-predictions from the
logs (not guessing): our scarf Garchomp was ranked pos 2-4 even against slow
opponents it clearly outspeeds. Cause: the `|request|` JSON gives our own
**item and ability in Showdown ID form** (`"choicescarf"`, `"roughskin"`), and
`Pokemon.from_request` stored them verbatim — but every lookup is keyed by
**display name** (`speed_multiplier("Choice Scarf")` = 1.5, `("choicescarf")` =
1.0). `_our_combatant` reads `mon.item` first, so **Choice Scarf was never applied
to Garchomp's speed** (modelled 151, not 226) → systematic under-ranking. The
0.16.0 scarf regression test passed only because it used the display-form
`tm.item`, masking the live ID-form path.

Same class of bug for abilities (Unburden / weather-speed / Adaptability) on our
own mons, and any damage-relevant item we might run (Life Orb/Choice Band — none
on the current team, so latent there).

- `data.item_name_from_id` / `data.ability_name_from_id`: reverse ID→display
  lookups built from the items/abilities DBs.
- `BattleParser._normalize_member_ids` applied at both `from_request` sites
  (team preview + per-turn rebuild) → `mon.item`/`mon.ability` are display names.
- Verified: a request-built Choice Scarf Garchomp now resolves to 226 speed.

Turn-1 baselines byte-identical (snapshots are synthetic and use display-form
team data, never the request) — header-only bump. Tests: request normalization
+ ID→name maps.

## 0.20.0 — 2026-06-20

### Handle `-clearnegativeboost` (White Herb) — offense mis-model fix

From the offensive misread triage: our Sneasler's Close Combat into Scrafty was
*under*-predicted (60% vs 93% actual) because Sneasler sat at a stale `atk -1`.
The parser handled `-clearboost`/`-clearallboost` (Haze/Clear Smog) but not
`-clearnegativeboost` — the message Showdown sends when **White Herb restores
stat drops** (an Intimidate −1, or Close Combat's self −Def/−SpD) and is
consumed. So the −1 lingered and dragged down every fact that read our boosts.

- `BattleParser._on_clearnegativeboost`: reset only the *negative* stat stages
  (positives untouched), mirroring `_on_clearboost`.
- **And** when it came `[from] item:` (White Herb), mark the item consumed — White
  Herb is single-use and losing it triggers **Unburden** (×2 Speed), which
  Showdown signals via this message (not always a separate `-enditem`). So e.g.
  Incineroar Intimidates our Sneasler → White Herb restores Atk *and* is spent →
  Sneasler is now correctly modelled as Unburden-fast.
- Verified: clearing the stale −1 raises the Sneasler→Scrafty prediction from
  60% toward ~91% (actual 93%).

Note: the synthetic turn-1 snapshot scenario doesn't run the parser or apply
Intimidate, so it neither sees this message nor models the Intimidate→White
Herb→Unburden chain — hence its baselines are unaffected. That chain only fires
in live play (a possible future scenario-generator enhancement).

Engine behaviour change (mid-game boost state); turn-1 baselines byte-identical
(no negative boosts at turn 1) — header-only bump. Parser test added.

## 0.19.0 — 2026-06-20

### Model Rage Fist hit-scaling (defensive mis-model fix)

From the misread triage: incoming Rage Fist (Annihilape) was badly
under-predicted (e.g. 50% predicted vs 95% actual into Basculegion) because we
treated it as a flat 50 BP. Rage Fist's power is 50 + 50 per time the user has
been hit this field stint (cap 350) — structurally identical to the already-
modelled Last Respects (50 + 50×fainted-allies), so it reuses that plumbing.

- `Pokemon.times_hit` (battle_state): per-stint hit counter, reset on switch
  (new object) — matches the Reg M-B "loses stacks on switch-out" rule.
- Parser increments `times_hit` exactly where it already attributes move-damage
  to a target (`_apply_hp_update` pending-event block), so residual / weather /
  item damage (no pending move) isn't counted.
- `damage.py`: Rage Fist power = `50 + 50×min(times_hit, 6)`; `times_hit` threaded
  through `full_damage_calc` / `incoming_damage` (`opp_times_hit`) / `outgoing_damage`,
  mirroring `ally_faint_count`. The engine passes `opp.times_hit` in the incoming
  fact loops.
- Verified: at `times_hit=1` the model now predicts 98% (was 50%) for the logged
  Annihilape → Basculegion case (actual 95%).

Turn-1 baselines byte-identical (no mon has been hit at turn 1 → flat 50 BP) —
header-only bump. Tests: Rage Fist BP scaling + cap; parser increment on a
damaging move and reset on switch.

## 0.18.0 — 2026-06-20

### `tools/team_report.py` — combined roster + prediction-accuracy report

Elevates the ad-hoc per-team analysis into a reusable, team-agnostic tool that
you **point at a logs directory** (or glob), optionally filtered to one named-team
version, and that emits **GitHub-flavoured Markdown** (`--out report.md`):

- **ROSTER** — per-mon bring rate, lead rate, win-rate-when-brought, KOs dealt,
  faints, net (KO − faint).
- **MOVE USAGE** — times each move was chosen per mon; least-used flagged as a
  swap candidate.
- **GAME LENGTH** — W/L bucketed by turn count (win-fast / lose-long signal).
- **PREDICTION** — offense / turn-order / defensive accuracy, reused verbatim.

The report is self-documenting: it auto-derives the team name/version from the
log paths, embeds the verbatim team paste (`teams/<name>/<tv>.txt`), and stamps
the engine version(s) read from the logs. A rendered sample is checked in at
`reports/meta-team_v2_0.17.0.md`.

`accuracy_report.py` refactored (no behaviour change) to expose
`compute_prediction(games, slop)` (data) + `prediction_report` (console) and
`_load(version, team_version=None)`, so the new tool composes the analysis with
zero duplication. `team_report.py` takes a path (`Battle Data/0.17.0`, any folder
of logs, or a glob), `--team`, `--slop`, `--out`. Pure helpers
(`load_games` / `roster_stats` / `move_usage` / `length_buckets`) are covered by
`tests/test_team_report.py`.

Engine unchanged — turn-1 baselines byte-identical (header-only bump).

## 0.17.0 — 2026-06-19

### Our stat-stage boosts now survive the per-turn request rebuild

Root-causes the offense-accuracy finding: across the 0.13.0 50-game run, our
moves were **over-predicted ~36:4** over vs under, and our actives recorded a
stat boost **zero times in 50 games** despite 77 turns facing an Intimidate user
(opponent boosts logged fine).

Cause: `BattleParser._rebuild_team` rebuilds `my_team` from the `|request|` JSON
every turn, and the request carries no stat stages — so an Intimidate −1 Atk (or
an opponent Rock Tomb −1 Spe) set via `-unboost` was **silently wiped before the
decision read it**. The engine therefore modelled our offense un-Intimidated and
systematically over-estimated our damage (picking attacks that fell short and
under-valuing Protect/switch).

- `_rebuild_team` now carries `boosts` forward by ident (like `item_consumed`).
  On an actual switch-out `_on_switch` replaces the entry with a fresh
  (empty-boost) object via `_update_or_add`, so a benched mon never drags stale
  stages back onto the field.
- Regression test `test_our_boosts_survive_request_rebuild`.

No turn-1 baseline change (the snapshot scenario builds `BattleState` directly,
bypassing the parser) — header-only bump. Residual offense over-predictions
(bulky spreads, Friend Guard, etc.) are smaller and need a fresh-log sample to
re-measure now that the dominant cause is fixed.

## 0.16.0 — 2026-06-19

### Forme-name resolution: one resolver, two jobs (kill the recurring mismatches)

Root-causes the recurring forme-name bugs (Pyroar ability, scarf Garchomp, the
accuracy-report `_base` bandaid, base/-Mega set duplication). `mon.species` is
the raw protocol name (base before `|detailschange|`, mega after), and the
codebase resolved forme identity three incompatible ways. Now there are exactly
two, with clear roles, and nothing keys off raw `mon.species` for modelling.

- **`_assumed_species` (inference) stays and is the only modelling answer** — a
  pre-mega mon is still assumed to become its mega forme (Fire Mane Pyroar,
  Drought Charizard, scarf-band speed, etc.).
- **`data.base_forme(name)` (new) is the single identity normaliser** — strips
  the mega suffix for membership/matching only, never a modelling choice.
- **Membership predicates** `_is_fake_out_user` / `_is_tr_setter` /
  `_is_tw_setter` = `base_forme(_assumed_species(mon)) in <SET>`. The three
  species sets are now **base-names-only**; the hand-listed `-Mega` duplicates
  (the old bandaid) are gone, and `test_no_mega_entries_in_species_sets` keeps
  them out.
- **Switch-eval / speed-history / pin-log** now route through the canonical
  helpers: `_observe_speed_from_history` matches actor↔active via `base_forme`;
  the `pin` log keys by the assessed forme (`_offense_species`); and
  `tools/accuracy_report.py` reconciles `pin`↔`ev` via `data.base_forme` instead
  of a private `_base` copy.
- **Dead-code removal:** the superseded `SwitchModule._infer_threat_types` and
  `_worst_effectiveness` (old type-matchup helpers, no live caller) and their
  tests are deleted; orphaned `types_of` / `type_effectiveness` / `move_type`
  imports dropped. `team_preview._mega_base_name` now delegates to `base_forme`
  (keeping its local `-Eternal` case).

No behaviour change: the old base/-Mega duplication already covered the live
megas, so **all turn-1 baselines are byte-identical** (header-only bump). Net
−1 module helper, −3 stale tests, +6 guard/predicate tests.

## 0.15.0 — 2026-06-19

### Damage-model gaps from the defensive-accuracy audit

The 0.13.0 prediction-accuracy audit (`tools/accuracy_report.py`) surfaced
recurring defensive under-predictions tracing to four unmodeled move mechanics.
Three were genuine code gaps (now fixed); the fourth was already correct in HEAD
and is now pinned by a test.

- **Body Press uses the user's Defense** (`damage.py`): mirrors the existing
  Foul Play special-case — `A = attacker_stats["def"]` (and the user's Def stat
  stages) for Body Press, instead of the (often low) Attack. Fixes e.g.
  Corviknight Body Press → Aerodactyl (was under by ~22%).
- **Freeze-Dry is 2× vs Water** (`damage.py`): `type_effectiveness` has no move
  context, so the Water component is patched after the fact (×4 on the normal
  ×0.5 Ice contribution). Fixes Ninetales-Alola Freeze-Dry → Basculegion (was
  under by ~27%).
- **Knock Off +50% vs an item holder** (`damage.py`): ×1.5 power when the target
  holds a removable item. Fixes Malamar-Mega Knock Off → (scarf) Garchomp (was
  under by ~33%). Unremovable edge cases (Sticky Hold, own Mega Stone) not
  modelled — small over-prediction at worst.
- **Fire Mane forme** (no change): `_effective_ability` already resolves a
  pre-mega Pyroar → Pyroar-Mega → Fire Mane (+50% Fire); the 0.13.0 log
  under-prediction predated that. Locked with a regression test.

**Turn-1 baselines:** `baseline` / `meta-team@v1` byte-identical (header-only).
`off-meta-team@v1` has **5 approved cell changes**, all our mon vs a Weavile
lead: the boosted Knock Off makes Weavile a real threat to our item-holders, so
the engine now switches to a safe pivot (Gallade) / Protects instead of throwing
a near-worthless attack. Reviewed and approved before regeneration.

## 0.14.0 — 2026-06-19

### Burn now halves physical damage

Fixes a long-standing gap: `full_damage_calc` hard-coded `burn = False`, so a
burned physical attacker was modelled at full power. Both damage facts
(`incoming_damage` / `outgoing_damage`) already thread the attacker's status
through, so the fix is a one-line gate in the Physical branch.

- **Physical branch** (`damage.py`): `burn = (attacker_status == "brn" and
  attacker_ability != "Guts")` → ×0.5 applied in `calc_damage`. Guts is exempt
  (it negates the Attack drop; its ×1.5 already lives in `atk_modifier`), and
  the Special branch keeps `burn = False` (burn never touches special damage).
- Affects mid-game incoming/outgoing damage facts where a status is in play;
  **turn-1 baselines byte-identical** (no statuses exist at turn 1) — header-only
  bump.
- Regression tests: `TestBurnPhysicalHalving` (physical ×0.5, special unaffected,
  non-burn status unaffected, Guts negation).

## 0.13.0 — 2026-06-18

### Battle-log observability + prelim M-B usage seeded from logs

No decision-logic change (turn-1 baselines byte-identical apart from the version
header). Adds the data plumbing to bootstrap Reg M-B opponent inference from our
own recorded games until Smogon M-B usage stats land.

- **Recorder logs the two speed modifiers** (`recorder.py`): each turn now carries
  `tw` (tailwind per side) and each active carries `b` (non-zero stat boosts).
  These are exactly what's needed to normalise observed turn order into a clean
  speed estimate offline (without them, our own Aerodactyl Tailwind silently
  corrupts the read). Schema in `docs/BATTLE_LOG_SCHEMA.md`.
- **`tools/seed_supplement_from_logs.py`** (new): mines `Battle Data/**/*.json`
  for opponent **moves** (revealed `opp[].mv`, merged by base species) and
  **teammates** (from the recorded `preview` sheet), and seeds them into
  `data/sets_supplement.json` for the new M-B mons. Guarded so a sparse sample
  can't mislead: only species seen ≥3 games AND with ≥1 observed damaging move
  (others stay on the safe synthetic-STAB fallback); idempotent via a `_seeded`
  marker. Items/abilities/spreads are not in the logs and stay on fallback.
- **Seeded 12 forme entries** from the 50-game M-B run (Staraptor/-Mega,
  Grimmsnarl, Swampert/-Mega, Sceptile/-Mega, Gholdengo, Metagross/-Mega,
  Raichu-Mega-X/Y) — moves + teammates.
- **Backlog**: turn-order → raw-speed estimation (now unblocked by the `tw`/`b`
  logging; would seed `spreads` and could wire the dormant `update_speed_belief`
  live), and accept/record Open Team Sheets (the path to real items/abilities).

## 0.12.0 — 2026-06-18

### Observation-driven item inference (prior + evidence)

The 0.11.0 modal item belief was a *static* prior — it never updated when battle
events contradicted it (a Garchomp assumed Choice Scarf stayed "scarfed" even
after it was outsped or used two moves). Split the belief into the usage-stats
**prior** and observed **evidence**, resolved at lookup. General and extensible:
a new rule is one parser signal + one ruled-out item set.

- **`ItemEvidence`** (battle_state.py) — per-opponent evidence keyed by normalized
  ident on `BattleState.opp_item_evidence`. Survives switches (the Pokemon object
  is replaced by `_update_or_add` on every pivot, wiping its `moves`/`item`).
  Holds `confirmed` (proven held), `consumed` (game-scoped, ≠ Unburden's
  field-stint `item_consumed`), `ruled_out`, and `stint_moves`.
- **Rules wired in the parser** (battle.py):
  - **≥2 distinct moves in one field stint → rule out all Choice items**
    (`CHOICE_ITEMS`). `stint_moves` resets on switch (a Choice lock frees on
    pivot); Struggle is excluded.
  - **Outsped when even the slowest scarfed spread would be faster → rule out
    Choice Scarf** (`_observe_speed_from_history` in modules.py, run once per turn
    from `build_turn_context`; reuses `will_outspeed`). Conservative — only fires
    on an undistorted same-bracket comparison, never a false clear.
  - **`[from] item: X` on damage/heal → confirm X** (Life Orb recoil, Black
    Sludge, Leftovers, Rocky Helmet — holder is the `[of]` source if present).
  - **`-item` reveal → confirm**; **`-enditem` → consumed**. Own-side events
    ignored (we know our items).
- **Resolution** (`_effective_item`): held-now > consumed → None > confirmed >
  field-stint consumed > prior with `ruled_out` removed. `_assumed_item` walks
  the usage list skipping ruled-out items; the 25% bar gates **only the literal
  top item** (pure prior), and once a higher-usage item has been ruled out it
  **commits to the next-most-likely unconditionally** (observation narrowed the
  field — e.g. Garchomp with Choice Scarf ruled out → Sitrus Berry at 16.5%).
- Turn-1 / empty-evidence behaviour is unchanged, so the snapshot baselines are
  byte-identical apart from the version header. Full suite green (+17 tests).

## 0.11.0 — 2026-06-18

### Unified, modal item inference (speed + damage share one belief)

Item assumption was fragmented: damage used a modal `_effective_item` (top-usage
≥40% else None), while speed carried its own probabilistic Choice-Scarf branch
baked into `speed_distribution`, and a dead `scarf_probability` helper lingered.
Generalized everything onto one modal belief and one effect table.

- **`data/speed_tiers.py`** — `speed_distribution` is now a pure **spread**
  distribution. Removed the scarf branch, the `scarfed` field, `_SCARF_*`
  constants, `scarf_adjusted_speed`, and the `item_distribution` dependency.
  Item/field effects are applied downstream, not baked into the prior.
- **`turn_order.py`** — `_apply_modifiers` takes a single `item` arg and applies
  `data.items.speed_multiplier(item)` (Choice Scarf ×1.5, Iron Ball / Macho Brace
  ×0.5); dropped the scarf-filter and the `_SLOW_ITEMS` set.
- **`decision/modules.py`** — `_opp_combatant` now passes `item=_effective_item(mon)`
  (the modal assumed item), so the speed and damage pipelines share one item
  belief instead of two.
- **Item-effect handling generalized** (no behavior change on its own):
  `data/items.py` gained `type_boost_multiplier`; `damage.py` and `turn_order.py`
  now consume the `data/items.py` tables instead of per-item `elif` chains.
  Gems removed from `TYPE_BOOST_ITEMS` (one-time consumables, not modeled).

### Item-assumption threshold lowered 40% → 25%

Assuming **no item** is not neutral — it is the *optimistic* read (no Choice
Scarf making a threat faster, no Focus Sash surviving our KO, no Life Orb /
type-boost on incoming hits). At the 40% floor, 63/245 species fell through to
None, 34 of them with a *consequential* plurality item. Lowered the floor to
**25%** (`_ASSUMED_ITEM_MIN_PCT`) so a clear plurality is committed to; only the
flattest distributions still assume None. Bias flips from optimistic to
conservative: e.g. an unrevealed Garchomp (Choice Scarf 27.9%) is now assumed
scarfed, so we play around it rather than into it.

- Turn-1 snapshot diff: **180 / 740 cells** shift (168 weight-only turn-order /
  damage-magnitude changes; 12 move/target flips, all opponents-now-assumed-Scarf
  → Protect/switch instead of attacking into a faster mon). Reviewed + spot-checked
  before regeneration. Regenerated `baseline.md`, `meta-team@v1.md`,
  `off-meta-team@v1.md`.
- Clamped `prob_outspeeds` / `prob_faster_than` to [0,1] (float overshoot exposed
  once the dominant-side mass was no longer split by a scarf branch).

## 0.10.0 — 2026-06-17

### Regulation M-B support — 38 new species, 6 moves, 2 abilities

The new Champions regulation (M-B) released today; folded its additions into the
data layer (sourced from Serebii's Champions Pokédex, spot-checked by the user).

- **22 base forms** → `smogon_champions_slim.json` (Vileplume, Sceptile, Blaziken,
  Swampert, Mawile, Metagross, Staraptor, Gholdengo, Annihilape, Grimmsnarl, …).
- **16 mega formes** → `_MEGA_SUPPLEMENTS` (stats/types) + `_MEGA_ABILITY_SUPPLEMENTS`
  (ability) in `data/species.py`: Raichu-Mega-X/Y, Sceptile/Blaziken/Swampert/
  Mawile/Metagross/Staraptor/Scolipede/Scrafty/Eelektross/Pyroar/Malamar/Barbaracle/
  Dragalge/Falinks-Mega.
- **6 signature moves** → `champions_moves.json`: Make It Rain (M-B: 95% acc, user
  SpA −2), Rage Fist (flat 50 BP — hit-count scaling not modeled, see BACKLOG),
  Barb Barrage, Spirit Break, No Retreat, Spin Out.
- **14 mega stones** → `champions_items.json` (Raichunite X/Y already present).
- **2 new official abilities** wired in `damage.py`: **Fire Mane** (+50% Fire,
  like Transistor) and **Eelevate** (Ground-type immunity, like Levitate; its
  on-KO highest-stat boost is Beast-Boost-style and left unscored). Both also added
  to `champions_abilities.json` (along with 8 standard abilities the curated subset
  was missing).
- **`tools/move_coverage.py`** (new): cross-references each mon's top-usage moves
  against the move DB. Confirms zero move-data gaps for mons that have usage; lists
  the 38 new mons that need hand-compiled usage (Smogon M-B stats land ~July).

No usage data exists for the new mons yet, so opponent moveset inference and the
mega stone→forme mapping for them are deferred (tracked in BACKLOG). Engine
behaviour for existing mons is unchanged: the baseline turn-1 snapshot diff is the
header version line only (120 decision rows byte-identical). Full suite green.

## 0.9.0 — 2026-06-16

### Named teams + A/B data separation

Adds a **team-name / team-version** axis, independent of the engine version, so
team A/B tests no longer mix in the battle-data folder or ELO log.  Three axes
now: engine version (`version.py`), **team name** (a distinct roster, bound to
**one account**), and **team version** (roster iterations A/B'd on the **same**
account).  See `teams/README.md`.

- **`teams/<name>/v<n>.txt`** pastes + **`teams/teams.json`** manifest (name →
  `label`, `account`, `current` version).  Seeded `meta-team/v1` from `team.txt`
  (byte-identical) and an empty `off-meta-team` slot.
- **`team.py`** — active-team selector (`set_active_team` / `get_team`), manifest
  readers (`list_teams`, `team_versions`, `current_version`, `team_account`,
  `team_label`), `resolve_team_spec` (`name` / `name@vN`), `validate_team`.  With
  no team selected, `get_team` falls back to the `team.txt` **frozen baseline** —
  so `turn1_summary.md` and every decision test are unaffected.
- **`recorder.py`** — `BattleRecorder(id, version, team=None, team_version=None)`
  files battles under `Battle Data/<version>/<team>/<team_version>/` and tags the
  payload, **only when set**; the legacy 2-arg call stays flat + untagged.
- **`main.py`** — `--team` / `--account` / `--list-teams` / `--max-games N`.
  Account profiles via `bot_secrets.PROFILES`; an explicitly-bound account with
  no usable creds **refuses to run** (no wrong-account laddering).  ELO entries
  gain `team` / `team_version` / `username` tags.  `--max-games N` makes the bot
  **shut itself down** after N completed games (run control only — zero effect on
  decisions/scoring), so a bounded test run can't keep laddering unattended.

**Audit hardening** (post-feature review, no decision impact):
- **Login failure on a named-team run now aborts** instead of falling back to
  guest — a wrong account password was silently guest-playing and saving the
  game mis-tagged as that team's data.  The baseline (no `--team`) keeps the
  legacy guest fallback.
- **Single source of truth for the active team**: dropped the duplicate
  `main.ACTIVE_TEAM` globals; the recorder + ELO tag sites read
  `team.active_team()` / `active_team_version()` directly.
- **`--list-teams` now validates the account binding** (flags `[NO CREDS]` when
  a team's profile has no credentials), the manifest is cached for the process,
  and the resolution/selector tests run against a temp fixture `teams/` dir so
  they no longer break when real rosters are added/renamed.

Engine behaviour unchanged: `turn1_summary.md` diff is the header version line
only (all 120 decision rows byte-identical).  Tests: `tests/test_teams.py`
(fixture-based) + `TestNamedTeamPath`.  Full suite 809.

## 0.8.12 — 2026-06-14

### Mega-evolution refreshes the ability (systematic)

`_effective_ability` returned a *revealed* ability directly — but mega-evolution
**replaces** the base ability, so an ability revealed *before* a mon megas is
stale.  Altaria reveals Cloud Nine / Natural Cure pre-mega; once it megas it's
**Pixilate**, but we kept the base ability, so its Hyper Voice stayed Normal-type
and we under-predicted incoming by ~50% (50-game 0.8.11 sample: Altaria-Mega
Hyper Voice → Aerodactyl 12% predicted / 62% actual, → Garchomp 25% / 68%).

Fix (one place, no per-species list): for any assumed `-Mega` forme,
`_effective_ability` uses the **mega forme's** ability regardless of what was
revealed (megas carry exactly one ability).  Applies to every mega whose ability
differs from its base — Altaria/Gardevoir → Pixilate, Charizard-Y → Drought, etc.

Turn-1 table byte-identical (turn-1 opponents have no revealed ability, so the
assumed-mega ability was already used).  Tests: `TestMegaAbilityRefresh`.  Full
suite 781.

## 0.8.11 — 2026-06-14

### Garchomp spread: hit the 226 Scarf-speed benchmark

The Choice Scarf Garchomp was at `6 HP / 32 Atk / 28 Spe` (Adamant) → 150 raw →
**225** effective, one short of the intended **226** benchmark (the original
"226" was computed under the pre-0.8.0 SP formula and didn't survive the SP
fix).  Re-tuned to `5 HP / 32 Atk / 29 Spe` (Adamant) → 151 raw → **226**,
keeping max Atk; the 1 SP came from HP to stay within the 66-SP cap.

Turn-1 table byte-identical (no opponent sits at the 225/226 boundary, and
Garchomp's HP doesn't affect its own offense scoring) — the extra point matters
mid-game in a Scarf-speed mirror.  This is the regenerated baseline. Full suite
778.

## 0.8.10 — 2026-06-14

### In-battle forme stats: Palafin-Hero and Aegislash stance

The species data only carries each Pokémon's **base** forme stats — the
suffix-strip fallback in `get_species` returned base stats for transform formes,
so `Palafin-Hero` was modelled with Zero-form **Atk 70** (real Hero is **160**)
and `Aegislash-Blade` with Shield's **50/140** (backwards from Blade's 140/50).
This is why the 50-game sample showed Palafin-Hero Wave Crash → Garchomp at
55% predicted / 86% actual.

- **`data.species._BATTLE_FORME_STATS`** — correct base-stat overrides for the
  Champions-legal stat-changing battle formes, consulted by `base_stats` before
  the generic lookup: `Palafin-Hero` (100/160/97/106/87/100) and
  `Aegislash-Blade` (60/140/50/140/50/60).  Types and base Speed are unchanged,
  so only stats are overridden; usage *spreads* still resolve to the base name.
  Palafin is fully fixed by this — it's revealed as `Palafin-Hero`, so the right
  stats just flow through (now Atk ~233 vs the old ~134).
- **Aegislash stance** (`_offense_species` / `_defense_species` in modules.py):
  Stance Change is dynamic (Blade when it attacks, Shield when it defends) and
  we can't know the live stance, so the safe/simple rule — **always Shield for
  the damage it receives, always Blade for the damage it deals** — is applied at
  every damage fact site (incoming → Blade attacker stats; outgoing → Shield
  defender bulk).  Keyed off the base name, so a revealed `Aegislash-Blade`
  still resolves both ways.  Non-stance species pass through unchanged
  (mega-forme inference preserved).
- Tests: `TestBattleFormeStats` (data) + `TestStanceForme` (modules).  Turn-1
  table byte-identical (neither species is a turn-1 lead).  Full suite 778.

## 0.8.9 — 2026-06-14

### Assume the weather an active weather-setter brings

The engine modelled an assumed Charizard's *movepool* (Mega-Y) but not its
*weather* — it computed incoming damage with `state.weather` (often None on the
turns that matter), so a Drought-Mega-Y Charizard's Weather Ball scored as a
feeble Normal 50 and its Heat Wave missed the sun boost.  Measured gap vs our
Sneasler: **Weather Ball 30% → 131% (OHKO), Heat Wave 62% → 93%** once sun is
assumed — and the 50-game 0.8.7 sample showed exactly those incoming hits
(Weather Ball → Sneasler ~100%).

- **`_assumed_weather(state)`** (modules.py): observed `state.weather` always
  wins; otherwise assume the weather an **active** weather-setting ability will
  put up — keyed off the assumed forme via `_effective_ability`, so a pre-mega
  Charizard (→ Mega-Y → **Drought**) implies sun before its `|detailschange|`
  arrives.  `Drought→sun`, `Drizzle→rain`, `Sand Stream→sand`, `Snow Warning→
  snow`.  On a **simultaneous** set, entry abilities fire fastest-first, so the
  **slowest** setter writes last and its weather sticks (ranked by base Speed).
- Threaded through **every fact site** in `build_turn_context` — both damage
  loops (Weather Ball type/power, Fire/Water modifiers, Solar Power) **and** the
  Combatant speed calc, so weather-speed abilities (Chlorophyll/Swift Swim/…)
  activate in the assumed weather on **both** sides (e.g. our Venusaur is fast in
  the sun an opposing Charizard brings).
- **Turn-1 table:** 4 decisions change (reviewed + approved), all in
  weather-setter matchups: vs rain Pelipper we now pivot to **Basculegion**
  (rain-boosted Adaptability Water) instead of Kingambit / instead of a weak Rock
  Tomb (1.20, 4.20, 6.20); vs sun Charizard, Garchomp goes for the 4× Rock Tomb
  while Kingambit Protects the now-correctly-lethal spread Heat Wave (3.17).
  Plus 3 weight-only shifts on Charizard/sun cells.  Summary + 120-row
  `test_turn1_decisions.py` table regenerated.  Full suite 773.

## 0.8.8 — 2026-06-14

### DamageOutput: weight a move by how much of the job it does

`DamageOutputModule` scored a damaging move `1 + fraction*2`, floored at ×1.0 —
so a move that threatens **~nothing** (immune / fully resisted / a dead
Choice-locked move) scored the same ×1.0 as a neutral baseline, and `TurnOrder`
×2 could still lift it above a switch.  That's why a Choice-locked Garchomp kept
firing Ground into a Levitate/Flying wall instead of pivoting (the smoke-test
finding), and a "1-damage" move would still stay in.

New formula for **damaging** moves — a single line:

    factor = 0.5 + 3.5 * fraction

- **Floors at 0.5** (a move threatening ~0): below a healthy switch (so we leave
  a useless matchup), above a suicidal one (so we don't sack a mon into an OHKO
  on entry).
- **Crosses the old 1+2f curve at ~33% damage**, so moves ≥33% keep ≈ today's
  weight (no over-switching off real super-effective chip); below that they taper
  toward the floor (switch-prone), above it they climb a little (sharpen
  "attack with the big move").
- **Status moves keep the ×1.0 baseline** (they deal 0 by design, not by
  failure) so ProtectValue / SetterUrgency / FakeOut still score them.

Verified on the dead-matchup case: a Choice-locked Garchomp vs a Ground-immune
Dragonite now **switches to a surviving bench mon** when one exists, and **stays
in (no sack)** when the only switch-in would be OHKO'd.

**Turn-1 table:** 16 of 120 decisions change (reviewed + approved): un-Protects 5
passive turn-1 double-Protects, attacks (mostly super-effective) instead of
speculative switches, and 4 "double-to-break-Focus-Sash" reshuffles on assumed-
Sash Whimsicott (defensible — secures the KO on the fast support mon).  Slope 3.5
was chosen from a sweep: it zeroes over-switching while avoiding slope-4's extra
aggression.  `turn1_summary.md` + the 120-row `test_turn1_decisions.py` table
regenerated; `TestDamageOutputModuleIntegration` updated to the new formula
(+ a guard that status moves keep ×1.0).  Full suite 773.

## 0.8.7 — 2026-06-14

### Zero-damage reason: tell an ability immunity from a Protect/miss

A move that deals 0 is no longer ambiguous.  The parser now tags the resolving
move event with *why* it dealt nothing, and — crucially — **reveals an immunity
ability** so we stop firing into an immune mon.

- **Parser (`battle.py`):** new `-immune` / `-miss` handlers and a Protect/
  Substitute tag in `-activate`.  Each sets `event["z"]` ∈
  {`immune`,`miss`,`protect`,`sub`}.  An `|-immune|…|[from] ability: X` records
  `event["za"]=X` **and sets `mon.ability=X`** on the target — a wrong assumed
  ability is exactly how we were "missing" immunities (e.g. re-Earthquaking a
  Levitate mon).
- **Recorder:** writes `z` / `za` into the battle-log `ev` events.
- **`accuracy_report.py`:** the offense filter now uses `z` — genuine
  non-connects (miss/protect/sub) are dropped, but **predicting damage on an
  immune target is surfaced** in a new "IMMUNITY MODEL GAPS" section (with the
  ability, when known).  This was the hole in 0.8.6's blunt "drop all 0%" filter
  (which could hide a wrong-ability immunity as if it were a Protect).
  Backward-compatible with logs that have no `z`.
- Tests: `TestZeroDamageReason` (immune w/ + w/o ability, miss, protect, sub,
  real-hit control).  Turn-1 table byte-identical (no immunity procs on turn 1).

## 0.8.6 — 2026-06-14

### Revealed mega stone commits to the mega forme

`_assumed_species` had a gap: a mon whose item was *revealed* to be a mega
stone (but which hadn't evolved yet) fell through to the population-weighted
forme guess, which lands on the **base** forme for base-dominant species
(Venusaur, Gyarados, Gallade, …).  Now a revealed stone resolves straight to
that stone's `-Mega` forme via the new `data.mega_forme_for_stone` (the
inverse of `mega_stones`).  Charizard/Delphox were already handled by the
population rule (their megas dominate usage); this fixes the *swing* species.

- A strict "top item ends in -ite → mega" rule was considered and rejected:
  the usage data files mega sets separately, so a base entry's top item is a
  *normal* item (Charizard → Charcoal, Delphox → Focus Sash), and that rule
  would send them to base — the opposite of what we want.  Population count
  remains the rule when the item is unknown.
- Tests: `TestMegaFormeForStone` (data layer), plus a base-dominant
  revealed-stone case in `TestAssumedSpecies` (Venusaurite → Venusaur-Mega).
  Turn-1 table byte-identical (turn-1 opponents have no revealed item).

### accuracy_report.py — UTF-8 console + offense connect filter

- Force UTF-8 stdout so the report's box-drawing glyphs don't crash on the
  Windows cp1252 console.
- Offense mis-models now exclude **non-connecting** hits (actual 0% — Protect,
  immunity, substitute; misses and switch-aways already fell out), so the list
  shows only real damage-model gaps.  Misdiagnosed Delphox-Mega over-prediction
  traced to **spread calibration** (we assume the modal frail spread), not
  forme — a separate backlog item.

## 0.8.5 — 2026-06-14

### Three damage-model fixes surfaced by the accuracy report

All in `damage.py`; turn-1 table byte-identical (no weather on turn 1, assumed
Charizard is Mega-Y not Tough-Claws Mega-X, and no turn-1 incoming fact flipped).

- **Weather Ball** now becomes the weather's type at 100 BP (rain→Water,
  sun→Fire, sand→Rock, hail→Ice) instead of a feeble Normal 50.  This was the
  rain culprit: the report flagged Politoed → Garchomp predicted 39% / actual
  100% — a rain-boosted Water Weather Ball we were modelling as Normal.
- **Foul Play** now computes damage from the *target's* Attack stat and Attack
  stat-stages, not the user's.  Fixes the Sableye → Sneasler under-prediction
  (8% → actual 24%): Foul Play hits with our own high Attack.
- **Tough Claws** ×1.3 on contact moves (e.g. Charizard-Mega-X Dragon Claw),
  via the new move-flags layer below.
- Tests: `TestWeatherBall`, `TestFoulPlay`, `TestToughClaws`. Full suite 704.

### Defensive `pin` now logs the whole assessed movepool

- The per-turn `"pin"` predicted-incoming record changed from a single
  scariest `{"mv","p"}` to a per-move map `{"mvs": {move: pred_frac}}` over
  *every* move the engine assessed for each (opponent → our mon).  This lets
  the accuracy report distinguish a genuine **model mis-calc on a move we
  assessed** from an **off-meta tech move we never considered** — so a
  defensive under-prediction can be triaged instead of guessed at.
- `tools/accuracy_report.py` defensive section now tags each case `[known]`
  (assessed move, under-rated → model gap) or `[TECH]` (unassessed move) and
  prints the actual move; backward-compatible with pre-0.8.6 single-move logs.

### Move-flags layer (`data/move_flags.py`)

- New per-move property flags — **contact / slicing / punch / bite** — as
  explicit positive sets, replacing the inverted `_NON_CONTACT_MOVES` hack.
  `move_flags(name)`, `move_has_flag(name, flag)`, `is_contact(name)`.
- **Contact is a full positive list** (178 moves over the Champions movepool —
  174 physical + the special-category contact moves Draining Kiss / Grass Knot
  / Infestation / Petal Dance), generated against `champions_moves.json` and
  the Bulbapedia contact list, so special contact moves a physical-only
  heuristic would miss are covered.  Tough Claws now keys off `is_contact`.
- **slicing / punch / bite** sets are seeded too (e.g. Kowtow Cleave + Dragon
  Claw/Shadow Claw are slicing; Ice Fang/Psychic Fangs are bite), plus
  **pulse** (Aura Sphere, Dark/Dragon/Water Pulse, Terrain Pulse), **sound**
  (Boomburst, Hyper Voice, Bug Buzz, Snarl, …) and **recoil** (Flare Blitz,
  Brave Bird, Wave Crash, Wood Hammer, …).

### Offensive-boost abilities wired into `atk_modifier`

All key off the move-flags layer above, the move's type, or its category — no
new per-attacker plumbing — so an assumed opponent carrying one has its
incoming threat rated correctly.  Turn-1 table byte-identical (no assumed
turn-1 lead runs any of them).

- **Flag-keyed:** Sharpness (×1.5 slicing), Strong Jaw (×1.5 bite), Iron Fist
  (×1.2 punch), Mega Launcher (×1.5 pulse), Punk Rock (×1.3 sound), Reckless
  (×1.2 recoil), Tough Claws (×1.3 contact).
- **Type-keyed:** Fairy Aura (×1.33 Fairy), Steely Spirit (×1.5 Steel), Water
  Bubble (×2.0 Water).  Transistor corrected to **×1.3** Electric (Champions
  reference; mainline Gen 9 is ×1.5).
- **Category-keyed:** Huge Power / Pure Power (×2.0 physical), Gorilla Tactics
  (×1.5 physical).  ×2.0 abilities land ~1.95 in practice from integer damage
  rounding — same approximation as the existing Choice-item modifiers.
- Tests: `TestFlagAbilities` extended to 16 cases (one per ability + negative
  type/category guards).  Full suite 721.
- **Deferred** (need attacker HP / status / weather / ally / turn-faint facts
  the calc doesn't yet receive): Blaze/Overgrow/Torrent/Swarm pinch,
  Flare/Toxic Boost + Guts, Sand Force, Solar Power sun-gating, Orichalcum
  Pulse / Hadron Engine, Battery/Power Spot/Plus/Minus, Slow Start, Supreme
  Overlord.

### Effectiveness / strike-count abilities in `full_damage_calc`

A second batch, applied inside `full_damage_calc` (not `atk_modifier`) because
they need the resolved type effectiveness or the move's spread status — still
no new per-attacker plumbing.  Turn-1 table byte-identical.

- **Neuroforce** — ×1.2 on a super-effective hit (`eff > 1`).
- **Tinted Lens** — ×2.0 on a not-very-effective hit (`0 < eff < 1`); leaves
  immune (`eff = 0`) and neutral/super-effective hits alone.
- **Parental Bond** (Kangaskhan-Mega) — single-target damage ≈ ×1.25 (the
  second strike at 25%), gated to non-spread moves, and its extra strike now
  **breaks Focus Sash / Sturdy** like a multi-hit move (folds into the
  `ko_prevented` guard).
- **Adaptability** was already correct (×2.0 STAB in `stab_multiplier`); **Flash
  Fire** immunity was already in `_ABILITY_TYPE_IMMUNITY`.  Still deferred to
  the plumbing batch: Analytic (move-last), Merciless (target poisoned),
  Stakeout (target switching), Flash Fire's post-hit +50%, Sniper.
- Tests: `TestEffectivenessAbilities` (6), `TestParentalBond` (4). Full
  suite 731.

### Conditional-fact abilities — attacker HP / status / weather / faint + Flash Fire

The third batch threads new *attacker* facts through the damage path
(`atk_modifier` gained `weather` / `attacker_hp_fraction` / `attacker_status` /
`ally_faint_count` / `flash_fire_active`), sourced in `build_turn_context` from
the in-scope `Pokemon` objects (`.hp_fraction`, `.status`, opponent faint
count) and forwarded through `outgoing_damage` / `incoming_damage`.

- **Pinch (≤⅓ HP):** Blaze/Overgrow/Torrent/Swarm — own-type ×1.5.
- **Defeatist (≤½ HP):** Atk & SpA ×0.5.
- **Status:** Guts (Atk ×1.5 while statused), Flare Boost (SpA ×1.5 burned),
  Toxic Boost (Atk ×1.5 poisoned).
- **Weather:** **Solar Power fixed** — was applying Fire/Electric ×1.5 in *all*
  weather; now SpA ×1.5 **in sun only**.  Sand Force — Rock/Ground/Steel ×1.3
  in sand.
- **Faint:** Supreme Overlord — Atk & SpA +10% per fainted ally (cap +50%);
  **Kingambit**, threaded for both our attacker and the opponent's.
- **Flash Fire (+50%):** new `Pokemon.flash_fire_active` flag, set by the parser
  on `|-start|…|ability: Flash Fire` (either side, resets on switch); boosts the
  holder's Fire moves ×1.5.
- **Dropped as out-of-format** (no Champions-legal holder): Slow Start
  (Regigigas), Orichalcum Pulse (Koraidon), Hadron Engine (Miraidon), Flower
  Gift (Cherrim) — so no turns-active or terrain tracking was needed.
- Tests: `TestPinchAbilities`, `TestStatusAbilities`, `TestWeatherGatedAbilities`
  (incl. a Solar-Power-no-sun regression), `TestSupremeOverlord`,
  `TestFlashFireBoost` (damage layer); `TestFlashFireActivation` (parser);
  `TestConditionalAbilityPlumbing` (Guts + Flash Fire reach the incoming facts).
  Turn-1 table byte-identical.  Full suite 762.

## 0.8.4 — 2026-06-14

### Defensive-prediction instrumentation + automated accuracy report

Pure observation — no decision change, turn-1 table unaffected.

- **Predicted incoming damage logged (`pin`).**  `build_turn_context` now
  records, per (opponent → our mon), the scariest assessed incoming hit's
  expected % — from the same `incoming_damage` it already runs for the OHKO
  facts.  Written per turn as a `"pin"` array.  Paired with the actual
  incoming `ev` damage, this makes the *defensive* model checkable (did a mon
  we thought was safe get hit harder than predicted?) — the parallel to the
  `damage_output` offensive predictions.
- **Crit flag (`cr`).**  New `|-crit|` handler marks the resolving move event
  so accuracy analysis can exclude crits; misses are excluded naturally (they
  deal no damage).
- **`tools/accuracy_report.py`** — automated report over a version's logs:
  (1) high-level stats (win rate, offense damage accuracy, defensive
  under-prediction count, turn-order accuracy), (2) a turn-order detail
  section, (3) per-case one-liners (attacker, defender, predicted, actual).
  Headline list is defensive under-predictions; offense mis-models follow.
  `--slop` configurable (default ±15%).
- Tests: crit capture + no-crit, predicted-incoming population, recorder
  `pin`/`cr` output.

## 0.8.3 — 2026-06-14

### Soften the SwitchModule tempo tax (0.6 → 0.8)

- **`SwitchModule.TEMPO_FACTOR` 0.6 → 0.8.**  Battle-log analysis (0.8.1 run)
  showed the bot grinding a 15%-into-walls attack rather than pivoting — a
  Choice-locked Garchomp threw Stomping Tantrum at a Ground-walling stall core
  (Aggron-Mega Def 230, Sinistcha resist, Pelipper immune) for ~12 turns
  because switch scores couldn't compete: a switch maxed ~0.6×(1+gain) while
  attacks stack turn-order/Tailwind/OHKO multipliers to 2–3+.  The flat ×0.6
  tax was the biggest drag.  Softening to ×0.8 keeps a gentle turn-forfeit
  cost (so switching still respects the conceded free hit) while letting a
  clearly-better pivot win.  Full removal was tested but moved 59/120 turn-1
  cells and risked over-switching; ×0.8 is the chosen middle ground.
- **41 turn-1 cells changed** — the expected switch-favoring pattern:
  gratuitous-Protect → Switch, and weak attacks → pivots into better matchups
  (e.g. Sneasler → Venusaur vs a Grass/Fairy Whimsicott).  No other tests
  affected.
- Note: this does not fix the underlying Choice-lock blindness (a locked mon
  still can't change moves and the engine doesn't model the lock) — that
  remains a backlog item; ×0.8 just makes pivoting off a bad position easier.

## 0.8.2 — 2026-06-13

### Garchomp Scarf spread rebuild + `h0` instrumentation

- **Garchomp → Adamant `6 HP / 32 Atk / 28 Spe`** (was the leftover even
  `14/13/13/-/13/13` Jolly spread from the Soft Sand build).  28 Speed SP is
  the minimum to clear the user's 224 effective-speed target — Scarf-boosted
  speed lands at **225** (224 isn't reachable: `floor(raw×1.5)` skips from 223
  to 225), with Atk maxed at 200 and 6 leftover SP into HP.  The old spread
  only reached Scarf-speed 222 *and* wasted ~37 Atk — it was never built for a
  Choice item.  **42 turn-1 cells changed**, all the expected "Garchomp hits
  harder" pattern: weight increases plus a few re-prioritisations onto
  super-effective targets (Poison Jab → Whimsicott at 4×, Rock Tomb →
  Charizard) and the partner now preferring to pivot to the stronger Garchomp.
- **`ev` events now carry `h0`** (target HP fraction before the hit), so a
  predicted guaranteed-OHKO is verifiable (`d >= h0`) and predicted-vs-actual
  damage compares on the correct remaining-HP denominator — the gap that made
  the first turn-order/damage accuracy pass unmeasurable.
- *Observed (not fixed here):* a Choice-locked Garchomp can exhaust its locked
  move's PP and be forced to Struggle in long games (confirmed: 12 Stomping
  Tantrums = its exact 12 PP, then Struggle) — a concrete failure mode of the
  unmodeled Choice-lock backlog item; the engine should switch a Choice-locked
  mon out before its move runs dry.

## 0.8.1 — 2026-06-13

### Actual move-resolution instrumentation (for prediction-accuracy analysis)

Pure observation — **no decision-making change**, turn-1 table byte-identical.
Adds the data needed to measure how often the engine is right about turn order
and damage, which the logs previously couldn't answer (only predictions were
recorded, never actuals).

- `BattleState` gains `turn_events` (the moves resolving this turn, in order)
  and `events_log` (`{turn: [events]}`).  `battle.py:_on_move` records each
  resolving move with its actor/move/target and the target's HP before the
  hit; `_apply_hp_update` attributes the resulting HP drop to that move
  (linked to the immediately-preceding `|move|`, cleared after one hit so
  residual/item damage isn't double-counted).  `_on_turn`/`_on_win` flush the
  turn's events into `events_log`.
- The recorder writes them as an optional per-turn `"ev"` array — actual
  order (`o`), side (`sd`), actor (`a`), move (`mv`), target (`tg`), and
  observed damage fraction (`d`).  Paired with the existing prediction reason
  strings (`damage_output: …% HP`, `turn_order: pos X/4`, guaranteed-OHKO),
  this makes turn-order and damage accuracy directly computable.
- Known approximation: a spread move hitting two targets records damage for
  the first only; switches aren't recorded as events (only `|move|`).
- Tests: `TestMoveInstrumentation` (parser capture, order, damage, flush,
  residual-not-attributed) and `TestMoveEventsInLog` (recorder output).

## 0.8.0 — 2026-06-13

### SP→stat formula correction (major) + Choice Scarf Garchomp

**Stat-calc bug fix — the biggest correctness change in the project.**
The Champions format replaced EVs with Stat Points (66 total, 32/stat cap).
`data/stat_calc.py:sp_to_ev_quarter` used an unverified placeholder mapping
(`1 SP = 1 floor(EV/4) unit`), which undercounted every invested stat by
roughly half — for **both our team and all opponents**, since the same
chokepoint feeds team.txt and the usage-data spreads.

- **Correct mapping (confirmed three ways): `32 SP = 252 EV`**, i.e.
  `1 SP = 7.875 EV`, so the formula's `floor(EV/4)` term is
  `floor(SP × 7.875 / 4) = floor(SP × 1.96875)` (a maxed stat → term 63, as
  252 EVs gave in the base game).  Confirmed by: (1) multiple Champions web
  sources, (2) the format's stat reference, and (3) an **empirical match
  against Showdown's own HP values** for all six of our mons (the old code
  produced 163/191/171/211/171/190; real values are 171/206/187/227/187/197 —
  the fix reproduces all six exactly).
- One-line change in `sp_to_ev_quarter`; the whole stat / damage / speed /
  turn-order pipeline inherits it.  No other stat math exists in the engine
  (single chokepoint, audited).
- **Test fallout (all reviewed):** turn-1 table re-priced (110 cells changed,
  ~13 true decision flips); `TestUpdateSpeedBelief` threshold 140→150 (Garchomp
  speeds rose, old threshold filtered nothing); `test_ko_before_acting_blocks_
  undeliverable_kill` pins Soft Sand on Garchomp to keep its doom-gate scenario
  valid (the new Scarf set outspeeds Weavile).

**Team change: Garchomp → Jolly Choice Scarf, Protect → Rock Tomb.**
Garchomp was the worst performer over the pooled 195-game sample (48.5% when
brought vs 54.3% without) and the team's worst archetype is rain/Tailwind —
opposing speed control.  Scarf (Garchomp → 211 spe) flips most of the rain
core (outspeeds Archaludon, rain Pelipper, rain Dragonite) and Rock Tomb adds
a 4× answer to Talonflame/Charizard.  Protect dropped because the engine does
not model Choice lock-in (open backlog item) and could otherwise lock into
Protect.  Keeps the Electro Shot immunity that walls Archaludon's rain STAB.

## 0.7.9 — 2026-06-13

### Self-healing reconnect loop (network resilience)

- **`run()` now retries `connect()` with exponential backoff and reconnects
  automatically when an established stream drops.**  Three transient DNS
  outages during the 0.7.x ladder runs (`socket.gaierror: getaddrinfo
  failed`) each killed the process — the bot had no retry, so a supervising
  wrapper had to restart it.  Now a network blip (DNS failure, refused
  connection, dropped websocket) is weathered: backoff runs
  `RECONNECT_DELAY_INITIAL` (5s) → ×2 → `RECONNECT_DELAY_MAX` (300s cap),
  resetting to 5s after any successful connect.
- **Self-healing resume:** after each reconnect the server sends a fresh
  `challstr`, which re-drives login + matchmaking through the existing
  global-message handlers — no special resume path.  `_reset_connection_state`
  drops per-connection state (parsers, recorders, requeue task, joining/
  finished sets) before reconnecting since active battles are forfeited
  server-side on a disconnect; cross-session ELO state is preserved.
- `shutdown()` sets a `_stopping` flag so Ctrl-C / forfeit cleanly breaks the
  loop.  `websockets.exceptions` is now imported explicitly
  (`from websockets.exceptions import WebSocketException`) — the lazy shim in
  this websockets version raised `AttributeError` when referenced in an
  `except` clause.
- New `tests/test_reconnect.py` (6 tests): backoff schedule + cap, reconnect
  after a stream drop, backoff reset after a good connect, state-reset
  clearing, ELO preserved, shutdown flag.  Pure-runtime change — turn-1 table
  unaffected.

## 0.7.8 — 2026-06-13

### Cosmetic-forme name resolution (data_gaps catch from the 0.7.7 run)

- **Progressive suffix-strip fallback in both name resolvers**
  (`data/species.py:get_species`, `data/sets.py:_resolve_name`).  Showdown
  reports decoration formes verbatim (`Alcremie-Rainbow-Swirl` flagged live —
  the mon was invisible in both damage directions); enumerating every
  cosmetic variant is hopeless, so unresolved names now strip `-Suffix`
  segments until an entry (or alias) matches.
- **Guarded by `_DISTINCT_FORME_SUFFIXES`:** the strip never crosses suffixes
  denoting a competitively distinct Pokémon (Galar/Alola/Hisui/Paldea,
  Therian/Origin/Bloodmoon/Crowned, Mega/X/Y, F) — `Stunfisk-Galar`
  (Ground/Steel) must not inherit base Stunfisk's (Ground/Electric) sets;
  an honest miss with a `data_gaps` flag beats silently wrong data.  The
  pre-existing `test_unresolvable_returns_none` guard caught exactly this
  during development.

## 0.7.7 — 2026-06-12

### Post-run fixes from the 0.7.6 hundred-game shakedown (48W-52L)

Every item below was caught live by the new `data_gaps` flags or the error
monitor during the 100-game ladder run — none affect the turn-1 table.

- **Struggle no longer sent with a target.**  `"randomNormal"` (Struggle,
  Outrage-style lock-ins, Metronome results — the server picks the target)
  was missing from `_NO_TARGET_TYPES`, so Struggle was emitted as e.g.
  `move 1 1` and rejected: *"You can't choose a target for Struggle"* — the
  slot then ran on the battle timer for the rest of the game (battle
  2630349715, a converted loss).  Fixed mid-run but never live (zero
  restarts), so the whole 0.7.6 sample played without it.
- **Bare `Meowstic` aliased in the species DB** (`Meowstic → Meowstic-M`).
  Showdown's species string for the male is the bare name; the slim DB only
  has gendered entries, so an opposing Meowstic had **no stats or types at
  all** — invisible to the engine in both damage directions
  (`stats:Meowstic` flagged in battle 2630372888).
- **Lead selector v2 (Task #4) — pair-based, initiative-aware.**
  `select_leads` now scores all C(n,2) lead *pairs*: combined type-matchup
  score vs the predicted opponent leads (unchanged v1 base) × initiative
  rows.  `_SLOW_LEAD_FACTOR` (×0.85) per pair member slower than both
  predicted leads with no attacking priority move — waived when the opponent
  roster has a Trick Room setter (slow IS fast under TR); `_TW_EXPOSED_FACTOR`
  (extra ×0.85) on a double-slow pair vs an undeniable priority Tailwind
  setter (Gale Wings / Prankster).  Magnitudes grounded in the 0.7.6 sample:
  Kingambit won 41.3% led vs 50.9% from the back; TW rosters were the worst
  archetype (45.9%).  With no rows firing the choice equals the old top-2
  ranking.  The priority check is move-data driven, so giving Kingambit
  Sucker Punch would automatically restore its lead eligibility.
- **Mid-battle forme changes keep their usage data.**  Added to the sets
  layer's `_FORME_ALIASES`: Aegislash-Blade/-Shield, Mimikyu-Busted,
  Palafin-Hero, Morpeko-Hangry, Greninja-Ash → their base entries.  The
  species DB already aliased these for types/stats, but the sets layer did
  not — after a `|detailschange|` the engine fell back to synthetic STAB
  guesses and blind ability inference (`moves:`/`sets:` gaps flagged for
  Mimikyu-Busted, Aegislash-Blade and Palafin-Hero during the run).

## 0.7.6 — 2026-06-11

### Sash/Sturdy KO-prevention + opponent item & forme inference

One release, three layers — each makes the *facts* smarter while every module
and adjuster stays untouched.

- **`DamageResult.ko_prevented` (damage layer).**  New fields `hits` and
  `ko_prevented` on `DamageResult`; `is_ohko` / `ohko_with_max_roll` now gate
  on `not ko_prevented`.  Computed in `full_damage_calc`: a full-HP defender
  holding a `_KO_PREVENTING_ITEMS` item (Focus Sash) or with a
  `_KO_PREVENTING_ABILITIES` ability (Sturdy) cannot be one-hit KO'd by a
  single-hit move.  Multi-hit moves (`expected_hits != 1.0`) break Sash —
  the engine routes Dual Wingbeat at Sash holders with no module rule.
  *Known approximation:* multi-hit damage is aggregated (power ×
  expected_hits) before the calc, so "2 hits whose total KOs" counts as
  breaking Sash even if no single hit would have.
- **Latent bug fix:** `build_turn_context`'s outgoing fact loop never passed
  `opp_is_full_hp` — chipped opponents were treated as full-HP for defensive
  modifiers and would have been treated as Sash-intact.
- **Opponent item inference (`_effective_item`).**  Revealed item >
  consumed (`item_consumed` → None) > usage-stats guess: `_assumed_item`
  returns the species' top item when its usage ≥ `_ASSUMED_ITEM_MIN_PCT`
  (40%).  Feeds **all** damage math (scope (b)): assumed Sash blocks our
  kill credit, assumed Chople Berry halves Close Combat into Kingambit, etc.
- **Opponent forme inference (`_assumed_species` / `data.assumed_forme`).**
  The usage stats file megas as separate entries, so base-entry items/stats
  describe only the non-mega minority (Charizard base = 1% of all
  Charizards).  `assumed_forme` resolves a pre-mega species to its
  population-dominant forme by raw count (Charizard → Charizard-Mega-Y,
  Glimmora → Glimmora-Mega, Dragonite → Dragonite-Mega; Aerodactyl at 22%
  mega stays base).  A revealed mega forme always wins; a revealed non-stone
  item demotes to base (`data.mega_stones()` is derived from the data — the
  top item of every -Mega entry — never a name-suffix check).  Routed through
  both fact loops, DamageOutput, SwitchModule, `_opp_combatant` (speed),
  `_effective_ability` (unrevealed Charizard is assumed Drought) and
  `_effective_item` (assumed item becomes the inert stone, not base-forme
  Sash).
- **Fixed a Lopunny stats mismatch** surfaced by the wiring: data lookups
  already resolved Lopunny → Lopunny-Mega, but damage stats used base-forme
  Atk 76 instead of Mega 136 — opposing Lopunny was drastically
  under-threatened.
- **51 turn-1 cells changed** (all user-reviewed): Sash-break redirects onto
  Whimsicott (Dual Wingbeat over single-hit kill shots: 1.2, 1.9, 1.10, 4.2,
  4.9), kill-credit weight drops on assumed-Sash/Chople targets, Glimmora
  cells re-anchored on the mega (2.19 attacks again), Charizard cells respect
  Mega-Y Drought (3.17, 5.17, 6.17), Pelipper/Dragonite redirects (1.20,
  2.20, 5.20), Lopunny threat respected (3.14, 6.14).  Known acceptable
  passivity: Chople-Kingambit double-Protect cluster (1.5, 2.5, 4.5, 3.12,
  6.12) — facts correct, little to lose vs non-setup teams.
- `test_opp_neutralized_before_acting_detects_faster_ally_ko` pins a revealed
  non-berry item on the target Kingambit (the unrevealed assumption is now
  Chople, which correctly suppresses the OHKO fact).
- **Our consumed items now drop out of the incoming facts.**  The incoming
  fact loop read the defender item from static team.txt (`tm.item`), so a
  popped Chople Berry kept halving incoming Fighting damage in the facts —
  underestimating a second Close Combat into a berry-spent Kingambit.  Now
  `our_item = None if mon.item_consumed else (mon.item or tm.item)`.
  Turn-1 table byte-identical (nothing is consumed on turn 1).
- **Double-KO force-switch crash fixed (backlog).**  When both actives
  fainted, `_build_choice`'s force-switch loop ranked each slot independently
  and both picked the same bench mon (`/choose switch 3, switch 3`) — an
  illegal choice the server rejected, leaving the bot stuck.  Root cause: the
  old phase-1 partner-veto moved into `coordinate()`'s
  `SwitchCollisionAdjuster` in 0.7.0, and `coordinate()` never runs on a
  force switch.  The loop now excludes targets claimed by an earlier forced
  slot; with one bench mon left the second slot correctly emits `pass`.
  Real-engine regression tests in `TestDoubleKoForceSwitch` (the old test
  mocked `scored_actions`, which is exactly what hid the regression).
- **Battle-log `data_gaps` flags (backlog).**  Silent data-lookup failures —
  no base stats (mon scored harmless), no types (matchups neutral), no usage
  moves (synthetic STAB fallback), no sets entry (inference blind),
  `find_member` failing for our own mon (slot skipped) — are now collected
  per battle (`data/diagnostics.py`, deduped `note_gap`/`drain_gaps`) and
  written as an optional top-level `"data_gaps"` array in the battle log,
  plus a WARNING at save.  Present only when something actually failed;
  clean battles are untouched.  Schema documented in BATTLE_LOG_SCHEMA.md.
- **Bench mons now evaluated with live item state (backlog).**
  `SwitchModule` read the bench item from static team.txt, so a Chople/Sitrus
  eaten during an earlier field stint kept counting in switch-in safety and
  offense estimates.  Bench candidates now use the live tracked item
  (`None` once consumed, revealed item wins, team.txt as fallback) — same
  rule as the actives' incoming fact loop.  Turn-1 table byte-identical.
- **Setter/Fake-Out list audit (backlog).**  Re-derived all three frozensets
  from usage data at their documented thresholds.  One real gap fixed:
  plain `"Meowstic"` (Showdown's species string for the male; 62% Fake Out)
  was missing from `_FAKE_OUT_USERS` — only the `-M`/`-F` variants were
  listed.  Gengar-Mega's absence from the TR setters is *correct* (base
  Gengar 47% TR, Mega 0%).  Known threshold asymmetries left as-is pending a
  design call: `Gardevoir` (base 15% TR, but 81% of the population are
  Mega-holders at 55% TR) and `Gallade-Mega` (19%) sit in the TR set below
  the raw per-forme threshold.

## 0.7.5 — 2026-06-11

### Merge IncomingOHKOModule + ProtectModule → ProtectValueModule

- **Replaced the two separate Protect-scoring modules (IncomingOHKOModule at
  position 3 and ProtectModule at position 9) with a single `ProtectValueModule`
  (position 3).** Module count goes 12 → 11.
- **Four multiplicative rows in one pass:** ×2.5 when threatened; ×3.0 when a
  partner can guaranteed-OHKO any threat; ×0.4 in 1v1 endgame; ×0.4 in 2v1
  numerical advantage.  Both reason prefixes (`"incoming_ohko:"` and
  `"protect:"`) are preserved — `_protect_is_justified` in the phase-2
  CoordinationAdjuster keys on them.
- **Behavior change (2v1 + partner clearing a threat):** old code suppressed
  the ×3.0 entirely in a 2v1 (giving 2.5×0.4=1.0); merged rows give
  2.5×3.0×0.4=3.0.  Turn-1 table is unaffected (always 2v2).
- No turn-1 cell changes.

## 0.7.4 — 2026-06-11

### FakeOut: remove partner-threat gate, tune PROTECT_BOOST to ×2.0

- **Removed the `PARTNER_THREAT_THRESHOLD` gate from `build_turn_context`.**
  Previously `ctx.fake_out[slot]` only fired when a non-FO opponent also
  threatened ≥30% damage to our active — meaning boards with weak FO partners
  (Farigiraf, Sneasler-as-setup, etc.) silently skipped the Fake-Out discount.
  Now `fake_out[slot] = fo_live` unconditionally: the signal fires whenever a
  fresh Fake Out user is on field, full stop.
- **Reduced `PROTECT_BOOST` from 3.0 → 2.0** to rebalance after the gate
  removal.  ×3.0 over-protected on boards where the FO user's partner posed
  little threat; ×2.0 Protects where IncomingOHKO genuinely demands it
  (e.g. Weavile/Garchomp, Inc/Garchomp boards with OHKO'd mons) and attacks
  elsewhere.
- **32 turn-1 cells changed** (19 decision flips + 13 weight-only):
  - *Flips:* 1.3, 1.5[B], 1.14, 1.15, 2.3, 2.5[A], 2.6, 3.15[B], 3.17[B],
    4.3, 4.19, 5.5, 5.17, 6.7, 6.11[A], 6.17[B], 6.19 — all Protect → attack/switch
  - *Weight-only:* 1.1, 2.1, 2.14, 2.15, 3.1, 3.3, 3.14, 4.1, 5.1, 5.3, 5.14, 5.15, 6.1, 6.3, 6.6

## 0.7.3 — 2026-06-11

### SwitchModule: pure multiplicative rows

- **Replaced the additive escape formula with four stacking multiplicative
  rows.**  Old formula: `TEMPO × (1 + gain×2×UNFORCED_PIVOT) + ESCAPE_BONUS`
  (additive escape bonus of +3.0, unforced pivots penalised by ×0.5 on the
  gain term).  New formula: `TEMPO × (1+g) × ESCAPE_FACTOR × safety` — four
  clean multipliers with no additive mixing and no `UNFORCED_PIVOT` gate.
  `ESCAPE_BONUS` (3.0) deleted; replaced by `ESCAPE_FACTOR = 4.0`.
- **Behavioral impact:** only the escape regime changes — unforced pivots
  (not escaping an OHKO) and danger pivots (switch-in itself OHKO'd) are
  numerically identical to before.  Escape pivots with offense gain are
  heavier (was `2.4 + 1.2g`, now `2.4(1+g)`), meaning escapes with a
  meaningful switch-in now beat Protect or mid-weight attacks they previously
  lost to.  11 turn-1 cells changed (4 decision flips, 7 weight-only):
  1.1 weight (+1.3), 1.6 flip (Protect+Switch → Attack+Switch, Venusaur
  already leaving), 1.10 flip (Dual Wingbeat → Switch→Sneasler, Aerodactyl
  escapes Kingambit Iron Head), 2.10 weight (+1.38), 4.6 flip (same as 1.6),
  4.7 flip (Close Combat → Switch→Basculegion, Sneasler escapes opp Sneasler),
  4.11/4.13/6.1/6.7/6.12 weight-only.

## 0.7.2 — 2026-06-10

### Symmetric Fake-Out adjuster + shared threat facts

- **FakeOutAdjuster is now symmetric — a pair pays the Fake-Out adjustment
  exactly once.**  Previously only the *lower* slot attacking freed the partner
  (a ported artifact of the old greedy scoring order), so mirror pairs scored
  3× apart by slot index alone: "Protect slot 0 + attack slot 1" kept both the
  Protect ×3 and the attack ×0.5, while the mirror got stripped.  Now *either*
  slot's attack divides the partner's `_fakeout_mult` back out (attack
  un-halved, Protect un-boosted); when both attack, one discount is kept.
  Double-Protect pairs are untouched (both keep ×3) — two Protects into a
  Fake Out give up no ground.  Six turn-1 cells changed, reviewed individually:
  two weight-only (2.19, 6.6 — Protect kept on its own justification at 7.5),
  two flips to double-attack (6.4 Close Combat → Incineroar on the Fake-Out+TR
  board; 6.15 Close Combat → Weavile, a guaranteed KO), one to double-Protect
  (3.15 — gives up no ground vs Weavile/Garchomp), and one to a pivot
  (6.7 Kingambit → Basculegion, which beats both the likely Close Combat and
  Fake Out into that slot).
- **Shared "can they kill me?" facts in `TurnContext`** (behaviour-preserving,
  verified byte-identical turn-1 table): `incoming_ohko[slot]` + 
  `neutralized[opp_slot]` are computed once per turn and read by IncomingOHKO,
  Protect and Switch, replacing three verbatim copies of the same
  `incoming_damage` threat loop (~90 lines).  `_opp_neutralized_before_acting`
  now runs once per opponent instead of once per slot×opponent×module.

### Tier-1 simplification pass (behaviour-preserving, byte-identical turn-1)

- **All yes/no damage facts now come from one place.**  `build_turn_context`
  is the only function that runs damage calcs for facts: the guaranteed-OHKO
  matrix (now also excluding Disabled moves, matching `_build_actions`), the
  incoming max-roll/min-roll threat matrices, `neutralized`, `doomed`, the
  Fake-Out per-slot condition, and the 1v1/2v1 board counts.
  `_partner_can_ohko` / `_opp_neutralized_before_acting` / `_ko_before_acting`
  became thin fact readers (still patchable seams for tests).  Side effect of
  unification: the partner-clears check now respects opponent screens and
  percentage HP like every other OHKO check (it previously passed neither —
  a mid-battle parameter drift; turn 1 unaffected).
- **TR/TW disruption split into single-purpose modules.**
  `SetterUrgencyModule` (one boost per turn, TR ×2.0 first, else TW ×1.5 —
  exclusivity by if/elif instead of cross-module recomputation) and
  `SetterDenialModule` (TR ×2.0 / TW ×1.5 on confirmed setter-kills, TR claim
  wins per action).  The `_denial_claimed` per-action tag is gone.
- **`_fakeout_mult` side-channel removed.**  `ctx.fake_out[slot]` holds the
  fact (fresh FO user + non-FO partner threatens ≥30%, computed in the same
  incoming-threat loop); the FakeOutAdjuster derives the partner's multiplier
  from the action itself (Protect ×3 / move ×0.5).  Actions no longer carry
  hidden mutable tags.
- **ThreatElimination's doom gate is now a ×0.2 cancelling row** (×5 × 0.2 =
  ×1.0) — code matches the doc's two-row form; no early-return gate.
- **Dead code removed:** `build_combatants` / `estimate_turn_order` /
  `TurnEntry` in `turn_order.py` (never called by the bot; `build_combatants`
  was a mega-unaware duplicate of `_our_combatant`), plus their tests.

## 0.7.1 — 2026-06-10

### More discrete decision rules

Two follow-up refactors to make individual rules cleaner and less
conditional-branchy.  Both are behaviour-preserving.

- **IncomingOHKO 1v1/2v1 suppression → two discrete ×0.4 rows.**  Instead of an
  early-return that skips the ×2.5 Protect boost in a 1v1 endgame or a 2v1
  numerical advantage, the module now always applies ×2.5 and then multiplies
  Protect by ×0.4 for each of those board states (they're mutually exclusive, so
  the net is ×1.0 — the old suppressed value).  Behaviour-preserving; turn-1 is
  always 2v2 so the table is unaffected.
- **TurnOrder doc fix (no code change).**  The position is our *rank* in the
  4-mon turn order (pos 1 = we act before all three other active mons), not "the
  number of foes we outspeed".

(An earlier attempt also folded the TR/TW *urgency* boost into denial; that was
reverted — urgency wasn't redundant, it's the weight that keeps attacking ahead
of a passive double-Protect on a setter lead.  TR/TW disruption keeps its
separate urgency (×2 / ×1.5 on all attacks) and denial (×2 / ×1.5 on the
setter-kill).)

## 0.7.0 — 2026-06-09

### Phase-2 refactor — `(move, target)` actions + joint `coordinate()`

The engine moves from **greedy-sequential + a `recoordinate` patch** to a clean
two-phase design: per-slot scoring of first-class `(move, target)` candidates,
then a single joint selection over candidate *pairs*.  This is the control-object
work's Stage 2 (Stage 1 was `TurnContext` in 0.6.10).  **Behaviour changes** (it
is not a behaviour-preserving refactor): the turn-1 table and decision-module
tests were regenerated against the new engine and re-validated.

- **`(move, target)` actions.** `_build_actions` now emits one candidate per live
  opponent for every single-target move, with `target_slot` fixed at build time.
  Targeting is part of an action's identity instead of a field modules pick and
  overwrite.  DamageOutput / ThreatElimination / the TR-TW denial / OppProtectRecency
  now score a candidate's *own* target — the `target_hp_fractions` redirect cache
  is gone, and so are all in-module target overwrites.
- **Two phases.** Phase 1 is 12 per-slot modules run in isolation (blind to the
  partner).  Phase 2 is `DecisionEngine.coordinate`, which picks the pair
  maximising `(w0·factor_a)·(w1·factor_b)` over both slots' candidates.  With the
  joint factors inert this is exactly each slot's independent best, so coordination
  only moves a choice when a real cross-slot effect makes another pair better.
- **`JointAdjuster`s replace the cross-slot modules + `recoordinate`.** Four pure
  pair-scorers are the *only* place cross-slot effects live:
  - **Doubling** — both attack the same target → ×0.40–0.70; if one slot already
    confirms the OHKO, a ×0.05 overkill near-veto on the *non-killer*, so the pair
    that **spreads** onto the survivor wins (the old explicit "redirect", now
    emergent from argmax).
  - **Coordination** — a gratuitous lone Protect beside an attacking partner →
    ×0.5 (favour double-attack); justified/double Protects untouched.
  - **FakeOut (free)** — when the lower slot attacks (absorbs the Fake Out), the
    partner's phase-1 Fake-Out multiplier is divided back out.  Replaces the old
    scoring-order "slot-1 exemption".
  - **SwitchCollision** — both slots switching to the same bench mon → ×0.
  The chosen pair's per-slot factors are baked into the final weights, so a
  decision's weight reflects the joint effects (logs/recorder stay meaningful).
- **No more order-induced blind spot.** Slot 0 is never committed before slot 1 is
  seen, so `recoordinate` (and `needs_overkill_recoordination` /
  `needs_decoordination_repair` / `_committed_is_confirmed_ohko`) are deleted;
  `main.py` runs phase-1 score-all → `coordinate` → record/mega/emit.
- **Notable behaviour shift:** with a Fake Out lead *and* a removable fast threat
  (e.g. Incineroar + opposing Aerodactyl), the joint pass can now prefer the safe
  **double-Protect** — it weighs that the remover itself might be Fake-Out-flinched.
  Both that line and the old attack line are sound; the "neutralized threat → don't
  over-protect" principle is still guarded (now via a non-Fake-Out board in
  `test_neutralized_threat_does_not_force_protect` and the unit test on
  `_opp_neutralized_before_acting`).
- Tests: 622.  `TestDoublingUpModule`/`TestCoordinationModule`/`TestRecoordinate`
  → `TestDoublingAdjuster`/`TestCoordinationAdjuster`/`TestFakeOutAdjuster`/
  `TestSwitchCollisionAdjuster`/`TestCoordinate`; turn-1 tables regenerated.

## 0.6.10 — 2026-06-09

### TurnContext — facts, not reason strings (control-object refactor, Stage 1)

The kill/death logic had become *load-bearing on reason strings*: modules signalled
"this is a confirmed kill" by appending a `threat_elimination:` reason and reading
it back elsewhere (DoublingUp, the recoordinate overkill redirect), and the "will I
die first?" withhold was an apply-then-cancel dance (`DeathBeforeActingModule` ×5
then ÷5, removing the reason and reverting the KO-target). Reasons are meant to be
*log output*, not a control channel — and apply-then-cancel is harder to read than a
gate. **Behaviour is identical** (every turn-1 cell and decision-module test holds);
this is a structural cleanup.

- **New `TurnContext`** (`decision/modules.py`) — per-turn facts computed **once**:
  `doomed[slot]` (KO'd before acting) and `ohko` (set of `(slot, move, opp_slot)`
  guaranteed-OHKO triples). Built by `build_turn_context` (mirrors
  ThreatElimination's exact damage call) and cached via `_ensure_turn_ctx(state)`
  (keyed on `state.turn`; reused across both slots' scoring **and** the recoordinate
  re-pass — board facts don't change within a turn).
- **`DeathBeforeActingModule` removed** — its job is now a **gate** inside
  ThreatEliminationModule: if `ctx.is_doomed(slot)` the ×5 is *never applied*
  (vs the old add-then-undo). Same outcome — an undeliverable kill earns no credit.
- **DoublingUp + the recoordinate overkill redirect** now read
  `ctx.guarantees_ohko(...)` / `ctx.is_doomed(...)` instead of sniffing the partner's
  reason string. New `_committed_is_confirmed_ohko(ctx, slot, action)` (engine.py)
  centralises the "confirmed kill?" test, falling back to `weight ≥ 15.0` when no
  ctx is present (direct unit tests).
- Pipeline is now **14 modules** (was 15); the 0.6.9 atomic-question split of the
  kill/death pair is preserved at the *question* level (ThreatElim still answers both
  "can I kill?" and "will I die first?") without a second module. The TR/TW splits
  are untouched.
- Deliberately **deferred to a follow-up**: CoordinationModule's
  `_protect_is_justified` still reads reason-string prefixes (migrating it would
  re-derive three modules' firing conditions and risk drift). Left as-is for Stage 1.
- Tests: 624 (−3 DeathBeforeActing apply/cancel tests removed; +2 TurnContext fact
  tests; ThreatElim integration retargeted to the gate). Turn-1 summary unchanged.

## 0.6.9 — 2026-06-08

### One-mega-per-battle aware team selection

A week of 0.6.8 play (1,606 games, 798–808 = **49.7%**, up from 0.6.7's 47.6%)
confirmed the focus-fire fix held — overkill-doubling fell to **0.0%** of turns
(from 9.7% in losses) with spread up to 93–95% — and surfaced the next lever in
the win-rate-by-bring data:

- Bringing **both** mega-stone holders (Aerodactyl + Venusaur) happened in
  **511 / 1,606 games (32%)** and won only **44.8%**, versus **51.9%** with one
  stone — a 7-point hole. Only one mega is allowed per battle, so the second
  stone holder plays with a **dead item** at base stats.

`select_team` valued every stone holder at its *mega* strength, over-bringing the
pair. **Fix:** selection is now greedy and one-mega-aware — the first stone
holder keeps mega value; any further stone holder is re-valued at its base form:
base typing/ability **and** base stats (scaled by its own `base_BST / mega_BST`).
The stat scaling is essential and generic — a mega whose typing is unchanged
(e.g. Aerodactyl, a speed/power mega) wouldn't be demoted by type scoring alone.
Keys off `member.mega_name` and the member's own stat sheet — **no species names**,
so it survives a team change. This is the stat-aware mega-vs-base comparison
backlogged as Task #5, applied at bring time.

- Replayed over all 1,606 historical previews: double-stone brings drop
  **31.8% → 4.6%**; the best stone is always kept at full mega value.
- Tests: 613 (+4 team-preview): second stone demoted by type *or* by stats when
  typing is unchanged; second stone still brought when its base form genuinely
  beats the alternatives; lone stone unaffected.

### Coordination re-pass — protect less, favour double-attack

A deep dive on the 0.6.8 set found opponent setup is the biggest loss correlate
(59.8% of losses vs 44.5% of wins involve a setup move) — largely a team gap (no
disruption/speed-control), but it also exposed an engine bias: the bot reaches
for Protect in spots where a coordinated **double-attack** is better. Turn-1 vs a
Fake Out lead, attacking both slots won 54% vs 45% for protecting (38% for
double-Protect). A first mechanistic theory (that Protect doesn't block Fake Out)
was **wrong** — moves are simultaneous; Protect (+4) does block Fake Out (+3).
The sound framing is coordination: a double-attack or a deliberate double-Protect
is usually right; a *lone* Protect beside an attacking partner is the exception,
correct only when that mon must genuinely shield.

- **New `CoordinationModule` (#14)** — when a partner has committed to an attack,
  a **gratuitous** Protect (no `incoming_ohko` / `protect:` / `field_condition`
  reason — e.g. only a FakeOut nudge) is penalised ×0.5 so the slot attacks too.
  *Justified* Protects (real OHKO incoming, partner-clears, TR/TW stall) are never
  touched, and a double-Protect (no attacking partner) is never penalised.
- **`recoordinate` gains a de-coordination repair** — slot 0 is scored before
  slot 1, so its FakeOut-driven Protect is decided blind; once slot 1's attack is
  known, slot 0 is re-scored and the module flips its gratuitous Protect to an
  attack. Symmetric with the existing overkill redirect.
- The FakeOut multipliers are deliberately **left unchanged** — over-protection
  is addressed through coordination, not by re-tuning a discount on shaky data.
- 7 turn-1 cells shift (all verified): a FakeOut-driven lone Protect → a real
  attack (Rock Tomb / Stomping Tantrum / Ice Fang→Garchomp 4×). No justified
  Protect was flipped.
- Tests: 621 (+8): CoordinationModule (penalise/skip/no-op cases) and the
  recoordinate de-coordination repair.

### Decision pipeline — atomic-question refactor (no behaviour change)

Two compound modules were split so each answers a single question and the weight
tables in `DECISION_ARCHITECTURE.md` read cleanly. **Behaviour is identical** —
every turn-1 cell and decision-module test is unchanged (the splits only multiply
the same factors in a new order, which commutes).

- **ThreatEliminationModule** is now *pure* — "can I guarantee a kill?" (×5). The
  "withhold if KO'd before acting" half moved into a new **DeathBeforeActingModule**
  ("will I die before I act?") that cancels the kill credit (÷5, reverts the
  KO-target override) when undeliverable.
- **SetterPresenceModule + FieldSetterDisruptionModule** → **TrickRoomDisruptionModule**
  + **TailwindDisruptionModule**, each answering its setter's present? / active?
  (urgency) / deniable? (denial) in order. TR keeps priority over TW for the single
  urgency boost and the per-action denial (via a `_denial_claimed` flag).
- Pipeline is now 15 modules; the generic weight table is 19 atomic rows. Tests: 625.

## 0.6.8 — 2026-05-30

### Focus-fire coordination re-pass (endgame attrition)

A full-folder review of the 189 0.6.7 games (90W–99L, 48%) found switching is
**well-calibrated** — when the bot switches the switch-in survives 97% of the
time, and ~90% of stays on an OHKO-threatened mon are correct; only 17/2181
(0.8%) decisions are genuine switch-misses, most of them defensible damage
trades. So switching was **not** re-tuned (a blunt buff would regress the
correct stays). Losses are close grinds (avg 6.8 turns vs 5.4 for wins, fought
down to the last mon), so the lever is the back-half exchanges, not the lead.

The real, quantified flaw was **overkill doubling**: 9.7% of loss turns (vs 6.8%
of win turns) had both actives attack the same opponent while one already
guaranteed its OHKO — and in 20 loss-turns the *second* attacker dumped a strong
hit (up to 413%) into the dying target while a 30–98% option on the surviving
opponent sat unused. Root cause: **slot 0 is scored before slot 1, so it commits
its best attack without knowing slot 1 will OHKO that target.** `DoublingUpModule`
only redirects the *later* slot off an *earlier* slot's kill, never the reverse.

- **`DecisionEngine.recoordinate()`** — after every active slot has a committed
  decision, any slot whose move doubles a target a *different* slot will
  confirm-OHKO is re-scored with the partner's decision visible, so the existing
  (order-agnostic) DoublingUp redirect sends its otherwise-wasted action at the
  surviving opponent. Gated on a confirmed kill (ThreatElimination fired, or
  weight ≥ 15) and a second live opponent to redirect onto — no module changes.
- **`main.py`** normal-turn loop is now three phases: decide all slots → run the
  coordination re-pass → record/mega/emit. The recorder logs the *final*
  (post-redirect) decision, so future battle data shows the redirect.
- Verified against the real battle `2621134956` t2 (Venusaur Giga Drain into a
  Basculegion that Kingambit OHKO'd): the re-pass now sends Venusaur's Sludge
  Bomb at the untouched Talonflame instead.
- `turn1_summary.md` and its test ground truth (`test_turn1_decisions.py`) now
  run the re-pass too, so they reflect actual in-game behaviour. Four turn-1
  cells changed, all replacing a wasted overkill attack: Aero+Venusaur *(mega
  Venusaur)* vs Whimsicott+Garchomp → **Ice Fang→Garchomp** (4×); vs
  Incineroar+Whimsicott → **Protect**; vs Whimsicott+Kingambit → **Switch
  Sneasler**; Aero+Sneasler *(mega Aero)* vs Weavile+Garchomp → **Protect**.

### Target visibility in logs

Both logs now show *who* each slot is attacking instead of leaving it to be
inferred from a numeric target slot:

- **`bot.log`** decision lines read `[A]  Kowtow Cleave -> Basculegion  x10.45 …`
  (target_slot resolved to the opponent species; omitted for Protect/switch).
- **Battle-data JSON** now names targets two ways: a decision-level **`ct`**
  (the chosen action's target species) and a per-action **`tg`** on every
  candidate in `acts` (each option's target species). Both resolve `ts` against
  the turn's `opp` list and are omitted when there's no opponent target. The
  numeric per-action `ts` is unchanged, so existing analysis keeps working.

Tests: 609 (+16).

## 0.6.7 — 2026-05-29

### Battle-feedback fixes (from the 0.6.6 review)

- **Ability-based type immunities** (#1, #2): the damage calc now zeroes a move
  the defender's ability nullifies — Levitate/Earth Eater→Ground, Dry Skin/
  Water Absorb/Storm Drain→Water, Flash Fire/Well-Baked Body→Fire, Volt Absorb/
  Lightning Rod/Motor Drive→Electric, Sap Sipper→Grass. Fixes Earth Power into
  Levitate Chimecho and Water moves into Dry Skin Heliolisk.
- **Opponent light screens** (#3): Reflect / Light Screen / Aurora Veil are
  tracked per side; our outgoing damage drops to 2/3 (doubles) when the
  defender has the matching screen — crits bypass, Aurora Veil covers both
  categories. (Our-screen→incoming direction deferred; team has no setters.)
- **Trick Room speed awareness** (#4): every engine speed check (TurnOrder,
  `_ko_before_acting`, `_opp_neutralized_before_acting`, FieldSetterDisruption)
  now passes `trick_room` to `will_outspeed`. Previously TR was ignored, so a
  fast mon read as moving first under opponent TR and attacks out-scored the
  stall Protect; now it correctly Protects / reads move order.
- Fixed a stray-space syntax typo in `main.py` (`my_slot_decisions`) that broke
  the force-switch tests.

#5 (stat-aware mega selection) is backlogged as Task #5. #6 (Aegislash immune to
Sludge Bomb) was **not a bug** — the type immunity works and the bot targeted
Sylveon (Poison ×2), not Aegislash. Tests: 593.

## 0.6.6 — 2026-05-29

### Credit KOs on weakened opponents

`outgoing_damage` evaluated KO thresholds against the opponent's **full**
typical-spread HP for percentage-tracked opponents, so the engine couldn't see
a kill on a chipped mon (battle `2620687657` T4: Sludge Bomb on a 41 % Alakazam
— lethal — got no `threat_elimination` credit).  The bot under-prioritised
finishing weakened threats.

- **`outgoing_damage` gains `opp_hp_percent`** — when set (and absolute current
  HP is unknown), it scales the typical max HP by the percentage, so OHKO flags
  and `hp_fraction_*` reflect the opponent's *remaining* HP.
- The KO-crediting call sites (`DamageOutputModule`, `ThreatEliminationModule`)
  now pass it, so a chipped opponent is correctly recognised and finished.

No turn-1 summary change (all turn-1 opponents are at full HP). Tests: 590.

## 0.6.5 — 2026-05-29

### Offensive speed gate — don't credit a kill we won't live to deliver

Surfaced in battle `2620687657`: Garchomp, **outsped** by Weavile (which OHKOs
it with Ice ×4), chose Stomping Tantrum for a "guaranteed OHKO on Alakazam"
(weight 8.11) over Protect (7.50) — but Weavile moved first and KO'd Garchomp,
so the attack never landed (Alakazam survived at full HP next turn).
`ThreatEliminationModule` granted its ×5.0 bonus without checking that we
survive long enough to deliver the kill — the offensive blind spot opposite the
defensive speed-awareness work (0.6.1).

- **`_ko_before_acting(state, slot)` added** — the offensive mirror of
  `_opp_neutralized_before_acting`.  True when an active opponent moves before us
  (faster, or Gale-Wings-style attacking priority), is **guaranteed** to OHKO us
  (min roll), and is not itself removed before acting (a faster ally killing it
  cancels this).
- **`ThreatEliminationModule` withholds its ×5.0** when `_ko_before_acting`
  holds, so a doomed attack no longer out-scores Protect / switching.  The
  *guaranteed* (min-roll) threshold means a survivable hit still lets us take the
  kill gamble — e.g. Kingambit's Chople Berry halving a 4× Close Combat (turn-1
  case 3.12), or a non-guaranteed roll.

**Effect:** the Garchomp case now Protects (Stomping Tantrum 8.11 → 1.62 <
Protect 7.50).  Turn-1 summary: one weight-only change — 6.16, Sneasler vs a
Gale Wings Talonflame, Rock Tomb 36.12 → 7.22 (the kill is genuinely
undeliverable; the decision is unchanged).  Tests: 589.

Known follow-on (not addressed): when KO'd-before-acting by a priority sweeper
with no partner answer (6.16), the bot still attacks because Protect/switch
isn't boosted enough to win — a separate Protect/switch-valuation gap.

## 0.6.4 — 2026-05-29

### Incoming-damage threat estimation — fix missing usage data

`incoming_damage` estimates an opponent's threat from its top-6 usage moves and
most-common spread.  **34 of the 218 Champions-legal species had no usage entry
under their battle name**, so `move_distribution` returned empty and
`incoming_damage` returned `[]` — which the decision engine reads as "this
opponent is harmless," silently disabling the IncomingOHKO / Protect / Switch
threat checks against them.  Four of the 34 (Lopunny — a Fake Out mega! —
Feraligatr, Gourgeist-Small, Vivillon-Pokeball) actually appeared as opponents
in the 0.5.6 games.

- **Name resolver in `data/sets.py` (`_resolve_name`).** `get_sets` and every
  distribution accessor now resolve a missing name to the best usage entry:
  exact → explicit forme alias (Meowstic-M/F→Meowstic, Maushold-Four→Maushold,
  Vivillon-*→Vivillon, Gourgeist/-Large/-Small→Gourgeist-Super,
  Polteageist-Antique→Polteageist, Sinistcha-Masterpiece→Sinistcha) →
  `"<name>-Mega"` for base forms that only appear as their Mega (Lopunny→
  Lopunny-Mega, plus Pidgeot, Beedrill, Pinsir, Houndoom, Camerupt, Banette,
  Ampharos, Emboar, Feraligatr, Meganium, Victreebel).  Resolves 22 of the 34.

- **Synthetic STAB fallback in `damage.py` (`_synthetic_stab_moves`).** For the
  remaining ~12 with no usable usage data — rare mons, or type-shifted formes
  like Stunfisk-Galar that must *not* alias to a different-typed entry —
  `incoming_damage` falls back to one representative ~80–95 BP STAB move per
  type, physical or special by the mon's higher attacking stat, so the threat is
  type-correct rather than zero.

- **Result:** every Champions-legal species now registers a threat (Ditto
  excepted — it only carries Transform pre-evolution).  Guarded by
  `tests/test_usage_coverage.py`.  Turn-1 effect: two Lopunny cells (4.14, 6.14)
  shift weight slightly — its defensive stats now use the real Lopunny-Mega
  spread instead of 0 EVs — but no decisions change.  Tests: 587.

## 0.6.3 — 2026-05-29

### Switch scoring rescale — board value instead of a capped multiplier (Task #3)

Switches were scored as a type-matchup multiplier capped at ×4.0 (usually
×0.5–1.2) while attacks reach 15–40, so across the 0.5.6 battle data the bot
switched only 6 / 326 turns and could never make a preservation pivot.

`SwitchModule` now scores a switch by the value of the resulting board (a cheap
1-ply lookahead), on the same scale as an attack:

    weight = TEMPO × (offense_term + escape) × safety

- **offense_term** = 1 + max(0, switch-in_offense − current_offense) × 2 — the
  *gain* in best damage from pivoting, so a switch earns offense credit only when
  the incoming mon threatens more than staying does.  The current mon's Struggle
  counts as zero offense, so a Struggling mon is correctly seen as contributing
  nothing (this is where the Struggle handling "falls out of switch scaling").
- the gain is **halved when not escaping** a KO — an unforced pivot concedes
  initiative (the opponent gets a free turn and need not stay in).
- **escape** = +3.0 when the current mon is OHKO-threatened by a connecting
  threat (speed-aware) and the switch-in survives every active opponent's max roll.
- **safety** = ×0.3 if the switch-in is itself OHKO'd; **TEMPO** = 0.6.
- A switch a partner already claimed is still vetoed (×0).

Built on the 0.6.2 trapping fix: switches are never offered for a trapped slot,
so the higher switch weights cannot trigger an illegal-switch loop.

**Turn-1 effect (8 cells, all slot B):** seven are sound escape pivots — a mon
that would be OHKO'd flees to a survivor with a better matchup (Kingambit
fleeing Close Combat in 6.1/6.12; Sneasler → Venusaur to wall rain in 4.20;
Venusaur → Basculegion vs Incineroar in 1.1/1.6; Sneasler → Basculegion in
4.11/4.13).  The eighth (1.15) is a low-weight pivot where the alternative was
Protect anyway.  Speculative turn-1 offense pivots do *not* fire — the
unforced-pivot discount keeps them below the current mon's own attack.
`turn1_summary.md` regenerated; tests: 576 (two board-value unit cases; 8
turn-1 expectations updated).

The old type-matchup helpers (`_infer_threat_types`, `_worst_effectiveness`)
are retained for reference and their tests, but no longer drive scoring.

## 0.6.2 — 2026-05-29

### Legal-action correctness: trapping + move availability

Reviewing the 0.5.6 battle data (45 games) surfaced battle `2620546298`, where
Kingambit (96% HP) chose **Struggle over switching** for three turns vs a Mega
Gengar. Investigation showed this was **not** a switch-scoring problem — it was
two legal-action bugs, both fixed here. (A first attempt, a `StuckPivotModule`,
was prototyped and reverted: it patched the symptom; these fix the cause.)

- **Trapping is now respected.** `available_switches` only checked "alive and
  not active" — it ignored the server's per-slot `trapped` flag (Mega Gengar's
  Shadow Tag, Arena Trap, Magnet Pull, trapping moves). `BattleState.trapped`
  is now read from each `|request|` `active[]` entry, and `_build_actions`
  suppresses switch actions for a trapped slot. `maybeTrapped` is treated as
  *not* trapped (the switch is still legal). A force-switch clears the flag.
  This also removes an **illegal-switch loop risk**: previously a rejected
  switch ("trapped") was re-decided identically and re-rejected until the turn
  timer fired. *(This is the prerequisite for the upcoming switch-value rescale,
  Task #3 — once switches can out-score attacks they must never be offered when
  trapped.)*

- **Our Disable/Encore tracking can no longer cause a false Struggle.**
  `_build_actions` filters the server's move list by our own
  `my_disabled_moves` / `my_encored_moves`. A stale Encore lock (or an Encore
  onto a move that then gets Disabled) made that filter drop *every* move →
  Struggle, even though the server still offered usable moves — the likely
  cause of Kingambit's "vanishing moves" t4–6 that returned t7. `_build_actions`
  now trusts the server: if our filter would empty the list while the server
  lists a usable move, we use the server's moves instead of Struggling.

- Tests: 574 (new `TestBuildActionsTrapped`, `TestTrapped`, and a stale-lock
  guard case). No turn-1 decisions change; `turn1_summary.md` is unchanged.

### Still open from the 0.5.6 review

- **Switch scoring rescale (Task #3)** — switches are capped at ×4.0 while
  attacks reach 15–40, so the bot switched only 6 / 326 turns. A board-value
  (1-ply lookahead) rescale is designed and unblocked by the trapping fix above;
  not yet implemented.

## 0.6.1 — 2026-05-29

### Bug fix + turn-order awareness for the Protect-decision modules

- **Fixed `_partner_can_ohko` false OHKOs vs percentage-HP opponents.**
  For an opponent tracked at percentage HP, the helper computed
  `opp_current_hp = max_hp * pct / 100` — but `max_hp` is a placeholder (100),
  so it fed the damage layer a phantom 100-HP target.  A ~97 %-avg hit then
  read as a *guaranteed* OHKO against the 100-HP bar.  Now it passes `None`
  for percentage HP (matching `DamageOutputModule`/`ThreatEliminationModule`),
  so KO detection uses typical-spread stats.  This was making `ProtectModule`
  fire on a guaranteed-OHKO premise that didn't exist (turn-1 case 4.6:
  Sneasler Protected when it should attack).

- **`_opp_neutralized_before_acting` helper added.** Returns True when a
  *faster* ally is guaranteed to OHKO an attacker this turn — i.e. it dies
  before it can land its hit.

- **`_opp_has_attacking_priority` helper added (Gale Wings).** A Gale Wings
  Talonflame's Brave Bird is +1 priority at full HP, so it strikes before our
  normal-priority KO move regardless of Speed.  Such an attacker is never
  treated as "neutralised before acting", so we correctly Protect against it.
  Talonflame is assumed to run Gale Wings (unrevealed ability → Gale Wings;
  a contradicting revealed ability disables it; chipped Talonflame loses the
  priority).  Other move-based priority (Prankster status, Fake Out, Sucker
  Punch) is still not modelled.

- **IncomingOHKOModule (Q3) is now speed-aware.** An OHKO threat that a faster
  ally is guaranteed to remove before it acts no longer pushes us toward
  Protect — it is not a live threat this turn.

- **ProtectModule (Q9) redesigned around "will I be OHKO'd this turn anyway?"**
  The old gate ("the threat outspeeds me") missed slower attackers we cannot
  remove (they still OHKO us *after* we act) and fired against faster attackers
  a partner kills first (the threat never lands).  New gate: (1) an opponent
  can OHKO us, (2) at least one such threat still connects (not neutralized
  before acting), and (3) a partner guarantees an OHKO on one of the threats.

- **SwitchModule's OHKO-escape check shares the same speed awareness**, so a
  switch is no longer inflated as an "OHKO escape" from a threat a faster ally
  is already removing.

- **Net turn-1 effect:** one decision changed (4.6 Sneasler Protect → Close
  Combat — the bug fix) and four inflated Protect weights dropped to honest
  values (2.19, 4.5, 4.13, 6.17).  Case 1.16 (Venusaur vs Talonflame+Garchomp)
  stays Protect ×7.50: the Gale Wings handling keeps Talonflame a live priority
  threat, so Venusaur correctly shields rather than attacking into a priority
  Brave Bird.  Tests: 565 (5 new speed-awareness / regression guards);
  `turn1_summary.md` regenerated.

## 0.6.0 — 2026-05-28

### Decision engine overhaul — 13 modules (up from 9)

- **Assumed opponent ability** — `_effective_ability(opp)` replaces raw
  `opp.ability` everywhere.  Falls back to the highest-usage-rate ability from
  the Champions data when the ability hasn't been revealed in battle.

- **IncomingOHKOModule added (Q3) — "Can they OHKO me?"**
  Protect ×2.5 when any opponent's max damage roll can KO this slot.
  Suppressed in 1v1 endgame and 2v1 numerical advantage.

- **TurnOrderModule added (Q4) — "What is my turn-order position?"**
  Attack weights scaled by estimated turn-order position (×2.0 / ×1.5 /
  ×1.0 / ×0.75 for positions 1–4).

- **SetterPresenceModule added (Q5) — "Is a TR/TW setter on the field?"**
  Extracted from `FakeOutModule` and redesigned as an independent module.
  When a known TR setter is active and TR is not yet running (or is on its
  last turn), all attacks gain **×2.0**.  Same logic for TW setters at **×1.5**.
  The boost is suppressed when the opposing effect is already active (TR active
  → no TW boost; TW active → no TR boost), preventing double-stacking.
  `FakeOutModule` no longer contains any setter logic.

- **ConsecutiveProtectModule added (Q8) — "Did I use Protect last turn?"**
  Protect ×0.2.  No exceptions, no waivers — not for HP, not for threats.

- **ProtectModule redesigned (Q9) — "Will I die before I can act?"**
  Replaces the old HP-threshold bonuses (×1.5 at <25%, ×3.0 at <5%).
  Protect ×3.0 only when all three hold: an opponent can OHKO this slot,
  that opponent outspeeds this slot, and the partner has a guaranteed OHKO
  on that same threat.  If the partner can't finish it, Protecting just
  delays the problem.

- **Species frozensets corrected from Champions usage data**
  All three frozensets were rebuilt by parsing the local sets file
  (`data/sets-gen9championsvgc2026regma-1760.txt`) to include only species
  that actually appear in the Champions format, removing all non-legal entries.

  * `_FAKE_OUT_USERS` (engine.py) — removed 7 illegal species (Hariyama,
    Ambipom, Hitmontop, Scream Tail, Togekiss, Maushold, Passimian);
    added 17 Champions-legal ones (Blastoise, Infernape, Lopunny, Medicham,
    Meowstic, Morpeko, Mr. Rime, Pikachu, Raichu, Sableye, Salazzle,
    Simipour, Tinkaton, Toxicroak, and their Mega/Alola forms).
  * `_TR_SETTER_SPECIES` (modules.py) — removed 5 illegal species (Porygon2,
    Cresselia, Indeedee, Bronzong, Runerigus-original); rebuilt with 32
    Champions-legal setters including Armarouge, Aromatisse, Audino, Chandelure,
    Chimecho, Cofagrigus, Espeon, Farigiraf, Gallade, Gardevoir, Gengar,
    Gourgeist-Super, Hatterene, Mimikyu, Mr. Rime, Oranguru, Reuniclus,
    Runerigus, Sinistcha, Slowbro, Slowking, Spiritomb, Trevenant, Wyrdeer,
    and Mega forms.
  * `_TAILWIND_SETTER_SPECIES` (modules.py) — removed 7 illegal species
    (Tornadus, Suicune, Jumpluff, Murkrow, Hawlucha, Flamigo, Ribombee);
    rebuilt with 24 Champions-legal setters including Aerodactyl, Altaria,
    Corviknight, Decidueye, Dragonite, Gliscor, Hydreigon, Kleavor, Noivern,
    Pelipper, Pidgeot, Skarmory, Talonflame, Toucannon, Vivillon, Volcarona,
    Whimsicott, and Mega forms.

- **Test suite: 560 tests** (up from 440)
  `TestSetterPresenceModule` added (11 tests).  `FakeOutModule` tests
  updated: Hariyama → Tinkaton, Tornadus → Noivern, Sneasler → Garchomp
  (Sneasler is now a FakeOut user), Bronzong → Cofagrigus.
  `tests/test_turn1_decisions.py` added — 120 integration tests covering
  all six lead configurations × 20 opponent matchups from `turn1_summary.md`.

---

## 0.5.11 — 2026-05-28

### Changes

- **ProtectModule redesigned — "Will I die before I can act?"**
  The HP-based Protect bonuses (×1.5 at <25% HP, ×3.0 at <5% HP) have been
  removed and replaced with a precise three-condition gate:

  1. An active opponent can OHKO this slot on their **max damage roll**.
  2. That same opponent **outspeeds** this slot (`will_outspeed > 0.5`) — they
     will act before us, meaning our selected attack would never fire without
     Protect.
  3. Our partner has at least one non-disabled move that guarantees an OHKO
     (`is_ohko`, not just max-roll) on that same threat.

  Only when all three hold does Protect receive ×3.0 (`PARTNER_KO_FACTOR`).
  Condition 3 is the key gate: Protecting is only worth it if the partner can
  actually eliminate the threat this turn.  If the partner can't KO the threat,
  surviving via Protect just delays the same problem to next turn.

  A new helper `_partner_can_ohko(state, partner_slot, opp)` checks all
  non-disabled partner moves for a guaranteed OHKO on the specified opponent.

  Constants removed: `CRITICAL_HP_THRESHOLD`, `LOW_HP_THRESHOLD`,
  `CRITICAL_HP_FACTOR`, `LOW_HP_FACTOR`.
  New constant: `PARTNER_KO_FACTOR = 3.0`.

  Suppress states (1v1 endgame and 2v1 numerical advantage) are unchanged.

  5 stale HP-based tests removed from `TestProtectModule`; 8 new tests added
  covering all three conditions, both suppress states, and the reason string.

---

## 0.5.10 — 2026-05-28

### Changes

- **IncomingOHKOModule added (new module #3) — "Can they OHKO me?"**
  The OHKO-threat boost for Protect has been extracted from `ProtectModule`
  into its own question at position 3 in the pipeline.  When any active
  opponent's maximum damage roll exceeds our current HP, all Protect-family
  actions receive **×2.5**.

  The boost is suppressed in 1v1 endgame and numerical advantage (2v1)
  states — the same conditions that suppress `ProtectModule`'s HP bonuses.
  Engine is now 12 modules.

  `ProtectModule` (now Q8, renamed question: "Is my HP low?") retains only
  the HP-based bonuses: ×1.5 at < 25% HP and ×3.0 at < 5% HP.
  `THREATENED_FACTOR = 2.5` moved from `ProtectModule` to `IncomingOHKOModule`.

  7 new tests added (`TestIncomingOHKOModule`).
  2 stale tests removed from `TestProtectModule`
  (`test_ohko_threat_bonus_applied`, `test_2v1_ohko_threat_protect_suppressed`).

---

## 0.5.9 — 2026-05-28

### Changes

- **ConsecutiveProtectModule added (new module #6)**
  The consecutive-Protect penalty has been extracted from `ProtectModule` into
  its own dedicated question.  If this slot used any Protect-family move last
  turn, all Protect-family actions receive **×0.2**.  The multiplier is applied
  unconditionally — there are no waivers for HP level, OHKO threats, or field
  conditions.  Engine is now 11 modules.

  Key differences from the old embedded penalty:
  · Multiplier changed from ×0.1 → ×0.2
  · The critical-HP waiver is removed entirely (previously at < 5% HP with an
    OHKO threat incoming, the ×0.1 penalty was replaced by ×2.5 to prevent an
    infinite loop; now the ×0.2 penalty always stacks with whatever bonuses Q7
    provides, so a consecutive Protect under OHKO threat is ×2.5 × ×0.2 = ×0.5
    rather than uncapped ×2.5)
  · The "suppress in 1v1/2v1" interactions are gone (suppress states are handled
    entirely by ProtectModule; the consecutive penalty fires regardless)

  8 new tests added (`TestConsecutiveProtectModule`).
  6 stale tests removed from `TestProtectModule` (consecutive/waiver logic).

---

## 0.5.8 — 2026-05-28

### Changes

- **Assumed ability for all opponent Pokémon**
  All modules now use `_effective_ability(opp)` instead of `opp.ability` when
  an opponent's ability has not been confirmed in battle.  The function returns
  the revealed ability if known, otherwise falls back to the highest-usage-rate
  ability for that species from the Champions sets data
  (`ability_distribution(species)[0]`).  Returns None only for species not in
  the data file (e.g. Tornadus, Murkrow — not in Reg MA usage data).

  Impact on specific modules:
  · DamageOutputModule, ThreatEliminationModule — damage calcs now use the
    assumed ability (e.g. Intimidate for Incineroar before it activates).
  · ProtectModule, SwitchModule, DoublingUpModule — OHKO-threat checks
    account for abilities that affect damage (e.g. Mold Breaker bypassing
    Sturdy on Garganacl).
  · FieldSetterDisruptionModule — the TR Prankster guard now catches any
    species whose top ability is Prankster even before it is revealed.
  · `_tw_setter_has_priority` — Prankster/Gale Wings inferred from usage
    data; Whimsicott (Prankster 99.3%) and Talonflame (Gale Wings 97.4%)
    continue to behave correctly before the ability is explicitly confirmed.
  · `_opp_combatant` — Combatant built with assumed ability for accurate
    speed estimates in turn-order and disruption modules.
  9 new tests added (`TestEffectiveAbility`).

---

## 0.5.7 — 2026-05-27

### Changes

- **Priority speed multipliers removed from PrioritySpeedModule**
  The ×1.5 (priority useful when opponent may outspeed) and ×0.8 (wasted
  priority when we outspeed all) adjustments have been removed.  Priority move
  order and speed-advantage scoring will be addressed in a dedicated module.
  Fake Out ×3.0 is unchanged.

- **ThreatEliminationModule simplified to guaranteed OHKO only**
  Max-roll OHKO (×2.5) and 2HKO (×1.5) bonuses removed.  Only moves that
  KO on every damage roll receive the ×5.0 bonus.  High-damage non-KO moves
  are already differentiated by DamageOutputModule.  FieldSetterDisruption
  updated to match (its internal KO re-score mirrored the same multipliers).

- **PrioritySpeedModule removed**
  The module is deleted entirely.  Move order and priority will be addressed
  in a dedicated module.  Engine is now 9 modules.

- **FieldConditionModule stall pattern changed to every-other-turn**
  Previously boosted Protect on turns_left = 1 (×3.0) and turns_left = 2
  (×2.0).  Now boosts on turns_left = 1 and turns_left = 3 (both ×3.0),
  leaving turns_left = 2 free to attack.  The intended stall pattern is:
  Protect (turn 3) → attack (turn 2) → Protect (turn 1), wasting two of the
  three remaining turns of the field effect.  TW and TR no longer stack —
  the ×3.0 is applied once even if both conditions are expiring together.

- **FieldSetterDisruptionModule — denial now requires guaranteed OHKO + speed**
  Previously applied the disruption bonus (×2.0 TR / ×1.5 TW) to any attack
  on a setter regardless of damage.  A non-lethal hit lets the setter move
  and establish the field effect on the same turn, so the bonus was misleading.

  New condition: all three must hold — (1) guaranteed OHKO (min roll ≥ setter
  HP), (2) we outspeed the setter (`will_outspeed > 0.5`), and (3) the setter
  lacks a priority ability.  Prankster users (Whimsicott, and any Pokémon
  with Prankster revealed) use Tailwind with +1 priority and are treated as
  undeniable.  Talonflame at full HP has Gale Wings active (+1 priority on
  Flying-type Tailwind); once damaged it loses Gale Wings and can be denied.
  `MIN_DAMAGE_FRACTION` threshold removed (superseded by the OHKO check).
  9 new tests, 3 existing tests updated.

- **TurnOrderModule added (new module #3)**
  Scales attack weights by estimated turn-order position in the 4-mon field.
  Position is determined by how many of the three other active Pokémon (two
  opponents + our partner) we are likely to outspeed (`will_outspeed > 0.5`).
  Multipliers: 1st (fastest) ×2.0 · 2nd ×1.5 · 3rd ×1.0 · 4th ×0.75.
  Protect-family and switch actions are unaffected.  Engine is now 10 modules.
  · `_opp_combatant` — Combatant built with assumed ability, improving speed
    estimates in turn-order and disruption modules.
  9 new tests added (`TestEffectiveAbility`).

- **Spread move handling removed**
  `is_spread_move` guards removed from `FieldSetterDisruptionModule` and
  `DoublingUpModule`.  The current team has no spread moves; the Spr column
  is removed from the generic weight table in the architecture docs.

---

## 0.5.6 — 2026-05-26

### Bug Fixes

- **Tailwind field-condition stall now actually fires (parser bug fixed)**
  `_on_sidestart` and `_on_sideend` were silently discarding every Tailwind
  message.  The handlers applied a regex to `args[0]` and expected to find
  the condition name ("Tailwind") there.  In real PS battle streams the
  condition is always in `args[1]` (e.g. `|-sidestart|p2: Alice|Tailwind`),
  so the regex matched the player's username instead, the "tailwind" substring
  check failed, and `opp_tailwind`/`opp_tailwind_turns_left` were never set.
  `FieldConditionModule` therefore had nothing to trigger on.

  Fix: extract the player side with `r'(p\d+)'` on `args[0]`; read the
  condition from `args[1]`.  Handles all observed PS formats:
  `"p2|Tailwind"`, `"p2: Alice|Tailwind"`, and the older
  `"p2: Tailwind|move: Tailwind"` form.

  4 new tests added covering both old and new message formats.

- **Weavile (and Hariyama) added to `_FAKE_OUT_USERS`**
  A fresh Weavile switch-in was not recognised as a Fake Out threat, so
  `FakeOutModule` did not boost Protect.  Both Weavile and Hariyama are now
  in the frozenset.  3 new tests added.

- **DoublingUpModule redirect no longer carries stale damage scores**
  When the partner had a confirmed OHKO on a target and `DoublingUpModule`
  redirected an action to the other opponent, the action kept its original
  (inflated) weight from scoring vs the dying target.  This caused moves like
  Poison Jab (great vs the dying target) to beat moves that were naturally
  scored vs the redirect target (e.g. Stomping Tantrum vs Glimmora).

  Fix: on redirect, reset `action.weight = 1.0` and strip stale
  `damage_output`/`threat_elimination`/`field_setter`/`opp_protect_recency`
  reasons.  Naturally-scored moves for the alt target now win cleanly.
  2 tests updated, 1 new test added.

- **Team-preview offensive scoring now respects opponent abilities**
  `_offensive_score()` in `team_preview.py` used the pure type chart and
  ignored opponent abilities like Dry Skin (Water immunity), Levitate (Ground
  immunity), Flash Fire (Fire immunity), etc.  This caused Basculegion's Water
  coverage to be over-rated against teams containing Heliolisk (Dry Skin).

  Fix: look up the opponent's ability via `ability_of(opp_form)` and apply
  `_ABILITY_DEFENSE_MODS` modifiers (the same table already used for defensive
  scoring) when computing the best offensive effectiveness.

## 0.5.5 — 2026-05-25

### Bug Fixes

- **Disable + Encore no longer causes the bot to time out**
  When an opponent used Encore on one of our Pokémon and then immediately used
  Disable on that same move, the bot would try to play the only move it was
  locked into — which was also disabled.  Showdown does not mark this as
  `"disabled": true` in the request JSON (it just sends the single Encored
  move without any flag), so the existing server-flag filter did not catch it.
  The bot would loop picking weight 0 actions and eventually time out.

  Fix adds three new tracking fields to `BattleState`:
  * `my_disabled_moves[slot]` — set from `|-activate|IDENT|move: Disable|MOVENAME`,
    cleared by `|-end|IDENT|Disable` and on switch-out.
  * `my_encored_moves[slot]` — set from `|-start|IDENT|Encore` (locked to
    `my_last_moves[slot]` at that moment), cleared by `|-end|IDENT|Encore`
    and on switch-out.

  `_build_actions` now:
  * Skips any move matching `my_disabled_moves[slot]` even when the server
    has not flagged it.
  * Skips every move except the one in `my_encored_moves[slot]` when Encore
    is active.
  * Falls back to Struggle (instead of nothing) when both are active on the
    same move — keeps the bot alive rather than erroring.

  14 new tests added (7 in `test_battle_parser.py`, 7 in
  `test_decision_modules.py`).  Full suite: **387 tests, 0 failures**.

### Documentation

- **`DECISION_ARCHITECTURE.md`** revised:
  * Uses the actual bot team (Garchomp / Kingambit / Sneasler / Basculegion-M /
    Venusaur / Aerodactyl) with real move sets throughout.
  * Part 1 example opponent team no longer includes Rillaboom (not legal in
    Reg MA); replaced with Talonflame.
  * "Brought?" column shows ✓ / ✗ only — Lead/Bench labels removed to avoid
    implying Part 1 decides lead order (it does not).
  * Type chart calculation example added below the scoring table.
  * Part 3 battle scenario updated: opponents are now Incineroar + Basculegion
    (was Sneasler + Basculegion); bench is Aerodactyl (was Dragonite).
  * Decision table expanded to 8 action columns (3 moves × 2 targets + Protect
    + Switch Aerodactyl).
  * Fake Out question now correctly shows as active (Incineroar is on the
    field Turn 1).
  * Protect explanation uses Basculegion Wave Crash as the OHKO threat (was
    incorrectly citing Sneasler Acrobatics).

---

## 0.5.4 — 2026-05-25

### New Features

- **Lead selection framework (team preview → battle)**
  The bot now learns which Pokémon opponents most often lead with and uses
  that knowledge at team preview to position its own counters in the lead
  slots.  The system has three parts:

  * **`data/lead_stats.py`** — persistent store for opponent lead counts.
    `record_leads(leads)` increments each species and `total_battles`, then
    writes atomically to `Battle Data/lead_stats.json`.  `lead_frequency(s)`
    and `all_lead_counts()` provide read access; `total_battles()` returns the
    sample size.

  * **`recorder.py` `record_outcome()`** — after every battle the recorder
    now extracts the turn-1 opponent actives from the frozen state snapshot
    and calls `record_leads()`, so the database grows automatically.  The
    update is wrapped in a bare `except` so a stat-write failure can never
    block the battle file from being saved.

  * **`team_preview.py` `select_leads()`** — replaced the ascending-slot-
    order stub with real logic: takes the opponent preview team, ranks each
    species by historical lead frequency, picks the top 2 as the predicted
    leads, then calls `score_members()` against those 2 to find our best
    counters and places them first.  Falls back to ascending slot order when
    `total_battles() == 0` (no data yet) or either list is empty.

- **`tools/build_lead_stats.py`** — one-shot script to bootstrap the lead
  database from all existing v0.5.0+ battle files.  Run with
  `python -m tools.build_lead_stats` from the project root.  Safe to re-run:
  always rebuilds from scratch.  Prints a ranked frequency table on completion.

## 0.5.3 — 2026-05-25

### Bug Fixes

- **`decision/modules.py` `SwitchModule._infer_threat_types()` — status moves excluded**
  The switch type-matchup scorer collected the type of every revealed opponent move,
  including status moves like Trick Room (Psychic), Tailwind (Flying), Follow Me
  (Normal), and Helping Hand (Normal).  These contributed false threat types that
  could penalise a switch-in for being weak to a move the opponent will never use
  to deal damage.  The method now checks `move_category(move_name) == "Status"` and
  skips those moves.  `incoming_damage()` was already filtering correctly
  (`power > 0` check) so OHKO-threat detection in `ProtectModule` and `SwitchModule`
  was not affected.

### New Features

- **`decision/modules.py` — `TrickRoomDisruptionModule` expanded to `FieldSetterDisruptionModule`**
  The module now handles both Trick Room and Tailwind setters:

  * **Trick Room setters** (Farigiraf, Indeedee, Cresselia, etc.) when TR is not yet
    active: ×2.0 — unchanged from previous behaviour.
  * **Tailwind setters** (Tornadus, Whimsicott, Talonflame, Jumpluff, Murkrow,
    Hawlucha, Ribombee, Flamigo) when opponent Tailwind is not yet active: ×1.5 —
    slightly weaker than TR since Tailwind is less permanent.

  Both setter types are identified either by species name or by a revealed move
  ("Trick Room" or "Tailwind" in `opp.moves`).  TR setters take priority in the
  evaluation order so an action is redirected to the TR setter before the Tailwind
  setter when both are present.

  The module is also renamed internally from `name = "trick_room"` to
  `name = "field_setter"` to reflect its expanded scope.

## 0.5.2 — 2026-05-25

### Bug Fixes

- **`decision/modules.py` `ProtectModule` — fix critical-HP consecutive Protect loop**
  At ≤ 5% HP the consecutive-Protect penalty was waived *and* the `CRITICAL_HP_FACTOR`
  (×3.0) bonus was applied, producing a weight of ×7.5 (×2.5 OHKO threat × ×3.0 HP
  bonus) that was impossible for a switch OHKO-escape (×4.0) to overcome.  The result
  was an infinite Protect loop (observed: Aerodactyl at 4.1% HP protected turns 3–5
  while ignoring a Venusaur escape with `switch_eval: OHKO escape` at weight 2.0).

  Fix: when `used_protect_last_turn` AND `critical_hp` the penalty is still waived but
  the `CRITICAL_HP_FACTOR` HP bonus is suppressed.  Only the OHKO-threat bonus (×2.5)
  may apply, capping Protect at 2.5 so a switch OHKO-escape (×4.0) reliably wins.
  A new reason string `"consecutive protect at critical HP (HP bonus suppressed)"`
  is appended for visibility in battle logs.

### Improvements

- **`decision/modules.py` `FieldConditionModule` — penultimate-turn stall**
  Previously the module only boosted Protect on the *last* active turn of opponent
  Tailwind or Trick Room (`turns_left == 1`, ×3.0).  It now also fires one turn
  earlier (`turns_left == 2`, ×2.0) so the bot stalls on turn N−1 as well, letting
  both the penultimate *and* final turns pass safely behind Protect.  The weaker
  ×2.0 multiplier ensures a confirmed OHKO (×5.0) can still override the stall.

## 0.5.1 — 2026-05-25

### Bug Fixes

- **`tools/analyze_battles.py` — Section 7 false positives fixed**
  The consecutive-Protect detector searched for `"used protect last turn"` in
  reason strings, which matched `opp_protect_recency: target used Protect last
  turn` (the *opponent's* Protect recency) rather than our bot's own consecutive
  penalty.  All three previously reported flags were false positives.  Section 7
  now uses cross-turn comparison: it checks whether the same slot chose a
  Protect-family move on turn N−1, which is the only reliable signal since the
  penalised Protect action (weight ×0.1) is too low to surface in the stored
  `acts` list.

- **`recorder.py` — penalised Protect now visible in battle logs**
  When the consecutive-Protect penalty fires, the Protect action (weight ×0.1)
  was always below the `weight > 1.0` cutoff and therefore never written to the
  `acts` array in the JSON.  `_select_actions` now checks whether any ranked
  action carries the `"used Protect last turn"` reason and, if so, always
  appends it to `acts` regardless of weight.  This makes the penalty observable
  in post-game analysis without cross-referencing prior turns.

### New Features

- **`decision/modules.py` — Trick Room disruption module** (`TrickRoomDisruptionModule`)
  When a known Trick Room setter is active and TR is not yet up, the module
  boosts attacks targeting that setter by **×2.0**.  If the setter is already
  the natural best damage target the boost is applied directly.  If a different
  opponent is the current best target the module re-evaluates the move against
  the setter (using the same DamageOutput + ThreatElim formulas) and redirects
  the action when the boosted TR-setter score exceeds the current score.

  Motivation: Farigiraf was the most common opponent lead at 23.1% of battles
  and successfully set Trick Room in multiple games because the bot had no
  mechanism to prioritise attacking it.  With this module, a Kingambit Kowtow
  Cleave (Dark, ×2 vs Farigiraf's Psychic typing) scoring ~7.7 before becomes
  ~30.0 after disruption, reliably redirecting the attack to the TR setter on
  turn 1.

  Known TR setters in Champions Reg M-A:
  `Farigiraf`, `Runerigus`, `Indeedee`, `Indeedee-F`, `Cresselia`, `Bronzong`,
  `Oranguru`, `Hatterene`, `Reuniclus`, `Porygon2`.
  Any species with `"Trick Room"` in its revealed move list is also flagged.

  Module runs after `ThreatEliminationModule` and before
  `OppProtectRecencyModule` in the engine pipeline.

## 0.5.0 — 2026-05-25

### Bug Fixes

- **`data/species.py` — alternate battle-form type lookup** (`_FORM_ALIASES`)
  When Aegislash switched to Blade forme the parser reported its species as
  `"Aegislash-Blade"`.  That key was absent from `smogon_champions_slim.json`,
  so `types_of("Aegislash-Blade")` returned `None` and the damage engine fell
  back to `["Normal"]`.  The consequences were severe:
  - **Close Combat** (Fighting vs Normal → ×2 STAB) was scored as dealing 53%
    damage to Aegislash-Blade; the correct answer is ×0 (Ghost immune to
    Fighting).  Sneasler chose it over actually viable moves.
  - **Sludge Bomb** (Poison vs Normal → ×1 STAB) was scored as dealing 44%
    damage; the correct answer is ×0 (Steel immune to Poison).  Venusaur-Mega
    chose it repeatedly over Earth Power.

  Fixed by adding `_FORM_ALIASES: dict[str, str]` — a table mapping in-battle
  form names to their canonical species entry — and consulting it in
  `get_species()` when an exact match is not found.  Initial entries cover all
  alternate-form species legal in Champions format whose form-specific name
  differs from the database key:

  | Form name | Resolves to | Typing |
  |---|---|---|
  | `Aegislash-Blade` | `Aegislash` | Steel / Ghost |
  | `Aegislash-Shield` | `Aegislash` | Steel / Ghost |
  | `Mimikyu-Busted` | `Mimikyu` | Ghost / Fairy |
  | `Palafin-Hero` | `Palafin` | Water |
  | `Morpeko-Hangry` | `Morpeko` | Electric / Dark |
  | `Greninja-Ash` | `Greninja` | Water / Dark |

  Spotted via turns 4, 6, and 7 of
  `battle-gen9championsvgc2026regma-2617643457`.

- **`data/species.py` — illegal mega entries removed**
  `Metagross-Mega` and `Sceptile-Mega` were present in `_MEGA_SUPPLEMENTS` and
  `_MEGA_ABILITY_SUPPLEMENTS` but absent from both `smogon_champions_slim.json`
  and the sets-usage file, confirming they are not legal in Champions format.
  Both entries removed from all three dicts.
  `Incineroar-Mega` and `Metagross-Mega` weight entries were also removed from
  `POKEMON_WEIGHTS`.

- **`data/species.py` — `Meowstic-Mega` key mismatch**
  The sets file and Showdown both use `"Meowstic-M-Mega"` for the male Meowstic
  mega, but the supplement dicts keyed it as `"Meowstic-Mega"`.  Renamed to
  `"Meowstic-M-Mega"` in `_MEGA_SUPPLEMENTS` and `_MEGA_ABILITY_SUPPLEMENTS`.

### Team Preview Improvements

- **Opponent mega assumptions** (`team_preview.py`)
  Scoring previously used the opponent's base-form typing throughout preview,
  even for Pokémon that virtually always carry a Mega Stone.  The engine now
  maps the top-8 most-used mega-form species (by raw usage count from the sets
  file) to their mega form before computing type matchups.  For species with two
  mega options (Charizard), the more popular form wins automatically.

  Current top-8 (data-driven, recomputed at import time):

  | Preview species | Assumed form |
  |---|---|
  | Floette | Floette-Mega |
  | Charizard | Charizard-Mega-Y |
  | Froslass | Froslass-Mega |
  | Gengar | Gengar-Mega |
  | Meganium | Meganium-Mega |
  | Tyranitar | Tyranitar-Mega |
  | Delphox | Delphox-Mega |
  | Dragonite | Dragonite-Mega |

- **Team preview battle log** (`recorder.py`, `main.py`)
  A `"preview"` block is now written to the top-level of every battle JSON when
  team preview occurs, containing the opponent's revealed team, the slot indices
  chosen, the species names in lead-first order, and the designated mega.
  Allows post-game sanity-checking of team selection decisions.

- **Lead order uses team order** (`team_preview.py`)
  `select_leads` previously returned slots in descending score order, placing
  the highest-scoring mon in slot A.  It now sorts slots by ascending team
  position (i.e. the order the mon appears in `team.txt`), keeping lead
  selection predictable until proper lead logic is implemented.

### Data Layer Cleanup

- **BSS leads data removed** (`data/usage.py`, `data/__init__.py`)
  `Leads-gen9championsbssregma-1760.txt` was a Battle Stadium Singles file
  accidentally included in the project.  `lead_usage()` and `all_leads()` were
  never called by any decision logic.  The file, the two functions, and all
  references in `__init__.py` and the test suite have been removed.

### Test Suite

| Version | Tests |
|---|---|
| 0.4.0 | 344 |
| 0.5.0 | 350 (+6) |

---

## 0.4.0 — 2026-05-24

### Refactor — Project Reorganisation

This release is a pure structural refactor.  No logic was changed; all 297
tests pass.  The goal was to make the codebase easier to navigate and extend
by giving each layer its own home.

- **`battle_state.py`** (new file)
  Extracted `Pokemon` and `BattleState` dataclasses — plus their private
  helpers `_parse_hp` and `_parse_status` — out of `battle.py` into a
  standalone module.  `battle.py` re-imports and re-exports them so all
  existing `from battle import BattleState, Pokemon` call sites work unchanged.
  Modules that need state but not parsing logic (e.g. `recorder.py`,
  `turn_order.py`) can now import `battle_state` directly without pulling in
  the full protocol parser.

- **`decision/` package** (split from `decision.py`)
  The 1 164-line `decision.py` monolith was split into a proper package:
  - `decision/engine.py` — `Action`, `ScoringModule`, `DecisionEngine`,
    `_build_actions`, and the shared constants `_PROTECT_MOVES` /
    `_FAKE_OUT_USERS`.  No imports from the data or team layers — purely
    stdlib + typing.
  - `decision/modules.py` — all nine concrete `ScoringModule` subclasses
    (`DamageOutputModule`, `ThreatEliminationModule`, `PrioritySpeedModule`,
    `ProtectModule`, `FakeOutModule`, `FieldConditionModule`, `SwitchModule`,
    `DoublingUpModule`, `OppProtectRecencyModule`), the internal combatant
    helpers (`_our_combatant`, `_opp_combatant`, `_our_stats`), and the
    `make_engine()` factory.
  - `decision/__init__.py` — re-exports the full public API so every existing
    `from decision import …` import works without change.
  The root-level `decision.py` was deleted after the package was verified.

- **`tools/` folder** (new directory)
  Moved developer/analysis utilities out of the project root:
  - `tools/pack_team.py` — previously `pack_team.py`; `TEAM_FILE` path
    updated for the new location; `main.py` import updated accordingly.
  - `tools/analyze_battles.py` — previously `analyze_battles.py`; `DATA_DIR`
    bumped to `Battle Data\0.4.0`.
  - `tools/__init__.py` — marks the folder as a package.

- **`tests/test_data_layer.py`** (new file, 27 tests)
  The five `data/_*_test.py` scripts (`_smoke_test.py`, `_extended_test.py`,
  `_damage_test.py`, `_decision_test.py`, `_turn_order_test.py`) were manual
  runner scripts that were never picked up by pytest.  Unique test cases for
  data-layer functions not covered elsewhere were migrated into a proper pytest
  file.  The five source scripts were then deleted.
  New coverage: `speed_distribution`, `prob_faster_than`, `update_speed_belief`,
  `update_speed_belief_slower`, `prob_outspeeds`, `lead_usage`,
  `archetype_usage`, `all_archetypes`, `teammate_distribution`,
  `WEATHER_SPEED_ABILITIES`.

### Protocol Parser (Area 3 Audit)

Seven Showdown protocol messages that were previously silently ignored are now
handled by `BattleParser`:

| Message | Handler | Effect |
|---|---|---|
| `\|-terastallize\|` | `_on_terastallize` | Sets `mon.terastallized = True` and `mon.tera_type` |
| `\|cant\|` | `_on_cant` | Clears the slot's last-move so ProtectModule / FakeOutModule don't misread flinch/paralysis as an intentional move |
| `\|-clearboost\|` | `_on_clearboost` | Zeros all stat stages for one Pokémon (Haze, Clear Smog) |
| `\|-clearallboost\|` | `_on_clearallboost` | Zeros stat stages for every Pokémon on the field |
| `\|-invertboost\|` | `_on_invertboost` | Inverts all stat stages (Topsy-Turvy) |
| `\|-setboost\|` | `_on_setboost` | Sets a single stat stage to an explicit value (Psych Up, Guard/Power Swap) |
| `\|-transform\|` | `_on_transform` | Copies target's species and revealed move list onto the transformer (Transform / Imposter) |

Fifteen new tests added in `tests/test_battle_parser.py` (51 total, up from 36).

### Bug Fixes

- **`recorder.py` — HP snapshot bug**
  All turns in every recorded battle file showed the *final* HP values (mostly
  0.0 for fainted Pokémon) rather than the HP at the moment each decision was
  made.  The root cause was `record_decision` storing `entry["state"] = state`
  — a live reference to the mutable `BattleState` object, which continued to
  change as the battle progressed.  When `_save()` ran at the end of the battle
  it read the final field values for every turn.
  Fixed by calling `_snapshot_state(state)` eagerly on the first call per turn;
  this captures weather / terrain / actives / team as plain immutable dicts so
  HP and status values are frozen at decision time regardless of when the file
  is written.

- **`damage.py` — Flower Trick / Frost Breath / Storm Throw always-crit**
  These moves guarantee a critical hit by game mechanic but `full_damage_calc`
  never set `crit=True` for them, so they were calculated at normal damage.
  Fixed by adding `_ALWAYS_CRIT_MOVES` and setting `crit = True` after reading
  move data.
  Also fixed a second bug: `calc_damage` with `crit=True` was not applying the
  Gen 6+ boost-clamping rules.  On a critical hit, the attacker's negative stat
  stages and the defender's positive stat stages are both ignored.  The fix adds
  `atk_boost = max(atk_boost, 0)` and `def_boost = min(def_boost, 0)` before
  the `stat_with_boost` calls whenever `crit` is `True`.

### Decision Engine Improvements

- **`PrioritySpeedModule` — Protect oscillation fix**
  Protect-family moves have priority +4, so `PrioritySpeedModule` was giving
  them an unconditional ×1.5 bonus whenever any opponent might outspeed us.
  This created a weight floor of ≈1.5 that could beat weakly-scoring attacks
  (weight ≈1.4–1.48), causing Protect to win on turns where no genuine threat
  justified it and producing oscillation over consecutive turns.
  `ProtectModule` already manages all Protect scoring deliberately; the fix adds
  an early `continue` in `PrioritySpeedModule` for any move whose name is in
  `_PROTECT_MOVES` so Protect receives no bonus from this module.
  Spotted via Kingambit alternating Protect / attack over turns 7–9 of
  `battle-gen9championsvgc2026regma-2617325206`.

- **`ProtectModule` — numerical-advantage suppression**
  The existing 1v1 endgame suppression (all Protect bonuses disabled when our
  last mon faces the opponent's last mon) was generalised to cover any
  numerical-advantage situation where we have more active Pokémon than the
  opponent.  In a 2v1, Protecting can only produce two outcomes:
  - Opponent targets the Protecting mon → partner attacks anyway; same
    effective result as just attacking, minus one attack.
  - Opponent targets the partner → Protecting mon wasted its turn and the
    opponent survives an extra turn.

  Neither outcome benefits the Protecting mon.  The fix adds
  `numerical_advantage = (our_active_count > active_opp_count > 0)` and
  combines it with `is_1v1_endgame` into a single `suppress_protect` flag.
  When set, all HP and threat bonuses are suppressed and the critical-HP waiver
  of the consecutive-Protect penalty is also blocked — the same rules that
  already applied to 1v1 endgame.
  Spotted via turn 10 of `battle-gen9championsvgc2026regma-2617139560`:
  Aerodactyl-Mega at 1.8% HP chose Protect (w=2.4, critical-HP ×3.0) over
  Dual Wingbeat (w=1.38) in a 2v1.

### Test Suite

| Version | Tests |
|---|---|
| 0.3.5 | 270 |
| 0.4.0 | 344 (+74) |

---

## 0.3.5 — 2026-05-24

### Infrastructure

- **`recorder.py` — Compact battle log format (v2)**
  Rewrote the battle recorder to produce significantly smaller JSON files,
  making logs cheaper to load and analyse with an LLM.
  Changes vs v1:
  - **Per-turn grouping**: both slot 0 and slot 1 decisions for the same turn
    now share a single state snapshot instead of duplicating it — the biggest
    single win (~20–25 % reduction).
  - **HP as fraction**: stored as `0.0–1.0` float instead of `"cur/max"` string.
  - **Abbreviated keys**: `id`, `v`, `t`, `n`, `w`, `te`, `tr`, `my`, `opp`,
    `team`, `dec`, `sl`, `ch`, `acts`, `lb`, `ts`, `sw`, `r`, `sts`, `mv`.
  - **No whitespace**: `separators=(',',':')` instead of `indent=2` (~30 %
    reduction on larger files).
  - **Null/empty fields omitted**.
  - **Top-N actions only**: up to 4 actions with weight > 1.0 per slot
    (minimum 3, chosen action always included), dropping irrelevant tail
    moves that scored 1.0.
  - **Path fix**: `_save()` now uses `"Battle Data"` (correct capitalisation)
    instead of `"battle data"`.
  Combined reduction: ~55–65 % smaller files vs v1.

- **`analyze_battles.py` — Updated for v2 format**
  Rewrote all field accesses to match the new schema.  `parse_hp()` removed
  (HP is now a float).  New `all_slot_decisions()` / `decisions_per_turn()`
  helpers flatten the turn-grouped structure for the analysis sections.
  `DATA_DIR` updated to `Battle Data\0.3.5`.

---

## 0.3.4 — 2026-05-24

### Bug Fixes

- **`team.py` — Basculegion-F/M gender form mismatch** (`find_member`)
  Showdown's battle protocol reports our own Pokémon using the base species
  name (e.g. `"Basculegion"`) rather than the gendered form name stored in
  `team.txt` (`"Basculegion-F"`).  `find_member` was only matching in the
  forward direction (battle sends form name, team stores base name), so
  `find_member("Basculegion")` returned `None` whenever Basculegion-F was
  active.  This caused `DamageOutputModule`, `ThreatEliminationModule`, and
  `ProtectModule` to all exit early, leaving every attack at weight 1.0 and
  Protect winning by default from `PrioritySpeedModule` alone.
  Fixed by adding a reverse check: `m.name.startswith(species + "-")`.
  Works for both `-F` and `-M` forms.

### Decision Engine Improvements

- **`ProtectModule` — 1v1 endgame suppression**
  When the bot is the last Pokémon standing and exactly one opponent remains,
  Protecting gains nothing — it delays the loss by one turn without changing
  the outcome.  All HP and threat bonuses (`CRITICAL_HP_FACTOR ×3.0`,
  `LOW_HP_FACTOR ×1.5`, `THREATENED_FACTOR ×2.5`) are now suppressed in this
  scenario so attack moves beat Protect at any HP level.  The consecutive
  Protect penalty (`×0.1`) is also no longer waived at critical HP in a 1v1.

- **`DoublingUpModule` — confirmed-OHKO redirect**
  Previously, when the partner had a confirmed OHKO (weight ≥ 15) on the
  shared target, all of the second slot's attacks received the `×0.05`
  near-veto, making Protect the default winner.  The module now checks for an
  alternative active opponent first.  If one exists, attacks are redirected to
  that target with no penalty instead of being near-vetoed, ensuring the bot
  attacks the surviving threat rather than wasting a turn on Protect.

---

## 0.3.3 — 2026-05-24

### Bug Fixes

- **`battle.py` — Trick Room detection** (`_on_fieldstart` / `_on_fieldend`)
  Showdown sends `-fieldstart|move: Trick Room`.  The handler was checking for
  `"trickroom"` (no space) after stripping the `move: ` prefix, but the
  cleaned string contains `"trick room"` (with space).  Both handlers now use
  `"trick room" in clean.lower()`.

- **`damage.py` — Weight-based move power** (Low Kick, Grass Knot, Heat Crash, Heavy Slam)
  These moves have `power: 0` in the Champions database, triggering the
  early-return in `full_damage_calc` before any scoring occurred.  Added
  `_low_kick_power` and `_heat_crash_power` helpers that compute effective BP
  from species weights, with a fallback of 50 kg (→ 80 BP) for unknown species.
  `get_weight` added to `data/species.py` with a 120+ entry lookup table.

### Decision Engine Improvements

- **`decision.py` — Weather-speed ability inference** (`_opp_combatant`)
  When an opponent's ability is unknown and weather is active, the engine now
  infers a weather-speed ability from the species' ability list (e.g. Sand Rush
  on Excadrill in sandstorm, Swift Swim on Kingdra in rain).  Prevents the bot
  from incorrectly assuming it outspeeds a ×2 speed-boosted opponent.

- **`SwitchModule` — OHKO-escape safety check**
  The OHKO-escape switch bonus (`×4.0` / `×2.0`) is now capped at `×0.8` if
  the incoming bench Pokémon would also be immediately OHKO-threatened by the
  active opponents, preventing the bot from escaping into an equally bad
  matchup.

- **`DoublingUpModule` — confirmed-OHKO near-veto**
  When the partner's committed action has a combined weight ≥ 15 (indicating a
  confirmed OHKO), attacks targeting the same slot receive a `×0.05` near-veto
  on top of the normal doubling-up penalty, redirecting damage to the surviving
  opponent.  Threshold of 10–15 applies a lighter `×0.65` redirect.

- **`OppProtectRecencyModule`** (new module)
  Applies a `×1.3` boost to attacks whose `target_slot` points at an opponent
  that used a Protect-family move last turn.  Consecutive Protect has a
  drastically reduced success rate, so these attacks are unlikely to be wasted.

---

## 0.3.2 and earlier

Initial versions. No changelog recorded.
