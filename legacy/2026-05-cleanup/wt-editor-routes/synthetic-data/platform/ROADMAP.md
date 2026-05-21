# SyntheticBankData — Yol Haritası

> Bankacılık alanında AI destekli sentetik veri üretim platformu

---

## Faz 1 — MVP (Tamamlandı) ✅

**Süre:** Adım 1-10 | **Durum:** Tamamlandı

- Proje iskeleti ve mimari tasarım
- Veritabanı modelleri (SQLAlchemy 2.0) ve Pydantic şemaları
- SchemaAnalyzer — CSV/Excel/JSON dosya okuma ve kolon profilleme
- ColumnClassifier — 30 semantik tip, Türkçe/İngilizce kolon adı eşleştirme
- PIIDetector — KVKK uyumlu 5-seviyeli PII tespiti ve aksiyon önerisi
- RuleInferenceEngine — 9 kural tipi, otomatik çıkarım ve doğrulama
- RelationshipInference — FK, mantıksal ve AI bazlı ilişki tespiti
- SyntheticDataGenerator — Faker tr_TR, TCKN/IBAN algoritmik üretim, kural bazlı üretim
- ScenarioGenerator — 12 bankacılık senaryosu, karışık dağılım desteği
- FastAPI REST API — 20+ endpoint, Swagger UI, async
- LLM entegrasyonu — OpenAI, Anthropic, Ollama, fallback
- Örnek veri setleri (müşteri, hesap, işlem CSV'leri)
- Birim test altyapısı (pytest, 8 test modülü)

---

## Faz 2 — Veri Kalitesi ve İleri Analiz

**Tahmini Süre:** 4-6 hafta | **Öncelik:** Yüksek

### 2.1 — Veri Kalitesi Motoru
- Profiling dashboard — kolon bazlı kalite metrikleri (completeness, accuracy, consistency)
- Anomali tespiti — istatistiksel outlier ve pattern kırılma tespiti
- Veri temizleme önerileri — otomatik düzeltme kuralları (trim, case normalization, type casting)
- Veri kalitesi skoru — dataset bazlı 0-100 skor (ağırlıklı metrikler)
- Kalite trend takibi — zaman serisi bazlı kalite değişim analizi

### 2.2 — Gelişmiş Dağılım Analizi
- KDE (Kernel Density Estimation) ile sürekli değişken dağılım tahmini
- GMM (Gaussian Mixture Model) ile çoklu dağılım bileşeni tespiti
- Kategorik değişkenler için Bayesian frekans tahmini
- Korelasyon matrisi — Pearson, Spearman, Cramér's V (karma tipler)
- Zaman serisi decomposition (trend, mevsimsellik, artık)

### 2.3 — Çok Tablolu İlişki Grafiği
- Graph Neural Network ile ilişki puanlama
- Kardinalite otomatik tespiti (value distribution analizi)
- Döngüsel bağımlılık çözücü — topological sort iyileştirmesi
- İlişki grafiği görselleştirme (D3.js veya Cytoscape.js)

---

## Faz 3 — Gelişmiş Üretim Yöntemleri

**Tahmini Süre:** 6-8 hafta | **Öncelik:** Yüksek

### 3.1 — GAN Tabanlı Üretim
- CTGAN (Conditional Tabular GAN) entegrasyonu
- TVAE (Tabular Variational AutoEncoder) desteği
- Kolon bazlı transformer embedding
- Eğitim pipeline'ı — veri ön işleme, normalization, eğitim, değerlendirme
- Model checkpoint ve versiyonlama

### 3.2 — Diferansiyel Gizlilik
- ε-differential privacy garantisi ile üretim
- Laplace ve Gaussian noise mekanizmaları
- Privacy budget yönetimi (toplam ε takibi)
- Gizlilik-fayda dengesi analiz raporu
- KVKK ve GDPR uyumluluk sertifikası oluşturma

### 3.3 — Koşullu ve Kısıtlı Üretim
- Doğal dil → kural dönüşümü (LLM destekli)
- SQL WHERE benzeri koşullu üretim DSL'i
- Çapraz tablo kısıtları (ör. toplam bakiye = müşteri limiti)
- Referans bütünlüğü garanti motoru — üretim sonrası doğrulama ve onarım
- Temporal consistency — zaman serisi tutarlılığı (işlem tarihi > hesap açılış)

---

## Faz 4 — Platform ve Altyapı

**Tahmini Süre:** 6-8 hafta | **Öncelik:** Orta

### 4.1 — Web Arayüzü (Frontend)
- React/Next.js tabanlı modern UI
- Drag & drop dosya yükleme
- Gerçek zamanlı üretim ilerleme takibi (WebSocket)
- Kolon profil görselleştirme (histogram, box plot, pie chart)
- İlişki grafiği interaktif editör
- Kural yönetimi paneli (ekleme, düzenleme, silme, önizleme)
- Karanlık mod ve responsive tasarım

### 4.2 — Kimlik ve Yetkilendirme
- JWT tabanlı kimlik doğrulama
- Rol bazlı erişim kontrolü (RBAC) — Admin, Analyst, Viewer
- API anahtarı yönetimi (rate limiting dahil)
- Audit log — tüm işlemler için izlenebilirlik
- LDAP/SSO entegrasyonu (kurumsal kullanım)

### 4.3 — Ölçeklenebilirlik
- Celery + Redis ile asenkron görev kuyruğu
- Büyük veri seti desteği — chunk bazlı işleme (1M+ satır)
- PostgreSQL connection pooling (PgBouncer)
- Docker Swarm / Kubernetes deployment manifest'leri
- Horizontal scaling — stateless API tasarımı
- Object storage entegrasyonu (MinIO / S3) — büyük dosya depolama

### 4.4 — CI/CD ve Monitoring
- GitHub Actions workflow — lint, test, build, deploy
- Pre-commit hooks — black, ruff, mypy
- Prometheus + Grafana metrikleri (istek sayısı, latency, hata oranı)
- Structured logging (JSON format, ELK stack uyumlu)
- Health check endpoint'leri — readiness ve liveness probe

---

## Faz 5 — Ekosistem ve Entegrasyon

**Tahmini Süre:** 4-6 hafta | **Öncelik:** Düşük-Orta

### 5.1 — Veritabanı Entegrasyonları
- Doğrudan PostgreSQL/MySQL/Oracle bağlantısı ile şema import
- SQL DDL parsing — CREATE TABLE → otomatik şema analizi
- Database reverse engineering — var olan DB'den tam profil çıkarma
- Sentetik veri → doğrudan hedef DB'ye INSERT pipeline'ı

### 5.2 — Bulut ve Veri Platformu Entegrasyonu
- AWS S3, Azure Blob Storage, GCS dosya depolama
- Snowflake, BigQuery, Redshift connector'ları
- Apache Spark ile büyük ölçekli üretim (10M+ satır)
- Apache Kafka ile streaming sentetik veri üretimi
- dbt model entegrasyonu — sentetik seed data

### 5.3 — SDK ve CLI
- Python SDK — `pip install syntheticbankdata`
- CLI araç — `synth generate --scenario bireysel --count 10000`
- Jupyter Notebook widget — interaktif üretim ve görselleştirme
- REST API istemci kütüphanesi (TypeScript, Go)

### 5.4 — Sektörel Genişleme
- Sigorta domain paketleri (poliçe, hasar, prim)
- Sağlık domain paketleri (hasta, randevu, reçete)
- E-ticaret domain paketleri (ürün, sipariş, ödeme)
- Telekom domain paketleri (abone, CDR, fatura)
- Özelleştirilebilir domain template sistemi

---

## Özet Zaman Çizelgesi

| Faz | Süre | Durum |
|-----|------|-------|
| Faz 1 — MVP | Adım 1-10 | ✅ Tamamlandı |
| Faz 2 — Veri Kalitesi | 4-6 hafta | 📋 Planlandı |
| Faz 3 — Gelişmiş Üretim | 6-8 hafta | 📋 Planlandı |
| Faz 4 — Platform | 6-8 hafta | 📋 Planlandı |
| Faz 5 — Ekosistem | 4-6 hafta | 📋 Planlandı |

**Toplam Tahmini Süre:** ~20-28 hafta (Faz 2-5)

---

_Son güncelleme: 2026-03-29_
