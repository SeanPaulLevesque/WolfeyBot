# Turn 1 First-Turn Decision Summary

Engine v0.28.0 | Turn 1 opening, 100% HP, no field effects, no revealed moves

> **Joint selection.** Each slot's `(move, target)` candidates are scored
> independently (phase 1); `DecisionEngine.coordinate` then picks the
> highest-value **pair** of actions (phase 2).
> All opponent HP treated as percentage (engine uses typical-spread stats for damage calcs).
> Mega evolution is resolved at turn start — the designated mega uses mega stats/ability.
>
> The phase-2 **joint adjusters** are the only cross-slot effects: *doubling* (both attack the same target → ×0.40–0.70, or ×0.05 overkill when one slot already confirms the OHKO, so the pair that spreads wins); *coordination* (a gratuitous lone Protect beside an attacking partner → ×0.5, favouring double-attack); *fake-out* (the slot absorbing a Fake Out frees its partner); and *switch-collision* (both switching to the same mon → ×0). These cells reflect actual in-game behaviour.

---

## 1. My Lead: **Aerodactyl** [A]  +  **Kingambit** [B] *(mega: Aerodactyl)*
Bench: Sneasler, Basculegion-M, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Kingambit [B] |
|---|---|---|---|---|
| 1.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `35.91` | Low Kick → Incineroar `1.82` |
| 1.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `47.70` | Low Kick → Incineroar `2.73` |
| 1.3 | Incineroar | Garchomp | Ice Fang → Garchomp `24.20` | Low Kick → Incineroar `1.82` |
| 1.4 | Incineroar | Farigiraf | Rock Tomb → Incineroar `4.91` | Kowtow Cleave → Farigiraf `8.25` |
| 1.5 | Incineroar | Kingambit | Protect → ? `5.00` | Protect → ? `2.00` |
| 1.6 | Incineroar | Aerodactyl | Rock Tomb → Incineroar `2.76` | Iron Head → Aerodactyl `6.55` |
| 1.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `71.81` | Kowtow Cleave → Farigiraf `8.25` |
| 1.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `96.80` | Kowtow Cleave → Farigiraf `8.25` |
| 1.9 | Whimsicott | Garchomp | Ice Fang → Garchomp `72.60` | Iron Head → Whimsicott `6.15` |
| 1.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `95.41` | Low Kick → Kingambit `3.85` |
| 1.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `35.91` | Kowtow Cleave → Garchomp `1.71` |
| 1.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `35.91` | Low Kick → Kingambit `2.56` |
| 1.13 | Aerodactyl | Garchomp | Ice Fang → Garchomp `54.45` | Iron Head → Aerodactyl `6.55` |
| 1.14 | Lopunny | Garchomp | Dual Wingbeat → Lopunny `20.38` | Protect → ? `7.50` |
| 1.15 | Weavile | Garchomp | Ice Fang → Garchomp `18.15` | Low Kick → Weavile `4.67` |
| 1.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `84.58` | Kowtow Cleave → Garchomp `2.57` |
| 1.17 | Charizard | Incineroar | Rock Tomb → Charizard `35.08` | Protect → ? `7.50` |
| 1.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `48.40` | Kowtow Cleave → Rotom-Wash `2.15` |
| 1.19 | Glimmora | Incineroar | Switch → Garchomp `7.41` | Protect → ? `2.00` |
| 1.20 | Pelipper | Dragonite | Ice Fang → Dragonite `7.63` | Kowtow Cleave → Pelipper `3.14` |

---

## 2. My Lead: **Aerodactyl** [A]  +  **Sneasler** [B] *(mega: Aerodactyl)*
Bench: Kingambit, Basculegion-M, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Sneasler [B] |
|---|---|---|---|---|
| 2.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `35.91` | Close Combat → Incineroar `3.77` |
| 2.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `47.70` | Close Combat → Incineroar `5.65` |
| 2.3 | Incineroar | Garchomp | Ice Fang → Garchomp `24.20` | Close Combat → Incineroar `3.77` |
| 2.4 | Incineroar | Farigiraf | Dual Wingbeat → Farigiraf `5.02` | Close Combat → Incineroar `11.31` |
| 2.5 | Incineroar | Kingambit | Rock Tomb → Incineroar `2.46` | Close Combat → Kingambit `4.97` |
| 2.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `4.74` | Close Combat → Incineroar `5.65` |
| 2.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `71.81` | Switch → Basculegion-M `7.32` |
| 2.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `96.80` | Protect → ? `7.50` |
| 2.9 | Whimsicott | Garchomp | Ice Fang → Garchomp `72.60` | Dire Claw → Whimsicott `8.96` |
| 2.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `95.41` | Close Combat → Kingambit `4.97` |
| 2.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `35.91` | Switch → Basculegion-M `1.83` |
| 2.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `35.91` | Close Combat → Kingambit `3.32` |
| 2.13 | Aerodactyl | Garchomp | Ice Fang → Garchomp `54.45` | Close Combat → Aerodactyl `3.97` |
| 2.14 | Lopunny | Garchomp | Ice Fang → Garchomp `18.15` | Close Combat → Lopunny `19.71` |
| 2.15 | Weavile | Garchomp | Ice Fang → Garchomp `18.15` | Close Combat → Weavile `10.09` |
| 2.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `84.58` | Protect → ? `7.50` |
| 2.17 | Charizard | Incineroar | Rock Tomb → Charizard `35.08` | Close Combat → Incineroar `5.65` |
| 2.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `48.40` | Close Combat → Rotom-Wash `3.02` |
| 2.19 | Glimmora | Incineroar | Switch → Garchomp `7.41` | Close Combat → Incineroar `2.83` |
| 2.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `10.57` | Switch → Basculegion-M `4.00` |

---

## 3. My Lead: **Aerodactyl** [A]  +  **Basculegion-M** [B] *(mega: Aerodactyl)*
Bench: Kingambit, Sneasler, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Basculegion-M [B] |
|---|---|---|---|---|
| 3.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `35.91` | Wave Crash → Incineroar `25.26` |
| 3.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `47.70` | Wave Crash → Incineroar `37.89` |
| 3.3 | Incineroar | Garchomp | Ice Fang → Garchomp `24.20` | Wave Crash → Incineroar `25.26` |
| 3.4 | Incineroar | Farigiraf | Dual Wingbeat → Farigiraf `5.02` | Wave Crash → Incineroar `75.78` |
| 3.5 | Incineroar | Kingambit | Switch → Sneasler `4.40` | Wave Crash → Incineroar `18.94` |
| 3.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `4.74` | Wave Crash → Incineroar `37.89` |
| 3.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `71.81` | Wave Crash → Farigiraf `6.42` |
| 3.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `96.80` | Wave Crash → Farigiraf `6.42` |
| 3.9 | Whimsicott | Garchomp | Dual Wingbeat → Whimsicott `95.41` | Wave Crash → Garchomp `3.56` |
| 3.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `95.41` | Switch → Venusaur `9.69` |
| 3.11 | Sneasler | Garchomp | Ice Fang → Garchomp `24.20` | Psychic Fangs → Sneasler `26.00` |
| 3.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `35.91` | Switch → Sneasler `3.20` |
| 3.13 | Aerodactyl | Garchomp | Ice Fang → Garchomp `54.45` | Wave Crash → Aerodactyl `10.12` |
| 3.14 | Lopunny | Garchomp | Ice Fang → Garchomp `18.15` | Wave Crash → Lopunny `2.89` |
| 3.15 | Weavile | Garchomp | Ice Fang → Garchomp `18.15` | Wave Crash → Weavile `3.78` |
| 3.16 | Talonflame | Garchomp | Ice Fang → Garchomp `54.45` | Wave Crash → Talonflame `47.93` |
| 3.17 | Charizard | Incineroar | Rock Tomb → Charizard `35.08` | Wave Crash → Incineroar `2.74` |
| 3.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `48.40` | Wave Crash → Rotom-Wash `1.69` |
| 3.19 | Glimmora | Incineroar | Protect → ? `7.50` | Wave Crash → Glimmora `15.41` |
| 3.20 | Pelipper | Dragonite | Ice Fang → Dragonite `7.63` | Wave Crash → Pelipper `3.46` |

---

## 4. My Lead: **Aerodactyl** [A]  +  **Venusaur** [B] *(mega: Aerodactyl)*
Bench: Kingambit, Sneasler, Basculegion-M, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Venusaur [B] |
|---|---|---|---|---|
| 4.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `35.91` | Switch → Basculegion-M `6.78` |
| 4.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `47.70` | Switch → Kingambit `3.20` |
| 4.3 | Incineroar | Garchomp | Ice Fang → Garchomp `24.20` | Switch → Basculegion-M `6.10` |
| 4.4 | Incineroar | Farigiraf | Dual Wingbeat → Farigiraf `5.02` | Switch → Basculegion-M `6.03` |
| 4.5 | Incineroar | Kingambit | Protect → ? `5.00` | Protect → ? `5.00` |
| 4.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `4.74` | Switch → Basculegion-M `9.44` |
| 4.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `71.81` | Sludge Bomb → Farigiraf `3.91` |
| 4.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `96.80` | Sludge Bomb → Farigiraf `3.91` |
| 4.9 | Whimsicott | Garchomp | Ice Fang → Garchomp `72.60` | Sludge Bomb → Whimsicott `10.77` |
| 4.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `95.41` | Earth Power → Kingambit `3.42` |
| 4.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `35.91` | Switch → Basculegion-M `1.70` |
| 4.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `35.91` | Earth Power → Kingambit `2.28` |
| 4.13 | Aerodactyl | Garchomp | Ice Fang → Garchomp `54.45` | Giga Drain → Aerodactyl `2.44` |
| 4.14 | Lopunny | Garchomp | Ice Fang → Garchomp `18.15` | Sludge Bomb → Lopunny `1.68` |
| 4.15 | Weavile | Garchomp | Ice Fang → Garchomp `18.15` | Sludge Bomb → Weavile `1.81` |
| 4.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `84.58` | Switch → Basculegion-M `8.57` |
| 4.17 | Charizard | Incineroar | Rock Tomb → Charizard `26.31` | Protect → ? `7.50` |
| 4.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `48.40` | Giga Drain → Rotom-Wash `2.71` |
| 4.19 | Glimmora | Incineroar | Protect → ? `7.50` | Earth Power → Glimmora `11.97` |
| 4.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `10.57` | Switch → Basculegion-M `3.35` |

---

## 5. My Lead: **Aerodactyl** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Kingambit, Sneasler, Basculegion-M, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Venusaur [B] |
|---|---|---|---|---|
| 5.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `18.27` | Earth Power → Incineroar `2.10` |
| 5.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `24.35` | Earth Power → Incineroar `3.15` |
| 5.3 | Incineroar | Garchomp | Ice Fang → Garchomp `3.37` | Earth Power → Incineroar `2.10` |
| 5.4 | Incineroar | Farigiraf | Rock Tomb → Incineroar `4.33` | Sludge Bomb → Farigiraf `6.55` |
| 5.5 | Incineroar | Kingambit | Protect → ? `5.00` | Protect → ? `2.00` |
| 5.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `4.04` | Earth Power → Incineroar `3.15` |
| 5.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `36.54` | Sludge Bomb → Farigiraf `4.37` |
| 5.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `13.48` | Sludge Bomb → Farigiraf `4.37` |
| 5.9 | Whimsicott | Garchomp | Dual Wingbeat → Whimsicott `48.69` | Giga Drain → Garchomp `2.24` |
| 5.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `48.69` | Earth Power → Kingambit `3.89` |
| 5.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `18.27` | Switch → Basculegion-M `1.60` |
| 5.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `18.27` | Earth Power → Kingambit `2.60` |
| 5.13 | Aerodactyl | Garchomp | Ice Fang → Garchomp `7.58` | Giga Drain → Aerodactyl `2.74` |
| 5.14 | Lopunny | Garchomp | Ice Fang → Garchomp `2.53` | Sludge Bomb → Lopunny `1.91` |
| 5.15 | Weavile | Garchomp | Switch → Kingambit `5.41` | Protect → ? `2.00` |
| 5.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `71.42` | Giga Drain → Garchomp `2.24` |
| 5.17 | Charizard | Incineroar | Rock Tomb → Charizard `22.55` | Earth Power → Incineroar `4.21` |
| 5.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `6.74` | Giga Drain → Rotom-Wash `3.05` |
| 5.19 | Glimmora | Incineroar | Switch → Garchomp `7.67` | Earth Power → Glimmora `13.80` |
| 5.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `9.16` | Switch → Kingambit `3.20` |

---

## 6. My Lead: **Aerodactyl** [A]  +  **Garchomp** [B] *(mega: Aerodactyl)*
Bench: Kingambit, Sneasler, Basculegion-M, Venusaur

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Garchomp [B] |
|---|---|---|---|---|
| 6.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `26.93` | Stomping Tantrum → Incineroar `6.26` |
| 6.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `35.78` | Stomping Tantrum → Incineroar `9.39` |
| 6.3 | Incineroar | Garchomp | Ice Fang → Garchomp `18.15` | Stomping Tantrum → Incineroar `6.26` |
| 6.4 | Incineroar | Farigiraf | Dual Wingbeat → Farigiraf `3.77` | Stomping Tantrum → Incineroar `12.51` |
| 6.5 | Incineroar | Kingambit | Switch → Sneasler `4.40` | Stomping Tantrum → Incineroar `3.13` |
| 6.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `3.16` | Stomping Tantrum → Incineroar `9.39` |
| 6.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `53.86` | Dragon Claw → Farigiraf `8.67` |
| 6.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `72.60` | Dragon Claw → Farigiraf `8.67` |
| 6.9 | Whimsicott | Garchomp | Ice Fang → Garchomp `54.45` | Poison Jab → Whimsicott `21.07` |
| 6.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `71.56` | Stomping Tantrum → Kingambit `8.35` |
| 6.11 | Sneasler | Garchomp | Ice Fang → Garchomp `18.15` | Stomping Tantrum → Sneasler `56.96` |
| 6.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `26.93` | Stomping Tantrum → Kingambit `5.57` |
| 6.13 | Aerodactyl | Garchomp | Ice Fang → Garchomp `36.30` | Rock Tomb → Aerodactyl `9.42` |
| 6.14 | Lopunny | Garchomp | Dual Wingbeat → Lopunny `13.58` | Dragon Claw → Garchomp `7.58` |
| 6.15 | Weavile | Garchomp | Ice Fang → Garchomp `12.10` | Rock Tomb → Weavile `6.64` |
| 6.16 | Talonflame | Garchomp | Ice Fang → Garchomp `36.30` | Rock Tomb → Talonflame `82.69` |
| 6.17 | Charizard | Incineroar | Rock Tomb → Charizard `26.31` | Stomping Tantrum → Incineroar `6.26` |
| 6.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `36.30` | Dragon Claw → Rotom-Wash `5.33` |
| 6.19 | Glimmora | Incineroar | Rock Tomb → Incineroar `1.84` | Stomping Tantrum → Glimmora `70.56` |
| 6.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `7.93` | Dragon Claw → Dragonite `6.18` |

---

## 7. My Lead: **Kingambit** [A]  +  **Sneasler** [B]
Bench: Aerodactyl, Basculegion-M, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Kingambit [A] | Sneasler [B] |
|---|---|---|---|---|
| 7.1 | Incineroar | Sneasler | Switch → Basculegion-M `6.48` | Close Combat → Incineroar `2.83` |
| 7.2 | Incineroar | Whimsicott | Iron Head → Whimsicott `3.07` | Dire Claw → Whimsicott `9.86` |
| 7.3 | Incineroar | Garchomp | Protect → ? `2.00` | Protect → ? `5.00` |
| 7.4 | Incineroar | Farigiraf | Kowtow Cleave → Farigiraf `4.12` | Close Combat → Incineroar `15.08` |
| 7.5 | Incineroar | Kingambit | Low Kick → Kingambit `1.28` | Close Combat → Incineroar `7.54` |
| 7.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `3.27` | Close Combat → Incineroar `8.48` |
| 7.7 | Farigiraf | Sneasler | Protect → ? `5.00` | Switch → Basculegion-M `7.32` |
| 7.8 | Farigiraf | Garchomp | Kowtow Cleave → Farigiraf `8.25` | Switch → Aerodactyl `4.06` |
| 7.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `6.15` | Switch → Venusaur `4.67` |
| 7.10 | Whimsicott | Kingambit | Iron Head → Whimsicott `8.19` | Dire Claw → Whimsicott `9.86` |
| 7.11 | Sneasler | Garchomp | Protect → ? `5.00` | Switch → Basculegion-M `7.34` |
| 7.12 | Sneasler | Kingambit | Switch → Garchomp `5.35` | Close Combat → Kingambit `2.49` |
| 7.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `6.55` | Switch → Basculegion-M `8.20` |
| 7.14 | Lopunny | Garchomp | Protect → ? `5.00` | Protect → ? `5.00` |
| 7.15 | Weavile | Garchomp | Protect → ? `2.00` | Protect → ? `5.00` |
| 7.16 | Talonflame | Garchomp | Kowtow Cleave → Talonflame `3.59` | Switch → Basculegion-M `7.02` |
| 7.17 | Charizard | Incineroar | Switch → Aerodactyl `5.95` | Protect → ? `5.00` |
| 7.18 | Rotom-Wash | Garchomp | Kowtow Cleave → Rotom-Wash `2.15` | Switch → Venusaur `3.74` |
| 7.19 | Glimmora | Incineroar | Iron Head → Glimmora `1.52` | Close Combat → Incineroar `7.54` |
| 7.20 | Pelipper | Dragonite | Kowtow Cleave → Pelipper `3.14` | Switch → Basculegion-M `4.00` |

---

## 8. My Lead: **Kingambit** [A]  +  **Basculegion-M** [B]
Bench: Aerodactyl, Sneasler, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Kingambit [A] | Basculegion-M [B] |
|---|---|---|---|---|
| 8.1 | Incineroar | Sneasler | Protect → ? `7.50` | Psychic Fangs → Sneasler `26.00` |
| 8.2 | Incineroar | Whimsicott | Iron Head → Whimsicott `3.07` | Wave Crash → Incineroar `56.83` |
| 8.3 | Incineroar | Garchomp | Kowtow Cleave → Garchomp `0.86` | Wave Crash → Incineroar `37.89` |
| 8.4 | Incineroar | Farigiraf | Kowtow Cleave → Farigiraf `4.12` | Wave Crash → Incineroar `101.03` |
| 8.5 | Incineroar | Kingambit | Low Kick → Kingambit `1.28` | Wave Crash → Incineroar `50.52` |
| 8.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `3.27` | Wave Crash → Incineroar `56.83` |
| 8.7 | Farigiraf | Sneasler | Kowtow Cleave → Farigiraf `4.12` | Psychic Fangs → Sneasler `104.01` |
| 8.8 | Farigiraf | Garchomp | Kowtow Cleave → Farigiraf `8.25` | Wave Crash → Garchomp `9.48` |
| 8.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `6.15` | Wave Crash → Garchomp `4.74` |
| 8.10 | Whimsicott | Kingambit | Iron Head → Whimsicott `8.19` | Switch → Venusaur `9.69` |
| 8.11 | Sneasler | Garchomp | Protect → ? `7.50` | Psychic Fangs → Sneasler `17.33` |
| 8.12 | Sneasler | Kingambit | Protect → ? `7.50` | Psychic Fangs → Sneasler `26.00` |
| 8.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `6.55` | Wave Crash → Aerodactyl `7.42` |
| 8.14 | Lopunny | Garchomp | Protect → ? `5.00` | Protect → ? `2.00` |
| 8.15 | Weavile | Garchomp | Low Kick → Weavile `2.33` | Wave Crash → Garchomp `3.16` |
| 8.16 | Talonflame | Garchomp | Kowtow Cleave → Garchomp `2.57` | Wave Crash → Talonflame `63.90` |
| 8.17 | Charizard | Incineroar | Switch → Aerodactyl `5.95` | Protect → ? `5.00` |
| 8.18 | Rotom-Wash | Garchomp | Kowtow Cleave → Rotom-Wash `2.15` | Wave Crash → Garchomp `3.16` |
| 8.19 | Glimmora | Incineroar | Iron Head → Glimmora `1.52` | Wave Crash → Incineroar `37.89` |
| 8.20 | Pelipper | Dragonite | Kowtow Cleave → Pelipper `3.14` | Wave Crash → Pelipper `2.54` |

---

## 9. My Lead: **Kingambit** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Aerodactyl, Sneasler, Basculegion-M, Garchomp

| # | Opp [A] | Opp [B] | Kingambit [A] | Venusaur [B] |
|---|---|---|---|---|
| 9.1 | Incineroar | Sneasler | Switch → Basculegion-M `6.48` | Earth Power → Sneasler `2.57` |
| 9.2 | Incineroar | Whimsicott | Iron Head → Whimsicott `3.07` | Sludge Bomb → Whimsicott `13.72` |
| 9.3 | Incineroar | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 9.4 | Incineroar | Farigiraf | Kowtow Cleave → Farigiraf `4.12` | Earth Power → Incineroar `8.41` |
| 9.5 | Incineroar | Kingambit | Low Kick → Incineroar `1.21` | Earth Power → Kingambit `5.19` |
| 9.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `3.27` | Earth Power → Incineroar `4.73` |
| 9.7 | Farigiraf | Sneasler | Kowtow Cleave → Farigiraf `4.12` | Earth Power → Sneasler `10.28` |
| 9.8 | Farigiraf | Garchomp | Kowtow Cleave → Farigiraf `8.25` | Giga Drain → Garchomp `5.96` |
| 9.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `6.15` | Sludge Bomb → Whimsicott `9.15` |
| 9.10 | Whimsicott | Kingambit | Iron Head → Whimsicott `8.19` | Sludge Bomb → Whimsicott `13.72` |
| 9.11 | Sneasler | Garchomp | Switch → Basculegion-M `6.48` | Protect → ? `2.00` |
| 9.12 | Sneasler | Kingambit | Switch → Garchomp `5.35` | Earth Power → Sneasler `2.57` |
| 9.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `6.55` | Giga Drain → Garchomp `2.98` |
| 9.14 | Lopunny | Garchomp | Protect → ? `5.00` | Protect → ? `2.00` |
| 9.15 | Weavile | Garchomp | Low Kick → Weavile `2.33` | Giga Drain → Garchomp `1.99` |
| 9.16 | Talonflame | Garchomp | Kowtow Cleave → Garchomp `2.57` | Sludge Bomb → Talonflame `4.51` |
| 9.17 | Charizard | Incineroar | Switch → Aerodactyl `5.95` | Switch → Garchomp `5.89` |
| 9.18 | Rotom-Wash | Garchomp | Kowtow Cleave → Garchomp `1.71` | Giga Drain → Rotom-Wash `4.07` |
| 9.19 | Glimmora | Incineroar | Low Kick → Incineroar `0.91` | Earth Power → Glimmora `41.39` |
| 9.20 | Pelipper | Dragonite | Kowtow Cleave → Pelipper `3.14` | Switch → Basculegion-M `3.20` |

---

## 10. My Lead: **Kingambit** [A]  +  **Garchomp** [B]
Bench: Aerodactyl, Sneasler, Basculegion-M, Venusaur

| # | Opp [A] | Opp [B] | Kingambit [A] | Garchomp [B] |
|---|---|---|---|---|
| 10.1 | Incineroar | Sneasler | Low Kick → Incineroar `0.91` | Stomping Tantrum → Sneasler `56.96` |
| 10.2 | Incineroar | Whimsicott | Iron Head → Whimsicott `3.07` | Poison Jab → Whimsicott `11.59` |
| 10.3 | Incineroar | Garchomp | Protect → ? `2.00` | Switch → Basculegion-M `4.35` |
| 10.4 | Incineroar | Farigiraf | Kowtow Cleave → Farigiraf `4.12` | Stomping Tantrum → Incineroar `12.51` |
| 10.5 | Incineroar | Kingambit | Low Kick → Kingambit `1.28` | Stomping Tantrum → Incineroar `6.26` |
| 10.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `3.27` | Stomping Tantrum → Incineroar `9.39` |
| 10.7 | Farigiraf | Sneasler | Kowtow Cleave → Farigiraf `4.12` | Stomping Tantrum → Sneasler `113.93` |
| 10.8 | Farigiraf | Garchomp | Kowtow Cleave → Farigiraf `8.25` | Dragon Claw → Garchomp `15.16` |
| 10.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `6.15` | Dragon Claw → Garchomp `11.37` |
| 10.10 | Whimsicott | Kingambit | Iron Head → Whimsicott `8.19` | Poison Jab → Whimsicott `11.59` |
| 10.11 | Sneasler | Garchomp | Kowtow Cleave → Garchomp `0.86` | Stomping Tantrum → Sneasler `56.96` |
| 10.12 | Sneasler | Kingambit | Low Kick → Kingambit `1.28` | Stomping Tantrum → Sneasler `56.96` |
| 10.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `6.55` | Dragon Claw → Garchomp `11.37` |
| 10.14 | Lopunny | Garchomp | Switch → Basculegion-M `4.33` | Dragon Claw → Garchomp `3.79` |
| 10.15 | Weavile | Garchomp | Low Kick → Weavile `2.33` | Dragon Claw → Garchomp `7.58` |
| 10.16 | Talonflame | Garchomp | Kowtow Cleave → Garchomp `2.57` | Rock Tomb → Talonflame `82.69` |
| 10.17 | Charizard | Incineroar | Protect → ? `7.50` | Rock Tomb → Charizard `25.48` |
| 10.18 | Rotom-Wash | Garchomp | Kowtow Cleave → Rotom-Wash `2.15` | Dragon Claw → Garchomp `7.58` |
| 10.19 | Glimmora | Incineroar | Low Kick → Incineroar `0.91` | Stomping Tantrum → Glimmora `70.56` |
| 10.20 | Pelipper | Dragonite | Kowtow Cleave → Pelipper `3.14` | Dragon Claw → Dragonite `6.18` |

---

## 11. My Lead: **Sneasler** [A]  +  **Basculegion-M** [B]
Bench: Aerodactyl, Kingambit, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Sneasler [A] | Basculegion-M [B] |
|---|---|---|---|---|
| 11.1 | Incineroar | Sneasler | Close Combat → Incineroar `2.83` | Psychic Fangs → Sneasler `34.67` |
| 11.2 | Incineroar | Whimsicott | Dire Claw → Whimsicott `8.96` | Wave Crash → Incineroar `37.89` |
| 11.3 | Incineroar | Garchomp | Switch → Aerodactyl `3.20` | Wave Crash → Incineroar `12.63` |
| 11.4 | Incineroar | Farigiraf | Close Combat → Farigiraf `4.85` | Wave Crash → Incineroar `75.78` |
| 11.5 | Incineroar | Kingambit | Close Combat → Kingambit `3.32` | Wave Crash → Incineroar `37.89` |
| 11.6 | Incineroar | Aerodactyl | Close Combat → Aerodactyl `3.97` | Wave Crash → Incineroar `37.89` |
| 11.7 | Farigiraf | Sneasler | Close Combat → Farigiraf `3.64` | Psychic Fangs → Sneasler `69.34` |
| 11.8 | Farigiraf | Garchomp | Switch → Kingambit `4.75` | Wave Crash → Farigiraf `6.42` |
| 11.9 | Whimsicott | Garchomp | Switch → Venusaur `4.67` | Wave Crash → Garchomp `3.56` |
| 11.10 | Whimsicott | Kingambit | Dire Claw → Whimsicott `17.93` | Switch → Venusaur `9.69` |
| 11.11 | Sneasler | Garchomp | Switch → Aerodactyl `5.45` | Psychic Fangs → Sneasler `13.00` |
| 11.12 | Sneasler | Kingambit | Close Combat → Kingambit `2.49` | Psychic Fangs → Sneasler `34.67` |
| 11.13 | Aerodactyl | Garchomp | Switch → Kingambit `5.29` | Wave Crash → Aerodactyl `10.12` |
| 11.14 | Lopunny | Garchomp | Protect → ? `5.00` | Protect → ? `2.00` |
| 11.15 | Weavile | Garchomp | Protect → ? `5.00` | Protect → ? `2.00` |
| 11.16 | Talonflame | Garchomp | Protect → ? `7.50` | Wave Crash → Talonflame `47.93` |
| 11.17 | Charizard | Incineroar | Protect → ? `5.00` | Protect → ? `5.00` |
| 11.18 | Rotom-Wash | Garchomp | Switch → Venusaur `3.74` | Wave Crash → Garchomp `2.37` |
| 11.19 | Glimmora | Incineroar | Close Combat → Incineroar `3.77` | Wave Crash → Glimmora `30.83` |
| 11.20 | Pelipper | Dragonite | Switch → Kingambit `3.74` | Wave Crash → Pelipper `3.46` |

---

## 12. My Lead: **Sneasler** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Aerodactyl, Kingambit, Basculegion-M, Garchomp

| # | Opp [A] | Opp [B] | Sneasler [A] | Venusaur [B] |
|---|---|---|---|---|
| 12.1 | Incineroar | Sneasler | Close Combat → Incineroar `2.83` | Earth Power → Sneasler `3.43` |
| 12.2 | Incineroar | Whimsicott | Dire Claw → Whimsicott `8.96` | Sludge Bomb → Whimsicott `9.15` |
| 12.3 | Incineroar | Garchomp | Protect → ? `5.00` | Protect → ? `2.00` |
| 12.4 | Incineroar | Farigiraf | Close Combat → Incineroar `7.54` | Sludge Bomb → Farigiraf `6.55` |
| 12.5 | Incineroar | Kingambit | Close Combat → Incineroar `3.77` | Earth Power → Kingambit `3.89` |
| 12.6 | Incineroar | Aerodactyl | Close Combat → Incineroar `4.24` | Giga Drain → Aerodactyl `3.66` |
| 12.7 | Farigiraf | Sneasler | Switch → Basculegion-M `7.32` | Earth Power → Sneasler `3.43` |
| 12.8 | Farigiraf | Garchomp | Switch → Kingambit `4.75` | Sludge Bomb → Farigiraf `4.37` |
| 12.9 | Whimsicott | Garchomp | Switch → Aerodactyl `3.20` | Sludge Bomb → Whimsicott `12.47` |
| 12.10 | Whimsicott | Kingambit | Dire Claw → Whimsicott `17.93` | Sludge Bomb → Whimsicott `9.15` |
| 12.11 | Sneasler | Garchomp | Switch → Basculegion-M `7.34` | Protect → ? `2.00` |
| 12.12 | Sneasler | Kingambit | Close Combat → Kingambit `2.49` | Earth Power → Sneasler `3.43` |
| 12.13 | Aerodactyl | Garchomp | Switch → Basculegion-M `8.20` | Giga Drain → Aerodactyl `2.74` |
| 12.14 | Lopunny | Garchomp | Protect → ? `5.00` | Protect → ? `2.00` |
| 12.15 | Weavile | Garchomp | Protect → ? `5.00` | Protect → ? `2.00` |
| 12.16 | Talonflame | Garchomp | Switch → Basculegion-M `7.02` | Sludge Bomb → Talonflame `3.38` |
| 12.17 | Charizard | Incineroar | Protect → ? `5.00` | Switch → Aerodactyl `6.73` |
| 12.18 | Rotom-Wash | Garchomp | Switch → Basculegion-M `3.32` | Giga Drain → Rotom-Wash `3.05` |
| 12.19 | Glimmora | Incineroar | Close Combat → Incineroar `3.77` | Earth Power → Glimmora `27.59` |
| 12.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `6.60` | Switch → Kingambit `3.20` |

---

## 13. My Lead: **Sneasler** [A]  +  **Garchomp** [B]
Bench: Aerodactyl, Kingambit, Basculegion-M, Venusaur

| # | Opp [A] | Opp [B] | Sneasler [A] | Garchomp [B] |
|---|---|---|---|---|
| 13.1 | Incineroar | Sneasler | Close Combat → Incineroar `1.88` | Stomping Tantrum → Sneasler `56.96` |
| 13.2 | Incineroar | Whimsicott | Dire Claw → Whimsicott `5.98` | Poison Jab → Whimsicott `11.59` |
| 13.3 | Incineroar | Garchomp | Protect → ? `5.00` | Switch → Basculegion-M `4.35` |
| 13.4 | Incineroar | Farigiraf | Close Combat → Incineroar `5.65` | Dragon Claw → Farigiraf `8.67` |
| 13.5 | Incineroar | Kingambit | Close Combat → Incineroar `2.83` | Stomping Tantrum → Kingambit `5.57` |
| 13.6 | Incineroar | Aerodactyl | Close Combat → Incineroar `2.83` | Rock Tomb → Aerodactyl `9.42` |
| 13.7 | Farigiraf | Sneasler | Switch → Basculegion-M `7.32` | Stomping Tantrum → Sneasler `56.96` |
| 13.8 | Farigiraf | Garchomp | Switch → Kingambit `4.75` | Dragon Claw → Garchomp `15.16` |
| 13.9 | Whimsicott | Garchomp | Switch → Venusaur `4.67` | Poison Jab → Whimsicott `21.07` |
| 13.10 | Whimsicott | Kingambit | Dire Claw → Whimsicott `11.95` | Poison Jab → Whimsicott `11.59` |
| 13.11 | Sneasler | Garchomp | Switch → Basculegion-M `7.34` | Stomping Tantrum → Sneasler `28.48` |
| 13.12 | Sneasler | Kingambit | Close Combat → Kingambit `1.66` | Stomping Tantrum → Sneasler `56.96` |
| 13.13 | Aerodactyl | Garchomp | Switch → Basculegion-M `8.20` | Dragon Claw → Garchomp `11.37` |
| 13.14 | Lopunny | Garchomp | Protect → ? `5.00` | Switch → Basculegion-M `3.25` |
| 13.15 | Weavile | Garchomp | Protect → ? `5.00` | Switch → Kingambit `5.43` |
| 13.16 | Talonflame | Garchomp | Protect → ? `7.50` | Rock Tomb → Talonflame `82.69` |
| 13.17 | Charizard | Incineroar | Close Combat → Incineroar `2.83` | Rock Tomb → Charizard `50.95` |
| 13.18 | Rotom-Wash | Garchomp | Switch → Venusaur `3.74` | Dragon Claw → Garchomp `7.58` |
| 13.19 | Glimmora | Incineroar | Close Combat → Incineroar `2.83` | Stomping Tantrum → Glimmora `70.56` |
| 13.20 | Pelipper | Dragonite | Switch → Basculegion-M `4.00` | Rock Tomb → Pelipper `8.02` |

---

## 14. My Lead: **Basculegion-M** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Aerodactyl, Kingambit, Sneasler, Garchomp

| # | Opp [A] | Opp [B] | Basculegion-M [A] | Venusaur [B] |
|---|---|---|---|---|
| 14.1 | Incineroar | Sneasler | Wave Crash → Incineroar `12.63` | Earth Power → Sneasler `5.14` |
| 14.2 | Incineroar | Whimsicott | Wave Crash → Incineroar `18.94` | Sludge Bomb → Whimsicott `24.95` |
| 14.3 | Incineroar | Garchomp | Wave Crash → Incineroar `12.63` | Giga Drain → Garchomp `2.98` |
| 14.4 | Incineroar | Farigiraf | Wave Crash → Incineroar `37.89` | Sludge Bomb → Farigiraf `8.73` |
| 14.5 | Incineroar | Kingambit | Wave Crash → Incineroar `18.94` | Earth Power → Kingambit `5.19` |
| 14.6 | Incineroar | Aerodactyl | Wave Crash → Incineroar `18.94` | Giga Drain → Aerodactyl `5.49` |
| 14.7 | Farigiraf | Sneasler | Psychic Fangs → Sneasler `34.67` | Sludge Bomb → Farigiraf `6.55` |
| 14.8 | Farigiraf | Garchomp | Wave Crash → Garchomp `6.32` | Sludge Bomb → Farigiraf `6.55` |
| 14.9 | Whimsicott | Garchomp | Wave Crash → Garchomp `3.56` | Sludge Bomb → Whimsicott `16.63` |
| 14.10 | Whimsicott | Kingambit | Switch → Sneasler `8.23` | Sludge Bomb → Whimsicott `24.95` |
| 14.11 | Sneasler | Garchomp | Psychic Fangs → Sneasler `13.00` | Giga Drain → Garchomp `1.99` |
| 14.12 | Sneasler | Kingambit | Psychic Fangs → Sneasler `17.33` | Earth Power → Kingambit `3.89` |
| 14.13 | Aerodactyl | Garchomp | Wave Crash → Aerodactyl `10.12` | Giga Drain → Garchomp `2.98` |
| 14.14 | Lopunny | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 14.15 | Weavile | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 14.16 | Talonflame | Garchomp | Wave Crash → Talonflame `47.93` | Giga Drain → Garchomp `2.98` |
| 14.17 | Charizard | Incineroar | Protect → ? `5.00` | Switch → Aerodactyl `6.73` |
| 14.18 | Rotom-Wash | Garchomp | Wave Crash → Garchomp `2.37` | Giga Drain → Rotom-Wash `4.07` |
| 14.19 | Glimmora | Incineroar | Wave Crash → Incineroar `12.63` | Earth Power → Glimmora `41.39` |
| 14.20 | Pelipper | Dragonite | Wave Crash → Pelipper `3.46` | Switch → Kingambit `3.20` |

---

## 15. My Lead: **Basculegion-M** [A]  +  **Garchomp** [B]
Bench: Aerodactyl, Kingambit, Sneasler, Venusaur

| # | Opp [A] | Opp [B] | Basculegion-M [A] | Garchomp [B] |
|---|---|---|---|---|
| 15.1 | Incineroar | Sneasler | Wave Crash → Incineroar `12.63` | Stomping Tantrum → Sneasler `56.96` |
| 15.2 | Incineroar | Whimsicott | Wave Crash → Incineroar `18.94` | Poison Jab → Whimsicott `21.07` |
| 15.3 | Incineroar | Garchomp | Wave Crash → Incineroar `12.63` | Dragon Claw → Garchomp `7.58` |
| 15.4 | Incineroar | Farigiraf | Wave Crash → Incineroar `37.89` | Dragon Claw → Farigiraf `8.67` |
| 15.5 | Incineroar | Kingambit | Wave Crash → Incineroar `18.94` | Stomping Tantrum → Kingambit `5.57` |
| 15.6 | Incineroar | Aerodactyl | Wave Crash → Incineroar `18.94` | Rock Tomb → Aerodactyl `9.42` |
| 15.7 | Farigiraf | Sneasler | Wave Crash → Farigiraf `3.21` | Stomping Tantrum → Sneasler `113.93` |
| 15.8 | Farigiraf | Garchomp | Wave Crash → Farigiraf `6.42` | Dragon Claw → Garchomp `15.16` |
| 15.9 | Whimsicott | Garchomp | Wave Crash → Garchomp `3.56` | Poison Jab → Whimsicott `21.07` |
| 15.10 | Whimsicott | Kingambit | Switch → Venusaur `9.69` | Poison Jab → Whimsicott `21.07` |
| 15.11 | Sneasler | Garchomp | Psychic Fangs → Sneasler `13.00` | Dragon Claw → Garchomp `7.58` |
| 15.12 | Sneasler | Kingambit | Psychic Fangs → Sneasler `17.33` | Stomping Tantrum → Kingambit `5.57` |
| 15.13 | Aerodactyl | Garchomp | Wave Crash → Aerodactyl `10.12` | Dragon Claw → Garchomp `11.37` |
| 15.14 | Lopunny | Garchomp | Wave Crash → Lopunny `1.44` | Dragon Claw → Garchomp `7.58` |
| 15.15 | Weavile | Garchomp | Wave Crash → Weavile `1.89` | Dragon Claw → Garchomp `7.58` |
| 15.16 | Talonflame | Garchomp | Wave Crash → Talonflame `47.93` | Dragon Claw → Garchomp `11.37` |
| 15.17 | Charizard | Incineroar | Wave Crash → Incineroar `1.37` | Rock Tomb → Charizard `50.95` |
| 15.18 | Rotom-Wash | Garchomp | Wave Crash → Rotom-Wash `1.69` | Dragon Claw → Garchomp `7.58` |
| 15.19 | Glimmora | Incineroar | Wave Crash → Incineroar `12.63` | Stomping Tantrum → Glimmora `70.56` |
| 15.20 | Pelipper | Dragonite | Wave Crash → Pelipper `3.46` | Dragon Claw → Dragonite `6.18` |

---

## 16. My Lead: **Venusaur** [A]  +  **Garchomp** [B] *(mega: Venusaur)*
Bench: Aerodactyl, Kingambit, Sneasler, Basculegion-M

| # | Opp [A] | Opp [B] | Venusaur [A] | Garchomp [B] |
|---|---|---|---|---|
| 16.1 | Incineroar | Sneasler | Earth Power → Incineroar `1.05` | Stomping Tantrum → Sneasler `56.96` |
| 16.2 | Incineroar | Whimsicott | Sludge Bomb → Whimsicott `8.32` | Poison Jab → Whimsicott `11.59` |
| 16.3 | Incineroar | Garchomp | Protect → ? `2.00` | Switch → Basculegion-M `4.35` |
| 16.4 | Incineroar | Farigiraf | Sludge Bomb → Farigiraf `3.27` | Stomping Tantrum → Incineroar `12.51` |
| 16.5 | Incineroar | Kingambit | Earth Power → Kingambit `1.95` | Stomping Tantrum → Incineroar `6.26` |
| 16.6 | Incineroar | Aerodactyl | Giga Drain → Aerodactyl `1.83` | Stomping Tantrum → Incineroar `9.39` |
| 16.7 | Farigiraf | Sneasler | Sludge Bomb → Farigiraf `2.18` | Stomping Tantrum → Sneasler `113.93` |
| 16.8 | Farigiraf | Garchomp | Sludge Bomb → Farigiraf `4.37` | Dragon Claw → Garchomp `15.16` |
| 16.9 | Whimsicott | Garchomp | Sludge Bomb → Whimsicott `12.47` | Dragon Claw → Garchomp `11.37` |
| 16.10 | Whimsicott | Kingambit | Sludge Bomb → Whimsicott `16.63` | Poison Jab → Whimsicott `11.59` |
| 16.11 | Sneasler | Garchomp | Switch → Basculegion-M `1.60` | Stomping Tantrum → Sneasler `28.48` |
| 16.12 | Sneasler | Kingambit | Earth Power → Kingambit `1.30` | Stomping Tantrum → Sneasler `56.96` |
| 16.13 | Aerodactyl | Garchomp | Giga Drain → Aerodactyl `2.74` | Dragon Claw → Garchomp `11.37` |
| 16.14 | Lopunny | Garchomp | Sludge Bomb → Lopunny `0.96` | Dragon Claw → Garchomp `7.58` |
| 16.15 | Weavile | Garchomp | Protect → ? `2.00` | Switch → Kingambit `5.43` |
| 16.16 | Talonflame | Garchomp | Giga Drain → Garchomp `2.24` | Rock Tomb → Talonflame `82.69` |
| 16.17 | Charizard | Incineroar | Earth Power → Incineroar `1.58` | Rock Tomb → Charizard `50.95` |
| 16.18 | Rotom-Wash | Garchomp | Giga Drain → Rotom-Wash `3.05` | Dragon Claw → Garchomp `7.58` |
| 16.19 | Glimmora | Incineroar | Earth Power → Glimmora `13.80` | Stomping Tantrum → Incineroar `6.26` |
| 16.20 | Pelipper | Dragonite | Switch → Kingambit `3.20` | Rock Tomb → Pelipper `8.02` |
