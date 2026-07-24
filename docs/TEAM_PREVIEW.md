# Team Preview — how the brings, mega, and lead are chosen

This covers `team_preview.py`: the once-per-game pipeline that runs the
instant the opponent's six is revealed, before turn 1. It answers three
questions:

1. **Which 4 of our 6 do we bring?** (`select_team`)
2. **Which brought Mega Stone holder actually mega evolves?** (`select_mega`)
3. **Which 2 of the 4 lead, and in what order do the rest sit?** (`select_leads`)

Since 0.45.8 the real dependency runs the other way from how the numbering
suggests: **the lead pair is chosen first**, by real-board evaluation over
the *full* 6-mon roster, and question 1 is answered by seeding that pair into
the bring and filling the remaining slots around it. `select_leads` still
runs afterward and still independently re-derives the winning pair — it just
usually finds the one already sitting in front, rather than discovering it
for the first time. See [Part 1](#part-1--select_team-which-4-to-bring) for
why.

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

### The lead pair is chosen first, by real-board evaluation (0.45.8)

Before any matchup averaging runs, `_select_lead_pair(opp_six, our_members)`
answers a sharper question: **of every possible pairing of our full 6**
(`C(6,2) = 15` candidates), which 2 actually perform best together on a real
turn-1 board against the opponent's likely leads?

This reuses `select_leads`'s own machinery completely unchanged —
`_score_lead_pairs`/`_eval_lead_board`/`make_engine()` are already generic
over an arbitrary slot list; they were just never previously called before
the bring-4 had already been narrowed. Widening the call to all 6 slots
means:

- Real turn order, Fake Out pressure, doom (dying before acting), spread
  credit, recoil, boosted-target focus — **every phase-1 module** — now
  informs *which 4 get brought*, not just which 2 of an already-narrowed 4
  get to lead.
- A strong two-mon partnership can't be missed just because the
  (partner-blind, board-blind) matchup average below happened to rank one of
  its members outside the top 4 on its own.

The winning pair is seeded directly into the bring (as slots 0–1); the
matchup-average scoring below then only has to fill the *remaining* n−2
slots — the bench, which doesn't play turn 1 and so has no real board to
evaluate against in the first place. That's a deliberate division of labor,
not an oversight: a turn-1 board eval has nothing meaningful to say about "is
this mon a good backup for later in the game," which is exactly the question
the broader six-way matchup average is built to answer.

**Fallback**: when there's no lead-frequency data yet (`total_battles() ==
0`) or the roster doesn't resolve, `_select_lead_pair` returns `None` and
`select_team` falls straight back to the pre-0.45.8 behavior — pure matchup
average, greedy pick over all 6, no seeding. This is exact byte-for-byte
equivalence, not an approximation of it (see
`tests/test_team_preview.py::TestRealBoardLeadPairSeedsTheBring`).

**Worked example** — meta-team v11 vs a detected Trick Room six
(`["Farigiraf", "Torkoal", "Sinistcha", "Hatterene", "Indeedee", "Snorlax"]`):

| | Bring |
|---|---|
| Pre-0.45.8 (matchup average only) | Kingambit, Chandelure, Decidueye-Hisui, Basculegion |
| Real-board pair found | **Greninja + Basculegion** |
| 0.45.8 (seeded) | Greninja, Basculegion, Kingambit, Chandelure |

The old scorer never brought Greninja here at all — evaluated 1v1 against
each opponent species independently, its matchup numbers didn't stand out.
But paired with Basculegion on a real board against this six's predicted
leads, it wins the actual turn-1 exchange convincingly enough to top every
other candidate pairing — a fact that was structurally invisible to a scorer
that never builds a board.

### The bench score: `_engine_matchup_scores`

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

### One mega per battle (joint search, 0.45.9)

Only one Pokémon can actually mega evolve, so a second stone holder playing
with an un-evolved stone is dead weight. With 0-1 stone holders on the
roster there's no ambiguity — that holder (if any) simply keeps its
`mega_val` throughout, no search needed.

With **2+** stone holders, which ONE should be mega is *coupled* to the rest
of the bring — whichever one ISN'T mega falls back to `base_val` for the
whole bring decision, which can change who else even makes the cut. So
`select_team` decides it jointly instead of letting greedy pick order
decide by accident (the pre-0.45.9 behavior: whichever holder happened to be
seeded via the lead pair, or picked first in the greedy loop, silently
"claimed" the mega slot for scoring purposes — an accident of iteration
order, not a real decision, and one that could disagree with what
`select_mega` designated afterward):

```python
def _fill(mega_holder):
    """Greedy-fill the bring assuming *mega_holder* is the one stone holder
    scored at its mega value; every other holder scores at base."""
    ...

best_picked, best_total = None, -1.0
for h in holders_all:            # every stone holder on the FULL 6-mon roster
    candidate = _fill(h)
    total = _bring_total(candidate, our_members, engine_scores, h)
    if total > best_total:
        best_picked, best_total = candidate, total
picked = best_picked
```

Real rosters essentially never carry 3+ Mega Stones, so this is at most a
couple of cheap re-runs of the existing greedy-fill, not a real
combinatorial search. `select_mega` (below) shares this exact
`_bring_total` criterion, so the two functions can never disagree about
which holder should be mega for a given battle.

### Archetype bring bonus (0.45.7, confidence-weighted since 0.45.9) — Trick Room

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

**Confidence, not a binary flag** — `_trick_room_confidence`: the MAX, across
the opponent's six, of each member's real population usage rate for the move
Trick Room on its **assumed forme** (`data.sets.move_distribution`; the
assumed forme matters — Gardevoir's own usage is 25% but Gardevoir-Mega's is
56%, so stripping the mega suffix first would silently under-read exactly
the case that matters). A near-100%-usage setter reads as near-certain; a
45%-of-the-time set earns roughly half the bring bonus, not the full swing.

This replaced an earlier binary version (`_is_trick_room_team`: does the six
contain ANY species clearing a static ≥40% threshold, applied at full
strength) after it was caught tripling Camerupt's score off a six that
included Sinistcha and Gardevoir-Mega — both real, but only *sometimes* run,
Trick Room setters — even though the opponent's actual game plan that game
was Rain, and Trick Room was never set once. Rejected fix: "suppress the
archetype whenever a weather setter is also present in the six" — Trick
Room *and* weather are not mutually exclusive (Trick-Room-sun with Torkoal
is a real, common VGC archetype), so a blanket conflict rule would misfire
against a genuine TR-sun team exactly as often as it fixed a false read.
Scaling by the setter's own real usage rate sidesteps this entirely — it
never reasons about weather at all, only the actual per-species probability.

**Reward** — for each of our 6 members, compute a roster-relative slowness
and scale by the archetype's confidence:

```
slowness(form_speed) = (roster_max_speed − form_speed) / (roster_max_speed − roster_min_speed)   ∈ [0, 1]
bring_multiplier = 1 + ARCHETYPE_SLOW_BOOST × confidence × slowness
```

applied **separately** to `mega_val` (using that member's mega-form Speed)
and `base_val` (using its base-form Speed) — Camerupt-Mega (base Speed 20) is
even *slower* than base Camerupt (40), so the two tuple entries need their
own multiplier, not one shared per species. `ARCHETYPE_SLOW_BOOST = 2.0`
shipped: the roster's single slowest form gets ×3.0 **at 100% confidence**;
the fastest gets ×1.0 regardless (no effect at all); a less-than-certain read
scales linearly down from there.

The registry (`_ARCHETYPES: list[Archetype]`) is built to extend without new
code: each row is `(key, label, confidence, reward_slow, max_boost)`, where
`confidence` returns a float in `[0, 1]`, not a bool. A speed-based archetype
that favors *fast* forms instead (`reward_slow=False`) reuses the exact same
mechanism. An archetype whose reaction *isn't* speed-based (discussed in
[Known limitations](#known-limitations)) would need its own reaction
field — the registry pattern (borrowed from `_SETUP_TYPES` in
`decision/modules.py`) is built for that: one row per archetype, not one
universal formula.

This composes correctly with the 0.45.8 real-board lead-pair seeding above:
when the seeded lead pair doesn't happen to include the archetype's favored
member (the real board found a stronger *lead* elsewhere), the archetype
bonus still pulls it into the bench-fill slots — confirmed on the worked
example below.

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
"Indeedee", "Snorlax"]` (Farigiraf is a 96.97%-usage Trick Room setter —
near-certain; sun also assumed via Torkoal's Drought):

| Member | Raw matchup (mega/base) | Archetype mult (mega/base) | Boosted (mega/base) |
|---|--:|--:|--:|
| Camerupt | 1.99 / 1.62 | **×2.94** / ×2.47 | **5.86** / 4.00 |
| Floette-Eternal | 2.09 / 1.61 | ×1.00 / ×1.24 | 2.09 / 1.99 |
| Arcanine-Hisui | 1.82 / 1.82 | ×1.28 / ×1.28 | 2.33 / 2.33 |
| Milotic | 1.53 / 1.53 | ×1.50 / ×1.50 | 2.29 / 2.29 |
| Kingambit | 1.65 / 1.65 | ×2.23 / ×2.23 | 3.69 / 3.69 |
| Basculegion | 1.37 / 1.37 | ×1.57 / ×1.57 | 2.15 / 2.15 |

Bring: **Floette-Eternal, Arcanine-Hisui, Camerupt, Kingambit** (mega:
Camerupt). With the archetype system disabled on this same six, the bring
SET is identical — `{Camerupt, Kingambit, Arcanine-Hisui, Floette-Eternal}`
— since Camerupt and Kingambit already ranked highly on raw matchup here, so
the archetype's *visible* effect on this particular roster lands on the mega
assignment (Camerupt over Floette-Eternal) rather than on which 4 are cut.

---

## Part 2 — `select_mega`: which stone holder actually evolves

Ranks the brought stone holders by `_bring_total` (see above) — the whole
bring's summed engine value with that holder as mega and every other holder
demoted to base. Since the bring is already fixed by the time this runs,
only one term changes between any two holder hypotheses, so this is
*algebraically identical* to the simpler `gain = mega_val − base_val`
ranking that shipped originally (sorted descending, ties broken by the
higher `mega_val`) — no formula change was needed here.

The real 0.45.9 fix is a **data-consistency** one: this used to compute its
own fresh, non-archetype-adjusted matchup scores, while `select_team`
(which decides who is even a bring-4 candidate in the first place) applies
the archetype bonus on top — the two could reach genuinely different
numbers for the same battle. Now both read the SAME archetype-adjusted
scores, so `select_mega` can never disagree with the bring `select_team`
already committed to.

(The original `gain` ranking replaced an even older defensive type-delta
ranking that scored ≈0 for most stones — a pure speed/power mega, unchanged
typing, showed no defensive gain under that scheme even when it was clearly
the correct pick.)

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

Before 0.45.8, `select_team`'s returned order had no functional bearing on
who leads — `select_leads` always independently re-derived the true best
pair from scratch. Since 0.45.8, `select_team` typically *already puts the
real lead pair first*, because it ran the same real-board search
(`_select_lead_pair`) over the full roster before bench-filling. But
`select_leads` still runs afterward and still independently re-derives the
winning pair over whatever 4 it's handed, rather than trusting the input
order — this is deliberate: it's the sole source of truth whenever
`select_team` *couldn't* seed a pair (no lead data yet, unresolvable
members), and the recompute is idempotent and cheap enough not to bother
skipping in the common case where it just reconfirms what's already there.

---

## Known limitations

Two real, current gaps — worth understanding before trusting a specific
matchup read, and candidates for future work:

**1. Only the LEAD portion of bring is speed/turn-order-aware; the BENCH
portion still isn't.** Since 0.45.8 the lead pair is chosen by a real board
eval (full turn order, doom, Fake Out, everything), but the remaining n−2
bench slots are still filled by `_engine_matchup_scores`/`_one_form`, which
never touches speed, priority, or turn order anywhere — a pure two-sided
damage-fraction average. This is *mostly* fine for a bench pick: a guaranteed
OHKO already floors `defense` to 0 regardless of who's faster, so "can this
resistant pick just get blown up anyway" is captured without needing speed
information, and a bench member doesn't have a turn-1 board to evaluate
against in the first place. What's genuinely missing is a **multi-turn speed
race**: e.g. a Grass-type bench pick that resists Mega Swampert's
Water/Ground and looks great on paper, but where Swampert's Swift Swim (in
rain, from some other teammate) lets it act first turn after turn once it
switches in — a sustained speed advantage the single-exchange damage-fraction
model has no way to represent.

**2. Weather detection is inconsistently scoped, and now touches more of the
pipeline than before.** `select_team`'s `_assumed_weather_for_six` (both for
bench-filling and, via `_archetype_bring_bonus`, the archetype system) scans
the **whole opponent six** for a weather setter. But every real-board
evaluation — `_preview_state`, called by both `_select_lead_pair`'s
full-roster search *and* `select_leads`'s narrower recompute — hardcodes
`s.weather = None` and relies entirely on the in-battle engine's own
`_assumed_weather` inference, which only scans the **two candidate mons on
that specific hypothetical board**, not the wider six. So if a Swift-Swim
mega is evaluated as part of a candidate pairing alongside a teammate that
*isn't* the rain-setter, that pairing's turn-order math never learns rain is
coming — even though `select_team` already knows the whole roster implies
it, and even though this candidate pairing now directly decides the lead (not
just a downstream reordering within an already-fixed bring-4, as before
0.45.8). Widening real-board evaluation to the bring decision makes this gap
matter slightly more than it used to, not less. The fix would be threading
`_assumed_weather_for_six`'s result into `_preview_state` as an explicit
override instead of only letting
the narrower per-board inference apply — not yet implemented.

---

## Constants quick-reference

| Constant | Value | Effect |
|---|--:|---|
| `_OFF_WEIGHT` | 2.0 | Bring score: offense weight |
| `_DEF_WEIGHT` | 1.0 | Bring score: defense weight |
| `_OPP_MEGA_WEIGHT` | 1.5 | Opponent's assumed mega counts extra in the bring average |
| `ARCHETYPE_SLOW_BOOST` | 2.0 | Trick Room archetype: bonus at the roster's slowest form, at 100% detection confidence |
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
