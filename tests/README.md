# WolfeyBot Unit Tests

## Running the tests

From the project root:

```bash
.venv\Scripts\python -m pytest
```

All 249 tests should pass in under a second. The `pytest.ini` at the project root
points pytest at the `tests/` directory automatically, so no arguments are needed.

To run a single file:

```bash
.venv\Scripts\python -m pytest tests/test_damage_core.py
```

To run a single test class or case:

```bash
.venv\Scripts\python -m pytest tests/test_decision_modules.py::TestProtectModule
.venv\Scripts\python -m pytest tests/test_decision_modules.py::TestProtectModule::test_1v1_endgame_no_bonuses_even_when_low_hp
```

---

## File overview

| File | Tests | What it covers |
|---|---|---|
| `test_battle_utils.py` | 22 | `_parse_hp`, `_parse_status`, `_side/slot/normalize_ident`, `Pokemon.hp_fraction`, `_update_or_add` |
| `test_battle_parser.py` | 36 | `BattleParser.feed()` — switch, damage, heal, status, boosts, Trick Room, Tailwind, turn counter, faint, win/loss callback, items, error recovery |
| `test_damage_core.py` | 62 | `calc_damage` formula arithmetic, `type_effectiveness`, `stab_multiplier`, `stat_with_boost`, `atk/def_modifier`, `weather_modifier`, `DamageResult` KO properties, `_low_kick_power`/`_heat_crash_power` |
| `test_turn_order.py` | 19 | `_apply_modifiers` (tailwind, paralysis, scarf, Unburden, stat stages), `priority_bracket`, `will_outspeed`, `estimate_turn_order` |
| `test_recorder.py` | 22 | `_hp_frac`, `_compact_action`, `_select_actions`, full save round-trip, compact JSON format, v2 abbreviated keys |
| `test_decision_modules.py` | 88 | `Action`, `_build_actions`, `DecisionEngine`, and every scoring module (see below) |

---

## Decision module coverage

### FakeOutModule
- No Fake Out user present → no-op
- Fresh Incineroar (no prior move) → Protect ×3.0, attacks ×0.5, switches unchanged
- Incineroar after a move → threat consumed, no-op
- Non-Fake-Out species → no-op

### OppProtectRecencyModule
- Target used Protect last turn → attack boosted ×1.3
- Target used a non-Protect move → no boost
- Action has no target slot → no boost
- Detects all Protect-family moves (Wide Guard, King's Shield, Detect)

### FieldConditionModule
- Last turn of opponent Tailwind → Protect ×3.0
- Last turn of Trick Room → Protect ×3.0
- Both conditions expiring → stacks to ×9.0
- Not expiring → no-op
- Non-Protect moves never affected

### ProtectModule
- **1v1 endgame**: all HP and threat bonuses suppressed even at low HP
- **1v1 endgame**: consecutive-Protect penalty still applies even at critical HP
- Consecutive Protect at normal HP → ×0.1 penalty
- Consecutive Protect at critical HP (<5%) outside 1v1 → penalty waived, CRITICAL_HP_FACTOR applied
- First Protect this field stint → no penalty
- Below 25% HP → LOW_HP_FACTOR (×1.5)
- Below 5% HP → CRITICAL_HP_FACTOR (×3.0)
- Opponent has max-roll OHKO → THREATENED_FACTOR (×2.5)

### DoublingUpModule
- Slot 0 with no prior partner decision → no-op
- Slot 1 targeting same opponent as partner → ×0.55 penalty (both threatening, no Protect)
- Target used Protect last turn → lighter ×0.70 penalty
- Partner has confirmed OHKO (weight ≥ 15) and alt target exists → redirect to alt target, no penalty
- Spread moves (Earthquake) → skipped entirely, no penalty

### SwitchModule
- Switch target already committed by partner → weight zeroed

### PrioritySpeedModule
- Fake Out receives ×3.0 boost when legal

### DamageOutputModule
- 80% damage fraction → weight = 1 + 0.80 × 2 = 2.6
- 0% damage (immune) → weight unchanged at 1.0

### ThreatEliminationModule
- Guaranteed OHKO (min roll ≥ HP) → ×5.0
- OHKO on max roll only → ×2.5

---

## Design notes

**Pure unit tests** (no mocking): All math functions in `damage.py`, `turn_order.py`,
and `recorder.py` are tested with plain inputs and outputs. These run in ~0.1 s.

**Async tests**: `BattleParser.feed()` is async. Tests use `asyncio.run()` directly
— no `pytest-asyncio` plugin required.

**Mocked module tests**: Decision module tests patch `decision.find_member` and
`decision.incoming_damage` so they run without `team.txt` loaded and without hitting
the data layer. This makes them fast and deterministic regardless of the team file.

**Spread-move caveat**: `DoublingUpModule` imports `is_spread_move` from `data`
inside the loop body. The spread-move test relies on the real data module confirming
that Earthquake is a spread move — no mock needed or used there.

---

## Key changelog behaviors with dedicated tests

These are the specific bug fixes and behavioral changes from the changelog that have
pinned tests to prevent regressions:

| Version | Change | Test |
|---|---|---|
| 0.3.3 | Trick Room detection uses `"trick room"` (with space) | `TestTrickRoom::test_fieldstart_trick_room_sets_flag` |
| 0.3.3 | `_low_kick_power` / `_heat_crash_power` weight-based moves | `TestLowKickPower`, `TestHeatCrashPower` |
| 0.3.4 | `ProtectModule` 1v1 endgame suppression | `TestProtectModule::test_1v1_endgame_*` |
| 0.3.4 | `DoublingUpModule` confirmed-OHKO redirect | `TestDoublingUpModule::test_redirect_when_partner_has_confirmed_ohko` |
| 0.3.5 | Recorder v2 compact format (abbreviated keys, HP as float) | `TestBattleRecorder::test_decision_uses_abbreviated_action_keys`, `test_hp_stored_as_fraction`, `test_no_whitespace_in_output` |
| 0.3.5 | `_select_actions` always includes chosen action | `TestSelectActions::test_chosen_always_included`, `test_chosen_included_even_if_weight_1_0` |
