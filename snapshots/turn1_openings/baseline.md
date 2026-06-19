# Turn 1 First-Turn Decision Summary

Engine v0.14.0 | Turn 1 opening, 100% HP, no field effects, no revealed moves

> **Joint selection.** Each slot's `(move, target)` candidates are scored
> independently (phase 1); `DecisionEngine.coordinate` then picks the
> highest-value **pair** of actions (phase 2).
> All opponent HP treated as percentage (engine uses typical-spread stats for damage calcs).
> Mega evolution is resolved at turn start — the designated mega uses mega stats/ability.
>
> The phase-2 **joint adjusters** are the only cross-slot effects: *doubling* (both attack the same target → ×0.40–0.70, or ×0.05 overkill when one slot already confirms the OHKO, so the pair that spreads wins); *coordination* (a gratuitous lone Protect beside an attacking partner → ×0.5, favouring double-attack); *fake-out* (the slot absorbing a Fake Out frees its partner); and *switch-collision* (both switching to the same mon → ×0). These cells reflect actual in-game behaviour.

---

## 1. My Lead: **Aerodactyl** [A]  +  **Venusaur** [B] *(mega: Aerodactyl)*
Bench: Kingambit, Sneasler, Basculegion, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Venusaur [B] |
|---|---|---|---|---|
| 1.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `28.48` | Switch → Basculegion `6.78` |
| 1.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `37.78` | Switch → Kingambit `3.20` |
| 1.3 | Incineroar | Garchomp | Ice Fang → Garchomp `2.90` | Switch → Basculegion `6.10` |
| 1.4 | Incineroar | Farigiraf | Rock Tomb → Incineroar `4.91` | Switch → Basculegion `6.03` |
| 1.5 | Incineroar | Kingambit | Protect → ? `5.00` | Protect → ? `5.00` |
| 1.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `4.74` | Switch → Basculegion `9.44` |
| 1.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `56.96` | Sludge Bomb → Farigiraf `3.91` |
| 1.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `11.58` | Sludge Bomb → Farigiraf `3.91` |
| 1.9 | Whimsicott | Garchomp | Dual Wingbeat → Whimsicott `56.67` | Giga Drain → Garchomp `2.00` |
| 1.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `75.56` | Earth Power → Kingambit `3.42` |
| 1.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `21.36` | Switch → Basculegion `1.70` |
| 1.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `28.48` | Earth Power → Kingambit `2.28` |
| 1.13 | Aerodactyl | Garchomp | Rock Tomb → Aerodactyl `6.32` | Switch → Basculegion `2.36` |
| 1.14 | Lopunny | Garchomp | Dual Wingbeat → Lopunny `10.83` | Giga Drain → Garchomp `1.33` |
| 1.15 | Weavile | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 1.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `56.39` | Switch → Basculegion `8.57` |
| 1.17 | Charizard | Incineroar | Rock Tomb → Charizard `26.31` | Protect → ? `7.50` |
| 1.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `5.79` | Giga Drain → Rotom-Wash `2.71` |
| 1.19 | Glimmora | Incineroar | Protect → ? `7.50` | Earth Power → Glimmora `11.97` |
| 1.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `10.57` | Switch → Basculegion `3.35` |

---

## 2. My Lead: **Aerodactyl** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Kingambit, Sneasler, Basculegion, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Venusaur [B] |
|---|---|---|---|---|
| 2.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `18.27` | Earth Power → Incineroar `2.10` |
| 2.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `24.35` | Earth Power → Incineroar `3.15` |
| 2.3 | Incineroar | Garchomp | Ice Fang → Garchomp `2.53` | Earth Power → Incineroar `2.10` |
| 2.4 | Incineroar | Farigiraf | Rock Tomb → Incineroar `4.33` | Sludge Bomb → Farigiraf `6.55` |
| 2.5 | Incineroar | Kingambit | Protect → ? `5.00` | Protect → ? `2.00` |
| 2.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `4.04` | Earth Power → Incineroar `3.15` |
| 2.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `36.54` | Sludge Bomb → Farigiraf `4.37` |
| 2.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `10.11` | Sludge Bomb → Farigiraf `4.37` |
| 2.9 | Whimsicott | Garchomp | Dual Wingbeat → Whimsicott `32.46` | Giga Drain → Garchomp `2.24` |
| 2.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `48.69` | Earth Power → Kingambit `3.89` |
| 2.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `12.18` | Switch → Basculegion `1.60` |
| 2.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `18.27` | Earth Power → Kingambit `2.60` |
| 2.13 | Aerodactyl | Garchomp | Ice Fang → Garchomp `5.05` | Giga Drain → Aerodactyl `2.74` |
| 2.14 | Lopunny | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 2.15 | Weavile | Garchomp | Switch → Kingambit `5.41` | Protect → ? `2.00` |
| 2.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `47.61` | Giga Drain → Garchomp `2.24` |
| 2.17 | Charizard | Incineroar | Rock Tomb → Charizard `22.55` | Earth Power → Incineroar `4.21` |
| 2.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `5.05` | Giga Drain → Rotom-Wash `3.05` |
| 2.19 | Glimmora | Incineroar | Switch → Garchomp `7.67` | Earth Power → Glimmora `13.80` |
| 2.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `9.16` | Switch → Kingambit `3.20` |

---

## 3. My Lead: **Garchomp** [A]  +  **Kingambit** [B]
Bench: Aerodactyl, Sneasler, Basculegion, Venusaur

| # | Opp [A] | Opp [B] | Garchomp [A] | Kingambit [B] |
|---|---|---|---|---|
| 3.1 | Incineroar | Sneasler | Stomping Tantrum → Sneasler `28.48` | Low Kick → Incineroar `1.82` |
| 3.2 | Incineroar | Whimsicott | Poison Jab → Whimsicott `10.53` | Iron Head → Whimsicott `3.38` |
| 3.3 | Incineroar | Garchomp | Dragon Claw → Garchomp `2.84` | Low Kick → Incineroar `1.82` |
| 3.4 | Incineroar | Farigiraf | Stomping Tantrum → Incineroar `6.26` | Kowtow Cleave → Farigiraf `8.25` |
| 3.5 | Incineroar | Kingambit | Stomping Tantrum → Incineroar `3.13` | Low Kick → Kingambit `2.56` |
| 3.6 | Incineroar | Aerodactyl | Stomping Tantrum → Incineroar `4.69` | Iron Head → Aerodactyl `6.55` |
| 3.7 | Farigiraf | Sneasler | Stomping Tantrum → Sneasler `56.96` | Kowtow Cleave → Farigiraf `8.25` |
| 3.8 | Farigiraf | Garchomp | Dragon Claw → Garchomp `11.37` | Kowtow Cleave → Farigiraf `8.25` |
| 3.9 | Whimsicott | Garchomp | Poison Jab → Whimsicott `15.80` | Iron Head → Whimsicott `3.38` |
| 3.10 | Whimsicott | Kingambit | Poison Jab → Whimsicott `21.07` | Iron Head → Whimsicott `4.51` |
| 3.11 | Sneasler | Garchomp | Stomping Tantrum → Sneasler `21.36` | Kowtow Cleave → Garchomp `1.71` |
| 3.12 | Sneasler | Kingambit | Stomping Tantrum → Sneasler `28.48` | Low Kick → Kingambit `2.56` |
| 3.13 | Aerodactyl | Garchomp | Dragon Claw → Garchomp `8.53` | Iron Head → Aerodactyl `6.55` |
| 3.14 | Lopunny | Garchomp | Dragon Claw → Garchomp `2.84` | Switch → Basculegion `4.33` |
| 3.15 | Weavile | Garchomp | Dragon Claw → Garchomp `2.84` | Low Kick → Weavile `4.67` |
| 3.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `62.02` | Kowtow Cleave → Garchomp `2.57` |
| 3.17 | Charizard | Incineroar | Rock Tomb → Charizard `25.48` | Protect → ? `7.50` |
| 3.18 | Rotom-Wash | Garchomp | Dragon Claw → Garchomp `5.69` | Kowtow Cleave → Rotom-Wash `2.15` |
| 3.19 | Glimmora | Incineroar | Stomping Tantrum → Glimmora `35.28` | Low Kick → Incineroar `1.82` |
| 3.20 | Pelipper | Dragonite | Dragon Claw → Dragonite `6.18` | Kowtow Cleave → Pelipper `3.14` |

---

## 4. My Lead: **Aerodactyl** [A]  +  **Sneasler** [B] *(mega: Aerodactyl)*
Bench: Kingambit, Basculegion, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Sneasler [B] |
|---|---|---|---|---|
| 4.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `28.48` | Close Combat → Incineroar `3.77` |
| 4.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `37.78` | Close Combat → Incineroar `5.65` |
| 4.3 | Incineroar | Garchomp | Ice Fang → Garchomp `2.90` | Switch → Basculegion `4.37` |
| 4.4 | Incineroar | Farigiraf | Dual Wingbeat → Farigiraf `4.11` | Close Combat → Incineroar `11.31` |
| 4.5 | Incineroar | Kingambit | Rock Tomb → Incineroar `2.46` | Close Combat → Kingambit `4.97` |
| 4.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `4.74` | Close Combat → Incineroar `5.65` |
| 4.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `56.96` | Switch → Basculegion `7.32` |
| 4.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `11.58` | Close Combat → Farigiraf `4.85` |
| 4.9 | Whimsicott | Garchomp | Dual Wingbeat → Whimsicott `56.67` | Switch → Venusaur `4.67` |
| 4.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `75.56` | Close Combat → Kingambit `4.97` |
| 4.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `21.36` | Switch → Basculegion `7.34` |
| 4.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `28.48` | Close Combat → Kingambit `3.32` |
| 4.13 | Aerodactyl | Garchomp | Rock Tomb → Aerodactyl `6.32` | Switch → Basculegion `8.20` |
| 4.14 | Lopunny | Garchomp | Ice Fang → Garchomp `1.93` | Close Combat → Lopunny `19.71` |
| 4.15 | Weavile | Garchomp | Ice Fang → Garchomp `1.93` | Close Combat → Weavile `10.09` |
| 4.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `56.39` | Protect → ? `7.50` |
| 4.17 | Charizard | Incineroar | Rock Tomb → Charizard `35.08` | Close Combat → Incineroar `5.65` |
| 4.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `5.79` | Switch → Garchomp `3.90` |
| 4.19 | Glimmora | Incineroar | Switch → Garchomp `7.41` | Close Combat → Incineroar `2.83` |
| 4.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `10.57` | Switch → Basculegion `4.00` |

---

## 5. My Lead: **Garchomp** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Aerodactyl, Kingambit, Sneasler, Basculegion

| # | Opp [A] | Opp [B] | Garchomp [A] | Venusaur [B] |
|---|---|---|---|---|
| 5.1 | Incineroar | Sneasler | Stomping Tantrum → Sneasler `28.48` | Earth Power → Incineroar `2.10` |
| 5.2 | Incineroar | Whimsicott | Poison Jab → Whimsicott `10.53` | Sludge Bomb → Whimsicott `9.15` |
| 5.3 | Incineroar | Garchomp | Dragon Claw → Garchomp `2.84` | Earth Power → Incineroar `2.10` |
| 5.4 | Incineroar | Farigiraf | Stomping Tantrum → Incineroar `6.26` | Sludge Bomb → Farigiraf `6.55` |
| 5.5 | Incineroar | Kingambit | Stomping Tantrum → Incineroar `3.13` | Earth Power → Kingambit `3.89` |
| 5.6 | Incineroar | Aerodactyl | Stomping Tantrum → Incineroar `4.69` | Giga Drain → Aerodactyl `3.66` |
| 5.7 | Farigiraf | Sneasler | Stomping Tantrum → Sneasler `56.96` | Sludge Bomb → Farigiraf `4.37` |
| 5.8 | Farigiraf | Garchomp | Dragon Claw → Garchomp `11.37` | Sludge Bomb → Farigiraf `4.37` |
| 5.9 | Whimsicott | Garchomp | Poison Jab → Whimsicott `15.80` | Sludge Bomb → Whimsicott `6.86` |
| 5.10 | Whimsicott | Kingambit | Poison Jab → Whimsicott `21.07` | Sludge Bomb → Whimsicott `9.15` |
| 5.11 | Sneasler | Garchomp | Stomping Tantrum → Sneasler `21.36` | Switch → Basculegion `1.60` |
| 5.12 | Sneasler | Kingambit | Stomping Tantrum → Sneasler `28.48` | Earth Power → Kingambit `2.60` |
| 5.13 | Aerodactyl | Garchomp | Dragon Claw → Garchomp `8.53` | Giga Drain → Aerodactyl `2.74` |
| 5.14 | Lopunny | Garchomp | Dragon Claw → Garchomp `2.84` | Sludge Bomb → Lopunny `1.91` |
| 5.15 | Weavile | Garchomp | Switch → Kingambit `5.43` | Protect → ? `2.00` |
| 5.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `62.02` | Giga Drain → Garchomp `2.24` |
| 5.17 | Charizard | Incineroar | Rock Tomb → Charizard `25.48` | Earth Power → Incineroar `3.15` |
| 5.18 | Rotom-Wash | Garchomp | Dragon Claw → Garchomp `5.69` | Giga Drain → Rotom-Wash `3.05` |
| 5.19 | Glimmora | Incineroar | Stomping Tantrum → Incineroar `3.13` | Earth Power → Glimmora `27.59` |
| 5.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `8.02` | Switch → Kingambit `3.20` |

---

## 6. My Lead: **Sneasler** [A]  +  **Kingambit** [B]
Bench: Aerodactyl, Basculegion, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Sneasler [A] | Kingambit [B] |
|---|---|---|---|---|
| 6.1 | Incineroar | Sneasler | Close Combat → Incineroar `2.83` | Switch → Basculegion `6.48` |
| 6.2 | Incineroar | Whimsicott | Dire Claw → Whimsicott `8.96` | Iron Head → Whimsicott `3.38` |
| 6.3 | Incineroar | Garchomp | Protect → ? `5.00` | Protect → ? `2.00` |
| 6.4 | Incineroar | Farigiraf | Close Combat → Incineroar `7.54` | Kowtow Cleave → Farigiraf `8.25` |
| 6.5 | Incineroar | Kingambit | Close Combat → Incineroar `3.77` | Low Kick → Kingambit `2.56` |
| 6.6 | Incineroar | Aerodactyl | Close Combat → Incineroar `4.24` | Iron Head → Aerodactyl `6.55` |
| 6.7 | Farigiraf | Sneasler | Switch → Basculegion `7.32` | Protect → ? `5.00` |
| 6.8 | Farigiraf | Garchomp | Close Combat → Garchomp `7.22` | Kowtow Cleave → Farigiraf `8.25` |
| 6.9 | Whimsicott | Garchomp | Dire Claw → Whimsicott `11.95` | Kowtow Cleave → Garchomp `2.57` |
| 6.10 | Whimsicott | Kingambit | Dire Claw → Whimsicott `17.93` | Iron Head → Whimsicott `4.51` |
| 6.11 | Sneasler | Garchomp | Switch → Garchomp `6.21` | Switch → Basculegion `6.48` |
| 6.12 | Sneasler | Kingambit | Close Combat → Kingambit `2.49` | Switch → Garchomp `5.35` |
| 6.13 | Aerodactyl | Garchomp | Switch → Basculegion `8.20` | Iron Head → Aerodactyl `6.55` |
| 6.14 | Lopunny | Garchomp | Close Combat → Lopunny `13.14` | Protect → ? `7.50` |
| 6.15 | Weavile | Garchomp | Close Combat → Weavile `6.72` | Low Kick → Weavile `1.87` |
| 6.16 | Talonflame | Garchomp | Switch → Basculegion `7.02` | Kowtow Cleave → Talonflame `3.59` |
| 6.17 | Charizard | Incineroar | Protect → ? `5.00` | Switch → Aerodactyl `5.95` |
| 6.18 | Rotom-Wash | Garchomp | Switch → Garchomp `3.90` | Kowtow Cleave → Rotom-Wash `2.15` |
| 6.19 | Glimmora | Incineroar | Close Combat → Incineroar `3.77` | Iron Head → Glimmora `3.05` |
| 6.20 | Pelipper | Dragonite | Switch → Basculegion `4.00` | Kowtow Cleave → Pelipper `3.14` |
