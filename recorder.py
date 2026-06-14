"""recorder.py — Battle data recorder for WolfeyBot.

Saves a compact JSON file per battle to:
    Battle Data/{version}/{battle_id}.json

Compact format (recorder v2, introduced 0.3.5):
  - Decisions grouped by turn — state snapshot is shared between slot 0 and
    slot 1, eliminating the largest source of redundancy in v1.
  - HP stored as a 0.0–1.0 fraction instead of "cur/max" strings.
  - Abbreviated keys: id, v, t, n, w, te, tr, my, opp, team, dec, sl, ch, ct,
    acts, lb, ts, tg, sw, r, sts, mv.
  - No whitespace (separators=(',', ':')) — saves ~30 % on large files.
  - Null / empty / False fields omitted.
  - Only the top-_MAX_ACTIONS actions stored per slot (weight > 1.0, minimum
    _MIN_ACTIONS, always including the chosen action).

Key abbreviations
-----------------
Turn-level:
  n   turn number
  w   weather
  te  terrain
  tr  trick room (True when active, omitted otherwise)
  my  our actives list  [{"s": species, "hp": 0-1, "sts": status?}, ...]
  opp opponent actives  [{"s": species, "hp": 0-1, "sts": status?, "mv": [...]?}, ...]
  team full team snapshot  [{"s": species, "hp": 0-1}, ...]
  dec per-slot decisions   [{sl, ch, acts}, ...]

Decision-level:
  sl  slot index (0 or 1)
  ch  chosen action label
  ct  chosen action's target species (resolved from ts; omitted if no opp target)

Action-level:
  lb  label
  w   weight (2 dp)
  ts  target_slot (omitted if null)
  tg  target species (resolved from ts; omitted if no opp target)
  sw  switch_target (omitted if falsy)
  r   reasons list (omitted if empty)

Usage::

    from recorder import BattleRecorder
    rec = BattleRecorder("battle-gen9…-1234", "0.3.5")
    rec.record_decision(state, slot=0, ranked_actions=engine.scored_actions(state, 0))
    rec.record_outcome(won=True)   # saves automatically
"""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from data import drain_gaps

_log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from decision import Action
    from battle import BattleState

# Absolute path to the project root (same directory as this file).
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Actions kept per slot: up to _MAX_ACTIONS with weight > 1.0,
# padded to _MIN_ACTIONS, always including the chosen action.
_MAX_ACTIONS = 4
_MIN_ACTIONS = 3


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hp_frac(hp: int, max_hp: int) -> float:
    """Return HP as a 0.0–1.0 fraction, rounded to 3 decimal places."""
    if max_hp <= 0:
        return 0.0
    return round(hp / max_hp, 3)


def _compact_action(a: "Action", opp_species: Optional[list] = None) -> dict:
    """Serialise one Action to a compact dict; omit null / empty fields.

    *opp_species* maps opponent slot index -> species name (or None).  When
    given, the action's numeric ``ts`` target is also resolved to a ``tg``
    species so the move's target is readable without cross-referencing the opp
    list.  ``ts`` is kept for backward compatibility.
    """
    out: dict = {"lb": a.label, "w": round(a.weight, 2)}
    if a.target_slot is not None:
        out["ts"] = a.target_slot
        if (opp_species is not None
                and 0 <= a.target_slot < len(opp_species)
                and opp_species[a.target_slot]):
            out["tg"] = opp_species[a.target_slot]
    if a.switch_target:
        out["sw"] = a.switch_target
    if a.reasons:
        out["r"] = list(a.reasons)
    return out


def _select_actions(ranked: list["Action"]) -> list["Action"]:
    """Return a sorted subset of *ranked*, obeying _MAX/_MIN_ACTIONS rules."""
    if not ranked:
        return []
    chosen = ranked[0]   # highest weight = chosen action

    # Start with actions whose weight exceeds 1.0 (capped at _MAX_ACTIONS)
    selected: list["Action"] = [a for a in ranked if a.weight > 1.0][:_MAX_ACTIONS]
    seen = {a.label for a in selected}

    # Always include chosen action
    if chosen.label not in seen:
        selected.append(chosen)
        seen.add(chosen.label)

    # Pad to _MIN_ACTIONS if needed
    for a in ranked:
        if len(selected) >= _MIN_ACTIONS:
            break
        if a.label not in seen:
            selected.append(a)
            seen.add(a.label)

    # Always include a penalised Protect action when the consecutive-protect
    # penalty fired.  The penalised weight (x0.1) normally falls below the
    # weight > 1.0 threshold so the reason is invisible in the JSON.  Including
    # it explicitly makes consecutive-protect auditing possible without cross-
    # referencing previous turns.
    for a in ranked:
        if a.label in seen:
            continue
        if any("used Protect last turn" in r for r in a.reasons):
            selected.append(a)
            seen.add(a.label)
            break

    # Keep weight-descending order so acts[0] is always the chosen action
    selected.sort(key=lambda a: a.weight, reverse=True)
    return selected


# ── Recorder ─────────────────────────────────────────────────────────────────

def _snapshot_state(state: "BattleState") -> dict:
    """
    Capture an immutable snapshot of the fields needed for turn serialisation.

    ``BattleState`` is a mutable object that continues to be modified as the
    battle progresses.  Storing a reference and reading it at save-time would
    record the *final* HP values for every turn — a silent bug that makes all
    earlier turns look as if every Pokémon had already fainted.

    This function extracts the relevant scalar and list fields immediately so
    the recorded HP/status values match the moment the decision was made.
    """
    def _mon_snap(mon) -> Optional[dict]:
        if mon is None:
            return None
        return {
            "species": mon.species,
            "hp":      mon.hp,
            "max_hp":  mon.max_hp,
            "status":  mon.status,
        }

    def _opp_snap(mon) -> Optional[dict]:
        if mon is None:
            return None
        return {
            "species": mon.species,
            "hp":      mon.hp,
            "max_hp":  mon.max_hp,
            "status":  mon.status,
            "moves":   list(mon.moves),
        }

    return {
        "weather":    state.weather,
        "terrain":    state.terrain,
        "trick_room": state.trick_room,
        "my_actives": [_mon_snap(m) for m in state.my_actives],
        "opp_actives":[_opp_snap(o) for o in state.opp_actives],
        "my_team":    [_mon_snap(p) for p in state.my_team],
    }


class BattleRecorder:
    """Records decisions and outcomes for one battle and persists them to disk."""

    def __init__(self, battle_id: str, version: str):
        self.battle_id   = battle_id
        self.version     = version
        self._started_at = datetime.now(timezone.utc).isoformat()
        # Discard data-gap flags left over from a previous battle (or an
        # aborted one) so this battle's "data_gaps" reflects only itself.
        drain_gaps()
        # Keyed by turn number.  Each value:
        #   {"snap": dict (immutable state snapshot), "slots": {slot: [Action]}}
        self._turns: dict[int, dict] = defaultdict(lambda: {"snap": None, "slots": {}})
        self._outcome: Optional[str] = None
        # Live reference to the battle state (set on first record_decision) so
        # _save can read state.events_log — the actual move order + damage that
        # resolved each turn (0.8.1 instrumentation).
        self._state = None
        # Team preview selection — set by record_preview() and written to "preview"
        # in the top-level JSON payload.  None if team preview was never recorded.
        self._preview: Optional[dict] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def record_preview(
        self,
        opp_team: list[str],
        slots:    list[int],
        bring:    list[str],
        mega:     Optional[str],
    ) -> None:
        """Record team preview selection data.

        Args:
            opp_team: Opponent's revealed species list (from |poke| messages).
            slots:    1-based slot indices of our selected team, leads-first.
            bring:    Species names in slot order (parallel to *slots*).
            mega:     Base species name of the designated mega, or ``None``.
        """
        d: dict = {
            "opp":   list(opp_team),
            "slots": list(slots),
            "bring": list(bring),
        }
        if mega:
            d["mega"] = mega
        self._preview = d

    def record_decision(
        self,
        state:          "BattleState",
        slot:           int,
        ranked_actions: list["Action"],
    ) -> None:
        """Append the scored action list for *slot* on the current turn.

        The state snapshot is taken eagerly on the *first* call for each turn
        so that HP values reflect the battle state at decision time, not the
        final state when the file is written.  Both slots share the same
        snapshot (taken from whichever slot fires first — the state is
        identical for both within a single request cycle).
        """
        self._state = state   # live ref; events_log filled as the turn resolves
        entry = self._turns[state.turn]
        if entry["snap"] is None:
            entry["snap"] = _snapshot_state(state)   # freeze now, not at save time
        entry["slots"][slot] = list(ranked_actions)

    def record_outcome(self, won: bool) -> None:
        """Record the battle result and write the JSON file to disk.

        Also updates the cumulative opponent-lead frequency stats so that
        future team-preview lead selection improves over time.  The stat
        update is wrapped in a bare ``except`` so that any I/O failure
        (missing directory, permission error, corrupted JSON) never prevents
        the battle file from being saved.
        """
        self._outcome = "win" if won else "loss"

        # ── Record opponent lead stats ────────────────────────────────────
        try:
            t1 = self._turns.get(1)
            if t1 and t1.get("snap"):
                opp_actives = t1["snap"].get("opp_actives", [])
                leads = [o["species"] for o in opp_actives if o is not None]
                if leads:
                    from data.lead_stats import record_leads
                    record_leads(leads)
        except Exception:
            pass  # never let stat recording block the battle save

        self._save()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_turn(self, turn_num: int, entry: dict) -> dict:
        """Convert one buffered turn entry into a compact dict."""
        snap: dict = entry["snap"]   # frozen dict captured at decision time
        t: dict = {"n": turn_num}

        # Shared condition fields — omit falsy values
        if snap["weather"]:
            t["w"] = snap["weather"]
        if snap["terrain"]:
            t["te"] = snap["terrain"]
        if snap["trick_room"]:
            t["tr"] = True

        # Our actives — list indexed by slot; None entries preserve slot alignment
        my_list = []
        for mon in snap["my_actives"]:
            if mon is None:
                my_list.append(None)
            else:
                m: dict = {"s": mon["species"], "hp": _hp_frac(mon["hp"], mon["max_hp"])}
                if mon["status"]:
                    m["sts"] = mon["status"]
                my_list.append(m)
        if any(x is not None for x in my_list):
            t["my"] = my_list

        # Opponent actives — list indexed by slot; None entries preserved
        opp_list = []
        for o in snap["opp_actives"]:
            if o is None:
                opp_list.append(None)
            else:
                oe: dict = {"s": o["species"], "hp": _hp_frac(o["hp"], o["max_hp"])}
                if o["status"]:
                    oe["sts"] = o["status"]
                if o["moves"]:
                    oe["mv"] = sorted(o["moves"])
                opp_list.append(oe)
        if any(x is not None for x in opp_list):
            t["opp"] = opp_list

        # Full team snapshot (tracks HP attrition and faints across the battle)
        team_list = [
            {"s": p["species"], "hp": _hp_frac(p["hp"], p["max_hp"])}
            for p in snap["my_team"]
        ]
        if team_list:
            t["team"] = team_list

        # Per-slot decisions.  opp_species lets each action resolve its numeric
        # target slot to the opponent species (tg).
        opp_species = [(o["s"] if o is not None else None) for o in opp_list]
        dec_list = []
        for slot, ranked in sorted(entry["slots"].items()):
            if not ranked:
                continue
            chosen = ranked[0]
            acts = [_compact_action(a, opp_species) for a in _select_actions(ranked)]
            dec: dict = {
                "sl":   slot,
                "ch":   chosen.label,
                "acts": acts,
            }
            # Resolve the chosen action's target slot to the opponent species so
            # the log shows *who* each slot attacked without cross-referencing
            # ``ts`` against the opp list.  Omitted for Protect / switches / any
            # action with no opponent target.
            cts = chosen.target_slot
            if cts is not None and 0 <= cts < len(opp_list) and opp_list[cts] is not None:
                dec["ct"] = opp_list[cts]["s"]
            dec_list.append(dec)
        if dec_list:
            t["dec"] = dec_list

        # Actual move-resolution events for this turn (0.8.1) — order, actor,
        # move, target, and observed damage fraction — for comparing the
        # engine's predictions against what really happened.  Internal linkage
        # keys (``_tgt_ident``) and null damage are stripped.
        events = getattr(self._state, "events_log", {}).get(turn_num) if self._state else None
        if events:
            ev_list = []
            for e in events:
                ev = {"o": e["o"], "sd": e["sd"], "a": e["a"], "mv": e["mv"]}
                if e.get("tg"):
                    ev["tg"] = e["tg"]
                if e.get("hp0") is not None:
                    ev["h0"] = round(e["hp0"], 3)   # target HP fraction before the hit
                if e.get("dmg") is not None:
                    ev["d"] = e["dmg"]
                ev_list.append(ev)
            t["ev"] = ev_list

        return t

    def _save(self) -> None:
        dir_path  = os.path.join(_PROJECT_ROOT, "Battle Data", self.version)
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, f"{self.battle_id}.json")

        turns = [
            self._build_turn(n, entry)
            for n, entry in sorted(self._turns.items())
            if entry["snap"] is not None
        ]
        payload: dict = {
            "id":      self.battle_id,
            "v":       self.version,
            "t":       self._started_at,
            "outcome": self._outcome,
        }
        if self._preview is not None:
            payload["preview"] = self._preview
        payload["turns"] = turns
        # Data-layer lookup failures seen during this battle (deduped
        # "kind:species" strings).  Present only when something went wrong —
        # a clean battle has no key at all.
        gaps = drain_gaps()
        if gaps:
            payload["data_gaps"] = gaps
            _log.warning("Battle %s data gaps: %s",
                         self.battle_id, ", ".join(gaps))
        with open(file_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, separators=(',', ':'), ensure_ascii=False)
