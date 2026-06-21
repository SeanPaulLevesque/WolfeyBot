"""test_teams.py — Named-team infrastructure (0.9.0).

Covers team.py's manifest/version resolution, the active-team selector (and its
baseline fallback), validation, the ELO-log A/B tagging and --max-games bounded
run in main, and the named-team login-failure abort.

The resolution/manifest/validation/selector tests run against a **temp fixture
``teams/`` directory** (see the ``fixture_teams`` fixture) rather than the live
repo rosters, so they stay green as real teams are added / renamed / versioned.
A single smoke test (TestRealTeams) checks the actually-shipped teams without
hardcoding their names.  Recorder path-nesting lives in test_recorder.py
(TestNamedTeamPath).
"""
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

import team


# A minimal but real Champions-legal paste — enough for validate_team / get_team
# to compute stats.  One mon keeps the fixtures small.
_FIXTURE_PASTE = """Garchomp @ Choice Scarf
Ability: Rough Skin
Level: 50
EVs: 5 HP / 32 Atk / 29 Spe
Adamant Nature
- Dragon Claw
- Stomping Tantrum
- Poison Jab
- Rock Tomb
"""


# The active-team selector and manifest cache are process-global; reset after
# every test so nothing leaks between tests (or out to other modules that expect
# the real team.txt baseline).
@pytest.fixture(autouse=True)
def _reset_team_state():
    yield
    team.set_active_team(None)
    team._reset_manifest_cache()
    team.get_team(reload=True)


@pytest.fixture
def fixture_teams(monkeypatch, tmp_path):
    """A self-contained temp ``teams/`` tree, so tests don't couple to the live
    repo rosters.  Layout:

        alpha/        v1, v2, v10   (manifest: acctA, current v1)   ← natural sort
        beta/         v1            (manifest: acctB, current v1)
        nomanifest/   v1, v3        (NOT in manifest)               ← disk fallback
        empty-team/   (no versions) (manifest: acctA, current v1)   ← missing roster
    """
    root = tmp_path / "teams"
    for name, versions in {
        "alpha": ("v1", "v2", "v10"),
        "beta": ("v1",),
        "nomanifest": ("v1", "v3"),
    }.items():
        (root / name).mkdir(parents=True, exist_ok=True)
        for v in versions:
            (root / name / f"{v}.txt").write_text(_FIXTURE_PASTE, encoding="utf-8")
    (root / "empty-team").mkdir(parents=True, exist_ok=True)
    manifest = {
        "alpha":      {"label": "Alpha Team", "account": "acctA", "current": "v1"},
        "beta":       {"label": "Beta Team",  "account": "acctB", "current": "v1"},
        "empty-team": {"label": "Empty",      "account": "acctA", "current": "v1"},
    }
    (root / "teams.json").write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.setattr(team, "TEAMS_DIR", root)
    monkeypatch.setattr(team, "TEAMS_MANIFEST", root / "teams.json")
    team._reset_manifest_cache()
    team.set_active_team(None)
    return root


# ── resolve_team_spec ─────────────────────────────────────────────────────────

@pytest.mark.usefixtures("fixture_teams")
class TestResolveSpec:
    def test_plain_name_uses_current_version(self):
        assert team.resolve_team_spec("alpha") == ("alpha", "v1")

    def test_at_version_pins_explicitly(self):
        assert team.resolve_team_spec("alpha@v2") == ("alpha", "v2")
        assert team.resolve_team_spec("alpha@v10") == ("alpha", "v10")

    def test_whitespace_tolerant(self):
        assert team.resolve_team_spec("  alpha @ v2 ") == ("alpha", "v2")


# ── manifest readers ──────────────────────────────────────────────────────────

@pytest.mark.usefixtures("fixture_teams")
class TestManifest:
    def test_list_teams_sorted(self):
        assert team.list_teams() == ["alpha", "beta", "empty-team", "nomanifest"]

    def test_account_binding(self):
        assert team.team_account("alpha") == "acctA"
        assert team.team_account("beta") == "acctB"
        assert team.team_account("nomanifest") is None      # not in manifest

    def test_human_label_falls_back_to_slug(self):
        assert team.team_label("alpha") == "Alpha Team"
        assert team.team_label("nomanifest") == "nomanifest"

    def test_versions_natural_sorted(self):
        assert team.team_versions("alpha") == ["v1", "v2", "v10"]   # v10 after v2
        assert team.team_versions("beta") == ["v1"]
        assert team.team_versions("empty-team") == []

    def test_current_version_prefers_manifest(self):
        assert team.current_version("alpha") == "v1"

    def test_current_version_falls_back_to_highest_on_disk(self):
        assert team.current_version("nomanifest") == "v3"

    def test_unknown_team_is_empty(self):
        assert team.team_account("nope") is None
        assert team.team_versions("nope") == []
        assert team.current_version("nope") is None


# ── validate_team ─────────────────────────────────────────────────────────────

@pytest.mark.usefixtures("fixture_teams")
class TestValidate:
    def test_roster_validates(self):
        ok, msg = team.validate_team("alpha")
        assert ok and "1 mons" in msg

    def test_missing_version_file(self):
        ok, msg = team.validate_team("empty-team")        # manifest current v1, no file
        assert not ok

    def test_unknown_team(self):
        ok, msg = team.validate_team("no-such-team")
        assert not ok


# ── active-team selector ──────────────────────────────────────────────────────

@pytest.mark.usefixtures("fixture_teams")
class TestActiveTeam:
    def test_select_resolves_file_and_members(self):
        name, ver = team.set_active_team("alpha")
        assert (name, ver) == ("alpha", "v1")
        assert team.active_team() == "alpha"
        assert team.active_team_version() == "v1"
        assert team.active_team_file().name == "v1.txt"
        assert [m.name for m in team.get_team()] == ["Garchomp"]

    def test_explicit_version_arg_overrides_suffix(self):
        assert team.set_active_team("alpha@v1", version="v9") == ("alpha", "v9")

    def test_clear_reverts_to_baseline(self):
        team.set_active_team("alpha")
        team.set_active_team(None)
        assert team.active_team() is None
        assert team.active_team_file() is None
        assert len(team.get_team()) >= 1          # baseline team.txt still loads

    def test_switch_invalidates_cache(self):
        team.set_active_team("alpha")
        first = team.get_team()
        team.set_active_team(None)
        second = team.get_team()
        assert first is not second                # rebuilt, not the stale object


# ── live shipped teams (no fixture — guards the real rosters) ─────────────────

class TestRealTeams:
    """Smoke-test the actually-shipped teams *without hardcoding names*, so this
    stays green as teams are added / renamed / versioned."""

    def test_shipped_teams_with_a_roster_validate(self):
        checked = 0
        for name in team.list_teams():
            if team.team_versions(name):          # skip not-yet-filled slots
                ok, msg = team.validate_team(name)
                assert ok, f"{name}: {msg}"
                checked += 1
        assert checked >= 1                       # at least one real team exists


class TestMegaFormResolution:
    """``_mega_form_name`` must disambiguate two-mega species by the HELD STONE.

    The base species name alone can't tell Raichu-Mega-X from -Y (and the
    ``<name>-Mega`` convention yields a non-existent ``Raichu-Mega``), so the
    stone is the authoritative source.  Regression for the v4 Raichu add, where
    a held Raichunite Y was silently dropped (mega_name=None → played as base
    Raichu with Static instead of Mega-Y / No Guard)."""

    def test_dual_mega_stone_selects_correct_forme(self):
        assert team._mega_form_name("Raichu", "Raichunite Y") == "Raichu-Mega-Y"
        assert team._mega_form_name("Raichu", "Raichunite X") == "Raichu-Mega-X"

    def test_stone_overrides_name_default(self):
        # _MEGA_NAMES defaults Charizard to -Y; the held X stone must win.
        assert team._mega_form_name("Charizard", "Charizardite X") == "Charizard-Mega-X"

    def test_single_mega_still_resolves_without_item(self):
        # No item → fall back to the <name>-Mega convention (single-mega species).
        assert team._mega_form_name("Lopunny") == "Lopunny-Mega"


# ── ELO-log A/B tagging (main.EloTracker) ─────────────────────────────────────

class TestEloTagging:
    def _record(self, tmp, **kw):
        import main
        elo_path = Path(tmp) / "elo.json"
        with patch("main.ELO_LOG_PATH", elo_path):
            tracker = main.EloTracker()
            tracker.record("battle-x", "0.9.0", 1200, True, **kw)
            return json.loads(elo_path.read_text(encoding="utf-8"))

    def test_tagged_entry_carries_team_and_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._record(tmp, team="meta-team",
                                 team_version="v1", username="DongQuixote2")
            e = data[-1]
            assert e["team"] == "meta-team"
            assert e["team_version"] == "v1"
            assert e["username"] == "DongQuixote2"
            assert e["outcome"] == "win"

    def test_untagged_entry_has_no_team_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._record(tmp)
            e = data[-1]
            assert "team" not in e
            assert "team_version" not in e
            assert "username" not in e


# ── --max-games bounded run (main.ShowdownClient) ─────────────────────────────

class TestMaxGames:
    """The bot must stop ITSELF after --max-games completed games, so an
    unattended run can't keep laddering (the 0.9.0 single-game-run incident)."""

    def test_arg_parses(self):
        import main
        assert main._parse_args(["--max-games", "3"]).max_games == 3
        assert main._parse_args([]).max_games is None

    def _play(self, client, battle_id, won):
        asyncio.run(client._make_battle_end_handler(battle_id)(won))

    def test_stops_after_max_games(self):
        import main
        with tempfile.TemporaryDirectory() as tmp:
            with patch("main.ELO_LOG_PATH", Path(tmp) / "elo.json"):
                client = main.ShowdownClient(max_games=2)
                self._play(client, "b1", True)
                assert client._games_done == 1 and not client._stopping
                self._play(client, "b2", False)
                assert client._games_done == 2 and client._stopping   # self-terminated

    def test_unbounded_never_stops(self):
        import main
        with tempfile.TemporaryDirectory() as tmp:
            with patch("main.ELO_LOG_PATH", Path(tmp) / "elo.json"):
                client = main.ShowdownClient(max_games=None)
                for i in range(5):
                    self._play(client, f"b{i}", True)
                assert client._games_done == 5 and not client._stopping


# ── named-team login-failure abort (no guest fallback) ────────────────────────

class TestLoginFallback:
    """Fix: a named-team run must ABORT on login failure (a wrong password would
    otherwise guest-play and mis-tag the data — the off-meta incident).  The
    baseline (no named team) keeps the legacy guest fallback."""

    def _client(self):
        import main
        client = main.ShowdownClient()
        client.ws = AsyncMock()                 # so shutdown()'s ws.close() works
        client._login = AsyncMock(return_value=False)   # simulate a bad password
        client._queue_search = AsyncMock()
        return client

    def test_named_team_login_failure_aborts(self, fixture_teams):
        team.set_active_team("alpha")
        with tempfile.TemporaryDirectory() as tmp, \
                patch("main.ELO_LOG_PATH", Path(tmp) / "e.json"), \
                patch("main.USERNAME", "u"), patch("main.PASSWORD", "p"):
            client = self._client()
            asyncio.run(client._handle_global("|challstr|abc|def"))
            assert client._stopping is True             # shut itself down
            client._queue_search.assert_not_called()    # did NOT guest-search

    def test_baseline_login_failure_falls_back_to_guest(self):
        team.set_active_team(None)
        with tempfile.TemporaryDirectory() as tmp, \
                patch("main.ELO_LOG_PATH", Path(tmp) / "e.json"), \
                patch("main.USERNAME", "u"), patch("main.PASSWORD", "p"):
            client = self._client()
            asyncio.run(client._handle_global("|challstr|abc|def"))
            assert client._stopping is False
            client._queue_search.assert_called_once()   # legacy guest fallback intact


# ── per-team scenario lead enumeration (Phase 2b) ─────────────────────────────

class TestScenarioAllPairsLeads:
    """The generic per-team lead enumeration: all C(n,2) pairs with mega-variant
    expansion (used to generate snapshots for any roster)."""

    class _M:                                   # minimal TeamMember stand-in
        def __init__(self, name, mega):
            self.name, self.mega_name = name, mega

    def test_no_stones_one_config_per_pair(self):
        from scenarios.turn1_openings import _all_pairs_leads
        leads = _all_pairs_leads([self._M("A", None), self._M("B", None), self._M("C", None)])
        assert sorted(leads) == sorted([("A", "B", None), ("A", "C", None), ("B", "C", None)])

    def test_one_stone_holder_is_the_mega(self):
        from scenarios.turn1_openings import _all_pairs_leads
        leads = _all_pairs_leads([self._M("A", None), self._M("B", "B-Mega"), self._M("C", None)])
        assert ("A", "B", "B") in leads          # B holds the only stone in A+B
        assert ("B", "C", "B") in leads
        assert ("A", "C", None) in leads
        assert len(leads) == 3

    def test_both_holders_emit_both_variants(self):
        from scenarios.turn1_openings import _all_pairs_leads
        leads = _all_pairs_leads([self._M("A", "A-Mega"), self._M("B", "B-Mega")])
        assert ("A", "B", "A") in leads and ("A", "B", "B") in leads
        assert len(leads) == 2
