"""test_our_leads.py — OUR lead-pair performance stats + the smoothed prior.

The pair prior must be neutral for unseen pairs, move meaningfully only with
real sample size, and never leak across team versions.
"""
from unittest.mock import patch

import pytest

import data.our_leads as OL


class TestOurLeads:
    def _isolate(self, monkeypatch, tmp_path):
        monkeypatch.setattr(OL, "_STATS_FILE", tmp_path / "our_lead_stats.json")

    def test_record_and_read_back(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        OL.record_result("t@v1", "Aerodactyl", "Basculegion", True)
        OL.record_result("t@v1", "Basculegion", "Aerodactyl", False)
        assert OL.pair_record("t@v1", "Aerodactyl", "Basculegion") == (1, 2)

    def test_pair_key_is_order_and_mega_independent(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        OL.record_result("t@v1", "Aerodactyl-Mega", "Basculegion", True)
        assert OL.pair_record("t@v1", "Basculegion", "Aerodactyl") == (1, 1)

    def test_unseen_pair_is_neutral(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        assert OL.pair_factor("t@v1", "A", "B") == 1.0

    def test_smoothing_magnitudes(self, monkeypatch, tmp_path):
        """10-1 → ~1.43 boost; 18-34 → ~0.74 penalty; 50% stays ~neutral."""
        self._isolate(monkeypatch, tmp_path)
        for w, g, expect in ((10, 11, 1.43), (18, 52, 0.74), (139, 281, 0.99)):
            OL.reset()
            for i in range(g):
                OL.record_result("t@v1", "A", "B", i < w)
            assert OL.pair_factor("t@v1", "A", "B") == pytest.approx(expect, abs=0.01)

    def test_no_cross_team_leakage(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        OL.record_result("t@v1", "A", "B", False)
        assert OL.pair_factor("t@v2", "A", "B") == 1.0
