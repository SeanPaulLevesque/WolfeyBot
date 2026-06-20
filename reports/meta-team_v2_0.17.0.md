# Team Report - meta-team v2

**Games:** 50 | **Win rate:** 25-25 (50%) | **Engine:** v0.17.0

*Source: `Battle Data/0.17.0 - team v2`*

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
| Kingambit | 88% | 36% | 50% | 29 | 4 | +25 |
| Garchomp | 96% | 74% | 48% | 28 | 6 | +22 |
| Venusaur | 72% | 38% | 44% | 24 | 5 | +19 |
| Basculegion | 38% | 20% | 68% | 19 | 2 | +17 |
| Sneasler | 86% | 22% | 44% | 23 | 10 | +13 |
| Staraptor | 20% | 10% | 70% | 8 | 0 | +8 |

## Move usage

Times each move was chosen (excludes switches). **Lowest** = swap candidate.

| Mon | Moves (chosen count) | Lowest |
|---|---|---|
| Garchomp | Stomping Tantrum 46, Poison Jab 36, Dragon Claw 32, Rock Tomb 19 | **Rock Tomb 19** |
| Kingambit | Kowtow Cleave 75, Iron Head 29, Protect 13, Low Kick 12 | **Low Kick 12** |
| Sneasler | Close Combat 48, Dire Claw 35, Rock Tomb 20, Protect 15 | **Protect 15** |
| Venusaur | Sludge Bomb 50, Earth Power 21, Giga Drain 17, Protect 15 | **Protect 15** |
| Basculegion | Wave Crash 32, Last Respects 14, Protect 5, Psychic Fangs 4 | **Psychic Fangs 4** |
| Staraptor | Close Combat 11, Brave Bird 9, Steel Wing 2, Protect 2 | **Steel Wing 2** |

## Game length

| Turns | Record | Win rate |
|---|---|--:|
| 1-3 | 4-0 | 100% |
| 4-6 | 11-14 | 44% |
| 7-9 | 10-6 | 62% |
| 10+ | 0-5 | 0% |

## Prediction accuracy

**Offense** 86% (153/178 within +/-15%, 25 mis-models) | **Turn order** 57% exact (+/-1 39%, off-by-2+ 4%) | **Defense** 17 mis-models (10 model gaps, 7 tech)

### Defensive mis-model
*Incoming hits >slop above prediction (crits/misses excluded). Mode `known` = assessed move under-rated; `tech` = move never assessed.*

| Attacker | Move | vs Defender | Predicted | Actual | Mode |
|---|---|---|--:|--:|---|
| Aerodactyl-Mega | Ice Fang | Garchomp | n/a | 100% | tech |
| Floette-Mega | Dazzling Gleam | Basculegion | n/a | 55% | tech |
| Annihilape | Rage Fist | Basculegion | 50% | 95% | known |
| Staraptor-Mega | Close Combat | Garchomp | 66% | 100% | known |
| Staraptor-Mega | Close Combat | Garchomp | 66% | 100% | known |
| Raichu-Mega-X | Volt Tackle | Sneasler | n/a | 87% | tech |
| Crabominable-Mega | Ice Hammer | Sneasler | 63% | 93% | known |
| Metagross-Mega | Ice Punch | Garchomp | n/a | 100% | tech |
| Raichu-Mega-Y | Zap Cannon | Basculegion | n/a | 100% | tech |
| Talonflame | Overheat | Kingambit | n/a | 96% | tech |
| Sylveon | Hyper Voice | Kingambit | 44% | 69% | known |
| Slowking-Galar | Psychic | Venusaur-Mega | 56% | 81% | known |
| Bellibolt | Discharge | Venusaur-Mega | n/a | 40% | tech |
| Kingambit | Iron Head | Garchomp | 47% | 66% | known |
| Froslass-Mega | Blizzard | Sneasler | 52% | 70% | known |
| Annihilape | Rage Fist | Garchomp | 27% | 44% | known |
| Incineroar | Throat Chop | Basculegion | 59% | 75% | known |

### Offensive mis-model
*Our outgoing damage vs actual (|error| > slop). Mode = over/under.*

| Attacker | Move | vs Target | Predicted | Actual | Mode |
|---|---|---|--:|--:|---|
| Garchomp | Poison Jab | Whimsicott | 100% | 29% | over |
| Kingambit | Iron Head | Altaria | 80% | 22% | over |
| Staraptor | Brave Bird | Gardevoir | 100% | 43% | over |
| Garchomp | Dragon Claw | Staraptor-Mega | 81% | 32% | over |
| Kingambit | Kowtow Cleave | Corviknight | 82% | 35% | over |
| Kingambit | Kowtow Cleave | Corviknight | 71% | 30% | over |
| Sneasler | Close Combat | Archaludon | 62% | 26% | over |
| Sneasler | Dire Claw | Grimmsnarl | 43% | 78% | under |
| Staraptor-Mega | Brave Bird | Sinistcha | 67% | 32% | over |
| Staraptor | Brave Bird | Staraptor | 90% | 55% | over |
| Sneasler | Close Combat | Scrafty | 60% | 93% | under |
| Sneasler | Close Combat | Scrafty | 59% | 92% | under |
| Garchomp | Dragon Claw | Staraptor-Mega | 68% | 37% | over |
| Basculegion | Wave Crash | Incineroar | 75% | 44% | over |
| Kingambit | Iron Head | Altaria | 50% | 20% | over |
| Kingambit | Kowtow Cleave | Pelipper | 66% | 37% | over |
| Basculegion | Psychic Fangs | Venusaur | 56% | 30% | over |
| Sneasler | Rock Tomb | Froslass-Mega | 59% | 37% | over |
| Garchomp | Poison Jab | Grimmsnarl | 63% | 83% | under |
| Sneasler | Close Combat | Kingambit | 80% | 99% | under |
| Kingambit | Kowtow Cleave | Sceptile | 51% | 34% | over |
| Garchomp | Poison Jab | Whimsicott | 100% | 83% | over |
| Garchomp | Stomping Tantrum | Archaludon | 76% | 60% | over |
| Basculegion | Wave Crash | Sylveon | 77% | 93% | under |
| Basculegion | Wave Crash | Sableye | 100% | 85% | over |

### Turn order
*Predicted resolution position (1 = fastest of 4) vs actual, over full 4-move turns. Protect/Endure jumping ahead is excluded.*

| Result | Count | Share |
|---|--:|--:|
| exact | 44 | 57% |
| off by 1 | 30 | 39% |
| off by 2+ | 3 | 4% |

Off-by-2+ misreads (board state at the misread turn; *Predicted* = where we expected the flagged mon, *Actual* = the real resolution order):

| Turn | my[a] | my[b] | opp[a] | opp[b] | TR | TW | Predicted | Actual order |
|--:|---|---|---|---|:-:|:-:|---|---|
| 3 | Garchomp | Sneasler | Sinistcha | Annihilape | - | - | my[b] 1/4 | opp[a] > my[a] > my[b] > opp[b] |
| 4 | Sneasler | Garchomp | Staraptor | Sinistcha | - | - | my[b] 3/4 | my[b] > my[a] > opp[a] > opp[b] |
| 2 | Garchomp | Sneasler | Sableye | Archaludon | - | - | my[b] 1/4 | opp[a] > my[a] > my[b] > opp[b] |
