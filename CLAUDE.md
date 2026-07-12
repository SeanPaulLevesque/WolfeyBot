# WolfeyBot — Project Guide for Claude

## What this project is

WolfeyBot is a Gen 9 VGC doubles bot that plays on Pokémon Showdown in the
**Champions format**. The live ladder rolled from Reg M-A to **Reg M-B** on
2026-06-17 (`BATTLE_FORMAT` in `main.py` is `gen9championsvgc2026regmb`); the
data/usage layer runs on the real Smogon **M-B** dumps since 0.37.0. It
connects via WebSocket, parses the battle protocol, and chooses moves using a
two-phase scoring engine (19 per-slot modules + 7 joint adjusters; see the
pipeline section below).

---

## Testing workflow — when a test fails, STOP and review together (IMPORTANT)

A failing test is a **signal to stop and review with the user**, never something
to make green by editing expectations. This is a hard rule:

- **Never edit a test's expected values/assertions, and never delete, skip, or
  `xfail` a test, to make it pass.** That throws away the regression guard.
- **On any failure, stop and surface it** — report (a) which test, (b) what it
  asserted, (c) what the code now produces, and (d) *why* the behavior changed —
  then **ask whether the new behavior is correct before changing anything.**
- A failure is exactly one of two things; decide **together** which:
  1. **Real regression** → fix the **code**, not the test.
  2. **Intended behavior change** → update the test *only after the user agrees*
     the new behavior is correct.
- **This applies to generated/bulk expectation tables too** (`snapshots/turn1_openings/baseline.md`,
  `tests/test_turn1_decisions.py`, etc.). Do **not** regenerate expected values
  wholesale to clear failures. Regeneration is allowed **only after** the user has
  reviewed and approved the behavior change that produced the diff — and even
  then, spot-check that the new values are actually correct, don't just trust the
  engine's current output.
- Editing a test is the **last** step, after agreement — never the reflex.

---

## Key files

| File | Purpose |
|---|---|
| `main.py` | WebSocket client — connects to Showdown, drives the game loop |
| `battle.py` / `battle_state.py` | `BattleState` and `Pokemon` dataclasses; battle protocol parser |
| `decision/engine.py` | `Action`, `ScoringModule`, `DecisionEngine`, `_build_actions` |
| `decision/modules.py` | All 19 per-slot modules + 7 joint adjusters + `make_engine()` factory |
| `team.py` | `find_member(species)` + active-team selector (`set_active_team`, `get_team`, `list_teams`, `validate_team`, `resolve_team_spec`) |
| `teams/` | Named ladder teams for A/B testing: `teams/<name>/v<n>.txt` pastes + `teams.json` manifest (name → label, account, current version). See `teams/README.md` |
| `snapshots/` | Decision-snapshot regression subsystem: `baseline_team.txt` (frozen baseline roster, the no-`--team` fallback) + `<scenario>/<team>.md` generated tables |
| `scenarios/` | Team-agnostic board-state templates; `turn1_openings.py` is the 6-lead × 20-opp turn-1 scenario |
| `damage.py` | `outgoing_damage()`, `incoming_damage()`, `type_effectiveness()` |
| `turn_order.py` | `will_outspeed()`, `priority_bracket()`, `Combatant` dataclass |
| `data/` | Usage: `moves-gen9championsvgc2026regmb-1760.txt` (Smogon M-B moveset dump → `sets.py`; "No Ability"/"Other" filtered at parse) + `leads-gen9championsvgc2026regmb-1760.txt` (ladder lead prior — a sub-observation tiebreak in `lead_stats.predict_pair`, never outranking our observed pair data). Dex: `smogon_champions_slim.json` (species/types/base stats) + `champions_moves/items/abilities/megas.json`. `sets_supplement.json` = hand-entered gap-fill merged at load (~empty; Watchog only) — the escape hatch for the next reg roll |
| `team_preview.py` | Bring-4 selection logic |
| `docs/DECISION_ARCHITECTURE.md` | Full narrative of how the engine works, with weight tables |
| `tools/` | Dev/analysis scripts (see "Running things" for the prompt-free fixed-command set). Investigation: `inspect_battle.py <id> [--turn N]` (turn-by-turn log summary), `replay_turn.py <id> <turn>` (rebuild a logged board, run the **current** engine — the "would the fix change this?" tool), `team_report.py <dir>` (roster-perf + prediction-accuracy report), `turns_vs_lead.py`, `endgame_autopsy.py`, `preview_backtest.py`. `scratch.py` = gitignored ad-hoc-analysis slot. |
| `CHANGELOG.md` | Per-version bug fixes — always check before investigating a bug |
| `snapshots/turn1_openings/baseline.md` | Generated first-turn decision table (6 our leads × 20 opp leads) for the baseline roster |
| `tests/` | pytest suite — run with `.venv\Scripts\pytest` |

**Teams:** the ladder roster is `teams/meta-team/v<n>.txt` (current version in
`teams.json`); `snapshots/baseline_team.txt` (= meta-team v1) is the frozen
no-`--team` fallback the snapshots pin against. `main.py --list-teams` prints
the rosters + accounts.

---

## Decision engine pipeline (two phases, since 0.7.0)

**Actions are `(move, target)` pairs.** `_build_actions` emits one candidate per
live opponent for every single-target move (fixed `target_slot`), so *which
target* is part of the action's identity — not a field that modules pick and
overwrite. Spread/status/self moves and switches are single candidates
(`target_slot=None`).

### Phase 1 — per-slot scoring (19 modules)
Each candidate starts at `weight = 1.0`; modules multiply — never add. A slot is
scored **in isolation** (blind to the partner) over its own candidates. The
numbering matches `docs/DECISION_ARCHITECTURE.md` and the `make_engine` list, but
**phase 1 is order-independent**: every module multiplies from precomputed
`TurnContext` facts and reads neither the running weight nor another module's
reasons, so the order is for readability only.

| # | Module | What it does |
|---|---|---|
| 1 | DamageOutput | `×(DAMAGE_INTERCEPT + DAMAGE_SLOPE × min(dmg_fraction, 1))` = `×(0.5 + 3.5×d)` scored against the candidate's **own** fixed target (spread/status: best live foe). **dmg_fraction is capped at 1.0 (lethal):** damage value saturates at the target's remaining HP, so overkill earns nothing — this is what lets `coordinate` route the right attacker (two equal OHKOs → the pairing falls to the chip that differs, not to whichever foe is overkilled hardest). Trade-off (accepted): a guaranteed KO via an overkill move no longer out-weights everything, so in rare cells it can yield to a switch/Protect. Damage modifiers come from the shared `_outgoing_attacker_mods(mon)` / `_outgoing_defender_mods(state, opp)` helpers (boosts, burn/status, HP, Flash Fire, times_hit / opp boosts, current HP, screens) — the single source of truth all `outgoing_damage` callers splat in, so a new modifier added there is picked up everywhere |
| 2 | ThreatElimination | "Can I guarantee a kill?" → ×5.0 when `ctx.guarantees_ohko(slot, move, its target)`. **Unconditional** now — the "will I die before I act?" ×0.2 cancel is a separate `DoomedModule` (#3). No target override (target is fixed) |
| 3 | Doomed | **Per-candidate** (`_move_undeliverable`): ×0.2 on each attack a certain killer would land before — so a priority move that out-speeds the threat is spared (revenge-KO) while slower moves are cut; Protect/switch untouched. Split out of ThreatElimination |
| 4 | PriorityKill | ×3.0 on a **priority** move (`priority_bracket > 0`) that `ctx.guarantees_ohko`s its target — it removes the foe before it can act, so prefer the priority KO over a slower one. Gated on guaranteed OHKO, so weak non-KO priority moves get nothing |
| 5 | PriorityBlock | ×0 on a **priority** attack while any live opponent has a priority-block ability (`_PRIORITY_BLOCK_ABILITIES` = Armor Tail / Queenly Majesty) — these block priority vs the holder *and its ally*, so it can't connect. Protect/switch/non-priority untouched; reads `_effective_ability` (assumes Armor Tail on an unrevealed Farigiraf). Composes with #4 (3.0×0=0) |
| 6 | ProtectValue | **Single row** on Protect-family moves when `ctx.is_threatened(slot)`: ×2.5. The partner-clears ×3.0 is now a phase-2 adjuster (`PartnerClearsAdjuster`, J6); the 1v1/2v1 "Protect only delays" ×0.4 cancels are a separate `EndgameStallModule` (#7) — one concern per module |
| 7 | EndgameStall | Protect ×0.2 when `ctx.is_threatened(slot)` and the board is a 1v1 endgame or 2v1 advantage (Protect only delays; ×0.4 → ×0.2 in 0.44.1, user-tuned — net with ProtectValue's ×2.5 is 0.5). Split out of ProtectValue |
| 8 | TurnOrder | By rank in the 4-mon turn order (pos 1 = we act before all 3 other actives): pos 1 ×2.0; pos 2 ×1.5; pos 3 ×1.0; pos 4 ×0.75 — attacks only |
| 9 | Urgency | One urgency boost per turn, first applicable setup in `_SETUP_TYPES` order (TR first): a setter present & its effect stoppable (not active, or last turn) → all attacks ×`SETUP_URGENCY` (flat ×2 for any setup). Target-agnostic — bias toward attacking, not stalling. Walks the shared `_SETUP_TYPES` registry, so a new urgent setup (screens, …) is one new row. (No TR↔TW cross-guard: the meta runs no mixed TR+TW teams.) |
| 10 | Setup Denial | A candidate aimed at a setter it guaranteed-OHKOs (`ctx.ohko`), that we outspeed, whose setup move has no +1 priority (Prankster/Gale Wings) → ×`SETUP_DENIAL` (flat ×2 for any setup). At most one denial per action (TR claim wins); active effects can't be denied. Same shared `_SETUP_TYPES` registry as Urgency (#9) |
| 11 | OppProtectRecency | ×1.3 if the candidate's target used Protect last turn |
| 12 | ConsecutiveProtect | ×0.2 if we used Protect last turn — no exceptions |
| 13 | FakeOut | `ctx.fake_out_fired(slot)` (fresh Fake Out user on field): Protect ×2.0, all attacks ×0.5 — for **every** slot |
| 14 | FieldCondition | turns_left=1 or 3 → Protect ×3.0 (stall every other turn) |
| 15 | Redirection | Hedge single-target attacks vs an active Rage Powder / Follow Me user: ×(damage to the redirector, capped 1.0); immune→×0, OHKO-on-redirector→×1.0. Exempts spread/status/switch, a Stalwart/Propeller-Tail attacker, and (Rage Powder) a Grass / Overcoat / Safety-Goggles attacker |
| 16 | SwitchTempo | Flat cost of switching at all: ×0.8 on every switch (forfeit the turn + concede a free hit). A switch must earn its keep via #17/#18 |
| 17 | SwitchOffense | ×(1+g), `g = max(0, switch_in_offense − current_offense)` (best single hit to the live foes). Floored at 0 — a softer-hitting defensive switch isn't penalised here. `_best_offense` is full-damage-modifier-aware via the shared `_outgoing_*_mods` helpers, for **both** the current mon (its boosts/burn/HP) and the switch-in (its own — e.g. a persistent burn), and the opponent's boosts/screens — so a debuffed mon vs a +Def wall is judged on the real board |
| 18 | SwitchSafety | One `_switch_in_survives` board check: ×4.0 if the current mon faces a connecting OHKO and the switch-in survives (escape); ×0.3 if the switch-in is itself OHKO'd (soft discount, not a veto). Same-bench-mon collision is phase 2. `_switch_in_survives` (and the active-mon threat facts in `build_turn_context`) are full-modifier-aware via the shared `_incoming_attacker_mods(opp)` / `_incoming_defender_mods(state, mon)` helpers — so a +Atk foe / our screens / our boosts all count |
| 19 | BoostedTarget | Attacks aimed at a stat-boosted opponent ×(1 + 0.4 × Σ positive stages) — 1 stage ×1.4, 2 ×1.8. Punish the snowball (endgame autopsy: opp boosted in 61% of late loss-turns vs 38% in wins). Positive stages only (accuracy/evasion count); spread attacks take the most-boosted live foe; Protect/switches untouched |

### Phase 2 — joint coordination (`DecisionEngine.coordinate`)
Phase 1 yields a ranked candidate list per slot. `coordinate` then picks the
**best joint pair** — `argmax (w0·factor_a)·(w1·factor_b)` over all candidate
pairs — where the `JointAdjuster`s below are the *only* cross-slot effects. With
all factors 1.0 the argmax is each slot's independent best, so coordination only
moves a choice off the per-slot optimum when a real interaction makes another pair
better. The chosen pair's per-slot factors are **baked into** the actions'
weights (so a decision's weight reflects the joint effects). `main.py` runs the
turn as: phase-1 score all → `coordinate` → record/mega/emit.

| Adjuster | Effect (per-slot factor on the pair) |
|---|---|
| Doubling | Both attack the same target: flat ×0.4 (penalty on the higher slot) — the spread-your-damage tax. Just the base penalty; the overkill near-veto is its own adjuster |
| Overkill | One slot already guarantees the OHKO on the shared target → ×0.05 near-veto on the *non-killer* (wasteful doubler), so the pair that **spreads** onto the survivor wins (emergent "redirect"). Composes on top of Doubling |
| JointSetupDenial | Both attack the same `_SETUP_TYPES` **setter**, neither solo-OHKOs it, but the summed **min rolls** kill it and both attacks resolve before it moves → waive the doubling tax (×1/0.4) and apply ×`SETUP_DENIAL` (×2). The combined kill no per-slot module can see (born from the 8-52 Swampert+Pelipper record: two ~0.7 hits kill Pelipper pre-Tailwind, but the doubling tax kept routing the second attacker onto Swampert). Reads `ctx.min_dmg` |
| Coordination | A **gratuitous** lone Protect (no `incoming_ohko`/`protect:`/`field_condition` reason) beside an attacking partner: ×0.5 on the Protect → favour double-attack; justified Protects and double-Protects untouched |
| FakeOut (free) | When **either** slot attacks, divide the partner's Fake-Out multiplier back out (attack un-halved, Protect un-boosted; known from `ctx.fake_out` + the action type) — a pair pays the Fake-Out adjustment once, never twice; symmetric since 0.7.2 |
| SwitchCollision | Both slots switch to the **same** bench mon → ×0 |
| PartnerClears | One slot Protects against a connecting OHKO **and** the partner's chosen attack guaranteed-OHKOs that threatener → ×3.0 on the Protect (survive while the partner removes it). Was a phase-1 ProtectValue row; moved to phase 2 because "is the threat cleared?" depends on the partner's actual action |

There is no scoring-order blind spot: slot 0 is never committed before slot 1 is
seen. The old greedy + `recoordinate` re-pass (0.6.8–0.6.10) is gone — its
overkill-redirect and gratuitous-Protect repairs are now emergent from choosing
the best pair.

### Key invariants (modules.py) — the rules that prevent recurring bugs
- **`TurnContext` is the single fact source.** `build_turn_context` runs **all**
  yes/no damage calcs (`ohko`, `doomed[slot]`, `incoming_ohko/certain[slot]`,
  `neutralized[opp_slot]`, `fake_out`, `min_dmg`) **once per turn**, cached by
  `_ensure_turn_ctx(state)` (keyed on `state.turn`). Modules read facts, never
  recompute. `_partner_can_ohko` / `_ko_before_acting` etc. are thin readers
  (tests patch them as seams).
- **Damage modifiers live in the shared helpers** — `_field_kwargs(state)` +
  `_outgoing/_incoming_attacker_mods` / `_*_defender_mods`. Every
  `outgoing_damage`/`incoming_damage` caller splats these, so a new modifier
  (weather, terrain, boosts, screens, type override, item belief) is added in
  **one** place and picked up everywhere.
- **Forme resolution — two helpers, never key off raw `mon.species`.**
  `_assumed_species(mon)` = the **modelling** answer (population-weighted forme:
  pre-mega Charizard → Charizard-Mega-Y; revealed mega/non-stone item override;
  `types_override` for a committed Protean); all stats/types/ability/speed use
  it. `data.base_forme(name)` = **identity** only (strip mega suffix for set
  membership / log matching). The species sets (`_FAKE_OUT_USERS`,
  `_TR_SETTER_SPECIES`, `_TAILWIND_SETTER_SPECIES`) hold **base names only**
  (enforced by `test_no_mega_entries_in_species_sets`); predicates compose as
  `base_forme(_assumed_species(mon)) in <SET>`.
- **Every opponent fact goes through an inference seam** — `_assumed_species`,
  `_effective_ability` (revealed > top-usage of the assumed forme), `_opp_item`
  / `_opp_has_item` (Poltergeist's "holds any item?" belief), `_choice_locked_move`.
  Item belief is a usage-stats prior resolved against `ItemEvidence`
  (battle_state.py, ident-keyed so it survives per-switch object replacement;
  fed by the parser: ≥2 moves/stint rules out Choice, speed observations rule
  Scarf in/out). This one belief feeds **both** damage and the speed pipeline
  (`turn_order` via `data.items.speed_multiplier`).

---

## Important API patterns

### Building a test BattleState
```python
from battle import BattleState, Pokemon
from decision.modules import make_engine
from team import find_member

s = BattleState(battle_id="test", my_side="p1")
s.my_actives = [make_our_mon("Garchomp"), make_our_mon("Kingambit")]
s.my_team = list(s.my_actives)
s.opp_actives = [make_opp_mon("Incineroar"), make_opp_mon("Farigiraf")]
s.available_switches = [make_our_mon(b) for b in bench]
s.moves_per_slot = [[{"move": m} for m in tm.moves], [...]]
s.my_last_moves = ["", ""]
s.opp_last_moves = ["", ""]
s.my_slot_decisions = [None, None]
s.my_disabled_moves = [None, None]   # required
s.my_encored_moves = [None, None]    # required
s.opp_tailwind = False
s.opp_tailwind_turns_left = 0
s.trick_room = False
s.trick_room_turns_left = 0
s.weather = None
s.my_tailwind = False
```

**Opponent Pokémon at unknown HP:** use `hp=100, max_hp=100, hp_is_percentage=True`
→ engine uses typical-spread stats for damage calcs.

**Our Pokémon:** use `find_member(species)` to get actual stats/item/ability.
On Turn 1, use pre-mega species name (e.g. `"Aerodactyl"`, not `"Aerodactyl-Mega"`).

### Scoring
```python
engine = make_engine()
ranked = engine.scored_actions(state, slot)   # list sorted best-first
best = ranked[0]                              # Action with .move_name / .switch_target / .weight / .reasons
```

---

## Running things

```
# Run the bot (defaults to --team meta-team; baseline roster if that can't resolve)
.venv\Scripts\python.exe main.py
.venv\Scripts\python.exe main.py --team meta-team@v1   # pin a version to A/B
.venv\Scripts\python.exe main.py --team off-meta-team  # runs on its bound account
.venv\Scripts\python.exe main.py --list-teams          # teams + accounts + validation
.venv\Scripts\python.exe main.py --max-games 5         # play N games then self-stop
.venv\Scripts\python.exe main.py --team ""             # force the baseline roster

# Run tests
.venv\Scripts\pytest

# Regenerate a decision snapshot (only after an approved behavior change)
.venv\Scripts\python.exe tools/gen_snapshot.py --scenario turn1_openings --team baseline
```

**Never prefix shell commands with `cd` — or `timeout`, or anything else.**
The tool's working directory is already the project root and persists between
calls. Allowlist entries are **prefix matches** (the first token must be the
allowlisted binary), so ANY prefix — `cd <repo> && ...`, `timeout 100
.venv/Scripts/pytest -q` — defeats them and forces a manual approval every
single time. Run commands bare with relative paths (`.venv\Scripts\pytest
-q`); if a command might hang, use the Bash tool's own `timeout` parameter,
never a shell `timeout` prefix.

**No `$(...)` command substitution, no `>`/`>>` shell writes — anywhere, ever.**
`$()` nests arbitrary commands, so it forces approval no matter what it wraps
— `sed -n "$(grep -n 'X' f),+10p" f` (the code-reading one-liner) burned ~6
approvals in one sitting. Locate code with the **Grep tool** (`-n`, `-A/-B/-C`
context) and read it with the **Read tool** (offset/limit) — both prompt-free.
Shell writes (`printf ... >> file`) are the Edit/Write tools' job.

**No heredocs, no `cat >> file` appends.** `python - <<PY` and `cat >> x
<<EOF` are arbitrary-code/write prompts that can never be safely allowlisted.
Instead:
- **File changes** (code, tests, docs) → the Edit/Write tools, always.
- **Ad-hoc analysis** → Write the snippet to **`tools/scratch.py`** (the
  designated gitignored scratch slot) and run it — `tools/*` is allowlisted,
  so this is prompt-free; overwrite it freely per investigation.
- **Releases** → `tools/release.py <version> --notes <file>` does the whole
  chore (version bump + CHANGELOG prepend from the notes file + snapshot
  regen + full suite) in one allowlisted call. Write the notes body with the
  Write tool first.

**Permissions (2026-07-10):** file Read/Edit/Write is auto-allowed **only
inside this project** (`.claude/settings.json` path-scoped rules); anything
outside — home dir, AppData, other repos, the `~/.claude` memory files —
prompts. So keep scratch **inside the repo**: commit messages / release notes
go in the gitignored `tools/scratch/` dir (not the AppData scratchpad, which
now prompts), and ad-hoc analysis stays `tools/scratch.py`.

**FIXED COMMAND STRINGS — the only thing that stops the approval prompts
(2026-07-10).** This desktop client **ignores hand-edited allow rules** in
`.claude/settings.json` / `settings.local.json` (proven across a restart, both
glob `*` and regex `.*` forms). It only honours rules it writes itself when
the user clicks **"Always allow"**, and it keys them to the **exact command
string**. So a command whose arguments vary (version, message, battle id,
paths, a `-c` snippet) re-prompts every single time. The fix is to make every
routine op an **unchanging command** — push the variability into a file the
script reads, not the command line. The user "Always allow"s each once; then
it's permanent. The full fixed set (invoke **exactly** as written, no args):
- tests → `.venv\Scripts\python.exe -m pytest -q` (always the full suite;
  a specific test file is a varying arg and will re-prompt)
- analysis → `.venv\Scripts\python.exe tools/scratch.py` (put the snippet
  IN the file; never pass args, never a `-c` one-liner)
- snapshots → `.venv\Scripts\python.exe tools/regen_snapshots.py`
- code commit → write `tools/scratch/commit.json`
  (`{"message"|"message_file", "paths":[...]}`) then
  `.venv\Scripts\python.exe tools/commit_code.py` (no args)
- release → write `tools/scratch/release.json`
  (`{"version", "notes_file"}`) + the notes body, then
  `.venv\Scripts\python.exe tools/release.py` (no args)
- data commit → `.venv\Scripts\python.exe tools/commit_push_data.py`
- games → `.venv\Scripts\python.exe tools/run_games.py`
When a script can't take a fixed form, **extend the script** to read a fixed
scratch file rather than passing args. Destructive git (checkout --, reset,
rm) stays manual on purpose.

---

## Backlog & version

- **Open tasks / ideas live in `BACKLOG.md`** — check it before starting new
  work; don't duplicate the task list here.
- **Version:** single source of truth is `version.py` (`__version__`), imported
  by `main.py` + `tools/gen_snapshot.py`; `tools/release.py` bumps it. Full
  per-version history is in `CHANGELOG.md` — check it before investigating a bug.

---

## Compact instructions

When compacting, always preserve:
- The two-phase pipeline (19 per-slot modules multiply → `coordinate` argmax
  over pairs) and the Key-invariants section above
- Any weight bug under investigation and which matchups reproduce it
- Key file paths and the test-BattleState / scored_actions API patterns
- The fixed-command workflow (approvals) and current engine version
