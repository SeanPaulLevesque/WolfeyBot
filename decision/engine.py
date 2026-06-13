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

from data.moves import needs_target, is_spread_move

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
    # Showdown's species string for the male is plain "Meowstic" — the bare
    # name must be present or the on-field membership check never matches
    # (62% of Meowstic carry Fake Out; audit 0.7.6).
    "Meowstic", "Meowstic-M", "Meowstic-F", "Meowstic-M-Mega", "Meowstic-F-Mega",
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
    # 0-based index into state.opp_actives identifying *which* opponent this
    # action targets — fixed when the candidate is built (one candidate per live
    # foe for single-target moves).  None for spread / status / self / field
    # moves and switches (the choice token needs no explicit target for them).
    target_slot:   Optional[int] = None

    @property
    def is_move(self) -> bool:
        return bool(self.move_name)

    @property
    def is_switch(self) -> bool:
        return bool(self.switch_target)


# A Protect is "justified" (a legitimate split exception) when a real threat or
# field reason drove it — a genuine OHKO incoming, a partner-clears-the-threat
# Protect, or a TR/TW stall turn.  A Protect lacking any of these is "gratuitous"
# (e.g. only the FakeOut nudge, or nothing better) and is what the
# CoordinationAdjuster squeezes out in favour of attacking alongside an
# attacking partner during the joint :meth:`DecisionEngine.coordinate` pass.
_PROTECT_JUSTIFIED_PREFIXES = ("incoming_ohko", "protect:", "field_condition")


def _protect_is_justified(action: Optional["Action"]) -> bool:
    """True if *action* is a Protect backed by a real threat/field reason."""
    if action is None:
        return False
    return any(r.startswith(_PROTECT_JUSTIFIED_PREFIXES)
               for r in (action.reasons or []))


def _is_attack(action: Optional["Action"]) -> bool:
    """True if *action* is a damaging move (not a Protect-family move, not a switch)."""
    return (action is not None and action.is_move
            and not action.is_switch
            and action.move_name not in _PROTECT_MOVES)


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


class JointAdjuster(ABC):
    """
    A **phase-2** cross-slot rule, evaluated by :meth:`DecisionEngine.coordinate`
    over *pairs* of candidate actions (one per active slot) rather than over a
    single slot's list.

    This is the *only* place cross-slot effects live.  A phase-1
    :class:`ScoringModule` scores each slot's ``(move, target)`` candidates in
    isolation (blind to the partner); a ``JointAdjuster`` then expresses how a
    specific *combination* of the two slots' choices should be rewarded or
    penalised — doubling the same target, a gratuitous lone Protect beside an
    attacker, a freed Fake-Out partner, two slots switching to the same mon.

    The contract is a pure function (no mutation): given the ordered pair
    ``(slot_a, action_a)`` and ``(slot_b, action_b)`` with ``slot_a < slot_b``,
    return ``(factor_a, factor_b, reason)`` — *per-slot* multipliers attributing
    the joint effect to whichever slot it falls on (the wasteful doubler, the
    gratuitous Protect, the freed Fake-Out partner …) and a short ``reason`` (or
    ``None``).  The engine maximises ``(w_a·factor_a)·(w_b·factor_b)`` over all
    candidate pairs and, on the chosen pair, bakes each per-slot factor into that
    slot's final weight — so a decision's weight always reflects the cross-slot
    effects that shaped it.  Return ``(1.0, 1.0, None)`` when the rule doesn't apply.
    """

    name: str = "unnamed"

    @abstractmethod
    def factor(
        self,
        state: "BattleState",
        slot_a: int,
        action_a: Action,
        slot_b: int,
        action_b: Action,
    ) -> tuple[float, float, Optional[str]]:
        """Return ``(factor_a, factor_b, reason_or_None)`` for this ordered pair."""


# ── Engine ────────────────────────────────────────────────────────────────────

class DecisionEngine:
    """
    Runs :class:`ScoringModule` objects over the legal actions and returns the
    highest-weighted choice.
    """

    def __init__(
        self,
        modules: Optional[list[ScoringModule]] = None,
        joint: Optional[list[JointAdjuster]] = None,
    ):
        # Phase 1: per-slot scoring modules (run in order, blind to the partner).
        self.modules: list[ScoringModule] = modules or []
        # Phase 2: cross-slot joint adjusters, applied to candidate *pairs* by
        # :meth:`coordinate`.
        self.joint: list[JointAdjuster] = joint or []

    def add_module(self, module: ScoringModule) -> None:
        """Append *module* to the end of the phase-1 scoring chain."""
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

    # ── Phase 2: joint coordination ────────────────────────────────────────────
    def _active_decision_slots(self, state: "BattleState") -> list[int]:
        """Slots that need a decision this turn (skip empty / fainted actives)."""
        slots: list[int] = []
        for s in range(len(state.moves_per_slot)):
            mon = state.my_actives[s] if s < len(state.my_actives) else None
            if mon is not None and getattr(mon, "fainted", False):
                continue
            slots.append(s)
        return slots

    @staticmethod
    def _winner(ranked: list["Action"]) -> "Action":
        """The best action from a ranked list (first positive weight, else first)."""
        if not ranked:
            return Action(label="Struggle", move_name="Struggle")
        return next((a for a in ranked if a.weight > 0), ranked[0])

    def _joint_factors(
        self, state: "BattleState",
        slot_a: int, a0: "Action", slot_b: int, a1: "Action",
    ) -> tuple[float, float, list[str]]:
        """Combined per-slot multipliers (and reasons) from every joint adjuster."""
        fa, fb = 1.0, 1.0
        reasons: list[str] = []
        for adj in self.joint:
            try:
                ga, gb, reason = adj.factor(state, slot_a, a0, slot_b, a1)
            except Exception:
                _log.exception("JointAdjuster '%s' raised; treating as x1.0", adj.name)
                continue
            fa *= ga
            fb *= gb
            if (ga != 1.0 or gb != 1.0) and reason:
                reasons.append(reason)
        return fa, fb, reasons

    def _pair_value(
        self, state: "BattleState",
        slot_a: int, a0: "Action", slot_b: int, a1: "Action",
    ) -> float:
        """Joint value of a candidate pair: ``(w0·factor_a)·(w1·factor_b)``.

        With every adjuster inert (factors 1.0) this is ``w0 × w1``, whose argmax
        is each slot's *independent* best — so the joint pass only moves a choice
        off the per-slot optimum when a real cross-slot effect makes a different
        pair score higher.
        """
        w0, w1 = max(a0.weight, 0.0), max(a1.weight, 0.0)
        if w0 == 0.0 or w1 == 0.0:
            return 0.0
        fa, fb, _ = self._joint_factors(state, slot_a, a0, slot_b, a1)
        return (w0 * fa) * (w1 * fb)

    def _bake_pair(
        self, state: "BattleState",
        slot_a: int, a0: "Action", slot_b: int, a1: "Action",
    ) -> None:
        """Fold the chosen pair's joint factors into each action's weight + reasons,
        so a final decision's weight reflects the cross-slot effects that shaped it."""
        fa, fb, reasons = self._joint_factors(state, slot_a, a0, slot_b, a1)
        a0.weight *= fa
        a1.weight *= fb
        for r in reasons:           # pair-level notes — relevant to both slots
            a0.reasons.append(r)
            a1.reasons.append(r)

    def coordinate(
        self, state: "BattleState",
    ) -> tuple[dict[int, "Action"], dict[int, list["Action"]]]:
        """
        Joint phase-2 selection — the single decision point that replaces the old
        greedy "score slot 0, then slot 1, then a recoordinate re-pass".

        Phase 1 (:meth:`scored_actions`) has already scored every ``(move, target)``
        candidate per slot *in isolation*.  This method then picks the best
        **combination** of the two active slots' actions by maximising
        :meth:`_pair_value` over all candidate pairs, so cross-slot repairs the old
        re-pass did by hand now fall out of choosing the best pair:

        * **Overkill / focus-fire** — a pair where both attack the same target a
          partner already confirm-OHKOs is penalised by the doubling adjuster, so
          the pair that *spreads* onto the survivor wins (the emergent "redirect").
        * **De-coordination** — a pair with a gratuitous lone Protect beside an
          attacking partner is penalised, so the double-attack pair wins.

        Because slot 0 is never committed before slot 1 is seen, there is no
        order-induced blind spot left to patch.

        Returns ``(chosen, ranked)`` — the chosen Action per slot and the phase-1
        ranked list per slot (for the recorder / logging) — and writes the chosen
        actions back into ``state.my_slot_decisions``.
        """
        slots = self._active_decision_slots(state)
        ranked: dict[int, list["Action"]] = {s: self.scored_actions(state, s) for s in slots}
        chosen: dict[int, "Action"] = {}
        decisions: list[Optional["Action"]] = [None] * len(state.moves_per_slot)

        live_slots = [s for s in slots if ranked.get(s)]

        if len(live_slots) >= 2:
            # Two live slots → choose the best joint pair.  (Doubles never has more
            # than two of our active slots; any beyond the first two fall back to
            # their independent best below.)
            s0, s1 = live_slots[0], live_slots[1]
            best_pair: Optional[tuple["Action", "Action"]] = None
            best_val = float("-inf")
            for a0 in ranked[s0]:
                for a1 in ranked[s1]:
                    val = self._pair_value(state, s0, a0, s1, a1)
                    if val > best_val:
                        best_val, best_pair = val, (a0, a1)
            a0, a1 = best_pair if best_pair else (self._winner(ranked[s0]), self._winner(ranked[s1]))
            self._bake_pair(state, s0, a0, s1, a1)
            chosen[s0], chosen[s1] = a0, a1
            decisions[s0], decisions[s1] = a0, a1
            handled = {s0, s1}
        else:
            handled = set()

        # Any remaining slots (single-active turns, or a 3rd slot) take their
        # independent best.
        for s in slots:
            if s in handled:
                continue
            chosen[s] = self._winner(ranked.get(s) or [])
            decisions[s] = chosen[s]

        state.my_slot_decisions = decisions
        return chosen, ranked


# ── Action builder ────────────────────────────────────────────────────────────

def _live_foe_slots(state: "BattleState") -> list[int]:
    """0-based indices of opponent active slots that are alive."""
    return [i for i, o in enumerate(state.opp_actives)
            if o is not None and not getattr(o, "fainted", False)]


def _move_candidates(state: "BattleState", name: str) -> list[Action]:
    """Return the candidate Action(s) for move *name*.

    A **single-target foe** move becomes one candidate per live opponent — so
    *which target* is a first-class part of the action's identity, fixed at
    build time, rather than a field that later modules pick and overwrite.  This
    is what lets the joint :meth:`DecisionEngine.coordinate` choose between
    "both hit X" and "split X / Y" as distinct board states.

    Spread / status / self / field moves — and the degenerate case of no live
    foe — collapse to a single candidate with ``target_slot=None`` (the choice
    token needs no explicit target for them).
    """
    single_foe = needs_target(name) and not is_spread_move(name)
    foes = _live_foe_slots(state)
    if single_foe and foes:
        return [Action(label=name, move_name=name, target_slot=f) for f in foes]
    return [Action(label=name, move_name=name)]


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
        # One candidate per live foe for single-target moves (fixed target_slot).
        actions.extend(_move_candidates(state, name))

    # Guard: our own Disable/Encore tracking must never empty the move list while
    # the server still offers a usable move.  That only happens when our lock is
    # stale (Encore expired, or the encored move was just Disabled) — trust the
    # server and drop our filter rather than wrongly falling back to Struggle.
    if not actions and server_usable:
        for n in server_usable:
            actions.extend(_move_candidates(state, n))

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


