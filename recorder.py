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


def _action_key(a: "Action") -> str:
    """Self-describing key for an action in the complete ``wall`` weight map.

    * ``"+<species>"``      — switch to that bench mon.
    * ``"<move>><slot>"``   — single-target move aimed at opponent *slot* (0/1).
    * ``"<move>"``          — spread / status / self move, or Protect (no target).

    The opponent slot index (not species) is used so the key is stable as the
    opponent's HP/species snapshot is read alongside it; resolve ``slot`` against
    the turn's ``opp`` list for the species.
    """
    if a.switch_target:
        return f"+{a.switch_target}"
    if a.target_slot is not None:
        return f"{a.move_name}>{a.target_slot}"
    return a.move_name


def _acts_entry_key(a: dict) -> str:
    """``_action_key`` equivalent for a logged ``acts`` entry (old-log fallback)."""
    if a.get("sw"):
        return f"+{a['sw']}"
    if a.get("ts") is not None:
        return f"{a['lb']}>{a['ts']}"
    return a["lb"]


def action_weights(dec: dict) -> dict:
    """Every scored action's weight for one slot decision, as ``{key: weight}``.

    Uses the complete ``wall`` map when present (new logs); otherwise derives a
    **partial** map from the curated ``acts`` list (old logs, pre-``wall`` — only
    the chosen action + top contenders were recorded).  This is the version-
    agnostic way for analysis to read per-action weights across all logs.
    """
    if "wall" in dec:
        return dec["wall"]
    return {_acts_entry_key(a): a["w"] for a in dec.get("acts", [])}


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
    def _nonzero_boosts(mon) -> dict:
        return {k: v for k, v in (getattr(mon, "boosts", None) or {}).items() if v}

    def _mon_snap(mon) -> Optional[dict]:
        if mon is None:
            return None
        return {
            "species": mon.species,
            "hp":      mon.hp,
            "max_hp":  mon.max_hp,
            "status":  mon.status,
            "boosts":  _nonzero_boosts(mon),
            # Whether our held item has been consumed — drives Unburden's ×2
            # speed in the turn-order model; needed to characterise Unburden
            # turn-order misreads offline (0.18.x).
            "item_consumed": bool(getattr(mon, "item_consumed", False)),
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
            "boosts":  _nonzero_boosts(mon),
        }

    return {
        "weather":     state.weather,
        "terrain":     state.terrain,
        "trick_room":  state.trick_room,
        # Tailwind + active stat boosts (0.13.0): the two speed modifiers needed
        # to turn observed turn order into a clean speed estimate offline.
        "my_tailwind":  bool(state.my_tailwind),
        "opp_tailwind": bool(state.opp_tailwind),
        "my_actives": [_mon_snap(m) for m in state.my_actives],
        "opp_actives":[_opp_snap(o) for o in state.opp_actives],
        "my_team":    [_mon_snap(p) for p in state.my_team],
    }


def _serialize_board(snap: dict) -> dict:
    """Compact ``{my, opp, team}`` active-mon lists from a state snapshot.

    Shared by per-turn serialisation and the top-level post-battle ``final``
    snapshot, so both render mons identically (species, HP fraction, status,
    boosts, item-consumed)."""
    out: dict = {}
    my_list = []
    for mon in snap["my_actives"]:
        if mon is None:
            my_list.append(None)
        else:
            m: dict = {"s": mon["species"], "hp": _hp_frac(mon["hp"], mon["max_hp"])}
            if mon["status"]:
                m["sts"] = mon["status"]
            if mon["boosts"]:
                m["b"] = mon["boosts"]
            if mon.get("item_consumed"):
                m["ic"] = True
            my_list.append(m)
    if any(x is not None for x in my_list):
        out["my"] = my_list

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
            if o["boosts"]:
                oe["b"] = o["boosts"]
            opp_list.append(oe)
    if any(x is not None for x in opp_list):
        out["opp"] = opp_list

    team_list = [{"s": p["species"], "hp": _hp_frac(p["hp"], p["max_hp"])}
                 for p in snap["my_team"]]
    if team_list:
        out["team"] = team_list
    return out


class BattleRecorder:
    """Records decisions and outcomes for one battle and persists them to disk."""

    def __init__(self, battle_id: str, version: str,
                 team: Optional[str] = None, team_version: Optional[str] = None):
        self.battle_id   = battle_id
        self.version     = version
        # Named-team A/B tags.  When set, the battle is filed under
        # Battle Data/<version>/<team>/<team_version>/ and tagged in the
        # payload.  Both None → flat Battle Data/<version>/ (legacy path).
        self.team         = team
        self.team_version = team_version
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
        # Post-battle board snapshot (final HP / faints) — captured at
        # record_outcome since the last turn has no following snapshot.
        self._final_snap: Optional[dict] = None

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
        # Freeze the final board (final HP / who fainted) before saving — the
        # last turn has no following snapshot to capture its result otherwise.
        if self._state is not None:
            self._final_snap = _snapshot_state(self._state)

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
        # Tailwind per side (omitted when neither is up) — a speed ×2 modifier
        # needed to normalise observed turn order into raw speed.
        if snap["my_tailwind"] or snap["opp_tailwind"]:
            t["tw"] = {"us": snap["my_tailwind"], "opp": snap["opp_tailwind"]}

        # Board state (our actives / opp actives / full team) at decision time.
        t.update(_serialize_board(snap))

        # Per-slot decisions.  opp_species resolves an action's numeric target
        # slot to the opponent species (tg / ct).
        opp_species = [(o["species"] if o is not None else None)
                       for o in snap["opp_actives"]]
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
                # Complete per-action weight map (every candidate, weights only),
                # self-describing keys — see _action_key / action_weights.  `acts`
                # above stays the detailed (reasons) subset; `wall` is additive.
                "wall": {_action_key(a): round(a.weight, 2) for a in ranked},
            }
            # Resolve the chosen action's target slot to the opponent species so
            # the log shows *who* each slot attacked without cross-referencing
            # ``ts`` against the opp list.  Omitted for Protect / switches / any
            # action with no opponent target.
            cts = chosen.target_slot
            if cts is not None and 0 <= cts < len(opp_species) and opp_species[cts]:
                dec["ct"] = opp_species[cts]
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
                if e.get("crit"):
                    ev["cr"] = True                 # critical hit — excluded from accuracy
                if e.get("z"):
                    ev["z"] = e["z"]                # 0-dmg reason: immune/miss/protect/sub
                    if e.get("za"):
                        ev["za"] = e["za"]          # ability that conferred immunity
                ev_list.append(ev)
            t["ev"] = ev_list

        # Predicted worst-case incoming damage this turn (0.8.4) — for defensive
        # accuracy analysis (did a mon we thought was safe get hit harder?).
        pin = getattr(self._state, "predicted_incoming_log", {}).get(turn_num) if self._state else None
        if pin:
            t["pin"] = pin

        # Turn result: faints this turn (per side) and switches (in/out).  These
        # are the explicit outcome of the turn — `res` complements the move-level
        # `ev` (which records damage but not faints) and captures faints with no
        # move (residual / recoil / weather) too.
        faints = (getattr(self._state, "faints_log", None) or {}).get(turn_num)
        if faints:
            res: dict = {}
            us  = [f["a"] for f in faints if f["sd"] == "us"]
            opp = [f["a"] for f in faints if f["sd"] == "opp"]
            if us:
                res["us"] = us
            if opp:
                res["opp"] = opp
            if res:
                t["res"] = res
        switches = (getattr(self._state, "switches_log", None) or {}).get(turn_num)
        if switches:
            t["sw"] = switches

        return t

    def _save(self) -> None:
        # Nest under team / team_version when tagged; flat otherwise (legacy).
        parts = [_PROJECT_ROOT, "Battle Data", self.version]
        if self.team:
            parts.append(self.team)
            if self.team_version:
                parts.append(self.team_version)
        dir_path  = os.path.join(*parts)
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
        # Named-team A/B tags (present only when running a named team).
        if self.team:
            payload["team"] = self.team
            if self.team_version:
                payload["team_version"] = self.team_version
        if self._preview is not None:
            payload["preview"] = self._preview
        # Post-battle board snapshot (final HP / faints) — the last turn's result.
        if self._final_snap is not None:
            payload["final"] = _serialize_board(self._final_snap)
        # Reliable record of every opponent forme/mega that appeared (accumulated
        # by the parser as it happens), independent of the decision-time
        # snapshots — so analysis needn't reconstruct megas from snapshot/event
        # triangulation.
        formes = sorted(getattr(self._state, "opp_formes_seen", None) or ())
        if formes:
            payload["opp_formes"] = formes
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
