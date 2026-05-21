"""Disk YAML'lerini in-memory cache'e yükleyen servis.

packages/dsl/catalog/*.yaml -> list[DslAction]

Uygulama başlangıcında bir kez okur, istek geldikçe cache'ten sunar.
POST /reload endpoint'i veya CatalogCache.reload() ile yeniden yüklenir.
"""
from __future__ import annotations

import logging
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml  # type: ignore[import-untyped]

from app.domains.dsl.schemas import DslAction, DslStats

logger = logging.getLogger(__name__)

# Proje kökü: backend/app/domains/dsl/loader.py -> 4 seviye yukarı
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_CATALOG_DIR = _PROJECT_ROOT / "packages" / "dsl" / "catalog"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CatalogCache:
    """Thread-safe in-memory katalog cache'i."""

    def __init__(self, catalog_dir: Path = _CATALOG_DIR) -> None:
        self._catalog_dir = catalog_dir
        self._lock = threading.RLock()
        self._actions: List[DslAction] = []
        self._by_id: Dict[str, DslAction] = {}
        self._loaded_at: Optional[str] = None

    # ── Yükleme ──────────────────────────────────────────────────────────
    def load(self) -> int:
        """Diskten YAML'leri okuyup cache'i doldurur. Yüklenen toplam action sayısını döner."""
        with self._lock:
            actions: List[DslAction] = []
            if not self._catalog_dir.exists():
                logger.warning("DSL katalog dizini yok: %s", self._catalog_dir)
                self._actions = []
                self._by_id = {}
                self._loaded_at = _iso_now()
                return 0

            for yaml_path in sorted(self._catalog_dir.glob("*.yaml")):
                try:
                    with yaml_path.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                except (OSError, yaml.YAMLError) as exc:  # pragma: no cover
                    logger.error("DSL katalog okunamadı %s: %s", yaml_path.name, exc)
                    continue

                raw_actions = data.get("actions") or []
                for raw in raw_actions:
                    if not isinstance(raw, dict):
                        continue
                    raw.setdefault("source_yaml", yaml_path.name)
                    try:
                        actions.append(DslAction.model_validate(raw))
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "DSL action parse hatası (%s#%s): %s",
                            yaml_path.name,
                            raw.get("id", "?"),
                            exc,
                        )

            self._actions = actions
            self._by_id = {a.id: a for a in actions}
            self._loaded_at = _iso_now()
            logger.info("DSL katalog yüklendi: %d cümlecik", len(actions))
            return len(actions)

    def ensure_loaded(self) -> None:
        if self._loaded_at is None:
            self.load()

    # ── Okuma API'si ─────────────────────────────────────────────────────
    @property
    def loaded_at(self) -> Optional[str]:
        return self._loaded_at

    def all(self) -> List[DslAction]:
        self.ensure_loaded()
        return list(self._actions)

    def get(self, action_id: str) -> Optional[DslAction]:
        self.ensure_loaded()
        return self._by_id.get(action_id)

    def filter(
        self,
        category: Optional[str] = None,
        lang: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[DslAction]:
        self.ensure_loaded()
        out: List[DslAction] = []
        for a in self._actions:
            if category:
                if not (a.category == category or a.category.startswith(category + ".")):
                    continue
            if lang and lang not in (a.aliases or {}):
                continue
            if tag and tag not in (a.tags or []):
                continue
            out.append(a)
        return out

    def search(self, query: str, lang: Optional[str] = None) -> List[tuple[DslAction, str, str]]:
        """Query'yi alias'larda ve description'da arar. (action, lang, alias) üçlüleri döner."""
        self.ensure_loaded()
        q = query.lower().strip()
        if not q:
            return []
        hits: List[tuple[DslAction, str, str]] = []
        for a in self._actions:
            aliases = a.aliases or {}
            langs = [lang] if lang else list(aliases.keys())
            matched = False
            for ln in langs:
                for alias in aliases.get(ln, []):
                    if q in alias.lower():
                        hits.append((a, ln, alias))
                        matched = True
                        break
                if matched:
                    break
            if not matched and not lang:
                if q in (a.id or "").lower() or q in (a.description or "").lower():
                    hits.append((a, "meta", a.description or a.id))
        return hits

    # ── Agregasyonlar ────────────────────────────────────────────────────
    def stats(self) -> DslStats:
        self.ensure_loaded()
        total = len(self._actions)
        top = Counter(a.category.split(".")[0] for a in self._actions if a.category)
        full = Counter(a.category for a in self._actions if a.category)
        impls = Counter(
            lang for a in self._actions for lang in (a.implementations or {}).keys()
        )
        sources = Counter(a.source_yaml or "?" for a in self._actions)
        tag_ctr: Counter[str] = Counter()
        for a in self._actions:
            for t in a.tags or []:
                tag_ctr[t] += 1

        tr = sum(1 for a in self._actions if "tr" in (a.aliases or {}))
        en = sum(1 for a in self._actions if "en" in (a.aliases or {}))
        both = sum(1 for a in self._actions if {"tr", "en"}.issubset((a.aliases or {}).keys()))

        _step_prefixes: dict[str, list[str]] = {
            "given": ["(Ön koşul)", "(On kosul)", "Given "],
            "when":  ["Eylem:", "When ", "Action:"],
            "then":  ["Doğrulama:", "Dogrulama:", "Then ", "Assert:"],
        }
        by_step: dict[str, int] = {"given": 0, "when": 0, "then": 0, "unknown": 0}
        for a in self._actions:
            desc = a.description or ""
            matched = False
            for st, prefixes in _step_prefixes.items():
                if any(desc.startswith(p) for p in prefixes):
                    by_step[st] += 1
                    matched = True
                    break
            if not matched:
                by_step["unknown"] += 1

        return DslStats(
            total=total,
            unique_ids=len(self._by_id),
            by_top_category=dict(top),
            by_full_category=dict(full),
            by_implementation=dict(impls),
            by_source_file=dict(sources),
            by_step_type=by_step,
            top_tags=[{"tag": k, "count": v} for k, v in tag_ctr.most_common(20)],
            aliases={"tr": tr, "en": en, "both": both},
            loaded_at=self._loaded_at,
        )


# Modül düzeyinde tek singleton — uygulama ömrü boyunca paylaşılır.
catalog_cache = CatalogCache()
