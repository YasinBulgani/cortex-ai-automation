"""Flaky Detector unit tests."""
import json

import pytest

from services.flaky_detector import FlakyDetector, FlakyTestInfo

@pytest.fixture
def detector(tmp_path):
    history = {
        "flaky_test": [{"status": s} for s in ["passed", "failed"] * 10],
        "stable_test": [{"status": "passed"}] * 20,
        "broken_test": [{"status": s, "error": "timeout"} for s in ["passed"] * 15 + ["failed"] * 5],
        "short_test": [{"status": "passed"}] * 3,
    }
    hist_file = tmp_path / "test-history.json"
    hist_file.write_text(json.dumps(history))
    return FlakyDetector(history_path=str(hist_file))

class TestFlakyAnalysis:
    def test_detects_flaky(self, detector):
        results = detector.analyze_all()
        flaky = next(r for r in results if r.test_id == "flaky_test")
        assert flaky.recommendation == "quarantine"
        assert flaky.flaky_score >= 0.3

    def test_stable_test(self, detector):
        results = detector.analyze_all()
        stable = next(r for r in results if r.test_id == "stable_test")
        assert stable.recommendation == "stable"
        assert stable.flaky_score == 0.0

    def test_skips_short_history(self, detector):
        results = detector.analyze_all()
        ids = [r.test_id for r in results]
        assert "short_test" not in ids

    def test_quarantine_list(self, detector):
        q = detector.get_quarantine_list()
        assert "flaky_test" in q
        assert "stable_test" not in q

    def test_deselect_args(self, detector):
        args = detector.generate_pytest_deselect_args()
        assert any("flaky_test" in a for a in args)

    def test_to_dict(self, detector):
        results = detector.analyze_all()
        for r in results:
            d = r.to_dict()
            assert "test_id" in d
            assert "flaky_score" in d

    def test_save_report(self, detector, tmp_path):
        detector.save_report(output_path=str(tmp_path / "flaky.json"))
        assert (tmp_path / "flaky.json").exists()

    def test_empty_history(self, tmp_path):
        d = FlakyDetector(history_path=str(tmp_path / "empty.json"))
        assert d.analyze_all() == []
