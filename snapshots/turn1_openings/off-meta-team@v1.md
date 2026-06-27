# Turn 1 First-Turn Decision Summary

Engine v0.31.0 | Turn 1 opening, 100% HP, no field effects, no revealed moves

> **Joint selection.** Each slot's `(move, target)` candidates are scored
> independently (phase 1); `DecisionEngine.coordinate` then picks the
> highest-value **pair** of actions (phase 2).
> All opponent HP treated as percentage (engine uses typical-spread stats for damage calcs).
> Mega evolution is resolved at turn start — the designated mega uses mega stats/ability.
>
> The phase-2 **joint adjusters** are the only cross-slot effects: *doubling* (both attack the same target → ×0.40–0.70, or ×0.05 overkill when one slot already confirms the OHKO, so the pair that spreads wins); *coordination* (a gratuitous lone Protect beside an attacking partner → ×0.5, favouring double-attack); *fake-out* (the slot absorbing a Fake Out frees its partner); and *switch-collision* (both switching to the same mon → ×0). These cells reflect actual in-game behaviour.

---

## 1. My Lead: **Gallade** [A]  +  **Arcanine-Hisui** [B]
Bench: Aegislash, Basculegion, Dragonite, Pelipper

| # | Opp [A] | Opp [B] | Gallade [A] | Arcanine-Hisui [B] |
|---|---|---|---|---|
| 1.1 | Incineroar | Sneasler | Psycho Cut → Sneasler `33.42` | Protect → ? `7.50` |
| 1.2 | Incineroar | Whimsicott | Sacred Sword → Incineroar `23.18` | Flare Blitz → Whimsicott `19.51` |
| 1.3 | Incineroar | Garchomp | Sacred Sword → Incineroar `11.59` | Switch → Basculegion `4.69` |
| 1.4 | Incineroar | Farigiraf | Sacred Sword → Farigiraf `4.47` | Head Smash → Incineroar `96.55` |
| 1.5 | Incineroar | Kingambit | Sacred Sword → Kingambit `3.05` | Head Smash → Incineroar `48.27` |
| 1.6 | Incineroar | Aerodactyl | Switch → Basculegion `9.68` | Head Smash → Incineroar `36.21` |
| 1.7 | Farigiraf | Sneasler | Psycho Cut → Sneasler `66.84` | Protect → ? `7.50` |
| 1.8 | Farigiraf | Garchomp | Sacred Sword → Farigiraf `5.96` | Switch → Pelipper `4.49` |
| 1.9 | Whimsicott | Garchomp | Sacred Sword → Garchomp `4.40` | Extreme Speed → Whimsicott `3.69` |
| 1.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `8.13` | Flare Blitz → Whimsicott `19.51` |
| 1.11 | Sneasler | Garchomp | Psycho Cut → Sneasler `25.06` | Protect → ? `7.50` |
| 1.12 | Sneasler | Kingambit | Psycho Cut → Sneasler `33.42` | Protect → ? `7.50` |
| 1.13 | Aerodactyl | Garchomp | Switch → Basculegion `9.93` | Head Smash → Aerodactyl `3.43` |
| 1.14 | Lopunny | Garchomp | Sacred Sword → Lopunny `12.33` | Protect → ? `7.50` |
| 1.15 | Weavile | Garchomp | Sacred Sword → Weavile `6.37` | Switch → Aegislash `3.20` |
| 1.16 | Talonflame | Garchomp | Switch → Basculegion `10.30` | Head Smash → Talonflame `31.75` |
| 1.17 | Charizard | Incineroar | Sacred Sword → Incineroar `11.59` | Head Smash → Charizard `110.90` |
| 1.18 | Rotom-Wash | Garchomp | Leaf Blade → Rotom-Wash `23.91` | Protect → ? `7.50` |
| 1.19 | Glimmora | Incineroar | Psycho Cut → Glimmora `11.37` | Protect → ? `7.50` |
| 1.20 | Pelipper | Dragonite | Psycho Cut → Dragonite `2.77` | Head Smash → Pelipper `28.28` |

---

## 2. My Lead: **Gallade** [A]  +  **Aegislash** [B]
Bench: Arcanine-Hisui, Basculegion, Dragonite, Pelipper

| # | Opp [A] | Opp [B] | Gallade [A] | Aegislash [B] |
|---|---|---|---|---|
| 2.1 | Incineroar | Sneasler | Psycho Cut → Sneasler `50.13` | Switch → Basculegion `1.58` |
| 2.2 | Incineroar | Whimsicott | Sacred Sword → Incineroar `34.76` | Iron Head → Whimsicott `4.86` |
| 2.3 | Incineroar | Garchomp | Sacred Sword → Incineroar `17.38` | Switch → Basculegion `1.81` |
| 2.4 | Incineroar | Farigiraf | Sacred Sword → Incineroar `46.35` | Iron Head → Farigiraf `2.88` |
| 2.5 | Incineroar | Kingambit | Sacred Sword → Incineroar `23.18` | Sacred Sword → Kingambit `1.53` |
| 2.6 | Incineroar | Aerodactyl | Sacred Sword → Incineroar `6.95` | Iron Head → Aerodactyl `5.20` |
| 2.7 | Farigiraf | Sneasler | Psycho Cut → Sneasler `100.26` | Iron Head → Farigiraf `2.88` |
| 2.8 | Farigiraf | Garchomp | Sacred Sword → Farigiraf `8.94` | Poltergeist → Garchomp `4.04` |
| 2.9 | Whimsicott | Garchomp | Sacred Sword → Garchomp `5.87` | Iron Head → Whimsicott `4.86` |
| 2.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `12.20` | Iron Head → Whimsicott `6.48` |
| 2.11 | Sneasler | Garchomp | Psycho Cut → Sneasler `33.42` | Switch → Basculegion `1.57` |
| 2.12 | Sneasler | Kingambit | Psycho Cut → Sneasler `50.13` | Sacred Sword → Kingambit `1.53` |
| 2.13 | Aerodactyl | Garchomp | Switch → Basculegion `9.93` | Iron Head → Aerodactyl `5.20` |
| 2.14 | Lopunny | Garchomp | Sacred Sword → Lopunny `16.45` | Poltergeist → Garchomp `1.52` |
| 2.15 | Weavile | Garchomp | Sacred Sword → Weavile `8.49` | Sacred Sword → Weavile `1.58` |
| 2.16 | Talonflame | Garchomp | Switch → Basculegion `10.30` | Poltergeist → Talonflame `4.17` |
| 2.17 | Charizard | Incineroar | Sacred Sword → Incineroar `17.38` | Switch → Arcanine-Hisui `14.31` |
| 2.18 | Rotom-Wash | Garchomp | Leaf Blade → Rotom-Wash `35.87` | Poltergeist → Garchomp `1.52` |
| 2.19 | Glimmora | Incineroar | Sacred Sword → Incineroar `17.38` | Switch → Basculegion `2.07` |
| 2.20 | Pelipper | Dragonite | Psycho Cut → Pelipper `8.94` | Poltergeist → Dragonite `1.82` |

---

## 3. My Lead: **Gallade** [A]  +  **Basculegion** [B]
Bench: Arcanine-Hisui, Aegislash, Dragonite, Pelipper

| # | Opp [A] | Opp [B] | Gallade [A] | Basculegion [B] |
|---|---|---|---|---|
| 3.1 | Incineroar | Sneasler | Psycho Cut → Sneasler `50.13` | Wave Crash → Incineroar `32.31` |
| 3.2 | Incineroar | Whimsicott | Psycho Cut → Whimsicott `4.93` | Wave Crash → Incineroar `64.62` |
| 3.3 | Incineroar | Garchomp | Sacred Sword → Garchomp `2.20` | Wave Crash → Incineroar `32.31` |
| 3.4 | Incineroar | Farigiraf | Sacred Sword → Farigiraf `5.96` | Wave Crash → Incineroar `96.93` |
| 3.5 | Incineroar | Kingambit | Sacred Sword → Incineroar `23.18` | Switch → Aegislash `3.20` |
| 3.6 | Incineroar | Aerodactyl | Switch → Arcanine-Hisui `6.81` | Wave Crash → Incineroar `32.31` |
| 3.7 | Farigiraf | Sneasler | Psycho Cut → Sneasler `100.26` | Wave Crash → Farigiraf `8.13` |
| 3.8 | Farigiraf | Garchomp | Sacred Sword → Farigiraf `8.94` | Wave Crash → Garchomp `8.07` |
| 3.9 | Whimsicott | Garchomp | Psycho Cut → Whimsicott `6.58` | Wave Crash → Garchomp `6.05` |
| 3.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `12.20` | Switch → Pelipper `5.75` |
| 3.11 | Sneasler | Garchomp | Psycho Cut → Sneasler `33.42` | Wave Crash → Garchomp `3.03` |
| 3.12 | Sneasler | Kingambit | Psycho Cut → Sneasler `50.13` | Switch → Aegislash `3.20` |
| 3.13 | Aerodactyl | Garchomp | Switch → Pelipper `3.32` | Wave Crash → Aerodactyl `17.58` |
| 3.14 | Lopunny | Garchomp | Sacred Sword → Lopunny `16.45` | Wave Crash → Garchomp `3.03` |
| 3.15 | Weavile | Garchomp | Sacred Sword → Weavile `8.49` | Switch → Aegislash `3.20` |
| 3.16 | Talonflame | Garchomp | Protect → ? `7.50` | Wave Crash → Talonflame `83.33` |
| 3.17 | Charizard | Incineroar | Sacred Sword → Incineroar `17.38` | Wave Crash → Charizard `27.15` |
| 3.18 | Rotom-Wash | Garchomp | Leaf Blade → Rotom-Wash `35.87` | Wave Crash → Garchomp `3.03` |
| 3.19 | Glimmora | Incineroar | Sacred Sword → Incineroar `17.38` | Wave Crash → Glimmora `40.14` |
| 3.20 | Pelipper | Dragonite | Psycho Cut → Dragonite `4.16` | Wave Crash → Pelipper `5.89` |

---

## 4. My Lead: **Gallade** [A]  +  **Dragonite** [B] *(mega: Dragonite)*
Bench: Arcanine-Hisui, Aegislash, Basculegion, Pelipper

| # | Opp [A] | Opp [B] | Gallade [A] | Dragonite [B] |
|---|---|---|---|---|
| 4.1 | Incineroar | Sneasler | Sacred Sword → Incineroar `11.59` | Air Slash → Sneasler `34.68` |
| 4.2 | Incineroar | Whimsicott | Sacred Sword → Incineroar `23.18` | Air Slash → Whimsicott `16.39` |
| 4.3 | Incineroar | Garchomp | Sacred Sword → Incineroar `11.59` | Dragon Pulse → Garchomp `6.42` |
| 4.4 | Incineroar | Farigiraf | Sacred Sword → Incineroar `34.76` | Dragon Pulse → Farigiraf `9.07` |
| 4.5 | Incineroar | Kingambit | Sacred Sword → Incineroar `17.38` | Dragon Pulse → Kingambit `2.63` |
| 4.6 | Incineroar | Aerodactyl | Switch → Basculegion `9.68` | Dragon Pulse → Aerodactyl `4.40` |
| 4.7 | Farigiraf | Sneasler | Psycho Cut → Sneasler `66.84` | Dragon Pulse → Farigiraf `6.81` |
| 4.8 | Farigiraf | Garchomp | Sacred Sword → Farigiraf `5.96` | Dragon Pulse → Garchomp `12.84` |
| 4.9 | Whimsicott | Garchomp | Sacred Sword → Garchomp `4.40` | Air Slash → Whimsicott `10.93` |
| 4.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `8.13` | Air Slash → Whimsicott `16.39` |
| 4.11 | Sneasler | Garchomp | Psycho Cut → Sneasler `25.06` | Dragon Pulse → Garchomp `4.28` |
| 4.12 | Sneasler | Kingambit | Sacred Sword → Kingambit `2.03` | Air Slash → Sneasler `34.68` |
| 4.13 | Aerodactyl | Garchomp | Switch → Basculegion `9.93` | Dragon Pulse → Garchomp `8.56` |
| 4.14 | Lopunny | Garchomp | Sacred Sword → Lopunny `12.33` | Dragon Pulse → Garchomp `4.28` |
| 4.15 | Weavile | Garchomp | Sacred Sword → Weavile `6.37` | Dragon Pulse → Garchomp `4.28` |
| 4.16 | Talonflame | Garchomp | Switch → Basculegion `10.30` | Dragon Pulse → Garchomp `8.56` |
| 4.17 | Charizard | Incineroar | Sacred Sword → Incineroar `11.59` | Dragon Pulse → Charizard `4.51` |
| 4.18 | Rotom-Wash | Garchomp | Leaf Blade → Rotom-Wash `23.91` | Dragon Pulse → Garchomp `6.42` |
| 4.19 | Glimmora | Incineroar | Sacred Sword → Incineroar `11.59` | Dragon Pulse → Glimmora `3.69` |
| 4.20 | Pelipper | Dragonite | Psycho Cut → Pelipper `5.96` | Dragon Pulse → Dragonite `8.01` |

---

## 5. My Lead: **Gallade** [A]  +  **Pelipper** [B]
Bench: Arcanine-Hisui, Aegislash, Basculegion, Dragonite

| # | Opp [A] | Opp [B] | Gallade [A] | Pelipper [B] |
|---|---|---|---|---|
| 5.1 | Incineroar | Sneasler | Sacred Sword → Incineroar `11.59` | Hurricane → Sneasler `49.95` |
| 5.2 | Incineroar | Whimsicott | Sacred Sword → Incineroar `23.18` | Hurricane → Whimsicott `23.55` |
| 5.3 | Incineroar | Garchomp | Sacred Sword → Incineroar `11.59` | Ice Beam → Garchomp `44.90` |
| 5.4 | Incineroar | Farigiraf | Sacred Sword → Incineroar `34.76` | Weather Ball → Farigiraf `11.30` |
| 5.5 | Incineroar | Kingambit | Sacred Sword → Incineroar `17.38` | Weather Ball → Kingambit `5.35` |
| 5.6 | Incineroar | Aerodactyl | Switch → Basculegion `14.80` | Weather Ball → Aerodactyl `10.46` |
| 5.7 | Farigiraf | Sneasler | Psycho Cut → Sneasler `66.84` | Weather Ball → Farigiraf `11.30` |
| 5.8 | Farigiraf | Garchomp | Sacred Sword → Farigiraf `5.96` | Ice Beam → Garchomp `89.80` |
| 5.9 | Whimsicott | Garchomp | Psycho Cut → Whimsicott `4.93` | Ice Beam → Garchomp `89.80` |
| 5.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `8.13` | Hurricane → Whimsicott `23.55` |
| 5.11 | Sneasler | Garchomp | Psycho Cut → Sneasler `25.06` | Ice Beam → Garchomp `44.90` |
| 5.12 | Sneasler | Kingambit | Psycho Cut → Sneasler `33.42` | Weather Ball → Kingambit `5.35` |
| 5.13 | Aerodactyl | Garchomp | Switch → Basculegion `15.06` | Ice Beam → Garchomp `67.35` |
| 5.14 | Lopunny | Garchomp | Sacred Sword → Lopunny `12.33` | Ice Beam → Garchomp `33.68` |
| 5.15 | Weavile | Garchomp | Sacred Sword → Weavile `6.37` | Ice Beam → Garchomp `33.68` |
| 5.16 | Talonflame | Garchomp | Switch → Basculegion `15.12` | Weather Ball → Talonflame `111.52` |
| 5.17 | Charizard | Incineroar | Sacred Sword → Incineroar `11.59` | Weather Ball → Charizard `50.53` |
| 5.18 | Rotom-Wash | Garchomp | Leaf Blade → Rotom-Wash `23.91` | Ice Beam → Garchomp `44.90` |
| 5.19 | Glimmora | Incineroar | Sacred Sword → Incineroar `11.59` | Weather Ball → Glimmora `56.40` |
| 5.20 | Pelipper | Dragonite | Psycho Cut → Pelipper `5.96` | Ice Beam → Dragonite `8.48` |

---

## 6. My Lead: **Arcanine-Hisui** [A]  +  **Aegislash** [B]
Bench: Gallade, Basculegion, Dragonite, Pelipper

| # | Opp [A] | Opp [B] | Arcanine-Hisui [A] | Aegislash [B] |
|---|---|---|---|---|
| 6.1 | Incineroar | Sneasler | Switch → Gallade `11.01` | King's Shield → ? `2.00` |
| 6.2 | Incineroar | Whimsicott | Head Smash → Incineroar `36.21` | Iron Head → Whimsicott `4.86` |
| 6.3 | Incineroar | Garchomp | Protect → ? `5.00` | King's Shield → ? `2.00` |
| 6.4 | Incineroar | Farigiraf | Head Smash → Incineroar `48.27` | Iron Head → Farigiraf `2.88` |
| 6.5 | Incineroar | Kingambit | Head Smash → Incineroar `24.14` | Sacred Sword → Kingambit `1.53` |
| 6.6 | Incineroar | Aerodactyl | Head Smash → Incineroar `36.21` | Iron Head → Aerodactyl `5.20` |
| 6.7 | Farigiraf | Sneasler | Switch → Gallade `11.80` | Poltergeist → Sneasler `3.06` |
| 6.8 | Farigiraf | Garchomp | Switch → Pelipper `4.49` | Poltergeist → Garchomp `4.04` |
| 6.9 | Whimsicott | Garchomp | Switch → Gallade `3.20` | Iron Head → Whimsicott `4.86` |
| 6.10 | Whimsicott | Kingambit | Flare Blitz → Kingambit `10.51` | Iron Head → Whimsicott `6.48` |
| 6.11 | Sneasler | Garchomp | Switch → Gallade `11.80` | King's Shield → ? `2.00` |
| 6.12 | Sneasler | Kingambit | Switch → Gallade `11.80` | King's Shield → ? `2.00` |
| 6.13 | Aerodactyl | Garchomp | Switch → Basculegion `6.07` | Iron Head → Aerodactyl `5.20` |
| 6.14 | Lopunny | Garchomp | Switch → Gallade `6.40` | King's Shield → ? `2.00` |
| 6.15 | Weavile | Garchomp | Switch → Gallade `10.37` | King's Shield → ? `2.00` |
| 6.16 | Talonflame | Garchomp | Head Smash → Talonflame `31.75` | Poltergeist → Garchomp `3.03` |
| 6.17 | Charizard | Incineroar | Head Smash → Charizard `55.45` | King's Shield → ? `7.50` |
| 6.18 | Rotom-Wash | Garchomp | Switch → Gallade `4.04` | Poltergeist → Rotom-Wash `1.89` |
| 6.19 | Glimmora | Incineroar | Switch → Basculegion `6.13` | King's Shield → ? `2.00` |
| 6.20 | Pelipper | Dragonite | Head Smash → Pelipper `28.28` | Poltergeist → Dragonite `1.82` |

---

## 7. My Lead: **Arcanine-Hisui** [A]  +  **Basculegion** [B]
Bench: Gallade, Aegislash, Dragonite, Pelipper

| # | Opp [A] | Opp [B] | Arcanine-Hisui [A] | Basculegion [B] |
|---|---|---|---|---|
| 7.1 | Incineroar | Sneasler | Switch → Gallade `11.01` | Wave Crash → Incineroar `16.16` |
| 7.2 | Incineroar | Whimsicott | Flare Blitz → Whimsicott `9.75` | Wave Crash → Incineroar `64.62` |
| 7.3 | Incineroar | Garchomp | Switch → Gallade `3.20` | Wave Crash → Incineroar `16.16` |
| 7.4 | Incineroar | Farigiraf | Head Smash → Farigiraf `6.16` | Wave Crash → Incineroar `96.93` |
| 7.5 | Incineroar | Kingambit | Head Smash → Incineroar `24.14` | Switch → Gallade `3.20` |
| 7.6 | Incineroar | Aerodactyl | Head Smash → Incineroar `36.21` | Wave Crash → Aerodactyl `23.44` |
| 7.7 | Farigiraf | Sneasler | Switch → Gallade `11.80` | Wave Crash → Sneasler `32.19` |
| 7.8 | Farigiraf | Garchomp | Switch → Pelipper `4.49` | Wave Crash → Farigiraf `8.13` |
| 7.9 | Whimsicott | Garchomp | Extreme Speed → Whimsicott `3.69` | Wave Crash → Garchomp `6.05` |
| 7.10 | Whimsicott | Kingambit | Flare Blitz → Whimsicott `19.51` | Switch → Pelipper `5.75` |
| 7.11 | Sneasler | Garchomp | Switch → Gallade `11.80` | Wave Crash → Sneasler `12.07` |
| 7.12 | Sneasler | Kingambit | Switch → Gallade `11.80` | Protect → ? `5.00` |
| 7.13 | Aerodactyl | Garchomp | Switch → Aegislash `3.20` | Wave Crash → Aerodactyl `17.58` |
| 7.14 | Lopunny | Garchomp | Protect → ? `7.50` | Wave Crash → Lopunny `9.20` |
| 7.15 | Weavile | Garchomp | Protect → ? `5.00` | Switch → Gallade `12.78` |
| 7.16 | Talonflame | Garchomp | Switch → Aegislash `3.20` | Wave Crash → Talonflame `83.33` |
| 7.17 | Charizard | Incineroar | Head Smash → Incineroar `18.10` | Wave Crash → Charizard `27.15` |
| 7.18 | Rotom-Wash | Garchomp | Switch → Gallade `4.04` | Wave Crash → Garchomp `3.03` |
| 7.19 | Glimmora | Incineroar | Protect → ? `7.50` | Wave Crash → Glimmora `20.07` |
| 7.20 | Pelipper | Dragonite | Head Smash → Pelipper `28.28` | Wave Crash → Dragonite `2.60` |

---

## 8. My Lead: **Arcanine-Hisui** [A]  +  **Dragonite** [B] *(mega: Dragonite)*
Bench: Gallade, Aegislash, Basculegion, Pelipper

| # | Opp [A] | Opp [B] | Arcanine-Hisui [A] | Dragonite [B] |
|---|---|---|---|---|
| 8.1 | Incineroar | Sneasler | Switch → Gallade `11.01` | Air Slash → Sneasler `17.34` |
| 8.2 | Incineroar | Whimsicott | Head Smash → Incineroar `24.14` | Air Slash → Whimsicott `16.39` |
| 8.3 | Incineroar | Garchomp | Head Smash → Incineroar `2.41` | Dragon Pulse → Garchomp `6.42` |
| 8.4 | Incineroar | Farigiraf | Head Smash → Incineroar `36.21` | Dragon Pulse → Farigiraf `9.07` |
| 8.5 | Incineroar | Kingambit | Head Smash → Incineroar `18.10` | Dragon Pulse → Kingambit `2.63` |
| 8.6 | Incineroar | Aerodactyl | Head Smash → Incineroar `24.14` | Dragon Pulse → Aerodactyl `8.80` |
| 8.7 | Farigiraf | Sneasler | Switch → Gallade `11.80` | Air Slash → Sneasler `34.68` |
| 8.8 | Farigiraf | Garchomp | Switch → Pelipper `4.49` | Dragon Pulse → Garchomp `12.84` |
| 8.9 | Whimsicott | Garchomp | Switch → Gallade `3.20` | Air Slash → Whimsicott `10.93` |
| 8.10 | Whimsicott | Kingambit | Flare Blitz → Kingambit `7.01` | Air Slash → Whimsicott `16.39` |
| 8.11 | Sneasler | Garchomp | Switch → Gallade `11.80` | Air Slash → Sneasler `11.56` |
| 8.12 | Sneasler | Kingambit | Switch → Gallade `11.80` | Air Slash → Sneasler `17.34` |
| 8.13 | Aerodactyl | Garchomp | Switch → Basculegion `6.07` | Dragon Pulse → Garchomp `8.56` |
| 8.14 | Lopunny | Garchomp | Protect → ? `7.50` | Air Slash → Lopunny `10.83` |
| 8.15 | Weavile | Garchomp | Switch → Gallade `10.37` | Dragon Pulse → Garchomp `2.14` |
| 8.16 | Talonflame | Garchomp | Head Smash → Talonflame `23.81` | Dragon Pulse → Garchomp `8.56` |
| 8.17 | Charizard | Incineroar | Head Smash → Charizard `36.97` | Dragon Pulse → Incineroar `3.53` |
| 8.18 | Rotom-Wash | Garchomp | Switch → Gallade `4.04` | Dragon Pulse → Garchomp `6.42` |
| 8.19 | Glimmora | Incineroar | Switch → Basculegion `6.13` | Protect → ? `2.00` |
| 8.20 | Pelipper | Dragonite | Head Smash → Pelipper `21.21` | Dragon Pulse → Dragonite `8.01` |

---

## 9. My Lead: **Arcanine-Hisui** [A]  +  **Pelipper** [B]
Bench: Gallade, Aegislash, Basculegion, Dragonite

| # | Opp [A] | Opp [B] | Arcanine-Hisui [A] | Pelipper [B] |
|---|---|---|---|---|
| 9.1 | Incineroar | Sneasler | Head Smash → Incineroar `12.07` | Hurricane → Sneasler `49.95` |
| 9.2 | Incineroar | Whimsicott | Head Smash → Incineroar `24.14` | Hurricane → Whimsicott `23.55` |
| 9.3 | Incineroar | Garchomp | Head Smash → Incineroar `12.07` | Ice Beam → Garchomp `44.90` |
| 9.4 | Incineroar | Farigiraf | Head Smash → Incineroar `36.21` | Weather Ball → Farigiraf `11.30` |
| 9.5 | Incineroar | Kingambit | Head Smash → Incineroar `18.10` | Weather Ball → Kingambit `5.35` |
| 9.6 | Incineroar | Aerodactyl | Head Smash → Incineroar `24.14` | Weather Ball → Aerodactyl `20.92` |
| 9.7 | Farigiraf | Sneasler | Head Smash → Farigiraf `3.08` | Hurricane → Sneasler `99.91` |
| 9.8 | Farigiraf | Garchomp | Head Smash → Farigiraf `6.16` | Ice Beam → Garchomp `89.80` |
| 9.9 | Whimsicott | Garchomp | Head Smash → Whimsicott `6.39` | Ice Beam → Garchomp `89.80` |
| 9.10 | Whimsicott | Kingambit | Flare Blitz → Kingambit `4.00` | Hurricane → Whimsicott `23.55` |
| 9.11 | Sneasler | Garchomp | Switch → Gallade `3.25` | Hurricane → Sneasler `24.98` |
| 9.12 | Sneasler | Kingambit | Switch → Gallade `13.00` | Hurricane → Sneasler `24.98` |
| 9.13 | Aerodactyl | Garchomp | Head Smash → Aerodactyl `12.88` | Ice Beam → Garchomp `67.35` |
| 9.14 | Lopunny | Garchomp | Switch → Basculegion `7.79` | Hurricane → Lopunny `17.40` |
| 9.15 | Weavile | Garchomp | Head Smash → Weavile `3.42` | Ice Beam → Garchomp `33.68` |
| 9.16 | Talonflame | Garchomp | Head Smash → Talonflame `119.05` | Ice Beam → Garchomp `67.35` |
| 9.17 | Charizard | Incineroar | Head Smash → Incineroar `12.07` | Weather Ball → Charizard `50.53` |
| 9.18 | Rotom-Wash | Garchomp | Protect → ? `7.50` | Ice Beam → Garchomp `44.90` |
| 9.19 | Glimmora | Incineroar | Head Smash → Incineroar `12.07` | Weather Ball → Glimmora `56.40` |
| 9.20 | Pelipper | Dragonite | Head Smash → Pelipper `21.21` | Ice Beam → Dragonite `8.48` |

---

## 10. My Lead: **Aegislash** [A]  +  **Basculegion** [B]
Bench: Gallade, Arcanine-Hisui, Dragonite, Pelipper

| # | Opp [A] | Opp [B] | Aegislash [A] | Basculegion [B] |
|---|---|---|---|---|
| 10.1 | Incineroar | Sneasler | Switch → Gallade `3.16` | Wave Crash → Incineroar `24.23` |
| 10.2 | Incineroar | Whimsicott | Iron Head → Whimsicott `2.43` | Wave Crash → Incineroar `96.93` |
| 10.3 | Incineroar | Garchomp | Poltergeist → Garchomp `0.76` | Wave Crash → Incineroar `48.47` |
| 10.4 | Incineroar | Farigiraf | Iron Head → Farigiraf `1.44` | Wave Crash → Incineroar `129.24` |
| 10.5 | Incineroar | Kingambit | King's Shield → ? `2.00` | Protect → ? `5.00` |
| 10.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `2.60` | Wave Crash → Incineroar `96.93` |
| 10.7 | Farigiraf | Sneasler | Switch → Gallade `3.16` | Wave Crash → Sneasler `48.29` |
| 10.8 | Farigiraf | Garchomp | Poltergeist → Garchomp `4.04` | Wave Crash → Farigiraf `12.20` |
| 10.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `4.86` | Wave Crash → Garchomp `8.07` |
| 10.10 | Whimsicott | Kingambit | Iron Head → Whimsicott `6.48` | Switch → Pelipper `5.75` |
| 10.11 | Sneasler | Garchomp | Switch → Gallade `3.16` | Wave Crash → Sneasler `16.10` |
| 10.12 | Sneasler | Kingambit | King's Shield → ? `2.00` | Switch → Gallade `9.53` |
| 10.13 | Aerodactyl | Garchomp | Poltergeist → Garchomp `3.03` | Wave Crash → Aerodactyl `23.44` |
| 10.14 | Lopunny | Garchomp | Switch → Gallade `1.79` | Wave Crash → Lopunny `12.26` |
| 10.15 | Weavile | Garchomp | King's Shield → ? `2.00` | Switch → Gallade `12.78` |
| 10.16 | Talonflame | Garchomp | Poltergeist → Garchomp `3.03` | Wave Crash → Talonflame `111.11` |
| 10.17 | Charizard | Incineroar | Switch → Arcanine-Hisui `14.31` | Wave Crash → Charizard `20.36` |
| 10.18 | Rotom-Wash | Garchomp | Poltergeist → Rotom-Wash `1.89` | Wave Crash → Garchomp `4.04` |
| 10.19 | Glimmora | Incineroar | Iron Head → Glimmora `0.93` | Wave Crash → Incineroar `48.47` |
| 10.20 | Pelipper | Dragonite | Poltergeist → Dragonite `1.82` | Wave Crash → Pelipper `7.85` |

---

## 11. My Lead: **Aegislash** [A]  +  **Dragonite** [B] *(mega: Dragonite)*
Bench: Gallade, Arcanine-Hisui, Basculegion, Pelipper

| # | Opp [A] | Opp [B] | Aegislash [A] | Dragonite [B] |
|---|---|---|---|---|
| 11.1 | Incineroar | Sneasler | Switch → Gallade `3.16` | Air Slash → Sneasler `17.34` |
| 11.2 | Incineroar | Whimsicott | Sacred Sword → Incineroar `1.26` | Air Slash → Whimsicott `16.39` |
| 11.3 | Incineroar | Garchomp | Switch → Basculegion `1.81` | Dragon Pulse → Garchomp `3.21` |
| 11.4 | Incineroar | Farigiraf | Sacred Sword → Incineroar `1.69` | Dragon Pulse → Farigiraf `9.07` |
| 11.5 | Incineroar | Kingambit | King's Shield → ? `2.00` | Protect → ? `2.00` |
| 11.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `2.60` | Dragon Pulse → Incineroar `5.30` |
| 11.7 | Farigiraf | Sneasler | Switch → Gallade `3.16` | Air Slash → Sneasler `34.68` |
| 11.8 | Farigiraf | Garchomp | Iron Head → Farigiraf `2.88` | Dragon Pulse → Garchomp `12.84` |
| 11.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `4.86` | Dragon Pulse → Garchomp `8.56` |
| 11.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `3.06` | Air Slash → Whimsicott `16.39` |
| 11.11 | Sneasler | Garchomp | Switch → Gallade `3.16` | Air Slash → Sneasler `11.56` |
| 11.12 | Sneasler | Kingambit | Switch → Gallade `3.16` | Air Slash → Sneasler `17.34` |
| 11.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `5.20` | Dragon Pulse → Garchomp `8.56` |
| 11.14 | Lopunny | Garchomp | Switch → Gallade `1.79` | Air Slash → Lopunny `10.83` |
| 11.15 | Weavile | Garchomp | Sacred Sword → Weavile `1.97` | Dragon Pulse → Garchomp `4.28` |
| 11.16 | Talonflame | Garchomp | Poltergeist → Talonflame `4.17` | Dragon Pulse → Garchomp `8.56` |
| 11.17 | Charizard | Incineroar | Switch → Arcanine-Hisui `14.31` | Dragon Pulse → Charizard `2.25` |
| 11.18 | Rotom-Wash | Garchomp | Poltergeist → Rotom-Wash `1.89` | Dragon Pulse → Garchomp `6.42` |
| 11.19 | Glimmora | Incineroar | King's Shield → ? `2.00` | Switch → Basculegion `2.07` |
| 11.20 | Pelipper | Dragonite | Poltergeist → Pelipper `3.73` | Dragon Pulse → Dragonite `8.01` |

---

## 12. My Lead: **Aegislash** [A]  +  **Pelipper** [B]
Bench: Gallade, Arcanine-Hisui, Basculegion, Dragonite

| # | Opp [A] | Opp [B] | Aegislash [A] | Pelipper [B] |
|---|---|---|---|---|
| 12.1 | Incineroar | Sneasler | Switch → Gallade `3.16` | Hurricane → Sneasler `24.98` |
| 12.2 | Incineroar | Whimsicott | Iron Head → Whimsicott `2.43` | Weather Ball → Incineroar `15.46` |
| 12.3 | Incineroar | Garchomp | Switch → Basculegion `2.49` | Ice Beam → Garchomp `22.45` |
| 12.4 | Incineroar | Farigiraf | Iron Head → Farigiraf `1.44` | Weather Ball → Incineroar `15.46` |
| 12.5 | Incineroar | Kingambit | Sacred Sword → Kingambit `0.77` | Weather Ball → Incineroar `7.73` |
| 12.6 | Incineroar | Aerodactyl | Switch → Basculegion `3.97` | Weather Ball → Aerodactyl `10.46` |
| 12.7 | Farigiraf | Sneasler | Switch → Gallade `3.16` | Hurricane → Sneasler `49.95` |
| 12.8 | Farigiraf | Garchomp | Iron Head → Farigiraf `2.88` | Ice Beam → Garchomp `89.80` |
| 12.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `4.86` | Ice Beam → Garchomp `89.80` |
| 12.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `3.06` | Hurricane → Whimsicott `23.55` |
| 12.11 | Sneasler | Garchomp | Switch → Gallade `3.16` | Hurricane → Sneasler `24.98` |
| 12.12 | Sneasler | Kingambit | Switch → Gallade `3.16` | Hurricane → Sneasler `24.98` |
| 12.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `5.20` | Ice Beam → Garchomp `67.35` |
| 12.14 | Lopunny | Garchomp | Switch → Basculegion `1.91` | Hurricane → Lopunny `17.40` |
| 12.15 | Weavile | Garchomp | Sacred Sword → Weavile `1.97` | Ice Beam → Garchomp `33.68` |
| 12.16 | Talonflame | Garchomp | Switch → Basculegion `3.91` | Weather Ball → Talonflame `111.52` |
| 12.17 | Charizard | Incineroar | Sacred Sword → Incineroar `0.63` | Weather Ball → Charizard `50.53` |
| 12.18 | Rotom-Wash | Garchomp | Poltergeist → Rotom-Wash `1.89` | Ice Beam → Garchomp `44.90` |
| 12.19 | Glimmora | Incineroar | Switch → Basculegion `2.92` | Weather Ball → Glimmora `28.20` |
| 12.20 | Pelipper | Dragonite | Poltergeist → Pelipper `3.73` | Ice Beam → Dragonite `8.48` |

---

## 13. My Lead: **Basculegion** [A]  +  **Dragonite** [B] *(mega: Dragonite)*
Bench: Gallade, Arcanine-Hisui, Aegislash, Pelipper

| # | Opp [A] | Opp [B] | Basculegion [A] | Dragonite [B] |
|---|---|---|---|---|
| 13.1 | Incineroar | Sneasler | Wave Crash → Incineroar `16.16` | Air Slash → Sneasler `34.68` |
| 13.2 | Incineroar | Whimsicott | Wave Crash → Incineroar `32.31` | Air Slash → Whimsicott `16.39` |
| 13.3 | Incineroar | Garchomp | Wave Crash → Incineroar `16.16` | Dragon Pulse → Garchomp `6.42` |
| 13.4 | Incineroar | Farigiraf | Wave Crash → Incineroar `48.47` | Dragon Pulse → Farigiraf `9.07` |
| 13.5 | Incineroar | Kingambit | Wave Crash → Incineroar `4.85` | Dragon Pulse → Kingambit `2.63` |
| 13.6 | Incineroar | Aerodactyl | Wave Crash → Incineroar `32.31` | Dragon Pulse → Aerodactyl `8.80` |
| 13.7 | Farigiraf | Sneasler | Wave Crash → Farigiraf `4.07` | Air Slash → Sneasler `69.36` |
| 13.8 | Farigiraf | Garchomp | Wave Crash → Farigiraf `8.13` | Dragon Pulse → Garchomp `12.84` |
| 13.9 | Whimsicott | Garchomp | Wave Crash → Garchomp `6.05` | Air Slash → Whimsicott `10.93` |
| 13.10 | Whimsicott | Kingambit | Switch → Pelipper `5.75` | Air Slash → Whimsicott `16.39` |
| 13.11 | Sneasler | Garchomp | Wave Crash → Sneasler `12.07` | Dragon Pulse → Garchomp `4.28` |
| 13.12 | Sneasler | Kingambit | Switch → Gallade `9.53` | Air Slash → Sneasler `17.34` |
| 13.13 | Aerodactyl | Garchomp | Wave Crash → Aerodactyl `17.58` | Dragon Pulse → Garchomp `8.56` |
| 13.14 | Lopunny | Garchomp | Wave Crash → Lopunny `9.20` | Dragon Pulse → Garchomp `4.28` |
| 13.15 | Weavile | Garchomp | Switch → Gallade `12.78` | Dragon Pulse → Garchomp `2.14` |
| 13.16 | Talonflame | Garchomp | Wave Crash → Talonflame `83.33` | Dragon Pulse → Garchomp `8.56` |
| 13.17 | Charizard | Incineroar | Wave Crash → Charizard `13.57` | Switch → Arcanine-Hisui `3.66` |
| 13.18 | Rotom-Wash | Garchomp | Wave Crash → Rotom-Wash `2.11` | Dragon Pulse → Garchomp `6.42` |
| 13.19 | Glimmora | Incineroar | Wave Crash → Incineroar `16.16` | Dragon Pulse → Glimmora `3.69` |
| 13.20 | Pelipper | Dragonite | Wave Crash → Pelipper `5.89` | Dragon Pulse → Dragonite `8.01` |

---

## 14. My Lead: **Basculegion** [A]  +  **Pelipper** [B]
Bench: Gallade, Arcanine-Hisui, Aegislash, Dragonite

| # | Opp [A] | Opp [B] | Basculegion [A] | Pelipper [B] |
|---|---|---|---|---|
| 14.1 | Incineroar | Sneasler | Wave Crash → Incineroar `23.53` | Hurricane → Sneasler `49.95` |
| 14.2 | Incineroar | Whimsicott | Wave Crash → Incineroar `47.06` | Hurricane → Whimsicott `23.55` |
| 14.3 | Incineroar | Garchomp | Wave Crash → Incineroar `23.53` | Ice Beam → Garchomp `44.90` |
| 14.4 | Incineroar | Farigiraf | Wave Crash → Farigiraf `87.51` | Weather Ball → Incineroar `15.46` |
| 14.5 | Incineroar | Kingambit | Wave Crash → Incineroar `7.06` | Weather Ball → Kingambit `5.35` |
| 14.6 | Incineroar | Aerodactyl | Wave Crash → Incineroar `47.06` | Weather Ball → Aerodactyl `20.92` |
| 14.7 | Farigiraf | Sneasler | Wave Crash → Farigiraf `58.34` | Hurricane → Sneasler `99.91` |
| 14.8 | Farigiraf | Garchomp | Wave Crash → Farigiraf `116.68` | Ice Beam → Garchomp `89.80` |
| 14.9 | Whimsicott | Garchomp | Wave Crash → Garchomp `43.39` | Hurricane → Whimsicott `23.55` |
| 14.10 | Whimsicott | Kingambit | Wave Crash → Kingambit `8.76` | Hurricane → Whimsicott `23.55` |
| 14.11 | Sneasler | Garchomp | Wave Crash → Sneasler `17.64` | Ice Beam → Garchomp `44.90` |
| 14.12 | Sneasler | Kingambit | Switch → Gallade `6.82` | Hurricane → Sneasler `24.98` |
| 14.13 | Aerodactyl | Garchomp | Wave Crash → Aerodactyl `25.99` | Ice Beam → Garchomp `67.35` |
| 14.14 | Lopunny | Garchomp | Wave Crash → Lopunny `13.33` | Ice Beam → Garchomp `33.68` |
| 14.15 | Weavile | Garchomp | Switch → Gallade `10.05` | Ice Beam → Garchomp `16.84` |
| 14.16 | Talonflame | Garchomp | Aqua Jet → Talonflame `131.56` | Ice Beam → Garchomp `67.35` |
| 14.17 | Charizard | Incineroar | Wave Crash → Incineroar `23.53` | Weather Ball → Charizard `50.53` |
| 14.18 | Rotom-Wash | Garchomp | Wave Crash → Rotom-Wash `2.98` | Ice Beam → Garchomp `44.90` |
| 14.19 | Glimmora | Incineroar | Wave Crash → Incineroar `23.53` | Weather Ball → Glimmora `56.40` |
| 14.20 | Pelipper | Dragonite | Wave Crash → Pelipper `5.89` | Ice Beam → Dragonite `8.48` |

---

## 15. My Lead: **Dragonite** [A]  +  **Pelipper** [B] *(mega: Dragonite)*
Bench: Gallade, Arcanine-Hisui, Aegislash, Basculegion

| # | Opp [A] | Opp [B] | Dragonite [A] | Pelipper [B] |
|---|---|---|---|---|
| 15.1 | Incineroar | Sneasler | Air Slash → Sneasler `11.56` | Weather Ball → Incineroar `7.73` |
| 15.2 | Incineroar | Whimsicott | Air Slash → Whimsicott `5.46` | Weather Ball → Incineroar `15.46` |
| 15.3 | Incineroar | Garchomp | Switch → Basculegion `1.97` | Ice Beam → Garchomp `22.45` |
| 15.4 | Incineroar | Farigiraf | Dragon Pulse → Farigiraf `3.40` | Weather Ball → Incineroar `15.46` |
| 15.5 | Incineroar | Kingambit | Dragon Pulse → Kingambit `0.98` | Weather Ball → Incineroar `7.73` |
| 15.6 | Incineroar | Aerodactyl | Switch → Basculegion `4.09` | Weather Ball → Aerodactyl `10.46` |
| 15.7 | Farigiraf | Sneasler | Air Slash → Sneasler `23.12` | Weather Ball → Farigiraf `11.30` |
| 15.8 | Farigiraf | Garchomp | Dragon Pulse → Farigiraf `4.54` | Ice Beam → Garchomp `89.80` |
| 15.9 | Whimsicott | Garchomp | Air Slash → Whimsicott `8.19` | Ice Beam → Garchomp `89.80` |
| 15.10 | Whimsicott | Kingambit | Air Slash → Whimsicott `10.93` | Weather Ball → Kingambit `10.70` |
| 15.11 | Sneasler | Garchomp | Air Slash → Sneasler `8.67` | Ice Beam → Garchomp `44.90` |
| 15.12 | Sneasler | Kingambit | Switch → Gallade `2.80` | Hurricane → Sneasler `24.98` |
| 15.13 | Aerodactyl | Garchomp | Dragon Pulse → Aerodactyl `4.40` | Ice Beam → Garchomp `67.35` |
| 15.14 | Lopunny | Garchomp | Air Slash → Lopunny `8.12` | Ice Beam → Garchomp `33.68` |
| 15.15 | Weavile | Garchomp | Switch → Gallade `3.70` | Ice Beam → Garchomp `16.84` |
| 15.16 | Talonflame | Garchomp | Dragon Pulse → Garchomp `6.42` | Weather Ball → Talonflame `111.52` |
| 15.17 | Charizard | Incineroar | Dragon Pulse → Incineroar `1.32` | Weather Ball → Charizard `50.53` |
| 15.18 | Rotom-Wash | Garchomp | Dragon Pulse → Rotom-Wash `2.79` | Ice Beam → Garchomp `44.90` |
| 15.19 | Glimmora | Incineroar | Switch → Basculegion `2.92` | Weather Ball → Glimmora `28.20` |
| 15.20 | Pelipper | Dragonite | Dragon Pulse → Pelipper `10.29` | Ice Beam → Dragonite `8.48` |
