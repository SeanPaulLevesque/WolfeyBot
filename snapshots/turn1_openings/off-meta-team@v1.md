# Turn 1 First-Turn Decision Summary

Engine v0.42.1 | Turn 1 opening, 100% HP, no field effects, no revealed moves

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
| 1.1 | Incineroar | Sneasler | Psycho Cut → Sneasler `10.00` | Protect → ? `7.50` |
| 1.2 | Incineroar | Whimsicott | Sacred Sword → Incineroar `20.00` | Head Smash → Whimsicott `12.00` |
| 1.3 | Incineroar | Garchomp | Sacred Sword → Incineroar `10.00` | Switch → Basculegion `4.69` |
| 1.4 | Incineroar | Farigiraf | Sacred Sword → Incineroar `30.00` | Head Smash → Farigiraf `9.77` |
| 1.5 | Incineroar | Kingambit | Sacred Sword → Kingambit `15.00` | Head Smash → Incineroar `40.00` |
| 1.6 | Incineroar | Aerodactyl | Switch → Basculegion `9.68` | Head Smash → Incineroar `30.00` |
| 1.7 | Farigiraf | Sneasler | Psycho Cut → Sneasler `20.00` | Protect → ? `7.50` |
| 1.8 | Farigiraf | Garchomp | Sacred Sword → Garchomp `5.87` | Switch → Basculegion `4.66` |
| 1.9 | Whimsicott | Garchomp | Sacred Sword → Garchomp `4.40` | Extreme Speed → Whimsicott `3.69` |
| 1.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `40.00` | Head Smash → Whimsicott `12.00` |
| 1.11 | Sneasler | Garchomp | Psycho Cut → Sneasler `7.50` | Protect → ? `7.50` |
| 1.12 | Sneasler | Kingambit | Sacred Sword → Kingambit `10.00` | Protect → ? `7.50` |
| 1.13 | Aerodactyl | Garchomp | Switch → Basculegion `9.93` | Switch → Aegislash `3.20` |
| 1.14 | Lopunny | Garchomp | Sacred Sword → Lopunny `7.50` | Protect → ? `7.50` |
| 1.15 | Weavile | Garchomp | Protect → ? `2.00` | Protect → ? `5.00` |
| 1.16 | Talonflame | Garchomp | Switch → Basculegion `10.30` | Head Smash → Talonflame `8.00` |
| 1.17 | Charizard | Incineroar | Sacred Sword → Incineroar `10.00` | Head Smash → Charizard `40.00` |
| 1.18 | Rotom-Wash | Garchomp | Leaf Blade → Rotom-Wash `15.00` | Protect → ? `7.50` |
| 1.19 | Glimmora | Incineroar | Psycho Cut → Glimmora `3.00` | Head Smash → Incineroar `40.00` |
| 1.20 | Pelipper | Dragonite | Psycho Cut → Pelipper `5.96` | Head Smash → Pelipper `32.00` |

---

## 2. My Lead: **Gallade** [A]  +  **Aegislash** [B]
Bench: Arcanine-Hisui, Basculegion, Dragonite, Pelipper

| # | Opp [A] | Opp [B] | Gallade [A] | Aegislash [B] |
|---|---|---|---|---|
| 2.1 | Incineroar | Sneasler | Sacred Sword → Incineroar `15.00` | Poltergeist → Sneasler `2.29` |
| 2.2 | Incineroar | Whimsicott | Sacred Sword → Incineroar `30.00` | Iron Head → Whimsicott `4.86` |
| 2.3 | Incineroar | Garchomp | Sacred Sword → Incineroar `15.00` | Switch → Basculegion `1.81` |
| 2.4 | Incineroar | Farigiraf | Sacred Sword → Incineroar `40.00` | Iron Head → Farigiraf `2.44` |
| 2.5 | Incineroar | Kingambit | Sacred Sword → Incineroar `20.00` | Sacred Sword → Kingambit `2.56` |
| 2.6 | Incineroar | Aerodactyl | Sacred Sword → Incineroar `6.00` | Iron Head → Aerodactyl `5.20` |
| 2.7 | Farigiraf | Sneasler | Psycho Cut → Sneasler `30.00` | Iron Head → Farigiraf `2.44` |
| 2.8 | Farigiraf | Garchomp | Sacred Sword → Farigiraf `7.06` | Poltergeist → Garchomp `4.04` |
| 2.9 | Whimsicott | Garchomp | Sacred Sword → Garchomp `5.87` | Iron Head → Whimsicott `4.86` |
| 2.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `60.00` | Iron Head → Whimsicott `6.48` |
| 2.11 | Sneasler | Garchomp | Psycho Cut → Sneasler `10.00` | Switch → Basculegion `1.57` |
| 2.12 | Sneasler | Kingambit | Sacred Sword → Kingambit `15.00` | Poltergeist → Sneasler `3.06` |
| 2.13 | Aerodactyl | Garchomp | Switch → Basculegion `9.93` | Iron Head → Aerodactyl `5.20` |
| 2.14 | Lopunny | Garchomp | Sacred Sword → Lopunny `10.00` | King's Shield → ? `7.50` |
| 2.15 | Weavile | Garchomp | Sacred Sword → Garchomp `1.47` | Sacred Sword → Weavile `3.00` |
| 2.16 | Talonflame | Garchomp | Switch → Basculegion `10.30` | Poltergeist → Talonflame `4.17` |
| 2.17 | Charizard | Incineroar | Sacred Sword → Incineroar `15.00` | Switch → Arcanine-Hisui `14.31` |
| 2.18 | Rotom-Wash | Garchomp | Leaf Blade → Rotom-Wash `20.00` | Poltergeist → Garchomp `1.52` |
| 2.19 | Glimmora | Incineroar | Sacred Sword → Incineroar `20.00` | Switch → Basculegion `2.24` |
| 2.20 | Pelipper | Dragonite | Psycho Cut → Pelipper `8.94` | Poltergeist → Dragonite `1.82` |

---

## 3. My Lead: **Gallade** [A]  +  **Basculegion** [B]
Bench: Arcanine-Hisui, Aegislash, Dragonite, Pelipper

| # | Opp [A] | Opp [B] | Gallade [A] | Basculegion [B] |
|---|---|---|---|---|
| 3.1 | Incineroar | Sneasler | Sacred Sword → Incineroar `15.00` | Wave Crash → Sneasler `20.00` |
| 3.2 | Incineroar | Whimsicott | Psycho Cut → Whimsicott `4.93` | Wave Crash → Incineroar `40.00` |
| 3.3 | Incineroar | Garchomp | Sacred Sword → Incineroar `15.00` | Wave Crash → Garchomp `4.00` |
| 3.4 | Incineroar | Farigiraf | Sacred Sword → Incineroar `40.00` | Wave Crash → Farigiraf `9.53` |
| 3.5 | Incineroar | Kingambit | Sacred Sword → Kingambit `20.00` | Wave Crash → Incineroar `30.00` |
| 3.6 | Incineroar | Aerodactyl | Switch → Arcanine-Hisui `6.81` | Wave Crash → Incineroar `20.00` |
| 3.7 | Farigiraf | Sneasler | Psycho Cut → Sneasler `30.00` | Wave Crash → Farigiraf `6.36` |
| 3.8 | Farigiraf | Garchomp | Sacred Sword → Farigiraf `7.06` | Wave Crash → Farigiraf `12.71` |
| 3.9 | Whimsicott | Garchomp | Psycho Cut → Whimsicott `6.58` | Wave Crash → Garchomp `6.00` |
| 3.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `60.00` | Wave Crash → Whimsicott `6.20` |
| 3.11 | Sneasler | Garchomp | Psycho Cut → Sneasler `10.00` | Wave Crash → Garchomp `3.00` |
| 3.12 | Sneasler | Kingambit | Sacred Sword → Kingambit `15.00` | Wave Crash → Sneasler `20.00` |
| 3.13 | Aerodactyl | Garchomp | Switch → Pelipper `3.32` | Wave Crash → Aerodactyl `6.00` |
| 3.14 | Lopunny | Garchomp | Sacred Sword → Lopunny `10.00` | Wave Crash → Garchomp `3.00` |
| 3.15 | Weavile | Garchomp | Protect → ? `2.00` | Protect → ? `5.00` |
| 3.16 | Talonflame | Garchomp | Protect → ? `7.50` | Wave Crash → Talonflame `30.00` |
| 3.17 | Charizard | Incineroar | Sacred Sword → Incineroar `15.00` | Wave Crash → Charizard `20.00` |
| 3.18 | Rotom-Wash | Garchomp | Leaf Blade → Rotom-Wash `20.00` | Wave Crash → Garchomp `3.00` |
| 3.19 | Glimmora | Incineroar | Sacred Sword → Incineroar `20.00` | Wave Crash → Glimmora `4.00` |
| 3.20 | Pelipper | Dragonite | Psycho Cut → Dragonite `4.16` | Wave Crash → Pelipper `5.89` |

---

## 4. My Lead: **Gallade** [A]  +  **Dragonite** [B] *(mega: Dragonite)*
Bench: Arcanine-Hisui, Aegislash, Basculegion, Pelipper

| # | Opp [A] | Opp [B] | Gallade [A] | Dragonite [B] |
|---|---|---|---|---|
| 4.1 | Incineroar | Sneasler | Sacred Sword → Incineroar `10.00` | Air Slash → Sneasler `30.00` |
| 4.2 | Incineroar | Whimsicott | Sacred Sword → Incineroar `20.00` | Air Slash → Whimsicott `12.00` |
| 4.3 | Incineroar | Garchomp | Sacred Sword → Incineroar `10.00` | Dragon Pulse → Garchomp `6.00` |
| 4.4 | Incineroar | Farigiraf | Sacred Sword → Incineroar `30.00` | Dragon Pulse → Farigiraf `8.36` |
| 4.5 | Incineroar | Kingambit | Sacred Sword → Kingambit `15.00` | Dragon Pulse → Incineroar `3.53` |
| 4.6 | Incineroar | Aerodactyl | Switch → Basculegion `9.68` | Dragon Pulse → Aerodactyl `4.40` |
| 4.7 | Farigiraf | Sneasler | Sacred Sword → Farigiraf `2.35` | Air Slash → Sneasler `60.00` |
| 4.8 | Farigiraf | Garchomp | Sacred Sword → Farigiraf `4.71` | Dragon Pulse → Garchomp `12.00` |
| 4.9 | Whimsicott | Garchomp | Psycho Cut → Whimsicott `4.93` | Dragon Pulse → Garchomp `8.00` |
| 4.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `40.00` | Air Slash → Whimsicott `12.00` |
| 4.11 | Sneasler | Garchomp | Psycho Cut → Sneasler `7.50` | Dragon Pulse → Garchomp `4.00` |
| 4.12 | Sneasler | Kingambit | Sacred Sword → Kingambit `10.00` | Air Slash → Sneasler `30.00` |
| 4.13 | Aerodactyl | Garchomp | Switch → Basculegion `9.93` | Dragon Pulse → Garchomp `8.00` |
| 4.14 | Lopunny | Garchomp | Sacred Sword → Lopunny `7.50` | Dragon Pulse → Garchomp `4.00` |
| 4.15 | Weavile | Garchomp | Sacred Sword → Weavile `1.50` | Dragon Pulse → Garchomp `4.00` |
| 4.16 | Talonflame | Garchomp | Switch → Basculegion `10.30` | Dragon Pulse → Garchomp `8.00` |
| 4.17 | Charizard | Incineroar | Sacred Sword → Incineroar `10.00` | Dragon Pulse → Charizard `4.51` |
| 4.18 | Rotom-Wash | Garchomp | Leaf Blade → Rotom-Wash `15.00` | Dragon Pulse → Garchomp `6.00` |
| 4.19 | Glimmora | Incineroar | Sacred Sword → Incineroar `15.00` | Dragon Pulse → Glimmora `5.52` |
| 4.20 | Pelipper | Dragonite | Psycho Cut → Pelipper `5.96` | Dragon Pulse → Pelipper `27.44` |

---

## 5. My Lead: **Gallade** [A]  +  **Pelipper** [B]
Bench: Arcanine-Hisui, Aegislash, Basculegion, Dragonite

| # | Opp [A] | Opp [B] | Gallade [A] | Pelipper [B] |
|---|---|---|---|---|
| 5.1 | Incineroar | Sneasler | Sacred Sword → Incineroar `10.00` | Hurricane → Sneasler `40.00` |
| 5.2 | Incineroar | Whimsicott | Sacred Sword → Incineroar `20.00` | Hurricane → Whimsicott `16.00` |
| 5.3 | Incineroar | Garchomp | Sacred Sword → Incineroar `10.00` | Ice Beam → Garchomp `40.00` |
| 5.4 | Incineroar | Farigiraf | Sacred Sword → Incineroar `30.00` | Weather Ball → Farigiraf `10.30` |
| 5.5 | Incineroar | Kingambit | Sacred Sword → Kingambit `15.00` | Weather Ball → Incineroar `7.73` |
| 5.6 | Incineroar | Aerodactyl | Switch → Basculegion `14.80` | Weather Ball → Aerodactyl `6.00` |
| 5.7 | Farigiraf | Sneasler | Psycho Cut → Sneasler `20.00` | Weather Ball → Farigiraf `10.30` |
| 5.8 | Farigiraf | Garchomp | Sacred Sword → Farigiraf `4.71` | Ice Beam → Garchomp `80.00` |
| 5.9 | Whimsicott | Garchomp | Psycho Cut → Whimsicott `4.93` | Ice Beam → Garchomp `80.00` |
| 5.10 | Whimsicott | Kingambit | Sacred Sword → Kingambit `40.00` | Hurricane → Whimsicott `16.00` |
| 5.11 | Sneasler | Garchomp | Psycho Cut → Sneasler `7.50` | Ice Beam → Garchomp `40.00` |
| 5.12 | Sneasler | Kingambit | Sacred Sword → Kingambit `10.00` | Hurricane → Sneasler `40.00` |
| 5.13 | Aerodactyl | Garchomp | Switch → Basculegion `15.06` | Ice Beam → Garchomp `60.00` |
| 5.14 | Lopunny | Garchomp | Sacred Sword → Lopunny `7.50` | Ice Beam → Garchomp `30.00` |
| 5.15 | Weavile | Garchomp | Sacred Sword → Weavile `1.50` | Ice Beam → Garchomp `30.00` |
| 5.16 | Talonflame | Garchomp | Switch → Basculegion `15.12` | Weather Ball → Talonflame `60.00` |
| 5.17 | Charizard | Incineroar | Sacred Sword → Incineroar `10.00` | Weather Ball → Charizard `40.00` |
| 5.18 | Rotom-Wash | Garchomp | Leaf Blade → Rotom-Wash `15.00` | Ice Beam → Garchomp `40.00` |
| 5.19 | Glimmora | Incineroar | Sacred Sword → Incineroar `15.00` | Switch → Basculegion `9.49` |
| 5.20 | Pelipper | Dragonite | Psycho Cut → Pelipper `5.96` | Hurricane → Pelipper `26.88` |

---

## 6. My Lead: **Arcanine-Hisui** [A]  +  **Aegislash** [B]
Bench: Gallade, Basculegion, Dragonite, Pelipper

| # | Opp [A] | Opp [B] | Arcanine-Hisui [A] | Aegislash [B] |
|---|---|---|---|---|
| 6.1 | Incineroar | Sneasler | Switch → Gallade `11.01` | King's Shield → ? `2.00` |
| 6.2 | Incineroar | Whimsicott | Head Smash → Incineroar `30.00` | Iron Head → Whimsicott `4.86` |
| 6.3 | Incineroar | Garchomp | Protect → ? `5.00` | King's Shield → ? `2.00` |
| 6.4 | Incineroar | Farigiraf | Head Smash → Incineroar `40.00` | Iron Head → Farigiraf `2.44` |
| 6.5 | Incineroar | Kingambit | Head Smash → Incineroar `20.00` | Switch → Gallade `7.83` |
| 6.6 | Incineroar | Aerodactyl | Head Smash → Incineroar `30.00` | Iron Head → Aerodactyl `5.20` |
| 6.7 | Farigiraf | Sneasler | Switch → Gallade `11.80` | Poltergeist → Sneasler `3.06` |
| 6.8 | Farigiraf | Garchomp | Switch → Basculegion `4.66` | Poltergeist → Garchomp `4.04` |
| 6.9 | Whimsicott | Garchomp | Switch → Gallade `3.20` | Iron Head → Whimsicott `4.86` |
| 6.10 | Whimsicott | Kingambit | Head Smash → Whimsicott `12.00` | Switch → Gallade `7.21` |
| 6.11 | Sneasler | Garchomp | Switch → Gallade `11.80` | King's Shield → ? `2.00` |
| 6.12 | Sneasler | Kingambit | Protect → ? `5.00` | Switch → Gallade `12.63` |
| 6.13 | Aerodactyl | Garchomp | Switch → Basculegion `6.07` | Iron Head → Aerodactyl `5.20` |
| 6.14 | Lopunny | Garchomp | Switch → Gallade `6.62` | Switch → Basculegion `5.78` |
| 6.15 | Weavile | Garchomp | Switch → Gallade `10.37` | King's Shield → ? `2.00` |
| 6.16 | Talonflame | Garchomp | Head Smash → Talonflame `8.00` | Poltergeist → Garchomp `3.03` |
| 6.17 | Charizard | Incineroar | Head Smash → Incineroar `20.00` | Poltergeist → Charizard `1.97` |
| 6.18 | Rotom-Wash | Garchomp | Switch → Gallade `4.04` | Poltergeist → Rotom-Wash `1.89` |
| 6.19 | Glimmora | Incineroar | Head Smash → Incineroar `20.00` | Switch → Basculegion `2.24` |
| 6.20 | Pelipper | Dragonite | Head Smash → Dragonite `11.56` | Poltergeist → Pelipper `3.73` |

---

## 7. My Lead: **Arcanine-Hisui** [A]  +  **Basculegion** [B]
Bench: Gallade, Aegislash, Dragonite, Pelipper

| # | Opp [A] | Opp [B] | Arcanine-Hisui [A] | Basculegion [B] |
|---|---|---|---|---|
| 7.1 | Incineroar | Sneasler | Switch → Gallade `11.01` | Wave Crash → Incineroar `10.00` |
| 7.2 | Incineroar | Whimsicott | Head Smash → Whimsicott `6.00` | Wave Crash → Incineroar `40.00` |
| 7.3 | Incineroar | Garchomp | Switch → Gallade `3.20` | Wave Crash → Incineroar `10.00` |
| 7.4 | Incineroar | Farigiraf | Head Smash → Incineroar `40.00` | Wave Crash → Farigiraf `9.53` |
| 7.5 | Incineroar | Kingambit | Head Smash → Incineroar `20.00` | Switch → Gallade `4.27` |
| 7.6 | Incineroar | Aerodactyl | Head Smash → Incineroar `30.00` | Wave Crash → Aerodactyl `8.00` |
| 7.7 | Farigiraf | Sneasler | Switch → Gallade `11.80` | Wave Crash → Sneasler `20.00` |
| 7.8 | Farigiraf | Garchomp | Switch → Gallade `3.65` | Wave Crash → Garchomp `8.00` |
| 7.9 | Whimsicott | Garchomp | Extreme Speed → Whimsicott `3.69` | Wave Crash → Garchomp `6.00` |
| 7.10 | Whimsicott | Kingambit | Head Smash → Whimsicott `12.00` | Switch → Gallade `7.34` |
| 7.11 | Sneasler | Garchomp | Switch → Gallade `11.80` | Wave Crash → Sneasler `7.50` |
| 7.12 | Sneasler | Kingambit | Switch → Gallade `11.80` | Protect → ? `5.00` |
| 7.13 | Aerodactyl | Garchomp | Extreme Speed → Aerodactyl `2.44` | Aqua Jet → Aerodactyl `12.00` |
| 7.14 | Lopunny | Garchomp | Protect → ? `7.50` | Wave Crash → Lopunny `7.50` |
| 7.15 | Weavile | Garchomp | Protect → ? `5.00` | Switch → Gallade `12.78` |
| 7.16 | Talonflame | Garchomp | Switch → Aegislash `3.20` | Wave Crash → Talonflame `30.00` |
| 7.17 | Charizard | Incineroar | Head Smash → Incineroar `20.00` | Wave Crash → Charizard `20.00` |
| 7.18 | Rotom-Wash | Garchomp | Switch → Gallade `4.04` | Wave Crash → Garchomp `3.00` |
| 7.19 | Glimmora | Incineroar | Head Smash → Incineroar `20.00` | Wave Crash → Glimmora `4.00` |
| 7.20 | Pelipper | Dragonite | Head Smash → Pelipper `16.00` | Aqua Jet → Pelipper `4.97` |

---

## 8. My Lead: **Arcanine-Hisui** [A]  +  **Dragonite** [B] *(mega: Dragonite)*
Bench: Gallade, Aegislash, Basculegion, Pelipper

| # | Opp [A] | Opp [B] | Arcanine-Hisui [A] | Dragonite [B] |
|---|---|---|---|---|
| 8.1 | Incineroar | Sneasler | Switch → Gallade `11.01` | Air Slash → Sneasler `15.00` |
| 8.2 | Incineroar | Whimsicott | Head Smash → Incineroar `20.00` | Air Slash → Whimsicott `12.00` |
| 8.3 | Incineroar | Garchomp | Switch → Basculegion `4.69` | Dragon Pulse → Garchomp `3.00` |
| 8.4 | Incineroar | Farigiraf | Head Smash → Incineroar `30.00` | Dragon Pulse → Farigiraf `8.36` |
| 8.5 | Incineroar | Kingambit | Head Smash → Incineroar `15.00` | Dragon Pulse → Kingambit `2.63` |
| 8.6 | Incineroar | Aerodactyl | Head Smash → Incineroar `20.00` | Dragon Pulse → Aerodactyl `8.80` |
| 8.7 | Farigiraf | Sneasler | Switch → Gallade `11.80` | Air Slash → Sneasler `30.00` |
| 8.8 | Farigiraf | Garchomp | Switch → Basculegion `4.66` | Dragon Pulse → Garchomp `12.00` |
| 8.9 | Whimsicott | Garchomp | Switch → Gallade `3.20` | Dragon Pulse → Garchomp `8.00` |
| 8.10 | Whimsicott | Kingambit | Flare Blitz → Kingambit `7.01` | Air Slash → Whimsicott `12.00` |
| 8.11 | Sneasler | Garchomp | Switch → Gallade `11.80` | Air Slash → Sneasler `10.00` |
| 8.12 | Sneasler | Kingambit | Switch → Gallade `11.80` | Air Slash → Sneasler `15.00` |
| 8.13 | Aerodactyl | Garchomp | Switch → Basculegion `6.07` | Dragon Pulse → Garchomp `8.00` |
| 8.14 | Lopunny | Garchomp | Protect → ? `7.50` | Air Slash → Lopunny `10.00` |
| 8.15 | Weavile | Garchomp | Switch → Gallade `10.37` | Dragon Pulse → Garchomp `2.00` |
| 8.16 | Talonflame | Garchomp | Head Smash → Talonflame `6.00` | Dragon Pulse → Garchomp `8.00` |
| 8.17 | Charizard | Incineroar | Head Smash → Incineroar `15.00` | Dragon Pulse → Charizard `4.51` |
| 8.18 | Rotom-Wash | Garchomp | Switch → Gallade `4.04` | Dragon Pulse → Garchomp `6.00` |
| 8.19 | Glimmora | Incineroar | Head Smash → Incineroar `15.00` | Dragon Pulse → Glimmora `5.52` |
| 8.20 | Pelipper | Dragonite | Head Smash → Pelipper `12.00` | Dragon Pulse → Pelipper `27.44` |

---

## 9. My Lead: **Arcanine-Hisui** [A]  +  **Pelipper** [B]
Bench: Gallade, Aegislash, Basculegion, Dragonite

| # | Opp [A] | Opp [B] | Arcanine-Hisui [A] | Pelipper [B] |
|---|---|---|---|---|
| 9.1 | Incineroar | Sneasler | Head Smash → Incineroar `10.00` | Hurricane → Sneasler `40.00` |
| 9.2 | Incineroar | Whimsicott | Head Smash → Incineroar `20.00` | Hurricane → Whimsicott `16.00` |
| 9.3 | Incineroar | Garchomp | Head Smash → Incineroar `10.00` | Ice Beam → Garchomp `40.00` |
| 9.4 | Incineroar | Farigiraf | Head Smash → Incineroar `30.00` | Weather Ball → Farigiraf `10.30` |
| 9.5 | Incineroar | Kingambit | Head Smash → Incineroar `15.00` | Weather Ball → Kingambit `5.35` |
| 9.6 | Incineroar | Aerodactyl | Head Smash → Incineroar `20.00` | Weather Ball → Aerodactyl `12.00` |
| 9.7 | Farigiraf | Sneasler | Head Smash → Farigiraf `2.44` | Hurricane → Sneasler `80.00` |
| 9.8 | Farigiraf | Garchomp | Head Smash → Farigiraf `4.88` | Ice Beam → Garchomp `80.00` |
| 9.9 | Whimsicott | Garchomp | Head Smash → Whimsicott `6.00` | Ice Beam → Garchomp `80.00` |
| 9.10 | Whimsicott | Kingambit | Switch → Gallade `6.29` | Hurricane → Whimsicott `16.00` |
| 9.11 | Sneasler | Garchomp | Switch → Gallade `3.25` | Hurricane → Sneasler `20.00` |
| 9.12 | Sneasler | Kingambit | Switch → Gallade `13.00` | Hurricane → Sneasler `20.00` |
| 9.13 | Aerodactyl | Garchomp | Head Smash → Aerodactyl `6.00` | Ice Beam → Garchomp `60.00` |
| 9.14 | Lopunny | Garchomp | Switch → Basculegion `8.06` | Hurricane → Lopunny `15.00` |
| 9.15 | Weavile | Garchomp | Head Smash → Weavile `1.50` | Ice Beam → Garchomp `30.00` |
| 9.16 | Talonflame | Garchomp | Head Smash → Talonflame `30.00` | Ice Beam → Garchomp `60.00` |
| 9.17 | Charizard | Incineroar | Head Smash → Incineroar `15.00` | Weather Ball → Charizard `40.00` |
| 9.18 | Rotom-Wash | Garchomp | Protect → ? `7.50` | Ice Beam → Garchomp `40.00` |
| 9.19 | Glimmora | Incineroar | Head Smash → Incineroar `15.00` | Switch → Basculegion `9.49` |
| 9.20 | Pelipper | Dragonite | Head Smash → Pelipper `12.00` | Hurricane → Pelipper `26.88` |

---

## 10. My Lead: **Aegislash** [A]  +  **Basculegion** [B]
Bench: Gallade, Arcanine-Hisui, Dragonite, Pelipper

| # | Opp [A] | Opp [B] | Aegislash [A] | Basculegion [B] |
|---|---|---|---|---|
| 10.1 | Incineroar | Sneasler | Switch → Gallade `3.16` | Wave Crash → Incineroar `15.00` |
| 10.2 | Incineroar | Whimsicott | Iron Head → Whimsicott `2.43` | Wave Crash → Incineroar `60.00` |
| 10.3 | Incineroar | Garchomp | Poltergeist → Garchomp `0.76` | Wave Crash → Incineroar `30.00` |
| 10.4 | Incineroar | Farigiraf | Iron Head → Farigiraf `1.22` | Wave Crash → Incineroar `80.00` |
| 10.5 | Incineroar | Kingambit | Switch → Gallade `7.83` | Protect → ? `5.00` |
| 10.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `2.60` | Wave Crash → Incineroar `60.00` |
| 10.7 | Farigiraf | Sneasler | Switch → Gallade `3.16` | Wave Crash → Sneasler `30.00` |
| 10.8 | Farigiraf | Garchomp | Poltergeist → Garchomp `4.04` | Wave Crash → Farigiraf `9.53` |
| 10.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `4.86` | Wave Crash → Garchomp `8.00` |
| 10.10 | Whimsicott | Kingambit | Iron Head → Whimsicott `6.48` | Switch → Gallade `7.34` |
| 10.11 | Sneasler | Garchomp | Switch → Gallade `3.16` | Wave Crash → Sneasler `10.00` |
| 10.12 | Sneasler | Kingambit | Switch → Gallade `12.63` | Protect → ? `5.00` |
| 10.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `5.20` | Wave Crash → Garchomp `8.00` |
| 10.14 | Lopunny | Garchomp | King's Shield → ? `7.50` | Wave Crash → Lopunny `10.00` |
| 10.15 | Weavile | Garchomp | King's Shield → ? `2.00` | Switch → Gallade `12.78` |
| 10.16 | Talonflame | Garchomp | Poltergeist → Garchomp `3.03` | Wave Crash → Talonflame `40.00` |
| 10.17 | Charizard | Incineroar | Switch → Arcanine-Hisui `14.31` | Wave Crash → Charizard `15.00` |
| 10.18 | Rotom-Wash | Garchomp | Poltergeist → Rotom-Wash `1.89` | Wave Crash → Garchomp `4.00` |
| 10.19 | Glimmora | Incineroar | Iron Head → Glimmora `1.03` | Wave Crash → Incineroar `30.00` |
| 10.20 | Pelipper | Dragonite | Poltergeist → Dragonite `1.82` | Wave Crash → Pelipper `7.85` |

---

## 11. My Lead: **Aegislash** [A]  +  **Dragonite** [B] *(mega: Dragonite)*
Bench: Gallade, Arcanine-Hisui, Basculegion, Pelipper

| # | Opp [A] | Opp [B] | Aegislash [A] | Dragonite [B] |
|---|---|---|---|---|
| 11.1 | Incineroar | Sneasler | Switch → Gallade `3.16` | Air Slash → Sneasler `15.00` |
| 11.2 | Incineroar | Whimsicott | Sacred Sword → Incineroar `1.26` | Air Slash → Whimsicott `12.00` |
| 11.3 | Incineroar | Garchomp | Switch → Basculegion `1.81` | Dragon Pulse → Garchomp `3.00` |
| 11.4 | Incineroar | Farigiraf | Sacred Sword → Incineroar `1.69` | Dragon Pulse → Farigiraf `8.36` |
| 11.5 | Incineroar | Kingambit | Switch → Gallade `7.83` | Protect → ? `2.00` |
| 11.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `2.60` | Dragon Pulse → Incineroar `5.30` |
| 11.7 | Farigiraf | Sneasler | Switch → Gallade `3.16` | Air Slash → Sneasler `30.00` |
| 11.8 | Farigiraf | Garchomp | Iron Head → Farigiraf `2.44` | Dragon Pulse → Garchomp `12.00` |
| 11.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `4.86` | Dragon Pulse → Garchomp `8.00` |
| 11.10 | Whimsicott | Kingambit | Switch → Gallade `7.21` | Air Slash → Whimsicott `12.00` |
| 11.11 | Sneasler | Garchomp | Switch → Gallade `3.16` | Air Slash → Sneasler `10.00` |
| 11.12 | Sneasler | Kingambit | Switch → Gallade `12.63` | Air Slash → Sneasler `15.00` |
| 11.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `5.20` | Dragon Pulse → Garchomp `8.00` |
| 11.14 | Lopunny | Garchomp | King's Shield → ? `7.50` | Air Slash → Lopunny `10.00` |
| 11.15 | Weavile | Garchomp | King's Shield → ? `2.00` | Switch → Gallade `3.70` |
| 11.16 | Talonflame | Garchomp | Poltergeist → Talonflame `4.17` | Dragon Pulse → Garchomp `8.00` |
| 11.17 | Charizard | Incineroar | Switch → Arcanine-Hisui `14.31` | Dragon Pulse → Charizard `2.25` |
| 11.18 | Rotom-Wash | Garchomp | Poltergeist → Rotom-Wash `1.89` | Dragon Pulse → Garchomp `6.00` |
| 11.19 | Glimmora | Incineroar | Switch → Basculegion `2.24` | Dragon Pulse → Glimmora `2.76` |
| 11.20 | Pelipper | Dragonite | Poltergeist → Pelipper `3.73` | Dragon Pulse → Dragonite `8.01` |

---

## 12. My Lead: **Aegislash** [A]  +  **Pelipper** [B]
Bench: Gallade, Arcanine-Hisui, Basculegion, Dragonite

| # | Opp [A] | Opp [B] | Aegislash [A] | Pelipper [B] |
|---|---|---|---|---|
| 12.1 | Incineroar | Sneasler | Switch → Gallade `3.16` | Hurricane → Sneasler `20.00` |
| 12.2 | Incineroar | Whimsicott | Iron Head → Whimsicott `2.43` | Weather Ball → Incineroar `15.46` |
| 12.3 | Incineroar | Garchomp | Switch → Basculegion `2.49` | Ice Beam → Garchomp `20.00` |
| 12.4 | Incineroar | Farigiraf | Switch → Basculegion `2.57` | Weather Ball → Incineroar `7.73` |
| 12.5 | Incineroar | Kingambit | Switch → Gallade `7.83` | Weather Ball → Incineroar `3.87` |
| 12.6 | Incineroar | Aerodactyl | Iron Head → Aerodactyl `2.60` | Weather Ball → Incineroar `11.60` |
| 12.7 | Farigiraf | Sneasler | Switch → Gallade `3.16` | Hurricane → Sneasler `40.00` |
| 12.8 | Farigiraf | Garchomp | Iron Head → Farigiraf `2.44` | Ice Beam → Garchomp `80.00` |
| 12.9 | Whimsicott | Garchomp | Iron Head → Whimsicott `4.86` | Ice Beam → Garchomp `80.00` |
| 12.10 | Whimsicott | Kingambit | Switch → Gallade `7.21` | Hurricane → Whimsicott `16.00` |
| 12.11 | Sneasler | Garchomp | Switch → Gallade `3.16` | Hurricane → Sneasler `20.00` |
| 12.12 | Sneasler | Kingambit | Switch → Gallade `12.63` | Hurricane → Sneasler `20.00` |
| 12.13 | Aerodactyl | Garchomp | Iron Head → Aerodactyl `5.20` | Ice Beam → Garchomp `60.00` |
| 12.14 | Lopunny | Garchomp | Switch → Basculegion `7.91` | Hurricane → Lopunny `15.00` |
| 12.15 | Weavile | Garchomp | Switch → Gallade `3.48` | Ice Beam → Garchomp `15.00` |
| 12.16 | Talonflame | Garchomp | Poltergeist → Talonflame `4.17` | Ice Beam → Garchomp `60.00` |
| 12.17 | Charizard | Incineroar | Sacred Sword → Incineroar `0.63` | Weather Ball → Charizard `40.00` |
| 12.18 | Rotom-Wash | Garchomp | Poltergeist → Rotom-Wash `1.89` | Ice Beam → Garchomp `40.00` |
| 12.19 | Glimmora | Incineroar | King's Shield → ? `2.00` | Switch → Basculegion `9.49` |
| 12.20 | Pelipper | Dragonite | Poltergeist → Pelipper `3.73` | Ice Beam → Dragonite `8.48` |

---

## 13. My Lead: **Basculegion** [A]  +  **Dragonite** [B] *(mega: Dragonite)*
Bench: Gallade, Arcanine-Hisui, Aegislash, Pelipper

| # | Opp [A] | Opp [B] | Basculegion [A] | Dragonite [B] |
|---|---|---|---|---|
| 13.1 | Incineroar | Sneasler | Wave Crash → Incineroar `10.00` | Air Slash → Sneasler `30.00` |
| 13.2 | Incineroar | Whimsicott | Wave Crash → Incineroar `20.00` | Air Slash → Whimsicott `12.00` |
| 13.3 | Incineroar | Garchomp | Wave Crash → Incineroar `10.00` | Dragon Pulse → Garchomp `6.00` |
| 13.4 | Incineroar | Farigiraf | Wave Crash → Incineroar `30.00` | Dragon Pulse → Farigiraf `8.36` |
| 13.5 | Incineroar | Kingambit | Protect → ? `5.00` | Switch → Gallade `2.14` |
| 13.6 | Incineroar | Aerodactyl | Wave Crash → Incineroar `20.00` | Dragon Pulse → Aerodactyl `8.80` |
| 13.7 | Farigiraf | Sneasler | Wave Crash → Farigiraf `3.18` | Air Slash → Sneasler `60.00` |
| 13.8 | Farigiraf | Garchomp | Wave Crash → Farigiraf `6.36` | Dragon Pulse → Farigiraf `12.54` |
| 13.9 | Whimsicott | Garchomp | Wave Crash → Garchomp `6.00` | Air Slash → Whimsicott `8.00` |
| 13.10 | Whimsicott | Kingambit | Switch → Gallade `7.34` | Air Slash → Whimsicott `12.00` |
| 13.11 | Sneasler | Garchomp | Wave Crash → Sneasler `7.50` | Dragon Pulse → Garchomp `4.00` |
| 13.12 | Sneasler | Kingambit | Switch → Gallade `9.53` | Air Slash → Sneasler `15.00` |
| 13.13 | Aerodactyl | Garchomp | Wave Crash → Aerodactyl `6.00` | Dragon Pulse → Garchomp `8.00` |
| 13.14 | Lopunny | Garchomp | Wave Crash → Lopunny `7.50` | Dragon Pulse → Garchomp `4.00` |
| 13.15 | Weavile | Garchomp | Switch → Gallade `12.78` | Dragon Pulse → Garchomp `2.00` |
| 13.16 | Talonflame | Garchomp | Wave Crash → Talonflame `30.00` | Dragon Pulse → Garchomp `8.00` |
| 13.17 | Charizard | Incineroar | Wave Crash → Charizard `10.00` | Switch → Arcanine-Hisui `3.66` |
| 13.18 | Rotom-Wash | Garchomp | Wave Crash → Rotom-Wash `2.11` | Dragon Pulse → Garchomp `6.00` |
| 13.19 | Glimmora | Incineroar | Wave Crash → Incineroar `10.00` | Dragon Pulse → Glimmora `5.52` |
| 13.20 | Pelipper | Dragonite | Aqua Jet → Pelipper `2.49` | Dragon Pulse → Pelipper `27.44` |

---

## 14. My Lead: **Basculegion** [A]  +  **Pelipper** [B]
Bench: Gallade, Arcanine-Hisui, Aegislash, Dragonite

| # | Opp [A] | Opp [B] | Basculegion [A] | Pelipper [B] |
|---|---|---|---|---|
| 14.1 | Incineroar | Sneasler | Wave Crash → Incineroar `10.00` | Hurricane → Sneasler `40.00` |
| 14.2 | Incineroar | Whimsicott | Wave Crash → Incineroar `20.00` | Hurricane → Whimsicott `16.00` |
| 14.3 | Incineroar | Garchomp | Wave Crash → Incineroar `10.00` | Ice Beam → Garchomp `40.00` |
| 14.4 | Incineroar | Farigiraf | Wave Crash → Farigiraf `60.00` | Weather Ball → Incineroar `15.46` |
| 14.5 | Incineroar | Kingambit | Wave Crash → Kingambit `3.00` | Weather Ball → Incineroar `7.73` |
| 14.6 | Incineroar | Aerodactyl | Wave Crash → Incineroar `20.00` | Weather Ball → Aerodactyl `12.00` |
| 14.7 | Farigiraf | Sneasler | Wave Crash → Farigiraf `40.00` | Hurricane → Sneasler `80.00` |
| 14.8 | Farigiraf | Garchomp | Wave Crash → Farigiraf `80.00` | Ice Beam → Garchomp `80.00` |
| 14.9 | Whimsicott | Garchomp | Wave Crash → Garchomp `30.00` | Hurricane → Whimsicott `16.00` |
| 14.10 | Whimsicott | Kingambit | Wave Crash → Kingambit `8.00` | Hurricane → Whimsicott `16.00` |
| 14.11 | Sneasler | Garchomp | Wave Crash → Sneasler `7.50` | Ice Beam → Garchomp `40.00` |
| 14.12 | Sneasler | Kingambit | Switch → Gallade `6.82` | Hurricane → Sneasler `20.00` |
| 14.13 | Aerodactyl | Garchomp | Wave Crash → Garchomp `30.00` | Weather Ball → Aerodactyl `12.00` |
| 14.14 | Lopunny | Garchomp | Wave Crash → Lopunny `7.50` | Ice Beam → Garchomp `30.00` |
| 14.15 | Weavile | Garchomp | Switch → Gallade `10.05` | Ice Beam → Garchomp `15.00` |
| 14.16 | Talonflame | Garchomp | Aqua Jet → Talonflame `90.00` | Ice Beam → Garchomp `60.00` |
| 14.17 | Charizard | Incineroar | Wave Crash → Incineroar `10.00` | Weather Ball → Charizard `40.00` |
| 14.18 | Rotom-Wash | Garchomp | Wave Crash → Rotom-Wash `2.98` | Ice Beam → Garchomp `40.00` |
| 14.19 | Glimmora | Incineroar | Wave Crash → Incineroar `10.00` | Weather Ball → Glimmora `8.00` |
| 14.20 | Pelipper | Dragonite | Aqua Jet → Pelipper `2.49` | Hurricane → Pelipper `26.88` |

---

## 15. My Lead: **Dragonite** [A]  +  **Pelipper** [B] *(mega: Dragonite)*
Bench: Gallade, Arcanine-Hisui, Aegislash, Basculegion

| # | Opp [A] | Opp [B] | Dragonite [A] | Pelipper [B] |
|---|---|---|---|---|
| 15.1 | Incineroar | Sneasler | Air Slash → Sneasler `10.00` | Weather Ball → Incineroar `7.73` |
| 15.2 | Incineroar | Whimsicott | Air Slash → Whimsicott `4.00` | Weather Ball → Incineroar `15.46` |
| 15.3 | Incineroar | Garchomp | Switch → Basculegion `1.97` | Ice Beam → Garchomp `20.00` |
| 15.4 | Incineroar | Farigiraf | Dragon Pulse → Farigiraf `3.13` | Weather Ball → Incineroar `15.46` |
| 15.5 | Incineroar | Kingambit | Switch → Gallade `2.14` | Weather Ball → Incineroar `3.87` |
| 15.6 | Incineroar | Aerodactyl | Dragon Pulse → Aerodactyl `2.93` | Weather Ball → Incineroar `11.60` |
| 15.7 | Farigiraf | Sneasler | Air Slash → Sneasler `20.00` | Switch → Gallade `10.85` |
| 15.8 | Farigiraf | Garchomp | Dragon Pulse → Farigiraf `4.18` | Ice Beam → Garchomp `80.00` |
| 15.9 | Whimsicott | Garchomp | Air Slash → Whimsicott `6.00` | Ice Beam → Garchomp `80.00` |
| 15.10 | Whimsicott | Kingambit | Air Slash → Whimsicott `8.00` | Weather Ball → Kingambit `10.70` |
| 15.11 | Sneasler | Garchomp | Air Slash → Sneasler `7.50` | Ice Beam → Garchomp `40.00` |
| 15.12 | Sneasler | Kingambit | Switch → Gallade `2.80` | Hurricane → Sneasler `20.00` |
| 15.13 | Aerodactyl | Garchomp | Dragon Pulse → Aerodactyl `4.40` | Ice Beam → Garchomp `60.00` |
| 15.14 | Lopunny | Garchomp | Air Slash → Lopunny `7.50` | Ice Beam → Garchomp `30.00` |
| 15.15 | Weavile | Garchomp | Switch → Gallade `3.70` | Ice Beam → Garchomp `15.00` |
| 15.16 | Talonflame | Garchomp | Dragon Pulse → Garchomp `6.00` | Weather Ball → Talonflame `60.00` |
| 15.17 | Charizard | Incineroar | Dragon Pulse → Incineroar `1.32` | Weather Ball → Charizard `40.00` |
| 15.18 | Rotom-Wash | Garchomp | Dragon Pulse → Rotom-Wash `2.79` | Ice Beam → Garchomp `40.00` |
| 15.19 | Glimmora | Incineroar | Dragon Pulse → Glimmora `2.07` | Switch → Basculegion `9.49` |
| 15.20 | Pelipper | Dragonite | Dragon Pulse → Pelipper `10.29` | Hurricane → Pelipper `26.88` |
