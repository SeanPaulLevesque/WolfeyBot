"""
main.py — Showdown bot client.
Imports BattleParser and BattleState directly from battle.py.

Usage:
    python main.py

Config (edit the constants below):
    USERNAME       — registered Showdown username (leave blank for guest mode)
    PASSWORD       — registered Showdown password (leave blank for guest mode)
    BATTLE_FORMAT  — Showdown format string to queue for
    LOG_LEVEL      — logging.DEBUG for full protocol trace, INFO for game events

Guest mode note:
    Guests can join and watch battles but Showdown rejects /choose commands in
    rated formats.  Set USERNAME + PASSWORD to play rated random battles.
    Alternatively change BATTLE_FORMAT to "gen9unratedrandombattle" for guest play.
"""

import argparse
import asyncio
import json as _json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import websockets
from websockets.exceptions import WebSocketException
import aiohttp

from battle import BattleParser, BattleState
from decision import make_engine, Action
from team import (
    get_team, set_active_team, list_teams, team_versions, current_version,
    team_account, team_label, validate_team, active_team, active_team_version,
    active_team_file,
)
from team_preview import select_team, select_leads, select_mega
from tools.pack_team import to_packed
from recorder import BattleRecorder

# ── Encoding fix ──────────────────────────────────────────────────────────────
# Showdown's protocol contains non-ASCII characters (e.g. ☆ in join messages,
# Pokémon names with accents, etc.).  On Windows the default stdout/stderr
# encoding is CP1252, which cannot represent those code points and raises a
# UnicodeEncodeError inside the logging StreamHandler.  Reconfigure both
# streams to UTF-8 with 'replace' as a fallback so any remaining unencodable
# characters become '?' instead of crashing.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


# ─── Config ──────────────────────────────────────────────────────────────────

import os as _os
# Local Showdown credentials live in a git-ignored bot_secrets.py (optional).
# Imported once here; both the default-cred resolution below and
# _resolve_account() reference this single handle.
try:
    import bot_secrets as _bot_secrets        # local only — listed in .gitignore
except ImportError:
    _bot_secrets = None

# Credentials, in priority order: env vars (PS_USERNAME / PS_PASSWORD), then the
# bot_secrets.py module-level vars.  Blank on both → guest mode.
USERNAME       = _os.environ.get("PS_USERNAME", "")
PASSWORD       = _os.environ.get("PS_PASSWORD", "")
if not (USERNAME and PASSWORD) and _bot_secrets is not None:
    USERNAME = USERNAME or getattr(_bot_secrets, "USERNAME", "")
    PASSWORD = PASSWORD or getattr(_bot_secrets, "PASSWORD", "")


def _resolve_account(profile: Optional[str]) -> tuple[str, str]:
    """Resolve an account-profile name to (username, password).

    ``bot_secrets.PROFILES`` is keyed by Showdown username (the key *is* the
    username; only the password lives in the value), so a team's ``account`` in
    teams.json reads as the account itself.  When ``profile`` is None (no
    binding) this falls back to the module-level USERNAME/PASSWORD (env / legacy
    bot_secrets vars).  An *explicitly named* profile that is missing or has no
    creds returns ``("", "")`` — never the default — so the caller can refuse
    rather than silently ladder on the wrong account.
    """
    if profile:
        profiles = {}
        if _bot_secrets is not None:
            profiles = getattr(_bot_secrets, "PROFILES", {}) or {}
        if profile in profiles:
            p = profiles[profile]
            # Key is the username; honour an explicit "username" for back-compat.
            return p.get("username", profile), p.get("password", "")
        return "", ""           # explicit profile unresolved → no silent fallback
    return USERNAME, PASSWORD


BATTLE_FORMAT  = "gen9championsvgc2026regmb"  # ← Champions 2026 Reg M-B format slug (M-A delisted from ladder 2026-06-17)
WS_URL         = "wss://sim3.psim.us/showdown/websocket"
LOGIN_URL      = "https://play.pokemonshowdown.com/api/login"

# Default named team when --team is omitted, so live runs are always tagged and
# data never lands in the untagged baseline path.  team.txt remains the fallback
# only if this team can't be resolved.  The active selection itself is owned by
# team.py (active_team() / active_team_version()) — single source of truth; the
# recorder + ELO tag sites read it from there.
DEFAULT_TEAM = "meta-team"

# Packed team string sent via /utm before every search.  Defaults to the
# baseline team.txt; main() recomputes it for the selected named team.
PACKED_TEAM: str = to_packed()

REQUEUE_DELAY  = 20                    # seconds to wait between battles before searching again

# Reconnect backoff: a transient network/DNS blip should not kill the bot.
# run() retries connect() with exponential backoff between these bounds and
# reconnects automatically if an established stream drops.
RECONNECT_DELAY_INITIAL = 5            # seconds before the first reconnect attempt
RECONNECT_DELAY_MAX     = 300          # cap on the exponential backoff

from version import __version__ as VERSION   # single source of truth (see version.py)
# VERSION drives the Battle Data/<version>/ log folder and the elo_log version field

# ─── Logging ─────────────────────────────────────────────────────────────────
# Console: INFO and above only, clean "HH:MM:SS  message" format.
#          WARN/ERROR prefix their level tag so problems stand out.
# File:    DEBUG and above, full format with level + logger name.

class _CompactFormatter(logging.Formatter):
    """Minimal console formatter — no logger name, no level tag for INFO."""
    def format(self, record: logging.LogRecord) -> str:
        ts  = self.formatTime(record, "%H:%M:%S")
        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)
        if record.levelno >= logging.WARNING:
            return f"{ts}  [{record.levelname[:4]}]  {msg}"
        return f"{ts}  {msg}"

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_CompactFormatter())
_console_handler.setLevel(logging.INFO)   # no DEBUG noise on the console

# Runtime log lives under scratch/ to keep the source root clean (scratch/ is
# git-ignored as a folder; see scratch/.gitignore).  makedirs guards a fresh
# checkout where the empty folder might be absent.
_os.makedirs("scratch", exist_ok=True)
_file_handler = logging.FileHandler("scratch/bot.log", mode="w", encoding="utf-8")
_file_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
))
_file_handler.setLevel(logging.DEBUG)     # full trace in the log file

# Root logger at DEBUG so both handlers can filter independently.
logging.basicConfig(level=logging.DEBUG, handlers=[_console_handler, _file_handler])

log = logging.getLogger("main")
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


def _log_unhandled_exception(exc_type, exc_value, exc_tb):
    """Route uncaught exceptions through the logging system so they land in bot.log."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    log.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))


sys.excepthook = _log_unhandled_exception


def _asyncio_exception_handler(loop, context):
    """Route asyncio task/future exceptions through logging (e.g. 'Task exception was never retrieved')."""
    exc = context.get("exception")
    msg = context.get("message", "asyncio error")
    if exc:
        log.error("asyncio: %s", msg, exc_info=exc)
    else:
        log.error("asyncio: %s  ctx=%s", msg, context)


# ─── ELO Tracker ─────────────────────────────────────────────────────────────

ELO_LOG_PATH = Path("elo_log.json")

class EloTracker:
    """
    Persists ELO data across sessions.

    Each battle appends one entry to ``elo_log.json``::

        {
            "timestamp":  "2026-05-23T14:30:00Z",
            "battle_id":  "battle-gen9championsvgc2026regma-12345",
            "version":    "0.3.2",
            "elo_before": 1412,     # null if unrated / guest
            "outcome":    "win"     # "win" | "loss" | "tie"
        }

    In-process stats (wins / losses / ties since this run started) are
    tracked separately so the log never needs to be re-read in the hot path.
    """

    def __init__(self):
        self._session_wins:   int = 0
        self._session_losses: int = 0
        self._session_ties:   int = 0
        self._last_elo:       Optional[int] = None   # most recent non-null ELO seen
        self._log = logging.getLogger("elo")

        # Load the last known ELO from the log so it shows on session start
        self._last_elo = self._load_last_elo()
        if self._last_elo is not None:
            self._log.info("ELO  last recorded: %d", self._last_elo)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_last_elo(self) -> Optional[int]:
        """Return the ELO from the most recent log entry that had one."""
        if not ELO_LOG_PATH.exists():
            return None
        try:
            entries = _json.loads(ELO_LOG_PATH.read_text(encoding="utf-8"))
            for entry in reversed(entries):
                elo = entry.get("elo_before")
                if elo is not None:
                    return int(elo)
        except Exception:
            pass
        return None

    def _load_all_time(self) -> tuple[int, int, int]:
        """Return (wins, losses, ties) totals from the full log file."""
        if not ELO_LOG_PATH.exists():
            return (0, 0, 0)
        try:
            entries = _json.loads(ELO_LOG_PATH.read_text(encoding="utf-8"))
            w = sum(1 for e in entries if e.get("outcome") == "win")
            l = sum(1 for e in entries if e.get("outcome") == "loss")
            t = sum(1 for e in entries if e.get("outcome") == "tie")
            return (w, l, t)
        except Exception:
            return (0, 0, 0)

    # ── Public API ────────────────────────────────────────────────────────────

    def record(self, battle_id: str, version: str, elo_before: Optional[int], won: Optional[bool],
               team: Optional[str] = None, team_version: Optional[str] = None,
               username: Optional[str] = None):
        """
        Append one battle result to the log file and update session counters.

        *won* can be ``True`` (win), ``False`` (loss), or ``None`` (tie / forfeit).
        *team* / *team_version* / *username* tag the entry for A/B filtering;
        omitted (None) when running the unnamed ``team.txt`` baseline.
        """
        outcome = "win" if won is True else ("loss" if won is False else "tie")

        if won is True:
            self._session_wins += 1
        elif won is False:
            self._session_losses += 1
        else:
            self._session_ties += 1

        if elo_before is not None:
            self._last_elo = elo_before

        entry = {
            "timestamp":  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "battle_id":  battle_id,
            "version":    version,
            "elo_before": elo_before,
            "outcome":    outcome,
        }
        # A/B tags — added only when running a named team, so the existing
        # baseline-era entries stay byte-shaped as before.
        if team:
            entry["team"] = team
            if team_version:
                entry["team_version"] = team_version
        if username:
            entry["username"] = username

        # Load → append → write  (atomic enough for a single-threaded bot)
        try:
            if ELO_LOG_PATH.exists():
                existing = _json.loads(ELO_LOG_PATH.read_text(encoding="utf-8"))
            else:
                existing = []
            existing.append(entry)
            ELO_LOG_PATH.write_text(
                _json.dumps(existing, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            self._log.exception("Failed to write ELO log")

        # Summary line
        elo_str = f"  ELO {elo_before}" if elo_before is not None else ""
        all_w, all_l, all_t = self._load_all_time()
        session_str = f"{self._session_wins}W-{self._session_losses}L"
        if self._session_ties:
            session_str += f"-{self._session_ties}T"
        alltime_str = f"{all_w}W-{all_l}L"
        if all_t:
            alltime_str += f"-{all_t}T"
        self._log.info(
            "ELO  %s%s  session %s  all-time %s",
            outcome.upper(), elo_str, session_str, alltime_str,
        )

    def session_summary(self) -> str:
        """One-line session record, e.g. ``'3W-1L  ELO ~1450'``."""
        parts = [f"{self._session_wins}W-{self._session_losses}L"]
        if self._session_ties:
            parts.append(f"-{self._session_ties}T")
        if self._last_elo is not None:
            parts.append(f"  ELO ~{self._last_elo}")
        return "".join(parts)


# ─── Decision Logic ───────────────────────────────────────────────────────────

# One engine instance shared across all battles in this process.
_engine = make_engine()

# Move targets that do NOT require an explicit target slot in the choice string.
_NO_TARGET_TYPES = frozenset({
    "self",
    "allySide",
    "allyTeam",
    "all",
    "foeSide",
    "allAdjacent",
    "allAdjacentFoes",
    "scripted",
    "allies",
    # Server picks the target (Struggle, Outrage-style lock-ins, Metronome
    # results).  Showdown REJECTS an explicit target for these: "[Invalid
    # choice] Can't move: You can't choose a target for Struggle".
    "randomNormal",
})



def _action_to_choice(
    action: Action,
    state:  BattleState,
    slot:   int,
    mega:   bool,
    is_doubles: bool,
) -> str:
    """
    Convert a decision engine :class:`Action` to the Showdown choice token for
    one slot, e.g. ``"move 2 1"`` or ``"move 1 mega"`` or ``"switch 3"``.
    """
    # ── Switch action ─────────────────────────────────────────────────────────
    if action.is_switch:
        active_idents = {p.ident for p in state.my_actives if p is not None}
        for i, mon in enumerate(state.my_team, start=1):
            if mon.species == action.switch_target and not mon.fainted:
                return f"switch {i}"
        # Fallback: first available bench slot
        for i, mon in enumerate(state.my_team, start=1):
            if not mon.fainted and mon.ident not in active_idents:
                return f"switch {i}"
        return "pass"

    # ── Move action ───────────────────────────────────────────────────────────
    move_dicts = state.moves_per_slot[slot] if slot < len(state.moves_per_slot) else []

    # Find the chosen move's 1-based index; fall back to first non-disabled move.
    move_idx:  Optional[int]  = None
    move_dict: Optional[dict] = None
    for i, md in enumerate(move_dicts, start=1):
        if md.get("disabled", False):
            continue
        if md.get("move", "").lower() == action.move_name.lower():
            move_idx, move_dict = i, md
            break
    if move_idx is None:
        for i, md in enumerate(move_dicts, start=1):
            if not md.get("disabled", False):
                move_idx, move_dict = i, md
                break

    if move_idx is None:
        log.warning("DECISION  slot %d: no valid move found, defaulting to move 1", slot)
        return f"move 1 1" if is_doubles else "move 1"

    parts = [f"move {move_idx}"]
    if is_doubles and move_dict is not None:
        target_type = move_dict.get("target", "normal")
        if target_type in _NO_TARGET_TYPES:
            tgt = None
        elif target_type == "adjacentAlly":
            tgt = f"-{2 - slot}"
        elif target_type == "adjacentAllyOrSelf":
            tgt = f"-{slot + 1}"
        else:
            # Normal / adjacentFoe / any: use recommended target from the
            # decision engine (set by DamageOutputModule / ThreatEliminationModule
            # to the opponent that drove the move choice).  Fall back to slot 1.
            tgt = str(action.target_slot + 1) if action.target_slot is not None else "1"
        if tgt is not None:
            parts.append(tgt)
    if mega:
        parts.append("mega")

    return " ".join(parts)


def _pick_team(state: BattleState, recorder: Optional[BattleRecorder] = None) -> str:
    """
    Build the ``/choose team:XXXX`` response for team preview.

    Chooses which Pokémon to bring (via :func:`select_team`) and in what
    order (via :func:`select_leads`).  The first two slots become leads;
    the remaining slots go to the back.

    Selection is driven by type matchups:
    * **Primary** — offensive coverage: which of our mons have moves that hit
      the opponent's revealed team super-effectively.
    * **Secondary** — defensive durability: how resistant each mon is to the
      opponent's STAB types.

    If *recorder* is provided the selection (opponent team, slot order, species
    names, designated mega) is persisted to the battle log via
    :meth:`BattleRecorder.record_preview`.
    """
    n    = min(state.max_team_size, len(state.my_team))
    team = get_team()

    slots = select_team(state.opp_preview_team, team, n=n)
    slots = select_leads(slots, team, state.opp_preview_team)

    state.designated_mega = select_mega(slots, team, state.opp_preview_team)

    if recorder is not None:
        bring = [team[i - 1].name for i in slots]
        # The opponent lead pair we predicted (only meaningful with lead data);
        # recorded so the report can later confirm a correct read → advantage.
        try:
            from data.lead_stats import predict_pair, total_battles
            predicted = (predict_pair(state.opp_preview_team)
                         if total_battles() > 0 else None)
        except Exception:
            predicted = None
        try:
            recorder.record_preview(
                opp_team=list(state.opp_preview_team),
                slots=list(slots),
                bring=bring,
                mega=state.designated_mega,
                pred=predicted,
            )
        except Exception:
            log.warning("Recorder failed to capture team preview")

    slots_str   = "".join(str(i) for i in slots)
    rqid_suffix = f"|{state.rqid}" if state.rqid is not None else ""
    log.info(
        "TEAM PREVIEW  bringing %s  designated_mega=%s  |  opp: %s",
        slots_str, state.designated_mega, state.opp_preview_team,
    )
    return f"/choose team {slots_str}{rqid_suffix}"


def _build_choice(
    state:    BattleState,
    recorder: Optional[BattleRecorder] = None,
) -> str:
    """
    Build the full ``/choose …`` string for the current state using the
    decision engine.  Handles force-switch phases, normal turns, and mega
    evolution.

    If *recorder* is provided each slot's ranked action list is captured via
    :meth:`BattleRecorder.record_decision` before the choice string is built.
    """
    # ── Team preview ──────────────────────────────────────────────────────────
    if state.team_preview:
        return _pick_team(state, recorder)

    rqid_suffix = f"|{state.rqid}" if state.rqid is not None else ""
    is_doubles  = state.is_doubles or len(state.my_actives) > 1

    choices: list[str] = []

    if any(state.force_switch):
        # ── Force-switch phase ────────────────────────────────────────────────
        # Use the decision engine so SwitchModule scores type matchup, OHKO
        # safety, and partner coordination — not just team order.
        claimed_targets: set[str] = set()
        for slot_idx, needs_switch in enumerate(state.force_switch):
            if not needs_switch:
                continue
            ranked = _engine.scored_actions(state, slot_idx)
            # During a force switch the server only accepts "switch N" — filter
            # to switch actions only (moves / Struggle are not legal here).
            # Targets claimed by an earlier forced slot are excluded: on a
            # double KO the per-slot rankings are independent (coordinate()'s
            # SwitchCollisionAdjuster never runs here), so both slots would
            # otherwise pick the same bench mon — an illegal choice the server
            # rejects ("/choose switch 3, switch 3").
            switch_ranked = [a for a in ranked
                             if a.is_switch and a.weight > 0
                             and a.switch_target not in claimed_targets]
            if switch_ranked:
                action = switch_ranked[0]
                claimed_targets.add(action.switch_target)
                state.my_slot_decisions.append(action)
                token = _action_to_choice(action, state, slot_idx, False, is_doubles)
                choices.append(token)
                reasons_str = " | ".join(action.reasons) if action.reasons else "team order"
                log.info("DECISION  slot %d force-switch -> %s  x%.2f  %s",
                         slot_idx, action.switch_target, action.weight, reasons_str)
            else:
                state.my_slot_decisions.append(None)
                choices.append("pass")
                log.warning("DECISION  slot %d force-switch but no available mons", slot_idx)

    else:
        # ── Normal turn: phase-1 scoring + joint coordinate() ─────────────────
        # Phase 1 scores each slot's (move, target) candidates in isolation;
        # coordinate() then selects the best *joint pair*, resolving every cross-
        # slot effect (doubling / overkill, gratuitous-Protect, fake-out freeing,
        # switch collision) at once — no scoring-order blind spot, no re-pass.
        # It writes the chosen action per slot into state.my_slot_decisions and
        # returns the chosen action + phase-1 ranked list for each decided slot.
        chosen, ranked_by_slot = _engine.coordinate(state)

        for slot_idx in range(len(state.moves_per_slot)):
            action = chosen.get(slot_idx)
            if action is None:
                # Fainted / empty slot coordinate() skipped (Showdown sometimes
                # keeps a fainted slot in the active array) — emit no token; the
                # server silently accepts the omission.
                active_mon = (state.my_actives[slot_idx]
                              if slot_idx < len(state.my_actives) else None)
                if active_mon is not None and active_mon.fainted:
                    log.warning(
                        "DECISION  slot %d: %s is fainted — skipping choice for this slot",
                        slot_idx, active_mon.species,
                    )
                continue

            slot_ranked = ranked_by_slot.get(slot_idx) or [action]
            # Record this slot's (final) decision for offline analysis.
            if recorder is not None:
                try:
                    recorder.record_decision(state, slot_idx, slot_ranked)
                except Exception:
                    log.warning("Recorder failed to capture slot %d decision", slot_idx)

            # Mega evolve as soon as the server says we can, but only for the
            # Pokémon designated at team preview.  When two mega users are
            # brought we must not trigger the second one — the server allows
            # only one mega per battle, and once the first has evolved the
            # second's canMegaEvo flag goes false anyway, but we guard here
            # too so the choice string is never generated in the first place.
            server_allows = (
                slot_idx < len(state.can_mega_evo) and state.can_mega_evo[slot_idx]
            )
            if server_allows and state.designated_mega is not None:
                active = (state.my_actives[slot_idx]
                          if slot_idx < len(state.my_actives) else None)
                mega = (active is not None
                        and active.species == state.designated_mega)
            else:
                # No designated mega set (team preview not run, or no megas in
                # team) — fall back to always mega when server allows it.
                mega = server_allows

            token = _action_to_choice(action, state, slot_idx, mega, is_doubles)
            choices.append(token)

            slot_label   = chr(ord('A') + slot_idx)
            mega_tag     = " [MEGA]" if mega else ""
            # Show who this slot is attacking (resolve target_slot -> species).
            target_str   = ""
            tslot = action.target_slot
            if tslot is not None and tslot < len(state.opp_actives):
                opp_t = state.opp_actives[tslot]
                if opp_t is not None:
                    target_str = f" -> {opp_t.species}"
            reasons_str  = " | ".join(action.reasons) if action.reasons else "no modifiers"
            log.info("   [%s]  %-40s  x%-5.2f  %s",
                     slot_label, action.label + target_str + mega_tag,
                     action.weight, reasons_str)

    if not choices:
        log.warning("DECISION  empty choice list — defaulting to move 1")
        choices = ["move 1 1" if is_doubles else "move 1"]

    return f"/choose {', '.join(choices)}{rqid_suffix}"


# ─── Client ──────────────────────────────────────────────────────────────────

class ShowdownClient:

    def __init__(self, max_games: Optional[int] = None):
        self.username: str = USERNAME or "Guest"
        self.ws = None
        self.parsers: dict[str, BattleParser] = {}
        self.finished_battles: set[str] = set()  # battle IDs that are over — ignore post-game msgs
        self._joining_battles: set[str] = set()   # sent /join but parser not yet created
        self.log = logging.getLogger("client")
        self._requeue_pending: bool = False  # prevents double-queue on burst updatesearch
        self._requeue_task: Optional[asyncio.Task] = None  # pending delayed-requeue task
        self._recorders: dict[str, BattleRecorder] = {}    # one recorder per active battle
        self._elo: EloTracker = EloTracker()               # persists ELO across sessions
        self._stopping: bool = False                       # set by shutdown() to break the reconnect loop
        # Bounded runs: stop after this many completed games (None = unbounded).
        # The bot shuts ITSELF down when the count is reached, so a run can't
        # over-play if no one is watching to stop it.
        self._max_games: Optional[int] = max_games
        self._games_done: int = 0

    # ── Connection / Auth ─────────────────────────────────────────────────────

    async def connect(self):
        self.log.info("Connecting to %s", WS_URL)
        self.ws = await websockets.connect(WS_URL)
        self.log.info("WebSocket open")

    async def _send_raw(self, message: str):
        """Send a raw string over the WebSocket."""
        self.log.debug("SEND  %r", message[:200])
        await self.ws.send(message)

    async def _queue_search(self):
        """Upload team (if configured) then queue for BATTLE_FORMAT."""
        if PACKED_TEAM:
            await self._send_raw(f"|/utm {PACKED_TEAM}")
        await self._send_raw(f"|/search {BATTLE_FORMAT}")

    async def _delayed_requeue(self):
        """Wait REQUEUE_DELAY seconds then queue for another battle."""
        try:
            self.log.info(
                "Waiting %d seconds before requeuing for %s ...",
                REQUEUE_DELAY, BATTLE_FORMAT,
            )
            await asyncio.sleep(REQUEUE_DELAY)
            if self._stopping:                       # max-games / shutdown raced in during the wait
                self.log.info("Requeue suppressed — shutting down.")
                return
            self.log.info("Requeue delay complete — searching for %s", BATTLE_FORMAT)
            await self._queue_search()
        except asyncio.CancelledError:
            self.log.info("Requeue timer cancelled (shutdown)")
        finally:
            self._requeue_task = None

    async def _send_battle(self, battle_id: str, choice: str):
        """Send a /choose (or other) command into a battle room.

        Client-to-server format is ROOMID|MESSAGE (first pipe separates room
        from message body).  The server splits at the first pipe only, so a
        choice like '/choose move 1|3' is routed to the room with the rqid
        intact — no spurious global-message popup.
        """
        await self._send_raw(f"{battle_id}|{choice}")

    async def _login(self, challstr: str) -> bool:
        """
        POST credentials to the Showdown login API and send /trn to authenticate.
        Returns True on success.  challstr is the raw 'ID|TOKEN' string from the server.
        """
        self.log.info("Logging in as %s ...", USERNAME)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    LOGIN_URL,
                    data={"name": USERNAME, "pass": PASSWORD, "challstr": challstr},
                ) as resp:
                    text = await resp.text()
        except Exception as exc:
            self.log.error("Login HTTP request failed: %s", exc)
            return False

        if not text.startswith("]"):
            self.log.error("Login API unexpected response: %s", text[:120])
            return False

        try:
            data = _json.loads(text[1:])
        except _json.JSONDecodeError:
            self.log.error("Login API response not valid JSON: %s", text[:120])
            return False

        assertion = data.get("assertion", "")
        if not assertion or str(assertion).startswith(";"):
            # Assertion starting with ";" means wrong password or banned account
            self.log.error("Login failed - bad assertion (wrong password?): %s", str(assertion)[:80])
            return False

        await self._send_raw(f"|/trn {USERNAME},0,{assertion}")
        self.log.debug("Login command sent - waiting for updateuser confirmation")
        return True

    # ── Main Loop ─────────────────────────────────────────────────────────────

    async def run(self):
        """Connect and process messages, reconnecting with exponential backoff
        on any network failure so a transient outage (DNS blip, dropped stream,
        refused connection) doesn't kill the bot.

        The reconnect is self-healing: after each successful reconnect the
        server sends a fresh ``challstr``, which re-drives login and
        matchmaking through the normal global-message handlers — no special
        resume logic needed.  Active battles are abandoned on a disconnect
        (Showdown forfeits them server-side), so per-connection state is reset
        before reconnecting.
        """
        delay = RECONNECT_DELAY_INITIAL
        while not self._stopping:
            try:
                await self.connect()
            except (OSError, WebSocketException, asyncio.TimeoutError) as exc:
                if self._stopping:
                    break
                self.log.warning("Connect failed (%s) — retrying in %ds", exc, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_DELAY_MAX)
                continue

            delay = RECONNECT_DELAY_INITIAL   # connected — reset the backoff

            try:
                async for raw in self.ws:
                    self.log.debug("RECV  %r", raw)

                    if raw.startswith(">battle-"):
                        await self._route_battle_message(raw)
                    else:
                        await self._handle_global(raw)
            except (OSError, WebSocketException) as exc:
                self.log.warning("Connection dropped (%s) — reconnecting", exc)
            else:
                if self._stopping:
                    break
                self.log.warning("WebSocket stream ended — reconnecting")

            if not self._stopping:
                self._reset_connection_state()

    def _reset_connection_state(self):
        """Drop per-connection state before a reconnect.

        Battles in progress are abandoned when the socket drops (the server
        forfeits them), so their parsers/recorders are cleared rather than
        carried across; the fresh ``challstr`` after reconnect starts a clean
        login + search cycle.  Cross-session state (``_elo``) is preserved.
        """
        if self._requeue_task and not self._requeue_task.done():
            self._requeue_task.cancel()
        self._requeue_task = None
        self._requeue_pending = False
        self.parsers.clear()
        self._joining_battles.clear()
        self.finished_battles.clear()
        self._recorders.clear()
        self.ws = None

    async def _route_battle_message(self, raw: str):
        """Create a BattleParser for new battles; feed all battle messages into it."""
        battle_id = raw.split("\n", 1)[0][1:]   # strip leading ">"

        # Ignore all messages for battles that have already ended
        if battle_id in self.finished_battles:
            return

        # |noinit| means the room doesn't exist or requires login.
        # Only discard if the battle hasn't been confirmed yet (still in the join
        # tracker). A stale noinit can arrive *after* the parser is already live
        # (e.g. the server processes a duplicate /join after game data was sent),
        # and we must not tear down an active battle in that case.
        #
        # Log level distinction:
        #   WARNING  — we sent /join for this room and it was rejected (real failure).
        #   DEBUG    — unsolicited noinit for a room we never joined.  This happens
        #              whenever Showdown assigns a private hash-suffix room (e.g.
        #              battle-...-2617847309-abc123pw).  The server also delivers a
        #              noinit for the truncated public alias (...-2617847309) because
        #              that room was never created.  These private-room battles cannot
        #              be spectated from outside — the noinit is expected and harmless.
        if "|noinit|" in raw:
            if battle_id in self._joining_battles or battle_id not in self.parsers:
                if battle_id in self._joining_battles:
                    self.log.warning("NOINIT %s - room unavailable, discarding", battle_id)
                else:
                    # Unsolicited: Showdown sent noinit for the public alias of a
                    # private (hash-suffix) battle room.  Not an error.
                    self.log.debug("NOINIT %s - unsolicited (private battle alias)", battle_id)
                self._joining_battles.discard(battle_id)
                self.parsers.pop(battle_id, None)
            else:
                self.log.debug("NOINIT %s - ignored, battle already active", battle_id)
            return

        if battle_id not in self.parsers:
            self.log.info("NEW BATTLE  %s", battle_id)
            self._joining_battles.discard(battle_id)
            self._recorders[battle_id] = BattleRecorder(
                battle_id, VERSION,
                team=active_team(), team_version=active_team_version(),
            )
            self.parsers[battle_id] = BattleParser(
                battle_id=battle_id,
                my_username=self.username,
                on_decision_needed=self._make_decision_handler(battle_id),
                on_battle_end=self._make_battle_end_handler(battle_id),
            )
            await self._send_battle(battle_id, "/timer on")

        await self.parsers[battle_id].feed(raw)

    # ── Global Message Handling ───────────────────────────────────────────────

    async def _handle_global(self, raw: str):
        for line in raw.split("\n"):
            if not line.startswith("|"):
                continue

            parts    = line.split("|")
            msg_type = parts[1] if len(parts) > 1 else ""
            args     = parts[2:]

            if msg_type == "challstr":
                # Reconstruct the full challstr token (format: "ID|TOKEN")
                challstr_val = "|".join(args)
                if USERNAME and PASSWORD:
                    # Authenticated mode: POST to login API, then wait for updateuser
                    # confirmation before searching.  _requeue_pending blocks the idle
                    # updatesearch from firing a premature /search while login is in flight.
                    self._requeue_pending = True
                    ok = await self._login(challstr_val)
                    if not ok:
                        if active_team() is not None:
                            # A named team is bound to a specific account.  Guest-
                            # playing would save games mis-tagged as that team's
                            # A/B data (the off-meta incident).  Abort instead of
                            # laddering as a guest on the wrong identity.
                            self.log.error(
                                "Login failed for the account bound to team '%s' — "
                                "refusing to guest-play (would mis-tag A/B data). "
                                "Check that account's password in bot_secrets.PROFILES. "
                                "Shutting down.", active_team())
                            await self.shutdown()
                            return
                        self.log.warning("Login failed - falling back to guest search")
                        self._requeue_pending = True
                        await self._queue_search()
                else:
                    # Guest mode: search immediately.  _requeue_pending prevents the
                    # idle updatesearch that Showdown fires right after connect from
                    # triggering a duplicate /search.
                    self.log.info("No credentials configured - searching as guest")
                    self._requeue_pending = True
                    await self._queue_search()

            elif msg_type == "updateuser":
                actual_name = args[0] if args else ""
                named = args[1] == "1" if len(args) > 1 else False
                self.username = actual_name.strip()
                if named and USERNAME:
                    # Login confirmed — now safe to submit team and search
                    self.log.info("Logged in as %s — queuing %s", self.username, BATTLE_FORMAT)
                    self._requeue_pending = True
                    await self._queue_search()
                else:
                    self.log.debug("User update: %s (named=%s)", actual_name, named)

            elif msg_type == "updatesearch":
                try:
                    search_data = _json.loads(args[0]) if args else {}
                except Exception:
                    search_data = {}
                searching = bool(search_data.get("searching"))
                has_games = bool(search_data.get("games"))
                # Guard: only requeue once per idle transition.
                # Showdown fires updatesearch several times in quick succession
                # after a battle ends — _requeue_pending prevents double-queuing.
                if not searching and not has_games and self.username and not self._requeue_pending:
                    self._requeue_pending = True
                    self._requeue_task = asyncio.create_task(self._delayed_requeue())
                elif has_games:
                    # Reset only when a match is confirmed, NOT on searching=True.
                    # Resetting on searching=True caused a race: the server briefly
                    # flips searching→[] as it finds a match, which re-triggered a
                    # second /search before the game appeared in has_games.
                    self._requeue_pending = False

                # Rejoin any active games we don't have a parser for yet
                # (can happen if the bot connected mid-battle or missed the init frame)
                # _joining_battles guards against double /join when updatesearch bursts
                # multiple times before the >battle- frame arrives and creates the parser.
                if has_games:
                    for gid in search_data.get("games", {}).keys():
                        if (gid not in self.parsers
                                and gid not in self.finished_battles
                                and gid not in self._joining_battles):
                            self._joining_battles.add(gid)
                            self.log.info("REJOINING existing battle  %s", gid)
                            await self._send_raw(f"|/join {gid}")

            elif msg_type == "pm":
                # |pm|SENDER|RECEIVER|MESSAGE
                # Errors come back as PMs from ~ (the server).
                sender  = args[0] if args else ""
                message = args[2] if len(args) > 2 else ""
                if message.startswith("/error"):
                    err = message[len("/error"):].strip()
                    if "choose a name" in err:
                        self.log.error(
                            "PM /error from server: %s  "
                            "-> Set USERNAME + PASSWORD in main.py to play rated battles", err)
                    else:
                        self.log.error("PM /error from %s: %s", sender.strip(), err)
                else:
                    self.log.debug("PM from %s: %s", sender.strip(), message)

            elif msg_type == "raw":
                # HTML server notices (rate-throttle warnings, etc.) — strip tags
                import re as _re
                text = _re.sub(r"<[^>]+>", "", args[0]) if args else ""
                self.log.warning("SERVER NOTICE  %s", text.strip())

            elif msg_type == "popup":
                self.log.warning("POPUP  %s", "|".join(args))

            elif msg_type == "error":
                self.log.error("SERVER ERROR  %s", "|".join(args))

    def _make_battle_end_handler(self, battle_id: str):
        async def on_battle_end(won: bool):
            outcome_str = "WIN" if won else "LOSS"
            self.log.info("Battle ended (%s) - cleaning up %s", outcome_str, battle_id)

            # Grab ELO from parser state before it's removed
            parser = self.parsers.get(battle_id)
            elo_before = parser.state.my_elo if parser is not None else None

            # Record ELO + outcome (tagged with the active team for A/B)
            self._elo.record(
                battle_id, VERSION, elo_before, won,
                team=active_team(), team_version=active_team_version(),
                username=self.username,
            )

            # Persist battle data before removing state
            recorder = self._recorders.pop(battle_id, None)
            if recorder is not None:
                try:
                    recorder.record_outcome(won)
                    self.log.info(
                        "Battle data saved: battle data/%s/%s.json",
                        VERSION, battle_id,
                    )
                except Exception:
                    self.log.exception("Failed to save battle data for %s", battle_id)
            self.parsers.pop(battle_id, None)
            self.finished_battles.add(battle_id)  # suppress all future msgs for this room
            # Requeue is handled by updatesearch arriving naturally after battle end

            # Bounded run: stop ourselves once we've played the requested number
            # of games, so the bot can't keep laddering unattended.  Done here
            # (after the game is fully recorded + state popped) so shutdown has
            # no active battle to forfeit.
            self._games_done += 1
            # Graceful early stop between games: a `tools/scratch/stop` file lets
            # an operator halt a running batch cleanly (finish the current game,
            # never forfeit).  Consumed on read so it doesn't stop the next run.
            _stop_file = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)), "tools", "scratch", "stop")
            if _os.path.exists(_stop_file):
                self.log.info("Stop file present — shutting down cleanly after %d game(s).",
                              self._games_done)
                try:
                    _os.remove(_stop_file)
                except OSError:
                    pass
                await self.shutdown()
            elif self._max_games is not None and self._games_done >= self._max_games:
                self.log.info("Reached --max-games (%d) — shutting down after %d game(s).",
                              self._max_games, self._games_done)
                await self.shutdown()
        return on_battle_end

    # ── Graceful shutdown ─────────────────────────────────────────────────────

    async def shutdown(self):
        """Forfeit all active battles, cancel any pending requeue, then close the WebSocket."""
        self._stopping = True   # break the reconnect loop in run()
        if self._requeue_task and not self._requeue_task.done():
            self._requeue_task.cancel()

        active = list(self.parsers.keys())
        if active:
            self.log.info("Shutdown: forfeiting %d active battle(s)", len(active))
            for battle_id in active:
                try:
                    await self._send_battle(battle_id, "/forfeit")
                    self.log.info("Forfeited %s", battle_id)
                except Exception as exc:
                    self.log.warning("Could not forfeit %s: %s", battle_id, exc)
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass

    # ── Decision Callback Factory ─────────────────────────────────────────────

    def _make_decision_handler(self, battle_id: str):
        """
        Returns an async callback that battle.py calls via on_decision_needed(state).
        battle.py already guards against duplicate rqid calls via _maybe_decide(),
        so we just pick and send here.
        """
        async def on_decision_needed(state: BattleState):
            self._log_state(state)
            recorder = self._recorders.get(battle_id)
            choice   = _build_choice(state, recorder)
            self.log.debug("SENDING  %s  ->  %s", battle_id, choice)
            await self._send_battle(battle_id, choice)

        return on_decision_needed

    # ── State Printer ─────────────────────────────────────────────────────────

    def _log_state(self, state: BattleState):
        force      = any(state.force_switch)
        turn_label = "FORCE SWITCH" if force else f"Turn {state.turn}"
        # Use just the trailing numeric ID to keep the header line compact.
        bid = state.battle_id.rsplit("-", 1)[-1]

        # On turn 1, append ELO if known
        elo_tag = ""
        if state.turn <= 1 and state.my_elo is not None:
            elo_tag = f"  ELO {state.my_elo}"

        log.info("── %s  [%s]%s %s", turn_label, bid, elo_tag, "─" * 44)

        # My active mons
        my_parts: list[str] = []
        for i, mon in enumerate(state.my_actives):
            s = chr(ord('A') + i)
            if mon and not mon.fainted:
                tag = (f" [{mon.status.upper()}]" if mon.status else "")
                tag += " [TERA]" if mon.terastallized else ""
                my_parts.append(f"[{s}] {mon.species} {mon.hp}/{mon.max_hp}{tag}")
            elif mon:
                my_parts.append(f"[{s}] {mon.species} fnt")
            else:
                my_parts.append(f"[{s}] ?")
        log.info("   MY   %s", "   ".join(my_parts))

        # Opponent active mons
        opp_parts: list[str] = []
        for i, mon in enumerate(state.opp_actives):
            s = chr(ord('A') + i)
            if mon and not mon.fainted:
                hp_str = f"{mon.hp}%" if mon.hp_is_percentage else f"{mon.hp}/{mon.max_hp}"
                tag = (f" [{mon.status.upper()}]" if mon.status else "")
                opp_parts.append(f"[{s}] {mon.species} {hp_str}{tag}")
            elif mon:
                opp_parts.append(f"[{s}] {mon.species} fnt")
            else:
                opp_parts.append(f"[{s}] ?")
        log.info("   OPP  %s", "   ".join(opp_parts))

        # Field conditions
        field_items: list[str] = []
        if state.weather:      field_items.append(state.weather)
        if state.terrain:      field_items.append(state.terrain)
        if state.trick_room:   field_items.append(f"TR({state.trick_room_turns_left})")
        if state.opp_tailwind: field_items.append(f"OppTW({state.opp_tailwind_turns_left})")
        if state.my_tailwind:  field_items.append(f"MyTW({state.my_tailwind_turns_left})")
        field_str = "  ".join(field_items) if field_items else "-"

        # Bench (non-fainted mons not currently active)
        active_idents = {m.ident for m in state.my_actives if m}
        bench_parts = [
            f"{p.species} {p.hp}/{p.max_hp}"
            for p in state.my_team
            if not p.fainted and p.ident not in active_idents
        ]
        bench_str = " · ".join(bench_parts) if bench_parts else "-"

        log.info("   FIELD  %-24s BENCH  %s", field_str, bench_str)


# ─── Entry Point ─────────────────────────────────────────────────────────────

async def main(max_games: Optional[int] = None):
    # Install the custom asyncio exception handler now that the loop is running.
    asyncio.get_running_loop().set_exception_handler(_asyncio_exception_handler)
    if max_games is not None:
        log.info("Bounded run: will stop after %d game(s).", max_games)
    client = ShowdownClient(max_games=max_games)
    try:
        await client.run()
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("Interrupted - closing")
    except WebSocketException as e:
        log.error("WebSocket closed: %s", e)
    except Exception:
        log.exception("Unhandled error")
        raise
    finally:
        await client.shutdown()


def _print_teams() -> None:
    """``--list-teams``: enumerate named teams with account + version + validation.

    Checks both the roster (loads + computes stats) *and* the account binding
    (its profile resolves to credentials in bot_secrets.PROFILES), so a team
    that can't actually launch is flagged here rather than at run time.  Note:
    this confirms creds are *present*, not *correct* — a wrong password still
    only surfaces at login (where a named-team run now aborts cleanly).
    """
    teams = list_teams()
    if not teams:
        print("No named teams found under teams/.")
        return
    print("Named teams (teams/):")
    for name in teams:
        acct = team_account(name)
        cur  = current_version(name) or "—"
        vers = ", ".join(team_versions(name)) or "(none)"
        roster_ok, msg = validate_team(name)
        # Account binding: does the bound profile resolve to usable creds?
        if acct:
            user, pw = _resolve_account(acct)
            acct_ok  = bool(user and pw)
            acct_str = f"account={acct}" + ("" if acct_ok else " [NO CREDS]")
        else:
            acct_ok  = True                      # no binding → default creds
            acct_str = "account=—"
        flag = "ok " if (roster_ok and acct_ok) else "!! "
        print(f"  {flag}{name:16} {acct_str:22} current={cur:4} "
              f"versions=[{vers}]  — {msg}")


def _apply_team_selection(team_spec: Optional[str], account_override: Optional[str]) -> None:
    """Resolve --team / --account into the active-team + credential globals.

    A None *team_spec* leaves the team.txt baseline (legacy creds) in place.
    An unresolvable named team logs an error and falls back to that baseline
    rather than crashing.
    """
    global PACKED_TEAM, USERNAME, PASSWORD
    if not team_spec:
        return
    name, version = set_active_team(team_spec)   # active selection now lives in team.py
    ok, msg = validate_team(name, version)
    if not ok:
        log.error("Team '%s@%s' is not usable (%s) — falling back to team.txt baseline.",
                  name, version, msg)
        set_active_team(None)
        return
    PACKED_TEAM = to_packed(active_team_file())
    # Account: explicit --account wins, else the team's manifest binding.
    profile = account_override or team_account(name)
    user, pw = _resolve_account(profile)
    if profile and not (user and pw):
        # An explicitly-bound account with no usable creds must NOT silently
        # fall back to the default account — that would ladder the wrong
        # account.  Stop and tell the user to fill in the password.
        log.error("Account profile '%s' (bound to team '%s') has no usable credentials "
                  "in bot_secrets.PROFILES — refusing to run so it can't ladder the "
                  "wrong account.  Add the username+password for '%s' and retry.",
                  profile, name, profile)
        sys.exit(1)
    if user and pw:
        USERNAME, PASSWORD = user, pw
    log.info("Active team: %s@%s (%s) — account profile '%s' as %s",
             name, version, team_label(name), profile or "—", USERNAME or "Guest")


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="WolfeyBot — Showdown Champions VGC bot")
    p.add_argument("--team", default=DEFAULT_TEAM,
                   help="named team to run, 'name' or 'name@vN' (default: %(default)s). "
                        "Use '' to run the team.txt baseline.")
    p.add_argument("--account", default=None,
                   help="override the account profile (bot_secrets.PROFILES key); "
                        "defaults to the team's manifest binding.")
    p.add_argument("--list-teams", action="store_true",
                   help="list named teams (with accounts/versions/validation) and exit.")
    p.add_argument("--max-games", type=int, default=None, metavar="N",
                   help="play N games then shut down automatically (default: unbounded). "
                        "The bot stops itself, so a bounded run won't over-play if unattended.")
    return p.parse_args(argv)


if __name__ == "__main__":
    _args = _parse_args()
    if _args.list_teams:
        _print_teams()
        sys.exit(0)
    _apply_team_selection(_args.team or None, _args.account)
    asyncio.run(main(max_games=_args.max_games))