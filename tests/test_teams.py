"""test_teams.py — Named-team infrastructure (0.9.0).

Covers team.py's manifest/version resolution, the active-team selector (and its
baseline fallback), team validation, and the ELO-log A/B tagging in
main.EloTracker.  Recorder path-nesting is covered in test_recorder.py
(TestNamedTeamPath).
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import team


# The active-team selector mutates process-global state (team._ACTIVE_NAME and
# the cached singleton) that other test modules rely on resolving to the
# team.txt baseline.  Reset after every test here so nothing leaks out.
@pytest.fixture(autouse=True)
def _reset_active_team():
    yield
    team.set_active_team(None)
    team.get_team(reload=True)


# ── resolve_team_spec ─────────────────────────────────────────────────────────

class TestResolveSpec:
    def test_plain_name_uses_current_version(self):
        assert team.resolve_team_spec("meta-team") == ("meta-team", "v1")

    def test_at_version_pins_explicitly(self):
        assert team.resolve_team_spec("meta-team@v2") == ("meta-team", "v2")

    def test_whitespace_tolerant(self):
        assert team.resolve_team_spec("  meta-team @ v3 ".replace(" @ ", "@").strip()) \
            == ("meta-team", "v3")


# ── manifest readers ──────────────────────────────────────────────────────────

class TestManifest:
    def test_list_teams(self):
        teams = team.list_teams()
        assert "meta-team" in teams
        assert "off-meta-team" in teams

    def test_account_binding(self):
        assert team.team_account("meta-team") == "main"
        assert team.team_account("off-meta-team") == "alt"

    def test_human_label(self):
        assert team.team_label("meta-team") == "meta team"
        assert team.team_label("off-meta-team") == "off-meta team"

    def test_versions_on_disk(self):
        assert team.team_versions("meta-team") == ["v1"]
        assert team.team_versions("off-meta-team") == []     # no v*.txt yet

    def test_current_version(self):
        assert team.current_version("meta-team") == "v1"

    def test_unknown_team_is_empty(self):
        assert team.team_account("nope") is None
        assert team.team_versions("nope") == []
        assert team.current_version("nope") is None


# ── validate_team ─────────────────────────────────────────────────────────────

class TestValidate:
    def test_meta_team_validates(self):
        ok, msg = team.validate_team("meta-team")
        assert ok
        assert "6" in msg          # 6 mons OK

    def test_off_meta_missing_roster(self):
        ok, msg = team.validate_team("off-meta-team")
        assert not ok              # v1.txt not added yet


# ── active-team selector ──────────────────────────────────────────────────────

class TestActiveTeam:
    def test_select_resolves_file_and_members(self):
        name, ver = team.set_active_team("meta-team")
        assert (name, ver) == ("meta-team", "v1")
        assert team.active_team() == "meta-team"
        assert team.active_team_version() == "v1"
        assert team.active_team_file().name == "v1.txt"
        members = [m.name for m in team.get_team()]
        assert "Garchomp" in members and len(members) == 6

    def test_explicit_version_arg_overrides_suffix(self):
        name, ver = team.set_active_team("meta-team@v1", version="v9")
        assert (name, ver) == ("meta-team", "v9")

    def test_clear_reverts_to_baseline(self):
        team.set_active_team("meta-team")
        team.set_active_team(None)
        assert team.active_team() is None
        assert team.active_team_file() is None
        # baseline (team.txt) still loads a full team
        assert len(team.get_team()) == 6

    def test_switch_invalidates_cache(self):
        team.set_active_team("meta-team")
        first = team.get_team()
        team.set_active_team(None)
        second = team.get_team()
        assert first is not second     # rebuilt, not the stale cached object


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
