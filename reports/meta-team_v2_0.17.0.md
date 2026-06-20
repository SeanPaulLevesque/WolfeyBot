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

**Offense** 86% (153/178 within +/-15%, 25 mis-models) | **Turn order** 57% exact (+/-1 39%, off-by-2+ 4%) | **Defense** 17 under-predictions (10 model gaps, 7 tech) | **Immunity** 3 fired into immune target

### Defensive under-predictions
*Took >slop more than predicted (crits/misses excluded). `known` = assessed move under-rated; `tech` = move never assessed.*

| Attacker | Move | vs Defender | Predicted | Actual | Delta | Kind |
|---|---|---|--:|--:|--:|---|
| Aerodactyl-Mega | Ice Fang | Garchomp | n/a | 100% | +63% | tech |
| Floette-Mega | Dazzling Gleam | Basculegion | n/a | 55% | +55% | tech |
| Annihilape | Rage Fist | Basculegion | 50% | 95% | +45% | known |
| Staraptor-Mega | Close Combat | Garchomp | 66% | 100% | +34% | known |
| Staraptor-Mega | Close Combat | Garchomp | 66% | 100% | +34% | known |
| Raichu-Mega-X | Volt Tackle | Sneasler | n/a | 87% | +31% | tech |
| Crabominable-Mega | Ice Hammer | Sneasler | 63% | 93% | +30% | known |
| Metagross-Mega | Ice Punch | Garchomp | n/a | 100% | +28% | tech |
| Raichu-Mega-Y | Zap Cannon | Basculegion | n/a | 100% | +26% | tech |
| Talonflame | Overheat | Kingambit | n/a | 96% | +26% | tech |
| Sylveon | Hyper Voice | Kingambit | 44% | 69% | +25% | known |
| Slowking-Galar | Psychic | Venusaur-Mega | 56% | 81% | +25% | known |
| Bellibolt | Discharge | Venusaur-Mega | n/a | 40% | +23% | tech |
| Kingambit | Iron Head | Garchomp | 47% | 66% | +19% | known |
| Froslass-Mega | Blizzard | Sneasler | 52% | 70% | +18% | known |
| Annihilape | Rage Fist | Garchomp | 27% | 44% | +17% | known |
| Incineroar | Throat Chop | Basculegion | 59% | 75% | +16% | known |

### Offense mis-models
*Our predicted damage vs actual (|error| > slop).*

| Move | vs Target | Predicted | Actual | Error |
|---|---|--:|--:|---|
| Poison Jab | Whimsicott | 100% | 29% | over 71% |
| Iron Head | Altaria | 80% | 22% | over 58% |
| Brave Bird | Gardevoir | 100% | 43% | over 57% |
| Dragon Claw | Staraptor-Mega | 81% | 32% | over 49% |
| Kowtow Cleave | Corviknight | 82% | 35% | over 47% |
| Kowtow Cleave | Corviknight | 71% | 30% | over 41% |
| Close Combat | Archaludon | 62% | 26% | over 36% |
| Dire Claw | Grimmsnarl | 43% | 78% | under 35% |
| Brave Bird | Sinistcha | 67% | 32% | over 35% |
| Brave Bird | Staraptor | 90% | 55% | over 35% |
| Close Combat | Scrafty | 60% | 93% | under 33% |
| Close Combat | Scrafty | 59% | 92% | under 33% |
| Dragon Claw | Staraptor-Mega | 68% | 37% | over 31% |
| Wave Crash | Incineroar | 75% | 44% | over 31% |
| Iron Head | Altaria | 50% | 20% | over 30% |
| Kowtow Cleave | Pelipper | 66% | 37% | over 29% |
| Psychic Fangs | Venusaur | 56% | 30% | over 26% |
| Rock Tomb | Froslass-Mega | 59% | 37% | over 22% |
| Poison Jab | Grimmsnarl | 63% | 83% | under 20% |
| Close Combat | Kingambit | 80% | 99% | under 19% |
| Kowtow Cleave | Sceptile | 51% | 34% | over 17% |
| Poison Jab | Whimsicott | 100% | 83% | over 17% |
| Stomping Tantrum | Archaludon | 76% | 60% | over 16% |
| Wave Crash | Sylveon | 77% | 93% | under 16% |
| Wave Crash | Sableye | 100% | 85% | over 15% |

### Immunity gaps
*Chose a move expecting damage, but the target was immune.*

| Move | vs Target | Why |
|---|---|---|
| Stomping Tantrum | Pelipper | type immunity |
| Stomping Tantrum | Pelipper | type immunity |
| Stomping Tantrum | Pelipper | type immunity |
