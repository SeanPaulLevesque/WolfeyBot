# WolfeyBot Changelog

---

## [0.3.2] — 2026-05-23

### Bug Fixes

#### Module dropout — Champions-format custom mega species (`damage.py`)
`_most_common_stats(species)` begins by calling `get_base_stats(species)`.  When a
Champions-format custom mega is active on the opponent's side — e.g. "Drampa-Mega",
"Chimecho-Mega" — that species name has no entry in the base-stats database (Drampa
has no canonical mega evolution), so `get_base_stats` returns `None` and
`_most_common_stats` propagates `None` upward.  `outgoing_damage` then returns `[]`
for that opponent.  When the ONLY live opponent is an unknown-species mega, all
attacks score weight 1.0 with no reasons, as confirmed in battles 2616671659
(Drampa-Mega) and 2616669221 (Altaria-Mega / Sinistcha).

**Fix:** Added a base-form fallback inside `_most_common_stats`.  If the exact
species name is not in the database, the function strips the last hyphenated suffix
(`"Drampa-Mega"` → `"Drampa"`) and retries.  If the base form has known stats, those
are used as an approximation (with zero SP, Hardy nature, since the Champions-format
mega spread is of course unknown).  The fallback is logged at DEBUG level.  `None` is
returned only when no base form can be found either.

This covers the full range of Champions-format custom megas without requiring a
maintained enumeration of each one.

#### ProtectModule consecutive-Protect penalty overrides critical-HP bonus (`decision.py`)
In 0.3.1 a two-tier HP bonus was added: critical HP (< 5%) gives ×3.0, normal low
HP (< 25%) gives ×1.5.  However, the consecutive-Protect penalty (×0.1) and the
HP bonuses were mutually exclusive — the penalty branch used `else` to skip bonuses
entirely.  A mon that had used Protect last turn and was at 0.6% HP received only
×0.1 on Protect, making it lose to any attack at ×1.3+.

Confirmed in battle 2616674247 T5: Aerodactyl-Mega at 0.59% HP, Protect ×0.08
(consecutive penalty crushed it), Dual Wingbeat ×1.30 chosen.

**Fix:** Changed the exclusive `if/else` to: when `used_protect_last_turn AND
NOT critical_hp`, apply ×0.1 and `continue` (skipping bonuses as before).  When
`used_protect_last_turn AND critical_hp`, skip the penalty and fall through to the
normal bonus block.  The mon is about to die regardless — giving it a chance to
survive through Protect a second time is correct.

Result at 0.59% HP + OHKO-threatened + used Protect last turn:
  - Before: ×0.1 (penalty only)
  - After:  ×2.5 (OHKO threat) × ×3.0 (critical HP) = ×7.5

#### SwitchModule dual-switch to same bench slot (`decision.py`)
When both active slots chose to switch in the same turn, `SwitchModule` had no
cross-slot awareness — each slot independently evaluated bench options and both
could commit to the same reserve Pokémon.  In doubles this is impossible (only one
slot can send in a given bench mon per turn); if submitted, Showdown would reject
one of the choices.

Confirmed in battle 2616660207 T9: both Sneasler (slot 0) and Aerodactyl-Mega
(slot 1) chose `Switch Kingambit` at w=1.8.

**Fix:** At the top of `SwitchModule.score()`, collect all switch targets that
earlier slots have already committed to via `state.my_slot_decisions`.  Any switch
action targeting a species in that set is vetoed (weight set to 0.0) so the second
slot is forced to choose either a different bench mon or a move.

---

## [0.3.1] — 2026-05-23

### Bug Fixes

#### Module dropout — fainted opponents in speed calculations (`decision.py`, `turn_order.py`)
`_opp_combatant()` and `build_combatants()` were building `Combatant` objects for
fainted opponents, which could cause `PrioritySpeedModule`'s speed comparison to
fail silently and leave all actions at weight 1.0.

**Fix:** Added `or mon.fainted` guard to both functions.

### Tuning / Optimisations

#### ProtectModule — steeper multiplier at critical HP (`decision.py`)
Added `CRITICAL_HP_THRESHOLD = 0.05` (5%) with `CRITICAL_HP_FACTOR = ×3.0`,
replacing the flat ×1.5 at sub-5% HP.

#### DoublingUpModule — redirect when partner has a near-certain KO (`decision.py`)
Added `PARTNER_KILLS_FACTOR = ×0.65` applied on top of the existing doubling-up
penalty when partner's committed action weight ≥ 10.0.

---

## [0.3.0] — 2026-05-23

### Features

#### Fake Out threat awareness (FakeOutModule)
Detects fresh Fake Out users (Incineroar, Scream Tail, Persian/Alola, Ambipom,
Mienshao, Lopunny/Mega, Hitmontop) and applies ×3.0 to Protect and ×0.5 to
non-switch attacks.

#### Cleaned-up console output
Two-tier logging: INFO console with `_CompactFormatter`, full DEBUG to `bot.log`.
Compact 4-line state block per turn; tabular per-slot decision lines.

### Bug Fixes

#### Switch-in last-move reset (`battle.py`)
`_on_switch` resets `my_last_moves[slot]` and `opp_last_moves[slot]` to `""` on
switch-in.

---

## [0.2.1] — 2026-05-23

### Bug Fixes

#### Dead-slot targeting
Added `or opp.fainted` to every `opp_actives` iteration guard in `decision.py`.

#### Server error freeze
`_on_error` now resets `state.last_rqid_handled = None`.

---

## [0.2.0] — 2026-05-23

### Bug Fixes

#### Last Respects power scaling
Added `ally_faint_count` parameter through `outgoing_damage` and `full_damage_calc`.

#### Stale damage estimates (missed KOs on damaged opponents)
Added `opp_current_hp` parameter to `outgoing_damage`; uses actual HP when not
a percentage proxy.

#### Phantom decisions for fainted active Pokémon
Added fainted-slot guard in `_build_choice`; appends `None` for fainted slots to
keep `DoublingUpModule` index bookkeeping correct.

---

## [0.1.0] — 2026-05-23 *(initial version)*

### Features

- Weighted multiplicative scoring engine
- DamageOutputModule, ThreatEliminationModule, PrioritySpeedModule, ProtectModule,
  SwitchModule, DoublingUpModule
- Multi-hit move scaling, Mega evolution, team preview, battle data recording,
  auto-timer, 3-minute requeue delay
