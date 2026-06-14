# WolfeyBot Changelog

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
