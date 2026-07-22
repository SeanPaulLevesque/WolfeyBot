# Turn 1 First-Turn Decision Summary

Engine v0.45.5 | Turn 1 opening, 100% HP, no field effects, no revealed moves

> **Joint selection.** Each slot's `(move, target)` candidates are scored
> independently (phase 1); `DecisionEngine.coordinate` then picks the
> highest-value **pair** of actions (phase 2).
> All opponent HP treated as percentage (engine uses typical-spread stats for damage calcs).
> Mega evolution is resolved at turn start — the designated mega uses mega stats/ability.
>
> The phase-2 **joint adjusters** are the only cross-slot effects: *doubling* (both attack the same target → ×0.40–0.70, or ×0.05 overkill when one slot already confirms the OHKO, so the pair that spreads wins); *coordination* (a gratuitous lone Protect beside an attacking partner → ×0.5, favouring double-attack); *fake-out* (the slot absorbing a Fake Out frees its partner); and *switch-collision* (both switching to the same mon → ×0). These cells reflect actual in-game behaviour.

---

## 1. My Lead: **Staraptor** [A]  +  **Kingambit** [B] *(mega: Staraptor)*
Bench: Sneasler, Basculegion-M, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Staraptor [A] | Kingambit [B] |
|---|---|---|---|---|
| 1.1 | Incineroar | Sneasler | Brave Bird → Sneasler `14.85` | Switch → Basculegion-M `6.48` |
| 1.2 | Incineroar | Whimsicott | Close Combat → Incineroar `4.40` | Iron Head → Whimsicott `3.00` |
| 1.3 | Incineroar | Garchomp | Close Combat → Incineroar `2.94` | Switch → Basculegion-M `1.40` |
| 1.4 | Incineroar | Farigiraf | Close Combat → Incineroar `5.87` | Kowtow Cleave → Farigiraf `2.43` |
| 1.5 | Incineroar | Kingambit | Close Combat → Incineroar `2.94` | Low Kick → Kingambit `10.00` |
| 1.6 | Incineroar | Aerodactyl | Close Combat → Incineroar `4.40` | Iron Head → Aerodactyl `3.00` |
| 1.7 | Farigiraf | Sneasler | Brave Bird → Sneasler `29.70` | Switch → Basculegion-M `6.48` |
| 1.8 | Farigiraf | Garchomp | Brave Bird → Garchomp `10.50` | Kowtow Cleave → Farigiraf `4.86` |
| 1.9 | Whimsicott | Garchomp | Brave Bird → Garchomp `7.88` | Iron Head → Whimsicott `6.00` |
| 1.10 | Whimsicott | Kingambit | Close Combat → Kingambit `60.00` | Iron Head → Whimsicott `8.00` |
| 1.11 | Sneasler | Garchomp | Brave Bird → Sneasler `14.85` | Switch → Basculegion-M `6.48` |
| 1.12 | Sneasler | Kingambit | Brave Bird → Sneasler `14.85` | Low Kick → Kingambit `10.00` |
| 1.13 | Aerodactyl | Garchomp | Brave Bird → Garchomp `7.88` | Iron Head → Aerodactyl `6.00` |
| 1.14 | Lopunny | Garchomp | Brave Bird → Lopunny `14.85` | Protect → ? `4.50` |
| 1.15 | Weavile | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 1.16 | Talonflame | Garchomp | Brave Bird → Talonflame `11.16` | Kowtow Cleave → Garchomp `3.43` |
| 1.17 | Charizard | Incineroar | Protect → ? `6.00` | Protect → ? `6.00` |
| 1.18 | Rotom-Wash | Garchomp | Brave Bird → Garchomp `5.25` | Kowtow Cleave → Rotom-Wash `2.15` |
| 1.19 | Glimmora | Incineroar | Switch → Garchomp `7.90` | Protect → ? `2.00` |
| 1.20 | Pelipper | Dragonite | Brave Bird → Pelipper `13.02` | Kowtow Cleave → Dragonite `1.99` |

---

## 2. My Lead: **Staraptor** [A]  +  **Sneasler** [B] *(mega: Staraptor)*
Bench: Kingambit, Basculegion-M, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Staraptor [A] | Sneasler [B] |
|---|---|---|---|---|
| 2.1 | Incineroar | Sneasler | Brave Bird → Sneasler `14.85` | Close Combat → Incineroar `1.88` |
| 2.2 | Incineroar | Whimsicott | Brave Bird → Whimsicott `5.94` | Close Combat → Incineroar `3.77` |
| 2.3 | Incineroar | Garchomp | Close Combat → Incineroar `2.94` | Switch → Basculegion-M `4.37` |
| 2.4 | Incineroar | Farigiraf | Close Combat → Incineroar `5.87` | Switch → Basculegion-M `4.37` |
| 2.5 | Incineroar | Kingambit | Close Combat → Kingambit `20.00` | Close Combat → Incineroar `2.83` |
| 2.6 | Incineroar | Aerodactyl | Steel Wing → Aerodactyl `4.77` | Close Combat → Incineroar `3.77` |
| 2.7 | Farigiraf | Sneasler | Brave Bird → Sneasler `29.70` | Switch → Basculegion-M `7.61` |
| 2.8 | Farigiraf | Garchomp | Brave Bird → Garchomp `10.50` | Switch → Kingambit `3.96` |
| 2.9 | Whimsicott | Garchomp | Brave Bird → Whimsicott `11.88` | Switch → Venusaur `4.67` |
| 2.10 | Whimsicott | Kingambit | Close Combat → Kingambit `60.00` | Dire Claw → Whimsicott `8.00` |
| 2.11 | Sneasler | Garchomp | Brave Bird → Sneasler `14.85` | Switch → Basculegion-M `7.34` |
| 2.12 | Sneasler | Kingambit | Brave Bird → Sneasler `14.85` | Close Combat → Kingambit `10.00` |
| 2.13 | Aerodactyl | Garchomp | Steel Wing → Aerodactyl `9.54` | Switch → Basculegion-M `8.20` |
| 2.14 | Lopunny | Garchomp | Brave Bird → Lopunny `14.85` | Switch → Basculegion-M `3.20` |
| 2.15 | Weavile | Garchomp | Protect → ? `2.00` | Protect → ? `6.00` |
| 2.16 | Talonflame | Garchomp | Brave Bird → Talonflame `11.16` | Switch → Basculegion-M `7.02` |
| 2.17 | Charizard | Incineroar | Protect → ? `6.00` | Protect → ? `6.00` |
| 2.18 | Rotom-Wash | Garchomp | Brave Bird → Garchomp `5.25` | Switch → Venusaur `3.74` |
| 2.19 | Glimmora | Incineroar | Switch → Garchomp `7.90` | Close Combat → Incineroar `2.83` |
| 2.20 | Pelipper | Dragonite | Brave Bird → Pelipper `13.02` | Rock Tomb → Pelipper `13.21` |

---

## 3. My Lead: **Staraptor** [A]  +  **Basculegion-M** [B] *(mega: Staraptor)*
Bench: Kingambit, Sneasler, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Staraptor [A] | Basculegion-M [B] |
|---|---|---|---|---|
| 3.1 | Incineroar | Sneasler | Brave Bird → Sneasler `14.85` | Wave Crash → Incineroar `19.80` |
| 3.2 | Incineroar | Whimsicott | Brave Bird → Whimsicott `5.94` | Wave Crash → Incineroar `39.60` |
| 3.3 | Incineroar | Garchomp | Brave Bird → Garchomp `2.63` | Wave Crash → Incineroar `19.80` |
| 3.4 | Incineroar | Farigiraf | Brave Bird → Farigiraf `4.25` | Wave Crash → Incineroar `59.40` |
| 3.5 | Incineroar | Kingambit | Close Combat → Kingambit `20.00` | Wave Crash → Incineroar `29.70` |
| 3.6 | Incineroar | Aerodactyl | Steel Wing → Aerodactyl `4.77` | Wave Crash → Incineroar `39.60` |
| 3.7 | Farigiraf | Sneasler | Brave Bird → Sneasler `29.70` | Wave Crash → Farigiraf `5.01` |
| 3.8 | Farigiraf | Garchomp | Brave Bird → Farigiraf `8.51` | Wave Crash → Garchomp `6.26` |
| 3.9 | Whimsicott | Garchomp | Brave Bird → Whimsicott `11.88` | Wave Crash → Garchomp `4.69` |
| 3.10 | Whimsicott | Kingambit | Close Combat → Kingambit `60.00` | Wave Crash → Whimsicott `4.87` |
| 3.11 | Sneasler | Garchomp | Brave Bird → Sneasler `14.85` | Wave Crash → Garchomp `2.35` |
| 3.12 | Sneasler | Kingambit | Close Combat → Kingambit `15.00` | Psychic Fangs → Sneasler `20.00` |
| 3.13 | Aerodactyl | Garchomp | Brave Bird → Garchomp `7.88` | Wave Crash → Aerodactyl `5.94` |
| 3.14 | Lopunny | Garchomp | Brave Bird → Lopunny `14.85` | Wave Crash → Garchomp `1.17` |
| 3.15 | Weavile | Garchomp | Close Combat → Weavile `3.00` | Wave Crash → Garchomp `2.35` |
| 3.16 | Talonflame | Garchomp | Brave Bird → Garchomp `7.88` | Wave Crash → Talonflame `29.70` |
| 3.17 | Charizard | Incineroar | Protect → ? `6.00` | Switch → Garchomp `4.04` |
| 3.18 | Rotom-Wash | Garchomp | Close Combat → Rotom-Wash `4.82` | Wave Crash → Garchomp `2.35` |
| 3.19 | Glimmora | Incineroar | Switch → Garchomp `7.90` | Wave Crash → Incineroar `19.80` |
| 3.20 | Pelipper | Dragonite | Brave Bird → Pelipper `13.02` | Wave Crash → Dragonite `2.12` |

---

## 4. My Lead: **Staraptor** [A]  +  **Venusaur** [B] *(mega: Staraptor)*
Bench: Kingambit, Sneasler, Basculegion-M, Garchomp

| # | Opp [A] | Opp [B] | Staraptor [A] | Venusaur [B] |
|---|---|---|---|---|
| 4.1 | Incineroar | Sneasler | Brave Bird → Sneasler `14.85` | Switch → Basculegion-M `6.78` |
| 4.2 | Incineroar | Whimsicott | Brave Bird → Whimsicott `5.94` | Switch → Kingambit `3.20` |
| 4.3 | Incineroar | Garchomp | Close Combat → Incineroar `2.94` | Switch → Basculegion-M `6.10` |
| 4.4 | Incineroar | Farigiraf | Close Combat → Incineroar `5.87` | Switch → Basculegion-M `6.10` |
| 4.5 | Incineroar | Kingambit | Close Combat → Kingambit `20.00` | Switch → Sneasler `6.72` |
| 4.6 | Incineroar | Aerodactyl | Steel Wing → Aerodactyl `4.77` | Switch → Basculegion-M `9.44` |
| 4.7 | Farigiraf | Sneasler | Brave Bird → Sneasler `29.70` | Sludge Bomb → Farigiraf `1.78` |
| 4.8 | Farigiraf | Garchomp | Brave Bird → Garchomp `10.50` | Sludge Bomb → Farigiraf `3.56` |
| 4.9 | Whimsicott | Garchomp | Brave Bird → Garchomp `7.88` | Sludge Bomb → Whimsicott `6.00` |
| 4.10 | Whimsicott | Kingambit | Close Combat → Kingambit `60.00` | Sludge Bomb → Whimsicott `8.00` |
| 4.11 | Sneasler | Garchomp | Brave Bird → Sneasler `14.85` | Switch → Basculegion-M `1.70` |
| 4.12 | Sneasler | Kingambit | Close Combat → Kingambit `15.00` | Switch → Sneasler `1.51` |
| 4.13 | Aerodactyl | Garchomp | Brave Bird → Garchomp `7.88` | Giga Drain → Aerodactyl `3.26` |
| 4.14 | Lopunny | Garchomp | Brave Bird → Lopunny `14.85` | Switch → Basculegion-M `1.19` |
| 4.15 | Weavile | Garchomp | Close Combat → Weavile `3.00` | Switch → Kingambit `1.67` |
| 4.16 | Talonflame | Garchomp | Brave Bird → Talonflame `11.16` | Switch → Basculegion-M `8.57` |
| 4.17 | Charizard | Incineroar | Protect → ? `6.00` | Switch → Garchomp `6.08` |
| 4.18 | Rotom-Wash | Garchomp | Brave Bird → Garchomp `5.25` | Giga Drain → Rotom-Wash `2.71` |
| 4.19 | Glimmora | Incineroar | Switch → Garchomp `7.90` | Protect → ? `6.00` |
| 4.20 | Pelipper | Dragonite | Brave Bird → Pelipper `13.02` | Switch → Basculegion-M `3.35` |

---

## 5. My Lead: **Staraptor** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Kingambit, Sneasler, Basculegion-M, Garchomp

| # | Opp [A] | Opp [B] | Staraptor [A] | Venusaur [B] |
|---|---|---|---|---|
| 5.1 | Incineroar | Sneasler | Brave Bird → Sneasler `14.85` | Switch → Basculegion-M `1.60` |
| 5.2 | Incineroar | Whimsicott | Close Combat → Incineroar `4.02` | Sludge Bomb → Whimsicott `4.00` |
| 5.3 | Incineroar | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 5.4 | Incineroar | Farigiraf | Close Combat → Incineroar `5.36` | Sludge Bomb → Farigiraf `3.00` |
| 5.5 | Incineroar | Kingambit | Close Combat → Kingambit `4.00` | Switch → Sneasler `1.61` |
| 5.6 | Incineroar | Aerodactyl | Steel Wing → Aerodactyl `4.34` | Switch → Basculegion-M `2.30` |
| 5.7 | Farigiraf | Sneasler | Brave Bird → Sneasler `29.70` | Sludge Bomb → Farigiraf `2.00` |
| 5.8 | Farigiraf | Garchomp | Brave Bird → Garchomp `7.15` | Sludge Bomb → Farigiraf `4.00` |
| 5.9 | Whimsicott | Garchomp | Brave Bird → Garchomp `4.77` | Sludge Bomb → Whimsicott `6.00` |
| 5.10 | Whimsicott | Kingambit | Close Combat → Kingambit `12.00` | Sludge Bomb → Whimsicott `8.00` |
| 5.11 | Sneasler | Garchomp | Brave Bird → Sneasler `9.90` | Switch → Basculegion-M `1.60` |
| 5.12 | Sneasler | Kingambit | Brave Bird → Sneasler `14.85` | Switch → Sneasler `1.42` |
| 5.13 | Aerodactyl | Garchomp | Brave Bird → Garchomp `4.77` | Giga Drain → Aerodactyl `3.66` |
| 5.14 | Lopunny | Garchomp | Brave Bird → Lopunny `9.90` | Switch → Basculegion-M `1.12` |
| 5.15 | Weavile | Garchomp | Protect → ? `6.00` | Protect → ? `2.00` |
| 5.16 | Talonflame | Garchomp | Brave Bird → Garchomp `4.77` | Sludge Bomb → Talonflame `4.51` |
| 5.17 | Charizard | Incineroar | Protect → ? `6.00` | Protect → ? `2.00` |
| 5.18 | Rotom-Wash | Garchomp | Switch → Basculegion-M `3.89` | Giga Drain → Rotom-Wash `3.00` |
| 5.19 | Glimmora | Incineroar | Switch → Garchomp `8.13` | Earth Power → Glimmora `2.00` |
| 5.20 | Pelipper | Dragonite | Brave Bird → Pelipper `11.81` | Switch → Kingambit `3.20` |

---

## 6. My Lead: **Staraptor** [A]  +  **Garchomp** [B] *(mega: Staraptor)*
Bench: Kingambit, Sneasler, Basculegion-M, Venusaur

| # | Opp [A] | Opp [B] | Staraptor [A] | Garchomp [B] |
|---|---|---|---|---|
| 6.1 | Incineroar | Sneasler | Brave Bird → Sneasler `9.90` | Stomping Tantrum → Incineroar `3.13` |
| 6.2 | Incineroar | Whimsicott | Brave Bird → Whimsicott `3.96` | Stomping Tantrum → Incineroar `6.26` |
| 6.3 | Incineroar | Garchomp | Close Combat → Incineroar `2.20` | Switch → Basculegion-M `4.35` |
| 6.4 | Incineroar | Farigiraf | Brave Bird → Farigiraf `3.19` | Stomping Tantrum → Incineroar `6.26` |
| 6.5 | Incineroar | Kingambit | Close Combat → Kingambit `15.00` | Stomping Tantrum → Incineroar `3.13` |
| 6.6 | Incineroar | Aerodactyl | Steel Wing → Aerodactyl `3.18` | Stomping Tantrum → Incineroar `6.26` |
| 6.7 | Farigiraf | Sneasler | Brave Bird → Farigiraf `2.13` | Stomping Tantrum → Sneasler `40.00` |
| 6.8 | Farigiraf | Garchomp | Brave Bird → Farigiraf `6.38` | Dragon Claw → Garchomp `15.16` |
| 6.9 | Whimsicott | Garchomp | Brave Bird → Whimsicott `7.92` | Dragon Claw → Garchomp `15.16` |
| 6.10 | Whimsicott | Kingambit | Close Combat → Kingambit `40.00` | Poison Jab → Whimsicott `16.00` |
| 6.11 | Sneasler | Garchomp | Brave Bird → Sneasler `9.90` | Switch → Basculegion-M `4.33` |
| 6.12 | Sneasler | Kingambit | Close Combat → Kingambit `10.00` | Stomping Tantrum → Sneasler `20.00` |
| 6.13 | Aerodactyl | Garchomp | Steel Wing → Aerodactyl `6.36` | Dragon Claw → Garchomp `15.16` |
| 6.14 | Lopunny | Garchomp | Brave Bird → Lopunny `9.90` | Dragon Claw → Garchomp `3.79` |
| 6.15 | Weavile | Garchomp | Close Combat → Weavile `2.00` | Switch → Kingambit `5.43` |
| 6.16 | Talonflame | Garchomp | Brave Bird → Garchomp `5.25` | Rock Tomb → Talonflame `80.00` |
| 6.17 | Charizard | Incineroar | Close Combat → Incineroar `2.20` | Rock Tomb → Charizard `20.00` |
| 6.18 | Rotom-Wash | Garchomp | Close Combat → Rotom-Wash `3.62` | Dragon Claw → Garchomp `7.58` |
| 6.19 | Glimmora | Incineroar | Switch → Basculegion-M `6.93` | Stomping Tantrum → Glimmora `4.00` |
| 6.20 | Pelipper | Dragonite | Brave Bird → Pelipper `9.77` | Rock Tomb → Pelipper `21.39` |

---

## 7. My Lead: **Kingambit** [A]  +  **Sneasler** [B]
Bench: Staraptor, Basculegion-M, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Kingambit [A] | Sneasler [B] |
|---|---|---|---|---|
| 7.1 | Incineroar | Sneasler | Switch → Staraptor `6.48` | Close Combat → Incineroar `2.83` |
| 7.2 | Incineroar | Whimsicott | Iron Head → Whimsicott `3.00` | Close Combat → Incineroar `5.65` |
| 7.3 | Incineroar | Garchomp | Protect → ? `2.00` | Protect → ? `6.00` |
| 7.4 | Incineroar | Farigiraf | Kowtow Cleave → Farigiraf `2.43` | Close Combat → Incineroar `7.54` |
| 7.5 | Incineroar | Kingambit | Low Kick → Kingambit `10.00` | Close Combat → Incineroar `3.77` |
| 7.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `3.00` | Close Combat → Incineroar `5.65` |
| 7.7 | Farigiraf | Sneasler | Switch → Staraptor `6.48` | Switch → Basculegion-M `7.61` |
| 7.8 | Farigiraf | Garchomp | Kowtow Cleave → Farigiraf `4.86` | Switch → Basculegion-M `3.89` |
| 7.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `6.00` | Switch → Venusaur `4.67` |
| 7.10 | Whimsicott | Kingambit | Low Kick → Kingambit `40.00` | Dire Claw → Whimsicott `12.00` |
| 7.11 | Sneasler | Garchomp | Switch → Staraptor `6.48` | Switch → Basculegion-M `7.34` |
| 7.12 | Sneasler | Kingambit | Switch → Staraptor `5.31` | Close Combat → Kingambit `15.00` |
| 7.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `6.00` | Switch → Basculegion-M `8.20` |
| 7.14 | Lopunny | Garchomp | Protect → ? `6.00` | Protect → ? `6.00` |
| 7.15 | Weavile | Garchomp | Protect → ? `2.00` | Protect → ? `6.00` |
| 7.16 | Talonflame | Garchomp | Kowtow Cleave → Talonflame `4.79` | Switch → Basculegion-M `7.02` |
| 7.17 | Charizard | Incineroar | Protect → ? `6.00` | Protect → ? `6.00` |
| 7.18 | Rotom-Wash | Garchomp | Kowtow Cleave → Rotom-Wash `2.15` | Switch → Venusaur `3.74` |
| 7.19 | Glimmora | Incineroar | Switch → Garchomp `1.60` | Close Combat → Incineroar `3.77` |
| 7.20 | Pelipper | Dragonite | Kowtow Cleave → Pelipper `4.19` | Rock Tomb → Dragonite `4.47` |

---

## 8. My Lead: **Kingambit** [A]  +  **Basculegion-M** [B]
Bench: Staraptor, Sneasler, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Kingambit [A] | Basculegion-M [B] |
|---|---|---|---|---|
| 8.1 | Incineroar | Sneasler | Switch → Staraptor `6.48` | Psychic Fangs → Sneasler `30.00` |
| 8.2 | Incineroar | Whimsicott | Iron Head → Whimsicott `3.00` | Wave Crash → Incineroar `59.40` |
| 8.3 | Incineroar | Garchomp | Switch → Staraptor `0.86` | Wave Crash → Incineroar `29.70` |
| 8.4 | Incineroar | Farigiraf | Kowtow Cleave → Farigiraf `2.43` | Wave Crash → Incineroar `79.20` |
| 8.5 | Incineroar | Kingambit | Low Kick → Kingambit `10.00` | Wave Crash → Incineroar `39.60` |
| 8.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `3.00` | Wave Crash → Incineroar `59.40` |
| 8.7 | Farigiraf | Sneasler | Switch → Staraptor `6.48` | Psychic Fangs → Sneasler `60.00` |
| 8.8 | Farigiraf | Garchomp | Kowtow Cleave → Farigiraf `4.86` | Wave Crash → Garchomp `9.39` |
| 8.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `6.00` | Wave Crash → Garchomp `6.26` |
| 8.10 | Whimsicott | Kingambit | Low Kick → Kingambit `40.00` | Wave Crash → Whimsicott `7.31` |
| 8.11 | Sneasler | Garchomp | Switch → Staraptor `6.48` | Psychic Fangs → Sneasler `20.00` |
| 8.12 | Sneasler | Kingambit | Low Kick → Kingambit `10.00` | Psychic Fangs → Sneasler `30.00` |
| 8.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `6.00` | Wave Crash → Garchomp `6.26` |
| 8.14 | Lopunny | Garchomp | Protect → ? `6.00` | Protect → ? `2.00` |
| 8.15 | Weavile | Garchomp | Iron Head → Weavile `1.50` | Wave Crash → Garchomp `3.13` |
| 8.16 | Talonflame | Garchomp | Kowtow Cleave → Garchomp `3.43` | Wave Crash → Talonflame `39.60` |
| 8.17 | Charizard | Incineroar | Switch → Garchomp `5.11` | Wave Crash → Charizard `5.94` |
| 8.18 | Rotom-Wash | Garchomp | Kowtow Cleave → Rotom-Wash `2.15` | Wave Crash → Garchomp `3.13` |
| 8.19 | Glimmora | Incineroar | Switch → Garchomp `1.60` | Wave Crash → Incineroar `29.70` |
| 8.20 | Pelipper | Dragonite | Kowtow Cleave → Dragonite `1.99` | Wave Crash → Pelipper `6.09` |

---

## 9. My Lead: **Kingambit** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Staraptor, Sneasler, Basculegion-M, Garchomp

| # | Opp [A] | Opp [B] | Kingambit [A] | Venusaur [B] |
|---|---|---|---|---|
| 9.1 | Incineroar | Sneasler | Switch → Staraptor `6.48` | Earth Power → Sneasler `2.57` |
| 9.2 | Incineroar | Whimsicott | Low Kick → Incineroar `1.82` | Sludge Bomb → Whimsicott `6.00` |
| 9.3 | Incineroar | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 9.4 | Incineroar | Farigiraf | Kowtow Cleave → Farigiraf `2.43` | Earth Power → Incineroar `4.21` |
| 9.5 | Incineroar | Kingambit | Low Kick → Kingambit `10.00` | Earth Power → Incineroar `2.10` |
| 9.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `3.00` | Earth Power → Incineroar `3.15` |
| 9.7 | Farigiraf | Sneasler | Switch → Staraptor `6.48` | Earth Power → Sneasler `5.14` |
| 9.8 | Farigiraf | Garchomp | Kowtow Cleave → Farigiraf `4.86` | Giga Drain → Garchomp `5.96` |
| 9.9 | Whimsicott | Garchomp | Kowtow Cleave → Garchomp `3.43` | Sludge Bomb → Whimsicott `8.00` |
| 9.10 | Whimsicott | Kingambit | Low Kick → Kingambit `40.00` | Sludge Bomb → Whimsicott `12.00` |
| 9.11 | Sneasler | Garchomp | Switch → Staraptor `6.48` | Protect → ? `2.00` |
| 9.12 | Sneasler | Kingambit | Low Kick → Kingambit `10.00` | Earth Power → Sneasler `2.57` |
| 9.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `6.00` | Giga Drain → Garchomp `3.98` |
| 9.14 | Lopunny | Garchomp | Protect → ? `6.00` | Protect → ? `2.00` |
| 9.15 | Weavile | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 9.16 | Talonflame | Garchomp | Kowtow Cleave → Garchomp `3.43` | Sludge Bomb → Talonflame `6.01` |
| 9.17 | Charizard | Incineroar | Protect → ? `6.00` | Protect → ? `2.00` |
| 9.18 | Rotom-Wash | Garchomp | Kowtow Cleave → Garchomp `1.71` | Giga Drain → Rotom-Wash `4.00` |
| 9.19 | Glimmora | Incineroar | Switch → Garchomp `1.60` | Earth Power → Glimmora `3.00` |
| 9.20 | Pelipper | Dragonite | Kowtow Cleave → Pelipper `4.19` | Switch → Basculegion-M `3.20` |

---

## 10. My Lead: **Kingambit** [A]  +  **Garchomp** [B]
Bench: Staraptor, Sneasler, Basculegion-M, Venusaur

| # | Opp [A] | Opp [B] | Kingambit [A] | Garchomp [B] |
|---|---|---|---|---|
| 10.1 | Incineroar | Sneasler | Switch → Staraptor `1.62` | Stomping Tantrum → Sneasler `20.00` |
| 10.2 | Incineroar | Whimsicott | Iron Head → Whimsicott `3.00` | Stomping Tantrum → Incineroar `6.26` |
| 10.3 | Incineroar | Garchomp | Protect → ? `2.00` | Switch → Basculegion-M `4.35` |
| 10.4 | Incineroar | Farigiraf | Kowtow Cleave → Farigiraf `2.43` | Stomping Tantrum → Incineroar `6.26` |
| 10.5 | Incineroar | Kingambit | Low Kick → Kingambit `10.00` | Stomping Tantrum → Incineroar `3.13` |
| 10.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `3.00` | Stomping Tantrum → Incineroar `6.26` |
| 10.7 | Farigiraf | Sneasler | Kowtow Cleave → Farigiraf `2.43` | Stomping Tantrum → Sneasler `40.00` |
| 10.8 | Farigiraf | Garchomp | Kowtow Cleave → Farigiraf `4.86` | Dragon Claw → Garchomp `15.16` |
| 10.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `6.00` | Dragon Claw → Garchomp `15.16` |
| 10.10 | Whimsicott | Kingambit | Low Kick → Kingambit `40.00` | Poison Jab → Whimsicott `16.00` |
| 10.11 | Sneasler | Garchomp | Switch → Staraptor `1.62` | Stomping Tantrum → Sneasler `20.00` |
| 10.12 | Sneasler | Kingambit | Low Kick → Kingambit `10.00` | Stomping Tantrum → Sneasler `20.00` |
| 10.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `6.00` | Dragon Claw → Garchomp `15.16` |
| 10.14 | Lopunny | Garchomp | Protect → ? `6.00` | Switch → Staraptor `4.82` |
| 10.15 | Weavile | Garchomp | Protect → ? `2.00` | Switch → Basculegion-M `4.34` |
| 10.16 | Talonflame | Garchomp | Kowtow Cleave → Garchomp `3.43` | Rock Tomb → Talonflame `80.00` |
| 10.17 | Charizard | Incineroar | Protect → ? `4.50` | Rock Tomb → Charizard `20.00` |
| 10.18 | Rotom-Wash | Garchomp | Kowtow Cleave → Rotom-Wash `2.15` | Dragon Claw → Garchomp `7.58` |
| 10.19 | Glimmora | Incineroar | Switch → Basculegion-M `1.36` | Stomping Tantrum → Glimmora `4.00` |
| 10.20 | Pelipper | Dragonite | Kowtow Cleave → Pelipper `4.19` | Dragon Claw → Dragonite `8.24` |

---

## 11. My Lead: **Sneasler** [A]  +  **Basculegion-M** [B]
Bench: Staraptor, Kingambit, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Sneasler [A] | Basculegion-M [B] |
|---|---|---|---|---|
| 11.1 | Incineroar | Sneasler | Close Combat → Incineroar `2.83` | Psychic Fangs → Sneasler `20.00` |
| 11.2 | Incineroar | Whimsicott | Dire Claw → Whimsicott `6.00` | Wave Crash → Incineroar `39.60` |
| 11.3 | Incineroar | Garchomp | Switch → Staraptor `3.20` | Wave Crash → Incineroar `19.80` |
| 11.4 | Incineroar | Farigiraf | Close Combat → Farigiraf `3.91` | Wave Crash → Incineroar `59.40` |
| 11.5 | Incineroar | Kingambit | Close Combat → Kingambit `20.00` | Wave Crash → Incineroar `29.70` |
| 11.6 | Incineroar | Aerodactyl | Close Combat → Aerodactyl `5.30` | Wave Crash → Incineroar `39.60` |
| 11.7 | Farigiraf | Sneasler | Switch → Staraptor `7.61` | Psychic Fangs → Sneasler `40.00` |
| 11.8 | Farigiraf | Garchomp | Switch → Kingambit `3.96` | Wave Crash → Garchomp `6.26` |
| 11.9 | Whimsicott | Garchomp | Switch → Venusaur `4.67` | Wave Crash → Garchomp `4.69` |
| 11.10 | Whimsicott | Kingambit | Close Combat → Kingambit `60.00` | Wave Crash → Whimsicott `4.87` |
| 11.11 | Sneasler | Garchomp | Switch → Staraptor `7.34` | Psychic Fangs → Sneasler `15.00` |
| 11.12 | Sneasler | Kingambit | Close Combat → Kingambit `15.00` | Psychic Fangs → Sneasler `20.00` |
| 11.13 | Aerodactyl | Garchomp | Switch → Kingambit `5.29` | Wave Crash → Aerodactyl `5.94` |
| 11.14 | Lopunny | Garchomp | Protect → ? `6.00` | Protect → ? `2.00` |
| 11.15 | Weavile | Garchomp | Switch → Kingambit `3.20` | Wave Crash → Weavile `2.97` |
| 11.16 | Talonflame | Garchomp | Protect → ? `4.50` | Wave Crash → Talonflame `29.70` |
| 11.17 | Charizard | Incineroar | Protect → ? `6.00` | Switch → Garchomp `4.04` |
| 11.18 | Rotom-Wash | Garchomp | Switch → Venusaur `3.74` | Wave Crash → Garchomp `2.35` |
| 11.19 | Glimmora | Incineroar | Close Combat → Glimmora `2.82` | Wave Crash → Incineroar `19.80` |
| 11.20 | Pelipper | Dragonite | Rock Tomb → Dragonite `4.47` | Wave Crash → Pelipper `4.57` |

---

## 12. My Lead: **Sneasler** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Staraptor, Kingambit, Basculegion-M, Garchomp

| # | Opp [A] | Opp [B] | Sneasler [A] | Venusaur [B] |
|---|---|---|---|---|
| 12.1 | Incineroar | Sneasler | Close Combat → Incineroar `2.83` | Earth Power → Sneasler `1.71` |
| 12.2 | Incineroar | Whimsicott | Close Combat → Incineroar `5.65` | Sludge Bomb → Whimsicott `4.00` |
| 12.3 | Incineroar | Garchomp | Protect → ? `6.00` | Protect → ? `2.00` |
| 12.4 | Incineroar | Farigiraf | Close Combat → Incineroar `7.54` | Sludge Bomb → Farigiraf `3.00` |
| 12.5 | Incineroar | Kingambit | Close Combat → Kingambit `20.00` | Earth Power → Incineroar `1.58` |
| 12.6 | Incineroar | Aerodactyl | Close Combat → Incineroar `5.65` | Giga Drain → Aerodactyl `2.44` |
| 12.7 | Farigiraf | Sneasler | Switch → Staraptor `7.61` | Earth Power → Sneasler `3.43` |
| 12.8 | Farigiraf | Garchomp | Switch → Kingambit `3.96` | Sludge Bomb → Farigiraf `4.00` |
| 12.9 | Whimsicott | Garchomp | Switch → Staraptor `3.20` | Sludge Bomb → Whimsicott `6.00` |
| 12.10 | Whimsicott | Kingambit | Close Combat → Kingambit `60.00` | Sludge Bomb → Whimsicott `8.00` |
| 12.11 | Sneasler | Garchomp | Switch → Staraptor `7.34` | Protect → ? `2.00` |
| 12.12 | Sneasler | Kingambit | Close Combat → Kingambit `15.00` | Earth Power → Sneasler `1.71` |
| 12.13 | Aerodactyl | Garchomp | Switch → Basculegion-M `8.20` | Giga Drain → Aerodactyl `3.66` |
| 12.14 | Lopunny | Garchomp | Protect → ? `6.00` | Protect → ? `2.00` |
| 12.15 | Weavile | Garchomp | Protect → ? `6.00` | Protect → ? `2.00` |
| 12.16 | Talonflame | Garchomp | Switch → Basculegion-M `7.02` | Sludge Bomb → Talonflame `4.51` |
| 12.17 | Charizard | Incineroar | Protect → ? `6.00` | Protect → ? `2.00` |
| 12.18 | Rotom-Wash | Garchomp | Switch → Basculegion-M `3.32` | Giga Drain → Rotom-Wash `3.00` |
| 12.19 | Glimmora | Incineroar | Close Combat → Incineroar `3.77` | Earth Power → Glimmora `2.00` |
| 12.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `8.81` | Switch → Kingambit `3.20` |

---

## 13. My Lead: **Sneasler** [A]  +  **Garchomp** [B]
Bench: Staraptor, Kingambit, Basculegion-M, Venusaur

| # | Opp [A] | Opp [B] | Sneasler [A] | Garchomp [B] |
|---|---|---|---|---|
| 13.1 | Incineroar | Sneasler | Close Combat → Incineroar `1.88` | Stomping Tantrum → Sneasler `20.00` |
| 13.2 | Incineroar | Whimsicott | Close Combat → Incineroar `3.77` | Poison Jab → Whimsicott `8.00` |
| 13.3 | Incineroar | Garchomp | Protect → ? `6.00` | Switch → Basculegion-M `4.35` |
| 13.4 | Incineroar | Farigiraf | Switch → Basculegion-M `4.37` | Stomping Tantrum → Incineroar `6.26` |
| 13.5 | Incineroar | Kingambit | Close Combat → Kingambit `15.00` | Stomping Tantrum → Incineroar `3.13` |
| 13.6 | Incineroar | Aerodactyl | Close Combat → Incineroar `3.77` | Rock Tomb → Aerodactyl `6.28` |
| 13.7 | Farigiraf | Sneasler | Switch → Staraptor `7.61` | Stomping Tantrum → Sneasler `40.00` |
| 13.8 | Farigiraf | Garchomp | Switch → Kingambit `3.96` | Dragon Claw → Garchomp `15.16` |
| 13.9 | Whimsicott | Garchomp | Switch → Venusaur `4.67` | Poison Jab → Whimsicott `16.00` |
| 13.10 | Whimsicott | Kingambit | Close Combat → Kingambit `40.00` | Poison Jab → Whimsicott `16.00` |
| 13.11 | Sneasler | Garchomp | Switch → Staraptor `7.34` | Stomping Tantrum → Sneasler `20.00` |
| 13.12 | Sneasler | Kingambit | Close Combat → Kingambit `10.00` | Stomping Tantrum → Sneasler `20.00` |
| 13.13 | Aerodactyl | Garchomp | Switch → Basculegion-M `8.20` | Dragon Claw → Garchomp `15.16` |
| 13.14 | Lopunny | Garchomp | Protect → ? `6.00` | Switch → Staraptor `4.82` |
| 13.15 | Weavile | Garchomp | Protect → ? `6.00` | Switch → Kingambit `5.43` |
| 13.16 | Talonflame | Garchomp | Switch → Basculegion-M `7.02` | Rock Tomb → Talonflame `80.00` |
| 13.17 | Charizard | Incineroar | Close Combat → Incineroar `2.83` | Rock Tomb → Charizard `20.00` |
| 13.18 | Rotom-Wash | Garchomp | Switch → Venusaur `3.74` | Dragon Claw → Garchomp `7.58` |
| 13.19 | Glimmora | Incineroar | Close Combat → Incineroar `2.83` | Stomping Tantrum → Glimmora `4.00` |
| 13.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `6.60` | Rock Tomb → Pelipper `21.39` |

---

## 14. My Lead: **Basculegion-M** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Staraptor, Kingambit, Sneasler, Garchomp

| # | Opp [A] | Opp [B] | Basculegion-M [A] | Venusaur [B] |
|---|---|---|---|---|
| 14.1 | Incineroar | Sneasler | Wave Crash → Incineroar `19.80` | Earth Power → Sneasler `2.57` |
| 14.2 | Incineroar | Whimsicott | Wave Crash → Incineroar `39.60` | Sludge Bomb → Whimsicott `6.00` |
| 14.3 | Incineroar | Garchomp | Wave Crash → Incineroar `19.80` | Giga Drain → Garchomp `1.49` |
| 14.4 | Incineroar | Farigiraf | Wave Crash → Incineroar `59.40` | Sludge Bomb → Farigiraf `4.00` |
| 14.5 | Incineroar | Kingambit | Wave Crash → Incineroar `5.94` | Earth Power → Kingambit `2.60` |
| 14.6 | Incineroar | Aerodactyl | Wave Crash → Incineroar `39.60` | Giga Drain → Aerodactyl `3.66` |
| 14.7 | Farigiraf | Sneasler | Psychic Fangs → Sneasler `40.00` | Sludge Bomb → Farigiraf `3.00` |
| 14.8 | Farigiraf | Garchomp | Wave Crash → Garchomp `6.26` | Sludge Bomb → Farigiraf `6.00` |
| 14.9 | Whimsicott | Garchomp | Wave Crash → Garchomp `4.69` | Sludge Bomb → Whimsicott `8.00` |
| 14.10 | Whimsicott | Kingambit | Switch → Sneasler `8.23` | Sludge Bomb → Whimsicott `12.00` |
| 14.11 | Sneasler | Garchomp | Psychic Fangs → Sneasler `15.00` | Switch → Staraptor `1.60` |
| 14.12 | Sneasler | Kingambit | Switch → Staraptor `3.20` | Earth Power → Sneasler `2.57` |
| 14.13 | Aerodactyl | Garchomp | Wave Crash → Aerodactyl `5.94` | Giga Drain → Garchomp `3.98` |
| 14.14 | Lopunny | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 14.15 | Weavile | Garchomp | Wave Crash → Weavile `2.97` | Switch → Kingambit `1.60` |
| 14.16 | Talonflame | Garchomp | Wave Crash → Talonflame `29.70` | Giga Drain → Garchomp `3.98` |
| 14.17 | Charizard | Incineroar | Switch → Garchomp `4.04` | Sludge Bomb → Charizard `2.15` |
| 14.18 | Rotom-Wash | Garchomp | Wave Crash → Garchomp `2.35` | Giga Drain → Rotom-Wash `4.00` |
| 14.19 | Glimmora | Incineroar | Wave Crash → Incineroar `19.80` | Earth Power → Glimmora `3.00` |
| 14.20 | Pelipper | Dragonite | Wave Crash → Pelipper `4.57` | Switch → Kingambit `3.20` |

---

## 15. My Lead: **Basculegion-M** [A]  +  **Garchomp** [B]
Bench: Staraptor, Kingambit, Sneasler, Venusaur

| # | Opp [A] | Opp [B] | Basculegion-M [A] | Garchomp [B] |
|---|---|---|---|---|
| 15.1 | Incineroar | Sneasler | Wave Crash → Incineroar `19.80` | Stomping Tantrum → Sneasler `20.00` |
| 15.2 | Incineroar | Whimsicott | Wave Crash → Incineroar `39.60` | Poison Jab → Whimsicott `8.00` |
| 15.3 | Incineroar | Garchomp | Wave Crash → Incineroar `19.80` | Dragon Claw → Garchomp `3.79` |
| 15.4 | Incineroar | Farigiraf | Wave Crash → Incineroar `59.40` | Dragon Claw → Farigiraf `3.50` |
| 15.5 | Incineroar | Kingambit | Wave Crash → Incineroar `5.94` | Stomping Tantrum → Kingambit `2.78` |
| 15.6 | Incineroar | Aerodactyl | Wave Crash → Incineroar `39.60` | Rock Tomb → Aerodactyl `6.28` |
| 15.7 | Farigiraf | Sneasler | Wave Crash → Farigiraf `5.01` | Stomping Tantrum → Sneasler `40.00` |
| 15.8 | Farigiraf | Garchomp | Wave Crash → Farigiraf `5.01` | Dragon Claw → Garchomp `15.16` |
| 15.9 | Whimsicott | Garchomp | Wave Crash → Garchomp `4.69` | Poison Jab → Whimsicott `16.00` |
| 15.10 | Whimsicott | Kingambit | Switch → Venusaur `9.69` | Poison Jab → Whimsicott `16.00` |
| 15.11 | Sneasler | Garchomp | Psychic Fangs → Sneasler `15.00` | Switch → Staraptor `4.33` |
| 15.12 | Sneasler | Kingambit | Switch → Staraptor `3.20` | Stomping Tantrum → Sneasler `20.00` |
| 15.13 | Aerodactyl | Garchomp | Wave Crash → Aerodactyl `5.94` | Dragon Claw → Garchomp `15.16` |
| 15.14 | Lopunny | Garchomp | Protect → ? `2.00` | Switch → Staraptor `4.82` |
| 15.15 | Weavile | Garchomp | Wave Crash → Weavile `2.97` | Switch → Kingambit `5.43` |
| 15.16 | Talonflame | Garchomp | Wave Crash → Talonflame `29.70` | Dragon Claw → Garchomp `15.16` |
| 15.17 | Charizard | Incineroar | Wave Crash → Incineroar `2.72` | Rock Tomb → Charizard `20.00` |
| 15.18 | Rotom-Wash | Garchomp | Wave Crash → Rotom-Wash `1.68` | Dragon Claw → Garchomp `7.58` |
| 15.19 | Glimmora | Incineroar | Wave Crash → Incineroar `19.80` | Stomping Tantrum → Glimmora `4.00` |
| 15.20 | Pelipper | Dragonite | Wave Crash → Pelipper `4.57` | Dragon Claw → Dragonite `8.24` |

---

## 16. My Lead: **Venusaur** [A]  +  **Garchomp** [B] *(mega: Venusaur)*
Bench: Staraptor, Kingambit, Sneasler, Basculegion-M

| # | Opp [A] | Opp [B] | Venusaur [A] | Garchomp [B] |
|---|---|---|---|---|
| 16.1 | Incineroar | Sneasler | Switch → Staraptor `1.60` | Stomping Tantrum → Sneasler `20.00` |
| 16.2 | Incineroar | Whimsicott | Sludge Bomb → Whimsicott `4.00` | Stomping Tantrum → Incineroar `6.26` |
| 16.3 | Incineroar | Garchomp | Protect → ? `2.00` | Switch → Basculegion-M `4.35` |
| 16.4 | Incineroar | Farigiraf | Sludge Bomb → Farigiraf `3.00` | Stomping Tantrum → Incineroar `6.26` |
| 16.5 | Incineroar | Kingambit | Earth Power → Kingambit `1.95` | Stomping Tantrum → Incineroar `3.13` |
| 16.6 | Incineroar | Aerodactyl | Giga Drain → Aerodactyl `2.44` | Stomping Tantrum → Incineroar `6.26` |
| 16.7 | Farigiraf | Sneasler | Sludge Bomb → Farigiraf `2.00` | Stomping Tantrum → Sneasler `40.00` |
| 16.8 | Farigiraf | Garchomp | Sludge Bomb → Farigiraf `4.00` | Dragon Claw → Garchomp `15.16` |
| 16.9 | Whimsicott | Garchomp | Sludge Bomb → Whimsicott `6.00` | Dragon Claw → Garchomp `15.16` |
| 16.10 | Whimsicott | Kingambit | Sludge Bomb → Whimsicott `8.00` | Stomping Tantrum → Kingambit `11.13` |
| 16.11 | Sneasler | Garchomp | Switch → Staraptor `1.60` | Stomping Tantrum → Sneasler `20.00` |
| 16.12 | Sneasler | Kingambit | Switch → Staraptor `1.60` | Stomping Tantrum → Sneasler `20.00` |
| 16.13 | Aerodactyl | Garchomp | Giga Drain → Aerodactyl `3.66` | Dragon Claw → Garchomp `15.16` |
| 16.14 | Lopunny | Garchomp | Protect → ? `2.00` | Switch → Staraptor `4.82` |
| 16.15 | Weavile | Garchomp | Protect → ? `2.00` | Switch → Kingambit `5.43` |
| 16.16 | Talonflame | Garchomp | Giga Drain → Garchomp `2.98` | Rock Tomb → Talonflame `80.00` |
| 16.17 | Charizard | Incineroar | Earth Power → Incineroar `1.58` | Rock Tomb → Charizard `20.00` |
| 16.18 | Rotom-Wash | Garchomp | Giga Drain → Rotom-Wash `3.00` | Dragon Claw → Garchomp `7.58` |
| 16.19 | Glimmora | Incineroar | Earth Power → Glimmora `2.00` | Stomping Tantrum → Incineroar `3.13` |
| 16.20 | Pelipper | Dragonite | Switch → Kingambit `3.20` | Rock Tomb → Pelipper `10.70` |
