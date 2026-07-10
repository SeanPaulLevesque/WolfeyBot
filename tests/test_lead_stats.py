"""test_lead_stats.py — opponent lead-frequency + co-occurrence stats and the
co-occurrence-aware lead-pair predictor.

The predictor must not pair two independently-popular leads (Whimsicott +
Farigiraf) that are rarely led *together*; it prefers the duo actually co-led.
"""
from unittest.mock import patch

import pytest

import data.lead_stats as L


# ── Recording: singles + pairs ────────────────────────────────────────────────

class TestRecordLeads:
    def _isolate(self, monkeypatch, tmp_path):
        monkeypatch.setattr(L, "_STATS_FILE", tmp_path / "lead_stats.json")

    def test_records_singles_and_pair(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        L.reset()
        L.record_leads(["Whimsicott", "Garchomp"])
        assert L.total_battles() == 1
        assert L.lead_frequency("Whimsicott") == 1
        assert L.lead_frequency("Garchomp") == 1
        assert L.lead_pair_frequency("Whimsicott", "Garchomp") == 1

    def test_pair_key_order_independent(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        L.reset()
        L.record_leads(["Garchomp", "Whimsicott"])   # reversed order
        assert L.lead_pair_frequency("Whimsicott", "Garchomp") == 1
        assert L.lead_pair_frequency("Garchomp", "Whimsicott") == 1

    def test_accumulates_across_games(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        L.reset()
        for _ in range(3):
            L.record_leads(["Whimsicott", "Garchomp"])
        L.record_leads(["Whimsicott", "Staraptor"])
        assert L.lead_pair_frequency("Whimsicott", "Garchomp") == 3
        assert L.lead_pair_frequency("Whimsicott", "Staraptor") == 1

    def test_blank_leads_skipped(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        L.reset()
        L.record_leads(["Garchomp", ""])     # one blank slot
        assert L.lead_frequency("Garchomp") == 1
        # no pair recorded from a single real lead
        assert L.lead_pair_frequency("Garchomp", "") == 0


# ── Prediction: co-occurrence-aware with graceful fallback ────────────────────

class TestPredictPair:
    @staticmethod
    def _patch(singles, pairs):
        """pairs keyed by L.pair_key(a, b)."""
        return (
            patch("data.lead_stats.lead_frequency",
                  side_effect=lambda s: singles.get(s, 0)),
            patch("data.lead_stats.lead_pair_frequency",
                  side_effect=lambda a, b: pairs.get(L.pair_key(a, b), 0)),
        )

    def test_prefers_co_led_pair_over_two_popular_singles(self):
        """The headline case: Whimsicott (top) + Farigiraf (also top) are co-led
        rarely; Whimsicott + Garchomp often → predict the latter."""
        singles = {"Whimsicott": 428, "Farigiraf": 361, "Garchomp": 100}
        pairs = {L.pair_key("Whimsicott", "Garchomp"): 62,
                 L.pair_key("Whimsicott", "Farigiraf"): 5}
        p1, p2 = self._patch(singles, pairs)
        with p1, p2:
            assert L.predict_pair(["Whimsicott", "Farigiraf", "Garchomp"]) \
                == ["Whimsicott", "Garchomp"]

    def test_below_threshold_anchors_on_top_single_and_real_partner(self):
        """No pair reaches PAIR_MIN_SUPPORT, but the top single has a real (freq 1)
        partner → anchor on it instead of blindly taking the #2 single."""
        singles = {"A": 100, "B": 50, "C": 10}   # top-2 singles would be A, B
        pairs = {L.pair_key("A", "C"): 1}          # A actually co-led only with C
        p1, p2 = self._patch(singles, pairs)
        with p1, p2:
            assert L.predict_pair(["A", "B", "C"], pair_min=2) == ["A", "C"]

    def test_no_pair_evidence_falls_back_to_top_two_singles(self):
        singles = {"A": 100, "B": 50, "C": 10}
        p1, p2 = self._patch(singles, {})          # no co-lead data at all
        with p1, p2:
            assert L.predict_pair(["A", "B", "C"]) == ["A", "B"]

    def test_threshold_met_exactly_predicts_pair(self):
        singles = {"A": 100, "B": 90, "C": 80}
        pairs = {L.pair_key("B", "C"): 2}          # exactly PAIR_MIN_SUPPORT
        p1, p2 = self._patch(singles, pairs)
        with p1, p2:
            assert L.predict_pair(["A", "B", "C"], pair_min=2) == ["B", "C"]

    def test_single_species_returned_as_is(self):
        with patch("data.lead_stats.lead_frequency", return_value=1):
            assert L.predict_pair(["OnlyOne"]) == ["OnlyOne"]


class TestPredictPairs:
    """Hedged prediction: top-K pairs weighted by co-lead evidence + a
    singles-shaped pseudo-count; weights sum to 1."""

    @staticmethod
    def _patch(singles, pairs):
        return (
            patch("data.lead_stats.lead_frequency",
                  side_effect=lambda s: singles.get(s, 0)),
            patch("data.lead_stats.ladder_lead_pct", return_value=0.0),
            patch("data.lead_stats.lead_pair_frequency",
                  side_effect=lambda a, b: pairs.get(L.pair_key(a, b), 0)),
        )

    def test_dominant_pair_data_dominates_weights(self):
        singles = {"Swampert": 100, "Pelipper": 120, "Archaludon": 60, "X": 10}
        pairs = {L.pair_key("Swampert", "Pelipper"): 51,
                 L.pair_key("Pelipper", "Archaludon"): 23}
        p1, p2, p3 = self._patch(singles, pairs)
        with p1, p2, p3:
            out = L.predict_pairs(["Swampert", "Pelipper", "Archaludon", "X"])
        assert sorted(out[0][0]) == ["Pelipper", "Swampert"]
        assert out[0][1] > 0.6                       # ~51/(51+23+eps)
        assert sum(w for _, w in out) == pytest.approx(1.0)
        assert len(out) == 3                          # default k

    def test_no_pair_data_falls_back_to_singles_shape(self):
        singles = {"A": 100, "B": 50, "C": 10, "D": 1}
        p1, p2, p3 = self._patch(singles, {})
        with p1, p2, p3:
            out = L.predict_pairs(["A", "B", "C", "D"])
        assert sorted(out[0][0]) == ["A", "B"]        # top singles product
        assert sum(w for _, w in out) == pytest.approx(1.0)

    def test_fewer_than_two_species(self):
        assert L.predict_pairs(["Solo"]) == []
