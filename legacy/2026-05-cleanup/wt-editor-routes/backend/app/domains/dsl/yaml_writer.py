"""`packages/dsl/catalog/*.yaml` için güvenli, round-trip YAML yazıcı.

Tasarım kuralları:
    * `ruamel.yaml` ile **round-trip** — dosyadaki yorumlar, anahtar sırası ve
      tırnak stili mümkün olduğunca korunur. `pyyaml` bu durumu bozar.
    * Yazma işlemi atomik: `tmp` dosyasına yazılır → `fsync` → `rename`.
    * Process içinde tek bir `RLock` ile korunur — paralel API çağrılarının
      aynı dosyayı yarıştırmasını önler. Çok-node setup'ında ayrıca git push
      aşamasında doğal serileştirme var.
    * Hangi YAML'e yazılacağı `category` prefix'inden belirlenir; bilinmiyorsa
      `uncategorized.yaml`'a düşer.
    * Cümleciklerin içindeki alan sırası, okunabilirlik için sabit bir
      şablona göre yazılır (id → category → description → aliases …).

Public API:
    * `load_all_actions()`                    — (path, raw_dict) listesi
    * `find_action_file(action_id)`           — action_id hangi dosyada?
    * `upsert_action(action_dict)`            — yoksa ekle, varsa üstüne yaz
    * `delete_action(action_id)`              — sil (ve dosya kaldıysa boş bırakma)
    * `write_actions(file_path, actions)`     — (düşük seviye) tüm listeyi yaz
"""

from __future__ import annotations

import io
import logging
import os
import threading
from pathlib import Path
from typing import Any, Iterable, Optional

from ruamel.yaml import YAML  # type: ignore[import-untyped]
from ruamel.yaml.comments import CommentedMap  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# packages/dsl/catalog — loader ile aynı kaynak
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
CATALOG_DIR = _PROJECT_ROOT / "packages" / "dsl" / "catalog"

# Kategori prefix'i → hedef YAML dosyası
_CATEGORY_TO_FILE: dict[str, str] = {
    "ui": "ui-actions.yaml",
    "api": "api-actions.yaml",
    "assert": "assertions.yaml",
    "bgts": "bgts-domain.yaml",
    "mobile": "mobile-actions.yaml",
}
DEFAULT_FILE = "uncategorized.yaml"

# Action içindeki alan sırası — hep aynı okunur olsun
_ACTION_FIELD_ORDER = [
    "id",
    "category",
    "description",
    "aliases",
    "parameters",
    "implementations",
    "tags",
    "since",
    "deprecated",
    "examples",
    "notes",
]

_LOCK = threading.RLock()


def _yaml() -> YAML:
    """Projedeki YAML stilini koruyacak şekilde yapılandırılmış parser."""
    y = YAML()
    y.preserve_quotes = True
    y.width = 120          # Mevcut kataloglarda satırlar uzun; sarmalamayı azalt
    y.indent(mapping=2, sequence=2, offset=0)
    y.allow_unicode = True
    return y


# ── Dosya seçimi ────────────────────────────────────────────────────────────


def target_file_for_category(category: str) -> Path:
    """Kategoriye göre hangi YAML dosyasında durmalı?

    `ui.click.right` → `ui-actions.yaml`, `bgts.approval` → `bgts-domain.yaml`.
    Bilinmeyen kategoriler `uncategorized.yaml`'a düşer.
    """
    top = (category or "").split(".", 1)[0]
    return CATALOG_DIR / _CATEGORY_TO_FILE.get(top, DEFAULT_FILE)


def find_action_file(action_id: str) -> Optional[Path]:
    """action_id hangi YAML dosyasında tanımlı? Bulamazsa None."""
    for path in sorted(CATALOG_DIR.glob("*.yaml")):
        try:
            data = _read_yaml(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("YAML okunamadı %s: %s", path.name, exc)
            continue
        for raw in data.get("actions") or []:
            if isinstance(raw, dict) and raw.get("id") == action_id:
                return path
    return None


# ── Ham okuma/yazma ─────────────────────────────────────────────────────────


def _read_yaml(path: Path) -> CommentedMap:
    if not path.exists():
        return CommentedMap({"version": "1.0.0", "actions": []})
    with path.open("r", encoding="utf-8") as f:
        data = _yaml().load(f)
    if data is None:
        data = CommentedMap()
    if not isinstance(data, (dict, CommentedMap)):
        raise ValueError(f"{path.name}: root bir eşleşme (map) olmalı")
    return data  # type: ignore[return-value]


def _write_yaml_atomic(path: Path, data: Any) -> None:
    """fsync + rename ile atomik yaz."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    buf = io.StringIO()
    _yaml().dump(data, buf)
    with tmp_path.open("w", encoding="utf-8") as f:
        f.write(buf.getvalue())
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


# ── Normalize ───────────────────────────────────────────────────────────────


def _reorder_fields(action: dict[str, Any]) -> CommentedMap:
    """Action içindeki alanları sabit sıraya koy."""
    out = CommentedMap()
    for key in _ACTION_FIELD_ORDER:
        if key in action:
            out[key] = action[key]
    # Kalan extra alanlar (örn. source_yaml) son'a
    for key, val in action.items():
        if key not in out and key != "source_yaml":
            out[key] = val
    return out


# ── Yüksek seviye API ──────────────────────────────────────────────────────


def load_all_actions() -> list[tuple[Path, dict[str, Any]]]:
    """Her katalog dosyasını açıp içindeki aksiyonları (path, raw_dict) olarak döner."""
    out: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(CATALOG_DIR.glob("*.yaml")):
        try:
            data = _read_yaml(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("YAML okunamadı %s: %s", path.name, exc)
            continue
        for raw in data.get("actions") or []:
            if isinstance(raw, dict):
                out.append((path, raw))
    return out


def upsert_action(action: dict[str, Any]) -> Path:
    """Cümleciği hedef YAML dosyasına ekle veya güncelle.

    Aynı id başka bir dosyada varsa onu silip hedefe taşır — kategori
    değişirse dosya da değişsin.

    Return: yazılan dosya yolu.
    """
    action_id = action.get("id")
    if not action_id:
        raise ValueError("action.id zorunlu")
    category = action.get("category") or ""
    target = target_file_for_category(category)

    with _LOCK:
        current_file = find_action_file(action_id)
        if current_file is not None and current_file != target:
            # Kategori değişti → eski dosyadan sil
            _remove_from_file(current_file, action_id)

        data = _read_yaml(target)
        actions: list[Any] = list(data.get("actions") or [])
        normalized = _reorder_fields(action)

        replaced = False
        for idx, item in enumerate(actions):
            if isinstance(item, dict) and item.get("id") == action_id:
                actions[idx] = normalized
                replaced = True
                break
        if not replaced:
            actions.append(normalized)
            actions.sort(key=lambda a: str(a.get("id") or ""))

        data["actions"] = actions
        if "version" not in data:
            data["version"] = "1.0.0"
        _write_yaml_atomic(target, data)
        logger.info(
            "DSL YAML yazıldı: %s (%s → %s)",
            target.name,
            action_id,
            "update" if replaced else "create",
        )
        return target


def delete_action(action_id: str) -> Optional[Path]:
    """Cümleciği tüm katalog dosyalarından sil.

    Return: silinen dosyanın yolu (yoksa None).
    """
    with _LOCK:
        path = find_action_file(action_id)
        if path is None:
            return None
        _remove_from_file(path, action_id)
        return path


def _remove_from_file(path: Path, action_id: str) -> None:
    data = _read_yaml(path)
    before = len(data.get("actions") or [])
    data["actions"] = [
        a for a in (data.get("actions") or [])
        if not (isinstance(a, dict) and a.get("id") == action_id)
    ]
    after = len(data["actions"])
    if after != before:
        _write_yaml_atomic(path, data)
        logger.info("DSL YAML sildi: %s → %s (%d -> %d)", path.name, action_id, before, after)


def write_actions(path: Path, actions: Iterable[dict[str, Any]]) -> None:
    """Verilen aksiyon listesini tek seferde dosyaya yazar (testler için)."""
    data = _read_yaml(path) if path.exists() else CommentedMap({"version": "1.0.0"})
    data["actions"] = [_reorder_fields(a) for a in actions]
    _write_yaml_atomic(path, data)


# ── Yardımcılar ────────────────────────────────────────────────────────────


def files_touched_by_action(action_id: str, new_category: str | None = None) -> list[Path]:
    """Bir action'ı yazmak/silmek için değişecek dosya listesi (git için)."""
    files: set[Path] = set()
    current = find_action_file(action_id)
    if current is not None:
        files.add(current)
    if new_category:
        files.add(target_file_for_category(new_category))
    return sorted(files)
