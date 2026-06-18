"""data — Champions format data layer for WolfeyBot.

Modules
-------
stat_calc    : SP-based stat formula (Champions Level 50).
species      : Species types + base stats from smogon_champions_slim.json.
sets         : Per-Pokémon SP spreads, items, moves from sets-*.txt.
usage        : Metagame archetype priors.
moves        : Champions move data from champions_moves.json.
items        : Champions item data from champions_items.json.
abilities    : Champions ability data from champions_abilities.json.
speed_tiers  : Speed distribution builder + Bayesian updater.

Required data files (place in this directory):
  smogon_champions_slim.json
  sets-gen9championsvgc2026regma-1760.txt
  metagame-gen9championsvgc2026regma-1760.txt
  champions_moves.json
  champions_items.json
  champions_abilities.json

Quick-access re-exports
-----------------------
"""
# Stat formula
from .stat_calc import (
    calc_stat, calc_hp, calc_speed, calc_all_stats,
    nature_modifier, speed_range, NATURE_MODS,
)

# Species
from .species import (
    get_species, base_stats, base_spe, types_of, ability_of,
    all_species, is_legal, get_weight,
)

# Sets / usage data
from .sets import (
    get_sets, assumed_forme, mega_stones, mega_forme_for_stone,
    spread_distribution, item_distribution,
    ability_distribution, move_distribution,
    teammate_distribution,
    parse_spread, all_pokemon,
)

# Data-gap diagnostics (battle-log "data_gaps" flags)
from .diagnostics import note_gap, drain_gaps

# Per-move property flags (contact / slicing / punch / bite)
from .move_flags import move_flags, move_has_flag, is_contact

# Metagame
from .usage import (
    archetype_usage, all_archetypes,
)

# Move data
from .moves import (
    get_move, move_power, move_type, move_category,
    move_priority, is_priority_move, is_spread_move,
    needs_target, expected_hits, all_moves,
    SPREAD_TARGETS, NO_TARGET_STRINGS,
)

# Item data
from .items import (
    get_item, item_exists, speed_multiplier, type_boost_multiplier,
    is_mega_stone, all_items,
    SPEED_BOOST_ITEMS, SPEED_HALVE_ITEMS, CHOICE_ITEMS,
    FOCUS_SASH_ITEMS, TYPE_BOOST_ITEMS,
)

# Ability data
from .abilities import (
    get_ability, ability_description,
    speed_multiplier_for_ability, all_abilities,
    WEATHER_SPEED_ABILITIES, SPEED_BOOST_ABILITIES,
    SPEED_RELATED_ABILITIES, PRIORITY_ABILITIES,
    INTIMIDATE_ABILITIES, INTIMIDATE_IMMUNE_ABILITIES,
)

# Speed tiers
from .speed_tiers import (
    SpeedOutcome,
    speed_distribution, prob_faster_than, prob_outspeeds,
    most_likely_speed,
    update_speed_belief, update_speed_belief_slower,
)

__all__ = [
    # stat_calc
    "calc_stat", "calc_hp", "calc_speed", "calc_all_stats",
    "nature_modifier", "speed_range", "NATURE_MODS",
    # species
    "get_species", "base_stats", "base_spe", "types_of", "ability_of",
    "all_species", "is_legal", "get_weight",
    # sets
    "get_sets", "assumed_forme", "mega_stones", "mega_forme_for_stone",
    "spread_distribution", "item_distribution",
    "ability_distribution", "move_distribution",
    "teammate_distribution",
    "parse_spread", "all_pokemon",
    # diagnostics
    "note_gap", "drain_gaps",
    # move flags
    "move_flags", "move_has_flag", "is_contact",
    # usage
    "archetype_usage", "all_archetypes",
    # moves
    "get_move", "move_power", "move_type", "move_category",
    "move_priority", "is_priority_move", "is_spread_move",
    "needs_target", "expected_hits", "all_moves",
    "SPREAD_TARGETS", "NO_TARGET_STRINGS",
    # items
    "get_item", "item_exists", "speed_multiplier", "type_boost_multiplier",
    "is_mega_stone", "all_items",
    "SPEED_BOOST_ITEMS", "SPEED_HALVE_ITEMS", "CHOICE_ITEMS",
    "FOCUS_SASH_ITEMS", "TYPE_BOOST_ITEMS",
    # abilities
    "get_ability", "ability_description",
    "speed_multiplier_for_ability", "all_abilities",
    "WEATHER_SPEED_ABILITIES", "SPEED_BOOST_ABILITIES",
    "SPEED_RELATED_ABILITIES", "PRIORITY_ABILITIES",
    "INTIMIDATE_ABILITIES", "INTIMIDATE_IMMUNE_ABILITIES",
    # speed_tiers
    "SpeedOutcome",
    "speed_distribution", "prob_faster_than", "prob_outspeeds",
    "most_likely_speed",
    "update_speed_belief", "update_speed_belief_slower",
]
