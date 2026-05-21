"""
core/locator_manager.py — Bridge / Adapter

Delegates to the canonical ``locators.locator_manager.LocatorManager`` while
keeping backward-compatible classmethods (``resolve``, ``load``, ``configure``,
``load_all``, ``clear``, ``keys``, ``get``, ``as_dict``).

Legacy feature-based JSON files under ``engine/data/locators/`` are still
loaded transparently: each NexusQA-style entry ``{key, type, value}`` is
converted into a Playwright selector and stored in a flat map so that
``resolve(key)`` works exactly as before.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_LOCATORS_DIR = Path(__file__).resolve().parent.parent / "data" / "locators"

_TYPE_MAP = {
    "id":          lambda v: f"#{v}",
    "css":         lambda v: v,
    "xpath":       lambda v: v if v.startswith("//") or v.startswith("(") else f"//{v}",
    "name":        lambda v: f'[name="{v}"]',
    "classname":   lambda v: f".{v}",
    "class":       lambda v: f".{v}",
    "linktext":    lambda v: f"text={v}",
    "text":        lambda v: f"text={v}",
    "testid":      lambda v: f"[data-testid=\"{v}\"]",
    "data-testid": lambda v: f"[data-testid=\"{v}\"]",
    "role":        lambda v: f"role={v}",
    "placeholder": lambda v: f'[placeholder="{v}"]',
    "label":       lambda v: f"label={v}",
}


def _canonical_manager():
    """Lazy import to avoid circular references at module load time."""
    from locators.locator_manager import LocatorManager as _Canonical
    return _Canonical


class LocatorManager:
    """
    Backward-compatible bridge.

    ``resolve(key)`` first checks the legacy flat map (loaded from
    ``data/locators/*.json``).  If no match is found it falls through as a raw
    selector — the same behavior as before.

    New code should use ``locators.locator_manager.LocatorManager`` directly.
    """

    _locators: dict[str, str] = {}
    _loaded_features: set[str] = set()
    _locators_dir: Path = _DEFAULT_LOCATORS_DIR
    _canonical: object | None = None

    @classmethod
    def configure(cls, locators_dir: str | Path):
        cls._locators_dir = Path(locators_dir)

    @classmethod
    def load(cls, feature_name: str, directory: str | Path | None = None) -> dict[str, str]:
        base_dir = Path(directory) if directory else cls._locators_dir

        if feature_name in cls._loaded_features:
            return cls._locators

        json_path = base_dir / f"{feature_name}.json"
        if not json_path.exists():
            logger.debug("Locator dosyasi bulunamadi: %s", json_path)
            return cls._locators

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"Locator JSON okunamadi: {json_path} — {exc}") from exc

        if not isinstance(entries, list):
            raise RuntimeError(f"Locator JSON bir liste olmali: {json_path}")

        for entry in entries:
            key = entry.get("key", "").strip()
            loc_type = entry.get("type", "css").strip().lower()
            value = entry.get("value", "").strip()
            if not key or not value:
                continue
            converter = _TYPE_MAP.get(loc_type)
            selector = converter(value) if converter else value
            cls._locators[key] = selector

        cls._loaded_features.add(feature_name)
        logger.info(
            "Locator'lar yuklendi: %s (%d adet, toplam: %d)",
            feature_name, len(entries), len(cls._locators),
        )
        return cls._locators

    @classmethod
    def load_all(cls, directory: str | Path | None = None) -> dict[str, str]:
        base_dir = Path(directory) if directory else cls._locators_dir
        if not base_dir.exists():
            return cls._locators
        for json_file in sorted(base_dir.glob("*.json")):
            cls.load(json_file.stem, base_dir)
        return cls._locators

    @classmethod
    def resolve(cls, key_or_selector: str) -> str:
        if key_or_selector in cls._locators:
            return cls._locators[key_or_selector]
        return key_or_selector

    @classmethod
    def get(cls, key: str) -> Optional[str]:
        return cls._locators.get(key)

    @classmethod
    def clear(cls):
        cls._locators.clear()
        cls._loaded_features.clear()

    @classmethod
    def keys(cls) -> list[str]:
        return list(cls._locators.keys())

    @classmethod
    def as_dict(cls) -> dict[str, str]:
        return dict(cls._locators)

    @classmethod
    def get_canonical(cls):
        """Return an instance of the canonical LocatorManager for rich operations."""
        if cls._canonical is None:
            cls._canonical = _canonical_manager()()
        return cls._canonical
