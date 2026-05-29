# battle.py
from __future__ import annotations
from typing import Optional
import json
import logging
import re

from battle_state import BattleState, Pokemon, _parse_hp, _parse_status  # noqa: F401

_log = logging.getLogger(__name__)


# ─── Parser ──────────────────────────────────────────────────────────────────

class BattleParser:
    """
    Consumes raw Showdown message strings, maintains BattleState.
    Call .feed(raw_message) for each WebSocket message.
    Fires on_decision_needed(state) when a choice is required.

    Supports both singles and doubles; the number of active slots is inferred
    from the |request| JSON's `active` array length.
    """

    def __init__(self, battle_id: str, my_username: str, on_decision_needed, on_battle_end=None):
        self.battle_id = battle_id
        self.my_username = my_username
        self.on_decision_needed = on_decision_needed  # async callback
        self.on_battle_end = on_battle_end            # async callback(won: bool) or None
        self.state = BattleState(battle_id=battle_id, my_side="p1")  # side set on |request|
        self._request_buf: str = ""  # accumulates split |request| JSON across frames

    async def feed(self, raw: str):
        lines = raw.strip().split("\n")

        # Strip room prefix line if present (">battle-...")
        if lines and lines[0].startswith(">"):
            lines = lines[1:]

        for line in lines:
            # ── Reassemble split |request| frames ────────────────────────────
            if self._request_buf:
                self._request_buf += line
                try:
                    json.loads(self._request_buf)
                    await self._dispatch("request", [self._request_buf], "")
                    self._request_buf = ""
                except json.JSONDecodeError:
                    continue
                continue

            if line.startswith("|request|"):
                payload = line[len("|request|"):]
                try:
                    json.loads(payload)
                    await self._dispatch("request", [payload], line)
                except json.JSONDecodeError:
                    self._request_buf = payload
                continue
            # ─────────────────────────────────────────────────────────────────

            if not line.startswith("|"):
                continue
            parts = line.split("|")
            msg_type = parts[1] if len(parts) > 1 else ""
            args = parts[2:]
            await self._dispatch(msg_type, args, line)

    async def _dispatch(self, msg_type: str, args: list[str], raw_line: str):
        handler = _HANDLERS.get(msg_type)
        if handler:
            await handler(self, args)

    # ─── Handlers ────────────────────────────────────────────────────────────

    async def _on_request(self, args: list[str]):
        """Dispatch a |request| message to the appropriate handler branch."""
        if not args or not args[0]:
            return
        data = json.loads(args[0])
        self.state._pending_request = data

        # "wait" — opponent is deciding, no action needed from us
        if data.get("wait"):
            return

        if data.get("teamPreview"):
            await self._handle_team_preview(data)
            return

        self.state.team_preview = False   # clear once a real turn arrives

        # Determine which side we are (request always describes our side)
        side_id = data.get("side", {}).get("id", "p1")
        self.state.my_side = side_id

        # Rebuild our team from request (always up to date with HP/status/etc.)
        side_pokemon = data.get("side", {}).get("pokemon", [])
        self._rebuild_team(side_pokemon, side_id)

        if data.get("forceSwitch"):
            self._handle_force_switch(data)
        else:
            self._handle_normal_turn(data, side_pokemon)

        self.state.rqid = data.get("rqid")
        self.state.my_slot_decisions = []   # fresh slate for this turn's cross-slot coordination

        # Always attempt a decision here.  _maybe_decide() is guarded by rqid.
        await self._maybe_decide()

    async def _handle_team_preview(self, data: dict) -> None:
        """Handle a teamPreview |request| — populate team and fire decision."""
        self.state.team_preview  = True
        self.state.max_team_size = data.get("maxChosenTeamSize", 4)
        side_id = data.get("side", {}).get("id", "p1")
        self.state.my_side = side_id
        side_pokemon = data.get("side", {}).get("pokemon", [])
        self.state.my_team = [Pokemon.from_request(p, side_id) for p in side_pokemon]
        self.state.rqid = data.get("rqid")
        await self._maybe_decide()

    def _rebuild_team(self, side_pokemon: list[dict], side_id: str) -> None:
        """Rebuild my_team from request JSON, preserving item_consumed flags.

        The request JSON always has the latest HP/status/etc.  item_consumed is
        not included in the JSON, so we carry it forward manually — Unburden's
        speed boost must survive until the mon actually switches out.
        """
        _old_item_consumed = {p.ident: p.item_consumed for p in self.state.my_team}
        self.state.my_team = [Pokemon.from_request(p, side_id) for p in side_pokemon]
        for mon in self.state.my_team:
            if _old_item_consumed.get(mon.ident):
                mon.item_consumed = True

    def _handle_force_switch(self, data: dict) -> None:
        """Populate state for a force-switch phase (one or more Pokémon fainted).

        active[] is absent/null in force-switch requests.  my_actives is kept
        as-is so fainted mons still occupy their slots until the switch resolves.
        available_switches excludes fainted mons and the still-active ones.
        """
        force_switch_raw = data.get("forceSwitch") or []
        self.state.force_switch = [bool(x) for x in force_switch_raw]
        num_slots = len(force_switch_raw)
        self.state.moves_per_slot   = [[] for _ in range(num_slots)]
        self.state.can_terastallize = [False] * num_slots
        self.state.can_mega_evo     = [False] * num_slots
        # A forced switch is mandatory — never trapped — and clearing any stale
        # trapped flag keeps _build_actions from suppressing the required switch.
        self.state.trapped          = [False] * num_slots
        active_idents = {p.ident for p in self.state.my_actives if p is not None}
        self.state.available_switches = [
            p for p in self.state.my_team
            if not p.fainted and p.ident not in active_idents
        ]

    def _handle_normal_turn(self, data: dict, side_pokemon: list[dict]) -> None:
        """Populate state for a normal turn (moves available, no force-switch)."""
        active_list = data.get("active") or []
        num_slots = len(active_list) if active_list else 1

        self.state.force_switch   = [False] * num_slots
        self.state.moves_per_slot = [slot.get("moves", []) for slot in active_list]
        # canTerastallize is a tera-type string (e.g. "Flying") when the mon
        # CAN tera, or false/absent when it cannot.  Coerce to bool.
        self.state.can_terastallize = [
            bool(slot.get("canTerastallize")) for slot in active_list
        ]
        self.state.can_mega_evo = [
            bool(slot.get("canMegaEvo")) for slot in active_list
        ]
        # `trapped: true` means this slot may not switch (Shadow Tag, Arena Trap,
        # trapping move, …).  `maybeTrapped` is only a hint — the switch is still
        # legal — so it is intentionally NOT treated as trapped here.
        self.state.trapped = [
            bool(slot.get("trapped")) for slot in active_list
        ]

        # Identify which team members are currently active (in slot order)
        active_side_entries = [p for p in side_pokemon if p.get("active")]
        active_team_mons: list[Optional[Pokemon]] = []
        for p_data in active_side_entries:
            mon = next(
                (p for p in self.state.my_team if p.ident == p_data["ident"]), None
            )
            active_team_mons.append(mon)
        if active_team_mons:
            self.state.my_actives = active_team_mons

        active_idents = {p.ident for p in self.state.my_actives if p is not None}
        self.state.available_switches = [
            p for p in self.state.my_team
            if not p.fainted and p.ident not in active_idents
        ]

    async def _on_turn(self, args: list[str]):
        self.state.turn = int(args[0]) if args else self.state.turn + 1
        # Decrement field-condition counters so decision modules see the
        # correct remaining-turn count when the request arrives.
        if self.state.my_tailwind_turns_left > 0:
            self.state.my_tailwind_turns_left -= 1
        if self.state.opp_tailwind_turns_left > 0:
            self.state.opp_tailwind_turns_left -= 1
        if self.state.trick_room_turns_left > 0:
            self.state.trick_room_turns_left -= 1
        await self._maybe_decide()

    async def _on_switch(self, args: list[str]):
        # |switch|IDENT|DETAILS|HP  (also handles |drag|)
        if len(args) < 3:
            return
        ident, details, condition = args[0], args[1], args[2]
        side  = _side_from_ident(ident)
        slot  = _slot_from_ident(ident)   # 0 for slot-a, 1 for slot-b
        species = details.split(",")[0]
        hp, max_hp = _parse_hp(condition)
        status = _parse_status(condition)

        mon = Pokemon(
            ident=_normalize_ident(ident),
            species=species,
            hp=hp,
            max_hp=max_hp,
            status=status,
            hp_is_percentage=(side != self.state.my_side and max_hp == 100),
        )

        if side == self.state.my_side:
            updated = _update_or_add(self.state.my_team, mon)
            # Grow list if this is a slot we haven't seen yet
            while len(self.state.my_actives) <= slot:
                self.state.my_actives.append(None)
            self.state.my_actives[slot] = updated
            # Reset last-move for this slot so ProtectModule doesn't penalise
            # the incoming mon for its predecessor's consecutive Protect.
            while len(self.state.my_last_moves) <= slot:
                self.state.my_last_moves.append("")
            self.state.my_last_moves[slot] = ""
            # Clear any Disable/Encore lock — new mon on field starts clean.
            while len(self.state.my_disabled_moves) <= slot:
                self.state.my_disabled_moves.append(None)
            while len(self.state.my_encored_moves) <= slot:
                self.state.my_encored_moves.append(None)
            self.state.my_disabled_moves[slot] = None
            self.state.my_encored_moves[slot] = None
        else:
            updated = _update_or_add(self.state.opp_team, mon)
            while len(self.state.opp_actives) <= slot:
                self.state.opp_actives.append(None)
            self.state.opp_actives[slot] = updated
            # Reset last-move for this slot so FakeOutModule correctly treats
            # the incoming mon as a Fake Out threat until it reveals a move.
            while len(self.state.opp_last_moves) <= slot:
                self.state.opp_last_moves.append("")
            self.state.opp_last_moves[slot] = ""

    async def _on_move(self, args: list[str]):
        # |move|SOURCE|MOVENAME|TARGET
        # Track revealed opponent moves; also remember our last move per slot.
        if len(args) < 2:
            return
        ident, move_name = args[0], args[1]
        side = _side_from_ident(ident)
        if side != self.state.my_side:
            mon = self._find_mon(ident)
            if mon and move_name not in mon.moves:
                mon.moves.append(move_name)
        else:
            slot = _slot_from_ident(ident)
            while len(self.state.my_last_moves) <= slot:
                self.state.my_last_moves.append("")
            self.state.my_last_moves[slot] = move_name
            return

        # Opponent move — track for Protect-spam and doubling-up detection
        slot = _slot_from_ident(ident)
        while len(self.state.opp_last_moves) <= slot:
            self.state.opp_last_moves.append("")
        self.state.opp_last_moves[slot] = move_name

    async def _on_damage(self, args: list[str]):
        if len(args) < 2:
            return
        self._apply_hp_update(args[0], args[1])

    async def _on_heal(self, args: list[str]):
        if len(args) < 2:
            return
        self._apply_hp_update(args[0], args[1])

    async def _on_status(self, args: list[str]):
        if len(args) < 2:
            return
        mon = self._find_mon(args[0])
        if mon:
            mon.status = args[1]

    async def _on_curestatus(self, args: list[str]):
        mon = self._find_mon(args[0]) if args else None
        if mon:
            mon.status = None

    async def _on_boost(self, args: list[str]):
        if len(args) < 3:
            return
        mon = self._find_mon(args[0])
        if mon:
            mon.boosts[args[1]] = mon.boosts.get(args[1], 0) + int(args[2])

    async def _on_unboost(self, args: list[str]):
        if len(args) < 3:
            return
        mon = self._find_mon(args[0])
        if mon:
            mon.boosts[args[1]] = mon.boosts.get(args[1], 0) - int(args[2])

    async def _on_weather(self, args: list[str]):
        # Showdown sends the move-name form ("RainDance", "SunnyDay",
        # "Sandstorm", …); the damage calc and turn-order speed abilities expect
        # the canonical short keys ("rain"/"sun"/"sand"/"hail").  Normalise here
        # so weather-boosted damage (e.g. Water in rain) is actually applied.
        raw = (args[0] if args else "") or ""
        aliases = {
            "raindance": "rain", "primordialsea": "rain", "rain": "rain",
            "sunnyday": "sun", "desolateland": "sun", "sun": "sun",
            "sandstorm": "sand", "sand": "sand",
            "snow": "hail", "hail": "hail",
        }
        self.state.weather = aliases.get(raw.strip().lower().replace(" ", ""))

    async def _on_sidestart(self, args: list[str]):
        # PS format: |-sidestart|SIDE|CONDITION
        # SIDE may be "p1", "p2: Alice" (with player name), or "p2: Tailwind" (older fmt).
        # CONDITION is always in args[1]: "Tailwind" or "move: Tailwind".
        # We extract the player number from args[0] and the condition from args[1].
        if len(args) < 2:
            return
        m = re.match(r'(p\d+)', args[0])
        if not m:
            return
        side      = m.group(1)
        condition = args[1].lower()
        if "tailwind" in condition:
            if side == self.state.my_side:
                self.state.my_tailwind = True
                self.state.my_tailwind_turns_left = 4
            else:
                self.state.opp_tailwind = True
                self.state.opp_tailwind_turns_left = 4
        for kw, name in (("aurora veil", "auroraveil"),
                         ("light screen", "lightscreen"), ("reflect", "reflect")):
            if kw in condition:
                target = (self.state.my_screens if side == self.state.my_side
                          else self.state.opp_screens)
                target.add(name)
                break

    async def _on_sideend(self, args: list[str]):
        # Same format as _on_sidestart — condition is in args[1].
        if len(args) < 2:
            return
        m = re.match(r'(p\d+)', args[0])
        if not m:
            return
        side      = m.group(1)
        condition = args[1].lower()
        if "tailwind" in condition:
            if side == self.state.my_side:
                self.state.my_tailwind = False
                self.state.my_tailwind_turns_left = 0
            else:
                self.state.opp_tailwind = False
                self.state.opp_tailwind_turns_left = 0
        for kw, name in (("aurora veil", "auroraveil"),
                         ("light screen", "lightscreen"), ("reflect", "reflect")):
            if kw in condition:
                target = (self.state.my_screens if side == self.state.my_side
                          else self.state.opp_screens)
                target.discard(name)
                break

    async def _on_fieldstart(self, args: list[str]):
        condition = args[0] if args else ""
        clean = re.sub(r'^(?:move|ability|item): ', '', condition)
        if "trick room" in clean.lower():
            self.state.trick_room = True
            self.state.trick_room_turns_left = 5
        else:
            self.state.terrain = clean

    async def _on_fieldend(self, args: list[str]):
        condition = args[0] if args else ""
        clean = re.sub(r'^(?:move|ability|item): ', '', condition)
        if "trick room" in clean.lower():
            self.state.trick_room = False
            self.state.trick_room_turns_left = 0
        else:
            self.state.terrain = None

    async def _on_player(self, args: list[str]):
        # |player|SIDE|USERNAME|AVATAR|RATING
        if len(args) < 2:
            return
        side_id, name = args[0], args[1]
        if name.strip() == self.my_username.strip():
            self.state.my_side = side_id
            # args[3] is the ELO rating (empty string for unrated / guest battles)
            if len(args) >= 4 and args[3]:
                try:
                    self.state.my_elo = int(args[3])
                except (ValueError, TypeError):
                    pass

    async def _on_gametype(self, args: list[str]):
        # |gametype|singles  or  |gametype|doubles
        if args and args[0] == "doubles":
            self.state.is_doubles = True

    async def _on_clearpoke(self, args: list[str]):
        """Reset the opponent preview list at the start of team preview."""
        self.state.opp_preview_team = []

    async def _on_poke(self, args: list[str]):
        """|poke|SIDE|DETAILS|item — one message per team member during preview."""
        if len(args) < 2:
            return
        side    = args[0]   # "p1" or "p2"
        details = args[1]   # "Garchomp, L50, M" etc.
        species = details.split(",")[0].strip()
        if side != self.state.my_side:
            if species not in self.state.opp_preview_team:
                self.state.opp_preview_team.append(species)

    async def _on_faint(self, args: list[str]):
        mon = self._find_mon(args[0]) if args else None
        if mon:
            mon.fainted = True
            mon.hp = 0

    async def _on_win(self, args: list[str]):
        winner = args[0] if args else "unknown"
        won = (winner.strip() == self.my_username.strip())
        _log.info("Battle over — %s (winner: %s)", "WIN" if won else "LOSS", winner.strip())
        if self.on_battle_end:
            await self.on_battle_end(won)

    async def _on_ability(self, args: list[str]):
        if len(args) < 2:
            return
        mon = self._find_mon(args[0])
        if mon:
            mon.ability = args[1]

    async def _on_item(self, args: list[str]):
        if len(args) < 2:
            return
        mon = self._find_mon(args[0])
        if mon:
            mon.item = args[1]

    async def _on_enditem(self, args: list[str]):
        if len(args) < 1:
            return
        mon = self._find_mon(args[0])
        if mon:
            mon.item = None
            mon.item_consumed = True

    async def _on_detailschange(self, args: list[str]):
        if len(args) < 2:
            return
        mon = self._find_mon(args[0])
        if mon:
            mon.species = args[1].split(",")[0]

    async def _on_error(self, args: list[str]):
        msg = args[0] if args else "unknown"
        _log.error("Choice rejected by server: %s", msg)
        # Allow the re-sent |request| (same rqid) to trigger a new decision.
        # Without this reset the dedup guard in _maybe_decide prevents recovery
        # and the bot sits idle until the timer auto-picks.
        self.state.last_rqid_handled = None

    async def _on_terastallize(self, args: list[str]):
        """|-terastallize|IDENT|TYPE — record that a Pokémon has Terastallized.

        Critical for damage accuracy: a Terastallized mon loses its original
        defensive typing and gains the Tera type instead.  The damage calculator
        already reads ``mon.terastallized`` and ``mon.tera_type``; we just need
        to set them here when Showdown confirms the activation.
        """
        if len(args) < 2:
            return
        mon = self._find_mon(args[0])
        if mon:
            mon.terastallized = True
            mon.tera_type = args[1]

    async def _on_cant(self, args: list[str]):
        """|cant|IDENT|REASON[|MOVE] — the Pokémon's action was prevented.

        Common causes: flinch, paralysis roll, sleep, freeze, confusion,
        Taunt, Disable, Encore forcing an unavailable move, etc.

        When this fires, |move| does NOT fire for that slot, so
        ``opp_last_moves`` (or ``my_last_moves``) would retain the previous
        turn's stale value.  Clearing to "" prevents ProtectModule from seeing
        two consecutive Protects when there was only one, and prevents
        FakeOutModule from treating a flinched mon as having used a move.
        """
        if not args:
            return
        ident = args[0]
        side = _side_from_ident(ident)
        slot = _slot_from_ident(ident)
        if side == self.state.my_side:
            while len(self.state.my_last_moves) <= slot:
                self.state.my_last_moves.append("")
            self.state.my_last_moves[slot] = ""
        else:
            while len(self.state.opp_last_moves) <= slot:
                self.state.opp_last_moves.append("")
            self.state.opp_last_moves[slot] = ""

    async def _on_activate(self, args: list[str]):
        """|-activate|IDENT|EFFECT[|DETAIL] — catch move: Disable to track locked moves.

        Showdown fires: |-activate|p1a: Venusaur|move: Disable|Giga Drain
        We record the Disabled move name so _build_actions can filter it out.
        """
        if len(args) < 3:
            return
        ident, effect = args[0], args[1]
        # Only care about Disable affecting our own Pokémon.
        if _side_from_ident(ident) != self.state.my_side:
            return
        if "disable" not in effect.lower():
            return
        slot = _slot_from_ident(ident)
        disabled_move = args[2] if len(args) >= 3 else ""
        if not disabled_move:
            return
        while len(self.state.my_disabled_moves) <= slot:
            self.state.my_disabled_moves.append(None)
        self.state.my_disabled_moves[slot] = disabled_move
        _log.info("DISABLE  slot %d  move '%s' is now disabled", slot, disabled_move)

    async def _on_start(self, args: list[str]):
        """|-start|IDENT|EFFECT — catch Encore to lock us into the last move used.

        Showdown fires: |-start|p1a: Venusaur|Encore
        We record the move our slot last used; _build_actions will allow only that.
        """
        if len(args) < 2:
            return
        ident, effect = args[0], args[1]
        if _side_from_ident(ident) != self.state.my_side:
            return
        if "encore" not in effect.lower():
            return
        slot = _slot_from_ident(ident)
        # The move we're locked into is the one we used last turn.
        while len(self.state.my_last_moves) <= slot:
            self.state.my_last_moves.append("")
        locked_move = self.state.my_last_moves[slot]
        while len(self.state.my_encored_moves) <= slot:
            self.state.my_encored_moves.append(None)
        self.state.my_encored_moves[slot] = locked_move or None
        _log.info("ENCORE  slot %d  locked into '%s'", slot, locked_move)

    async def _on_end(self, args: list[str]):
        """|-end|IDENT|EFFECT — clear Disable or Encore when the effect ends."""
        if len(args) < 2:
            return
        ident, effect = args[0], args[1]
        if _side_from_ident(ident) != self.state.my_side:
            return
        slot = _slot_from_ident(ident)
        effect_lower = effect.lower()
        if "disable" in effect_lower:
            while len(self.state.my_disabled_moves) <= slot:
                self.state.my_disabled_moves.append(None)
            self.state.my_disabled_moves[slot] = None
            _log.info("DISABLE ended  slot %d", slot)
        elif "encore" in effect_lower:
            while len(self.state.my_encored_moves) <= slot:
                self.state.my_encored_moves.append(None)
            self.state.my_encored_moves[slot] = None
            _log.info("ENCORE ended  slot %d", slot)

    async def _on_clearboost(self, args: list[str]):
        """|-clearboost|IDENT — reset all stat stages for one Pokémon.

        Fired by Haze (clears each adjacent mon individually) and Clear Smog
        (clears only the target).  Both are seen in VGC.
        """
        if not args:
            return
        mon = self._find_mon(args[0])
        if mon:
            for key in list(mon.boosts.keys()):
                mon.boosts[key] = 0

    async def _on_clearallboost(self, args: list[str]):
        """|-clearallboost — reset all stat stages for every Pokémon on the field."""
        for mon in self.state.my_team + self.state.opp_team:
            for key in list(mon.boosts.keys()):
                mon.boosts[key] = 0

    async def _on_invertboost(self, args: list[str]):
        """|-invertboost|IDENT — invert all stat stages (Topsy-Turvy)."""
        if not args:
            return
        mon = self._find_mon(args[0])
        if mon:
            for key in list(mon.boosts.keys()):
                mon.boosts[key] = -mon.boosts[key]

    async def _on_setboost(self, args: list[str]):
        """|-setboost|IDENT|STAT|AMOUNT — set a stat stage to an explicit value.

        Used by Psych Up (copies target's boosts), Guard Swap, Power Swap, etc.
        """
        if len(args) < 3:
            return
        mon = self._find_mon(args[0])
        if mon:
            try:
                mon.boosts[args[1]] = int(args[2])
            except (ValueError, KeyError):
                pass

    async def _on_transform(self, args: list[str]):
        """|-transform|IDENT|TARGET — copy species and revealed moves.

        Fired when Transform or Imposter activates.  We copy the target's
        species (for data lookups) and its currently-revealed move list
        (so the bot doesn't think Ditto has an empty moveset mid-battle).
        Stats are not stored on the Pokemon object so no update is needed there.
        """
        if len(args) < 2:
            return
        mon = self._find_mon(args[0])
        target = self._find_mon(args[1])
        if mon and target:
            mon.species = target.species
            mon.moves = list(target.moves)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    async def _maybe_decide(self):
        """Fire on_decision_needed only once per rqid to prevent stale replays."""
        if self.state.rqid != self.state.last_rqid_handled:
            self.state.last_rqid_handled = self.state.rqid
            await self.on_decision_needed(self.state)

    def _find_mon(self, ident: str) -> Optional[Pokemon]:
        normalized = _normalize_ident(ident)
        side = _side_from_ident(ident)
        team = self.state.my_team if side == self.state.my_side else self.state.opp_team
        return next((p for p in team if p.ident == normalized), None)

    def _apply_hp_update(self, ident: str, condition: str):
        mon = self._find_mon(ident)
        if mon:
            mon.hp, mon.max_hp = _parse_hp(condition)
            mon.status = _parse_status(condition)
            mon.fainted = (condition.strip() == "0 fnt")


# ─── Handler Registry ────────────────────────────────────────────────────────

_HANDLERS = {
    "request":        BattleParser._on_request,
    "turn":           BattleParser._on_turn,
    "switch":         BattleParser._on_switch,
    "drag":           BattleParser._on_switch,      # same format
    "replace":        BattleParser._on_switch,      # zen mode etc
    "move":           BattleParser._on_move,
    "-damage":        BattleParser._on_damage,
    "-heal":          BattleParser._on_heal,
    "-sethp":         BattleParser._on_damage,      # same handling
    "-status":        BattleParser._on_status,
    "-curestatus":    BattleParser._on_curestatus,
    "-boost":         BattleParser._on_boost,
    "-unboost":       BattleParser._on_unboost,
    "weather":        BattleParser._on_weather,
    "-weather":       BattleParser._on_weather,
    "-sidestart":     BattleParser._on_sidestart,
    "-sideend":       BattleParser._on_sideend,
    "-fieldstart":    BattleParser._on_fieldstart,
    "-fieldend":      BattleParser._on_fieldend,
    "player":         BattleParser._on_player,
    "gametype":       BattleParser._on_gametype,
    "clearpoke":      BattleParser._on_clearpoke,
    "poke":           BattleParser._on_poke,
    "faint":          BattleParser._on_faint,
    "win":            BattleParser._on_win,
    "tie":            BattleParser._on_win,
    "-ability":       BattleParser._on_ability,
    "-item":          BattleParser._on_item,
    "-enditem":       BattleParser._on_enditem,
    "detailschange":  BattleParser._on_detailschange,
    "-formechange":   BattleParser._on_detailschange,
    "error":          BattleParser._on_error,
    # ── New in Area 3 audit ──────────────────────────────────────────────────
    "-terastallize":  BattleParser._on_terastallize,
    "cant":           BattleParser._on_cant,
    "-clearboost":    BattleParser._on_clearboost,
    "-clearallboost": BattleParser._on_clearallboost,
    "-invertboost":   BattleParser._on_invertboost,
    "-setboost":      BattleParser._on_setboost,
    "-transform":     BattleParser._on_transform,
    # ── Disable / Encore tracking ────────────────────────────────────────────
    "-activate":      BattleParser._on_activate,
    "-start":         BattleParser._on_start,
    "-end":           BattleParser._on_end,
}


# ─── Utility Functions ────────────────────────────────────────────────────────

def _side_from_ident(ident: str) -> str:
    """'p2a: Garchomp' → 'p2'"""
    return ident[:2]


def _slot_from_ident(ident: str) -> int:
    """'p1a: Garganacl' → 0  |  'p1b: Clefable' → 1  |  'p1: X' → 0"""
    if len(ident) >= 3 and ident[2].isalpha() and ident[2] != ':':
        return ord(ident[2].lower()) - ord('a')
    return 0


def _normalize_ident(ident: str) -> str:
    """'p1a: Garganacl' → 'p1: Garganacl' (strip slot letter for team lookup)"""
    return re.sub(r"^(p\d)[a-z]:", r"\1:", ident)



def _update_or_add(team: list[Pokemon], mon: Pokemon) -> Pokemon:
    """Update existing entry by ident, or append if new (opponent reveals)."""
    for i, existing in enumerate(team):
        if existing.ident == mon.ident:
            team[i] = mon
            return team[i]
    team.append(mon)
    return mon
