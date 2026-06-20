# Team Report - meta-team v2

**Games:** 25 | **Win rate:** 13-12 (52%) | **Engine:** v0.20.0

*Source: `Battle Data/0.20.0 - team v2`*

## Team

```
Staraptor @ Staraptite
Ability: Intimidate
Level: 50
EVs: 18 HP / 16 Atk / 32 Spe
Jolly Nature
- Close Combat
- Brave Bird
- Steel Wing
- Protect

Kingambit @ Chople Berry
Ability: Defiant
Level: 50
EVs: 31 HP / 32 Atk / 3 Spe
Adamant Nature
- Kowtow Cleave
- Iron Head
- Low Kick
- Protect

Sneasler @ White Herb
Ability: Unburden
Level: 50
EVs: 32 HP / 5 Atk / 16 Def / 13 Spe
Jolly Nature
- Close Combat
- Dire Claw
- Rock Tomb
- Protect

Basculegion-M (M) @ Sitrus Berry
Ability: Adaptability
Level: 50
EVs: 32 HP / 17 Atk / 17 Def
Adamant Nature
- Wave Crash
- Last Respects
- Psychic Fangs
- Protect

Venusaur @ Venusaurite
Ability: Chlorophyll
Level: 50
EVs: 32 HP / 7 Def / 18 SpA / 9 Spe
Modest Nature
- Sludge Bomb
- Giga Drain
- Earth Power
- Protect

Garchomp @ Choice Scarf
Ability: Rough Skin
Level: 50
EVs: 5 HP / 32 Atk / 29 Spe
Adamant Nature
- Dragon Claw
- Stomping Tantrum
- Poison Jab
- Rock Tomb
```

## Roster

Sorted by net (KOs - faints). *WR (brought)* is subject to selection bias.

| Mon | Bring | Lead | WR (brought) | KOs | Faints | Net |
|---|--:|--:|--:|--:|--:|--:|
| Sneasler | 72% | 40% | 44% | 12 | 0 | +12 |
| Kingambit | 88% | 32% | 50% | 14 | 3 | +11 |
| Venusaur | 64% | 32% | 50% | 13 | 2 | +11 |
| Basculegion | 44% | 16% | 73% | 10 | 0 | +10 |
| Garchomp | 96% | 56% | 50% | 13 | 6 | +7 |
| Staraptor | 36% | 24% | 56% | 8 | 3 | +5 |

## Move usage

Times each move was chosen (excludes switches). **Lowest** = swap candidate.

| Mon | Moves (chosen count) | Lowest |
|---|---|---|
| Garchomp | Stomping Tantrum 45, Dragon Claw 12, Rock Tomb 9, Poison Jab 8 | **Poison Jab 8** |
| Kingambit | Kowtow Cleave 32, Iron Head 16, Protect 4, Low Kick 3 | **Low Kick 3** |
| Sneasler | Close Combat 25, Dire Claw 16, Protect 8, Rock Tomb 3 | **Rock Tomb 3** |
| Venusaur | Sludge Bomb 19, Giga Drain 15, Earth Power 10, Protect 3 | **Protect 3** |
| Basculegion | Wave Crash 19, Last Respects 12, Protect 1 | **Protect 1** |
| Staraptor | Brave Bird 12, Close Combat 11, Steel Wing 2, Protect 2 | **Steel Wing 2** |

## Game length

| Turns | Record | Win rate |
|---|---|--:|
| 1-3 | 1-0 | 100% |
| 4-6 | 7-3 | 70% |
| 7-9 | 4-9 | 31% |
| 10+ | 1-0 | 100% |

## Opponent archetypes

*W/L when the opponent established each condition. A game can count in several (e.g. Tailwind + Sun); `None` = no TR/TW/weather.*

| Archetype | Record | Win rate | Games |
|---|---|--:|--:|
| Trick Room | 1-3 | 25% | 4 |
| Tailwind | 2-8 | 20% | 10 |
| Rain | 1-5 | 17% | 6 |
| Sun | 2-1 | 67% | 3 |
| Sand | 1-1 | 50% | 2 |
| None | 6-1 | 86% | 7 |

## Opponent megas

*W/L vs the opponent mega that appeared (one mega-evolves per battle); `None (no mega)` = opponent never mega-evolved.*

| Opponent mega | Record | Win rate | Games |
|---|---|--:|--:|
| Floette-Mega | 1-2 | 33% | 3 |
| Pyroar-Mega | 1-1 | 50% | 2 |
| Swampert-Mega | 0-2 | 0% | 2 |
| Blaziken-Mega | 1-0 | 100% | 1 |
| Chandelure-Mega | 0-1 | 0% | 1 |
| Charizard-Mega-Y | 1-0 | 100% | 1 |
| Delphox-Mega | 1-0 | 100% | 1 |
| Metagross-Mega | 0-1 | 0% | 1 |
| Raichu-Mega-X | 0-1 | 0% | 1 |
| Scovillain-Mega | 0-1 | 0% | 1 |
| Scrafty-Mega | 1-0 | 100% | 1 |
| Staraptor-Mega | 0-1 | 0% | 1 |
| Steelix-Mega | 0-1 | 0% | 1 |
| None (no mega) | 7-1 | 88% | 8 |

## Prediction accuracy

*Each case is a **gap** (actionable) or **accepted** (explained, with reason). Goal: gaps to zero; accepted rows stay so the checks keep running.*

**Offense** 11 (11 gaps) | **Defense** 4 (2 gaps) | **Turn order** 13 misreads (3 gaps) | **Immunity** 3 (0 gaps)

### Defensive mis-model
*Incoming hits >slop above prediction (crits/misses excluded).*

| Attacker | Move | vs Defender | Predicted | Actual | Disposition |
|---|---|---|--:|--:|---|
| Metagross-Mega | Psychic Fangs | Staraptor-Mega | 47% | 89% | gap |
| Armarouge | Heat Wave | Kingambit | 79% | 100% | gap |
| Excadrill | Horn Drill | Staraptor-Mega | n/a | 100% | accepted: unassessed move (off-meta / below usage cutoff) |
| Floette-Mega | Dazzling Gleam | Sneasler | n/a | 52% | accepted: unassessed move (off-meta / below usage cutoff) |

### Offensive mis-model
*Our outgoing damage vs actual (|error| > slop). Dir = over/under.*

| Attacker | Move | vs Target | Predicted | Actual | Dir | Disposition |
|---|---|---|--:|--:|:-:|---|
| Garchomp | Stomping Tantrum | Scovillain | 100% | 41% | over | gap |
| Sneasler | Close Combat | Archaludon | 93% | 39% | over | gap |
| Staraptor | Steel Wing | Ninetales-Alola | 100% | 52% | over | gap |
| Staraptor | Brave Bird | Sinistcha | 100% | 53% | over | gap |
| Kingambit | Kowtow Cleave | Meowstic | 100% | 62% | over | gap |
| Staraptor-Mega | Close Combat | Maushold-Four | 40% | 73% | under | gap |
| Sneasler | Close Combat | Raichu | 88% | 64% | over | gap |
| Garchomp | Poison Jab | Grimmsnarl | 63% | 39% | over | gap |
| Garchomp | Dragon Claw | Swampert-Mega | 38% | 19% | over | gap |
| Venusaur-Mega | Sludge Bomb | Sinistcha | 43% | 60% | under | gap |
| Garchomp | Stomping Tantrum | Scovillain-Mega | 36% | 20% | over | gap |

### Turn order
*Predicted resolution position (1 = fastest of 4) vs actual, over full 4-move turns. Protect/Endure jumping ahead is excluded.*

| Result | Count | Share |
|---|--:|--:|
| exact | 21 | 62% |
| off by 1 | 9 | 26% |
| off by 2+ | 4 | 12% |

Off-by-2+ misreads (board state at the misread turn; *Predicted* = where we expected the flagged mon, *Actual* = the real resolution order):

| Turn | my[a] | my[b] | opp[a] | opp[b] | TR | TW | Predicted | Actual order | Disposition |
|--:|---|---|---|---|:-:|:-:|---|---|---|
| 5 | Garchomp | Venusaur | Annihilape | Pelipper | - | opp | my[a] 3/4 | my[a] > opp[a] > opp[b] > my[b] | gap |
| 2 | Garchomp | Basculegion | Garchomp | Delphox | - | - | my[a] 3/4 | my[a] > opp[b] > opp[a] > my[b] | gap |
| 4 | Garchomp | Sneasler | Garchomp | Staraptor | - | - | my[a] 4/4 | opp[b] > my[a] > my[b] > opp[a] | gap |
| 2 | Garchomp | Staraptor | Maushold-Four | Grimmsnarl | - | - | my[b] 2/4 | opp[b] > my[a] > opp[a] > my[b] | accepted: priority (higher-priority move resolved ahead) |

### Immunity
*Move fired into an immune target.*

| Move | vs Target | Predicted | Why | Disposition |
|---|---|--:|---|---|
| Stomping Tantrum | Corviknight | 0% | type immunity | accepted: forced (0% predicted, Choice-locked into sole immune target) |
| Stomping Tantrum | Corviknight | 0% | type immunity | accepted: forced (0% predicted, Choice-locked into sole immune target) |
| Stomping Tantrum | Corviknight | 0% | type immunity | accepted: forced (0% predicted, Choice-locked into sole immune target) |
