"""scenario_to_feature generator testleri.

TSPM senaryolarının Gherkin `.feature` ve pytest-bdd glue `.py`
dosyalarına doğru çevrildiğini doğrular.
"""

from __future__ import annotations

from pathlib import Path

from core.scenario_to_feature import (
    _build_feature_body,
    _build_glue_body,
    _normalize_keyword,
    cleanup_feature_package,
    generate_feature_package,
)


def test_normalize_keyword_handles_variants() -> None:
    assert _normalize_keyword("given") == "Given"
    assert _normalize_keyword("Given") == "Given"
    assert _normalize_keyword("verilen") == "Given"
    assert _normalize_keyword("Eğer") == "When"
    assert _normalize_keyword(None) == "Given"
    assert _normalize_keyword("") == "Given"
    # Bilinmeyen → default Given
    assert _normalize_keyword("xyz") == "Given"


def test_feature_body_preserves_title_and_steps() -> None:
    scenarios = [
        {
            "title": "Başarılı giriş",
            "steps": [
                {"keyword": "Given", "text": "kullanıcı ana sayfadadır"},
                {"keyword": "When", "text": 'kullanıcı "#email" kutusuna "u@x" yazar'},
                {"keyword": "Then", "text": 'URL "/home" içermelidir'},
            ],
        }
    ]
    body = _build_feature_body(scenarios)
    assert "Scenario: Başarılı giriş" in body
    assert "Given kullanıcı ana sayfadadır" in body
    assert "When kullanıcı" in body
    assert "Then URL" in body


def test_feature_body_uses_and_for_consecutive_same_keyword() -> None:
    scenarios = [
        {
            "title": "Çoklu adım",
            "steps": [
                {"keyword": "Given", "text": "adım 1"},
                {"keyword": "Given", "text": "adım 2"},
                {"keyword": "When", "text": "eylem"},
                {"keyword": "When", "text": "başka eylem"},
            ],
        }
    ]
    body = _build_feature_body(scenarios)
    # 2. Given → And, 2. When → And
    assert body.count("Given adım") == 1
    assert body.count("And adım 2") == 1
    assert body.count("And başka eylem") == 1


def test_feature_body_handles_empty_steps() -> None:
    body = _build_feature_body([{"title": "Boş", "steps": []}])
    assert "Scenario: Boş" in body
    assert "bu senaryoda adım bulunmuyor" in body


def test_glue_body_imports_all_step_modules() -> None:
    body = _build_glue_body(
        feature_relative_path="features/ai_generated/run_x.feature",
        step_modules=["common_steps", "bgts_login_steps"],
    )
    assert "from pytest_bdd import scenarios" in body
    assert "from steps.common_steps import *" in body
    assert "from steps.bgts_login_steps import *" in body
    assert 'scenarios("../../features/ai_generated/run_x.feature")' in body


def test_generate_and_cleanup_feature_package(tmp_path: Path) -> None:
    # Minimum steps/ dizini oluştur
    (tmp_path / "steps").mkdir()
    (tmp_path / "steps" / "common_steps.py").write_text("# dummy")

    scenarios = [
        {
            "id": "abc",
            "title": "Test",
            "steps": [{"keyword": "Given", "text": "adım"}],
        }
    ]
    pkg = generate_feature_package(
        base_dir=tmp_path,
        run_id="20260419_test",
        scenarios=scenarios,
    )

    assert pkg.feature_file.exists()
    assert pkg.test_file.exists()
    assert "Scenario: Test" in pkg.feature_file.read_text()
    assert "from steps.common_steps import *" in pkg.test_file.read_text()

    # Cleanup
    cleanup_feature_package(tmp_path, "20260419_test")
    assert not pkg.feature_file.exists()
    assert not pkg.test_file.exists()


def test_generate_raises_on_empty_scenarios(tmp_path: Path) -> None:
    import pytest
    with pytest.raises(ValueError):
        generate_feature_package(base_dir=tmp_path, run_id="x", scenarios=[])
