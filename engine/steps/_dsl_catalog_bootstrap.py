"""
engine/steps/_dsl_catalog_bootstrap.py

DSL Katalog Pilot Migration:
Katalog'dan (packages/dsl/catalog/*.yaml) yeni alias kayıtlarını
runtime'da ekler. Şu an sadece pilot olarak 5 click step'i kapsar
— bunların mevcut TR pattern'leri engine/steps/click_steps.py'de
kayıtlı, ek olarak katalogdaki EN alias'ları da aynı fonksiyona
bağlanır.

Import edilme: engine/steps/conftest.py bu modülü import ederse
(manuel ya da pytest collection zamanında), katalog alias'ları
aktif hale gelir. Pilot kapsamında varsayılan olarak import edilmez
— etkinleştirmek için ortam değişkeni:

    TWAI_DSL_PILOT=1 pytest engine/steps/...
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Repo kökünü sys.path'e ekle ki packages.* import edilebilsin
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Pilot kapsamındaki cümlecik id'leri — sadece bu id'lerin EN alias'ları kaydolsun.
PILOT_IDS = {
    "step_click_element",
    "step_double_click",
    "step_right_click",
    "step_click_text",
    "step_force_click",
}


def bootstrap_pilot() -> None:
    """Pilot kapsamındaki katalog alias'larını pytest-bdd'e kaydet.

    Mevcut TR pattern'leri değiştirmeden YENİ alias'lar (katalogda eklenmiş
    olanlar) da aynı fonksiyona bağlanır. Böylece aynı test hem Türkçe hem
    İngilizce yazılabilir.
    """
    try:
        from packages.dsl.loaders.python import register_catalog
    except ImportError as exc:
        logger.warning("DSL: loader import edilemedi: %s", exc)
        return

    # skip_ids: pilot olmayan herkes atlansın
    all_catalog = None
    try:
        from packages.dsl.loaders.python.loader import load_catalog
        all_catalog = [a.get("id") for a in load_catalog() if isinstance(a, dict)]
    except Exception:
        all_catalog = []

    skip_ids = [i for i in all_catalog if i and i not in PILOT_IDS]

    bindings = register_catalog(skip_ids=skip_ids)
    active = [b for b in bindings if not b.skipped_reason]
    registered = sum(len(b.aliases_registered) for b in active)
    logger.info(
        "DSL pilot: %d cümlecik için %d alias kaydedildi (EN+TR)",
        len(active),
        registered,
    )


# Varsayılan davranış: sadece TWAI_DSL_PILOT=1 ise çalış.
if os.getenv("TWAI_DSL_PILOT") == "1":
    bootstrap_pilot()
