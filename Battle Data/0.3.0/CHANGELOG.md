# WolfeyBot Changelog

---

## [0.3.0] — 2026-05-23

### Features

#### Fake Out threat awareness (FakeOutModule)
The bot now detects when an opponent has a fresh Fake Out user on the field
and adjusts its scoring accordingly.

**Background:** Fake Out is a +3 priority move that flinches its target and
can only be used on the first turn a Pokémon is active. In VGC doubles the
correct response is almost always to Protect one of your two active mons
(the flinch target is unknown in advance) while the partner acts freely.
Prior to 0.3.0 the engine had no awareness of this — Protect received only
the generic ×1.5 "priority useful" boost, which was routinely beaten by any
moderate damage multiplier.

**Detection:** A Fake Out threat is active when any non-fainted opponent is
a member of `_FAKE_OUT_USERS` (Incineroar, Scream Tail, Persian, Persian-Alola,
Ambipom, Mienshao, Lopunny, Lopunny-Mega, Hitmontop) **and** the last
observed move for that opponent's slot is unknown (empty string — meaning
the mon either just switched in or the battle is on its first turn). The
threat clears as soon as any move is recorded for that slot.

**Scoring adjustments (both active slots):**
- Protect-family moves: ×3.0
- Non-switch attacks: ×0.5 (expected-value discount for the ~50% flinch
  probability in doubles)
- Switch actions: unaffected (switching out sidesteps Fake Out entirely)

The ×0.5 discount is calibrated so a guaranteed OHKO attack (typical weight
≈22) lands at ≈11, almost exactly matching Protect's combined weight from
FakeOutModule × ProtectModule × PrioritySpeedModule (≈11.25). Below OHKO
level Protect clearly wins; at OHKO level it is a genuine toss-up, which
reflects how top players actually evaluate the matchup.

**Covered species:** Incineroar (most common), Scream Tail, Persian /
Persian-Alola, Ambipom, Mienshao, Lopunny / Lopunny-Mega, Hitmontop.

#### Cleaned-up console output
The console was previously printing every raw WebSocket frame (DEBUG level)
alongside verbose per-field state dumps, making it difficult to follow a
battle in real time.

**Changes:**
- Console handler now filters to INFO and above; full DEBUG trace still
  writes to `bot.log`.
- New `_CompactFormatter`: INFO lines show `HH:MM:SS  message` with no
  logger name or level tag; WARN/ERROR prefix `[WARN]` / `[ERRO]` so
  problems stand out.
- `_log_state` redesigned from 10+ separate log calls to a clean 4-line
  block: header, MY actives, OPP actives, FIELD + BENCH.
- Per-slot decision log now shows `[A]  Move Name  x4.10  reason | reason`
  instead of a raw Python list repr.
- `SENDING` command demoted to DEBUG (already visible in the decision line).
- `"Timer started"` and `"Login command sent"` demoted to DEBUG.
- Login confirmation collapsed into a single `"Logged in as X — queuing Y"` line.

### Bug Fixes

#### Switch-in last-move reset (`battle.py`)
`_on_switch` now resets the incoming slot's entry in `my_last_moves` (our
side) and `opp_last_moves` (opponent side) to `""` whenever a Pokémon
switches in. This fixes two independent bugs:

- **Opponent side:** `FakeOutModule` can correctly distinguish a fresh
  switch-in (Fake Out available) from a mon that has already moved this
  field-entry (Fake Out consumed). Previously the slot retained the
  previous mon's last move indefinitely.

- **Our side:** `ProtectModule`'s consecutive-Protect penalty (×0.1) no
  longer incorrectly fired on a mon that switched in to replace one that
  had used Protect the previous turn.

---

## [0.2.1] — 2026-05-23

### Bug Fixes

#### Dead-slot targeting (engine attacks fainted opponents)
When an opponent Pokémon fainted mid-battle, it remained in `opp_actives`
with `fainted=True`. Every scoring module iterated `opp_actives` guarded
only by `if opp is None`, so fainted mons were treated as live targets. The
engine would compute damage against them, assign `target_slot` to their
slot, and submit that choice to Showdown.

Observed in 0.2.0 data:
- Battle 2616391896 T4S1: Kingambit chose Kowtow Cleave targeting fainted
  opponent Basculegion (slot 1, 0/0 HP).
- Battle 2616402673 T7S1: Sneasler chose Close Combat targeting fainted
  opponent Kingambit (slot 1, 0/0 HP) — this triggered the server error and
  subsequent timer freeze (see below).

**Root cause:** All `for opp in state.opp_actives` guards checked
`opp is None` but not `opp.fainted`.

**Fix:** Added `or opp.fainted` to every guard across `DamageOutputModule`,
`ThreatEliminationModule`, `ProtectModule`, `SwitchModule`, and
`DoublingUpModule` in `decision.py`. The `active_opps` list comprehension
in `DoublingUpModule` similarly gained `and not o.fainted`.

#### Server error freeze (bot goes silent after rejected choice)
When Showdown rejected a choice (e.g. move targeting a fainted slot) it
sends `|error|` and immediately re-sends `|request|` with the **same
`rqid`** to ask for a new choice. The bot's dedup guard
(`rqid == last_rqid_handled`) blocked `_maybe_decide()` from firing, so no
new choice was submitted. The bot sat idle until Showdown's auto-timer
picked a random move.

This was the direct cause of the observed timer event in battle 2616402673:
Sneasler's invalid targeting caused an error, the bot froze, and Showdown
auto-moved on the expiring timer. The game was won by luck.

**Root cause:** `_on_error` in `battle.py` only logged the rejection; it
did not reset `last_rqid_handled`, so the re-sent request was silently
dropped.

**Fix:** `_on_error` now resets `state.last_rqid_handled = None`, allowing
the re-sent `|request|` to pass the dedup guard and trigger a fresh
decision.

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
observed HP is an absolute value (`hp_is_percentage=False`), it replaces
the typical-spread HP in the stats dict before the formula runs.

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
