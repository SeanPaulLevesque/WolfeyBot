# Turn 1 First-Turn Decision Summary

Engine v0.45.7 | Turn 1 opening, 100% HP, no field effects, no revealed moves

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
| 1.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `20.00` | Switch → Basculegion `6.78` |
| 1.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `40.00` | Switch → Kingambit `3.20` |
| 1.3 | Incineroar | Garchomp | Ice Fang → Garchomp `20.00` | Switch → Basculegion `6.10` |
| 1.4 | Incineroar | Farigiraf | Rock Tomb → Incineroar `4.91` | Switch → Basculegion `6.10` |
| 1.5 | Incineroar | Kingambit | Protect → ? `6.00` | Switch → Sneasler `6.72` |
| 1.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `6.00` | Switch → Basculegion `9.44` |
| 1.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `40.00` | Sludge Bomb → Farigiraf `1.78` |
| 1.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `80.00` | Sludge Bomb → Farigiraf `3.56` |
| 1.9 | Whimsicott | Garchomp | Ice Fang → Garchomp `80.00` | Sludge Bomb → Whimsicott `6.00` |
| 1.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `80.00` | Earth Power → Kingambit `4.57` |
| 1.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `20.00` | Switch → Basculegion `1.70` |
| 1.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `20.00` | Switch → Sneasler `1.51` |
| 1.13 | Aerodactyl | Garchomp | Ice Fang → Garchomp `60.00` | Giga Drain → Aerodactyl `3.26` |
| 1.14 | Lopunny | Garchomp | Dual Wingbeat → Lopunny `15.00` | Switch → Basculegion `1.19` |
| 1.15 | Weavile | Garchomp | Ice Fang → Garchomp `15.00` | Switch → Kingambit `1.67` |
| 1.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `60.00` | Switch → Basculegion `8.57` |
| 1.17 | Charizard | Incineroar | Rock Tomb → Charizard `15.00` | Switch → Garchomp `6.08` |
| 1.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `40.00` | Giga Drain → Rotom-Wash `2.71` |
| 1.19 | Glimmora | Incineroar | Switch → Garchomp `8.34` | Protect → ? `6.00` |
| 1.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `14.10` | Switch → Basculegion `3.35` |

---

## 2. My Lead: **Aerodactyl** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Kingambit, Sneasler, Basculegion, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Venusaur [B] |
|---|---|---|---|---|
| 2.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `15.00` | Switch → Basculegion `1.60` |
| 2.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `30.00` | Earth Power → Incineroar `2.10` |
| 2.3 | Incineroar | Garchomp | Ice Fang → Garchomp `3.37` | Switch → Basculegion `1.47` |
| 2.4 | Incineroar | Farigiraf | Rock Tomb → Incineroar `4.33` | Sludge Bomb → Farigiraf `3.00` |
| 2.5 | Incineroar | Kingambit | Switch → Sneasler `6.82` | Protect → ? `2.00` |
| 2.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `5.39` | Switch → Basculegion `2.30` |
| 2.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `30.00` | Sludge Bomb → Farigiraf `2.00` |
| 2.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `13.48` | Sludge Bomb → Farigiraf `4.00` |
| 2.9 | Whimsicott | Garchomp | Dual Wingbeat → Whimsicott `60.00` | Giga Drain → Garchomp `2.98` |
| 2.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `60.00` | Earth Power → Kingambit `5.19` |
| 2.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `15.00` | Switch → Basculegion `1.60` |
| 2.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `15.00` | Switch → Sneasler `1.42` |
| 2.13 | Aerodactyl | Garchomp | Ice Fang → Garchomp `10.11` | Giga Drain → Aerodactyl `3.66` |
| 2.14 | Lopunny | Garchomp | Protect → ? `2.00` | Protect → ? `2.00` |
| 2.15 | Weavile | Garchomp | Protect → ? `6.00` | Protect → ? `2.00` |
| 2.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `60.00` | Giga Drain → Garchomp `2.98` |
| 2.17 | Charizard | Incineroar | Rock Tomb → Charizard `15.00` | Earth Power → Incineroar `2.10` |
| 2.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `6.74` | Giga Drain → Rotom-Wash `3.00` |
| 2.19 | Glimmora | Incineroar | Switch → Garchomp `8.60` | Earth Power → Glimmora `2.00` |
| 2.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `12.21` | Switch → Kingambit `3.20` |

---

## 3. My Lead: **Garchomp** [A]  +  **Kingambit** [B]
Bench: Aerodactyl, Sneasler, Basculegion, Venusaur

| # | Opp [A] | Opp [B] | Garchomp [A] | Kingambit [B] |
|---|---|---|---|---|
| 3.1 | Incineroar | Sneasler | Stomping Tantrum → Sneasler `20.00` | Switch → Basculegion `1.62` |
| 3.2 | Incineroar | Whimsicott | Stomping Tantrum → Incineroar `6.26` | Iron Head → Whimsicott `3.00` |
| 3.3 | Incineroar | Garchomp | Switch → Basculegion `4.35` | Protect → ? `2.00` |
| 3.4 | Incineroar | Farigiraf | Stomping Tantrum → Incineroar `6.26` | Kowtow Cleave → Farigiraf `2.43` |
| 3.5 | Incineroar | Kingambit | Stomping Tantrum → Incineroar `3.13` | Low Kick → Kingambit `10.00` |
| 3.6 | Incineroar | Aerodactyl | Stomping Tantrum → Incineroar `6.26` | Iron Head → Aerodactyl `3.00` |
| 3.7 | Farigiraf | Sneasler | Stomping Tantrum → Sneasler `40.00` | Kowtow Cleave → Farigiraf `2.43` |
| 3.8 | Farigiraf | Garchomp | Dragon Claw → Garchomp `15.16` | Kowtow Cleave → Farigiraf `4.86` |
| 3.9 | Whimsicott | Garchomp | Dragon Claw → Garchomp `15.16` | Iron Head → Whimsicott `6.00` |
| 3.10 | Whimsicott | Kingambit | Poison Jab → Whimsicott `16.00` | Low Kick → Kingambit `40.00` |
| 3.11 | Sneasler | Garchomp | Stomping Tantrum → Sneasler `20.00` | Switch → Basculegion `1.62` |
| 3.12 | Sneasler | Kingambit | Stomping Tantrum → Sneasler `20.00` | Low Kick → Kingambit `10.00` |
| 3.13 | Aerodactyl | Garchomp | Dragon Claw → Garchomp `15.16` | Iron Head → Aerodactyl `6.00` |
| 3.14 | Lopunny | Garchomp | Switch → Basculegion `3.40` | Protect → ? `6.00` |
| 3.15 | Weavile | Garchomp | Switch → Basculegion `4.34` | Protect → ? `2.00` |
| 3.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `80.00` | Kowtow Cleave → Garchomp `3.43` |
| 3.17 | Charizard | Incineroar | Rock Tomb → Charizard `20.00` | Switch → Aerodactyl `5.95` |
| 3.18 | Rotom-Wash | Garchomp | Dragon Claw → Garchomp `7.58` | Kowtow Cleave → Rotom-Wash `2.15` |
| 3.19 | Glimmora | Incineroar | Stomping Tantrum → Glimmora `4.00` | Switch → Basculegion `1.36` |
| 3.20 | Pelipper | Dragonite | Dragon Claw → Dragonite `8.24` | Kowtow Cleave → Pelipper `4.19` |

---

## 4. My Lead: **Aerodactyl** [A]  +  **Sneasler** [B] *(mega: Aerodactyl)*
Bench: Kingambit, Basculegion, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Aerodactyl [A] | Sneasler [B] |
|---|---|---|---|---|
| 4.1 | Incineroar | Sneasler | Dual Wingbeat → Sneasler `20.00` | Close Combat → Incineroar `1.88` |
| 4.2 | Incineroar | Whimsicott | Dual Wingbeat → Whimsicott `40.00` | Close Combat → Incineroar `3.77` |
| 4.3 | Incineroar | Garchomp | Ice Fang → Garchomp `20.00` | Close Combat → Incineroar `1.88` |
| 4.4 | Incineroar | Farigiraf | Dual Wingbeat → Farigiraf `4.03` | Close Combat → Incineroar `5.65` |
| 4.5 | Incineroar | Kingambit | Rock Tomb → Incineroar `2.46` | Close Combat → Kingambit `15.00` |
| 4.6 | Incineroar | Aerodactyl | Rock Tomb → Aerodactyl `6.00` | Close Combat → Incineroar `3.77` |
| 4.7 | Farigiraf | Sneasler | Dual Wingbeat → Sneasler `40.00` | Switch → Basculegion `7.61` |
| 4.8 | Farigiraf | Garchomp | Ice Fang → Garchomp `80.00` | Protect → ? `4.50` |
| 4.9 | Whimsicott | Garchomp | Ice Fang → Garchomp `80.00` | Dire Claw → Whimsicott `6.00` |
| 4.10 | Whimsicott | Kingambit | Dual Wingbeat → Whimsicott `80.00` | Close Combat → Kingambit `40.00` |
| 4.11 | Sneasler | Garchomp | Dual Wingbeat → Sneasler `20.00` | Switch → Basculegion `1.83` |
| 4.12 | Sneasler | Kingambit | Dual Wingbeat → Sneasler `20.00` | Close Combat → Kingambit `10.00` |
| 4.13 | Aerodactyl | Garchomp | Ice Fang → Garchomp `60.00` | Close Combat → Aerodactyl `5.30` |
| 4.14 | Lopunny | Garchomp | Ice Fang → Garchomp `15.00` | Close Combat → Lopunny `7.50` |
| 4.15 | Weavile | Garchomp | Ice Fang → Garchomp `15.00` | Close Combat → Weavile `1.50` |
| 4.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `60.00` | Switch → Basculegion `7.02` |
| 4.17 | Charizard | Incineroar | Rock Tomb → Charizard `20.00` | Close Combat → Incineroar `2.83` |
| 4.18 | Rotom-Wash | Garchomp | Ice Fang → Garchomp `40.00` | Close Combat → Rotom-Wash `3.02` |
| 4.19 | Glimmora | Incineroar | Switch → Garchomp `8.34` | Close Combat → Incineroar `2.83` |
| 4.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `14.10` | Rock Tomb → Pelipper `13.21` |

---

## 5. My Lead: **Garchomp** [A]  +  **Venusaur** [B] *(mega: Venusaur)*
Bench: Aerodactyl, Kingambit, Sneasler, Basculegion

| # | Opp [A] | Opp [B] | Garchomp [A] | Venusaur [B] |
|---|---|---|---|---|
| 5.1 | Incineroar | Sneasler | Stomping Tantrum → Sneasler `20.00` | Switch → Basculegion `1.60` |
| 5.2 | Incineroar | Whimsicott | Stomping Tantrum → Incineroar `6.26` | Sludge Bomb → Whimsicott `4.00` |
| 5.3 | Incineroar | Garchomp | Switch → Basculegion `4.35` | Protect → ? `2.00` |
| 5.4 | Incineroar | Farigiraf | Stomping Tantrum → Incineroar `6.26` | Sludge Bomb → Farigiraf `3.00` |
| 5.5 | Incineroar | Kingambit | Stomping Tantrum → Incineroar `3.13` | Earth Power → Kingambit `1.95` |
| 5.6 | Incineroar | Aerodactyl | Stomping Tantrum → Incineroar `6.26` | Giga Drain → Aerodactyl `2.44` |
| 5.7 | Farigiraf | Sneasler | Stomping Tantrum → Sneasler `40.00` | Sludge Bomb → Farigiraf `2.00` |
| 5.8 | Farigiraf | Garchomp | Dragon Claw → Garchomp `15.16` | Sludge Bomb → Farigiraf `4.00` |
| 5.9 | Whimsicott | Garchomp | Dragon Claw → Garchomp `15.16` | Sludge Bomb → Whimsicott `6.00` |
| 5.10 | Whimsicott | Kingambit | Stomping Tantrum → Kingambit `11.13` | Sludge Bomb → Whimsicott `8.00` |
| 5.11 | Sneasler | Garchomp | Stomping Tantrum → Sneasler `20.00` | Switch → Basculegion `1.60` |
| 5.12 | Sneasler | Kingambit | Stomping Tantrum → Sneasler `20.00` | Switch → Sneasler `1.42` |
| 5.13 | Aerodactyl | Garchomp | Dragon Claw → Garchomp `15.16` | Giga Drain → Aerodactyl `3.66` |
| 5.14 | Lopunny | Garchomp | Switch → Basculegion `3.40` | Protect → ? `2.00` |
| 5.15 | Weavile | Garchomp | Switch → Kingambit `5.43` | Protect → ? `2.00` |
| 5.16 | Talonflame | Garchomp | Rock Tomb → Talonflame `80.00` | Giga Drain → Garchomp `2.98` |
| 5.17 | Charizard | Incineroar | Rock Tomb → Charizard `20.00` | Switch → Aerodactyl `1.68` |
| 5.18 | Rotom-Wash | Garchomp | Dragon Claw → Garchomp `7.58` | Giga Drain → Rotom-Wash `3.00` |
| 5.19 | Glimmora | Incineroar | Stomping Tantrum → Incineroar `3.13` | Earth Power → Glimmora `2.00` |
| 5.20 | Pelipper | Dragonite | Rock Tomb → Pelipper `10.70` | Switch → Kingambit `3.20` |

---

## 6. My Lead: **Sneasler** [A]  +  **Kingambit** [B]
Bench: Aerodactyl, Basculegion, Venusaur, Garchomp

| # | Opp [A] | Opp [B] | Sneasler [A] | Kingambit [B] |
|---|---|---|---|---|
| 6.1 | Incineroar | Sneasler | Close Combat → Incineroar `2.83` | Switch → Basculegion `6.48` |
| 6.2 | Incineroar | Whimsicott | Close Combat → Incineroar `5.65` | Iron Head → Whimsicott `3.00` |
| 6.3 | Incineroar | Garchomp | Protect → ? `6.00` | Protect → ? `2.00` |
| 6.4 | Incineroar | Farigiraf | Close Combat → Incineroar `7.54` | Kowtow Cleave → Farigiraf `2.43` |
| 6.5 | Incineroar | Kingambit | Close Combat → Incineroar `3.77` | Low Kick → Kingambit `10.00` |
| 6.6 | Incineroar | Aerodactyl | Close Combat → Incineroar `5.65` | Iron Head → Aerodactyl `3.00` |
| 6.7 | Farigiraf | Sneasler | Switch → Basculegion `7.61` | Protect → ? `6.00` |
| 6.8 | Farigiraf | Garchomp | Switch → Aerodactyl `4.08` | Kowtow Cleave → Farigiraf `4.86` |
| 6.9 | Whimsicott | Garchomp | Switch → Venusaur `4.67` | Iron Head → Whimsicott `6.00` |
| 6.10 | Whimsicott | Kingambit | Close Combat → Kingambit `60.00` | Iron Head → Whimsicott `8.00` |
| 6.11 | Sneasler | Garchomp | Switch → Basculegion `7.34` | Protect → ? `6.00` |
| 6.12 | Sneasler | Kingambit | Close Combat → Kingambit `15.00` | Switch → Garchomp `4.18` |
| 6.13 | Aerodactyl | Garchomp | Switch → Basculegion `8.20` | Iron Head → Aerodactyl `6.00` |
| 6.14 | Lopunny | Garchomp | Protect → ? `6.00` | Protect → ? `6.00` |
| 6.15 | Weavile | Garchomp | Protect → ? `6.00` | Protect → ? `2.00` |
| 6.16 | Talonflame | Garchomp | Switch → Basculegion `7.02` | Kowtow Cleave → Talonflame `4.79` |
| 6.17 | Charizard | Incineroar | Protect → ? `6.00` | Protect → ? `6.00` |
| 6.18 | Rotom-Wash | Garchomp | Switch → Venusaur `3.74` | Kowtow Cleave → Rotom-Wash `2.15` |
| 6.19 | Glimmora | Incineroar | Close Combat → Incineroar `3.77` | Switch → Garchomp `1.60` |
| 6.20 | Pelipper | Dragonite | Rock Tomb → Dragonite `4.47` | Kowtow Cleave → Pelipper `4.19` |
