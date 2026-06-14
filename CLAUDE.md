# WolfeyBot — Project Guide for Claude

## What this project is

WolfeyBot is a Gen 9 VGC doubles bot that plays on Pokémon Showdown in the
**Champions format (Reg MA)**. It connects via WebSocket, parses the battle
protocol, and chooses moves using a two-phase scoring engine (12 per-slot
modules + 4 joint adjusters; see the pipeline section below).

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
- **This applies to generated/bulk expectation tables too** (`turn1_summary.md`,
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
| `decision/modules.py` | All 13 concrete modules + `make_engine()` factory |
| `team.py` | `find_member(species)` — returns team member data from `team.txt` |
| `team.txt` | Pokémon Showdown paste of the current 6-mon roster |
| `damage.py` | `outgoing_damage()`, `incoming_damage()`, `type_effectiveness()` |
| `turn_order.py` | `will_outspeed()`, `priority_bracket()`, `Combatant` dataclass |
| `data/` | `smogon_champions_slim.json` (218 Champions-legal species) + move/type data |
| `team_preview.py` | Bring-4 selection logic |
| `docs/DECISION_ARCHITECTURE.md` | Full narrative of how the engine works, with weight tables |
| `tools/` | Dev/analysis scripts: battle analysis, lead stats, ELO chart, team packing |
| `CHANGELOG.md` | Per-version bug fixes — always check before investigating a bug |
| `turn1_summary.md` | Generated first-turn decision table (5 our leads × 20 opp leads) |
| `_gen_turn1_summary.py` | Script that produces `turn1_summary.md` |
| `tests/` | pytest suite — run with `.venv\Scripts\pytest` |

---

## Current team (team.txt)

| Pokémon | Item | Ability | Nature | Key moves |
|---|---|---|---|---|
| Aerodactyl | Aerodactylite | Unnerve | Jolly | Dual Wingbeat / Rock Tomb / Ice Fang / Protect |
| Kingambit | Chople Berry | Defiant | Adamant | Kowtow Cleave / Iron Head / Low Kick / Protect |
| Sneasler | White Herb | Unburden | Jolly | Close Combat / Dire Claw / Rock Tomb / Protect |
| Basculegion-M | Sitrus Berry | Adaptability | Adamant | Liquidation / Last Respects / Psychic Fangs / Protect |
| Venusaur | Venusaurite | Chlorophyll | Modest | Sludge Bomb / Giga Drain / Earth Power / Protect |
| Garchomp | Choice Scarf | Rough Skin | Adamant | Dragon Claw / Stomping Tantrum / Poison Jab / Rock Tomb |

---

## Decision engine pipeline (two phases, since 0.7.0)

**Actions are `(move, target)` pairs.** `_build_actions` emits one candidate per
live opponent for every single-target move (fixed `target_slot`), so *which
target* is part of the action's identity — not a field that modules pick and
overwrite. Spread/status/self moves and switches are single candidates
(`target_slot=None`).

### Phase 1 — per-slot scoring (11 modules, in order)
Each candidate starts at `weight = 1.0`; modules multiply — never add. A slot is
scored **in isolation** (blind to the partner) over its own candidates.

| # | Module | What it does |
|---|---|---|
| 1 | DamageOutput | `×(1 + dmg_fraction × 2.0)` scored against the candidate's **own** fixed target (spread/status: best live foe) |
| 2 | ThreatElimination | "Can I guarantee a kill?" → ×5.0 when `ctx.guarantees_ohko(slot, move, its target)`. "Will I die before I act?" → if `ctx.is_doomed(slot)`, the same kill candidate gets ×0.2 (cancels the ×5; net ×1.0). No target override (target is fixed) |
| 3 | ProtectValue | Four multiplicative rows on Protect-family moves when `ctx.is_threatened(slot)`: ×2.5 always; ×3.0 if a partner can guaranteed-OHKO any threat; ×0.4 in 1v1 endgame; ×0.4 in 2v1 (mutually exclusive with 1v1). Net in 2v1 with partner clearing: 2.5×3.0×0.4=3.0 |
| 4 | TurnOrder | By rank in the 4-mon turn order (pos 1 = we act before all 3 other actives): pos 1 ×2.0; pos 2 ×1.5; pos 3 ×1.0; pos 4 ×0.75 — attacks only |
| 5 | SetterUrgency | One urgency boost per turn, TR first (if/elif): TR setter present & TR not active (or last turn) & no opp TW → all attacks ×2.0; **else** TW setter present & TW not active (or last turn) & no TR → all attacks ×1.5. Target-agnostic — bias toward attacking, not stalling |
| 6 | SetterDenial | A candidate aimed at a setter it guaranteed-OHKOs (`ctx.ohko`), that we outspeed, whose setup move has no +1 priority (Prankster/Gale Wings) → TR setter ×2.0, TW setter ×1.5. At most one denial per action (TR claim wins); active effects can't be denied |
| 7 | OppProtectRecency | ×1.3 if the candidate's target used Protect last turn |
| 8 | ConsecutiveProtect | ×0.2 if we used Protect last turn — no exceptions |
| 9 | FakeOut | `ctx.fake_out_fired(slot)` (fresh Fake Out user on field): Protect ×2.0, all attacks ×0.5 — for **every** slot |
| 10 | FieldCondition | turns_left=1 or 3 → Protect ×3.0 (stall every other turn) |
| 11 | Switch | Board-value (1-ply): `TEMPO×(1+g)×escape×safety` — TEMPO=0.6, g=offense gain, escape=×4.0 if escaping a connecting OHKO into a survivor, safety=×0.3 if switch-in OHKO'd (no same-mon veto — that's phase 2) |

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
| Doubling | Both attack the same target: ×0.40–0.70 (penalty on the higher slot); if one slot already confirms the OHKO, ×0.05 **overkill** near-veto on the *non-killer* → the pair that **spreads** onto the survivor wins (emergent "redirect") |
| Coordination | A **gratuitous** lone Protect (no `incoming_ohko`/`protect:`/`field_condition` reason) beside an attacking partner: ×0.5 on the Protect → favour double-attack; justified Protects and double-Protects untouched |
| FakeOut (free) | When **either** slot attacks, divide the partner's Fake-Out multiplier back out (attack un-halved, Protect un-boosted; known from `ctx.fake_out` + the action type) — a pair pays the Fake-Out adjustment once, never twice; symmetric since 0.7.2 |
| SwitchCollision | Both slots switch to the **same** bench mon → ×0 |

There is no scoring-order blind spot: slot 0 is never committed before slot 1 is
seen. The old greedy + `recoordinate` re-pass (0.6.8–0.6.10) is gone — its
overkill-redirect and gratuitous-Protect repairs are now emergent from choosing
the best pair.

### Key constants in engine.py / modules.py
- `TurnContext` (modules.py) — per-turn precomputed facts: `doomed[slot]` (KO'd
  before acting), `ohko` (set of `(slot, move, opp_slot)` guaranteed-OHKO
  triples), `incoming_ohko[slot]` / `incoming_certain[slot]` (opp slots whose
  max / min roll OHKOs us), `neutralized[opp_slot]` (opp KO'd before it acts),
  `fake_out[slot]` (Fake-Out adjustment applies), and board counts behind the
  1v1/2v1 rows. Built once per turn by `build_turn_context` — the **only**
  place damage calcs run for yes/no facts — and cached via
  `_ensure_turn_ctx(state)` (keyed on `state.turn`). `_partner_can_ohko` /
  `_opp_neutralized_before_acting` / `_ko_before_acting` are thin fact readers
  (tests patch them as seams; the build passes the partial ctx explicitly)
- **Opponent inference seams (modules.py, since 0.7.6)** — every fact about an
  unrevealed opponent goes through three helpers: `_assumed_species(mon)`
  (population-weighted forme via `data.assumed_forme` — a pre-mega Charizard
  is modelled as Charizard-Mega-Y; revealed mega or revealed non-stone item
  overrides), `_effective_ability(mon)` (revealed > top-usage ability of the
  assumed forme), `_effective_item(mon)` (revealed > consumed→None > top-usage
  item if ≥40%, `_ASSUMED_ITEM_MIN_PCT`). Assumed items feed **all** damage
  math; Focus Sash/Sturdy set `DamageResult.ko_prevented` (damage.py), which
  gates `is_ohko`/`ohko_with_max_roll` — multi-hit moves break Sash naturally
- `JointAdjuster` (engine.py) — phase-2 base class; `factor(state, slot_a, a0,
  slot_b, a1) -> (factor_a, factor_b, reason)`. Concrete: `DoublingAdjuster`,
  `CoordinationAdjuster`, `FakeOutAdjuster`, `SwitchCollisionAdjuster` (modules.py)
- `_PROTECT_MOVES` — frozenset of all Protect-family move names
- `_FAKE_OUT_USERS` — frozenset: Incineroar, Kangaskhan, Tinkaton, Weavile, Sneasler, Lopunny(-Mega), Toxicroak, Salazzle, etc. (Champions-legal only; derived from usage stats)
- `_TR_SETTER_SPECIES` — Farigiraf, Oranguru, Hatterene, Cofagrigus, Runerigus, Slowbro/Slowking variants, Reuniclus, Wyrdeer, etc. (≥40% TR usage in Champions stats)
- `_TAILWIND_SETTER_SPECIES` — Talonflame, Whimsicott, Aerodactyl, Noivern, Pelipper, Corviknight, Dragonite, etc. (≥20% TW usage in Champions stats)

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
# Run the bot
.venv\Scripts\python.exe main.py

# Run tests
.venv\Scripts\pytest

# Regenerate turn1_summary.md
.venv\Scripts\python.exe _gen_turn1_summary.py
```

**Never prefix shell commands with `cd`.** The tool's working directory is
already the project root and persists between calls. A compound command like
`cd C:\...\WolfeyBot && ...` (or `cd ...; ...`) trips Claude Code's
path-resolution safety check and forces a manual approval every single time.
Run commands bare with relative paths, exactly as in the block above
(`.venv\Scripts\pytest -q`, not `cd <repo> && .venv/Scripts/pytest -q`).

---

## Pending tasks

- **Task #3** — Audit switch-in order logic after a faint
- **Task #4** — Build lead selection framework. *Done (0.7.7):* `select_team`
  is one-mega-aware (0.6.9); `select_leads` is pair-based and initiative-aware
  (0.7.7) — all C(n,2) lead pairs scored as matchup-vs-predicted-leads ×
  slow-lead/Tailwind-exposure rows, with the slow row waived vs TR rosters.
  Remaining idea: validate the row magnitudes (×0.85) against the next
  100-game sample's led-vs-back splits.
- **Task #5** — Stat-aware mega selection. *Core idea now implemented in
  `select_team` (0.6.9):* a second stone-holder is demoted to base typing/ability
  **and** base stats (`base_BST / mega_BST`), which is the stat-aware mega-vs-base
  comparison this task wanted. Remaining: `select_mega` (which of the *brought*
  stones actually evolves) still ranks by defensive type-delta (≈0 for our team)
  → could reuse the same stat-aware base-vs-mega value. Lower priority now that
  we rarely bring two stones.
- **Ongoing** — Investigate weight issues surfaced by `turn1_summary.md`. The
  FakeOut over-protection (×0.5 discount looked too aggressive; gratuitous lone
  Protects) is now addressed *via coordination* — `CoordinationModule` (0.6.9)
  flips a gratuitous lone Protect to an attack beside an attacking partner,
  rather than re-tuning the FakeOut multipliers. Remaining: opponent **setup**
  (Tailwind/TR/defensive boosts) is the biggest loss correlate (59.8% of 0.6.8
  losses) — largely a team gap (no Taunt/Haze/speed-control), tracked separately.

---

## Current version

Single source of truth: **`version.py`** (`__version__`), imported by `main.py`
(battle-log folder + elo log) and `_gen_turn1_summary.py` (summary header).
Bump that one line per release and add a `CHANGELOG.md` entry; everything else
derives from it. See `CHANGELOG.md` for full history.

---

## Compact instructions

When compacting, always preserve:
- The 13-module pipeline order and what each module does
- Current team (species, items, moves)
- Any weight bug currently under investigation and which matchups reproduce it
- Pending task numbers and descriptions
- Key file paths and API patterns (BattleState construction, scored_actions)
- Current engine version
