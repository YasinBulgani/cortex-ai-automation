"""YAML katalog -> pytest-bdd step registration.

Bu modül, ``packages/dsl/catalog/*.yaml`` altındaki cümlecikleri okuyup
her alias için bir pytest-bdd step (``@when``, ``@given``, ``@then``) kaydeder.

Strateji:
1. Katalog YAML'lerini yükle.
2. Her action için Python implementation referansını (module + function) çöz.
3. Her alias (TR + EN) için o fonksiyonu yeni bir pytest-bdd step olarak kaydet.

Böylece **tek bir implementation** Python'da yaşar, ama kullanıcı feature
dosyasında hem TR hem EN hem de birden çok alternatif yazım şeklini
kullanabilir — hepsi aynı fonksiyona resolve olur.

Avantaj: ``catalog/*.yaml`` güncellenince ekstra kod yazmadan yeni alias'lar
devreye girer.
"""
from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

import yaml  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_CATALOG_DIR = Path(__file__).resolve().parents[2] / "catalog"


@dataclass
class CatalogBinding:
    """Tek bir cümleciğin yüklenmiş hali (debug / inspect için)."""

    id: str
    category: str
    keyword: str  # given/when/then
    aliases_registered: List[str] = field(default_factory=list)
    impl_ref: Optional[str] = None  # "engine.steps.click_steps.step_click_element"
    skipped_reason: Optional[str] = None


def _detect_keyword(tags: List[str]) -> str:
    """Tag listesinden ``given``/``when``/``then`` çıkar. Yoksa ``when``."""
    for kw in ("given", "when", "then"):
        if kw in tags:
            return kw
    return "when"


def _resolve_impl(impl: dict) -> Optional[Callable]:
    """Implementation bloğundan gerçek Python callable'ı çöz."""
    module_path = impl.get("module")
    function_name = impl.get("function")
    source_file = impl.get("source_file", "")

    # Tercihen module.function ile
    if module_path and function_name:
        try:
            module = importlib.import_module(module_path)
            return getattr(module, function_name, None)
        except ImportError as exc:
            logger.debug("DSL: import başarısız %s: %s", module_path, exc)

    # Fallback: source_file + function_name ile
    if source_file and function_name:
        # engine/steps/click_steps.py -> engine.steps.click_steps
        dotted = source_file.replace("/", ".").removesuffix(".py")
        try:
            module = importlib.import_module(dotted)
            return getattr(module, function_name, None)
        except ImportError:
            pass

    return None


def load_catalog(catalog_dir: Path = _CATALOG_DIR) -> List[dict]:
    """Tüm YAML'leri düz bir action listesi olarak dön."""
    actions: List[dict] = []
    if not catalog_dir.is_dir():
        logger.warning("DSL: Katalog dizini yok: %s", catalog_dir)
        return actions
    for path in sorted(catalog_dir.glob("*.yaml")):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            logger.error("DSL: %s parse hatası: %s", path.name, exc)
            continue
        for a in data.get("actions") or []:
            if isinstance(a, dict):
                a.setdefault("_source_yaml", path.name)
                actions.append(a)
    return actions


def register_catalog(
    *,
    dry_run: bool = False,
    only_categories: Optional[List[str]] = None,
    skip_ids: Optional[List[str]] = None,
) -> List[CatalogBinding]:
    """Katalog YAML'lerini okuyup pytest-bdd step'leri olarak kaydeder.

    Dönen listede her cümlecik için bir ``CatalogBinding`` bulunur (debug amaçlı).

    Args:
        dry_run: True ise kayıt yapmaz sadece neyin olacağını döner.
        only_categories: Sadece bu üst kategorilerde (``ui``, ``api``...) olanları kaydet.
        skip_ids: Kaydetmemesi gereken id listesi (pilot migration'da kullanılır).
    """
    try:
        from pytest_bdd import given, parsers, then, when
    except ImportError:
        logger.warning("DSL: pytest-bdd yüklü değil, katalog kaydı atlandı.")
        return []

    keyword_decorators = {"given": given, "when": when, "then": then}

    bindings: List[CatalogBinding] = []
    skip_set = set(skip_ids or [])

    for action in load_catalog():
        aid = action.get("id") or "?"
        category = action.get("category") or ""
        top_cat = category.split(".")[0]

        binding = CatalogBinding(
            id=aid,
            category=category,
            keyword=_detect_keyword(action.get("tags") or []),
        )

        if aid in skip_set:
            binding.skipped_reason = "skip_ids"
            bindings.append(binding)
            continue
        if only_categories and top_cat not in only_categories:
            binding.skipped_reason = "not in only_categories"
            bindings.append(binding)
            continue

        impls = action.get("implementations") or {}
        py_impl = impls.get("python")
        if not py_impl:
            binding.skipped_reason = "no python implementation"
            bindings.append(binding)
            continue

        fn = _resolve_impl(py_impl) if not dry_run else None
        binding.impl_ref = f"{py_impl.get('module') or py_impl.get('source_file')}.{py_impl.get('function') or '?'}"

        if not dry_run and fn is None:
            binding.skipped_reason = "impl not resolvable"
            bindings.append(binding)
            continue

        aliases: Dict[str, List[str]] = action.get("aliases") or {}
        all_aliases: List[str] = []
        for lang_aliases in aliases.values():
            all_aliases.extend(lang_aliases or [])

        if not all_aliases:
            binding.skipped_reason = "no aliases"
            bindings.append(binding)
            continue

        decorator_factory = keyword_decorators[binding.keyword]
        for alias in all_aliases:
            if dry_run:
                binding.aliases_registered.append(alias)
                continue
            try:
                # pytest-bdd parsers.parse kullan ({param} yer tutucular için)
                decorator_factory(parsers.parse(alias))(fn)
                binding.aliases_registered.append(alias)
            except Exception as exc:  # noqa: BLE001
                logger.warning("DSL: alias kaydedilemedi %s -> %s: %s", aid, alias, exc)

        bindings.append(binding)

    registered = sum(len(b.aliases_registered) for b in bindings if not b.skipped_reason)
    total_actions = sum(1 for b in bindings if not b.skipped_reason)
    logger.info(
        "DSL: %d alias kaydedildi (%d cümlecik aktif, %d atlandı)",
        registered,
        total_actions,
        len(bindings) - total_actions,
    )
    return bindings
