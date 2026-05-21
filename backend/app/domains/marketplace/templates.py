"""Banking marketplace — hazır test senaryosu template registry.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §6 / E4.2.

Amaç:
    "EFT", "FAST", "KKB sorgusu", "SWIFT MT103", "Kredi tahsis" gibi
    bankacılık senaryolarının hazır şablon kütüphanesi. TSPM'e tek
    tıkla kopyalanabilir.

Veri modeli:
    * Template: id, kategori, adı, açıklama, gherkin, tags, preconditions,
      sample_data (opsiyonel sentetik veri şeması önerisi)
    * Registry: built-in tuple + DB (opsiyonel DB genişletme).

Bu ilk sprint'te 20 built-in template. DB persist ileride
(``scenario_templates`` tablosu). Router + frontend "gallery" da sonraki.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


# ── Veri modeli ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Template:
    id: str
    category: str                 # "payments" | "credit" | "card" | "kyc" | "reporting"
    name: str
    description: str
    gherkin: str
    tags: Tuple[str, ...] = field(default_factory=tuple)
    preconditions: Tuple[str, ...] = field(default_factory=tuple)
    sample_data_keys: Tuple[str, ...] = field(default_factory=tuple)
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        d = asdict(self)
        # Tuple → list, JSON serialize dostu
        for k in ("tags", "preconditions", "sample_data_keys"):
            d[k] = list(d[k])
        return d


# ── Built-in şablonlar ──────────────────────────────────────────────────


_T = lambda id_, cat, name, desc, g, tags=(), pre=(), data=(): Template(
    id=id_, category=cat, name=name, description=desc, gherkin=g,
    tags=tags, preconditions=pre, sample_data_keys=data,
)


TEMPLATES: Tuple[Template, ...] = (
    # ── Payments ────────────────────────────────────────────────────────
    _T(
        "eft.happy_path",
        "payments",
        "EFT — mutlu yol (aynı gün)",
        "Müşteri kendi hesabından başka bankaya EFT yapar.",
        """\
Senaryo: EFT gönderim mutlu yol
  Given bir müşteri '123' no'lu hesabıyla login olmuş
    And 'EFT' menüsünü açtı
  When alıcı IBAN 'TR00 0000 0000 0000 0000 0001' ve tutar 100,00 TL girilir
    And onay kodu girilir ve gönder butonuna basılır
  Then işlem başarıyla tamamlanır
    And referans numarası gösterilir
    And kaynak hesap bakiyesi 100 TL azalır
""",
        tags=("eft", "payments", "happy-path"),
        pre=("test_user_with_balance_gte_200", "eft_limit_not_exceeded"),
        data=("customer_iban", "beneficiary_iban", "amount"),
    ),
    _T(
        "eft.insufficient_balance",
        "payments",
        "EFT — yetersiz bakiye",
        "Yetersiz bakiye durumunda hata gösterilir.",
        """\
Senaryo: EFT gönderim yetersiz bakiye
  Given bakiyesi 50 TL olan müşteri 'EFT' ekranında
  When 100 TL EFT başlatılır
  Then 'Yetersiz bakiye' hata mesajı gösterilir
    And bakiye değişmez
""",
        tags=("eft", "payments", "negative"),
    ),
    _T(
        "eft.outside_hours",
        "payments",
        "EFT — saat dışı uyarısı",
        "EFT saatleri dışında sistem uyarı gösterir ve saklar.",
        """\
Senaryo: EFT saat dışı bekleyen işlem
  Given saat 18:00'dan sonra müşteri EFT başlatır
  When alıcı IBAN ve tutar girilir
  Then 'Sonraki iş gününde iletilecek' uyarısı gösterilir
    And işlem 'Bekleyen EFT' listesine eklenir
""",
        tags=("eft", "payments", "edge-case"),
    ),
    _T(
        "fast.instant_transfer",
        "payments",
        "FAST — anlık transfer",
        "7/24 FAST transfer başarılı senaryosu.",
        """\
Senaryo: FAST anlık transfer mutlu yol
  Given müşteri FAST ekranında
  When alıcı telefonu veya IBAN'ı ve tutar girilir
  Then 10 saniye içinde 'Başarılı' sonucu döner
    And referans numarası gösterilir
""",
        tags=("fast", "payments", "happy-path"),
    ),
    _T(
        "fast.limit_exceeded",
        "payments",
        "FAST — günlük limit aşıldı",
        "Günlük FAST limiti aşılırsa sistem engeller.",
        """\
Senaryo: FAST günlük limit
  Given müşteri bugün 29.500 TL FAST yaptı
  When 1.000 TL'lik yeni FAST başlatılır
  Then 'Günlük FAST limiti aşıldı' hatası gösterilir
""",
        tags=("fast", "payments", "limits"),
    ),
    _T(
        "swift.mt103_outgoing",
        "payments",
        "SWIFT MT103 — giden transfer",
        "Yurtdışı SWIFT MT103 gönderim.",
        """\
Senaryo: SWIFT MT103 giden transfer
  Given müşteri SWIFT menüsünde
  When alıcı BIC, IBAN, tutar, döviz cinsi girilir
    And masraf paylaşımı 'SHA' seçilir
  Then MT103 mesajı oluşturulur
    And referans ID gösterilir
    And işlem 'İşleniyor' durumuna geçer
""",
        tags=("swift", "mt103", "international"),
        pre=("customer_has_fx_account",),
        data=("beneficiary_bic", "beneficiary_iban", "amount", "currency"),
    ),
    # ── Credit ──────────────────────────────────────────────────────────
    _T(
        "loan.application_approved",
        "credit",
        "Kredi başvurusu — onay",
        "Bireysel kredi başvurusu mutlu yol.",
        """\
Senaryo: Kredi başvurusu onaylanır
  Given uygun kredi skorlu müşteri
  When 50.000 TL 24 ay kredi başvurusu yapılır
  Then ön onay sonucu 5 saniye içinde gösterilir
    And aylık taksit tutarı hesaplanır
    And sözleşme PDF'si oluşturulur
""",
        tags=("loan", "credit", "happy-path"),
        pre=("kkb_score_gte_1500",),
        data=("requested_amount", "term_months", "purpose"),
    ),
    _T(
        "loan.application_rejected_kkb",
        "credit",
        "Kredi başvurusu — KKB red",
        "Düşük KKB skoru nedeniyle reddetme.",
        """\
Senaryo: KKB skoru düşük müşteri reddedilir
  Given KKB skoru 800 olan müşteri
  When 10.000 TL kredi başvurusu yapılır
  Then 'Başvurunuz olumsuz sonuçlandı' mesajı gösterilir
    And red nedeni loglanır (PII maskesiz)
""",
        tags=("loan", "credit", "negative"),
    ),
    _T(
        "kkb.inquiry",
        "credit",
        "KKB sorgulama",
        "Müşteri kendi KKB notunu sorgular.",
        """\
Senaryo: KKB kendi not sorgusu
  Given müşteri '/kkb' menüsünde
  When SMS OTP girilir
  Then müşterinin güncel KKB skoru gösterilir
    And son 6 aydaki sorgu sayısı gösterilir
""",
        tags=("kkb", "credit", "self-service"),
    ),
    # ── Card ────────────────────────────────────────────────────────────
    _T(
        "card.activation",
        "card",
        "Yeni kart aktivasyonu",
        "Gönderilen yeni kartın aktivasyonu.",
        """\
Senaryo: Kart aktivasyonu
  Given müşteri yeni kartını eline aldı
  When son 6 hane ve kimlik no girilir
    And SMS OTP doğrulanır
  Then kart aktif duruma geçer
    And PIN tanımlama ekranı açılır
""",
        tags=("card", "activation"),
    ),
    _T(
        "card.fraud_detected_block",
        "card",
        "Fraud — kart blok",
        "Şüpheli işlem tespitinde kart otomatik bloklanır.",
        """\
Senaryo: Fraud tespiti kart blok
  Given müşteri kartıyla 1 dakika içinde 3 farklı ülkede işlem dener
  When fraud motoru alarmı tetikler
  Then kart 'Geçici blok' statüsüne alınır
    And müşteriye SMS ile bildirim gider
    And müşteri hizmetleri çağrı kaydı oluşturulur
""",
        tags=("card", "fraud", "security"),
        pre=("fraud_engine_enabled",),
    ),
    _T(
        "card.limit_increase_request",
        "card",
        "Kart limit artırım talebi",
        "Müşteri kart limit artırımı ister.",
        """\
Senaryo: Kart limit artırım başvurusu
  Given müşteri kredi kartı yönetimindedir
  When limit artırım talebi oluşturulur
  Then sistem gelir beyanını sorar
    And ön-onay 30 saniye içinde cevap döner
""",
        tags=("card", "limit"),
    ),
    # ── KYC / Account ───────────────────────────────────────────────────
    _T(
        "kyc.video_onboarding",
        "kyc",
        "Video dijital onboarding",
        "Mobil şube video ile hesap açma.",
        """\
Senaryo: Video onboarding mutlu yol
  Given potansiyel müşteri uygulamayı açar
  When kimlik fotoğrafı ve selfie gönderilir
    And video görüşme tamamlanır
  Then hesap 'Aktif' durumuna geçer
    And müşteri numarası atanır
    And hoşgeldin SMS'i gider
""",
        tags=("kyc", "onboarding", "mobile"),
    ),
    _T(
        "kyc.identity_mismatch",
        "kyc",
        "Kimlik uyumsuzluğu — red",
        "NVI doğrulamasında uyumsuzluk.",
        """\
Senaryo: NVI kimlik uyumsuz
  Given müşteri video onboarding başlattı
  When NVI'den dönen isim-soyisim girilenle eşleşmez
  Then başvuru 'Red' statüsüne alınır
    And fraud ekibine ticket açılır
""",
        tags=("kyc", "security"),
    ),
    _T(
        "account.opening_individual",
        "kyc",
        "Bireysel hesap açma",
        "Mevcut müşteriye ek vadesiz TL hesap.",
        """\
Senaryo: Mevcut müşteriye yeni vadesiz hesap
  Given mevcut müşteri login olmuş
  When 'Yeni hesap aç' akışına girer
    And TL vadesiz seçilir
  Then IBAN oluşturulur
    And hesap listesinde görünür
""",
        tags=("account", "onboarding"),
    ),
    # ── Reporting / Compliance ──────────────────────────────────────────
    _T(
        "statement.export_pdf",
        "reporting",
        "Hesap özeti PDF indirme",
        "Son 3 aylık hesap özeti PDF.",
        """\
Senaryo: Hesap özeti PDF indir
  Given müşteri hesap detayında
  When '3 ay' ve 'PDF' seçilir
  Then 10 saniye içinde PDF indirilir
    And PDF'te hesap no + işlemler + bakiye gösterilir
""",
        tags=("reporting", "self-service"),
    ),
    _T(
        "mastb.cbs_reporting",
        "reporting",
        "MASAK — şüpheli işlem bildirimi",
        "Eşik üstü işlemin MASAK'a iletilmesi.",
        """\
Senaryo: MASAK şüpheli işlem oluşur
  Given müşteri tek günde 200.000 TL üzeri nakit çekim yaptı
  When batch akşam çalışır
  Then 'MASAK bildirim' kaydı oluşturulur
    And compliance ekip dashboard'unda görünür
""",
        tags=("compliance", "reporting", "masak"),
    ),
    _T(
        "kvkk.data_subject_request",
        "reporting",
        "KVKK — veri sahibi talep yönetimi",
        "Müşteri KVKK kapsamında verilerinin silinmesini ister.",
        """\
Senaryo: KVKK silme talebi
  Given müşteri '/kvkk/talep' ekranında
  When 'Verilerimin silinmesi' seçilir ve onay verilir
  Then talep ID'si oluşur
    And 15 iş günü içinde yanıt SLA'sı gösterilir
    And compliance ekip ticket'ı oluşur
""",
        tags=("compliance", "kvkk"),
    ),
    # ── Security ────────────────────────────────────────────────────────
    _T(
        "auth.wrong_password_lockout",
        "security",
        "Yanlış şifre — hesap kilitleme",
        "Ardışık 3 yanlış deneme sonrası 30 dk kilit.",
        """\
Senaryo: Ardışık 3 yanlış şifre kilit
  Given müşteri giriş ekranında
  When 3 kez yanlış şifre girilir
  Then hesap 30 dakika kilitlenir
    And 'Kilit açmak için müşteri hizmetleri' mesajı gösterilir
""",
        tags=("security", "auth"),
    ),
    _T(
        "auth.mfa_enrollment",
        "security",
        "MFA — TOTP kayıt",
        "Müşteri TOTP (Authenticator) kaydeder.",
        """\
Senaryo: Authenticator MFA kayıt
  Given müşteri güvenlik ayarlarında
  When 'Authenticator ekle' seçilir
    And QR kod taranır ve 6 haneli kod girilir
  Then MFA 'Aktif' duruma geçer
    And sonraki girişlerde kod istenir
""",
        tags=("security", "mfa"),
    ),
)


# Category index — O(1) lookup
_BY_CAT: Dict[str, Tuple[Template, ...]] = {}
_BY_ID: Dict[str, Template] = {}


def _build_indexes() -> None:
    global _BY_CAT, _BY_ID
    by_cat: Dict[str, List[Template]] = {}
    for t in TEMPLATES:
        by_cat.setdefault(t.category, []).append(t)
        _BY_ID[t.id] = t
    _BY_CAT = {k: tuple(v) for k, v in by_cat.items()}


_build_indexes()


# ── Query API ────────────────────────────────────────────────────────────


def list_categories() -> List[str]:
    return sorted(_BY_CAT.keys())


def list_templates(
    *, category: Optional[str] = None, tag: Optional[str] = None
) -> List[Template]:
    items: Sequence[Template] = (
        _BY_CAT.get(category, ())
        if category is not None
        else TEMPLATES
    )
    if tag:
        items = [t for t in items if tag in t.tags]
    return list(items)


def get_template(template_id: str) -> Optional[Template]:
    return _BY_ID.get(template_id)


def search(query: str) -> List[Template]:
    """Basit case-insensitive arama — name + description + gherkin içinde."""
    q = (query or "").strip().lower()
    if not q:
        return []
    tokens = [t for t in re.split(r"\s+", q) if t]
    out: List[Template] = []
    for t in TEMPLATES:
        hay = f"{t.name} {t.description} {t.gherkin} {' '.join(t.tags)}".lower()
        if all(tok in hay for tok in tokens):
            out.append(t)
    return out


def stats() -> Dict[str, int]:
    return {
        "total": len(TEMPLATES),
        **{cat: len(items) for cat, items in _BY_CAT.items()},
    }
