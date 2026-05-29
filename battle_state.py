"""battle_state.py — BattleState and Pokemon dataclasses for WolfeyBot.

These data classes are the shared state object threaded through the parser
(battle.py), the decision engine (decision/), and the recorder (recorder.py).
Keeping them separate from the protocol parser makes them independently
importable by modules that need state but not parsing logic.

For backward compatibility, battle.py re-exports both classes so the common
import pattern ``from battle import BattleParser, BattleState, Pokemon``
continues to work unchanged.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import re


# ── HP / status parsers (used by Pokemon.from_request and BattleParser) ──────

def _parse_hp(condition: str) -> tuple[int, int]:
    """'281/281 brn' → (281, 281). '0 fnt' → (0, 0)."""
    if not condition or condition.strip() == "0 fnt":
        return 0, 0
    match = re.match(r"(\d+)/(\d+)", condition)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 0, 0


def _parse_status(condition: str) -> Optional[str]:
    """'281/281 brn' → 'brn'. '281/281' or '0 fnt' → None."""
    if not condition or "fnt" in condition:
        return None
    parts = condition.strip().split(" ")
    return parts[1] if len(parts) >= 2 else None


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class Pokemon:
    ident: str  # "p1: Garganacl"
    species: str
    hp: int
    max_hp: int
    fainted: bool = False
    status: Optional[str] = None  # "brn" "par" "slp" "frz" "psn" "tox"
    boosts: dict = field(default_factory=lambda: {
        "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0, "accuracy": 0, "evasion": 0
    })
    ability: Optional[str] = None
    item: Optional[str] = None
    moves: list[str] = field(default_factory=list)  # revealed moves
    terastallized: bool = False
    tera_type: Optional[str] = None
    # True when HP was sent as x/100 percentage (non-randbat opponent); max_hp is not real stat.
    hp_is_percentage: bool = False
    # True once the held item has been consumed or removed this field stint.
    # Cleared automatically when a Pokémon switches out (new Pokemon object created).
    # Used by turn_order to apply the Unburden speed doubling.
    item_consumed: bool = False

    @property
    def hp_fraction(self) -> float:
        return self.hp / self.max_hp if self.max_hp else 0.0

    @classmethod
    def from_request(cls, data: dict, side_id: str) -> "Pokemon":
        """Build from |request| JSON side.pokemon entry."""
        species = data["details"].split(",")[0]
        hp, max_hp = _parse_hp(data["condition"])
        return cls(
            ident=data["ident"],
            species=species,
            hp=hp,
            max_hp=max_hp,
            fainted=(data["condition"] == "0 fnt"),
            ability=data.get("ability"),
            item=data.get("item"),
            moves=data.get("moves", []),
            tera_type=data.get("teraType"),
            terastallized=data.get("terastallized", False),
        )


@dataclass
class BattleState:
    battle_id: str
    my_side: str  # "p1" or "p2"
    turn: int = 0
    weather: Optional[str] = None
    terrain: Optional[str] = None
    trick_room: bool = False
    is_doubles: bool = False

    # My side — populated from |request|
    my_team: list[Pokemon] = field(default_factory=list)
    # Active slots: length 1 for singles, 2 for doubles.
    # my_actives[0] = slot-a mon, my_actives[1] = slot-b mon (doubles only).
    my_actives: list[Optional[Pokemon]] = field(default_factory=list)

    # Opponent — built from observed messages only
    opp_team: list[Pokemon] = field(default_factory=list)
    opp_actives: list[Optional[Pokemon]] = field(default_factory=list)

    # Side conditions
    my_tailwind:  bool = False   # Tailwind active on our side
    opp_tailwind: bool = False   # Tailwind active on opponent's side
    # Damage-reducing screens active per side, as a set of canonical names:
    # {"reflect", "lightscreen", "auroraveil"}.  In doubles each reduces the
    # matching damage category to 2/3 (crits bypass; Aurora Veil covers both).
    my_screens:  set = field(default_factory=set)
    opp_screens: set = field(default_factory=set)
    # Turns remaining for each field condition (0 = not active).
    # Set when the condition starts; decremented each turn; zeroed when it ends.
    # Tailwind lasts 4 turns (including the turn it is used).
    # Trick Room lasts 5 turns (including the turn it is used).
    my_tailwind_turns_left:  int = 0
    opp_tailwind_turns_left: int = 0
    trick_room_turns_left:   int = 0

    # Last move used by each of our active slots (indexed by slot, "" = unknown).
    # Updated from |move| messages so ProtectModule can detect consecutive Protect.
    my_last_moves: list[str] = field(default_factory=list)

    # Disable / Encore tracking — per active slot (index matches my_actives).
    # my_disabled_moves[slot] = move name that has been Disabled on that slot,
    #   or None if no move is currently Disabled.
    # my_encored_moves[slot]  = move name that slot is locked into by Encore,
    #   or None if no Encore is in effect.
    # Both are cleared on switch-out and when the effect ends (|-end| message).
    my_disabled_moves: list[Optional[str]] = field(default_factory=list)
    my_encored_moves:  list[Optional[str]] = field(default_factory=list)

    # Last move used by each opponent slot (indexed by slot, "" = unknown).
    # Updated from |move| messages so DoublingUpModule can detect opponent Protect.
    opp_last_moves: list[str] = field(default_factory=list)

    # Actions decided for each of our slots so far this turn.
    # Populated by _build_choice in main.py after each slot is resolved so that
    # later-slot modules can see what earlier slots committed to targeting.
    # Reset to [] at the start of every new request.
    my_slot_decisions: list = field(default_factory=list)

    # Current request data (from most recent |request| message)
    # moves_per_slot[i] = list of move dicts for active slot i
    moves_per_slot: list[list[dict]] = field(default_factory=list)
    available_switches: list[Pokemon] = field(default_factory=list)
    # Per-slot tera, mega, and force-switch flags (index matches my_actives)
    can_terastallize: list[bool] = field(default_factory=list)
    can_mega_evo:     list[bool] = field(default_factory=list)
    force_switch: list[bool] = field(default_factory=list)
    # trapped[slot] = True when the server says this active mon may not switch
    # (Shadow Tag, Arena Trap, Magnet Pull, a trapping move, etc.).  Read from
    # the |request| active[] entry; _build_actions suppresses switches for it.
    trapped: list[bool] = field(default_factory=list)
    rqid: Optional[int] = None
    last_rqid_handled: Optional[int] = None

    # Elo rating at the START of this battle (parsed from |player| message).
    # None for unrated / guest battles.
    my_elo: Optional[int] = None

    # Team preview state
    team_preview:     bool      = False   # True while waiting for /choose team:
    max_team_size:    int       = 4       # how many Pokémon to bring (from request)
    opp_preview_team: list[str] = field(default_factory=list)  # species seen in |poke|
    # Base species name of the Pokémon that should mega evolve this battle.
    # None = no mega in the selected team (or team preview not yet processed).
    # When set, _build_choice only sends "mega" for the matching active slot.
    designated_mega:  Optional[str] = None

    # Pending request buffer
    _pending_request: Optional[dict] = field(default=None, repr=False)

    # ── Backwards-compat properties for singles / slot-0 access ──────────────

    @property
    def my_active(self) -> Optional[Pokemon]:
        """Slot-0 active (convenience for singles or when only one slot matters)."""
        return self.my_actives[0] if self.my_actives else None

    @property
    def opp_active(self) -> Optional[Pokemon]:
        """Slot-0 opponent active."""
        return self.opp_actives[0] if self.opp_actives else None

    @property
    def available_moves(self) -> list[dict]:
        """Slot-0 move list (backwards compat for singles callers)."""
        return self.moves_per_slot[0] if self.moves_per_slot else []
