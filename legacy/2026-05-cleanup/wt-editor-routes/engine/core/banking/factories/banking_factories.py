"""
factory_boy tabanlı bankacılık veri fabrikaları.
İlişkisel üretim: Müşteri → Hesap → İşlem → Kredi → Taksit → Kart
"""
import random
import factory
from datetime import datetime
from factory.fuzzy import FuzzyChoice, FuzzyFloat, FuzzyInteger

from banking.generators.identity  import generate_tc_kimlik, generate_vkn
from banking.generators.account   import generate_tr_iban, generate_swift, TR_BANK_CODES
from banking.generators.card      import generate_card_number, generate_cvv, generate_card_expiry
from banking.generators.transaction import generate_eft_reference, generate_transaction_date, generate_aciklama
from banking.generators.credit    import (
    classify_segment, generate_faiz_orani, generate_kredi_limiti,
    generate_risk_skoru, generate_aylik_gelir
)


class MusteriFactory(factory.Factory):
    class Meta:
        model = dict

    musteri_no   = factory.Sequence(lambda n: f"MUS{n:08d}")
    tc_kimlik    = factory.LazyFunction(generate_tc_kimlik)
    ad           = factory.Faker('first_name', locale='tr_TR')
    soyad        = factory.Faker('last_name',  locale='tr_TR')
    dogum_tarihi = factory.Faker('date_of_birth', minimum_age=18, maximum_age=75)
    telefon      = factory.LazyFunction(
        lambda: f"+905{random.randint(10,59)}{random.randint(1000000,9999999)}"
    )
    email        = factory.LazyAttribute(
        lambda o: f"{o['ad'].lower().replace(' ','')}.{o['soyad'].lower()}@test.example.com"
        if isinstance(o, dict)
        else f"test{random.randint(1000,9999)}@test.example.com"
    )
    aylik_gelir  = factory.LazyFunction(lambda: round(random.uniform(5000, 60000), 2))
    segment      = factory.LazyAttribute(lambda o: classify_segment(o.aylik_gelir) if hasattr(o, 'aylik_gelir') else 'Bireysel')
    risk_skoru   = factory.LazyFunction(lambda: generate_risk_skoru('Bireysel'))
    kvkk_onay    = True
    kimlik_tipi  = 'TC'


class KurumsalMusteriFactory(MusteriFactory):
    tc_kimlik   = None
    vkn         = factory.LazyFunction(generate_vkn)
    unvan       = factory.Faker('company', locale='tr_TR')
    kimlik_tipi = 'VKN'
    segment     = 'KOBİ'
    aylik_gelir = factory.LazyFunction(lambda: round(random.uniform(50000, 500000), 2))


class HesapFactory(factory.Factory):
    class Meta:
        model = dict

    hesap_no    = factory.Sequence(lambda n: f"HSP{n:010d}")
    iban        = factory.LazyFunction(generate_tr_iban)
    hesap_turu  = FuzzyChoice(['Vadesiz TL', 'Vadeli TL', 'Döviz USD', 'Döviz EUR'])
    bakiye      = FuzzyFloat(0, 250_000)
    para_birimi = factory.LazyAttribute(
        lambda o: 'USD' if 'USD' in o.hesap_turu else
                  'EUR' if 'EUR' in o.hesap_turu else 'TRY'
        if hasattr(o, 'hesap_turu') else 'TRY'
    )
    acilis_tarihi = factory.Faker('date_between', start_date='-10y', end_date='today')
    aktif       = True
    banka_kodu  = factory.LazyFunction(lambda: random.choice(list(TR_BANK_CODES.keys())))


class IslemFactory(factory.Factory):
    class Meta:
        model = dict

    referans_no  = factory.LazyFunction(generate_eft_reference)
    islem_turu   = FuzzyChoice(['EFT', 'Havale', 'FAST', 'POS', 'ATM', 'Faiz', 'Masraf'])
    tutar        = FuzzyFloat(1, 50_000)
    para_birimi  = FuzzyChoice(['TRY', 'TRY', 'TRY', 'USD', 'EUR'])
    aciklama     = factory.LazyAttribute(
        lambda o: generate_aciklama(o.islem_turu) if hasattr(o, 'islem_turu') else 'İşlem'
    )
    tarih        = factory.LazyFunction(generate_transaction_date)
    durum        = FuzzyChoice(['Tamamlandı', 'Tamamlandı', 'Tamamlandı', 'Beklemede', 'İptal'])


class KrediFactory(factory.Factory):
    class Meta:
        model = dict

    kredi_no    = factory.Sequence(lambda n: f"KRD{n:010d}")
    kredi_turu  = FuzzyChoice(['Konut', 'Taşıt', 'İhtiyaç', 'Ticari', 'KOBİ'])
    anapara     = FuzzyFloat(10_000, 2_000_000)
    faiz_orani  = factory.LazyFunction(lambda: generate_faiz_orani('ihtiyac_kredisi'))
    vade_ay     = FuzzyInteger(6, 240)
    durum       = FuzzyChoice(['Aktif', 'Aktif', 'Aktif', 'Kapalı', 'Gecikme'])
    kullandirma_tarihi = factory.Faker('date_between', start_date='-5y', end_date='today')


class KartFactory(factory.Factory):
    class Meta:
        model = dict

    kart_no     = factory.LazyFunction(lambda: generate_card_number('troy'))
    kart_turu   = FuzzyChoice(['Troy Debit', 'Troy Credit', 'Visa Debit', 'Mastercard Credit'])
    cvv         = factory.LazyFunction(lambda: generate_cvv('troy'))
    gecerlilik  = factory.LazyFunction(generate_card_expiry)
    limit       = FuzzyFloat(5_000, 100_000)
    aktif       = True


FACTORY_MAP = {
    'musteri':    MusteriFactory,
    'kurumsal':   KurumsalMusteriFactory,
    'hesap':      HesapFactory,
    'islem':      IslemFactory,
    'kredi':      KrediFactory,
    'kart':       KartFactory,
}


def generate_banking_data(entity_type: str, count: int = 10, seed: int = None) -> list:
    """Belirtilen bankacılık varlık tipinden count adet üretir."""
    if seed is not None:
        random.seed(seed)
        import faker as fk
        fk.proxy.DEFAULT_LOCALE = 'tr_TR'
    factory_cls = FACTORY_MAP.get(entity_type)
    if not factory_cls:
        raise ValueError(f"Bilinmeyen entity tipi: {entity_type}. Geçerli: {list(FACTORY_MAP.keys())}")
    return [factory_cls() for _ in range(count)]


def generate_relational_dataset(
    musteri_count: int = 5,
    hesap_per_musteri: int = 2,
    islem_per_hesap: int = 10,
    kredi_per_musteri: int = 1,
    seed: int = None
) -> dict:
    """FK bütünlüklü ilişkisel bankacılık veri seti üretir."""
    if seed is not None:
        random.seed(seed)

    musteriler = []
    hesaplar   = []
    islemler   = []
    krediler   = []
    kartlar    = []

    for i in range(musteri_count):
        m = MusteriFactory()
        musteriler.append(m)

        for j in range(hesap_per_musteri):
            h = HesapFactory()
            h['musteri_no'] = m['musteri_no']
            hesaplar.append(h)

            for k in range(islem_per_hesap):
                t = IslemFactory()
                t['kaynak_hesap'] = h['hesap_no']
                t['kaynak_iban']  = h['iban']
                islemler.append(t)

            if j == 0:
                kart = KartFactory()
                kart['hesap_no']   = h['hesap_no']
                kart['musteri_no'] = m['musteri_no']
                kartlar.append(kart)

        for _ in range(kredi_per_musteri):
            kr = KrediFactory()
            kr['musteri_no'] = m['musteri_no']
            krediler.append(kr)

    return {
        'musteri':  musteriler,
        'hesap':    hesaplar,
        'islem':    islemler,
        'kredi':    krediler,
        'kart':     kartlar,
        'meta': {
            'musteri_count': len(musteriler),
            'hesap_count':   len(hesaplar),
            'islem_count':   len(islemler),
            'kredi_count':   len(krediler),
            'kart_count':    len(kartlar),
        }
    }
