"""
TestwrightAI — Bankacılık Test Verisi API Route'ları
BDDK/KVKK uyumlu, AI-free, kural tabanlı veri üretimi.
Endpoint prefix: /api/banking
"""
import sys
import os
import random
import json
import csv
import io
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file

# Proje root'u sys.path'e ekle
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CORE_PYTHON = os.path.join(_PROJECT_ROOT, 'core', 'python')
if _CORE_PYTHON not in sys.path:
    sys.path.insert(0, _CORE_PYTHON)

banking_bp = Blueprint('banking', __name__, url_prefix='/api/banking')

# ── Lazy import (banking paketi yüklü değilse graceful degradation) ──────────
try:
    from banking.generators.identity    import generate_tc_kimlik, validate_tc_kimlik, generate_vkn, validate_vkn, generate_tc_kimlik_batch
    from banking.generators.account     import generate_tr_iban, validate_tr_iban, generate_swift, get_bank_list, TR_BANK_CODES
    from banking.generators.card        import generate_card_number, luhn_check, generate_cvv, generate_card_expiry, mask_card_number
    from banking.generators.transaction import generate_eft_reference, generate_fast_reference, generate_doviz_kuru, generate_transaction_date, generate_cek_numarasi, generate_aciklama, generate_merchant, DOVIZ_KURLAR
    from banking.generators.credit      import generate_faiz_orani, generate_kredi_limiti, generate_risk_skoru, classify_segment, generate_aylik_gelir, SEGMENT_KURALLAR, FAIZ_SPREAD, TCMB_POLITIKA_FAIZ
    from banking.factories.banking_factories import generate_banking_data, generate_relational_dataset, FACTORY_MAP
    BANKING_AVAILABLE = True
except ImportError as e:
    BANKING_AVAILABLE = False
    _IMPORT_ERROR = str(e)


def _check_banking():
    if not BANKING_AVAILABLE:
        return jsonify({'ok': False, 'error': f'Banking modülü yüklenemedi: {_IMPORT_ERROR}'}), 503
    return None


# ════════════════════════════════════════════════════════════════════════════
# INFO
# ════════════════════════════════════════════════════════════════════════════

@banking_bp.route('/info', methods=['GET'])
def banking_info():
    """Bankacılık modülü bilgisi ve endpoint listesi."""
    return jsonify({
        'ok': True,
        'module': 'TestwrightAI Banking DataSim',
        'version': '1.0.0',
        'bddk_compliant': True,
        'kvkk_compliant': True,
        'ai_used': False,
        'available': BANKING_AVAILABLE,
        'endpoints': {
            'GET  /api/banking/info':               'Bu endpoint',
            'GET  /api/banking/banks':              'Türk banka listesi',
            'POST /api/banking/tc-kimlik':          'TC Kimlik No üretimi',
            'POST /api/banking/vkn':                'VKN üretimi',
            'POST /api/banking/iban':               'TR IBAN üretimi',
            'POST /api/banking/card':               'Luhn kart no üretimi',
            'POST /api/banking/transaction':        'İşlem verisi üretimi',
            'POST /api/banking/credit':             'Kredi verisi üretimi',
            'POST /api/banking/generate':           'Genel bankacılık verisi (tip seç)',
            'POST /api/banking/multi-table':        'İlişkisel çok tablo üretimi',
            'POST /api/banking/validate':           'Veri doğrulama (TC/VKN/IBAN/Luhn)',
            'POST /api/banking/edge-cases':         'Edge case senaryoları',
            'POST /api/banking/export':             'CSV/JSON export',
        },
        'supported_types': list(FACTORY_MAP.keys()) if BANKING_AVAILABLE else [],
    }), 200


@banking_bp.route('/banks', methods=['GET'])
def get_banks():
    """Türk banka kodu, adı ve SWIFT listesi."""
    err = _check_banking()
    if err: return err
    return jsonify({'ok': True, 'banks': get_bank_list(), 'count': len(get_bank_list())}), 200


# ════════════════════════════════════════════════════════════════════════════
# KİMLİK
# ════════════════════════════════════════════════════════════════════════════

@banking_bp.route('/tc-kimlik', methods=['POST'])
def tc_kimlik_endpoint():
    """TC Kimlik No üretimi ve doğrulama."""
    err = _check_banking()
    if err: return err
    data  = request.get_json() or {}
    count = min(int(data.get('count', 1)), 1000)
    seed  = data.get('seed')
    mode  = data.get('mode', 'generate')   # generate | validate

    if mode == 'validate':
        tc = data.get('tc', '')
        valid = validate_tc_kimlik(str(tc))
        return jsonify({'ok': True, 'tc': tc, 'valid': valid, 'reason': 'Geçerli' if valid else 'Algoritma doğrulaması başarısız'}), 200

    batch = generate_tc_kimlik_batch(count, seed=seed)
    return jsonify({'ok': True, 'count': len(batch), 'data': batch, 'algorithm': 'Mod-10 (11 hane)', 'bddk_note': 'Algoritmik üretim - gerçek kimlik değil'}), 200


@banking_bp.route('/vkn', methods=['POST'])
def vkn_endpoint():
    """VKN üretimi ve doğrulama."""
    err = _check_banking()
    if err: return err
    data  = request.get_json() or {}
    count = min(int(data.get('count', 1)), 1000)
    seed  = data.get('seed')
    mode  = data.get('mode', 'generate')

    if mode == 'validate':
        vkn = data.get('vkn', '')
        valid = validate_vkn(str(vkn))
        return jsonify({'ok': True, 'vkn': vkn, 'valid': valid}), 200

    if seed is not None:
        random.seed(seed)
    batch = [generate_vkn() for _ in range(count)]
    return jsonify({'ok': True, 'count': len(batch), 'data': batch, 'algorithm': '10 hane - yerleşik checksum'}), 200


# ════════════════════════════════════════════════════════════════════════════
# HESAP
# ════════════════════════════════════════════════════════════════════════════

@banking_bp.route('/iban', methods=['POST'])
def iban_endpoint():
    """TR IBAN üretimi ve doğrulama."""
    err = _check_banking()
    if err: return err
    data      = request.get_json() or {}
    count     = min(int(data.get('count', 1)), 1000)
    bank_code = data.get('bank_code')
    seed      = data.get('seed')
    mode      = data.get('mode', 'generate')

    if mode == 'validate':
        iban = data.get('iban', '')
        valid = validate_tr_iban(str(iban))
        return jsonify({'ok': True, 'iban': iban, 'valid': valid, 'standard': 'ISO 13616 MOD-97-10'}), 200

    if seed is not None:
        random.seed(seed)
    ibans = [generate_tr_iban(bank_code) for _ in range(count)]
    swift = generate_swift(bank_code)
    return jsonify({
        'ok': True, 'count': len(ibans), 'data': ibans,
        'bank_code': bank_code or 'random',
        'bank_name': TR_BANK_CODES.get(bank_code, 'Rastgele') if bank_code else 'Rastgele',
        'swift': swift,
        'standard': 'ISO 13616, TR format: TR + 2 check + 5 banka + 1 rezerv + 16 hesap = 26'
    }), 200


# ════════════════════════════════════════════════════════════════════════════
# KART
# ════════════════════════════════════════════════════════════════════════════

@banking_bp.route('/card', methods=['POST'])
def card_endpoint():
    """Luhn geçerli kart numarası üretimi."""
    err = _check_banking()
    if err: return err
    data      = request.get_json() or {}
    count     = min(int(data.get('count', 1)), 1000)
    card_type = data.get('card_type', 'troy')
    masked    = data.get('masked', False)
    seed      = data.get('seed')

    if seed is not None:
        random.seed(seed)

    cards = []
    for _ in range(count):
        no  = generate_card_number(card_type)
        cvv = generate_cvv(card_type)
        exp = generate_card_expiry()
        cards.append({
            'number':  mask_card_number(no) if masked else no,
            'cvv':     cvv,
            'expiry':  exp,
            'type':    card_type,
            'valid':   luhn_check(no),
        })

    return jsonify({
        'ok': True, 'count': len(cards), 'data': cards,
        'algorithm': 'Luhn (ISO/IEC 7812)',
        'prefix_info': {'troy': '9792xx', 'visa': '4xxxxx', 'mastercard': '51-55xxxx'}
    }), 200


# ════════════════════════════════════════════════════════════════════════════
# İŞLEM
# ════════════════════════════════════════════════════════════════════════════

@banking_bp.route('/transaction', methods=['POST'])
def transaction_endpoint():
    """Bankacılık işlem verisi üretimi."""
    err = _check_banking()
    if err: return err
    data      = request.get_json() or {}
    count     = min(int(data.get('count', 10)), 5000)
    islem_turu = data.get('islem_turu')
    seed      = data.get('seed')

    turu_list = ['EFT', 'Havale', 'FAST', 'POS', 'ATM', 'Faiz', 'Masraf']
    if seed is not None:
        random.seed(seed)

    islemler = []
    for _ in range(count):
        turu = islem_turu or random.choice(turu_list)
        islemler.append({
            'referans_no': generate_eft_reference(),
            'islem_turu':  turu,
            'tutar':       round(random.uniform(1, 50000), 2),
            'para_birimi': random.choice(['TRY', 'TRY', 'TRY', 'USD', 'EUR']),
            'aciklama':    generate_aciklama(turu),
            'tarih':       generate_transaction_date(),
            'durum':       random.choice(['Tamamlandı','Tamamlandı','Tamamlandı','Beklemede','İptal']),
            'isyeri':      generate_merchant() if turu == 'POS' else None,
        })

    return jsonify({'ok': True, 'count': len(islemler), 'data': islemler}), 200


# ════════════════════════════════════════════════════════════════════════════
# KREDİ
# ════════════════════════════════════════════════════════════════════════════

@banking_bp.route('/credit', methods=['POST'])
def credit_endpoint():
    """Kredi verisi üretimi."""
    err = _check_banking()
    if err: return err
    data      = request.get_json() or {}
    count     = min(int(data.get('count', 5)), 1000)
    kredi_turu = data.get('kredi_turu', 'ihtiyac_kredisi')
    seed      = data.get('seed')

    if seed is not None:
        random.seed(seed)

    krediler = []
    for i in range(count):
        gelir   = round(random.uniform(5000, 80000), 2)
        segment = classify_segment(gelir)
        risk    = generate_risk_skoru(segment)
        yas     = random.randint(22, 65)
        limit   = generate_kredi_limiti(gelir, segment, yas, risk)
        faiz    = generate_faiz_orani(kredi_turu)
        vade    = random.randint(6, 120)

        krediler.append({
            'kredi_no':          f"KRD{i+1:010d}",
            'kredi_turu':        kredi_turu,
            'anapara':           round(random.uniform(limit * 0.1, limit), 2),
            'faiz_orani':        faiz,
            'vade_ay':           vade,
            'aylik_taksit':      round((limit * (faiz/100/12)) / (1 - (1 + faiz/100/12)**(-vade)), 2),
            'musteri_gelir':     gelir,
            'musteri_segment':   segment,
            'risk_skoru':        risk,
            'tcmb_politika_faiz': TCMB_POLITIKA_FAIZ,
            'durum':             random.choice(['Aktif','Aktif','Aktif','Kapalı','Gecikme']),
        })

    return jsonify({'ok': True, 'count': len(krediler), 'data': krediler}), 200


# ════════════════════════════════════════════════════════════════════════════
# GENEL ÜRETİM
# ════════════════════════════════════════════════════════════════════════════

@banking_bp.route('/generate', methods=['POST'])
def banking_generate():
    """Genel bankacılık veri üretimi (tip parametreli)."""
    err = _check_banking()
    if err: return err
    data        = request.get_json() or {}
    entity_type = data.get('entity_type', 'musteri')
    count       = min(int(data.get('count', 10)), 1000)
    seed        = data.get('seed')

    if entity_type not in FACTORY_MAP:
        return jsonify({
            'ok': False,
            'error': f"Geçersiz entity_type: '{entity_type}'",
            'valid_types': list(FACTORY_MAP.keys())
        }), 400

    rows = generate_banking_data(entity_type, count, seed)
    # dict içindeki datetime/date nesnelerini stringe çevir
    def serialize(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return str(obj)

    serialized = []
    for row in rows:
        serialized.append({k: (serialize(v) if not isinstance(v, (str, int, float, bool, type(None))) else v) for k, v in row.items()})

    return jsonify({
        'ok': True,
        'entity_type': entity_type,
        'count': len(serialized),
        'columns': list(serialized[0].keys()) if serialized else [],
        'data': serialized,
        'bddk_compliant': True,
    }), 200


# ════════════════════════════════════════════════════════════════════════════
# İLİŞKİSEL ÇOK TABLO
# ════════════════════════════════════════════════════════════════════════════

@banking_bp.route('/multi-table', methods=['POST'])
def multi_table():
    """FK bütünlüklü ilişkisel bankacılık veri seti üretimi."""
    err = _check_banking()
    if err: return err
    data = request.get_json() or {}

    musteri_count      = min(int(data.get('musteri_count', 3)), 200)
    hesap_per_musteri  = min(int(data.get('hesap_per_musteri', 2)), 10)
    islem_per_hesap    = min(int(data.get('islem_per_hesap', 5)), 50)
    kredi_per_musteri  = min(int(data.get('kredi_per_musteri', 1)), 5)
    seed               = data.get('seed')

    dataset = generate_relational_dataset(
        musteri_count=musteri_count,
        hesap_per_musteri=hesap_per_musteri,
        islem_per_hesap=islem_per_hesap,
        kredi_per_musteri=kredi_per_musteri,
        seed=seed,
    )

    def serialize_dataset(ds):
        result = {}
        for key, rows in ds.items():
            if key == 'meta':
                result[key] = rows
                continue
            serialized = []
            for row in rows:
                serialized.append({
                    k: (v.isoformat() if hasattr(v, 'isoformat') else v)
                    for k, v in row.items()
                })
            result[key] = serialized
        return result

    return jsonify({
        'ok': True,
        'meta': dataset['meta'],
        'dataset': serialize_dataset(dataset),
        'fk_integrity': True,
        'bddk_compliant': True,
    }), 200


# ════════════════════════════════════════════════════════════════════════════
# DOĞRULAMA
# ════════════════════════════════════════════════════════════════════════════

@banking_bp.route('/validate', methods=['POST'])
def validate_endpoint():
    """TC Kimlik, VKN, IBAN, Kart No doğrulama."""
    err = _check_banking()
    if err: return err
    data      = request.get_json() or {}
    value     = str(data.get('value', ''))
    data_type = data.get('type', 'auto')

    results = {}

    if data_type in ('auto', 'tc_kimlik'):
        results['tc_kimlik'] = {'valid': validate_tc_kimlik(value), 'algorithm': 'Mod-10 (11 hane)'}

    if data_type in ('auto', 'vkn'):
        results['vkn'] = {'valid': validate_vkn(value), 'algorithm': 'Checksum (10 hane)'}

    if data_type in ('auto', 'iban'):
        results['iban'] = {'valid': validate_tr_iban(value), 'standard': 'ISO 13616 MOD-97-10'}

    if data_type in ('auto', 'luhn'):
        results['luhn'] = {'valid': luhn_check(value.replace(' ', '')), 'standard': 'ISO/IEC 7812'}

    best_match = next((t for t, r in results.items() if r['valid']), None)

    return jsonify({
        'ok': True,
        'value': value,
        'type_requested': data_type,
        'results': results,
        'best_match': best_match,
    }), 200


# ════════════════════════════════════════════════════════════════════════════
# EDGE CASE SENARYOLARI
# ════════════════════════════════════════════════════════════════════════════

@banking_bp.route('/edge-cases', methods=['POST'])
def edge_cases():
    """Bankacılık edge case ve sınır değer senaryoları üretimi."""
    err = _check_banking()
    if err: return err
    data      = request.get_json() or {}
    scenarios = data.get('scenarios', ['all'])

    SCENARIOS = {
        'sifir_bakiye': {
            'description': 'Sıfır bakiyeli hesap — yetersiz bakiye testi',
            'data': {'hesap_no': 'HSP0000000001', 'iban': generate_tr_iban(), 'bakiye': 0.0, 'para_birimi': 'TRY'}
        },
        'maksimum_limit': {
            'description': 'Limit üstü transfer denemesi',
            'data': {'tutar': 9_999_999.99, 'para_birimi': 'TRY', 'aciklama': 'Maksimum limit aşımı testi'}
        },
        'negatif_islem': {
            'description': 'Negatif/iade işlemi',
            'data': {'tutar': -500.00, 'islem_turu': 'İade', 'aciklama': 'POS iade - 3 gün içinde'}
        },
        'yabanci_musteri': {
            'description': 'Yabancı uyruklu müşteri — pasaport ile',
            'data': {
                'kimlik_tipi': 'PASAPORT',
                'kimlik_no': f"P{''.join([str(random.randint(0,9)) for _ in range(7)])}",
                'uyruk': random.choice(['DE', 'GB', 'US', 'NL', 'FR']),
                'tc_kimlik': None
            }
        },
        'tuzel_kisi': {
            'description': 'Tüzel kişi — VKN ile, TC yok',
            'data': {'kimlik_tipi': 'VKN', 'vkn': generate_vkn(), 'tc_kimlik': None, 'segment': 'KOBİ'}
        },
        'artik_yil': {
            'description': '29 Şubat doğum tarihi edge case',
            'data': {'dogum_tarihi': '2000-02-29', 'tc_kimlik': generate_tc_kimlik(), 'not': '2025 yılında yaş hesabı: 28 Şubat mı yoksa 1 Mart mı?'}
        },
        'yil_sonu': {
            'description': 'Yıl sonu kapanış işlemi',
            'data': {'tarih': '2025-12-31T23:59:59', 'islem_turu': 'Yıl Sonu Kapanış', 'tutar': round(random.uniform(100, 10000), 2)}
        },
        'doviz_cevrim': {
            'description': 'USD→TRY döviz çevrim işlemi',
            'data': {
                'kaynak_para_birimi': 'USD',
                'hedef_para_birimi': 'TRY',
                'tutar_usd': round(random.uniform(100, 5000), 2),
                'kur': generate_doviz_kuru('USD', 'TRY'),
                'islem_turu': 'Döviz Alım-Satım'
            }
        },
        'temerrut': {
            'description': 'Temerrüt müşteri senaryosu',
            'data': {
                'tc_kimlik': generate_tc_kimlik(),
                'risk_skoru': generate_risk_skoru('Temel', temerrut=True),
                'gecikme_gun': random.randint(30, 180),
                'segment': 'Temel',
                'kredi_durumu': 'Gecikme'
            }
        },
    }

    if 'all' in scenarios:
        result = SCENARIOS
    else:
        result = {k: SCENARIOS[k] for k in scenarios if k in SCENARIOS}

    return jsonify({
        'ok': True,
        'count': len(result),
        'scenarios': result,
        'available_scenarios': list(SCENARIOS.keys()),
    }), 200


# ════════════════════════════════════════════════════════════════════════════
# EXPORT
# ════════════════════════════════════════════════════════════════════════════

@banking_bp.route('/export', methods=['POST'])
def export_data():
    """Üretilen veriyi CSV veya JSON olarak indir."""
    err = _check_banking()
    if err: return err
    data        = request.get_json() or {}
    entity_type = data.get('entity_type', 'musteri')
    count       = min(int(data.get('count', 100)), 5000)
    fmt         = data.get('format', 'json')
    seed        = data.get('seed')

    rows = generate_banking_data(entity_type, count, seed)

    def serialize(v):
        if hasattr(v, 'isoformat'):
            return v.isoformat()
        return v

    serialized = [{k: serialize(v) for k, v in row.items()} for row in rows]

    if fmt == 'csv':
        if not serialized:
            return jsonify({'ok': False, 'error': 'Veri yok'}), 400
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=serialized[0].keys())
        writer.writeheader()
        writer.writerows(serialized)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'banking_{entity_type}_{count}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )

    return send_file(
        io.BytesIO(json.dumps(serialized, ensure_ascii=False, indent=2).encode('utf-8')),
        mimetype='application/json',
        as_attachment=True,
        download_name=f'banking_{entity_type}_{count}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )


# ════════════════════════════════════════════════════════════════════════════
# DB ŞEMA OKUMA + AI VERİ ÜRETİMİ
# ════════════════════════════════════════════════════════════════════════════

import sqlite3 as _sqlite3

_PROJECT_DB_ROOT = os.path.join(_PROJECT_ROOT, 'data')
_DEMO_DB_PATH = os.path.join(_PROJECT_DB_ROOT, 'demo_banking.sqlite')

# Oturum bazlı DB bağlantı cache (basit in-memory)
_db_connections: dict = {}


def _get_schema_reader(db_type: str, conn_str: str):
    """SchemaReader instance döner (lazy import)."""
    from banking.db_schema_reader import SchemaReader
    return SchemaReader(db_type=db_type, conn_str=conn_str)


@banking_bp.route('/db/providers', methods=['GET'])
def list_llm_providers():
    """Kullanılabilir LLM sağlayıcıları listele (Anthropic, OpenAI, Ollama)."""
    try:
        from banking.ai_data_generator import AIDataGenerator
        providers = AIDataGenerator.get_available_providers()
        active = next((p for p, info in providers.items() if info['available']), None)
        return jsonify({'ok': True, 'providers': providers, 'active': active}), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@banking_bp.route('/db/connections', methods=['GET'])
def list_db_connections():
    """Kullanılabilir DB bağlantılarını listele (demo dahil)."""
    connections = [
        {
            'id':       'demo',
            'label':    '🏦 Demo Bankacılık DB (SQLite)',
            'db_type':  'sqlite',
            'conn_str': _DEMO_DB_PATH,
            'built_in': True,
            'description': '7 tablolu Türk bankacılık şeması — MUSTERILER, HESAPLAR, ISLEMLER, KREDILER, KARTLAR, KURUMSAL_MUSTERILER, DOVIZ_ISLEMLERI',
        }
    ]
    # Kullanıcının kaydettiği bağlantılar
    for cid, info in _db_connections.items():
        connections.append({
            'id':       cid,
            'label':    info.get('label', cid),
            'db_type':  info.get('db_type'),
            'built_in': False,
            'description': f"{info.get('db_type','?')} — {info.get('conn_str','?')[:60]}",
        })
    return jsonify({'ok': True, 'connections': connections}), 200


@banking_bp.route('/db/connect', methods=['POST'])
def db_connect():
    """
    Bir DB'ye bağlan ve şemasını oku.
    Body: {db_type:'sqlite'|'postgresql'|'mysql', conn_str:'...', label:'...'}
    Özel: {db_type:'demo'} → demo SQLite'ı kullan
    """
    data     = request.get_json() or {}
    db_type  = data.get('db_type', 'demo')
    conn_str = data.get('conn_str', '')
    label    = data.get('label', '')

    if db_type == 'demo':
        db_type  = 'sqlite'
        conn_str = _DEMO_DB_PATH
        label    = '🏦 Demo Bankacılık DB'

    if not conn_str:
        return jsonify({'ok': False, 'error': 'conn_str zorunlu'}), 400

    try:
        reader = _get_schema_reader(db_type, conn_str)
        reader.connect()
        tables     = reader.read_schema()
        schema_dict = reader.schema_to_dict(tables)
        schema_ddl  = reader.schema_to_ddl(tables)
        topo_order  = reader.topological_order(tables)
        reader.disconnect()

        conn_id = f"conn_{len(_db_connections)+1}"
        _db_connections[conn_id] = {
            'db_type':  db_type,
            'conn_str': conn_str,
            'label':    label or conn_id,
        }

        # Default counts: 10 rows per table
        default_counts = {t: 10 for t in topo_order}

        return jsonify({
            'ok':            True,
            'conn_id':       conn_id,
            'label':         label or conn_id,
            'db_type':       db_type,
            'schema':        schema_dict,
            'schema_ddl':    schema_ddl,
            'table_order':   topo_order,
            'table_count':   len(topo_order),
            'default_counts': default_counts,
        }), 200

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@banking_bp.route('/db/analyze', methods=['POST'])
def db_analyze_schema():
    """
    LLM ile şemayı analiz et, iş kurallarını çıkar.
    Body: {schema_ddl:'...', schema_dict:{...}}
    """
    data       = request.get_json() or {}
    schema_ddl = data.get('schema_ddl', '')
    schema_dict = data.get('schema_dict', {})

    if not schema_ddl:
        return jsonify({'ok': False, 'error': 'schema_ddl zorunlu'}), 400

    try:
        from banking.ai_data_generator import AIDataGenerator
        gen      = AIDataGenerator()
        analysis = gen.analyze_schema(schema_ddl)
        return jsonify({
            'ok':       True,
            'has_llm':  gen.has_llm,
            'model':    gen.model,
            'provider': gen.provider,
            'analysis': analysis,
        }), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@banking_bp.route('/db/ai-generate', methods=['POST'])
def db_ai_generate():
    """
    Şema + LLM analizi kullanarak test verisi üret.
    Body: {
        schema_dict: {...},   -- /db/connect'ten gelen
        schema_ddl:  '...',
        counts:      {TABLO: N, ...},
        extra_rules: '...',   -- opsiyonel ek iş kuralları
        analysis:    {...},   -- opsiyonel, /db/analyze'dan
        seed:        42,      -- opsiyonel deterministik seed
    }
    """
    data        = request.get_json() or {}
    schema_dict    = data.get('schema_dict', {})
    schema_ddl     = data.get('schema_ddl', '')
    counts         = data.get('counts', {})
    extra_rules    = data.get('extra_rules', '')
    analysis       = data.get('analysis')
    seed           = data.get('seed')
    preferred_model = data.get('model')  # Ollama model seçimi

    if not schema_dict:
        return jsonify({'ok': False, 'error': 'schema_dict zorunlu'}), 400
    if not counts:
        counts = {t: 10 for t in schema_dict.keys()}

    # Sınırla (aşırı yük önle)
    counts = {t: min(int(n), 100) for t, n in counts.items()}

    try:
        from banking.ai_data_generator import AIDataGenerator
        gen = AIDataGenerator(preferred_model=preferred_model)
        result = gen.generate(
            schema_dict=schema_dict,
            schema_ddl=schema_ddl,
            counts=counts,
            extra_rules=extra_rules,
            analysis=analysis,
            seed=seed,
        )

        # Build meta
        meta = {t: len(rows) for t, rows in result['data'].items()}

        return jsonify({
            'ok':      True,
            'method':  result['method'],
            'model':   result.get('model'),
            'message': result.get('message', ''),
            'analysis': result.get('analysis', {}),
            'dataset': result['data'],
            'meta':    meta,
        }), 200

    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'trace': traceback.format_exc()[-500:]}), 500


@banking_bp.route('/db/insert', methods=['POST'])
def db_insert():
    """
    Üretilen veriyi hedef DB'ye INSERT et.
    Body: {
        db_type:  'sqlite',
        conn_str: '...',
        dataset:  {TABLO: [rows...]},
        table_order: [...],   -- insert sırası (FK uyumu için)
        truncate_first: false
    }
    """
    data        = request.get_json() or {}
    db_type     = data.get('db_type', 'demo')
    conn_str    = data.get('conn_str', '')
    dataset     = data.get('dataset', {})
    table_order = data.get('table_order', list(dataset.keys()))
    truncate    = data.get('truncate_first', False)

    if db_type == 'demo':
        db_type  = 'sqlite'
        conn_str = _DEMO_DB_PATH

    if not dataset:
        return jsonify({'ok': False, 'error': 'dataset boş'}), 400

    try:
        if db_type == 'sqlite':
            conn = _sqlite3.connect(conn_str)
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            insert_counts = {}
            errors = []

            for tname in table_order:
                rows = dataset.get(tname, [])
                if not rows:
                    continue

                if truncate:
                    try:
                        cursor.execute(f"DELETE FROM `{tname}`")
                    except Exception as e:
                        errors.append(f"TRUNCATE {tname}: {e}")

                cols     = [k for k in rows[0].keys()]
                placeholders = ','.join(['?' for _ in cols])
                sql = f"INSERT OR IGNORE INTO `{tname}` ({','.join(cols)}) VALUES ({placeholders})"

                inserted = 0
                for row in rows:
                    try:
                        vals = [row.get(c) for c in cols]
                        cursor.execute(sql, vals)
                        inserted += 1
                    except Exception as e:
                        errors.append(f"{tname}: {e}")

                insert_counts[tname] = inserted

            conn.commit()
            conn.close()

            return jsonify({
                'ok':           True,
                'insert_counts': insert_counts,
                'total':        sum(insert_counts.values()),
                'errors':       errors[:10],
            }), 200

        else:
            return jsonify({'ok': False, 'error': f'{db_type} insert henüz desteklenmiyor'}), 400

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@banking_bp.route('/db/query', methods=['POST'])
def db_query():
    """
    DB'de SELECT sorgusu çalıştır (sadece SELECT, güvenlik için).
    Body: {db_type:'sqlite', conn_str:'...', sql:'SELECT ...', limit:100}
    """
    data     = request.get_json() or {}
    db_type  = data.get('db_type', 'demo')
    conn_str = data.get('conn_str', '')
    sql      = data.get('sql', '').strip()
    limit    = min(int(data.get('limit', 50)), 500)

    if db_type == 'demo':
        db_type  = 'sqlite'
        conn_str = _DEMO_DB_PATH

    if not sql.upper().startswith('SELECT'):
        return jsonify({'ok': False, 'error': 'Sadece SELECT sorgusuna izin verilir'}), 400

    try:
        conn = _sqlite3.connect(conn_str)
        conn.row_factory = _sqlite3.Row
        c = conn.cursor()
        c.execute(f"{sql} LIMIT {limit}")
        rows = [dict(r) for r in c.fetchall()]
        cols = [d[0] for d in c.description] if c.description else []
        conn.close()
        return jsonify({'ok': True, 'rows': rows, 'columns': cols, 'count': len(rows)}), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ════════════════════════════════════════════════════════════════════════════
# BLUEPRINT KAYIT
# ════════════════════════════════════════════════════════════════════════════

def register_banking_routes(app):
    app.register_blueprint(banking_bp)
    import logging
    logging.getLogger(__name__).info('Banking routes registered: /api/banking/*')
