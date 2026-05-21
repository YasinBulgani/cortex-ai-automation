"""
Unit tests for core.data_reader — Domain/Environment Test Data Reader
"""
import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.data_reader import DataReader


@pytest.fixture(autouse=True)
def clean_data():
    DataReader.clear()
    yield
    DataReader.clear()


@pytest.fixture
def data_dir(tmp_path):
    """Gecici dizinde ornek test data JSON dosyalari olusturur."""
    domain_data = {
        "username": "admin@example.com",
        "password": "admin123",
        "expectedName": "Admin Kullanici",
        "baseUrl": "http://localhost:3000",
    }
    (tmp_path / "default-test-data.json").write_text(
        json.dumps(domain_data), encoding="utf-8"
    )

    prod_data = {
        "username": "admin@prod.com",
        "password": "prodpass",
        "baseUrl": "https://prod.example.com",
    }
    (tmp_path / "default-prod-data.json").write_text(
        json.dumps(prod_data), encoding="utf-8"
    )

    common_data = {
        "locale": "tr-TR",
        "timeout": "30000",
    }
    (tmp_path / "common-test-data.json").write_text(
        json.dumps(common_data), encoding="utf-8"
    )

    girit_data = {
        "username": "girit@test.com",
        "password": "giritpass",
    }
    (tmp_path / "girit-test-data.json").write_text(
        json.dumps(girit_data), encoding="utf-8"
    )
    return tmp_path


class TestLoad:
    def test_load_domain_data(self, data_dir):
        result = DataReader.load("default", "test", data_dir)
        assert result["username"] == "admin@example.com"
        assert result["password"] == "admin123"

    def test_load_merges_common(self, data_dir):
        result = DataReader.load("default", "test", data_dir)
        assert result["locale"] == "tr-TR"
        assert result["timeout"] == "30000"

    def test_load_prod_data(self, data_dir):
        result = DataReader.load("default", "prod", data_dir)
        assert result["username"] == "admin@prod.com"

    def test_load_different_domain(self, data_dir):
        result = DataReader.load("girit", "test", data_dir)
        assert result["username"] == "girit@test.com"

    def test_load_nonexistent_domain(self, data_dir):
        result = DataReader.load("nonexistent", "test", data_dir)
        assert "locale" in result  # common dosyasini yukler

    def test_reload_changes_data(self, data_dir):
        DataReader.load("default", "test", data_dir)
        assert DataReader.get("username") == "admin@example.com"
        DataReader.reload("girit", "test")
        DataReader.configure(data_dir)
        DataReader.load("girit", "test", data_dir)
        assert DataReader.get("username") == "girit@test.com"


class TestGet:
    def test_get_existing_key(self, data_dir):
        DataReader.load("default", "test", data_dir)
        assert DataReader.get("username") == "admin@example.com"

    def test_get_missing_key_returns_default(self, data_dir):
        DataReader.load("default", "test", data_dir)
        assert DataReader.get("nonexistent") == ""
        assert DataReader.get("nonexistent", "fallback") == "fallback"

    def test_get_required_raises(self, data_dir):
        DataReader.load("default", "test", data_dir)
        with pytest.raises(KeyError):
            DataReader.get_required("nonexistent")

    def test_get_required_returns_value(self, data_dir):
        DataReader.load("default", "test", data_dir)
        assert DataReader.get_required("username") == "admin@example.com"

    def test_has(self, data_dir):
        DataReader.load("default", "test", data_dir)
        assert DataReader.has("username") is True
        assert DataReader.has("nonexistent") is False


class TestRenderValue:
    def test_render_at_syntax(self, data_dir):
        DataReader.load("default", "test", data_dir)
        result = DataReader.render_value("Kullanici @username ile giris yapar")
        assert result == "Kullanici admin@example.com ile giris yapar"

    def test_render_brace_syntax(self, data_dir):
        DataReader.load("default", "test", data_dir)
        result = DataReader.render_value("Kullanici {username} ile giris yapar")
        assert result == "Kullanici admin@example.com ile giris yapar"

    def test_render_mixed_syntax(self, data_dir):
        DataReader.load("default", "test", data_dir)
        result = DataReader.render_value("@username sifre: {password}")
        assert result == "admin@example.com sifre: admin123"

    def test_render_missing_key_unchanged(self, data_dir):
        DataReader.load("default", "test", data_dir)
        result = DataReader.render_value("@nonexistent ile {missing}")
        assert result == "@nonexistent ile {missing}"

    def test_render_non_string_passthrough(self, data_dir):
        DataReader.load("default", "test", data_dir)
        assert DataReader.render_value(42) == 42
        assert DataReader.render_value(None) is None


class TestMetadata:
    def test_current_domain(self, data_dir):
        DataReader.load("girit", "test", data_dir)
        assert DataReader.current_domain() == "girit"

    def test_current_env(self, data_dir):
        DataReader.load("default", "prod", data_dir)
        assert DataReader.current_env() == "prod"

    def test_all_returns_copy(self, data_dir):
        DataReader.load("default", "test", data_dir)
        all_data = DataReader.all()
        assert isinstance(all_data, dict)
        assert "username" in all_data
        all_data["new_key"] = "test"
        assert not DataReader.has("new_key")
