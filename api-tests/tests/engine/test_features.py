"""Engine feature file management tests."""

import pytest

from config.constants import EnginePaths


@pytest.mark.engine
class TestFeatures:

    def test_list_features(self, engine):
        resp = engine.get(EnginePaths.FEATURES)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_and_delete_folder(self, engine):
        resp = engine.post(EnginePaths.FEATURE_FOLDER, json={"path": "test_folder_temp"})
        assert resp.status_code == 200

        del_resp = engine.delete(EnginePaths.FEATURE_FOLDER, json={"path": "test_folder_temp"})
        assert del_resp.status_code == 200

    @pytest.mark.negative
    def test_create_folder_empty_path(self, engine):
        resp = engine.post(EnginePaths.FEATURE_FOLDER, json={"path": ""})
        assert resp.status_code == 400

    def test_save_and_get_feature(self, engine):
        feature_name = "test_temp.feature"
        content = 'Feature: Test\n  Scenario: Hello\n    Given I am testing\n'

        save_resp = engine.put(
            EnginePaths.FEATURE_DETAIL.format(name=feature_name),
            json={"content": content},
        )
        assert save_resp.status_code == 200

        get_resp = engine.get(EnginePaths.FEATURE_DETAIL.format(name=feature_name))
        assert get_resp.status_code == 200
        assert "content" in get_resp.json()

        engine.delete(EnginePaths.FEATURE_DETAIL.format(name=feature_name))

    @pytest.mark.negative
    def test_get_nonexistent_feature(self, engine):
        resp = engine.get(EnginePaths.FEATURE_DETAIL.format(name="nonexistent.feature"))
        assert resp.status_code == 404
