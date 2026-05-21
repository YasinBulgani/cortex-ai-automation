# -*- coding: utf-8 -*-
"""
Yapılandırma sabitleri.
OPENAI_API_KEY ortam değişkeninden okunur.
"""
import os
from pathlib import Path

# Adayların bulunduğu ana klasör (bu script'in üst dizininde adaylar/)
_BASE = Path(__file__).resolve().parent
ADAY_KLASORU = Path(os.getenv("ADAY_KLASORU", str(_BASE / "adaylar")))

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Dosya adları
GORUSME_DOSYASI = "gorusme_notlari.md"
ANALIZ_DOSYASI = "analiz.json"
