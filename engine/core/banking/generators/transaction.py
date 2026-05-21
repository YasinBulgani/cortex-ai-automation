"""
İşlem, EFT, döviz kuru veri üretim modülü.
"""
import random
from datetime import datetime, timedelta
from typing import Literal

IslemTuru = Literal['EFT', 'Havale', 'FAST', 'POS', 'ATM', 'Faiz', 'Masraf', 'İade', 'Döviz']

DOVIZ_KURLAR = {
    'USD/TRY': 34.50,
    'EUR/TRY': 37.20,
    'GBP/TRY': 43.80,
    'CHF/TRY': 39.10,
    'USD/EUR': 0.928,
}

TURKISH_MERCHANTS = [
    'Migros', 'CarrefourSA', 'BİM', 'A101', 'Teknosa', 'MediaMarkt',
    'LC Waikiki', 'Zara TR', 'Koton', 'Decathlon', 'Getir', 'Trendyol',
    'Amazon TR', 'Hepsiburada', 'Shell İstasyon', 'BP İstasyon',
    'İstanbul Havalimanı', 'THY', 'Pegasus', 'Sahibinden.com'
]


def generate_eft_reference(bank_code: str = '0046') -> str:
    """TCMB EFT referans numarası: banka(4) + tarih(8) + sekans(8)"""
    today = datetime.now().strftime('%Y%m%d')
    seq = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{bank_code}{today}{seq}"


def generate_fast_reference() -> str:
    """FAST referans numarası: 20 hane"""
    return ''.join([str(random.randint(0, 9)) for _ in range(20)])


def generate_cek_numarasi() -> str:
    """Çek seri numarası: 3 büyük harf + 7 rakam"""
    harfler = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
    rakamlar = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return harfler + rakamlar


def generate_doviz_kuru(kaynak: str = 'USD', hedef: str = 'TRY', bant_pct: float = 0.03) -> float:
    """Gerçekçi döviz kuru üretir (±%3 bant)."""
    pair = f"{kaynak}/{hedef}"
    reverse = f"{hedef}/{kaynak}"
    if pair in DOVIZ_KURLAR:
        base = DOVIZ_KURLAR[pair]
    elif reverse in DOVIZ_KURLAR:
        base = 1 / DOVIZ_KURLAR[reverse]
    else:
        base = 1.0
    band = base * bant_pct
    return round(random.uniform(base - band, base + band), 4)


def generate_transaction_date(days_back: int = 365) -> str:
    """Son N gün içinde rastgele tarih üretir."""
    start = datetime.now() - timedelta(days=days_back)
    delta = timedelta(seconds=random.randint(0, days_back * 86400))
    return (start + delta).strftime('%Y-%m-%d %H:%M:%S')


def generate_merchant() -> str:
    """Türk işyeri adı üretir."""
    return random.choice(TURKISH_MERCHANTS)


def generate_aciklama(islem_turu: str = 'EFT') -> str:
    """İşlem açıklaması üretir."""
    templates = {
        'EFT': ['EFT - {} tarihli gönderim', 'Borç ödemesi - {}', 'Fatura ödemesi'],
        'Havale': ['İç havale', 'Aile transferi', 'Kira ödemesi'],
        'FAST': ['FAST anlık transfer', 'FAST - {} TL'],
        'POS': [f'{m} - POS' for m in TURKISH_MERCHANTS[:5]],
        'ATM': ['ATM nakit çekim', 'ATM para yatırma'],
        'Faiz': ['Aylık mevduat faizi', 'Kredili mevduat faizi'],
        'Masraf': ['Hesap işletim ücreti', 'EFT masraf', 'SMS ücret'],
    }
    options = templates.get(islem_turu, ['İşlem'])
    tmpl = random.choice(options)
    if '{}' in tmpl:
        tmpl = tmpl.format(datetime.now().strftime('%d.%m.%Y'))
    return tmpl
