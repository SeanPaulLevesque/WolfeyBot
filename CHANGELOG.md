# WolfeyBot Changelog

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
