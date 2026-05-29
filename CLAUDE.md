# WolfeyBot — Project Guide for Claude

## What this project is

WolfeyBot is a Gen 9 VGC doubles bot that plays on Pokémon Showdown in the
**Champions format (Reg MA)**. It connects via WebSocket, parses the battle
protocol, and chooses moves using a scoring engine made up of 13 stacked
multiplier modules.

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
| `DECISION_ARCHITECTURE.md` | Full narrative of how the engine works, with weight tables |
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
| Garchomp | Soft Sand | Rough Skin | Adamant | Dragon Claw / Stomping Tantrum / Poison Jab / Protect |

---

## Decision engine pipeline (13 modules, in order)

Each action starts at `weight = 1.0`. Modules multiply — never add.

| # | Module | What it does |
|---|---|---|
| 1 | DamageOutput | `×(1 + dmg_fraction × 2.0)` — sets `target_slot` to best opponent |
| 2 | ThreatElimination | ×5.0 guaranteed OHKO only; **withheld if we're guaranteed-KO'd before acting** (a faster/priority opp min-roll-OHKOs us & isn't removed first — offensive mirror of `_opp_neutralized_before_acting`) |
| 3 | IncomingOHKO | An opponent's max roll can OHKO us **and the threat isn't killed before it acts** (no faster ally guarantees its OHKO) → Protect ×2.5; suppress in 1v1/2v1 |
| 4 | TurnOrder | Fastest (pos 1/4): ×2.0; pos 2: ×1.5; pos 3: ×1.0; slowest (pos 4): ×0.75 — attacks only |
| 5 | SetterPresence | TR setter on field: attacks ×2.0; TW setter: attacks ×1.5 — unconditional urgency boost |
| 6 | FieldSetterDisruption | Only when guaranteed OHKO + we outspeed + no Prankster/Gale Wings: ×2.0 vs TR setters, ×1.5 vs TW setters; redirect if deny-score > current weight |
| 7 | OppProtectRecency | ×1.3 if target used Protect last turn |
| 8 | ConsecutiveProtect | ×0.2 if we used Protect last turn — no exceptions |
| 9 | Protect | An opp can OHKO us + ≥1 such threat still connects (not killed before it acts) + a partner has a guaranteed OHKO on one of the threats: ×3.0; suppress in 1v1/2v1 |
| 10 | FakeOut | Fake Out user on field (empty last move): Protect ×3.0, all attacks ×0.5 |
| 11 | FieldCondition | turns_left=1 or 3 → Protect ×3.0 (stall every other turn); no bonus at turns_left=2 |
| 12 | Switch | Board-value (1-ply): `TEMPO×(offense_term+escape)×safety`. offense_term=1+max(0, switchin_offense−current_offense)×2 (halved unless escaping; current Struggle counts as 0); escape +3.0 if current mon OHKO-threatened (connecting) & switch-in survives; safety ×0.3 if switch-in is OHKO'd; TEMPO 0.6; ×0 if partner switching same mon |
| 13 | DoublingUp | Both hitting same target: ×0.40–0.70 penalty; partner confirmed OHKO (w≥15): redirect or ×0.05 |

**Slot A is scored first. Slot B sees Slot A's committed decision** — DoublingUp
reads `my_slot_decisions[0]` when scoring slot 1.

### Key constants in engine.py / modules.py
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

---

## Pending tasks

- **Task #3** — Audit switch-in order logic after a faint
- **Task #4** — Build lead selection framework
- **Task #5** — Stat-aware mega selection. `select_mega` ranks candidates by
  *defensive type-delta* (mega typing vs base), which is always 0 for our team
  (Aerodactyl & Venusaur keep their typing on mega), so it never discriminates
  and falls through to the type-based offensive score — ignoring the mega STAT
  jump and stat-abilities (Mega Venusaur bulk + Thick Fat, Mega Aerodactyl
  speed/power). Replace the delta with a stat-aware mega-vs-base value
  comparison. Only matters when two stone-holders are brought together.
- **Ongoing** — Investigate weight issues surfaced by `turn1_summary.md`
  (FakeOut ×0.5 discount may be too aggressive; double-Protect scenarios
  where neither slot has a good attack warrant review)

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
