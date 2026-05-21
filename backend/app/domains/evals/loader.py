"""YAML suite yükleyici + validator.

Tasarım:
    * ``suites/`` dizinini default arama yolu olarak kullanır; harici bir
      path geçilirse ona fallback.
    * YAML parse hatalarını meaningful ``ValueError`` ile yükseltir.
    * Aynı ``Suite.name`` birden fazla dosyada varsa ValueError.

PyYAML opsiyonel bağımlılık. Kurulu değilse sadece eval özelliği kırılır;
backend'in geri kalanı etkilenmez (``requirements.txt`` zaten pyyaml içerir).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .schemas import Suite

logger = logging.getLogger(__name__)

_DEFAULT_SUITES_DIR = Path(__file__).resolve().parent / "suites"


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - deps
        raise RuntimeError("pyyaml kurulu değil — eval suite yüklenemiyor") from exc
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Suite dosyası okunamadı: {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Suite YAML parse hatası ({path}): {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Suite YAML kökü bir mapping olmalı: {path}")
    return data


def load_suite_file(path: Path) -> Suite:
    data = _load_yaml(path)
    return Suite.from_dict(data)


def load_suites(
    directory: Optional[Path] = None,
    *,
    names: Optional[Iterable[str]] = None,
) -> List[Suite]:
    """Bir dizinden ``*.yaml`` / ``*.yml`` suite'leri yükler.

    Args:
        directory: Suite klasörü. ``None`` → ``backend/app/domains/evals/suites``.
        names: Sadece bu isimlerdeki suite'leri döndür (opsiyonel filtre).

    Raises:
        ValueError: Aynı ``Suite.name`` birden fazla dosyada bulunursa.
    """
    base = directory or _DEFAULT_SUITES_DIR
    if not base.exists() or not base.is_dir():
        logger.warning("Eval suites dizini bulunamadı: %s", base)
        return []

    suites: Dict[str, Suite] = {}
    name_filter = set(names) if names else None

    for file in sorted(base.iterdir()):
        if not file.is_file():
            continue
        if file.suffix.lower() not in {".yaml", ".yml"}:
            continue
        try:
            suite = load_suite_file(file)
        except ValueError as exc:
            logger.error("Suite yüklenemedi (%s): %s", file.name, exc)
            raise
        if name_filter and suite.name not in name_filter:
            continue
        if suite.name in suites:
            raise ValueError(
                f"Duplicate suite adı: '{suite.name}' "
                f"(hem {suites[suite.name].description or '?'} hem {file.name})"
            )
        suites[suite.name] = suite

    return list(suites.values())


def default_suites_dir() -> Path:
    return _DEFAULT_SUITES_DIR
