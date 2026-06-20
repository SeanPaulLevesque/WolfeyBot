"""Unit tests for tools/team_report.py compute helpers.

These exercise the pure aggregation functions on synthetic in-memory game dicts
(battle-log schema) — no filesystem, no real logs — so the report's roster /
move-usage / game-length math stays correct as the tool evolves.
"""
import json

from tools.team_report import roster_stats, move_usage, length_buckets, load_games


def _turn(my, team=None, dec=None, ev=None):
    t = {"my": my, "opp": []}
    if team is not None:
        t["team"] = team
    if dec is not None:
        t["dec"] = dec
    if ev is not None:
        t["ev"] = ev
    return t


# A 2-turn WIN: lead Garchomp+Kingambit; bench Sneasler, Venusaur.
# Garchomp KOs with Dragon Claw (d ≥ h0); Kingambit Protects; Sneasler faints.
_GAME_WIN = {
    "outcome": "win",
    "turns": [
        _turn(
            my=[{"s": "Garchomp", "hp": 1.0}, {"s": "Kingambit", "hp": 1.0}],
            team=[{"s": "Garchomp"}, {"s": "Kingambit"}, {"s": "Sneasler"}, {"s": "Venusaur"}],
            dec=[{"sl": 0, "ch": "Dragon Claw"}, {"sl": 1, "ch": "Protect"}],
            ev=[{"o": 0, "sd": "us", "a": "Garchomp", "mv": "Dragon Claw",
                 "tg": "Pelipper", "h0": 0.5, "d": 0.6}],
        ),
        _turn(
            my=[{"s": "Garchomp", "hp": 1.0}, {"s": "Sneasler", "hp": 0.0}],
            dec=[{"sl": 0, "ch": "Dragon Claw"}, {"sl": 1, "ch": "Switch Venusaur"}],
        ),
    ],
}

# An 8-turn LOSS: lead Garchomp+Venusaur; bench Staraptor, Kingambit.
_GAME_LOSS = {
    "outcome": "loss",
    "turns": [
        _turn(
            my=[{"s": "Garchomp", "hp": 1.0}, {"s": "Venusaur", "hp": 1.0}],
            team=[{"s": "Garchomp"}, {"s": "Venusaur"}, {"s": "Staraptor"}, {"s": "Kingambit"}],
            dec=[{"sl": 0, "ch": "Poison Jab"}, {"sl": 1, "ch": "Sludge Bomb"}],
        ),
    ] + [_turn(my=[{"s": "Garchomp", "hp": 1.0}, {"s": "Venusaur", "hp": 1.0}])
         for _ in range(7)],   # pad to 8 turns total -> "7-9" bucket
}


class TestRosterStats:
    def test_bring_and_lead_counts(self):
        s = roster_stats([_GAME_WIN, _GAME_LOSS])
        assert s["Garchomp"]["bring"] == 2          # brought both games
        assert s["Garchomp"]["lead"] == 2           # led both games
        assert s["Staraptor"]["bring"] == 1         # only in the loss
        assert s["Staraptor"]["lead"] == 0          # benched (not a lead)

    def test_win_when_brought(self):
        s = roster_stats([_GAME_WIN, _GAME_LOSS])
        assert s["Kingambit"]["games_brought"] == 2
        assert s["Kingambit"]["wins_brought"] == 1  # win game only
        assert s["Sneasler"]["wins_brought"] == 1   # brought only in the win

    def test_ko_and_faint_attribution(self):
        s = roster_stats([_GAME_WIN])
        assert s["Garchomp"]["kos"] == 1            # the one d≥h0 hit (turn 1)
        assert s["Sneasler"]["faints"] == 1         # observed at 0 HP once
        assert s["Garchomp"]["faints"] == 0

    def test_faint_counted_once_per_game(self):
        # Sneasler at 0 HP across two turns should still count as one faint.
        g = {"outcome": "loss", "turns": [
            _turn(my=[{"s": "Sneasler", "hp": 0.0}], team=[{"s": "Sneasler"}]),
            _turn(my=[{"s": "Sneasler", "hp": 0.0}]),
        ]}
        assert roster_stats([g])["Sneasler"]["faints"] == 1


class TestMoveUsage:
    def test_counts_chosen_moves_excluding_switches(self):
        u = move_usage([_GAME_WIN])
        assert u["Garchomp"]["Dragon Claw"] == 2
        assert u["Kingambit"]["Protect"] == 1
        # "Switch Venusaur" must not appear as a move use.
        assert "Switch Venusaur" not in u.get("Sneasler", {})


class TestLoadGames:
    def _write(self, p, obj):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj), encoding="utf-8")

    def test_loads_recursively_and_filters_by_team(self, tmp_path):
        self._write(tmp_path / "v1" / "a.json", {"outcome": "win"})
        self._write(tmp_path / "v2" / "b.json", {"outcome": "loss"})
        self._write(tmp_path / "v2" / "deep" / "c.json", {"outcome": "win"})
        # No filter: all three logs, recursively.
        assert len(load_games(str(tmp_path))) == 3
        # team=v2: only the two under a /v2/ path segment.
        v2 = load_games(str(tmp_path), team_version="v2")
        assert len(v2) == 2
        assert {g["outcome"] for g in v2} == {"loss", "win"}

    def test_missing_dir_returns_empty(self, tmp_path):
        assert load_games(str(tmp_path / "nope")) == []


class TestLengthBuckets:
    def test_buckets_and_winrate(self):
        b = length_buckets([_GAME_WIN, _GAME_LOSS])
        assert b["1-3"] == [1, 1]   # the 2-turn win
        assert b["7-9"] == [0, 1]   # the 8-turn loss
        assert b["4-6"] == [0, 0]
        assert b["10+"] == [0, 0]
