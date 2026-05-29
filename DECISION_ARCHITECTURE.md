# WolfeyBot — How It Thinks

WolfeyBot plays VGC doubles by running type-matchup math and thirteen decision
questions on every single turn.  This page walks through exactly what it
does — from the team preview screen all the way to choosing a move on turn 7.

---

## Part 1 — Team Preview: Choosing Which 4 to Bring

> 📸 *Screenshot: the Showdown team-preview screen showing the opponent's
> six Pokémon revealed.  Capture this right before clicking "Choose".*

When the opponent's team appears, the bot scores each of our six Pokémon
against the full opponent team.  Two things are measured:

**Offensive coverage** (weighted ×2) — For each opponent, what's the best
type multiplier our moves can reach?  Stomping Tantrum (Ground) vs Incineroar
(Fire/Dark) scores ×2.0 for that matchup; Dragon Claw (Dragon) vs the same
target scores ×1.0.  These are summed across all six opponents.

**Defensive durability** (weighted ×1) — For each opponent, how badly can
their STAB types hit us?  The contribution per opponent is:

| Incoming hit lands as… | Score added |
|---|---|
| Immune (×0.0) | +4.0 |
| Resist (×0.5) | +2.0 |
| Neutral (×1.0) | +1.0 |
| Weak (×2.0) | +0.5 |
| Quad-weak (×4.0) | +0.25 |

The combined score is `(offense × 2) + (defense × 1)`.  The top four are
brought.

### Example — scoring our team against Farigiraf / Incineroar / Sneasler / Kingambit / Talonflame / Pelipper

| Our Pokémon | Moves | Offensive coverage | Defensive durability | **Combined** | Brought? |
|---|---|---|---|---|---|
| Garchomp | Dragon Claw · Stomping Tantrum · Poison Jab · Protect | 14.5 | 8.8 | **37.8** | ✓ |
| Kingambit | Kowtow Cleave · Iron Head · Low Kick · Protect | 12.1 | 7.3 | **31.5** | ✓ |
| Sneasler | Close Combat · Dire Claw · Rock Tomb · Protect | 10.4 | 7.0 | **27.8** | ✓ |
| Aerodactyl | Dual Wingbeat · Rock Tomb · Ice Fang · Protect | 9.6 | 5.9 | **25.1** | ✓ |
| Venusaur | Sludge Bomb · Giga Drain · Earth Power · Protect | 8.3 | 7.2 | **23.8** | ✗ |
| Basculegion-M | Liquidation · Last Respects · Psychic Fangs · Protect | 7.1 | 4.8 | **19.0** | ✗ |

*(Numbers are illustrative — the real calculation uses the exact type chart
and each Pokémon's full move list.)*

### How type matchups are calculated

Each move is a specific type.  Each Pokémon can have up to two types.  Look
up the move's type against **each** of the defender's types, then multiply
the results together.

**Example: Stomping Tantrum (Ground-type) vs Incineroar (Fire / Dark)**

| Move type | Defender type | Multiplier |
|---|---|---|
| Ground | Fire | ×2 (super effective) |
| Ground | Dark | ×1 (neutral) |
| **Combined** | | **×2 × ×1 = ×2** |

**Example: Stomping Tantrum (Ground-type) vs Aerodactyl (Rock / Flying)**

| Move type | Defender type | Multiplier |
|---|---|---|
| Ground | Rock | ×1 (neutral) |
| Ground | Flying | ×0 (immune — Flying types are unaffected by Ground) |
| **Combined** | | **×1 × ×0 = ×0** |

The bot runs this calculation for every move against every opponent to find
the highest multiplier available.

---

## Part 2 — Team Preview: Choosing the Lead Order

The bot tracks which Pokémon opponents have led with across every recorded
battle.  As of this writing, across **72 battles**:

| Opponent lead | Times seen | % of battles |
|---|---|---|
| Whimsicott | 10 | 13.9 % |
| Garchomp | 10 | 13.9 % |
| Farigiraf | 8 | 11.1 % |
| Incineroar | 8 | 11.1 % |
| Sneasler | 6 | 8.3 % |
| Aerodactyl | 6 | 8.3 % |
| Rotom-Wash | 5 | 6.9 % |
| Lopunny | 5 | 6.9 % |
| Charizard | 4 | 5.6 % |
| Glimmora | 4 | 5.6 % |
| … | … | … |

When the bot sees the opponent's six Pokémon, it picks the **two most
historically common leads** from that team.  It then re-runs the
offense/defense scoring from Part 1 — but scored against *just those two
predicted leads* instead of all six.  The two of our four brought mons that
score best against the predicted leads go out first.

**Example:** Opponent shows Farigiraf, Incineroar, Talonflame, Pelipper,
Sneasler, Kingambit.  The bot sees two top leads: Farigiraf (#3 at 11.1%)
and Incineroar (#4 at 11.1%).  It scores our four mons against
Farigiraf + Incineroar specifically.  Kingambit (Kowtow Cleave super-effective
on Farigiraf) and Garchomp (Stomping Tantrum super-effective on Incineroar)
score highest — they lead.

*If there is no lead data yet, the two highest overall-matchup mons lead by
default.*

---

## Part 3 — In-Battle Decisions

### The battle screen

> 📸 *Screenshot: Turn 1 of a battle with Garchomp (slot A) + Kingambit
> (slot B) on our side vs Incineroar (slot 1) + Basculegion (slot 2) on the
> opponent's side.  Capture before any moves are selected.*

All examples in this section use this Turn 1 position:

| Side | Slot A / 1 | Slot B / 2 |
|---|---|---|
| **Ours** | Garchomp — 100 % HP | Kingambit — 100 % HP |
| **Opponent** | Incineroar — 100 % HP | Basculegion — 100 % HP |

Bench available: **Sneasler, Aerodactyl**

---

### How damage is estimated

The bot does not know the opponent's actual EV spread.  It uses the **most
popular published competitive spread** for each Pokémon, taken from usage
statistics.  "Incineroar" is assumed to be running the most common
bulky-support set seen in tournament data — not a custom set.

This means damage numbers are estimates, but they are the best available
guess without scouting.

---

### The 13 questions (Garchomp, slot A, Turn 1)

Every possible action starts at weight **1.00**.  The bot runs through thirteen
questions in order; each one multiplies the weight up or down.  At the end,
the highest-weight action wins.

Garchomp's available actions this turn (moves: Dragon Claw · Stomping Tantrum
· Poison Jab · Protect):

| Action | Type | Matchup | Expected damage |
|---|---|---|---|
| **Stomping Tantrum → Incineroar** | Ground | ×2 vs Fire/Dark | ~85 % HP |
| **Stomping Tantrum → Basculegion** | Ground | ×1 neutral | ~40 % HP |
| **Dragon Claw → Incineroar** | Dragon | ×1 neutral | ~30 % HP |
| **Dragon Claw → Basculegion** | Dragon | ×1 neutral | ~28 % HP |
| **Poison Jab → Incineroar** | Poison | ×1 neutral | ~22 % HP |
| **Poison Jab → Basculegion** | Poison | ×0.5 resist | ~11 % HP |
| **Protect** | — | Always legal | — |
| **Switch → Aerodactyl** | — | Rock/Flying | — |

> **Column key:** ST = Stomping Tantrum · DC = Dragon Claw · PJ = Poison Jab ·
> →I = targeting Incineroar · →B = targeting Basculegion · Prot = Protect ·
> SwA = Switch Aerodactyl
>
> **A dash ( — ) means the module has no effect this turn (×1.00).**

| # | Question | ST→I | ST→B | DC→I | DC→B | PJ→I | PJ→B | Prot | SwA |
|---|---|---|---|---|---|---|---|---|---|
| — | Starting weight | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1 | **How much damage do I deal?** | ×2.70 (85 %) | ×1.80 (40 %) | ×1.60 (30 %) | ×1.56 (28 %) | ×1.44 (22 %) | ×1.22 (11 %) | — | — |
| 2 | **Can I KO one of them this turn?** | — | — | — | — | — | — | — | — |
| 3 | **Can they OHKO me?** | — | — | — | — | — | — | ×2.50 (Wave Crash) | — |
| 4 | **What is my turn-order position?** | ×2.00 (pos 1/4) | ×2.00 | ×2.00 | ×2.00 | ×2.00 | ×2.00 | — | — |
| 5 | **Is a TR/TW setter on the field?** | — | — | — | — | — | — | — | — |
| 6 | **Can I deny their Trick Room or Tailwind?** | — | — | — | — | — | — | — | — |
| 7 | **Did they just use Protect last turn?** | — | — | — | — | — | — | — | — |
| 8 | **Did I use Protect last turn?** | — | — | — | — | — | — | — (first turn) | — |
| 9 | **Will I be OHKO'd this turn anyway?** | — | — | — | — | — | — | — | — |
| 10 | **Is Fake Out coming this turn?** | ×0.50 | ×0.50 | ×0.50 | ×0.50 | ×0.50 | ×0.50 | ×3.00 | — |
| 11 | **Is their Trick Room or Tailwind about to expire?** | — | — | — | — | — | — | — | — |
| 12 | **Is switching out worth more than staying?** | — | — | — | — | — | — | — | ×0.18 |
| 13 | **Are both of us targeting the same opponent?** | — | — | — | — | — | — | — | — |
| — | **Final weight** | **2.70** | **1.80** | **1.60** | **1.56** | **1.44** | **1.22** | **7.50 ✓** | **0.18** |

**Bot chooses Protect** at weight 7.50.

---

### Generic weight table

The same thirteen questions in general form — applicable to any turn, any lead,
any opponent.  Every cell is filled in; **×1.0 means no effect**.

> **Column key:**
> Attack = any damaging move ·
> Protect = Protect-family move ·
> Switch = switch action
>
> **d** = average damage as a fraction of the target's HP (0.0 – 1.0+)

| # | Question | Attack | Protect | Switch |
|---|---|---|---|---|
| — | Starting weight | 1.00 | 1.00 | 1.00 |
| 1 | **How much damage do I deal?** | ×(1 + d×2.0) | ×1.00 | ×1.00 |
| 2 | **Can I KO one of them this turn?** | ×5.0 guaranteed OHKO · ×1.0 otherwise · **withheld entirely if we're guaranteed-KO'd before we can act** (a faster or priority opponent min-roll-OHKOs us and isn't removed first) — a kill we don't live to deliver isn't credited | ×1.00 | ×1.00 |
| 3 | **Can they OHKO me?** | ×1.00 | ×2.5 if an opp has a max-roll OHKO that will still connect — i.e. it is *not* killed before it acts by a faster ally's guaranteed OHKO · ×1.0 otherwise · suppressed in 1v1 endgame / 2v1 | ×1.00 |
| 4 | **What is my turn-order position?** | pos 1 (fastest): ×2.0 · pos 2: ×1.5 · pos 3: ×1.0 · pos 4 (slowest): ×0.75 — position = # of others we likely outspeed (will_outspeed > 0.5) | ×1.00 | ×1.00 |
| 5 | **Is a TR/TW setter on the field?** | TR setter on field + TR not active (or last turn) + no opp TW active: ×2.0 · TW setter on field + TW not active (or last turn) + no TR active: ×1.5 · ×1.0 otherwise | ×1.00 | ×1.00 |
| 6 | **Can I deny their Trick Room or Tailwind?** | ×2.0 vs TR setter · ×1.5 vs TW setter · only when: guaranteed OHKO + we outspeed + no Prankster/Gale Wings priority · redirect if deny-score > current weight · ×1.0 otherwise | ×1.00 | ×1.00 |
| 7 | **Did they just use Protect last turn?** | ×1.3 if target Protected last turn · ×1.0 otherwise | ×1.00 | ×1.00 |
| 8 | **Did I use Protect last turn?** | ×1.00 | ×0.2 if this slot used Protect last turn · ×1.0 otherwise · no exceptions | ×1.00 |
| 9 | **Will I be OHKO'd this turn anyway?** | ×1.00 | ×3.0 when: an opp can OHKO us + at least one such threat still connects (not killed before it acts) + a partner has a guaranteed OHKO on one of the threats · ×1.0 otherwise · suppressed in 1v1 endgame / 2v1 | ×1.00 |
| 10 | **Is Fake Out coming this turn?** | ×0.5 FO threat · ×1.0 otherwise | ×3.0 FO threat · ×1.0 otherwise | ×1.00 |
| 11 | **Is their Trick Room or Tailwind about to expire?** | ×1.00 | turns left = 1 or 3: ×3.0 (applied once even if both TW and TR qualify) · ×1.0 otherwise | ×1.00 |
| 12 | **Is switching out worth more than staying?** | ×1.00 | ×1.00 | board value = TEMPO × (offense_term + escape) × safety. offense_term = 1 + max(0, switch-in_offense − current_offense) × 2 (the gain over staying; halved when not escaping — an unforced pivot concedes initiative). escape = +3.0 when the current mon is OHKO-threatened (by a connecting threat) and the switch-in survives. safety = ×0.3 if the switch-in is itself OHKO'd, else ×1.0. TEMPO = 0.6. ×0.0 if a partner is already switching to the same mon |
| 13 | **Are both of us targeting the same opponent?** | Not doubling: ×1.0 · Both favour: ×0.70 · One favours: ×0.55 · Neither: ×0.40 · Partner near-KO (w ≥ 10): ×0.65 additional · Partner OHKO (w ≥ 15) + alt target: redirect & reset · Partner OHKO (w ≥ 15) no alt: ×0.05 additional | ×1.00 | ×1.00 |

---

### What each question means



**Question 1 — "How much damage do I deal?"**
Formula: `1.0 + (average damage % ÷ 100) × 2.0`.  A move expected to deal
100 % HP (guaranteed KO) scores ×3.00; 50 % scores ×2.00; chip damage of
25 % scores ×1.50.  This question also picks the target — the bot aims at
whichever opponent takes more damage.  Stomping Tantrum's Ground-type ×2
bonus vs Incineroar (Fire/Dark) is what drives the ×2.70 score here.

**Question 2 — "Can I KO one of them this turn or next?"**
Only a guaranteed OHKO (every damage roll exceeds the target's remaining HP)
scores ×5.00.  Stomping Tantrum deals ~85 % per hit against Incineroar — a
near-miss that might land on a lucky roll, but not a guarantee — so this
question has no effect here.  High-damage moves that fall short of a certain
KO are already rewarded by Question 1.

**Offensive speed gate:** the ×5.00 is withheld entirely when we will be
guaranteed-KO'd before we can act — a faster opponent (or a priority attacker
like Gale Wings Brave Bird) that min-roll-OHKOs us and isn't itself removed
first.  A "guaranteed" kill we never live to deliver isn't guaranteed, so
crediting it would let a doomed attack out-score Protecting or switching.  This
is the offensive mirror of Question 3's speed-aware threat check.

**Question 3 — "Can they OHKO me?"**
Basculegion has Wave Crash (Water-type, 120 BP, physical, boosted by
Adaptability).  Water is ×2 super effective vs Garchomp (Ground/Dragon).
Wave Crash lands for 128–151 % of Garchomp's HP — a guaranteed one-hit KO
on every damage roll.  The answer is **yes**, so Protect gains **×2.50**.

This question only affects Protect-family moves.  Attacks are untouched —
Q3 is purely about whether Protecting this turn guarantees survival.  The
boost is suppressed in a 1v1 endgame or when we have a numerical advantage
(2v1), where Protecting cannot improve the outcome regardless of the threat.

**Speed awareness:** an attacker that a *faster* ally is guaranteed to OHKO
this turn dies before it can act, so it is not a live OHKO threat and does
not trigger the boost.  Exception: a Gale Wings Talonflame (priority Brave
Bird at full HP) strikes before our normal-priority KO move, so it is always
treated as a live threat.  Other move-based priority (Prankster status, Fake
Out, Sucker Punch) is not yet modelled.

**Question 4 — "What is my turn-order position?"**
Garchomp (102 base Speed) is faster than all three other active Pokémon —
Incineroar (65), Basculegion (67), and partner Kingambit (50).  Outspeeding
all three places Garchomp in position 1 of 4, applying **×2.00** to all
attack moves.  Going first means every attack is guaranteed to land before
the target can act in response.

The slowest possible position (4th, outspeeding 0 of 3 others) earns only
**×0.75** — the move might land after the target has already acted or been
KO'd by a partner.

| Others outsped | Position | Multiplier |
|---|---|---|
| 3 of 3 | 1st | ×2.0 |
| 2 of 3 | 2nd | ×1.5 |
| 1 of 3 | 3rd | ×1.0 |
| 0 of 3 | 4th | ×0.75 |

**Question 5 — "Is a TR/TW setter on the field?"**
Neither Incineroar nor Basculegion is a Trick Room or Tailwind setter, so
this question has no effect on Turn 1 here.  Whenever a known setter is
active and its field effect is not yet established (or on the final turn
before expiry, when re-setting is a real risk), all attacking moves gain an
unconditional urgency boost: **×2.0** for Trick Room setters and **×1.5** for
Tailwind setters.  The boost fires regardless of whether we can actually KO
the setter.

If the opponent's Trick Room is already running (with more than one turn
remaining) the TR setter boost is suppressed — the setter has already done
its damage this game.  Active Tailwind suppresses the TR boost, and active
Trick Room suppresses the TW boost, preventing overlap with the
FieldSetterDisruption bonuses of the next question.

If Farigiraf (a Trick Room setter) were active here instead of Basculegion,
every one of Garchomp's attacking moves would gain **×2.0**, making a
guaranteed attack on Farigiraf far more attractive even before the denial
conditions of Question 6 are checked.

**Question 6 — "Can I deny their Trick Room or Tailwind?"**
Neither Incineroar nor Basculegion is a known Trick Room or Tailwind setter,
so no effect this turn.  Three conditions must ALL be true before any bonus
fires: (1) we can guaranteed-OHKO the setter, (2) we outspeed it so our
attack lands before it moves, and (3) the setter cannot use the field effect
with +1 priority.

Prankster setters (Whimsicott, and any species with Prankster revealed) use
Tailwind as a priority Status move — we can never attack before it goes up,
so no bonus is ever given.  Talonflame at full HP has Gale Wings active,
giving Flying-type Tailwind +1 priority; once it takes any damage Gale Wings
is lost and it can be denied.

If Farigiraf were in Slot 1 and we had a move that guaranteed an OHKO on it,
targeting Farigiraf would gain **×2.00** — stopping Trick Room before it is
established is a very high priority.  Tailwind setters without a priority
ability (Noivern, Corviknight, etc.) get **×1.50** when the OHKO and speed
conditions are both met.

**Question 7 — "Did they just use Protect last turn?"**
Turn 1 — nobody has moved yet.  On any later turn, if the target used Protect
the turn before (Protect fails if used back-to-back in Gen 9), attacking it
gains **×1.30**.

**Question 8 — "Did I use Protect last turn?"**
Turn 1 — Garchomp has not moved yet, so no penalty.  On any later turn where
this slot used a Protect-family move, all Protect actions receive **×0.2**.
In Gen 9, consecutive Protect has a greatly reduced success rate, so the
expected value is far below a first-use Protect.  The multiplier is always
applied — there are no exceptions for HP level, threat level, or any other
condition.

**Question 9 — "Will I be OHKO'd this turn anyway?"**
No opponent can OHKO Garchomp here, so no boost fires.  In general, all three
conditions must hold for Protect to gain **×3.0**: (1) an opponent can OHKO
this slot on its max damage roll, (2) **speed awareness** — at least one such
threat will actually connect: it is *not* killed before it acts by a faster
ally's guaranteed OHKO (this covers both faster attackers and slower
attackers we cannot remove — either way the hit lands unless we Protect), and
(3) a partner has a non-disabled move that guarantees an OHKO on one of the
OHKO threats.  Condition 3 is the value gate: Protecting is worth the ×3.0
when surviving the unavoidable hit also leaves a threat dead (partner clears
it), so we enter next turn ahead and free to act.  Condition 2 is mostly
Speed-based, but a Gale Wings Talonflame (priority Brave Bird at full HP) is
always treated as connecting; other move-based priority is not yet modelled.
Suppressed in 1v1 endgame and 2v1 numerical advantage.

**Question 10 — "Is Fake Out coming this turn?"**
Incineroar is on the field for the first turn of the battle, and Incineroar
is a known Fake Out user.  Fake Out (priority +3) will flinch one of our
Pokémon 100 % of the time this turn — whichever target Incineroar picks can't
move at all.  In response, the bot discounts **all attacks by ×0.50** (they
might be wasted on a flinched Pokémon, or Incineroar might redirect to the
other slot) and boosts **Protect to ×3.00** on top of any other modifier.

The combined Protect score becomes: ×2.50 (Q3 OHKO threat) × ×3.00 (Q10 Fake
Out) = **×7.50** — the clear winner.

**Question 11 — "Is their Trick Room or Tailwind about to expire?"**
No active field conditions.  The stalling pattern targets every other turn
across the last three: Protect on turn 3 (×3.0), attack freely on turn 2
(no bonus), Protect on the last turn (×3.0).  This wastes two of the three
remaining turns of the field effect without losing two consecutive attacks.

**Question 12 — "Is switching out worth more than staying?"**
A switch is scored by the *value of the resulting board* (a 1-ply lookahead)
rather than a capped type-matchup multiplier, so it competes on the same scale
as an attack: `weight = TEMPO × (offense_term + escape) × safety`.

* **offense_term** rewards the *gain* in best-damage from pivoting —
  `1 + max(0, switch-in_offense − current_offense) × 2` — so a switch only
  scores for offense when the incoming mon threatens meaningfully more than
  staying does.  (The current mon's Struggle counts as zero, so a mon that can
  only Struggle is correctly seen as contributing nothing.)  When we are *not*
  escaping a KO this gain is halved: an unforced pivot concedes initiative.
* **escape** adds **+3.0** when the current mon is OHKO-threatened by a threat
  that will actually connect (speed-aware) and the switch-in survives every
  active opponent's max roll — the value of not losing the mon for free.
* **safety** multiplies by **×0.3** if the switch-in is itself OHKO'd (don't
  pivot into another KO), and **TEMPO = 0.6** discounts for giving up the turn.

In this example Aerodactyl (Rock/Flying) is ×2 weak to Water, so Basculegion's
Wave Crash OHKOs it just as it OHKOs Garchomp: the switch-in does *not* survive,
so there is no escape bonus and safety drops to ×0.3 → **×0.18**.  Had the
switch-in resisted Wave Crash and survived, the escape bonus would lift it to a
weight that competes with Protecting or attacking.  A switch a partner already
claimed is vetoed (**×0.0**).

**Question 13 — "Are both of us targeting the same opponent?"**
This question only applies to Slot B (Kingambit) after Slot A (Garchomp) has
already committed.  Slot A never has a doubling-up penalty.  If Kingambit in
Slot B aimed at the same target Garchomp is already guaranteed to KO, this
module redirects or penalises that choice to avoid overkill.

---

## Weight quick-reference

| Final weight | What it means in practice |
|---|---|
| 10.0 + | Near-certain KO on a key target — almost never override this |
| 4.0 – 9.9 | Strong reason: guaranteed KO range, or a Protect that shields a partner KO |
| 2.0 – 3.9 | Clearly preferred — good damage, 2HKO, solid protective reason, or a clean OHKO-escape switch |
| 1.0 – 1.9 | Roughly baseline — worth doing but no standout reason |
| 0.5 – 0.9 | Discouraged — the bot knows a better option exists |
| 0.0 | Hard veto — will never be chosen (e.g. partner switching to same bench slot) |

