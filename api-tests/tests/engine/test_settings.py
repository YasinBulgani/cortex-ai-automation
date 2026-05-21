"""Engine settings and utility endpoint tests."""

import pytest

from config.constants import EnginePaths


@pytest.mark.engine
class TestSettings:

    def test_get_settings(self, engine):
        resp = engine.get(EnginePaths.SETTINGS)
        assert resp.status_code == 200
        data = resp.json()
        assert "BASE_URL" in data
        assert "BROWSER" in data
        assert "has_api_key" in data

    def test_get_stats(self, engine):
        resp = engine.get(EnginePaths.STATS)
        assert resp.status_code == 200
        data = resp.json()
        assert "totals" in data

    def test_comprehensive_report(self, engine):
        resp = engine.get(EnginePaths.REPORTS)
        assert resp.status_code == 200
