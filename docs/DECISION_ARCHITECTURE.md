# WolfeyBot — How It Thinks

WolfeyBot plays Gen 9 VGC doubles (Champions / Reg M-B). This page explains how it
makes decisions, from the team-preview screen to choosing a move each turn. It is
the plain-language companion to the code in `team_preview.py` (preview) and
`decision/` (in-battle).

Three decisions are made:

1. **Which 4 to bring** (Part 1)
2. **Which 2 lead** (Part 2)
3. **What each active Pokémon does each turn** (Part 3)

---

## Part 1 — Team Preview: which 4 to bring

When the opponent's six Pokémon appear, the bot scores each of *our* six against
the whole enemy team and brings the top four. Each mon's score is:

```
combined = offense × 2  +  defense × 1
```

**Offense** — for each of the six opponents, the best type-multiplier any of our
moves can reach against it, summed. (Stomping Tantrum vs Incineroar = ×2.0; Dragon
Claw vs the same = ×1.0; the best available move counts.)

**Defense** — for each opponent, take the *worst* (highest) multiplier its STAB
types hit us for, and invert it. More resilient = higher score:

| Their best hit on us | Score |
|---|---|
| Immune (×0) | +4.0 |
| Resist (×0.5) | +2.0 |
| Neutral (×1.0) | +1.0 |
| Weak (×2.0) | +0.5 |
| Quad-weak (×4.0) | +0.25 |

Abilities that change incoming damage are folded in first (Levitate → Ground ×0,
Thick Fat → Fire/Ice ×0.5, etc.).

**One mega per battle.** Only one Mega Stone can activate, so when two stone
holders would both be brought, the second is re-valued at its *base* form — base
typing, base ability, and base stats (scaled by `base_BST / mega_BST`) — so the bot
doesn't over-rate a second, dead stone.

### Example

Opponent: Farigiraf / Incineroar / Sneasler / Kingambit / Talonflame / Pelipper.
These are the engine's actual scores for the current team (`offense × 2 + defense`):

| Our Pokémon | offense | defense | **combined** | Brought? |
|---|---|---|---|---|
| Sneasler | 13.5 | 5.2 | **32.2** | ✓ |
| Aerodactyl | 11.5 | 6.0 | **29.0** | ✓ |
| Kingambit | 11.0 | 6.2 | **28.2** | ✓ |
| Basculegion | 11.0 | 5.5 | **27.5** | ✓ |
| Garchomp | 9.0 | 6.0 | **24.0** | ✗ |
| Venusaur | 9.0 | 4.5 | **22.5** | ✗ |

Against *this* team Garchomp's coverage is mediocre (off 9.0), so it's left
home — a reminder the bring is matchup-specific, not a fixed "best six".

### How a type multiplier is found

A move has one type; a Pokémon has one or two. Multiply the move's effectiveness
against each defender type:

- **Stomping Tantrum (Ground) vs Incineroar (Fire/Dark):** ×2 (Fire) × ×1 (Dark) = **×2**
- **Stomping Tantrum (Ground) vs Aerodactyl (Rock/Flying):** ×1 (Rock) × ×0 (Flying) = **×0**

---

## Part 2 — Team Preview: which 2 lead

The bot records which Pokémon opponents actually lead with, every battle
(`Battle Data/lead_stats.json`, rebuilt by `tools/build_lead_stats.py`). Across
**2,947 recorded battles** the most common leads are:

| Opponent lead | Times led | % of battles |
|---|---|---|
| Garchomp | 948 | 32.2 % |
| Sneasler | 284 | 9.6 % |
| Farigiraf | 233 | 7.9 % |
| Whimsicott | 199 | 6.8 % |
| Aerodactyl | 166 | 5.6 % |
| Incineroar | 159 | 5.4 % |
| Sableye | 127 | 4.3 % |
| Rotom-Wash | 108 | 3.7 % |
| Talonflame | 108 | 3.7 % |
| Pelipper | 102 | 3.5 % |
| Charizard | 95 | 3.2 % |
| Basculegion | 89 | 3.0 % |

*(A species can be led in up to two slots per battle, so the column is "fraction
of battles in which the opponent led with this mon," not a share of 100 %.)*

From the opponent's previewed six, the bot predicts the **two highest-frequency
leads**, then re-runs the Part 1 offense/defense scoring against *only those two*.
The two of our four brought mons that score best there go out first; the rest keep
their order. (With no lead data, the two highest overall-matchup mons lead.)

**Example.** Opponent previews Garchomp, Whimsicott, Incineroar, Sableye,
Rotom-Wash, Tyranitar. Highest lead frequencies among them: **Garchomp (32.2 %)**
and **Whimsicott (6.8 %)**. The bot brings Sneasler / Venusaur / Kingambit /
Garchomp, then scores those four against the predicted Garchomp + Whimsicott pair:
**Venusaur** (Giga Drain ×2 on Garchomp — Grass vs Ground — and Sludge Bomb ×2 on
Whimsicott) and **Garchomp** score highest, so they lead.

---

## Part 3 — In-Battle Decisions

Each turn the engine works in **two phases**:

- **Phase 1** scores every action of *each slot on its own* (blind to the partner).
- **Phase 2** (`DecisionEngine.coordinate`) picks the best *joint pair* of actions
  for the two slots.

**Actions carry their target.** A single-target move becomes one candidate per
live opponent — "Rock Tomb → foe A" and "Rock Tomb → foe B" are separate choices,
so *which* foe to hit is decided by the scoring, not patched afterwards. Spread /
status / self moves, Protect, and switches are single candidates. Every candidate
starts at **weight 1.0**; modules **multiply** it (never add). `d` below = a move's
average damage as a fraction of the target's current HP.

### The per-action weight table

Each candidate starts at **1.0** and every rule **multiplies** it. Rows above the
divider are **phase 1** (each slot scored on its own); rows below are **phase 2** —
joint rules applied to the chosen *pair*. `coordinate` maximises
`(w_A × factor_A) × (w_B × factor_B)` over all candidate pairs, so with no joint
effect the result is just each slot's independent best. `d` = a move's average
damage as a fraction of the target's HP.

**Row id** (leftmost column) = `module.row`: the module's position in the phase-1
pipeline (`make_engine`, in `decision/modules.py`), then the row within that
module. So **3.2** is ProtectValue's second row, and a module that owns several
rows shares one module number (e.g. ProtectValue is **3.1–3.4**). Because rows are
grouped by theme, not strict execution order, the module numbers are **not**
strictly ascending. Phase-1 modules:
**1** DamageOutput · **2** ThreatElimination · **3** ProtectValue · **4** TurnOrder ·
**5** SetterUrgency · **6** SetterDenial · **7** OppProtectRecency ·
**8** ConsecutiveProtect · **9** FakeOut · **10** FieldCondition · **11** Redirection ·
**12** Switch · **13** EndgameStall · **14** Doomed · **15** PriorityKill.
Phase-2 joint adjusters:
**J1** Doubling · **J2** Coordination · **J3** FakeOut (free) · **J4** SwitchCollision ·
**J5** PartnerClears.

Several rows sit beside their thematic siblings rather than in pipeline order:
**13** EndgameStall (1v1/2v1 cancel) and **14** Doomed (the "KO'd before we act"
attack penalty) were split out of ProtectValue and ThreatElimination, so rows
**13.x** / **14.1** sit near the **3.x** / **2.x** rows; **15** PriorityKill (the
priority-move revenge-KO boost) is the natural counterpart to **14**, so **15.1**
sits beside **14.1**.  **J5** PartnerClears is
the old "Threat Clear" boost — moved to phase 2 because whether a threat is
cleared depends on the *partner's* chosen action.

<style>.decision-table td, .decision-table th { text-align: center; }</style>
<table class="decision-table">
<thead>
<tr>
  <th rowspan="2" style="text-align:center">#</th>
  <th rowspan="2" style="text-align:center"></th>
  <th colspan="3" style="text-align:center">Target Slot 1</th>
  <th colspan="3" style="text-align:center">Target Slot 2</th>
  <th rowspan="2" style="text-align:center">Protect</th>
  <th rowspan="2" style="text-align:center">Switch&nbsp;1</th>
  <th rowspan="2" style="text-align:center">Switch&nbsp;2</th>
  <th rowspan="2" style="text-align:center">Note</th>
</tr>
<tr>
  <th style="text-align:center">Attack 1</th><th style="text-align:center">Attack 2</th><th style="text-align:center">Attack 3</th>
  <th style="text-align:center">Attack 1</th><th style="text-align:center">Attack 2</th><th style="text-align:center">Attack 3</th>
</tr>
</thead>
<tbody>
<tr><td>—</td><td>Starting Weight</td><td>1</td><td>1</td><td>1</td><td>1</td><td>1</td><td>1</td><td>1</td><td>1</td><td>1</td><td>All options equally likely to start</td></tr>
<tr><td>1.1</td><td>Predicted Damage Dealt</td><td colspan="6">×(1&nbsp;+&nbsp;d×2.0)</td><td>—</td><td>—</td><td>—</td><td></td></tr>
<tr><td>2.1</td><td>Score A Guaranteed Kill</td><td colspan="6">×5</td><td>—</td><td>—</td><td>—</td><td>lowest damage roll ≥ the target's HP (unconditional — the doom cancel is its own module, #14)</td></tr>
<tr><td>14.1</td><td>Die Before Acting</td><td colspan="6">×0.2</td><td>—</td><td>—</td><td>—</td><td>per-candidate: a certain killer would land before <em>this move</em> (so a priority move that out-speeds the threat is spared — revenge-KO); Protect/switch untouched</td></tr>
<tr><td>15.1</td><td>Priority Kill</td><td colspan="6">×3.0</td><td>—</td><td>—</td><td>—</td><td>a <em>priority</em> move (bracket&nbsp;&gt;&nbsp;0) that guarantees the OHKO — it removes the foe before it can act, so prefer it over a slower KO</td></tr>
<tr><td>3.1</td><td>Incoming Kill</td><td colspan="6">—</td><td>×2.5</td><td>—</td><td>—</td><td>an opponent's max roll kills this mon at its current HP</td></tr>
<tr><td>13.1</td><td>1v1 Endgame</td><td colspan="6">—</td><td>×0.4</td><td>—</td><td>—</td><td>Protect stalling in 1v1 is net neutral</td></tr>
<tr><td>13.2</td><td>2v1 Endgame</td><td colspan="6">—</td><td>×0.4</td><td>—</td><td>—</td><td>Protect stalling in 2v1 is net negative</td></tr>
<tr><td>4.1</td><td>Turn Order</td><td colspan="6">pos 1 ×2.0 · pos 2 ×1.5 · pos 3 ×1.0 · pos 4 ×0.75</td><td>—</td><td>—</td><td>—</td><td>position = our rank in the 4-mon turn order</td></tr>
<tr><td>5.1</td><td>Trick Room urgency</td><td colspan="6">×2.0</td><td>—</td><td>—</td><td>—</td><td>a TR setter is up, TR not active (or last turn)</td></tr>
<tr><td>6.1</td><td>Trick Room denial (setter Slot 1)</td><td colspan="3">×2.0</td><td colspan="3">—</td><td>—</td><td>—</td><td>—</td><td>OHKOs the Slot-1 TR setter</td></tr>
<tr><td>6.2</td><td>Trick Room denial (setter Slot 2)</td><td colspan="3">—</td><td colspan="3">×2.0</td><td>—</td><td>—</td><td>—</td><td>OHKOs the Slot-2 TR setter</td></tr>
<tr><td>5.2</td><td>Tailwind urgency</td><td colspan="6">×1.5</td><td>—</td><td>—</td><td>—</td><td>a TW setter is up, TW not active (or last turn)</td></tr>
<tr><td>6.3</td><td>Tailwind denial (setter Slot 1)</td><td colspan="3">×1.5</td><td colspan="3">—</td><td>—</td><td>—</td><td>—</td><td>OHKOs the Slot-1 TW setter</td></tr>
<tr><td>6.4</td><td>Tailwind denial (setter Slot 2)</td><td colspan="3">—</td><td colspan="3">×1.5</td><td>—</td><td>—</td><td>—</td><td>OHKOs the Slot-2 TW setter</td></tr>
<tr><td>7.1</td><td>target Protected last turn (Slot 1)</td><td colspan="3">×1.3</td><td colspan="3">—</td><td>—</td><td>—</td><td>—</td><td>the Slot-1 target used Protect last turn, so it can't Protect again</td></tr>
<tr><td>7.2</td><td>target Protected last turn (Slot 2)</td><td colspan="3">—</td><td colspan="3">×1.3</td><td>—</td><td>—</td><td>—</td><td>the Slot-2 target used Protect last turn, so it can't Protect again</td></tr>
<tr><td>8.1</td><td>I used Protect last turn</td><td colspan="6">—</td><td>×0.2</td><td>—</td><td>—</td><td>consecutive Protect</td></tr>
<tr><td>9.1</td><td>Fake Out threatened</td><td colspan="6">×0.5</td><td>×3.0</td><td>—</td><td>—</td><td>a fresh Fake Out user is on the field</td></tr>
<tr><td>10.1</td><td>Field Condition stall</td><td colspan="6">—</td><td>×3.0</td><td>—</td><td>—</td><td>opp Trick Room / Tailwind has 1 or 3 turns left</td></tr>
<tr><td>11.1</td><td>redirection hedge</td><td colspan="6">×d&nbsp;(to redirector)</td><td>—</td><td>—</td><td>—</td><td>Rage Powder / Follow Me user active; hedge our attack on the possibility of redirection</td></tr>
<tr><td>12.1</td><td>switch value</td><td colspan="6">—</td><td>—</td><td colspan="2">TEMPO × (1+g) × escape × safety</td><td>1-ply board value; TEMPO 0.6; g = offense gain; ×4.0 if escaping a connecting OHKO into a surviving switch-in; ×0.3 if the switch-in is itself OHKO'd</td></tr>
<tr><td colspan="12"><strong>Phase 2 — joint adjusters (applied to the chosen pair)</strong></td></tr>
<tr><td>J1</td><td>doubling up</td><td colspan="6">×0.40–0.70</td><td>—</td><td>—</td><td>—</td><td>both slots attack the same target; ×0.05 on the non-killer when one slot already confirms the OHKO, so the pair that spreads onto the survivor wins</td></tr>
<tr><td>J2</td><td>attack alongside partner</td><td colspan="6">—</td><td>×0.5</td><td>—</td><td>—</td><td>a gratuitous lone Protect (no real OHKO/stall reason, e.g. only a Fake Out nudge) beside an attacking partner — favour the double-attack</td></tr>
<tr><td>J3</td><td>Fake Out absorbed (free partner)</td><td colspan="6">×2.0</td><td>×0.33</td><td>—</td><td>—</td><td>when either slot attacks, the partner's Fake-Out multiplier above is divided back out (attack un-halved, Protect un-boosted) — a pair pays the Fake-Out adjustment once, never twice</td></tr>
<tr><td>J4</td><td>switch collision</td><td colspan="6">—</td><td>—</td><td colspan="2">×0</td><td>both slots switch to the same bench mon → that pair is vetoed</td></tr>
<tr><td>J5</td><td>Partner Clears</td><td colspan="6">—</td><td>×3.0</td><td>—</td><td>—</td><td>one slot Protects against a connecting OHKO and the partner's chosen attack guaranteed-OHKOs that threatener → Protect so we survive while the partner removes it (was phase-1 "Threat Clear"; it's a cross-slot question, so it's phase 2)</td></tr>
</tbody>
</table>

The phase-2 rules subsume the old hand-coded repairs: "redirect off a partner's
kill" and "flip a wasteful Protect to an attack" are now emergent from picking the
best pair, so there is no separate re-pass.

### Worked example (turn 1)

Our **Garchomp + Kingambit** face **Incineroar + Basculegion** (Incineroar is a
Fake-Out user).

**Phase 1 — Garchomp on its own.** Incineroar's Fake Out boosts Protect ×3 and
halves every attack, so in isolation Garchomp's best candidate is to shield:

| Garchomp candidate | weight |
|---|---|
| **Protect** | **3.00** (Fake Out ×3) |
| Stomping Tantrum → Incineroar | 2.63 (×2 Ground, halved by Fake Out) |
| Stomping Tantrum → Basculegion | 2.05 |
| Dragon Claw → Basculegion | 1.94 |

**Phase 2 — the pair.** Kingambit's best action is an attack (Kowtow Cleave →
Basculegion, a guaranteed OHKO). Beside an attacking partner two joint rules pull
Garchomp's Protect down: the **Fake Out absorbed** adjuster strips its ×3 boost
(the attacker is the one assumed to eat the flinch — a pair claims the Fake-Out
adjustment once, never twice), and the **Coordination** adjuster halves it as a
gratuitous lone Protect (no incoming OHKO, no stall): 3.00 → 0.50. In the
double-attack pair the same Fake-Out rule instead *frees* Kingambit's attack from
its ×0.5 discount (6.33 → 12.67). Stomping Tantrum → Incineroar (2.63) is now
Garchomp's best, and the chosen pair is **both attacking**: Garchomp → Incineroar,
Kingambit → Basculegion.

That's the whole design in one turn: per-slot scoring leaned toward a shield, and
joint coordination corrected it — *don't gratuitously Protect while your partner
swings.*

### What the final weight means

| Final weight | In practice |
|---|---|
| 10 + | near-certain KO on a key target — almost never override |
| 4 – 10 | strong: guaranteed-KO range, or a Protect that shields a partner KO |
| 2 – 4 | clearly preferred — good damage, solid protective reason, or a clean escape-switch |
| 1 – 2 | baseline — fine, no standout reason |
| < 1 | discouraged — a better option exists |
| 0 | hard veto — never chosen |
