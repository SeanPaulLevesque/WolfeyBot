# WolfeyBot Changelog

---

## [0.2.0] — 2026-05-23

### Bug Fixes

#### Last Respects power scaling
Last Respects was always evaluated at its base 50 BP regardless of how many
allies had fainted. The move scales as `50 + (faint_count × 50)`, reaching
100 / 150 / 200 BP with 1 / 2 / 3 fainted allies.

**Root cause:** `full_damage_calc` read the static move data power and never
consulted battle state.

**Fix:** Added `ally_faint_count` parameter to `outgoing_damage` and
`full_damage_calc`. Both `DamageOutputModule` and `ThreatEliminationModule`
now compute `sum(p.fainted for p in state.my_team)` and pass it through.

#### Stale damage estimates (missed KOs on damaged opponents)
The bot was evaluating damage as a fraction of the opponent's *typical full
HP* (from the metagame spread database), not their *actual current HP*. This
caused the engine to miss guaranteed KOs on weakened opponents throughout
entire games.

Examples from 0.1.0 data:
- Araquanid at 32% HP: Dual Wingbeat showed 91% damage → actually 283% (OHKO)
- Charizard-Mega-Y at 2% HP: any move showed 38–59% → actually 1900–2600% (OHKO)
- Dragonite-Mega at 8% HP: Kowtow Cleave showed 49% → actually 612% (OHKO)

This was the most impactful bug — missed KOs were found in every single
0.1.0 battle, often across 4–10 consecutive turns.

**Root cause:** `outgoing_damage` used `_most_common_stats(opp_species)` as
the HP denominator unconditionally.

**Fix:** Added `opp_current_hp` parameter to `outgoing_damage`. When the
observed HP is an absolute value (not a percentage proxy,
`hp_is_percentage=False`), it replaces the typical-spread HP in the stats
dict before the formula runs. Both `DamageOutputModule` and
`ThreatEliminationModule` pass `opp.hp` when applicable.

#### Phantom decisions for fainted active Pokémon
In late-game doubles when a Pokémon faints with no bench replacement,
Showdown still includes that slot in the `active` array of the next turn
request. The engine was generating (and recording) full scored decision
trees for the fainted slot, sending moves for a dead Pokémon.

**Root cause:** `_build_choice` iterated `range(len(state.moves_per_slot))`
without checking whether the corresponding active mon was alive.

**Fix:** Added a fainted-mon guard at the top of the normal-turn loop in
`_build_choice`. Fainted slots are skipped with a warning log; `None` is
appended to `my_slot_decisions` so the slot index bookkeeping stays correct
for `DoublingUpModule`.

---

## [0.1.0] — 2026-05-23 *(initial version)*

### Features

- **Weighted multiplicative scoring engine** — all actions start at weight
  1.0; modules multiply weights, never add.
- **DamageOutputModule** — scores moves by expected damage fraction; sets
  `action.target_slot` to the best opponent for consistent move + target
  pairing.
- **ThreatEliminationModule** — large KO bonuses (×5.0 guaranteed OHKO,
  ×2.5 max-roll OHKO, ×1.5 2HKO); overrides `target_slot` for KO targets.
- **PrioritySpeedModule** — ×1.5 for priority when opponent may outspeed;
  ×3.0 bonus for Fake Out; ×0.8 when priority is unnecessary.
- **ProtectModule** — ×2.5 when OHKO-threatened, ×1.5 at low HP, ×0.1
  consecutive-Protect penalty to stop spamming.
- **SwitchModule** — type-matchup evaluation; OHKO-escape tier lifts weights
  to ×4.0 for good switches (vs ×1.8 normal).
- **DoublingUpModule** — penalises doubling up into the same target (×0.55
  to ×0.85 depending on Protect history and other-opponent threat).
- **Multi-hit move scaling** — `expected_hits()` lookup multiplies per-hit
  power so Dual Wingbeat (2×40=80) is not undervalued vs Ice Fang (65).
- **Mega evolution** — triggered automatically whenever `canMegaEvo` is set.
- **Team preview** — sends `/choose team 1234` (fixed lead order).
- **Targeting** — `action.target_slot` wired through to `/choose` string;
  move and target are always the same opponent.
- **Battle data recording** — per-battle JSON saved to
  `battle data/{version}/{battle_id}.json` with full ranked action lists,
  state snapshots, and outcome.
- **Auto-timer** — `/timer on` sent on battle join.
- **3-minute requeue delay** between battles.
