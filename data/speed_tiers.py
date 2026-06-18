"""speed_tiers.py — Speed tier estimation and Bayesian updater.

Given a Pokémon's name this module builds a probability-weighted distribution
of *raw* Speed stat values at Level 50, drawing on:

  * Common SP spread distributions from the sets file
  * Base Speed from species data

This is a pure **spread** distribution.  Item and field effects (Choice Scarf,
Iron Ball, Tailwind, paralysis, weather abilities) are *not* applied here —
turn_order applies them from the single modal assumed item.  See
``data.items.speed_multiplier`` and ``decision.modules._effective_item``.

Turn-order reasoning then uses Bayesian updates each time an actual move
order is observed in battle.

Example usage::

    from data.speed_tiers import speed_distribution, update_speed_belief

    # Prior: what speed values is Garchomp likely to have?
    dist = speed_distribution("Garchomp")
    for outcome in dist[:3]:
        print(f"{outcome.speed:3d}  p={outcome.probability:.3f}"
              f"  {outcome.nature} / spe={outcome.sp}")

    # After seeing Garchomp move before our 135-speed Pokémon:
    dist = update_speed_belief(dist, observed_faster_than=135)
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Optional

from .species import base_spe
from .sets import spread_distribution, parse_spread
from .stat_calc import calc_speed


# ── Data container ───────────────────────────────────────────────────────────

@dataclass
class SpeedOutcome:
    """One possible Speed configuration (spread) with an associated probability.

    This is a pure *spread* distribution — item and field modifiers (Choice
    Scarf, Iron Ball, Tailwind, paralysis, weather abilities) are applied by
    turn_order from the modal assumed item, not here.
    """
    speed:       int          # Speed from this spread (== raw_speed; no item here)
    raw_speed:   int          # alias kept for turn_order's modifier pipeline
    nature:      str          # e.g. "Jolly"
    sp:          int          # Speed SP value used (0–32)
    probability: float        # relative weight (distribution sums to ~1.0)


# ── Core builder ─────────────────────────────────────────────────────────────

def speed_distribution(
        name: str,
        *,
        assume_iv: int = 31,
        level: int = 50,
        min_spread_pct: float = 1.0,
) -> list[SpeedOutcome]:
    """
    Return a probability-weighted list of :class:`SpeedOutcome` for *name*.

    Probability is derived from spread usage % (from sets data).  Outcomes with
    the same Speed are merged.  This is a pure spread distribution — item
    effects (e.g. Choice Scarf) are applied later by turn_order, not here.

    Args:
        name:           Pokémon name (e.g. "Garchomp").
        assume_iv:      IV assumption (default 31 = perfect).
        level:          Battle level (default 50).
        min_spread_pct: Ignore spreads below this percentage.  Spreads in the
                        "Other" bucket are always omitted.
    """
    base = base_spe(name)
    if base is None:
        return []

    spreads = spread_distribution(name)        # [(spread_str, pct), …]

    # Filter to meaningful spreads and normalise within known mass
    relevant   = [(s, p) for s, p in spreads if p >= min_spread_pct]
    known_mass = sum(p for _, p in relevant) / 100.0

    if not relevant:
        return _uninformed_distribution(base, assume_iv, level)

    raw_outcomes: list[SpeedOutcome] = []
    for spread_str, spread_pct in relevant:
        parsed = parse_spread(spread_str)
        if parsed is None:
            continue
        sp_val  = parsed["spe"]
        nature  = parsed["nature"]
        # Normalise: spread share within known mass × total known fraction
        sp_prob = (spread_pct / 100.0) / known_mass

        raw_spd = calc_speed(base, sp_val, nature, assume_iv, level)

        raw_outcomes.append(SpeedOutcome(
            speed=raw_spd, raw_speed=raw_spd,
            nature=nature, sp=sp_val,
            probability=sp_prob,
        ))

    return _merge_and_sort(raw_outcomes)


# ── Bayesian updaters ─────────────────────────────────────────────────────────

def update_speed_belief(
        prior: list[SpeedOutcome],
        observed_faster_than: int,
) -> list[SpeedOutcome]:
    """
    Bayesian update: the Pokémon moved *before* a Pokémon with
    ``observed_faster_than`` Speed (ignoring priority moves).

    Removes outcomes where ``speed <= observed_faster_than`` and
    renormalises.  Returns the original distribution unchanged if no
    outcomes survive (contradictory observation).
    """
    compatible = [o for o in prior if o.speed > observed_faster_than]
    return _renormalise(compatible) if compatible else prior


def update_speed_belief_slower(
        prior: list[SpeedOutcome],
        observed_slower_than: int,
) -> list[SpeedOutcome]:
    """
    Bayesian update: the Pokémon moved *after* a Pokémon with
    ``observed_slower_than`` Speed.

    Keeps only outcomes where ``speed < observed_slower_than``.
    """
    compatible = [o for o in prior if o.speed < observed_slower_than]
    return _renormalise(compatible) if compatible else prior


# ── Query helpers ─────────────────────────────────────────────────────────────

def prob_faster_than(
        name: str,
        threshold_speed: int,
        **kwargs,
) -> float:
    """
    Return ``P(Pokémon's Speed > threshold_speed)`` ∈ [0, 1].

    Returns 0.5 (coin-flip) when no data is available.
    """
    dist = speed_distribution(name, **kwargs)
    if not dist:
        return 0.5
    total   = sum(o.probability for o in dist)
    faster  = sum(o.probability for o in dist if o.speed > threshold_speed)
    # Clamp: float accumulation can overshoot [0,1] when one side dominates.
    return min(1.0, max(0.0, faster / total)) if total else 0.5


def prob_outspeeds(
        name_a: str,
        name_b: str,
        **kwargs,
) -> float:
    """
    Return ``P(Pokémon A moves before Pokémon B)`` ∈ [0, 1].

    Folds over the joint distribution, treating each pair of outcomes as
    independent.
    """
    dist_a = speed_distribution(name_a, **kwargs)
    dist_b = speed_distribution(name_b, **kwargs)
    if not dist_a or not dist_b:
        return 0.5

    total_b = sum(o.probability for o in dist_b)
    if total_b == 0:
        return 0.5

    result = 0.0
    for a in dist_a:
        for b in dist_b:
            if a.speed > b.speed:
                result += a.probability * (b.probability / total_b)
    total_a = sum(o.probability for o in dist_a)
    # Clamp: float accumulation can overshoot [0,1] when one side dominates.
    return min(1.0, max(0.0, result / total_a)) if total_a else 0.5


def most_likely_speed(name: str, **kwargs) -> Optional[int]:
    """Return the single most probable Speed value, or None."""
    dist = speed_distribution(name, **kwargs)
    return dist[0].speed if dist else None


# ── Internal helpers ─────────────────────────────────────────────────────────

def _merge_and_sort(outcomes: list[SpeedOutcome]) -> list[SpeedOutcome]:
    """Merge outcomes that share the same Speed, then sort by probability."""
    merged: dict[int, SpeedOutcome] = {}
    for o in outcomes:
        key = o.speed
        if key in merged:
            merged[key] = replace(
                merged[key], probability=merged[key].probability + o.probability
            )
        else:
            merged[key] = o
    return sorted(merged.values(), key=lambda x: -x.probability)


def _renormalise(outcomes: list[SpeedOutcome]) -> list[SpeedOutcome]:
    total = sum(o.probability for o in outcomes)
    if total == 0:
        return outcomes
    return sorted(
        [replace(o, probability=o.probability / total) for o in outcomes],
        key=lambda x: -x.probability,
    )


def _uninformed_distribution(
        base_speed: int,
        iv: int,
        level: int,
) -> list[SpeedOutcome]:
    """Fallback when no set data exists: sample a coarse grid."""
    natures = [
        ("Jolly",   "spe_boost"),
        ("Timid",   "spe_boost"),
        ("Neutral", "neutral"),
        ("Adamant", "neutral"),   # Adamant doesn't affect Speed
        ("Modest",  "neutral"),
    ]
    sp_values = [0, 8, 16, 24, 32]
    base_prob = 1.0 / (len(natures) * len(sp_values))

    outcomes: list[SpeedOutcome] = []
    for nat_name, _ in natures:
        for sp in sp_values:
            raw = calc_speed(
                base_speed, sp,
                "Hardy" if nat_name == "Neutral" else nat_name,
                iv, level,
            )
            outcomes.append(SpeedOutcome(
                speed=raw, raw_speed=raw, nature=nat_name, sp=sp,
                probability=base_prob,
            ))
    return _merge_and_sort(outcomes)
