"""
TestwrightAI Banking — Rule-Based Schema-Aware Generator
Generates test data that matches real DB column names/types.
Used as fallback when no LLM API key is available.
"""
import random
import string
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from banking.generators.identity    import generate_tc_kimlik, generate_vkn
from banking.generators.account     import generate_tr_iban, TR_BANK_CODES
from banking.generators.card        import generate_card_number, generate_cvv, generate_card_expiry
from banking.generators.transaction import generate_eft_reference, DOVIZ_KURLAR

# ── Static lookup data ────────────────────────────────────────────────────
TR_NAMES_M  = ['Ahmet','Mehmet','Ali','Mustafa','Hasan','Hüseyin','İbrahim','Ömer',
               'Emre','Burak','Serkan','Murat','Oğuzhan','Furkan','Kerem']
TR_NAMES_F  = ['Fatma','Ayşe','Emine','Hatice','Zeynep','Elif','Büşra','Merve',
               'Selin','Özge','Derya','Gizem','Esra','Pınar','Ceren']
TR_SURNAMES = ['Yılmaz','Kaya','Demir','Şahin','Çelik','Yıldız','Yıldırım',
               'Öztürk','Arslan','Doğan','Koç','Aydın','Aslan','Çetin','Kılıç',
               'Özdemir','Yalçın','Uçar','Güneş','Karahan']
TR_CITIES   = ['İstanbul','Ankara','İzmir','Bursa','Antalya','Adana','Konya',
               'Gaziantep','Mersin','Kayseri','Eskişehir','Samsun','Denizli']
TR_SECTORS  = ['Bankacılık','Perakende','İnşaat','Üretim','Teknoloji','Sağlık',
               'Eğitim','Turizm','Lojistik','Enerji','Fintech','Sigorta']
TR_COMPANIES= ['Yıldız Holding A.Ş.','Koç Grubu A.Ş.','Sabancı Holding A.Ş.',
               'Eczacıbaşı A.Ş.','Alarko Holding A.Ş.','Cengiz Holding A.Ş.',
               'Limak Holding A.Ş.','Borusan A.Ş.','Doğuş Holding A.Ş.']
TR_TAX_OFFICES = ['Kadıköy VD','Beşiktaş VD','Bağcılar VD','Keçiören VD',
                  'Karşıyaka VD','Nilüfer VD','Muratpaşa VD','Meram VD']
TR_BANKS    = ['Ziraat Bankası','Halkbank','Yapı Kredi','Akbank','Vakıfbank',
               'Garanti BBVA','İş Bankası','TEB','ING Bank','Denizbank']
TR_STREETS  = ['Atatürk Cad.','İnönü Sok.','Cumhuriyet Bulv.','Bağımsızlık Cad.',
               'Fatih Sultan Mehmet Bulv.','Vatan Cad.','Millet Cad.']
HESAP_TURLERI  = ['Vadesiz','Vadeli','Tasarruf','Mevduat','Yatırım','Döviz']
KREDI_TURLERI  = ['Konut','Taşıt','İhtiyaç','Ticari','KOBİ','Bireysel','Rotatif']
ISLEM_TURLERI  = ['EFT','FAST','Havale','ATM Çekim','POS','Online Ödeme','Otomatik Ödeme']
KART_TURLERI   = ['troy','visa','mastercard','visa_debit','troy_debit']
CURRENCIES     = ['TRY','TRY','TRY','USD','EUR','GBP']  # TRY weighted
DURUM          = {
    'hesap':  ['AKTIF','AKTIF','AKTIF','PASIF','DONDURULMUŞ'],
    'kredi':  ['AKTIF','AKTIF','KAPALI','TEMERRÜT','YENİDEN_YAPILANDIRILMIŞ'],
    'kart':   ['AKTIF','AKTIF','AKTIF','PASIF','BLOKE'],
    'islem':  ['TAMAMLANDI','TAMAMLANDI','TAMAMLANDI','BEKLEMEDE','İPTAL'],
}
SEGMENTS    = ['Temel','Bireysel','Bireysel','Premium','Özel Bankacılık',
               'Mikro','KOBİ','Kurumsal']


def _ascii_name(s: str) -> str:
    """Convert Turkish name to ASCII for email generation."""
    s = unicodedata.normalize('NFKD', s.lower())
    return ''.join(c for c in s if c.isascii() and c.isalpha())


def _rand_date(years_back: int = 5, years_forward: int = 0) -> str:
    start = datetime.now() - timedelta(days=years_back * 365)
    end   = datetime.now() + timedelta(days=years_forward * 365)
    d = start + timedelta(days=random.randint(0, (end - start).days))
    return d.strftime('%Y-%m-%d')


def _rand_ts(days_back: int = 365) -> str:
    t = datetime.now() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return t.strftime('%Y-%m-%d %H:%M:%S')


def _generate_value(col, context: dict) -> Any:
    """Generate a single value for a column given its generator hint."""
    g   = col.get('generator', 'text') if isinstance(col, dict) else col.generator
    nm  = (col.get('name','') if isinstance(col, dict) else col.name).lower()
    tp  = (col.get('type','TEXT') if isinstance(col, dict) else col.col_type).upper()
    tbl = context.get('table_name', '').lower()
    pools = context.get('id_pools', {})

    # PK — autoincrement
    is_pk = col.get('is_pk', False) if isinstance(col, dict) else col.is_pk
    if is_pk:
        return context.get('_row_idx', 0) + 1

    # FK reference
    if g == 'fk_ref':
        ft = col.get('fk_table') if isinstance(col, dict) else col.fk_table
        pool = pools.get(ft, [])
        return random.choice(pool) if pool else 1

    # ── Identity ────────────────────────────────────────────────────────────
    if g == 'tc_kimlik':  return generate_tc_kimlik()
    if g == 'vkn':        return generate_vkn()

    # ── IBAN / Card ──────────────────────────────────────────────────────────
    if g == 'iban':
        bc = random.choice(list(TR_BANK_CODES.keys()))
        return generate_tr_iban(bc)
    if g == 'card_number':
        ct = random.choice(['troy','visa','mastercard'])
        context.setdefault('_card_type', ct)
        return generate_card_number(ct)
    if g == 'cvv':     return generate_cvv()
    if g == 'card_expiry': return generate_card_expiry()

    # ── Personal ─────────────────────────────────────────────────────────────
    if g == 'gender':
        v = random.choice(['E','K'])
        context['_gender'] = v
        return v
    if g == 'first_name':
        gender = context.get('_gender', random.choice(['E','K']))
        v = random.choice(TR_NAMES_M if gender == 'E' else TR_NAMES_F)
        context['_first_name'] = v
        return v
    if g == 'last_name':
        v = random.choice(TR_SURNAMES)
        context['_last_name'] = v
        return v
    if g == 'birth_date': return _rand_date(years_back=70, years_forward=-18)
    if g == 'phone':
        pfx = random.choice(['532','533','535','537','538','542','505','506'])
        return '+90' + pfx + ''.join(str(random.randint(0,9)) for _ in range(7))
    if g == 'email':
        fn = _ascii_name(context.get('_first_name', 'test'))
        ln = _ascii_name(context.get('_last_name',  'user'))
        domain = random.choice(['gmail.com','hotmail.com','yahoo.com','outlook.com'])
        return f"{fn}.{ln}{random.randint(1,99)}@{domain}"
    if g == 'address':
        no = random.randint(1, 200)
        st = random.choice(TR_STREETS)
        return f"{no} {st} No:{random.randint(1,50)}"
    if g == 'city': return random.choice(TR_CITIES)
    if g == 'country': return 'Türkiye'

    # ── Financial ────────────────────────────────────────────────────────────
    if g == 'balance':     return round(random.uniform(0, 500_000), 2)
    if g == 'amount':      return round(random.uniform(50, 25_000), 2)
    if g == 'credit_limit':
        return round(random.choice([5_000,10_000,15_000,20_000,25_000,50_000,100_000]), 2)
    if g == 'used_limit':
        limit = context.get('_credit_limit', 10_000)
        return round(random.uniform(0, limit * 0.9), 2)
    if g == 'interest_rate': return round(random.uniform(28.0, 55.0), 2)
    if g == 'income':      return round(random.uniform(7_500, 200_000), 2)
    if g == 'debt_amount': return round(random.uniform(0, 500_000), 2)
    if g == 'installment': return round(random.uniform(500, 15_000), 2)
    if g == 'term_months': return random.choice([6,12,18,24,36,48,60,120])
    if g == 'small_int':   return random.randint(0, 48)
    if g == 'employee_count': return random.choice([5,10,25,50,100,250,500,1000,5000])
    if g == 'risk_score':
        return random.randint(300, 850)   # Türk bankacılık kredi skoru aralığı
    if g == 'exchange_rate':
        base_rate = DOVIZ_KURLAR.get('USD/TRY', 34.5)
        return round(base_rate * random.uniform(0.97, 1.03), 4)

    # ── Reference ────────────────────────────────────────────────────────────
    if g == 'reference_no':
        bc = random.choice(list(TR_BANK_CODES.keys()))
        return generate_eft_reference(bc)
    if g == 'swift_code':
        from banking.generators.account import TR_SWIFT_CODES
        return random.choice(list(TR_SWIFT_CODES.values()))

    # ── Date/Time ────────────────────────────────────────────────────────────
    if g == 'past_date':         return _rand_date(years_back=5)
    if g == 'future_date':       return _rand_date(years_back=0, years_forward=30)
    if g == 'transaction_date':  return _rand_ts(days_back=365)
    if g == 'date':              return _rand_date(years_back=3)

    # ── Flags/Enum ───────────────────────────────────────────────────────────
    if g == 'bool_flag':     return random.choice([0, 1])
    if g == 'temerrut_flag': return random.choices([0, 1], weights=[92, 8])[0]
    if g == 'segment':       return random.choice(SEGMENTS)
    if g == 'status':
        for key, vals in DURUM.items():
            if key in tbl:
                return random.choice(vals)
        return random.choice(['AKTIF', 'PASIF'])
    if g == 'type_enum':
        if 'hesap' in tbl:  return random.choice(HESAP_TURLERI)
        if 'kredi' in tbl:  return random.choice(KREDI_TURLERI)
        if 'islem' in tbl:  return random.choice(ISLEM_TURLERI)
        if 'kart'  in tbl:  return random.choice(KART_TURLERI)
        return 'GENEL'
    if g == 'currency':  return random.choice(CURRENCIES)

    # ── Corporate ────────────────────────────────────────────────────────────
    if g == 'company_name': return random.choice(TR_COMPANIES)
    if g == 'sector':       return random.choice(TR_SECTORS)
    if g == 'tax_office':   return random.choice(TR_TAX_OFFICES)
    if g == 'bank_name':    return random.choice(TR_BANKS)
    if g == 'bank_code':    return random.choice(list(TR_BANK_CODES.keys()))
    if g == 'description':
        descs = ['Maaş ödemesi','Fatura ödemesi','Market alışverişi',
                 'Kredi taksiti','EFT transferi','Yatırım geri dönüşü',
                 'Kira ödemesi','Sigorta primi']
        return random.choice(descs)

    # ── Int / fallback ───────────────────────────────────────────────────────
    if g == 'int':
        if 'sayisi' in nm or 'count' in nm or 'adet' in nm:
            return random.randint(1, 100)
        return random.randint(1, 9999)

    base_type = tp.split('(')[0]
    if base_type in ('INTEGER','INT','BIGINT','SMALLINT'):
        return random.randint(1, 9999)
    if base_type in ('DECIMAL','NUMERIC','REAL','FLOAT','DOUBLE'):
        return round(random.uniform(0, 10_000), 2)
    if base_type in ('DATE',):
        return _rand_date(3)
    if base_type in ('DATETIME','TIMESTAMP'):
        return _rand_ts(365)
    if base_type in ('BOOLEAN','TINYINT'):
        return random.choice([0, 1])

    # Final fallback: random uppercase string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class SchemaAwareGenerator:
    """Generates test data for all tables in a DB schema respecting FK order."""

    def __init__(self, schema_dict: dict, seed: Optional[int] = None):
        self.schema = schema_dict
        if seed is not None:
            random.seed(seed)
        self.id_pools: Dict[str, list] = {}  # table → list of generated PK values

    def generate_for_table(self, table_name: str, count: int = 10) -> List[dict]:
        tdef = self.schema.get(table_name)
        if not tdef:
            return []

        columns    = tdef.get('columns', [])
        pk_columns = tdef.get('pk_columns', [])
        rows = []

        for i in range(count):
            row     = {}
            context = {
                'table_name': table_name,
                'id_pools':   self.id_pools,
                '_row_idx':   i,
            }

            for col in columns:
                col_name = col.get('name', '') if isinstance(col, dict) else col.name
                is_pk    = col.get('is_pk', False) if isinstance(col, dict) else col.is_pk

                if is_pk:
                    row[col_name] = i + 1
                    continue

                val = _generate_value(col, context)
                row[col_name] = val

                # Update context for inter-column dependencies
                gen = col.get('generator','') if isinstance(col, dict) else col.generator
                if gen in ('gender','first_name','last_name','credit_limit'):
                    key_map = {
                        'gender': '_gender',
                        'first_name': '_first_name',
                        'last_name': '_last_name',
                        'credit_limit': '_credit_limit',
                    }
                    context[key_map[gen]] = val

            rows.append(row)

        # Register PKs for FK references
        if pk_columns:
            pk_col = pk_columns[0]
            self.id_pools[table_name] = [r[pk_col] for r in rows if pk_col in r]

        return rows

    def _topo_order(self) -> List[str]:
        visited, order = set(), []
        def visit(n):
            if n in visited or n not in self.schema: return
            visited.add(n)
            tdef = self.schema[n]
            parents = tdef.get('parents', []) if isinstance(tdef, dict) else []
            for p in parents: visit(p)
            order.append(n)
        for n in self.schema: visit(n)
        return order

    def generate_all(self, counts: Dict[str, int]) -> Dict[str, List[dict]]:
        """Generate rows for each table in FK-safe order."""
        order  = self._topo_order()
        result = {}
        for tname in order:
            if tname in counts:
                result[tname] = self.generate_for_table(tname, counts[tname])
        return result
