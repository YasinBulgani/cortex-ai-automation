# Mimari Tasarım — SyntheticBankData

## 1. Genel Bakış

SyntheticBankData, bankacılık alanında gerçekçi sentetik veri üretmek için tasarlanmış bir platformdur. Kullanıcılar mevcut bir veritabanı şemasını yükler; sistem bu şemayı analiz ederek kolon tiplerini, ilişkileri ve iş kurallarını otomatik olarak çıkarır, ardından bu bilgilere dayalı olarak gerçekçi sentetik veriler üretir.

Platform **sabit kolon isimlerine bağımlı değildir** — dinamik şema analizi sayesinde herhangi bir banka veritabanı yapısına uyum sağlar.

---

## 2. High-Level Mimari

```
┌─────────────────────────────────────────────────────────┐
│                      İstemci (Client)                    │
│              (Web UI / API İstemcisi / CLI)               │
└──────────────────────────┬──────────────────────────────┘
                           │  HTTP / REST
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Gateway                        │
│              (api/ — Endpoint Yönlendirme)                │
└──────────────────────────┬──────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌────────────┐   ┌────────────────┐   ┌──────────────┐
│  Şema       │   │  Kural Motoru  │   │  Senaryo     │
│  Analiz     │   │  (Rule Engine) │   │  Üretici     │
│  Hattı      │   │                │   │  (Scenario   │
│  (Pipeline) │   │                │   │   Generator) │
└──────┬─────┘   └───────┬────────┘   └──────┬───────┘
       │                 │                    │
       ▼                 ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│              Sentetik Veri Üretim Motoru                  │
│              (synthetic_generator.py)                     │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                PostgreSQL Veritabanı                      │
│         (Şema Metadata + Üretilen Veriler)               │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Low-Level Bileşen Tasarımı

### 3.1 Şema Analiz Hattı (Schema Analysis Pipeline)

Kullanıcı bir SQL DDL dosyası, CSV başlık satırı veya doğrudan veritabanı bağlantısı sağladığında bu hat devreye girer.

| Bileşen | Dosya | Sorumluluk |
|---|---|---|
| **Schema Analyzer** | `schema_analyzer.py` | DDL parse etme, kolon tipleri çıkarma, tablo yapısını modelleme |
| **Column Classifier** | `column_classifier.py` | Kolon isimlerini ve tiplerini semantik olarak sınıflandırma (ör. email, IBAN, TC kimlik) |
| **PII Detector** | `pii_detector.py` | Kişisel veri içeren kolonları tespit etme ve etiketleme |
| **Relationship Inference** | `relationship_inference.py` | Tablolar arası ilişkileri (FK, mantıksal bağ) çıkarma |

**Akış:**
```
DDL/CSV/DB Bağlantısı
    → Schema Analyzer (yapı çıkarma)
    → Column Classifier (semantik sınıflandırma)
    → PII Detector (hassas veri tespiti)
    → Relationship Inference (ilişki çıkarma)
    → SchemaMetadata modeli (çıktı)
```

### 3.2 Kural Motoru (Rule Engine)

`rule_engine.py` — YAML tabanlı kural dosyalarından (`rules/` klasörü) iş kurallarını yükler ve uygular.

**Kural Türleri:**
- **Değer Aralıkları:** Min/max bakiye, faiz oranı sınırları
- **Format Kuralları:** IBAN formatı, telefon numarası deseni
- **Koşullu Kurallar:** Kredi skoru < 500 ise kredi limiti düşük olmalı
- **Dağılım Kuralları:** Yaş dağılımı normal dağılım, gelir dağılımı log-normal

### 3.3 Sentetik Veri Üretim Motoru

`synthetic_generator.py` — SchemaMetadata + Kural Seti → Sentetik veri çıktısı.

**Üretim Stratejileri:**
- `Faker` tabanlı alan üretimi (isim, adres, email vb.)
- İstatistiksel dağılım tabanlı sayısal üretim (numpy)
- İlişkisel tutarlılık: FK bağlantıları korunarak üretim
- Zaman serisi üretimi: İşlem tarihleri kronolojik sırada

### 3.4 Senaryo Üretici (Scenario Generator)

`scenario_generator.py` — Belirli bankacılık senaryolarını simüle eder:
- Dolandırıcılık işlemleri
- Kredi başvuru süreçleri
- Hesap açma/kapama akışları
- Yüksek riskli müşteri profilleri

### 3.5 API Katmanı

`api/` — FastAPI endpoint'leri:

| Endpoint | Metot | Açıklama |
|---|---|---|
| `/schema/upload` | POST | DDL/CSV yükle, şema analizi başlat |
| `/schema/{id}` | GET | Analiz edilmiş şema bilgisini getir |
| `/generate` | POST | Sentetik veri üretimi başlat |
| `/generate/{id}/status` | GET | Üretim durumunu sorgula |
| `/generate/{id}/download` | GET | Üretilen veriyi indir (CSV/SQL) |
| `/rules` | GET/POST | Kural listele / yeni kural ekle |
| `/scenarios` | GET/POST | Senaryo listele / senaryo çalıştır |

---

## 4. Veri Modelleri

### SchemaMetadata
```python
class SchemaMetadata:
    tables: List[TableInfo]         # Tablo listesi
    relationships: List[Relationship]  # Tablolar arası ilişkiler
    pii_columns: List[PIIColumn]     # PII içeren kolonlar
```

### TableInfo
```python
class TableInfo:
    name: str
    columns: List[ColumnInfo]       # Kolon bilgileri

class ColumnInfo:
    name: str
    data_type: str                  # SQL veri tipi
    semantic_type: str              # Semantik sınıf (email, iban, currency vb.)
    is_nullable: bool
    is_pii: bool
    constraints: dict               # CHECK, UNIQUE vb.
```

---

## 5. Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| API Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Veritabanı | PostgreSQL 16 |
| Veri Üretimi | Faker, NumPy, Pandas |
| Doğrulama | Pydantic v2 |
| Kural Tanımları | YAML (PyYAML) |
| Konteyner | Docker + Docker Compose |

---

## 6. Tasarım Kararları

1. **Modüler Monolith:** MVP aşamasında tüm servisler tek bir uygulamada çalışır; ileride mikro servislere ayrılabilir.
2. **Dinamik Şema:** Sabit kolon isimlerine bağlanmak yerine, semantik sınıflandırma ile her yapıya uyum sağlanır.
3. **YAML Kurallar:** İş kuralları kod dışında, YAML dosyalarında tutularak teknik olmayan kullanıcıların da düzenleme yapabilmesi sağlanır.
4. **Pipeline Deseni:** Şema analizi adımları pipeline olarak zincirlenir; her adım bağımsız test edilebilir.
5. **Asenkron Üretim:** Büyük veri setleri için üretim işlemi arka planda çalışır, durum sorgulaması ile takip edilir.
