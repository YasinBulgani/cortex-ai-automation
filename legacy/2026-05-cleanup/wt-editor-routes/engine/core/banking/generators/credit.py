"""
Kredi, faiz oranı, risk skoru, müşteri segmenti üretim modülü.
BDDK kredi mevzuatı referanslı kurallar.
"""
import random
from typing import Optional

# TCMB politika faizi (2025 Q1 başı)
TCMB_POLITIKA_FAIZ = 42.5

SEGMENT_KURALLAR = {
    'Temel':             {'gelir_max': 8000,   'kredi_kats': 2.0, 'skor_ort': 580},
    'Bireysel':          {'gelir_max': 20000,  'kredi_kats': 3.0, 'skor_ort': 680},
    'Premium':           {'gelir_max': 50000,  'kredi_kats': 5.0, 'skor_ort': 780},
    'Özel Bankacılık':   {'gelir_max': None,   'kredi_kats': 8.0, 'skor_ort': 860},
    'Mikro İşletme':     {'gelir_max': None,   'kredi_kats': 4.0, 'skor_ort': 620},
    'KOBİ':              {'gelir_max': None,   'kredi_kats': 12.0,'skor_ort': 720},
    'Kurumsal':          {'gelir_max': None,   'kredi_kats': 20.0,'skor_ort': 800},
}

FAIZ_SPREAD = {
    'konut_kredisi':    (2.0,  6.0),
    'tasit_kredisi':    (3.0,  8.0),
    'ihtiyac_kredisi':  (5.0,  15.0),
    'ticari_kredi':     (-2.0, 4.0),
    'kobi_kredisi':     (1.0,  7.0),
    'kredi_karti':      (10.0, 20.0),
    'mevduat_tl':       (-8.0, -4.0),
    'mevduat_usd':      (-40.0, -38.0),  # Sabit 2-4%
}


def classify_segment(aylik_gelir: float, is_tuzel: bool = False) -> str:
    """Gelire göre müşteri segmenti belirler."""
    if is_tuzel:
        yillik = aylik_gelir * 12
        if yillik < 25_000_000:   return 'Mikro İşletme'
        elif yillik < 125_000_000: return 'KOBİ'
        else:                      return 'Kurumsal'
    if aylik_gelir <= 8000:    return 'Temel'
    elif aylik_gelir <= 20000: return 'Bireysel'
    elif aylik_gelir <= 50000: return 'Premium'
    else:                      return 'Özel Bankacılık'


def generate_faiz_orani(urun_tipi: str = 'ihtiyac_kredisi') -> float:
    """TCMB politika faizine spread ekleyerek faiz oranı üretir."""
    if urun_tipi == 'mevduat_usd':
        return round(random.uniform(2.0, 4.5), 2)
    min_sp, max_sp = FAIZ_SPREAD.get(urun_tipi, (0.0, 5.0))
    oran = TCMB_POLITIKA_FAIZ + random.uniform(min_sp, max_sp)
    return round(max(0.1, oran), 2)


def generate_kredi_limiti(
    aylik_gelir: float,
    segment: Optional[str] = None,
    yas: int = 35,
    risk_skoru: int = 700
) -> float:
    """BDDK kural setine göre kredi limiti hesaplar."""
    if segment is None:
        segment = classify_segment(aylik_gelir)
    kats = SEGMENT_KURALLAR.get(segment, {}).get('kredi_kats', 3.0)
    if yas < 25:   kats *= 0.7
    elif yas > 70: kats *= 0.8
    if risk_skoru < 500:   kats *= 0.5
    elif risk_skoru < 700: kats *= 0.8
    elif risk_skoru > 850: kats *= 1.2
    limit = aylik_gelir * kats
    return round(limit / 100) * 100


def generate_risk_skoru(segment: str = 'Bireysel', temerrut: bool = False) -> int:
    """Müşteri risk/kredi skoru üretir (1-999, KKB/Findeks dağılımı)."""
    if temerrut:
        return max(1, min(999, int(random.gauss(350, 80))))
    ort = SEGMENT_KURALLAR.get(segment, {}).get('skor_ort', 680)
    return max(1, min(999, int(random.gauss(ort, 70))))


def generate_aylik_gelir(segment: str = 'Bireysel') -> float:
    """Segmente uygun aylık gelir üretir."""
    araliklar = {
        'Temel':           (3000, 8000),
        'Bireysel':        (8001, 20000),
        'Premium':         (20001, 50000),
        'Özel Bankacılık': (50001, 200000),
        'Mikro İşletme':   (10000, 80000),
        'KOBİ':            (50000, 500000),
        'Kurumsal':        (200000, 5000000),
    }
    lo, hi = araliklar.get(segment, (5000, 20000))
    return round(random.uniform(lo, hi), 2)
