"""data/diagnostics.py — Deduped collector for data-layer lookup failures.

When a species/forme lookup silently fails (no base stats, no types, no usage
sets, no team entry), the engine degrades quietly: the opponent scores as
harmless, every matchup goes neutral, or a slot is skipped entirely.  The
failure sites call :func:`note_gap`; the battle recorder drains the set into
an optional ``"data_gaps"`` field of the battle log, so the flag appears only
when something actually went wrong during that battle.

Kinds in use:
  * ``stats``       — no base stats / usage spread for a species
                      (damage._most_common_stats → opponent invisible)
  * ``types``       — types_of() returned nothing
                      (full_damage_calc → all matchups neutral 1.0)
  * ``moves``       — no usage move data; synthetic STAB fallback used
                      (damage.incoming_damage)
  * ``sets``        — no usage sets entry at all (_assumed_ability)
  * ``team_member`` — find_member() failed for one of OUR active mons
                      (fact loops skip the slot)

The collector is process-global and battle-scoped by convention:
``BattleRecorder.__init__`` clears it (discarding stale gaps from a previous
battle or aborted session) and ``BattleRecorder._save`` drains it.  Battles
are played one at a time; concurrent battles would cross-contaminate.
"""
from __future__ import annotations

_GAPS: set[tuple[str, str]] = set()


def note_gap(kind: str, name: str) -> None:
    """Record a failed data lookup (deduped)."""
    _GAPS.add((kind, name))


def drain_gaps() -> list[str]:
    """Return all recorded gaps as sorted ``"kind:name"`` strings and clear."""
    out = sorted(f"{k}:{n}" for k, n in _GAPS)
    _GAPS.clear()
    return out
