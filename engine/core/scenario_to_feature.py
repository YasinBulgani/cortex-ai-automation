"""TSPM senaryolarını pytest-BDD `.feature` dosyasına dönüştürür.

Kullanım akışı:
    1. Backend TSPM, `/api/nexus/run` uçuna `mode=playwright` ile istek atar.
    2. `generate_feature_package(scenarios, ...)` çağrılır.
    3. Döndürülen `test_file` path'i `pytest` subprocess'ine verilir.
    4. Normal `/api/run` akışı (watchdog, Allure, SSE) devreye girer.

Çıktı dosyaları:
    engine/features/ai_generated/run_{run_id}.feature
    engine/tests/ai_generated/test_run_{run_id}.py   (pytest-bdd glue)

Temizlik: `cleanup_feature_package(run_id)` run bitince çağrılmalı.
"""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_logger = logging.getLogger(__name__)

# Dosya konumları — settings.BASE_DIR altında
_FEATURES_SUBDIR = Path("features") / "ai_generated"
_TESTS_SUBDIR = Path("tests") / "ai_generated"

_VALID_KEYWORDS = {"Given", "When", "Then", "And", "But"}
_KEYWORD_MAP_TR = {
    "verilen": "Given",
    "given": "Given",
    "eğer": "When",
    "egr": "When",
    "when": "When",
    "o zaman": "Then",
    "then": "Then",
    "ve": "And",
    "and": "And",
    "ama": "But",
    "but": "But",
}


@dataclass(frozen=True)
class FeaturePackage:
    """Üretilen feature + test glue dosyalarının path'leri."""

    run_id: str
    feature_file: Path
    test_file: Path


def _normalize_keyword(raw: str | None) -> str:
    """`given`/`when`/`then` + Türkçe varyantları → Gherkin keyword'üne normalize."""
    if not raw:
        return "Given"
    low = raw.strip().lower().rstrip(":")
    if low in _KEYWORD_MAP_TR:
        return _KEYWORD_MAP_TR[low]
    capitalized = raw.strip().capitalize().rstrip(":")
    return capitalized if capitalized in _VALID_KEYWORDS else "Given"


def _sanitize_title(title: str) -> str:
    """Gherkin scenario başlığına uygun olmayan karakterleri temizler."""
    cleaned = re.sub(r"[\r\n]+", " ", title or "").strip()
    return cleaned or "Untitled Scenario"


def _format_step(step: dict, default_kw: str = "Given") -> str:
    """Tek bir step objesini Gherkin satırına çevirir.

    Beklenen step şeması (esnek):
        { "keyword": "Given"|"When"|"Then"|"And"|"But"|None,
          "text":    "kullanıcı ana sayfadadır" }
    """
    kw = _normalize_keyword(step.get("keyword") or default_kw)
    text = (step.get("text") or "").strip()
    if not text:
        return ""
    # Birden fazla satır içeren step metni → pytest-bdd'yi şaşırtır, tek satıra sıkıştır
    text = re.sub(r"[\r\n]+", " ", text)
    return f"    {kw} {text}"


def _build_feature_body(scenarios: Iterable[dict]) -> str:
    """Senaryolar listesini tek bir `.feature` dosyası gövdesine çevirir."""
    lines: list[str] = [
        "# Bu dosya TSPM tarafından otomatik üretildi — elle düzenlemeyin.",
        "Feature: TSPM dinamik koşum",
        "",
    ]
    for sc in scenarios:
        title = _sanitize_title(sc.get("title", "Scenario"))
        lines.append(f"  Scenario: {title}")
        steps = sc.get("steps") or []
        if not steps:
            lines.append("    Given bu senaryoda adım bulunmuyor")
            lines.append("")
            continue
        # İlk step Given, sonrakiler "And" olabilir
        last_kw: str | None = None
        for idx, st in enumerate(steps):
            current_kw = _normalize_keyword(st.get("keyword"))
            # Ardışık aynı keyword'ler "And" ile kısaltılır (okunurluk)
            if idx > 0 and current_kw == last_kw and current_kw in {"Given", "When", "Then"}:
                st = {**st, "keyword": "And"}
            rendered = _format_step(st, default_kw="Given" if idx == 0 else "And")
            if rendered:
                lines.append(rendered)
            last_kw = current_kw
        lines.append("")
    return "\n".join(lines)


def _build_glue_body(feature_relative_path: str, step_modules: list[str]) -> str:
    """pytest-bdd glue dosyası — scenarios() + tüm step modül importları."""
    lines: list[str] = [
        "# Bu dosya TSPM tarafından otomatik üretildi — elle düzenlemeyin.",
        "from pytest_bdd import scenarios",
        "",
    ]
    for mod in step_modules:
        lines.append(f"from steps.{mod} import *  # noqa: F401,F403")
    lines.append("")
    lines.append(f'scenarios("../../{feature_relative_path}")')
    lines.append("")
    return "\n".join(lines)


def _discover_step_modules(base_dir: Path) -> list[str]:
    """engine/steps/ altındaki tüm step modüllerini keşfet."""
    steps_dir = base_dir / "steps"
    if not steps_dir.exists():
        return []
    modules: list[str] = []
    for f in sorted(steps_dir.glob("*.py")):
        if f.name.startswith("_") or f.name in {"__init__.py", "conftest.py"}:
            continue
        modules.append(f.stem)
    return modules


def generate_feature_package(
    base_dir: Path,
    run_id: str,
    scenarios: list[dict],
) -> FeaturePackage:
    """Senaryolar için `.feature` + glue `.py` dosyalarını yazar.

    Args:
        base_dir: engine kök dizini (settings.BASE_DIR).
        run_id:   Benzersiz koşum ID'si — dosya isminde kullanılır.
        scenarios: TSPM'den gelen senaryo listesi.

    Returns:
        FeaturePackage: feature ve test dosyası yolları.
    """
    if not scenarios:
        raise ValueError("scenarios listesi boş — feature üretilemez")

    features_dir = base_dir / _FEATURES_SUBDIR
    tests_dir = base_dir / _TESTS_SUBDIR
    features_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    # pytest-bdd'nin `scenarios(...)` için `__init__.py` gerekli
    (tests_dir / "__init__.py").touch(exist_ok=True)

    feature_name = f"run_{run_id}.feature"
    test_name = f"test_run_{run_id}.py"

    feature_path = features_dir / feature_name
    test_path = tests_dir / test_name

    feature_body = _build_feature_body(scenarios)
    feature_path.write_text(feature_body, encoding="utf-8")

    step_modules = _discover_step_modules(base_dir)
    glue_body = _build_glue_body(
        feature_relative_path=f"features/ai_generated/{feature_name}",
        step_modules=step_modules,
    )
    test_path.write_text(glue_body, encoding="utf-8")

    _logger.info(
        "Feature paketi üretildi: run_id=%s scenarios=%d steps=%d",
        run_id,
        len(scenarios),
        sum(len(s.get("steps") or []) for s in scenarios),
    )

    return FeaturePackage(run_id=run_id, feature_file=feature_path, test_file=test_path)


def cleanup_feature_package(base_dir: Path, run_id: str) -> None:
    """Üretilen dosyaları siler — disk kirliliğini önler."""
    features_dir = base_dir / _FEATURES_SUBDIR
    tests_dir = base_dir / _TESTS_SUBDIR
    for path in (
        features_dir / f"run_{run_id}.feature",
        tests_dir / f"test_run_{run_id}.py",
    ):
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            _logger.warning("cleanup hatası %s: %s", path, exc)


def cleanup_all_generated(base_dir: Path, older_than_seconds: int = 3600) -> int:
    """Belirli bir yaştan eski tüm auto-generated dosyaları siler.

    Uzun süredir koşmayan tortuları temizler.
    Returns: silinen dosya sayısı.
    """
    import time

    now = time.time()
    deleted = 0
    for subdir in (_FEATURES_SUBDIR, _TESTS_SUBDIR):
        full = base_dir / subdir
        if not full.exists():
            continue
        for path in full.glob("*"):
            if path.name in {"__init__.py"}:
                continue
            try:
                if now - path.stat().st_mtime > older_than_seconds:
                    path.unlink(missing_ok=True)
                    deleted += 1
            except OSError:
                continue
    return deleted
