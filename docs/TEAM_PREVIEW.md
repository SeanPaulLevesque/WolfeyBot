# Team Preview — how the brings, mega, and lead are chosen

This covers `team_preview.py`: the once-per-game pipeline that runs the
instant the opponent's six is revealed, before turn 1. It answers three
questions, in order, and each answer feeds the next:

1. **Which 4 of our 6 do we bring?** (`select_team`)
2. **Which brought Mega Stone holder actually mega evolves?** (`select_mega`)
3. **Which 2 of the 4 lead, and in what order do the rest sit?** (`select_leads`)

This is a separate system from the per-turn decision engine documented in
[DECISION_ARCHITECTURE.md](DECISION_ARCHITECTURE.md) — that engine scores
`(move, target)` candidates on a live board; this one scores **roster
choices** before any board exists. They share machinery (the same
`outgoing_damage`/`incoming_damage` calls, the same `make_engine()` for the
lead-board eval) but solve a different problem: an *average over the
opponent's whole six* (bring) or a *hedge over several possible opponent
pairs* (lead), rather than one concrete turn.

**Entry point** (`main.py`'s team-preview handler, called once per game):

```python
slots = select_team(state.opp_preview_team, team, n=n)
slots = select_leads(slots, team, state.opp_preview_team)
state.designated_mega = select_mega(slots, team, state.opp_preview_team)
```

Note the order: `select_leads` reorders the bring-4 (leads first) *before*
`select_mega` runs — but `select_mega` only cares about which stone holder
gained the most from megaing, not lead position, so the order between the
last two doesn't matter in practice.

---

## Part 1 — `select_team`: which 4 to bring

### The core score: `_engine_matchup_scores`

For each of our 6 members, against **every** species in the opponent's
revealed six, compute:

- **offense** = the best damage fraction we deal (real `outgoing_damage`,
  capped at 1.0 — an OHKO can't score higher than a min-roll OHKO)
- **defense** = `1 − worst damage fraction they deal to us` (real
  `incoming_damage`, floored at 0 — a guaranteed OHKO zeroes it outright,
  *regardless of who's faster* — see [Known limitations](#known-limitations))

averaged over the six and combined as:

```
matchup_value = _OFF_WEIGHT × mean(offense) + _DEF_WEIGHT × mean(defense)
```

Shipped at `_OFF_WEIGHT = 2.0`, `_DEF_WEIGHT = 1.0` (offense counts double —
inherited from the pre-engine legacy scorer, kept as tunable constants).

This is **real damage**, not a type-chart multiplier: it calls the same
`outgoing_damage`/`incoming_damage` used in battle, so it's automatically
STAB-, ability-, item-, and (see below) weather-aware. A stone holder is
scored **twice** — once at its mega stats/ability, once at its base — so the
one-mega-per-battle rule (below) has real numbers for both cases instead of a
BST-ratio approximation.

### Weather (0.45.2)

`_assumed_weather_for_six(opp_six)` scans the **whole opponent six** (not
just who's predicted to lead) for a species whose `assumed_forme` carries a
weather-setting ability (`Drought`/`Drizzle`/`Sand Stream`/`Snow Warning`).
If found, that weather is passed into every `outgoing_damage`/
`incoming_damage` call in `_one_form` — both sides, every matchup pair.

Mega-aware for free: `assumed_forme` already resolves to the *modal* forme
(Charizard → Mega-Y → Drought only if Mega-Y actually outnumbers Mega-X in
usage; a modal Mega-X team correctly implies no weather). A rain+sun
conflict on one roster resolves by the slowest setter's weather sticking
(entry abilities fire fastest-first, so the slowest writes last) — same
tiebreak the in-battle `_assumed_weather` uses.

### Opponent-mega weight

The opponent's own assumed mega counts **`_OPP_MEGA_WEIGHT` = 1.5×** in the
six-way average (a weighted mean, not a flat bonus) — their mega is the
team's designated centerpiece, so its matchup should outweigh an average
member's. Shipped after an A/B eyeball across 6 curated opponent sixes: 1.5
moved 2 of 6 (both sun teams, correctly demoting a fragile pick out of the
bring); 2.0 changed nothing 1.5 hadn't already done.

### One mega per battle (native demotion)

Only one Pokémon can actually mega evolve, so a second stone holder playing
with an un-evolved stone is dead weight. `select_team` handles this with a
**greedy pick**, not a static rule:

```python
while remaining and len(picked) < n:
    best = max(remaining, key=_value)   # mega_val, unless a mega is
    picked.append(best)                  # already claimed by an earlier pick
    remaining.remove(best)               # — then base_val
    if <best holds a stone> and not mega_claimed:
        mega_claimed = True
```

The **first** stone holder taken keeps its `mega_val`; any **later** stone
holder is re-valued at its real `base_val` (its own base stats/ability/typing
run through the same real damage calc — not a BST-scaling guess). This
correctly demotes a second mega candidate even when its typing is unchanged
by mega evolution (a pure speed/power mega gains nothing defensively, which a
type-only demotion would miss).

### Archetype bring bonus (0.45.7) — Trick Room

A recognized opponent **archetype** layers one more multiplier on top of the
real matchup score — matching the empirical-pair-prior pattern in lead
selection (matchup × prior, logged separately, never folded into the damage
calc itself).

**The framing**: an archetype is a field condition that changes who wins the
speed race, in a way a static damage/bulk average can't see. Trick Room is
the first instance — it inverts speed order entirely, so the archetype
should reward whichever of *our own* roster benefits most from that
inversion. Deliberately **not a species list**: the reward is a pure function
of base Speed, computed fresh against whatever roster is active.

**Detection** — `_is_trick_room_team`: does the opponent's six contain a
species whose `assumed_forme` is in `_TR_SETTER_SPECIES`
(`decision.modules`: base-formes running Trick Room in ≥40% of their usage —
the *same* population-usage signal that already drives `UrgencyModule`/
`SetupDenialModule` in-battle, just applied to the whole preview six instead
of the live board)?

**Reward** — for each of our 6 members, compute a roster-relative slowness:

```
slowness(form_speed) = (roster_max_speed − form_speed) / (roster_max_speed − roster_min_speed)   ∈ [0, 1]
bring_multiplier = 1 + ARCHETYPE_SLOW_BOOST × slowness
```

applied **separately** to `mega_val` (using that member's mega-form Speed)
and `base_val` (using its base-form Speed) — Camerupt-Mega (base Speed 20) is
even *slower* than base Camerupt (40), so the two tuple entries need their
own multiplier, not one shared per species. `ARCHETYPE_SLOW_BOOST = 2.0`
shipped: the roster's single slowest form gets ×3.0; the fastest gets ×1.0
(no effect at all).

The registry (`_ARCHETYPES: list[Archetype]`) is built to extend without new
code: each row is `(key, label, detect, reward_slow, max_boost)`. A
speed-based archetype that favors *fast* forms instead (`reward_slow=False`)
reuses the exact same mechanism. An archetype whose reaction *isn't*
speed-based (discussed in
[Known limitations](#known-limitations)) would need its own reaction
field — the registry pattern (borrowed from `_SETUP_TYPES` in
`decision/modules.py`) is built for that: one row per archetype, not one
universal formula.

**Verified effect** (live ladder data, 0.45.7, off-meta-team v4 — the team
whose roster includes Camerupt): 25 of 50 games faced a detected Trick Room
opponent; Camerupt + Kingambit were both brought in **25 of 25** of them.
Scored in isolation, Camerupt-Mega's bonus (×3.00) was the single largest of
any roster member; Kingambit's (×2.27) was second — exactly proportional to
base Speed, with zero hand-picked names anywhere in the mechanism.

### Fallback paths

- **No opponent data at all** (`opp_species_list` empty): keep team order,
  first `n` slots.
- **Unresolvable members** (`_members_resolvable` fails — synthetic test
  fixtures, or a corrupt roster): log a warning, keep team order. Real teams
  always resolve through `team.find_member`; this path only exists for tests.
  (The old type-chart parallel scorer that used to back this fallback was
  deleted in cleanup C — there is no non-engine scoring path anymore.)

### Worked example

Off-meta-team v4 vs `["Farigiraf", "Torkoal", "Sinistcha", "Hatterene",
"Indeedee", "Snorlax"]` (a detected Trick Room six; sun also assumed via
Torkoal's Drought):

| Member | Raw matchup (mega/base) | Archetype mult (mega/base) | Boosted (mega/base) |
|---|--:|--:|--:|
| Floette-Eternal | 2.09 / 1.61 | ×1.00 / ×1.24 | 2.09 / 2.00 |
| Camerupt | 1.99 / 1.62 | **×3.00** / ×2.51 | **5.98** / 4.08 |
| Arcanine-Hisui | 1.82 / 1.82 | ×1.29 / ×1.29 | 2.35 / 2.35 |
| Milotic | 1.53 / 1.53 | ×1.51 / ×1.51 | 2.31 / 2.31 |
| Kingambit | 1.65 / 1.65 | ×2.27 / ×2.27 | 3.75 / 3.75 |
| Basculegion | 1.37 / 1.37 | ×1.59 / ×1.59 | 2.17 / 2.17 |

Bring (greedy pick, mega slot claimed by Camerupt first): **Camerupt,
Kingambit, Arcanine-Hisui, Milotic**. With the archetype system disabled on
this same six, the bring set is `{Camerupt, Kingambit, Arcanine-Hisui,
Floette-Eternal}` — on this particular roster Camerupt and Kingambit already
ranked highly on raw matchup, so the archetype's *visible* effect here lands
on the marginal 4th slot (Milotic vs. Floette-Eternal) and on bring
**order** (Camerupt moves to slot 1) rather than rescuing them from being cut
— see the note on bring order below.

---

## Part 2 — `select_mega`: which stone holder actually evolves

Among the brought stone holders, pick the one whose **engine matchup value
gains the most from mega evolving**:

```
gain(member) = mega_val − base_val        (from _engine_matchup_scores)
```

sorted descending, ties broken by the higher `mega_val`. This replaced an
older defensive type-delta ranking that scored ≈0 for most stones — a pure
speed/power mega (unchanged typing) showed no defensive gain under that
scheme even when it was clearly the correct pick.

**Fallback**: with only one stone holder brought, or no opponent data, it's
just the first (only) stone holder in the bring — no engine calc needed.
`None` when nothing brought carries a Mega Stone.

---

## Part 3 — `select_leads`: which 2 lead

### Step 1 — predict the opponent's lead pair

Two data sources, read from `data/lead_stats.py`:

- **Our own observation history** (`Battle Data/lead_stats.json`) —
  `counts` (per-species lead frequency) and `pairs` (per-battle co-occurrence,
  keyed `"A|B"` sorted), accumulated by `record_leads` every game since
  v0.5.0.
- **The Smogon ladder-wide lead file** (`data/leads-gen9…-1760.txt`) — a
  per-species prior with no pair information, scaled down by ÷100 in
  `_single_prior` so it only ever acts as a tiebreak among species we've
  never (or rarely) seen lead; a single real observation always outranks it.

`predict_pair` returns one best-guess pair, in three tiers of evidence:

1. **Confident co-lead** — the candidate pair from the six with the highest
   observed co-lead count, if it reaches `PAIR_MIN_SUPPORT = 2`. This is what
   stops two independently-popular leads that are rarely paired together
   (the classic case: two supports each individually common, but never led
   as a duo) from being predicted as a pair just because each is popular
   alone.
2. **Anchor + real partner** — otherwise, anchor on the single most-likely
   lead (`_single_prior`) and pair it with whichever previewed species it's
   actually been co-led with most (any positive count).
3. **Top-2 singles** — only with zero co-lead evidence for this exact six,
   fall back to the two highest individual lead frequencies.

`predict_pairs` (plural) is the **hedged** form used for actual lead
scoring: the top `k=3` candidate pairs, each weighted by observed co-lead
count plus `pseudo=2.0` pseudo-observations distributed by the singles
prior, normalized to sum to 1. Committing to a single predicted pair is how
a *correct* read still loses — if the read is wrong, the counter-pick built
entirely around it collapses; hedging across the top-3 keeps a reasonable
answer even when the single best guess isn't the one that shows up.

### Step 2 — score every candidate lead pair (`_score_lead_pairs`)

For every `C(n,2)` combination of our brought slots, against every hedged
opponent pair, build a **real turn-1 `BattleState`** (`_preview_state`) and
read the actual decision engine's phase-1 weights (`_eval_lead_board`):

- **Per-slot value** = the best-weighted **attack** action for that mon on
  that board — already folding in real damage (capped at lethal),
  guaranteed-kill bonuses, true turn order, and Fake Out pressure, because
  it's reading the same `engine.scored_actions` the live game uses.
- **`_DOOMED_LEAD_FACTOR = 0.25`** — if the board facts say this slot would
  be KO'd before it can act (`ctx.is_doomed`), the in-battle engine only
  discounts that move ×0.2 (a big kill-stack can still win the argmax); at
  preview, a doomed lead is punished harder, because we can simply not start
  that mon at all. (Root cause: Chandelure led into rain on a doomed-but-huge
  overkill read and went 3–15 vs. a Swampert+Pelipper rain core.)
- **`_SWITCH_WANT_FACTOR = 0.5`** — if the engine's own best action for this
  slot is a **switch**, not an attack, that's the engine telling us this mon
  doesn't want to be on this board at all; the pair is self-refuting.
- **`_LEAD_COVERAGE_FACTOR = 1.0`** (shipped inert) — would penalize a pair
  where both slots' best attack targets the **same** opponent, leaving the
  other free. Exists as an experiment knob; not yet enabled by default.
- **`_ATK_FLOOR = 0.05`** — a slot with no usable attack (e.g. a
  Choice-locked mismatch) still contributes something rather than zeroing
  the whole pair.

Slot values are **multiplied**, not averaged, mirroring the in-battle joint
engine — one dead slot should sink the pair's score, not get diluted by a
strong partner.

**Field variants**: for a given predicted opponent pair, if it contains a
Trick Room setter, the board is also evaluated with Trick Room active; same
for an opponent Tailwind setter — the two (or one) results are averaged, so
a genuinely imminent field effect is priced by the real turn-order model
rather than ignored. Variants key on the *pair itself*, not the wider
roster, deliberately — a setter still sitting on the bench is turns away,
and averaging in a speculative field effect would drown the base-board
reality.

**Combining across the hedge**: candidate-pair scores across the `k`
weighted opponent pairs are combined as a **weighted geometric mean**, not
arithmetic. Board scores are multiplicative kill-stacks spanning orders of
magnitude, so an arithmetic mean lets a low-probability jackpot board
outvote a likely disaster; log-space averaging keeps the likely board
decisive while still crediting a pair that's merely doomed against one
low-weight read. (This mattered: correct single-pair predictions were
observed *losing* 43% vs. 52% before hedging shipped.)

**Empirical pair prior** (`data/our_leads.py`, `pair_factor`) — our own
historical W-L for *this exact lead pair, on this exact team version*,
smoothed with a Beta prior of `SMOOTHING_K = 10` pseudo-games at 50% (an
unseen pair is exactly ×1.0; 10-1 → ×1.43; 18-34 → ×0.74). The board eval is
fundamentally a turn-1 model and can systematically favor pairs that don't
actually convert over a full game — this closes that gap using our real
results, keyed per team version since pair performance doesn't transfer
across rosters. `_PAIR_PRIOR_POWER = 1.0` (an exponent on the prior — >1
would lean harder on it) is a shipped-inert experiment knob.

The winning pair becomes the lead; the rest of the bring keeps its
`select_team`-assigned relative order in the back slots.

### Fallback paths

- No opponent data, or an empty bring list: keep (sorted) bring order.
- No lead-frequency data recorded yet (`total_battles() == 0`): keep
  (sorted) bring order — there's nothing to predict from.
- Unresolvable members: keep bring order (same reasoning as `select_team`'s
  fallback — no legacy non-engine path exists anymore).

### A note on bring order vs. lead order

`select_team`'s returned order (used for logging, and to decide which stone
holder is "first" for the mega-demotion greedy pick) has **no effect** on
which 2 of the 4 actually lead: `select_leads` independently re-derives the
true best pair from the real board eval over every `C(4,2)` combination,
regardless of the order it received. So the archetype bring bonus's effect
on bring *order* (e.g. Camerupt moving to slot 1) is cosmetic; its only
functional effect is on the composition of *which 4* make the bring-4 in
marginal cases.

---

## Known limitations

Two real, current gaps — worth understanding before trusting a specific
matchup read, and candidates for future work:

**1. `select_team`'s matchup score is completely speed/turn-order-blind.**
`_one_form` never touches speed, priority, or turn order anywhere — it's a
pure two-sided damage-fraction average. This is *mostly* fine: a guaranteed
OHKO already floors `defense` to 0 regardless of who's faster, so "can this
resistant pick just get blown up anyway" is captured without needing speed
information. What's genuinely missing is a **multi-turn speed race**: e.g. a
Grass-type that resists Mega Swampert's Water/Ground and looks great on
paper, but where Swampert's Swift Swim (in rain, from some other teammate)
lets it act first turn after turn — a sustained speed advantage the
single-exchange damage-fraction model has no way to represent.

**2. Weather detection is inconsistently scoped between the two stages.**
`select_team`'s `_assumed_weather_for_six` scans the **whole opponent six**
for a weather setter. But `select_leads`'s board eval (`_preview_state`)
hardcodes `s.weather = None` and relies entirely on the in-battle engine's
own `_assumed_weather` inference, which only scans the **two candidate mons
on that specific hypothetical board** — not the wider six. So if a
Swift-Swim mega is evaluated leading alongside a teammate that *isn't* the
rain-setter, that particular candidate pairing's turn-order math never
learns rain is coming, even though `select_team` already knows the whole
roster implies it. The fix would be threading `_assumed_weather_for_six`'s
result into `_preview_state` as an explicit override instead of only letting
the narrower per-board inference apply — not yet implemented.

---

## Constants quick-reference

| Constant | Value | Effect |
|---|--:|---|
| `_OFF_WEIGHT` | 2.0 | Bring score: offense weight |
| `_DEF_WEIGHT` | 1.0 | Bring score: defense weight |
| `_OPP_MEGA_WEIGHT` | 1.5 | Opponent's assumed mega counts extra in the bring average |
| `ARCHETYPE_SLOW_BOOST` | 2.0 | Trick Room archetype: bonus at the roster's slowest form |
| `_DOOMED_LEAD_FACTOR` | 0.25 | Lead score: penalty when the board says this slot dies before acting |
| `_SWITCH_WANT_FACTOR` | 0.5 | Lead score: penalty when the engine's own best action is to switch out |
| `_LEAD_COVERAGE_FACTOR` | 1.0 (inert) | Lead score: would penalize both leads answering the same opponent |
| `_PAIR_PRIOR_POWER` | 1.0 (inert) | Exponent on the empirical pair-performance prior |
| `_ATK_FLOOR` | 0.05 | Lead score: minimum credit for a slot with no usable attack |
| `PAIR_MIN_SUPPORT` (`lead_stats.py`) | 2 | Co-lead count needed to predict a pair outright |
| `SMOOTHING_K` (`our_leads.py`) | 10 | Beta-smoothing pseudo-games for the empirical pair prior |

All of these except the two marked inert are live shipped defaults, not
experiment-only values — see `tools/preview_ab.py` for the harness that
exercises non-default values to eyeball candidate changes before shipping
them.

## Data files

| Path | Written by | Read by |
|---|---|---|
| `Battle Data/lead_stats.json` | `data.lead_stats.record_leads` (every game) | `predict_pair`/`predict_pairs` |
| `Battle Data/our_lead_stats.json` | `data.our_leads.record_result` (every game) | `pair_factor` |
| `data/leads-gen9…-1760.txt` | (static Smogon export) | `ladder_lead_pct` |

## Tools

- `tools/preview_inspect.py` — explain one preview decision end to end (bring
  scores, mega candidates, predicted/hedged opponent pairs, every lead-pair
  score with its firing notes). Reads `tools/scratch/preview.json`.
- `tools/preview_ab.py` — A/B table across multiple opponent sixes and
  multiple constant overrides at once, for eyeballing a candidate tuning
  change before shipping it. Reads `tools/scratch/preview_ab.json`.
- `tools/preview_backtest.py` — replay every logged battle's actual preview
  through the *current* selector and compare against what was really played
  (aggregate corpus check, rather than one matchup at a time).
- `tests/test_team_preview.py` — unit coverage for every mechanism above.
