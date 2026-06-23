# Team Report - meta-team v5

**Games:** 26 | **Win rate:** 13-13 (50%) | **Engine:** v0.22.0

*Source: `Battle Data/0.22.0/meta-team/v5/*.json`*

## Team

```
Raichu @ Raichunite Y
Ability: Static
Level: 50
EVs: 2 HP / 32 SpA / 32 Spe
Modest Nature
- Zap Cannon
- Focus Blast
- Grass Knot
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

Arcanine-Hisui @ Focus Sash
Ability: Rock Head
EVs: 2 HP / 32 Atk / 32 Spe
Jolly Nature
- Flare Blitz
- Head Smash
- Iron Head
- Protect

Basculegion-M (M) @ Mystic Water
Ability: Adaptability
Level: 50
EVs: 32 HP / 17 Atk / 17 Def
Adamant Nature
- Wave Crash
- Last Respects
- Psychic Fangs
- Protect

Metagross @ Metagrossite
Ability: Clear Body
EVs: 14 HP / 27 Atk / 25 Spe
Jolly Nature
- Protect
- Body Press
- Psychic Fangs
- Iron Head

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

Sorted by net (KOs - faints). KDR = KOs/faints (∞ = no faints). *WR (brought)* is subject to selection bias.

| Mon | Bring | Lead | WR (brought) | KOs | Faints | Net | KDR |
|---|--:|--:|--:|--:|--:|--:|--:|
| Garchomp | 88% | 62% | 52% | 18 | 12 | +6 | 1.50 |
| Kingambit | 92% | 42% | 50% | 17 | 12 | +5 | 1.42 |
| Basculegion | 46% | 27% | 42% | 11 | 6 | +5 | 1.83 |
| Metagross | 73% | 46% | 47% | 10 | 9 | +1 | 1.11 |
| Raichu | 31% | 19% | 75% | 5 | 6 | -1 | 0.83 |
| Arcanine-Hisui | 69% | 4% | 44% | 10 | 13 | -3 | 0.77 |

## Move usage

Times each move was chosen (excludes switches). **Lowest** = swap candidate.

| Mon | Moves (chosen count) | Lowest |
|---|---|---|
| Kingambit | Kowtow Cleave 34, Iron Head 18, Low Kick 16, Protect 5 | **Protect 5** |
| Garchomp | Dragon Claw 20, Stomping Tantrum 19, Poison Jab 10, Rock Tomb 4 | **Rock Tomb 4** |
| Metagross | Psychic Fangs 26, Iron Head 20, Body Press 8, Protect 1 | **Protect 1** |
| Arcanine-Hisui | Head Smash 25, Flare Blitz 8, Protect 4 | **Protect 4** |
| Basculegion | Wave Crash 21, Psychic Fangs 7, Last Respects 6, Protect 3 | **Protect 3** |
| Raichu | Zap Cannon 7, Focus Blast 5, Grass Knot 1, Protect 1 | **Grass Knot 1** |

## Game length

| Turns | Record | Win rate |
|---|---|--:|
| 1-3 | 4-0 | 100% |
| 4-6 | 6-7 | 46% |
| 7-9 | 2-5 | 29% |
| 10+ | 1-1 | 50% |

## Opponent archetypes

*W/L when the opponent established each condition. A game can count in several (e.g. Tailwind + Sun); `None` = no TR/TW/weather.*

| Archetype | Record | Win rate | Games |
|---|---|--:|--:|
| Trick Room | 1-1 | 50% | 2 |
| Tailwind | 3-5 | 38% | 8 |
| Rain | 3-1 | 75% | 4 |
| None | 8-6 | 57% | 14 |

## Opponent megas

*W/L vs the opponent mega that appeared (one mega-evolves per battle); `None (no mega)` = opponent never mega-evolved.*

| Opponent mega | Record | Win rate | Games |
|---|---|--:|--:|
| Staraptor-Mega | 0-3 | 0% | 3 |
| Metagross-Mega | 0-2 | 0% | 2 |
| Altaria-Mega | 1-0 | 100% | 1 |
| Blaziken-Mega | 0-1 | 0% | 1 |
| Dragonite-Mega | 0-1 | 0% | 1 |
| Eelektross-Mega | 1-0 | 100% | 1 |
| Gengar-Mega | 1-0 | 100% | 1 |
| Golurk-Mega | 1-0 | 100% | 1 |
| Meganium-Mega | 0-1 | 0% | 1 |
| Pyroar-Mega | 0-1 | 0% | 1 |
| Raichu-Mega-Y | 1-0 | 100% | 1 |
| Swampert-Mega | 1-0 | 100% | 1 |
| None (no mega) | 7-4 | 64% | 11 |

## Prediction accuracy

*Each case is a **gap** (actionable) or **accepted** (explained, with reason). Goal: gaps to zero; accepted rows stay so the checks keep running.*

**Offense** 9 (9 gaps) | **Defense** 3 (2 gaps) | **Turn order** 16 misreads (1 gaps) | **Immunity** 0 (0 gaps)

### Defensive mis-model
*Incoming hits >slop above prediction (crits/misses excluded).*

| Attacker | Move | vs Defender | Predicted | Actual | Disposition |
|---|---|---|--:|--:|---|
| Primarina | Hyper Voice | Metagross-Mega | 12% | 32% | gap<!-- 2637853132:t4 --> |
| Hydrapple | Earth Power | Kingambit | 66% | 82% | gap<!-- 2637892017:t2 --> |
| Pyroar-Mega | Scorching Sands | Arcanine-Hisui | n/a | 95% | accepted: unassessed move (off-meta / below usage cutoff)<!-- 7gucltwd08kwqswr72btp7seob2pj3ypw:t6 --> |

### Offensive mis-model
*Our outgoing damage vs actual (|error| > slop). Dir = over/under.*

| Attacker | Move | vs Target | Predicted | Actual | Dir | Disposition |
|---|---|---|--:|--:|:-:|---|
| Kingambit | Low Kick | Meowscarada | 75% | 20% | over | gap<!-- 2637851861:t4 --> |
| Basculegion | Last Respects | Dragonite-Mega | 45% | 80% | under | gap<!-- 2637898268:t7 --> |
| Kingambit | Iron Head | Staraptor-Mega | 61% | 27% | over | gap<!-- otc0c0wgr8de24a3mqtwjkqdvev23w6pw:t3 --> |
| Metagross | Iron Head | Grimmsnarl | 57% | 87% | under | gap<!-- qkawn6uwnem2pen0kr9t4lsmgg0l7h7pw:t3 --> |
| Metagross-Mega | Psychic Fangs | Sinistcha-Masterpiece | 41% | 66% | under | gap<!-- n3o8l39wl5tn59x00jg87fn7x0034rppw:t2 --> |
| Kingambit | Iron Head | Grimmsnarl | 65% | 87% | under | gap<!-- qkawn6uwnem2pen0kr9t4lsmgg0l7h7pw:t3 --> |
| Metagross-Mega | Psychic Fangs | Garchomp | 48% | 68% | under | gap<!-- yu762x9a0k80943ynmgor1ux4w1td94pw:t3 --> |
| Kingambit | Kowtow Cleave | Milotic | 44% | 27% | over | gap<!-- p7exsdntlrnokvtu2t5aldbp6q25qtkpw:t11 --> |
| Garchomp | Rock Tomb | Pelipper | 62% | 45% | over | gap<!-- 2637905476:t1 --> |

### Turn order
*Predicted resolution position (1 = fastest of 4) vs actual, over full 4-move turns. Protect/Endure jumping ahead is excluded.*

| Result | Count | Share |
|---|--:|--:|
| exact | 13 | 45% |
| off by 1 | 12 | 41% |
| off by 2+ | 4 | 14% |

Off-by-2+ misreads (board state at the misread turn; *Predicted* = where we expected the flagged mon, *Actual* = the real resolution order):

| Turn | my[a] | my[b] | opp[a] | opp[b] | TR | TW | Predicted | Actual order | Disposition |
|--:|---|---|---|---|:-:|:-:|---|---|---|
| 2 | Kingambit | Raichu | Kingambit | Golurk | - | - | my[a] 2/4 | my[b] > opp[b] > opp[a] > my[a] | gap<!-- 2637851861:t2 --> |
| 3 | Kingambit | Metagross | Toxapex | Grimmsnarl | - | - | my[b] 1/4 | opp[b] > my[b] > my[a] > opp[a] | accepted: priority (higher-priority move resolved ahead)<!-- qkawn6uwnem2pen0kr9t4lsmgg0l7h7pw:t3 --> |
| 1 | Garchomp | Metagross | Whimsicott | Staraptor | - | - | my[a] 1/4 | opp[a] > opp[b] > my[a] > my[b] | accepted: priority (higher-priority move resolved ahead)<!-- otc0c0wgr8de24a3mqtwjkqdvev23w6pw:t1 --> |
| 2 | Garchomp | Arcanine-Hisui | Rotom-Heat | Mamoswine | - | - | my[a] 1/4 | opp[b] > opp[a] > my[a] > my[b] | accepted: priority (higher-priority move resolved ahead)<!-- 2637895499:t2 --> |
