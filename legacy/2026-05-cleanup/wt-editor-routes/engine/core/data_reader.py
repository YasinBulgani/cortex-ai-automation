"""
core/data_reader.py — Domain/Environment Bazli Test Verisi Okuyucu

NexusQA projesindeki DataReader.java pattern'inin Python uyarlamasi.

Dosya adi formati:
    {domain}-{env}-data.json   (ornek: default-test-data.json, girit-prod-data.json)

Ozellikler:
  - Domain ve environment bazli JSON veri dosyalari
  - common-{env}-data.json ile ortak verileri merge etme
  - @var syntax'ini (MaviYaka) ve {var} syntax'ini (TestwrightAI) destekler
  - GlobalContext ile entegre calisir

Kullanim:
    DataReader.load("default", "test")
    username = DataReader.get("username")
    rendered = DataReader.render_value("Kullanici @username ile giris yapar")
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "testdata"


class DataReader:
    """Domain ve environment bazli test verisi okuyucu."""

    _data: dict[str, str] = {}
    _current_domain: str = "default"
    _current_env: str = "test"
    _data_dir: Path = _DEFAULT_DATA_DIR

    @classmethod
    def configure(cls, data_dir: str | Path):
        """Veri dosyalarinin bulundugu dizini degistirir."""
        cls._data_dir = Path(data_dir)

    @classmethod
    def load(cls, domain: str = "default", env: str = "test", data_dir: str | Path | None = None) -> dict[str, str]:
        """
        Belirtilen domain ve environment icin veri dosyasini yukler.
        Varsa common-{env}-data.json ile merge eder.

        Args:
            domain: Domain adi (ornek: default, girit, plus)
            env: Ortam (test, staging, prod)
            data_dir: Opsiyonel dizin yolu

        Returns:
            Yuklenen veri dict'i
        """
        base_dir = Path(data_dir) if data_dir else cls._data_dir
        cls._current_domain = domain
        cls._current_env = env

        merged: dict[str, str] = {}

        # 1) Domain/env dosyasini yukle
        domain_file = base_dir / f"{domain}-{env}-data.json"
        if domain_file.exists():
            try:
                with open(domain_file, "r", encoding="utf-8") as f:
                    domain_data = json.load(f)
                if isinstance(domain_data, dict):
                    merged.update(domain_data)
                logger.info("Domain veri dosyasi yuklendi: %s", domain_file.name)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Veri dosyasi okunamadi: %s — %s", domain_file, exc)
        else:
            logger.warning("Domain veri dosyasi bulunamadi: %s", domain_file)

        # 2) Common dosyayi yukle ve ustune yaz (oncelik common'da)
        common_file = base_dir / f"common-{env}-data.json"
        if common_file.exists():
            try:
                with open(common_file, "r", encoding="utf-8") as f:
                    common_data = json.load(f)
                if isinstance(common_data, dict):
                    merged.update(common_data)
                logger.info("Common veri dosyasi merge edildi: %s", common_file.name)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Common dosya okunamadi: %s — %s", common_file, exc)

        cls._data = merged
        return cls._data

    @classmethod
    def reload(cls, domain: str, env: str):
        """Yeni domain/env icin veriyi yeniden yukler. Multi-domain kosularda kullanilir."""
        cls._data.clear()
        return cls.load(domain, env)

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        """Verilen key'e karsilik gelen degeri doner."""
        return cls._data.get(key, default)

    @classmethod
    def get_required(cls, key: str) -> str:
        """Zorunlu veri alanini doner, yoksa hata firlatir."""
        if key not in cls._data:
            raise KeyError(
                f"Test verisinde '{key}' bulunamadi "
                f"(domain={cls._current_domain}, env={cls._current_env})"
            )
        return cls._data[key]

    @classmethod
    def render_value(cls, text: str) -> str:
        """
        Metindeki placeholder'lari cozumler.
        Hem @var (MaviYaka) hem {var} (TestwrightAI) syntax'ini destekler.

        Ornekler:
            "@username" -> data'dan username degeri
            "{username}" -> data'dan username degeri
            "+-izinAciklama" -> degistirilmez (ozel prefix degil)
        """
        if not isinstance(text, str):
            return text

        # @var syntax'i (NexusQA pattern)
        def replace_at(match):
            key = match.group(1)
            return cls._data.get(key, match.group(0))

        text = re.sub(r"@(\w+)", replace_at, text)

        # {var} syntax'i (TestwrightAI pattern)
        def replace_brace(match):
            key = match.group(1)
            return cls._data.get(key, match.group(0))

        text = re.sub(r"\{(\w+)\}", replace_brace, text)

        return text

    @classmethod
    def has(cls, key: str) -> bool:
        """Key'in var olup olmadigini kontrol eder."""
        return key in cls._data

    @classmethod
    def all(cls) -> dict[str, str]:
        """Tum verilerin kopyasini doner."""
        return dict(cls._data)

    @classmethod
    def clear(cls):
        """Tum verileri temizler."""
        cls._data.clear()

    @classmethod
    def current_domain(cls) -> str:
        return cls._current_domain

    @classmethod
    def current_env(cls) -> str:
        return cls._current_env
