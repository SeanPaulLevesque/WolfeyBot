# WolfeyBot v0.1.0 — Decision Module Overview

## Team

| Pokémon | Item | Ability | Role |
|---|---|---|---|
| Aerodactyl (→ Mega) | Aerodactylite | Unnerve → Tough Claws | Fast physical attacker / Dual Wingbeat spread |
| Kingambit | Chople Berry | Defiant | Priority Kowtow Cleave, Defiant Sword's Dance bait |
| Basculegion-F | Sitrus Berry | Adaptability | Last Respects sweeper, Liquidation |
| Sneasler | Mental Herb | Unburden | Close Combat, Dire Claw chip |
| Rotom-Wash | Magnet | Levitate | Hydro Pump / Thunderbolt pivot |
| Garchomp | Soft Sand | Rough Skin | Dragon Claw / Stomping Tantrum wallbreaker |

---

## Architecture

The decision engine (`decision.py`) uses a **weighted multiplicative scoring** pipeline.

Every legal action for a slot starts with `weight = 1.0`. A chain of **ScoringModules** runs in order; each module multiplies the weight by a factor that reflects how desirable that action is. Modules never add to the weight — they only multiply, so:

- `> 1.0` = encouraged  
- `< 1.0` = discouraged  
- `0.0` = vetoed (never picked)  

After all modules run, the highest-weight action is chosen for that slot. If all actions end up at 0.0 the first action is chosen as a fallback.

```
actions = [all legal moves + switches]  weight = 1.0 each
    ↓  DamageOutputModule
    ↓  ThreatEliminationModule
    ↓  PrioritySpeedModule
    ↓  ProtectModule
    ↓  SwitchModule
    ↓  DoublingUpModule
best action (highest weight) → choice string → /choose …
```

---

## Modules

### 1. DamageOutputModule
Calculates the expected damage fraction (avg damage ÷ opponent current HP) for every move against every active opponent. The best fraction across all targets sets:

```
weight × (1.0 + fraction × 2.0)
```

- OHKO → ×3.0 (100% fraction)
- 50%  → ×2.0
- 25%  → ×1.5
- 0%   → ×1.0 (immune / status)

Also sets `action.target_slot` to the opponent slot that produced the best fraction, so the move and target are always consistent.

Multi-hit moves (Dual Wingbeat, Surging Strikes, etc.) are correctly scaled by their **expected hit count** before the formula runs (e.g. Dual Wingbeat: 40 bp × 2 = 80 effective).

### 2. ThreatEliminationModule
On top of the damage score, adds a large KO bonus:

| KO quality | Multiplier |
|---|---|
| Guaranteed OHKO (min roll ≥ HP) | ×5.0 |
| OHKO on max roll only | ×2.5 |
| 2HKO (two avg hits ≥ HP) | ×1.5 |

Takes the best opportunity across all opponents. If a different opponent offers the KO than the one DamageOutputModule targeted, `target_slot` is overridden to the KO target.

### 3. PrioritySpeedModule
Adjusts priority moves based on the speed matchup:

- Any opponent may outspeed us → priority move ×1.5
- We comfortably outspeed all opponents → priority move ×0.8 (wasted priority)
- **Fake Out** (only legal on switch-in turn) → additional ×3.0 on top

### 4. ProtectModule
Encourages Protect when threatened, discourages it when already used last turn.

| Situation | Multiplier |
|---|---|
| Used Protect last turn | ×0.1 (consecutive penalty — overrides bonuses) |
| Opponent threatens OHKO on max roll | ×2.5 |
| HP below 25% | ×1.5 |

Consecutive penalty fires regardless of how good the situation looks — spamming Protect almost always fails on the second attempt.

### 5. SwitchModule
Evaluates bench options by comparing type-effectiveness of the opponent's known/inferred attack types against the switch target versus the current mon.

**Normal threat level:**

| Switch target's worst matchup | Factor |
|---|---|
| Resists all threats (≤0.5×) | ×1.8 |
| Neutral (≤1.0×) | ×1.2 |
| Weak to any threat (>1.0×) | ×0.5 |

**OHKO-threatened** (current mon will die on max roll — must get out):

| Switch target's worst matchup | Factor |
|---|---|
| Resists all threats (≤0.5×) | ×4.0 |
| Neutral | ×2.0 |
| Weak to threats | ×0.4 |

Threat types are inferred from: revealed opponent moves + each opponent's primary STAB type.

### 6. DoublingUpModule *(runs last)*
Applies a penalty when this slot's chosen move would target the **same opponent** that the partner slot already committed to (doubling up).

Doubling up risks two moves being wasted if the target uses Protect. The penalty is lighter when:

- **Target protected last turn** → unlikely to spam Protect again
- **Other opponent is not threatening** → we're not giving up much by ignoring them

| Target protected last turn | Other opp not threatening | Factor |
|---|---|---|
| ✓ | ✓ | ×0.85 |
| ✓ | ✗ | ×0.70 |
| ✗ | ✓ | ×0.70 |
| ✗ | ✗ | ×0.55 |

Spread moves (which hit all opponents) are exempt — `target_slot` is irrelevant for them.

---

## Cross-slot Coordination

`state.my_slot_decisions` is populated as each slot is resolved. When slot 1 is being scored, DoublingUpModule reads `state.my_slot_decisions[0].target_slot` to know where slot 0 is already pointing.

---

## Team Preview

When the server sends a `teamPreview: true` request, the bot reads `state.opp_preview_team` (built from `|poke|` messages) and sends `/choose team 1234` to bring the first four Pokémon in team order. No smart lead selection yet in 0.1.0.

---

## Targeting

All damage modules store the opponent slot index that drove their score on `action.target_slot`. `_action_to_choice()` in `main.py` converts this to the Showdown 1-indexed target (`target_slot + 1`) so the move and target are always the same opponent.

---

## Known Limitations (0.1.0)

- **Lead selection**: always brings mons 1-4 in team order; does not adapt to opponent preview.
- **Switches**: SwitchModule uses type matchup only; does not model speed matchups or partner synergy.
- **Tera**: `can_terastallize` flag is tracked but no module applies a Tera bonus yet.
- **Partner synergy**: modules are independent per slot; no model of "what does my partner hit" to coordinate better.
- **Item / ability effects**: damage calc uses known abilities and items where implemented, but many situational effects (Intimidate, weather-setting abilities, choice lock) are not tracked.
