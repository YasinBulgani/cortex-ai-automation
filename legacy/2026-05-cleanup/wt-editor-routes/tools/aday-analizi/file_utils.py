# -*- coding: utf-8 -*-
"""
Dosya okuma / yazma yardımcıları.
"""
from pathlib import Path

from .config import ADAY_KLASORU, GORUSME_DOSYASI


def adaylari_bul(aday_klasoru: Path | None = None) -> list[Path]:
    """
    adaylar/ altındaki tüm aday klasörlerini döner.
    """
    root = aday_klasoru or ADAY_KLASORU
    if not root.exists():
        return []
    return [d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]


def gorusme_notunu_oku(aday_path: Path, dosya_adi: str | None = None) -> str:
    """
    Aday klasöründeki gorusme_notlari.md dosyasını okur.
    """
    ad = dosya_adi or GORUSME_DOSYASI
    not_dosyasi = aday_path / ad
    if not not_dosyasi.exists():
        raise FileNotFoundError(f"{aday_path.name} için görüşme notu yok: {not_dosyasi}")
    return not_dosyasi.read_text(encoding="utf-8")
