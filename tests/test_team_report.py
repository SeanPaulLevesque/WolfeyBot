"""Unit tests for tools/team_report.py compute helpers.

These exercise the pure aggregation functions on synthetic in-memory game dicts
(battle-log schema) — no filesystem, no real logs — so the report's roster /
move-usage / game-length math stays correct as the tool evolves.
"""
import json

from tools.team_report import (
    roster_stats, move_usage, length_buckets, load_games, derive_team_meta,
    archetype_breakdown, opp_mega_breakdown,
)
from tools.accuracy_report import compute_prediction


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

    def test_faint_from_incoming_ko_when_never_seen_at_zero_hp(self):
        # The real-log case: a fainted mon is replaced by its switch-in before
        # the next decision snapshot, so it is NEVER observed at hp<=0.  The
        # faint must still be counted, from the incoming lethal hit (d >= h0) —
        # symmetric to KO attribution.  (Regression: Basculegion read 0 faints
        # across 23 games it was brought to.)
        g = {"outcome": "loss", "turns": [
            _turn(my=[{"s": "Basculegion", "hp": 0.4}, {"s": "Garchomp", "hp": 1.0}],
                  team=[{"s": "Basculegion"}, {"s": "Garchomp"}],
                  ev=[{"o": 0, "sd": "opp", "a": "Whimsicott", "mv": "Moonblast",
                       "tg": "Basculegion", "h0": 0.4, "d": 0.55}]),
            # next snapshot already shows the switch-in, not the 0-HP Basculegion
            _turn(my=[{"s": "Venusaur", "hp": 1.0}, {"s": "Garchomp", "hp": 1.0}]),
        ]}
        s = roster_stats([g])
        assert s["Basculegion"]["faints"] == 1
        assert "Whimsicott" not in s   # opp attacker is never credited in our roster


class TestMoveUsage:
    def test_counts_chosen_moves_excluding_switches(self):
        u = move_usage([_GAME_WIN])
        assert u["Garchomp"]["Dragon Claw"] == 2
        assert u["Kingambit"]["Protect"] == 1
        # "Switch Venusaur" must not appear as a move use.
        assert "Switch Venusaur" not in u.get("Sneasler", {})


class TestArchetypeBreakdown:
    def _g(self, outcome, *turns):
        return {"outcome": outcome, "turns": list(turns)}

    def test_multilabel_and_winrate(self):
        games = [
            # WIN vs Tailwind + Sun
            self._g("win", {"tw": {"opp": True}}, {"w": "sun"}),
            # LOSS vs Trick Room
            self._g("loss", {"tr": True}),
            # LOSS vs Sun (so Sun is 1-1)
            self._g("loss", {"w": "sun"}),
            # WIN vs nothing -> None
            self._g("win", {}),
        ]
        a = archetype_breakdown(games)
        assert a["Tailwind"] == [1, 1]
        assert a["Sun"] == [1, 2]        # one win, one loss
        assert a["Trick Room"] == [0, 1]
        assert a["None"] == [1, 1]
        assert a["Rain"] == [0, 0]       # never seen

    def test_snow_maps_from_hail(self):
        a = archetype_breakdown([self._g("win", {"w": "hail"})])
        assert a["Snow"] == [1, 1]


class TestOppMegaBreakdown:
    def _g(self, outcome, *opp_seqs):
        # opp_seqs: list of opp-active lists per turn
        return {"outcome": outcome,
                "turns": [{"opp": [{"s": s} for s in opp]} for opp in opp_seqs]}

    def test_tally_and_none_bucket(self):
        games = [
            self._g("win", ["Charizard", "Incineroar"], ["Charizard-Mega-Y", "Incineroar"]),
            self._g("loss", ["Charizard-Mega-Y", "Pelipper"]),
            self._g("win", ["Garchomp", "Pelipper"]),   # no mega
        ]
        m = opp_mega_breakdown(games)
        assert m["Charizard-Mega-Y"] == [1, 2]          # one win, one loss
        assert m["None (no mega)"] == [1, 1]
        # None is ordered last
        assert list(m.keys())[-1] == "None (no mega)"


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


class TestDeriveTeamMeta:
    def test_named_team_layout(self):
        files = ["Battle Data/0.17.0/meta-team/v2/battle-x.json"]
        assert derive_team_meta(files) == ("meta-team", "v2")

    def test_windows_separators(self):
        files = [r"Battle Data\0.17.0\off-meta-team\v1\battle-y.json"]
        assert derive_team_meta(files) == ("off-meta-team", "v1")

    def test_flat_layout_returns_none(self):
        files = ["Battle Data/0.9.0/battle-z.json"]
        assert derive_team_meta(files) == (None, None)


class TestComputePrediction:
    """The shared analysis must carry the offense attacker and per-case
    turn-order misreads that the Markdown report renders."""

    # Full 4-move turn: our Garchomp's Poison Jab predicted 100% / pos 1/4, but
    # actually did 30% and resolved 3rd → one offense over-miss + one off-by-2.
    _GAME = {"outcome": "loss", "turns": [{
        "n": 4,
        "tr": False,
        "tw": {"opp": True},
        "my": [{"s": "Garchomp", "hp": 1.0}, {"s": "Sneasler", "hp": 1.0}],
        "opp": [{"s": "Whimsicott"}, {"s": "Sableye"}],
        "dec": [{"sl": 0, "ch": "Poison Jab", "ct": "Whimsicott",
                 "acts": [{"lb": "Poison Jab",
                           "r": ["damage_output: 100% HP -> x3.00", "turn_order: pos 1/4"]}]}],
        "ev": [
            {"o": 0, "sd": "opp", "a": "Whimsicott", "mv": "Moonblast"},
            {"o": 1, "sd": "opp", "a": "Sableye", "mv": "Foul Play"},
            {"o": 2, "sd": "us", "a": "Garchomp", "mv": "Poison Jab",
             "tg": "Whimsicott", "h0": 1.0, "d": 0.3},
            {"o": 3, "sd": "us", "a": "Sneasler", "mv": "Close Combat",
             "tg": "Sableye", "h0": 1.0, "d": 0.5},
        ],
    }]}

    def test_offense_miss_carries_attacker(self):
        s = compute_prediction([self._GAME])
        assert len(s["off_miss"]) == 1
        err, our_mon, mv, tg, pred, act, disp, loc = s["off_miss"][0]
        assert our_mon == "Garchomp" and mv == "Poison Jab" and tg == "Whimsicott"
        assert err < 0          # over-prediction (predicted 100%, actual 30%)
        assert disp == "gap"    # offense defaults to actionable until investigated
        assert loc == "?:t4"    # incident locator (battle:turn) for tracing back

    def test_turn_order_misread_captured(self):
        s = compute_prediction([self._GAME])
        assert s["to_total"] == 1 and s["to_worse"] == 1
        m = s["to_miss"][0]
        assert m["diff"] == 2 and m["mon"] == "my[a]" and m["pred_pos"] == 1
        assert m["act_pos"] == 3 and m["turn"] == 4 and m["loc"] == "?:t4"
        # No priority/TR/paralysis explains it -> a genuine speed gap.
        assert m["disposition"] == "gap"

    def test_turn_order_priority_accepted(self):
        # A +priority opp move (Aqua Jet) resolving ahead explains our mon landing
        # later than predicted -> accepted, not a speed gap.
        game = {"outcome": "loss", "turns": [{
            "n": 1, "tr": False,
            "my": [{"s": "Garchomp", "hp": 1.0}, {"s": "Sneasler", "hp": 1.0}],
            "opp": [{"s": "Basculegion"}, {"s": "Pelipper"}],
            "dec": [{"sl": 0, "ch": "Dragon Claw", "ct": "Basculegion",
                     "acts": [{"lb": "Dragon Claw", "r": ["turn_order: pos 1/4"]}]}],
            "ev": [
                {"o": 0, "sd": "opp", "a": "Basculegion", "mv": "Aqua Jet"},
                {"o": 1, "sd": "us", "a": "Garchomp", "mv": "Dragon Claw", "tg": "Basculegion"},
                {"o": 2, "sd": "us", "a": "Sneasler", "mv": "Close Combat", "tg": "Pelipper"},
                {"o": 3, "sd": "opp", "a": "Pelipper", "mv": "Hurricane"},
            ],
        }]}
        m = compute_prediction([game])["to_miss"][0]
        assert m["disposition"].startswith("accepted: priority")

    def _immune_game(self, predicted_pct):
        """A turn where our move hit an immune target, with the engine predicting
        *predicted_pct* damage."""
        return {"outcome": "loss", "turns": [{
            "my": [{"s": "Garchomp", "hp": 1.0}],
            "opp": [{"s": "Pelipper"}],
            "dec": [{"sl": 0, "ch": "Stomping Tantrum", "ct": "Pelipper",
                     "acts": [{"lb": "Stomping Tantrum",
                               "r": [f"damage_output: {predicted_pct}% HP -> x1.0"]}]}],
            "ev": [{"o": 0, "sd": "us", "a": "Garchomp", "mv": "Stomping Tantrum",
                    "tg": "Pelipper", "h0": 1.0, "z": "immune", "za": None}],
        }]}

    def test_immune_zero_prediction_accepted(self):
        # Forced Choice-lock into a sole immune target: predicted 0% is correct,
        # so it stays in the report but disposition is 'accepted' (not a gap).
        imm = compute_prediction([self._immune_game(0)])["off_immune"]
        assert len(imm) == 1
        assert imm[0][4].startswith("accepted")

    def test_immune_positive_prediction_is_gap(self):
        # We expected damage but the target was immune -> a real model gap.
        imm = compute_prediction([self._immune_game(80)])["off_immune"]
        assert len(imm) == 1 and imm[0][4] == "gap"

    def test_turn_order_misread_board_state(self):
        m = compute_prediction([self._GAME])["to_miss"][0]
        assert m["my"] == ["Garchomp", "Sneasler"]
        assert m["opp"] == ["Whimsicott", "Sableye"]
        assert m["tr"] is False and m["tw"] == {"opp": True}
        # Resolution order, slot-labelled (Whimsicott first → opp[a]).
        assert m["order"] == ["opp[a]", "opp[b]", "my[a]", "my[b]"]


class TestLengthBuckets:
    def test_buckets_and_winrate(self):
        b = length_buckets([_GAME_WIN, _GAME_LOSS])
        assert b["1-3"] == [1, 1]   # the 2-turn win
        assert b["7-9"] == [0, 1]   # the 8-turn loss
        assert b["4-6"] == [0, 0]
        assert b["10+"] == [0, 0]
