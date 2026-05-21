"""Prompt katalog / sicil sunucusu.

Agent'lar sabit `SYSTEM = \"\"\"...\"\"\"` kodlamak yerine buraya gelip
`PromptRegistry.get(key)` / `PromptRegistry.get_system(key)` çağırır. Bu,
prompt'ların versiyonlanmasını (örn. A/B testi, rollback) ve LLM model
rota kararlarının merkezi yönetimini sağlar.

Katalog:
  1) `BGTS_PROMPTS_CATALOG` env değişkeni varsa oradaki JSON'u kullan.
  2) Yoksa paket içindeki `prompts_catalog.json`'u kullan.

Katalog eksik / bozuksa sessizce boş katalogla çalışır ve agent'lar
`fallback_system` parametresindeki string'e düşer — bu sayede geçiş
dönemi boyunca hiçbir agent sessizce kırılmaz.

Not: Bu dosya cache'deki .pyc'den rekonstrükte edildi (2026-04-19).
Orijinal kaynak dosyaları git'e eklenmemişti; API 1:1 korundu.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

_logger = logging.getLogger(__name__)

_DEFAULT_CATALOG = Path(__file__).resolve().parent / "prompts_catalog.json"


@dataclass
class Prompt:
    """Katalog'daki bir prompt kaydı."""

    key: str
    version: int = 0
    system: str = ""
    user_template: str = ""
    model: Optional[str] = None
    description: str = ""


def _catalog_path() -> Path:
    """Katalog JSON yolu — env override edilebilir."""
    override = os.environ.get("BGTS_PROMPTS_CATALOG")
    if override:
        p = Path(override)
        if p.exists():
            return p
    return _DEFAULT_CATALOG


@lru_cache(maxsize=1)
def _load() -> dict[str, Prompt]:
    """Katalog'u yükler, `key → Prompt` sözlüğü döner."""
    path = _catalog_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _logger.info("Prompt kataloğu bulunamadı (%s); boş katalogla devam.", path)
        return {}
    except json.JSONDecodeError as exc:
        _logger.info("Prompt kataloğu bozuk (%s): %s", path, exc)
        return {}

    prompts_in = data.get("prompts", data) if isinstance(data, dict) else []
    out: dict[str, Prompt] = {}
    if isinstance(prompts_in, dict):
        for key, cfg in prompts_in.items():
            if not isinstance(cfg, dict):
                continue
            system = cfg.get("system", "")
            out[key] = Prompt(
                key=key,
                version=int(cfg.get("version", 0)),
                system=system,
                user_template=cfg.get("user_template", ""),
                model=cfg.get("model"),
                description=cfg.get("description", ""),
            )
    elif isinstance(prompts_in, list):
        for cfg in prompts_in:
            if not isinstance(cfg, dict):
                continue
            key = cfg.get("key")
            if not key:
                continue
            out[key] = Prompt(
                key=key,
                version=int(cfg.get("version", 0)),
                system=cfg.get("system", ""),
                user_template=cfg.get("user_template", ""),
                model=cfg.get("model"),
                description=cfg.get("description", ""),
            )
    return out


class PromptRegistry:
    """Global registry — tüm yöntemler static."""

    @staticmethod
    def get(key: str, fallback: str = "", fallback_system: str = "") -> Prompt:
        '''Prompt'u döner; yoksa verilen fallback'le sahte bir Prompt uydurur.

        Agent dosyalarında in-line ``SYSTEM = """..."""`` kaldırılırken bu
        fallback en son güvence olur — dosyanın eski davranışını korur.

        İki parametre adı da (fallback / fallback_system) kabul edilir, ikincisi
        geriye dönük uyumluluk için.
        '''
        reg = _load()
        if key in reg:
            return reg[key]
        system = fallback or fallback_system
        if system:
            return Prompt(key=key, version=0, system=system)
        return Prompt(key=key, version=0, system="")

    @staticmethod
    def get_system(key: str, fallback: str = "", fallback_system: str = "") -> str:
        """Sadece sistem prompt'u döner — en sık kullanılan kısayol."""
        return PromptRegistry.get(
            key, fallback=fallback, fallback_system=fallback_system
        ).system

    @staticmethod
    def list_all() -> list[Prompt]:
        """Katalog'daki tüm prompt'ları döner (UI/admin için)."""
        return list(_load().values())
