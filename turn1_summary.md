# Turn 1 First-Turn Decision Summary

Engine v0.8.7 | Turn 1 opening, 100% HP, no field effects, no revealed moves

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
| 1.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `19.85` | Switch → Basculegion `6.78` |
| 1.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `26.95` | Switch → Kingambit `3.20` |
| 1.3 | Incineroar | Garchomp | Ice Fang → Garchomp `2.92` | Switch → Basculegion `6.10` |
| 1.4 | Incineroar | Farigiraf | Rock Tomb → Incineroar `4.23` | Switch → Basculegion `6.03` |
| 1.5 | Incineroar | Kingambit | Protect → ? `5.00` | Protect → ? `5.00` |
| 1.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `3.51` | Switch → Basculegion `9.44` |
| 1.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `39.69` | Sludge Bomb → Farigiraf `3.66` |
| 1.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `11.68` | Sludge Bomb → Farigiraf `3.66` |
| 1.9 | Whimsicott | Garchomp | Dual Wingbeat → Whimsicott `53.89` | Giga Drain → Garchomp `1.95` |
| 1.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `53.89` | Earth Power → Kingambit `3.03` |
| 1.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `19.85` | Switch → Basculegion `1.70` |
| 1.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `19.85` | Earth Power → Kingambit `2.02` |
| 1.13 | Aerodactyl | Garchomp | Rock Tomb → Aerodactyl `7.02` | Switch → Basculegion `2.36` |
| 1.14 | Lopunny | Garchomp | Dual Wingbeat → Lopunny `11.96` | Giga Drain → Garchomp `1.30` |
| 1.15 | Weavile | Garchomp | Rock Tomb → Weavile `2.45` | Switch → Kingambit `1.67` |
| 1.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `56.37` | Switch → Basculegion `8.57` |
| 1.17 | Charizard | Incineroar | Rock Tomb → Charizard `23.62` | Protect → ? `7.50` |
| 1.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `5.84` | Giga Drain → Rotom-Wash `2.08` |
| 1.19 | Glimmora | Incineroar | Protect → ? `15.00` | Switch → Garchomp `5.27` |
| 1.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `8.19` | Switch → Kingambit `3.20` |

---

## 2. My Lead: **Aerodactyl** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Kingambit, Sneasler, Basculegion, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Venusaur [B] |
|---|---|---|---|---|
| 2.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `13.12` | Earth Power → Incineroar `1.92` |
| 2.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `17.93` | Earth Power → Incineroar `2.87` |
| 2.3 | Incineroar | Garchomp | Ice Fang → Garchomp `2.64` | Earth Power → Incineroar `1.92` |
| 2.4 | Incineroar | Farigiraf | Rock Tomb → Incineroar `3.90` | Sludge Bomb → Farigiraf `5.89` |
| 2.5 | Incineroar | Kingambit | Protect → ? `5.00` | Protect → ? `2.00` |
| 2.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `3.11` | Earth Power → Incineroar `2.87` |
| 2.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `26.24` | Sludge Bomb → Farigiraf `3.92` |
| 2.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `10.56` | Sludge Bomb → Farigiraf `3.92` |
| 2.9 | Whimsicott | Garchomp | Dual Wingbeat → Whimsicott `35.86` | Giga Drain → Garchomp `2.08` |
| 2.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `35.86` | Earth Power → Kingambit `3.30` |
| 2.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `13.12` | Switch → Basculegion `1.60` |
| 2.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `13.12` | Earth Power → Kingambit `2.20` |
| 2.13 | Aerodactyl | Garchomp | Rock Tomb → Aerodactyl `6.23` | Switch → Basculegion `2.30` |
| 2.14 | Lopunny | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 2.15 | Weavile | Garchomp | Switch → Kingambit `5.41` | Protect → ? `2.00` |
| 2.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `48.85` | Giga Drain → Garchomp `2.08` |
| 2.17 | Charizard | Incineroar | Rock Tomb → Charizard `20.75` | Earth Power → Incineroar `1.92` |
| 2.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `5.28` | Giga Drain → Rotom-Wash `2.28` |
| 2.19 | Glimmora | Incineroar | Switch → Garchomp `7.67` | Earth Power → Glimmora `9.67` |
| 2.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `7.38` | Switch → Kingambit `3.20` |

---

## 3. My Lead: **Garchomp** [A]  +  **Kingambit** [B]
Bench: Aerodactyl, Sneasler, Basculegion, Venusaur

| # | Opp [A] | Opp [B] | Garchomp [A] | Kingambit [B] |
|---|---|---|---|---|
| 3.1 | Incineroar | Sneasler | Stomping Tantrum → Sneasler `19.85` | Switch → Basculegion `1.62` |
| 3.2 | Incineroar | Whimsicott | Poison Jab → Whimsicott `7.09` | Iron Head → Whimsicott `2.37` |
| 3.3 | Incineroar | Garchomp | Dragon Claw → Garchomp `2.88` | Low Kick → Incineroar `1.57` |
| 3.4 | Incineroar | Farigiraf | Stomping Tantrum → Incineroar `5.00` | Kowtow Cleave → Farigiraf `6.14` |
| 3.5 | Incineroar | Kingambit | Stomping Tantrum → Incineroar `2.50` | Low Kick → Kingambit `2.18` |
| 3.6 | Incineroar | Aerodactyl | Stomping Tantrum → Incineroar `3.75` | Iron Head → Aerodactyl `4.55` |
| 3.7 | Farigiraf | Sneasler | Stomping Tantrum → Sneasler `39.69` | Kowtow Cleave → Farigiraf `6.14` |
| 3.8 | Farigiraf | Garchomp | Dragon Claw → Garchomp `11.52` | Kowtow Cleave → Farigiraf `6.14` |
| 3.9 | Whimsicott | Garchomp | Dragon Claw → Garchomp `8.64` | Iron Head → Whimsicott `4.32` |
| 3.10 | Whimsicott | Kingambit | Poison Jab → Whimsicott `14.18` | Low Kick → Kingambit `3.27` |
| 3.11 | Sneasler | Garchomp | Stomping Tantrum → Sneasler `19.85` | Switch → Basculegion `1.62` |
| 3.12 | Sneasler | Kingambit | Stomping Tantrum → Sneasler `19.85` | Low Kick → Kingambit `2.18` |
| 3.13 | Aerodactyl | Garchomp | Dragon Claw → Garchomp `8.64` | Iron Head → Aerodactyl `4.55` |
| 3.14 | Lopunny | Garchomp | Dragon Claw → Garchomp `2.88` | Switch → Basculegion `4.33` |
| 3.15 | Weavile | Garchomp | Dragon Claw → Garchomp `2.88` | Low Kick → Weavile `3.20` |
| 3.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `57.97` | Kowtow Cleave → Garchomp `2.27` |
| 3.17 | Charizard | Incineroar | Rock Tomb → Charizard `18.13` | Low Kick → Incineroar `1.57` |
| 3.18 | Rotom-Wash | Garchomp | Dragon Claw → Garchomp `5.76` | Kowtow Cleave → Rotom-Wash `1.77` |
| 3.19 | Glimmora | Incineroar | Stomping Tantrum → Glimmora `23.73` | Low Kick → Incineroar `1.57` |
| 3.20 | Pelipper | Dragonite | Dragon Claw → Dragonite `5.68` | Kowtow Cleave → Pelipper `2.60` |

---

## 4. My Lead: **Aerodactyl** [A]  +  **Sneasler** [B] *(mega: Aerodactyl)*
Bench: Kingambit, Basculegion, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Sneasler [B] |
|---|---|---|---|---|
| 4.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `19.85` | Close Combat → Incineroar `2.87` |
| 4.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `26.95` | Close Combat → Incineroar `4.30` |
| 4.3 | Incineroar | Garchomp | Ice Fang → Garchomp `2.92` | Switch → Basculegion `4.37` |
| 4.4 | Incineroar | Farigiraf | Dual Wingbeat → Farigiraf `3.78` | Close Combat → Incineroar `8.60` |
| 4.5 | Incineroar | Kingambit | Protect → ? `5.00` | Protect → ? `2.00` |
| 4.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `3.51` | Close Combat → Incineroar `4.30` |
| 4.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `39.69` | Switch → Basculegion `7.32` |
| 4.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `11.68` | Switch → Kingambit `4.75` |
| 4.9 | Whimsicott | Garchomp | Dual Wingbeat → Whimsicott `53.89` | Switch → Venusaur `4.67` |
| 4.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `53.89` | Close Combat → Kingambit `3.91` |
| 4.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `19.85` | Switch → Basculegion `7.34` |
| 4.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `19.85` | Close Combat → Kingambit `2.61` |
| 4.13 | Aerodactyl | Garchomp | Rock Tomb → Aerodactyl `7.02` | Switch → Basculegion `8.20` |
| 4.14 | Lopunny | Garchomp | Dual Wingbeat → Lopunny `11.96` | Switch → Basculegion `3.20` |
| 4.15 | Weavile | Garchomp | Ice Fang → Garchomp `2.19` | Close Combat → Weavile `6.30` |
| 4.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `56.37` | Protect → ? `7.50` |
| 4.17 | Charizard | Incineroar | Rock Tomb → Charizard `23.62` | Close Combat → Incineroar `4.30` |
| 4.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `5.84` | Switch → Garchomp `3.90` |
| 4.19 | Glimmora | Incineroar | Switch → Garchomp `7.41` | Close Combat → Incineroar `2.15` |
| 4.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `8.19` | Switch → Kingambit `3.74` |

---

## 5. My Lead: **Garchomp** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Aerodactyl, Kingambit, Sneasler, Basculegion

| # | Opp [A] | Opp [B] | Garchomp [A] | Venusaur [B] |
|---|---|---|---|---|
| 5.1 | Incineroar | Sneasler | Stomping Tantrum → Sneasler `19.85` | Earth Power → Incineroar `1.92` |
| 5.2 | Incineroar | Whimsicott | Poison Jab → Whimsicott `7.09` | Sludge Bomb → Whimsicott `5.82` |
| 5.3 | Incineroar | Garchomp | Dragon Claw → Garchomp `2.88` | Earth Power → Incineroar `1.92` |
| 5.4 | Incineroar | Farigiraf | Stomping Tantrum → Incineroar `5.00` | Sludge Bomb → Farigiraf `5.89` |
| 5.5 | Incineroar | Kingambit | Stomping Tantrum → Incineroar `2.50` | Earth Power → Kingambit `3.30` |
| 5.6 | Incineroar | Aerodactyl | Stomping Tantrum → Incineroar `3.75` | Giga Drain → Aerodactyl `3.16` |
| 5.7 | Farigiraf | Sneasler | Stomping Tantrum → Sneasler `39.69` | Sludge Bomb → Farigiraf `3.92` |
| 5.8 | Farigiraf | Garchomp | Dragon Claw → Garchomp `11.52` | Sludge Bomb → Farigiraf `3.92` |
| 5.9 | Whimsicott | Garchomp | Dragon Claw → Garchomp `8.64` | Sludge Bomb → Whimsicott `7.93` |
| 5.10 | Whimsicott | Kingambit | Poison Jab → Whimsicott `14.18` | Sludge Bomb → Whimsicott `5.82` |
| 5.11 | Sneasler | Garchomp | Stomping Tantrum → Sneasler `19.85` | Switch → Basculegion `1.60` |
| 5.12 | Sneasler | Kingambit | Stomping Tantrum → Sneasler `19.85` | Earth Power → Kingambit `2.20` |
| 5.13 | Aerodactyl | Garchomp | Dragon Claw → Garchomp `8.64` | Giga Drain → Aerodactyl `2.37` |
| 5.14 | Lopunny | Garchomp | Dragon Claw → Garchomp `2.88` | Sludge Bomb → Lopunny `1.63` |
| 5.15 | Weavile | Garchomp | Switch → Kingambit `5.43` | Protect → ? `2.00` |
| 5.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `57.97` | Giga Drain → Garchomp `2.08` |
| 5.17 | Charizard | Incineroar | Rock Tomb → Charizard `18.13` | Earth Power → Incineroar `1.92` |
| 5.18 | Rotom-Wash | Garchomp | Dragon Claw → Garchomp `5.76` | Giga Drain → Rotom-Wash `2.28` |
| 5.19 | Glimmora | Incineroar | Stomping Tantrum → Incineroar `2.50` | Earth Power → Glimmora `19.34` |
| 5.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `6.73` | Switch → Kingambit `3.20` |

---

## 6. My Lead: **Sneasler** [A]  +  **Kingambit** [B]
Bench: Aerodactyl, Basculegion, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Sneasler [A] | Kingambit [B] |
|---|---|---|---|---|
| 6.1 | Incineroar | Sneasler | Close Combat → Incineroar `2.15` | Switch → Basculegion `6.48` |
| 6.2 | Incineroar | Whimsicott | Dire Claw → Whimsicott `5.93` | Iron Head → Whimsicott `2.37` |
| 6.3 | Incineroar | Garchomp | Protect → ? `5.00` | Protect → ? `2.00` |
| 6.4 | Incineroar | Farigiraf | Close Combat → Incineroar `5.74` | Kowtow Cleave → Farigiraf `6.14` |
| 6.5 | Incineroar | Kingambit | Close Combat → Incineroar `2.87` | Low Kick → Kingambit `2.18` |
| 6.6 | Incineroar | Aerodactyl | Close Combat → Incineroar `3.23` | Iron Head → Aerodactyl `4.55` |
| 6.7 | Farigiraf | Sneasler | Switch → Basculegion `7.32` | Protect → ? `5.00` |
| 6.8 | Farigiraf | Garchomp | Close Combat → Garchomp `6.27` | Kowtow Cleave → Farigiraf `6.14` |
| 6.9 | Whimsicott | Garchomp | Switch → Venusaur `4.67` | Iron Head → Whimsicott `4.32` |
| 6.10 | Whimsicott | Kingambit | Dire Claw → Whimsicott `11.85` | Low Kick → Kingambit `3.27` |
| 6.11 | Sneasler | Garchomp | Switch → Garchomp `6.21` | Switch → Basculegion `6.48` |
| 6.12 | Sneasler | Kingambit | Protect → ? `2.00` | Switch → Garchomp `5.35` |
| 6.13 | Aerodactyl | Garchomp | Switch → Basculegion `8.20` | Iron Head → Aerodactyl `4.55` |
| 6.14 | Lopunny | Garchomp | Protect → ? `5.00` | Protect → ? `15.00` |
| 6.15 | Weavile | Garchomp | Protect → ? `5.00` | Protect → ? `2.00` |
| 6.16 | Talonflame | Garchomp | Switch → Basculegion `7.02` | Kowtow Cleave → Talonflame `2.86` |
| 6.17 | Charizard | Incineroar | Protect → ? `5.00` | Switch → Aerodactyl `5.95` |
| 6.18 | Rotom-Wash | Garchomp | Switch → Garchomp `3.90` | Kowtow Cleave → Rotom-Wash `1.77` |
| 6.19 | Glimmora | Incineroar | Close Combat → Incineroar `2.87` | Iron Head → Glimmora `2.28` |
| 6.20 | Pelipper | Dragonite | Rock Tomb → Dragonite `4.06` | Kowtow Cleave → Pelipper `2.60` |
