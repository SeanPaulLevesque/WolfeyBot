"""decision — Modular move picker for WolfeyBot doubles.

Re-exports the full public API from :mod:`decision.engine` and
:mod:`decision.modules` so that the common import patterns::

    from decision import make_engine, Action
    from decision import DecisionEngine, ScoringModule

continue to work unchanged after the package was split from a single
``decision.py`` module.
"""
from decision.engine import (  # noqa: F401
    Action,
    ScoringModule,
    JointAdjuster,
    DecisionEngine,
    _build_actions,
    _PROTECT_MOVES,
    _FAKE_OUT_USERS,
)
from decision.modules import (  # noqa: F401
    DamageOutputModule,
    ThreatEliminationModule,
    DoomedModule,
    PriorityKillModule,
    PriorityBlockModule,
    ProtectValueModule,
    PartnerClearsAdjuster,
    EndgameStallModule,
    TurnOrderModule,
    UrgencyModule,
    SetupDenialModule,
    SetupType,
    _SETUP_TYPES,
    SETUP_URGENCY,
    SETUP_DENIAL,
    ConsecutiveProtectModule,
    SwitchModule,
    DoublingAdjuster,
    CoordinationAdjuster,
    FakeOutAdjuster,
    SwitchCollisionAdjuster,
    OppProtectRecencyModule,
    FakeOutModule,
    FieldConditionModule,
    _fake_out_threatened,
    _move_undeliverable,
    _our_combatant,
    _opp_combatant,
    _our_stats,
    _assumed_ability,
    _effective_ability,
    _assumed_item,
    _effective_item,
    _opp_item,
    _assumed_species,
    _offense_species,
    _defense_species,
    make_engine,
)
