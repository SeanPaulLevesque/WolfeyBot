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

- **Phase 1** scores each possible action of each slot on its own (blind to the partner).
- **Phase 2** coordinates to pick the best joint pair of actions for the two slots.

**Actions carry their target.** A single-target move becomes one candidate per
live opponent — "Rock Tomb → foe A" and "Rock Tomb → foe B" are separate choices. Spread /
status / self moves, Protect, and switches are single candidates. Every candidate
starts at **weight 1.0**; modules **multiply** those weights. 

### The per-action weight table



<table>
<thead>
<tr>
  <th rowspan="2" align="center"><small>#</small></th>
  <th rowspan="2" align="center"></th>
  <th colspan="3" align="center"><small>Target Slot 1</small></th>
  <th colspan="3" align="center"><small>Target Slot 2</small></th>
  <th rowspan="2" align="center"><small>Protect</small></th>
  <th rowspan="2" align="center"><small>Switch&nbsp;1</small></th>
  <th rowspan="2" align="center"><small>Switch&nbsp;2</small></th>
  <th rowspan="2" align="center"><small>Note</small></th>
</tr>
<tr>
  <th align="center"><small>Attack 1</small></th><th align="center"><small>Attack 2</small></th><th align="center"><small>Attack 3</small></th>
  <th align="center"><small>Attack 1</small></th><th align="center"><small>Attack 2</small></th><th align="center"><small>Attack 3</small></th>
</tr>
</thead>
<tbody>
<tr><td><small>—</small></td><td><small>Starting Weight</small></td><td><small>1</small></td><td><small>1</small></td><td><small>1</small></td><td><small>1</small></td><td><small>1</small></td><td><small>1</small></td><td><small>1</small></td><td><small>1</small></td><td><small>1</small></td><td><small>All options equally likely to start</small></td></tr>
<tr><td><small>1</small></td><td><small>Predicted Damage Dealt</small></td><td><small>×(1&nbsp;+&nbsp;d×2.0)</small></td><td><small>×(1&nbsp;+&nbsp;d×2.0)</small></td><td><small>×(1&nbsp;+&nbsp;d×2.0)</small></td><td><small>×(1&nbsp;+&nbsp;d×2.0)</small></td><td><small>×(1&nbsp;+&nbsp;d×2.0)</small></td><td><small>×(1&nbsp;+&nbsp;d×2.0)</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>d = median damage roll as a fraction of the target's current HP, **capped at 1.0** — overkill earns nothing (value saturates at lethal, so the joint pass routes by chip, not by which foe is overkilled hardest)</small></td></tr>
<tr><td><small>2</small></td><td><small>Score A Guaranteed Kill</small></td><td><small>×5</small></td><td><small>×5</small></td><td><small>×5</small></td><td><small>×5</small></td><td><small>×5</small></td><td><small>×5</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>Lowest damage roll ≥ the target's HP</small></td></tr>
<tr><td><small>3</small></td><td><small>Die Before Acting</small></td><td><small>×0.2</small></td><td><small>×0.2</small></td><td><small>×0.2</small></td><td><small>×0.2</small></td><td><small>×0.2</small></td><td><small>×0.2</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>A faster threat will kill before we act (priority aware)</small></td></tr>
<tr><td><small>4</small></td><td><small>Priority Kill</small></td><td><small>×3.0</small></td><td><small>×3.0</small></td><td><small>×3.0</small></td><td><small>×3.0</small></td><td><small>×3.0</small></td><td><small>×3.0</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>If one of our priority moves can score a kill</small></td></tr>
<tr><td><small>5</small></td><td><small>Priority Block</small></td><td><small>×0</small></td><td><small>×0</small></td><td><small>×0</small></td><td><small>×0</small></td><td><small>×0</small></td><td><small>×0</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>Cancel priority attacks while an opponent has Armor&nbsp;Tail / Queenly&nbsp;Majesty on the field</small></td></tr>
<tr><td><small>6</small></td><td><small>Incoming Kill</small></td><td colspan="6"><small>—</small></td><td><small>×2.5</small></td><td><small>—</small></td><td><small>—</small></td><td><small>An opponent's max roll kills this mon at its current HP</small></td></tr>
<tr><td><small>7.a</small></td><td><small>1v1 Endgame</small></td><td colspan="6"><small>—</small></td><td><small>×0.4</small></td><td><small>—</small></td><td><small>—</small></td><td><small>Protect stalling in 1v1 is net neutral</small></td></tr>
<tr><td><small>7.b</small></td><td><small>2v1 Endgame</small></td><td colspan="6"><small>—</small></td><td><small>×0.4</small></td><td><small>—</small></td><td><small>—</small></td><td><small>Protect stalling in 2v1 is net negative</small></td></tr>
<tr><td><small>8</small></td><td><small>Turn Order</small></td><td colspan="6"><small>pos 1 ×2.0 · pos 2 ×1.5 · pos 3 ×1.0 · pos 4 ×0.75</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>pos = Our rank in the 4-mon turn order</small></td></tr>
<tr><td><small>9</small></td><td><small>Setup Urgency</small></td><td colspan="6"><small>×2.0</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>A setter is on the field, but their effect isn't active*</small></td></tr>
<tr><td><small>10</small></td><td><small>Setup Denial</small></td><td><small>×2.0</small></td><td><small>×2.0</small></td><td><small>×2.0</small></td><td><small>×2.0</small></td><td><small>×2.0</small></td><td><small>×2.0</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>OHKOs a setter*</small></td></tr>
<tr><td><small>11.a</small></td><td><small>target Protected last turn (Slot 1)</small></td><td colspan="3"><small>×1.3</small></td><td colspan="3"><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>the Slot-1 target used Protect last turn, so it can't Protect again</small></td></tr>
<tr><td><small>11.b</small></td><td><small>target Protected last turn (Slot 2)</small></td><td colspan="3"><small>—</small></td><td colspan="3"><small>×1.3</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>the Slot-2 target used Protect last turn, so it can't Protect again</small></td></tr>
<tr><td><small>12</small></td><td><small>I used Protect last turn</small></td><td colspan="6"><small>—</small></td><td><small>×0.2</small></td><td><small>—</small></td><td><small>—</small></td><td><small>consecutive Protect</small></td></tr>
<tr><td><small>13</small></td><td><small>Fake Out threatened</small></td><td colspan="6"><small>×0.5</small></td><td><small>×3.0</small></td><td><small>—</small></td><td><small>—</small></td><td><small>a fresh Fake Out user is on the field</small></td></tr>
<tr><td><small>14</small></td><td><small>Field Condition stall</small></td><td colspan="6"><small>—</small></td><td><small>×3.0</small></td><td><small>—</small></td><td><small>—</small></td><td><small>opp Trick Room / Tailwind has 1 or 3 turns left</small></td></tr>
<tr><td><small>15</small></td><td><small>redirection hedge</small></td><td><small>×d&nbsp;(to redirector)</small></td><td><small>×d&nbsp;(to redirector)</small></td><td><small>×d&nbsp;(to redirector)</small></td><td><small>×d&nbsp;(to redirector)</small></td><td><small>×d&nbsp;(to redirector)</small></td><td><small>×d&nbsp;(to redirector)</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>Rage Powder / Follow Me user active; hedge our attack on the possibility of redirection</small></td></tr>
<tr><td><small>16</small></td><td><small>Switch tempo</small></td><td colspan="6"><small>—</small></td><td><small>—</small></td><td><small>×0.8</small></td><td><small>×0.8</small></td><td><small>flat cost of switching — forfeit the turn + concede a free hit</small></td></tr>
<tr><td><small>17</small></td><td><small>Switch offense</small></td><td colspan="6"><small>—</small></td><td><small>—</small></td><td><small>×(1+g)</small></td><td><small>×(1+g)</small></td><td><small>g = the switch-in's best-damage gain over the mon staying in (floored at 0)</small></td></tr>
<tr><td><small>18</small></td><td><small>Switch safety</small></td><td colspan="6"><small>—</small></td><td><small>—</small></td><td><small>×4.0 / ×0.3</small></td><td><small>×4.0 / ×0.3</small></td><td><small>×4.0 escape a connecting OHKO into a surviving switch-in; ×0.3 if the switch-in is itself OHKO'd</small></td></tr>
<tr><td colspan="12"><small><strong>Phase 2 — joint adjusters (applied to the chosen pair)</strong></small></td></tr>
<tr><td><small>J1</small></td><td><small>doubling up</small></td><td colspan="6"><small>×0.4</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>flat penalty when both slots attack the same target — the spread-your-damage tax</small></td></tr>
<tr><td><small>J2</small></td><td><small>overkill</small></td><td colspan="6"><small>×0.05</small></td><td><small>—</small></td><td><small>—</small></td><td><small>—</small></td><td><small>one slot already guarantees the OHKO on the shared target → near-veto the other (wasteful) doubler, so the pair that spreads onto the survivor wins. Composes on top of J1</small></td></tr>
<tr><td><small>J3</small></td><td><small>attack alongside partner</small></td><td colspan="6"><small>—</small></td><td><small>×0.5</small></td><td><small>—</small></td><td><small>—</small></td><td><small>a gratuitous lone Protect (no real OHKO/stall reason, e.g. only a Fake Out nudge) beside an attacking partner — favour the double-attack</small></td></tr>
<tr><td><small>J4</small></td><td><small>Fake Out absorbed (free partner)</small></td><td colspan="6"><small>×2.0</small></td><td><small>×0.33</small></td><td><small>—</small></td><td><small>—</small></td><td><small>when either slot attacks, the partner's Fake-Out multiplier above is divided back out (attack un-halved, Protect un-boosted) — a pair pays the Fake-Out adjustment once, never twice</small></td></tr>
<tr><td><small>J5</small></td><td><small>switch collision</small></td><td colspan="6"><small>—</small></td><td><small>—</small></td><td colspan="2"><small>×0</small></td><td><small>both slots switch to the same bench mon → that pair is vetoed</small></td></tr>
<tr><td><small>J6</small></td><td><small>Partner Clears</small></td><td colspan="6"><small>—</small></td><td><small>×3.0</small></td><td><small>—</small></td><td><small>—</small></td><td><small>one slot Protects against a connecting OHKO and the partner's chosen attack guaranteed-OHKOs that threatener → Protect so we survive while the partner removes it (was phase-1 "Threat Clear"; it's a cross-slot question, so it's phase 2)</small></td></tr>
</tbody>
</table>


### Worked example (turn 1)

Our **Garchomp + Kingambit** vs **Incineroar + Basculegion** 

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
