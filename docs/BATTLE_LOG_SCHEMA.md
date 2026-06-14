# WolfeyBot Battle Log Schema

Reference for analyzing `Battle Data/{version}/*.json` files.
This file is the only context needed — do not load `recorder.py` or `analyze_battles.py`.

---

## Top-level object

```
{
  "id":      "battle-gen9championsvgc2026regma-2617125251",  // Showdown battle ID
  "v":       "0.4.0",                                        // bot version
  "t":       "2026-05-24T19:23:28Z",                        // UTC timestamp
  "outcome": "win" | "loss" | null,                         // null = abandoned
  "turns":   [ <turn>, ... ],
  "data_gaps": ["stats:Stunfisk-Galar", "types:Fakemon"]    // OPTIONAL (0.7.6)
}
```

`data_gaps` (optional, 0.7.6+): deduped `"kind:species"` strings for every
data-layer lookup that failed during the battle — present **only** when at
least one lookup failed, so its mere presence flags a problem.  Kinds:
`stats` (no base stats/spread — the mon scored as harmless), `types`
(matchups went neutral), `moves` (no usage moves — synthetic STAB fallback),
`sets` (no usage entry — ability/item inference blind), `team_member`
(find_member failed for one of OUR mons — slot skipped in the fact loops).
Also emitted as a `WARNING` log line when the battle is saved.

---

## Turn object

```
{
  "n":    1,           // turn number
  "w":    "SunnyDay",  // weather: "SunnyDay" | "RainDance" | "Sandstorm" | "Snow" | null (omitted)
  "te":   "Electric",  // terrain (omitted if none)
  "tr":   true,        // Trick Room active (omitted when false)
  "my":   [ <active>, ... ],   // our active slot(s), index = slot
  "opp":  [ <active>, ... ],   // opponent actives, index = slot
  "team": [ <active>, ... ],   // full 4-mon team snapshot (including actives)
  "dec":  [ <decision>, ... ], // one entry per active slot that had a choice
  "ev":   [ <event>, ... ]     // OPTIONAL (0.8.1) actual move resolution (omitted if none)
}
```

### Move-resolution event object (`ev`, 0.8.1+)

The actual moves that resolved this turn, in order — for comparing the
engine's *predictions* (in `dec[].acts[].r` reason strings: `damage_output:
…% HP`, `turn_order: pos X/4`, guaranteed-OHKO) against what really happened.

```
{
  "o":  0,            // resolution order index within the turn (0 = acted first)
  "sd": "us",         // "us" | "opp"
  "a":  "Garchomp",   // actor species
  "mv": "Earthquake", // move used
  "tg": "Incineroar", // target species (omitted if no single target)
  "h0": 1.0,          // target HP fraction BEFORE the hit (omitted if no target; 0.8.2+)
  "d":  0.6           // observed damage as a fraction of target max HP (omitted if none)
}
```

With `h0` + `d`, a predicted guaranteed-OHKO is verifiable (`d >= h0` ⇒ the
hit removed the target's remaining HP), and predicted-vs-actual damage can be
compared on the correct remaining-HP denominator.

Known limits: a spread move hitting two targets records `d` for the first
target only; switches are not recorded as events (only `|move|` actions).

### Active mon object (`my`, `opp`, `team`)

```
{
  "s":   "Sneasler",  // species name
  "hp":  0.74,        // current HP as 0.0–1.0 fraction (0.0 = fainted)
  "sts": "brn",       // status: "brn"|"par"|"slp"|"frz"|"psn"|"tox" (omitted if none)
  "mv":  ["Earthquake", "Close Combat"]  // opp only: revealed moves (omitted if none known)
}
```

---

## Decision object

```
{
  "sl":   0,          // slot index: 0 = left active, 1 = right active
  "ch":   "Protect",  // chosen action label (the action actually sent)
  "acts": [ <action>, ... ]  // top scored actions, highest weight first (up to 4)
}
```

### Action object

```
{
  "lb":  "Protect",              // label: move name or "Switch {species}"
  "w":   2.5,                    // final weight (2 dp). All actions start at 1.0; modules multiply.
  "ts":  0,                      // target_slot: 0 or 1 (omitted if null / not applicable)
  "sw":  "Sneasler",             // switch_target species (omitted for move actions)
  "r":   ["protect: OHKO threat -> x2.5", "priority_speed: already outspeeds -> x0.8"]
                                 // reason strings, one per module adjustment (omitted if empty)
}
```

---

## Scoring modules and reason string format

Each reason string is `"{module}: {description} -> x{multiplier}"`.

| Module | Fires when | Typical multiplier |
|---|---|---|
| `damage_output` | Move deals damage | `1.0 + fraction × 2.0`  (e.g. 50% HP → x2.0) |
| `threat_elimination` | Guaranteed OHKO / max-roll OHKO / 2HKO | x5.0 / x2.5 / x1.5 |
| `opp_protect_recency` | Target used Protect last turn | x1.3 |
| `priority_speed` | Priority move; speed matchup check | x1.5 (useful) / x0.8 (wasted) |
| `priority_speed` | Fake Out available (first turn in) | extra x3.0 |
| `protect` | OHKO threat incoming | x2.5 |
| `protect` | Low HP < 25% | x1.5 |
| `protect` | Critical HP < 5% | x3.0 |
| `protect` | Used Protect last turn | x0.1 (penalty) |
| `protect` | 1v1 endgame | no bonus applied |
| `fake_out` | Opponent Fake Out user is fresh | Protect x3.0 / attacks x0.5 |
| `field_condition` | Last turn of opp Tailwind or Trick Room | x3.0 |
| `switch_eval` | Type matchup vs inferred threats | x0.4–x4.0 |
| `switch_eval` | Partner already switching to same target | x0 (veto) |
| `doubling_up` | Both slots targeting same opponent | x0.55–x0.85 (penalty) |
| `doubling_up` | Partner has confirmed OHKO, redirect available | redirect, no penalty |
| `doubling_up` | Partner has confirmed OHKO, no alt target | extra x0.05 |

**Reading a weight:** A weight of `16.0` means the modules collectively multiplied 1.0 × 3.20 × 5.0.
The chosen action (`ch`) is always the highest-weight action in `acts`.

---

## Real example — turn 1

```json
{
  "n": 1,
  "w": "SunnyDay",
  "tr": true,
  "my":  [{"s": "Sneasler",  "hp": 0.82},
          {"s": "Basculegion","hp": 1.0}],
  "opp": [{"s": "Charizard-Mega-Y", "hp": 0.42, "mv": ["Weather Ball"]},
          {"s": "Rotom-Wash",        "hp": 0.9,  "mv": ["Hydro Pump","Thunderbolt","Will-O-Wisp"]}],
  "team":[{"s": "Sneasler",   "hp": 0.82},
          {"s": "Basculegion","hp": 1.0},
          {"s": "Kingambit",  "hp": 1.0},
          {"s": "Aerodactyl-Mega","hp": 1.0}],
  "dec": [
    {
      "sl": 0, "ch": "Protect",
      "acts": [
        {"lb": "Protect",      "w": 2.0,  "r": ["priority_speed: already outspeeds all opponents -> x0.8",
                                                  "protect: OHKO threat -> x2.5"]},
        {"lb": "Dual Wingbeat","w": 1.83, "ts": 0, "r": ["damage_output: 41% HP -> x1.83"]},
        {"lb": "Rock Tomb",    "w": 1.68, "ts": 1, "r": ["damage_output: 34% HP -> x1.68"]},
        {"lb": "Ice Fang",     "w": 1.45, "ts": 0, "r": ["damage_output: 23% HP -> x1.45"]}
      ]
    },
    {
      "sl": 1, "ch": "Iron Head",
      "acts": [
        {"lb": "Iron Head",    "w": 16.0, "ts": 0, "r": ["damage_output: 110% HP -> x3.20",
                                                           "threat_elimination: guaranteed OHKO on Hatterene -> x5.0"]},
        {"lb": "Kowtow Cleave","w": 3.37, "ts": 0, "r": ["damage_output: 62% HP -> x2.25",
                                                           "threat_elimination: 2HKO on Hatterene -> x1.5"]},
        {"lb": "Protect",      "w": 1.5,  "r": ["priority_speed: priority useful (opponent may outspeed) -> x1.5"]},
        {"lb": "Low Kick",     "w": 1.22, "ts": 1, "r": ["damage_output: 11% HP -> x1.22"]}
      ]
    }
  ]
}
```

---

## Quick reference

| Field | Type | Notes |
|---|---|---|
| `hp` | float 0.0–1.0 | 0.0 = fainted |
| `ts` | int 0 or 1 | opponent slot index; 0 = left, 1 = right |
| `w` (action) | float | product of all module multipliers; starts at 1.0 |
| `w` (turn) | string | weather condition name |
| `tr` | bool | only present (true) when Trick Room is active |
| `sw` | string | species name; only on switch actions |
| `mv` | list[str] | opponent revealed moves; only on `opp` entries; omitted if empty |
| `sts` | string | status condition; omitted if none |

Weather values: `"SunnyDay"` · `"RainDance"` · `"Sandstorm"` · `"Snow"`
Status values: `"brn"` · `"par"` · `"slp"` · `"frz"` · `"psn"` · `"tox"`
