# -*- coding: utf-8 -*-
"""
Tüm aday klasörlerindeki gorusme_notlari.md dosyalarını okur,
ChatGPT ile analiz eder ve analiz.json olarak aynı klasöre yazar.

Kullanım:
  python -m aday_analizi.main
  # veya
  python aday_analizi/main.py

Ortam değişkenleri:
  OPENAI_API_KEY   : OpenAI API anahtarı (zorunlu)
  ADAY_KLASORU     : Aday klasörlerinin olduğu dizin (varsayılan: ./adaylar)
  OPENAI_MODEL     : Model adı (varsayılan: gpt-4o-mini)
"""
from pathlib import Path

# .env yükle (proje kökünde veya aday_analizi/ içinde)
def _load_dotenv():
    try:
        from dotenv import load_dotenv
        base = Path(__file__).resolve().parent
        for p in [base / ".env", base.parent / ".env"]:
            if p.exists():
                load_dotenv(p)
                break
    except ImportError:
        pass


_load_dotenv()

from . import adaylari_bul, analiz_kaydet, chatgpt_analiz_et, gorusme_notunu_oku
from .config import ADAY_KLASORU, GORUSME_DOSYASI


def main(aday_klasoru: Path | None = None) -> None:
    aday_klasoru = aday_klasoru or ADAY_KLASORU

    if not aday_klasoru.exists():
        print(f"Aday klasörü bulunamadı: {aday_klasoru}")
        print("  ADAY_KLASORU ile farklı bir dizin verebilirsiniz.")
        return

    adaylar = adaylari_bul(aday_klasoru)
    if not adaylar:
        print(f"Hiç aday klasörü yok: {aday_klasoru}")
        return

    print(f"Toplam {len(adaylar)} aday klasörü bulundu.\n")

    for aday in sorted(adaylar):
        try:
            print(f"Analiz ediliyor: {aday.name}")
            notlar = gorusme_notunu_oku(aday, GORUSME_DOSYASI)
            analiz = chatgpt_analiz_et(notlar)
            analiz_kaydet(aday, analiz)
            print(f"  ✔ Tamamlandı: {aday.name}\n")
        except FileNotFoundError as e:
            print(f"  ✖ Atlanıyor ({aday.name}): {e}\n")
        except Exception as e:
            print(f"  ✖ Hata ({aday.name}): {e}\n")


if __name__ == "__main__":
    main()
