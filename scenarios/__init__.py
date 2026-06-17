"""Scenario definitions for decision snapshots.

A *scenario* is a team-parameterised board-state template: given a team it
produces concrete ``BattleState``s, which the engine scores.  ``tools/gen_snapshot.py``
renders a scenario for a team into ``snapshots/<scenario>/<team>.md`` — a
"snapshot" that doubles as a human-readable table and a regression baseline.
"""
