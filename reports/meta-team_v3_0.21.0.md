# Team Report - meta-team v3

**Games:** 51 | **Win rate:** 26-25 (51%) | **Engine:** v0.21.0

*Source: `Battle Data/0.21.0/meta-team/v3/*.json`*

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

Gholdengo @ Focus Sash
Ability: Good as Gold
Level: 50
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
- Flash Cannon
- Shadow Ball
- Thunderbolt
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
| Gholdengo | 84% | 33% | 53% | 35 | 5 | +30 |
| Garchomp | 98% | 69% | 52% | 32 | 6 | +26 |
| Venusaur | 82% | 37% | 50% | 30 | 5 | +25 |
| Basculegion | 45% | 25% | 43% | 21 | 0 | +21 |
| Kingambit | 75% | 29% | 53% | 18 | 9 | +9 |
| Staraptor | 16% | 6% | 50% | 3 | 1 | +2 |

## Move usage

Times each move was chosen (excludes switches). **Lowest** = swap candidate.

| Mon | Moves (chosen count) | Lowest |
|---|---|---|
| Garchomp | Stomping Tantrum 53, Dragon Claw 35, Poison Jab 31, Rock Tomb 16 | **Rock Tomb 16** |
| Gholdengo | Shadow Ball 49, Flash Cannon 36, Thunderbolt 20, Protect 19 | **Protect 19** |
| Venusaur | Sludge Bomb 41, Earth Power 37, Giga Drain 19, Protect 10 | **Protect 10** |
| Kingambit | Kowtow Cleave 50, Iron Head 19, Low Kick 12, Protect 9 | **Protect 9** |
| Basculegion | Wave Crash 37, Last Respects 19, Psychic Fangs 6, Protect 5 | **Protect 5** |
| Staraptor | Brave Bird 6, Close Combat 5, Protect 1 | **Protect 1** |

## Game length

| Turns | Record | Win rate |
|---|---|--:|
| 1-3 | 1-0 | 100% |
| 4-6 | 19-16 | 54% |
| 7-9 | 6-7 | 46% |
| 10+ | 0-2 | 0% |

## Opponent archetypes

*W/L when the opponent established each condition. A game can count in several (e.g. Tailwind + Sun); `None` = no TR/TW/weather.*

| Archetype | Record | Win rate | Games |
|---|---|--:|--:|
| Trick Room | 6-6 | 50% | 12 |
| Tailwind | 6-6 | 50% | 12 |
| Rain | 5-2 | 71% | 7 |
| Sun | 2-5 | 29% | 7 |
| None | 12-10 | 55% | 22 |

## Opponent megas

*W/L vs the opponent mega that appeared (one mega-evolves per battle); `None (no mega)` = opponent never mega-evolved.*

| Opponent mega | Record | Win rate | Games |
|---|---|--:|--:|
| Staraptor-Mega | 0-6 | 0% | 6 |
| Mawile-Mega | 2-3 | 40% | 5 |
| Charizard-Mega-Y | 1-3 | 25% | 4 |
| Raichu-Mega-Y | 3-1 | 75% | 4 |
| Delphox-Mega | 2-1 | 67% | 3 |
| Swampert-Mega | 1-2 | 33% | 3 |
| Camerupt-Mega | 1-1 | 50% | 2 |
| Blastoise-Mega | 1-0 | 100% | 1 |
| Blaziken-Mega | 1-0 | 100% | 1 |
| Crabominable-Mega | 1-0 | 100% | 1 |
| Dragalge-Mega | 0-1 | 0% | 1 |
| Eelektross-Mega | 0-1 | 0% | 1 |
| Falinks-Mega | 0-1 | 0% | 1 |
| Froslass-Mega | 0-1 | 0% | 1 |
| Gengar-Mega | 1-0 | 100% | 1 |
| Malamar-Mega | 0-1 | 0% | 1 |
| Metagross-Mega | 1-0 | 100% | 1 |
| Pyroar-Mega | 0-1 | 0% | 1 |
| Raichu-Mega-X | 1-0 | 100% | 1 |
| Venusaur-Mega | 0-1 | 0% | 1 |
| None (no mega) | 10-2 | 83% | 12 |

## Prediction accuracy

*Each case is a **gap** (actionable) or **accepted** (explained, with reason). Goal: gaps to zero; accepted rows stay so the checks keep running.*

**Offense** 25 (25 gaps) | **Defense** 11 (6 gaps) | **Turn order** 35 misreads (0 gaps) | **Immunity** 0 (0 gaps)

### Defensive mis-model
*Incoming hits >slop above prediction (crits/misses excluded).*

| Attacker | Move | vs Defender | Predicted | Actual | Disposition |
|---|---|---|--:|--:|---|
| Annihilape | Rage Fist | Venusaur-Mega | 21% | 85% | gap<!-- 2636096126:t1 --> |
| Primarina | Hyper Voice | Kingambit | 13% | 47% | gap<!-- 2636106712:t4 --> |
| Farigiraf | Psychic | Staraptor-Mega | 51% | 78% | gap<!-- eocion8emm7sdjch5543m6i9xd213kopw:t4 --> |
| Slowking | Muddy Water | Garchomp | 51% | 72% | gap<!-- 2636142190:t5 --> |
| Sinistcha | Matcha Gotcha | Basculegion | 49% | 69% | gap<!-- rxn2pdjhaqcnii7on8v6lhuf9a78u0vpw:t3 --> |
| Garchomp | Earthquake | Garchomp | 39% | 55% | gap<!-- q2ih4j02bu254y5ardym801vvc08hatpw:t2 --> |
| Volcarona | Giga Drain | Basculegion | n/a | 74% | accepted: unassessed move (off-meta / below usage cutoff)<!-- 8ndttwjuigdnam6uqpqveiwq2wkf7fppw:t5 --> |
| Musharna | Shadow Ball | Gholdengo | n/a | 63% | accepted: unassessed move (off-meta / below usage cutoff)<!-- 2636145009:t2 --> |
| Rampardos | Ice Beam | Garchomp | n/a | 100% | accepted: unassessed move (off-meta / below usage cutoff)<!-- 2636145009:t2 --> |
| Staraptor | Final Gambit | Garchomp | n/a | 100% | accepted: unassessed move (off-meta / below usage cutoff)<!-- 2636101084:t1 --> |
| Sableye | Foul Play | Venusaur-Mega | n/a | 22% | accepted: unassessed move (off-meta / below usage cutoff)<!-- 2636127845:t5 --> |

### Offensive mis-model
*Our outgoing damage vs actual (|error| > slop). Dir = over/under.*

| Attacker | Move | vs Target | Predicted | Actual | Dir | Disposition |
|---|---|---|--:|--:|:-:|---|
| Gholdengo | Thunderbolt | Staraptor-Mega | 78% | 15% | over | gap<!-- 2636122437:t3 --> |
| Gholdengo | Thunderbolt | Staraptor-Mega | 77% | 15% | over | gap<!-- 1bmgkoj1u6d6mmh4jgnjw2pcse4a713pw:t5 --> |
| Kingambit | Kowtow Cleave | Farigiraf | 100% | 43% | over | gap<!-- 2636137084:t1 --> |
| Gholdengo | Shadow Ball | Sinistcha-Masterpiece | 81% | 30% | over | gap<!-- 0jll745op03jp7yfuavtkx2xcg5jdh5pw:t1 --> |
| Kingambit | Kowtow Cleave | Farigiraf | 100% | 50% | over | gap<!-- eocion8emm7sdjch5543m6i9xd213kopw:t1 --> |
| Kingambit | Kowtow Cleave | Farigiraf | 100% | 50% | over | gap<!-- 2636121650:t1 --> |
| Venusaur-Mega | Sludge Bomb | Staraptor-Mega | 80% | 32% | over | gap<!-- j32qy5bx1ypkjtbe3blolf7pw10nbflpw:t5 --> |
| Garchomp | Dragon Claw | Dragapult | 100% | 63% | over | gap<!-- wy0gsk8jev90cv0xn9if1p9widfqsr2pw:t1 --> |
| Garchomp | Poison Jab | Whimsicott | 100% | 66% | over | gap<!-- 2636099479:t1 --> |
| Kingambit | Kowtow Cleave | Froslass | 100% | 69% | over | gap<!-- rxn2pdjhaqcnii7on8v6lhuf9a78u0vpw:t1 --> |
| Garchomp | Poison Jab | Whimsicott | 100% | 70% | over | gap<!-- 2636092305:t1 --> |
| Gholdengo | Shadow Ball | Annihilape | 90% | 61% | over | gap<!-- 2636153133:t1 --> |
| Garchomp | Dragon Claw | Staraptor | 35% | 62% | under | gap<!-- 2636131021:t1 --> |
| Basculegion | Wave Crash | Crabominable-Mega | 28% | 54% | under | gap<!-- 2636137084:t7 --> |
| Garchomp | Poison Jab | Rotom-Wash | 41% | 16% | over | gap<!-- 2636099479:t3 --> |
| Kingambit | Kowtow Cleave | Pelipper | 61% | 36% | over | gap<!-- wy0gsk8jev90cv0xn9if1p9widfqsr2pw:t4 --> |
| Garchomp | Dragon Claw | Sinistcha-Masterpiece | 58% | 33% | over | gap<!-- 2636148433:t7 --> |
| Kingambit | Low Kick | Kingambit | 59% | 83% | under | gap<!-- 2636094509:t5 --> |
| Kingambit | Kowtow Cleave | Farigiraf | 100% | 77% | over | gap<!-- 2636093539:t3 --> |
| Garchomp | Poison Jab | Grimmsnarl | 63% | 42% | over | gap<!-- 2636121650:t1 --> |
| Garchomp | Stomping Tantrum | Vanilluxe | 60% | 41% | over | gap<!-- 2636126957:t3 --> |
| Gholdengo | Flash Cannon | Whimsicott | 100% | 81% | over | gap<!-- jtfyaed153cafytf7l8uxb8k7o0rygvpw:t3 --> |
| Basculegion | Wave Crash | Crabominable-Mega | 28% | 46% | under | gap<!-- 2636137084:t8 --> |
| Basculegion | Wave Crash | Mawile | 63% | 80% | under | gap<!-- xvr030n8x2f5h7rab5sqgheb2hl7uqnpw:t1 --> |
| Gholdengo | Flash Cannon | Farigiraf | 45% | 30% | over | gap<!-- 2636129704:t1 --> |

### Turn order
*Predicted resolution position (1 = fastest of 4) vs actual, over full 4-move turns. Protect/Endure jumping ahead is excluded.*

| Result | Count | Share |
|---|--:|--:|
| exact | 54 | 61% |
| off by 1 | 31 | 35% |
| off by 2+ | 4 | 4% |

Off-by-2+ misreads (board state at the misread turn; *Predicted* = where we expected the flagged mon, *Actual* = the real resolution order):

| Turn | my[a] | my[b] | opp[a] | opp[b] | TR | TW | Predicted | Actual order | Disposition |
|--:|---|---|---|---|:-:|:-:|---|---|---|
| 1 | Basculegion | Garchomp | Rotom-Wash | Whimsicott | - | - | my[b] 1/4 | opp[b] > opp[a] > my[b] > my[a] | accepted: priority (higher-priority move resolved ahead)<!-- 2636099479:t1 --> |
| 1 | Venusaur | Garchomp | Whimsicott | Glimmora | - | - | my[b] 1/4 | opp[a] > opp[b] > my[b] > my[a] | accepted: priority (higher-priority move resolved ahead)<!-- 2636107949:t1 --> |
| 1 | Garchomp | Gholdengo | Grimmsnarl | Annihilape | - | - | my[b] 2/4 | opp[a] > my[a] > opp[b] > my[b] | accepted: priority (higher-priority move resolved ahead)<!-- 2636153133:t1 --> |
| 2 | Garchomp | Gholdengo | Grimmsnarl | Annihilape | - | - | my[b] 2/4 | opp[a] > my[a] > opp[b] > my[b] | accepted: priority (higher-priority move resolved ahead)<!-- 2636153133:t2 --> |
