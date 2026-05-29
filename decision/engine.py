"""decision/engine.py — Core types and engine for the WolfeyBot decision system.

Architecture
------------
Each active Pokémon slot is given a list of *Actions* (its available moves plus
any bench switches).  Every action starts at ``weight = 1.0``.  A chain of
:class:`ScoringModule` objects then multiplies those weights; the highest-weight
action is returned as the decision for that slot.

Concrete scoring modules live in :mod:`decision.modules`.  The public API
(including :func:`decision.modules.make_engine`) is re-exported from
:mod:`decision.__init__` so callers can simply::

    from decision import make_engine, Action

Weight conventions
------------------
* All actions start at ``weight = 1.0``.
* Modules **multiply** (never add).  This keeps vetoes clean (x0 = never
  pick), bonuses composable (x2 then x3 = x6), and the scale intuitive:
  >1 = encouraged, <1 = discouraged, 0 = forbidden.
* No normalisation is done.  Only relative ordering matters.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from battle import BattleState, Pokemon

_log = logging.getLogger(__name__)

# ── Constants shared with modules ─────────────────────────────────────────────

_PROTECT_MOVES = frozenset({
    "Protect", "Detect", "King's Shield", "Baneful Bunker", "Obstruct",
    "Wide Guard", "Quick Guard", "Crafty Shield", "Mat Block",
})

# Species that can use Fake Out (priority +3, flinches target, first-turn only).
# Used by FakeOutModule to detect when a fresh switch-in poses a flinch threat.
# Derived from Champions format usage data (sets-gen9championsvgc2026regma).
# Both pre-mega and mega forms are listed because the engine checks the current
# species name, which may be either form depending on whether mega-evolution
# has occurred yet this battle.
_FAKE_OUT_USERS = frozenset({
    "Blastoise", "Blastoise-Mega",
    "Incineroar",
    "Infernape",
    "Kangaskhan", "Kangaskhan-Mega",
    "Liepard",
    "Lopunny", "Lopunny-Mega",
    "Medicham", "Medicham-Mega",
    "Meowstic-M", "Meowstic-F", "Meowstic-M-Mega", "Meowstic-F-Mega",
    "Morpeko",
    "Mr. Rime",
    "Pikachu",
    "Raichu", "Raichu-Alola",
    "Sableye", "Sableye-Mega",
    "Salazzle",
    "Simipour",
    "Sneasler",
    "Tinkaton",
    "Toxicroak",
    "Weavile",
})


# ── Core data types ───────────────────────────────────────────────────────────

@dataclass
class Action:
    """One possible choice for a single active slot this turn."""

    label:         str            # display name: "Dragon Claw" / "Switch Sylveon"
    move_name:     str   = ""     # non-empty for move actions
    switch_target: str   = ""     # species name, non-empty for switch actions
    weight:        float = 1.0    # starts at 1.0; modules multiply this value
    reasons:       list[str] = field(default_factory=list)
    # 0-based index into state.opp_actives for the recommended target in doubles.
    # None means "use default targeting logic".  Modules set this to the opponent
    # that drove their scoring decision so move + target stay consistent.
    target_slot:   Optional[int] = None
    # Per-opponent damage fractions filled by DamageOutputModule.
    # Maps opp_slot → (hp_fraction_avg, hp_fraction_min).
    # Used by DoublingUpModule to re-score a redirected move against its new
    # target without losing TurnOrder and other non-target-specific factors.
    target_hp_fractions: dict = field(default_factory=dict)

    @property
    def is_move(self) -> bool:
        return bool(self.move_name)

    @property
    def is_switch(self) -> bool:
        return bool(self.switch_target)


# ── Module base class ─────────────────────────────────────────────────────────

class ScoringModule(ABC):
    """
    Base class for all decision modules.

    Subclass this and implement :meth:`score`.  The engine calls modules in
    registration order; every module receives the *same* ``actions`` list so
    each module's changes compound on top of all previous ones.
    """

    name: str = "unnamed"

    @abstractmethod
    def score(
        self,
        state: "BattleState",
        slot: int,
        actions: list[Action],
    ) -> None:
        """
        Adjust ``action.weight`` in-place for each action in *actions*.

        Contract:
        * Use ``action.weight *= factor`` -- never ``+=``.
        * To veto an action: ``action.weight *= 0.0``.
        * Append a short string to ``action.reasons`` to explain each change.
        * If data is unavailable, silently return -- do not crash the engine.
        """


# ── Engine ────────────────────────────────────────────────────────────────────

class DecisionEngine:
    """
    Runs :class:`ScoringModule` objects over the legal actions and returns the
    highest-weighted choice.
    """

    def __init__(self, modules: Optional[list[ScoringModule]] = None):
        self.modules: list[ScoringModule] = modules or []

    def add_module(self, module: ScoringModule) -> None:
        """Append *module* to the end of the scoring chain."""
        self.modules.append(module)

    def scored_actions(self, state: "BattleState", slot: int) -> list[Action]:
        """
        Build actions, run all modules, and return the list sorted
        highest-weight first.  Useful for logging and debugging.
        """
        actions = _build_actions(state, slot)
        if not actions:
            return []

        for module in self.modules:
            try:
                module.score(state, slot, actions)
            except Exception:
                _log.exception(
                    "ScoringModule '%s' raised an exception; skipping it",
                    module.name,
                )

        return sorted(actions, key=lambda a: -a.weight)

    def decide(self, state: "BattleState", slot: int) -> Action:
        """
        Return the best :class:`Action` for *slot* given *state*.

        If every weight is 0.0, returns the first available action rather than
        raising so the bot always has something to send.
        """
        ranked = self.scored_actions(state, slot)
        if not ranked:
            return Action(label="Struggle", move_name="Struggle")

        winner = next((a for a in ranked if a.weight > 0), ranked[0])
        _log.debug(
            "slot %d -> %s  (weight=%.2f)  %s",
            slot, winner.label, winner.weight, winner.reasons,
        )
        return winner


# ── Action builder ────────────────────────────────────────────────────────────

def _build_actions(state: "BattleState", slot: int) -> list[Action]:
    """
    Return every legal action for *slot*.

    Move source: ``state.moves_per_slot[slot]`` -- the server's own list, which
    already reflects Choice locks, Disable, Taunt, and any other restriction.

    Switch source: ``state.available_switches`` -- bench Pokemon that are alive
    and not currently active.  Switches are suppressed for a slot the server has
    flagged ``trapped`` (Shadow Tag, Arena Trap, a trapping move, etc.) so we
    never propose an illegal switch and get stuck re-sending a rejected choice.
    """
    actions: list[Action] = []

    # ── Moves ─────────────────────────────────────────────────────────────────
    move_dicts = (state.moves_per_slot[slot]
                  if slot < len(state.moves_per_slot) else [])

    # Disable: move the server never flags disabled but we tracked via |-activate|
    disabled_move = (state.my_disabled_moves[slot]
                     if slot < len(state.my_disabled_moves) else None)
    # Encore: if set, only the locked move is legal
    encored_move = (state.my_encored_moves[slot]
                    if slot < len(state.my_encored_moves) else None)

    # Moves the *server* considers usable this turn (it already accounts for PP,
    # Disable, Taunt, Encore, Choice locks, etc.).  This is the ground truth.
    server_usable = [
        md.get("move", "") for md in move_dicts
        if md.get("move") and md.get("move", "").lower() != "struggle"
        and not md.get("disabled", False)
    ]

    for md in move_dicts:
        if md.get("disabled", False):
            continue
        name = md.get("move", "")
        if not name or name.lower() == "struggle":
            continue
        # Skip a Disabled move even when the server hasn't flagged it
        if disabled_move and name.lower() == disabled_move.lower():
            continue
        # Skip every move except the Encored one
        if encored_move and name.lower() != encored_move.lower():
            continue
        actions.append(Action(label=name, move_name=name))

    # Guard: our own Disable/Encore tracking must never empty the move list while
    # the server still offers a usable move.  That only happens when our lock is
    # stale (Encore expired, or the encored move was just Disabled) — trust the
    # server and drop our filter rather than wrongly falling back to Struggle.
    if not actions and server_usable:
        actions = [Action(label=n, move_name=n) for n in server_usable]

    if not actions:
        # Genuinely no legal move (server offered none) → Struggle.
        actions.append(Action(label="Struggle", move_name="Struggle"))

    # ── Switches ──────────────────────────────────────────────────────────────
    # A trapped slot cannot switch; offering switches risks an illegal-choice
    # loop (server rejects → we re-decide identically → reject again).
    trapped = (state.trapped[slot]
               if slot < len(getattr(state, "trapped", []) or []) else False)
    force_switch = (state.force_switch[slot]
                    if slot < len(state.force_switch) else False)
    if not trapped or force_switch:
        for bench in state.available_switches:
            actions.append(Action(
                label=f"Switch {bench.species}",
                switch_target=bench.species,
            ))

    return actions


