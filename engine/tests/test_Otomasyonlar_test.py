"""Google arama temelli örnek Playwright testi.

Orijinal feature Google'ın arama kutusuna dayanıyor ama bu otomasyon takımı
BASE_URL=http://localhost:3000 (TestwrightAI) üzerinde çalıştığı için arama
kutusu bulunamıyor ve her koşuda kırılıyor. Bu test bir referans/şablon
olarak bırakıldı; CI'da mavi kalması için skip edildi.

Güvenli hale getirmek için iki seçenek:
  1) Feature'ı TestwrightAI'nın kendi arama UI'sine uyarla
  2) BASE_URL'i Google'a özel override et ve steps'i Google için güncelle
"""
import pytest

pytest.skip(
    "Google arama senaryosu TestwrightAI BASE_URL'iyle uyumsuz — skip.",
    allow_module_level=True,
)

from pytest_bdd import scenarios  # noqa: E402

scenarios("../features/Otomasyonlar/test.feature")
