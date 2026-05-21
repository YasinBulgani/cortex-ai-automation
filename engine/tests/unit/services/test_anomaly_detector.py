"""Anomaly Detector unit tests."""
import json

import pytest

from services.anomaly_detector import AnomalyDetector, Anomaly

@pytest.fixture
def detector(tmp_path):
    return AnomalyDetector(history_path=str(tmp_path / "metrics.json"))

class TestAnomalyDetection:
    def test_no_anomaly_with_insufficient_history(self, detector):
        result = detector.analyze_test_run({"total": 50, "passed": 48, "failed": 2, "total_duration": 100})
        assert result == []

    def test_detects_anomaly_with_sufficient_history(self, detector):
        import random
        random.seed(42)
        for _ in range(10):
            detector.analyze_test_run({
                "total": 50, "passed": 48, "failed": random.randint(1, 3),
                "total_duration": 100 + random.randint(-10, 10), "avg_duration": 2.0,
            })
        anomalies = detector.analyze_test_run({
            "total": 50, "passed": 20, "failed": 30,
            "total_duration": 500, "avg_duration": 10.0,
        })
        assert len(anomalies) > 0
        assert all(isinstance(a, Anomaly) for a in anomalies)

    def test_anomaly_to_dict(self, detector):
        a = Anomaly("test_metric", 100.0, (10.0, 50.0), 4.5, "critical", "desc")
        d = a.to_dict()
        assert d["severity"] == "critical"
        assert d["z_score"] == 4.5

    def test_history_persistence(self, detector):
        detector.analyze_test_run({"total": 10, "passed": 9, "failed": 1, "total_duration": 30})
        assert len(detector.history) > 0

    def test_bad_path_no_crash(self, tmp_path):
        d = AnomalyDetector(history_path="/nonexistent/deep/path/metrics.json")
        d.analyze_test_run({"total": 10, "passed": 9, "failed": 1, "total_duration": 30})
