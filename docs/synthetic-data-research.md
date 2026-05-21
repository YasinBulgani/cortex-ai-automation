# BGTS Sentetik Veri Üretim Platformu — Kapsamlı Araştırma ve Analiz Raporu

**Tarih:** 2026-04-03  
**Hazırlayan:** AI Araştırma Agent'ı  
**Kapsam:** Mevcut altyapı analizi, tahminleme yöntemleri, dış kaynak entegrasyonu, gizlilik, kalite metrikleri, bankacılık uyumu ve uygulama yol haritası  
**Hedef Kitle:** BGTS platformu geliştiricileri, test mimarları, QA liderleri

---

## İçindekiler

1. [Yönetici Özeti](#1-yönetici-özeti)
2. [Mevcut Durum Analizi](#2-mevcut-durum-analizi)
3. [Dış Veri Kaynağı Entegrasyonu](#3-dış-veri-kaynağı-entegrasyonu)
4. [İstatistiksel Tahminleme Yöntemleri](#4-i̇statistiksel-tahminleme-yöntemleri)
5. [Derin Öğrenme Tabanlı Yöntemler](#5-derin-öğrenme-tabanlı-yöntemler)
6. [Korelasyon ve İlişki Koruma](#6-korelasyon-ve-i̇lişki-koruma)
7. [Gizlilik ve KVKK Uyumu](#7-gizlilik-ve-kvkk-uyumu)
8. [Kalite Metrikleri ve Değerlendirme](#8-kalite-metrikleri-ve-değerlendirme)
9. [Bankacılık Sektörü Özel Gereksinimleri](#9-bankacılık-sektörü-özel-gereksinimleri)
10. [Mimari Öneri](#10-mimari-öneri)
11. [Uygulama Yol Haritası](#11-uygulama-yol-haritası)
12. [Referanslar](#12-referanslar)

---

## 1. Yönetici Özeti

BGTS Test Dönüşüm platformunun `engine/ai_synthetic_data/` modülü, CSV dosyalarından şema analizi yaparak Faker tabanlı sentetik veri üretebilen bir MVP pipeline'a sahiptir. Ancak bu pipeline bankacılık sektörünün gerektirdiği **istatistiksel sadakat**, **kolonlar arası korelasyon koruma**, **ilişkisel bütünlük** ve **gizlilik garantileri** açısından önemli eksiklikler taşımaktadır.

Bu rapor, mevcut altyapıyı derinlemesine analiz ederek, onu **üretim kalitesinde bir sentetik veri platformuna** dönüştürmek için gereken yöntemleri, araçları ve mimari kararları kapsamlı şekilde sunmaktadır.

**Temel bulgular:**

- Mevcut pipeline 5 üretim tipi destekliyor (faker, sequential, enum, range, date_range) — ancak hiçbiri orijinal veri dağılımını gerçekçi biçimde modelleyemiyor
- Kolonlar arası korelasyon tamamen kayboluyor (segment↔bakiye, yaş↔kredi_skoru)
- Tablolar arası ilişkisel bütünlük (FK) desteklenmiyor
- Gizlilik garantisi yok — PII tespiti var ama diferansiyel gizlilik uygulanmıyor
- Kalite ölçümü yapılmıyor — üretilen verinin orijinale ne kadar benzediği bilinmiyor

**Önerilen strateji:** 3 fazlı bir yol haritası ile mevcut pipeline'ı bozmadan, yanına yeni katmanlar ekleyerek platformu güçlendirmek. İlk faz (KDE + Koşullu Dağılım) 2 hafta, ikinci faz (CTGAN + İlişkisel) 4 hafta, üçüncü faz (Diferansiyel Gizlilik + Kalite) 3 hafta.

---

## 2. Mevcut Durum Analizi

### 2.1 Pipeline Mimarisi

Mevcut sentetik veri pipeline'ı `engine/ai_synthetic_data/app/` altında 4 temel modülden oluşmaktadır:

```
CSV Dosya → SchemaAnalyzer → SemanticClassifier → RuleEngine → SyntheticGenerator → DataFrame
               (analyzer.py)    (classifier.py)    (rule_engine.py)  (generator.py)
```

**FastAPI Endpoint'leri:**
- `POST /api/data/analyze-and-infer` — CSV yükle, analiz et, kural çıkar
- `POST /api/data/generate` — Kurallara göre sentetik veri üret

**Veritabanı Modelleri:** Customer → Account → Transaction ilişkisel yapı (`models/banking.py`), PostgreSQL + asyncpg ile async erişim.

### 2.2 Modül Detay Analizi

#### SchemaAnalyzer (`analyzer.py` — 52 satır)

**Yapabildiği:**
- Pandas DataFrame'den veri tipi tespiti (int, float, string, datetime, boolean)
- Sayısal kolonlar için: min, max, mean, std hesaplama
- Kategorik kolonlar için: en sık 5 değer ve normalize frekansları
- Null oranı ve benzersiz değer sayısı

**Yapamadığı:**
- Dağılım tipi tespiti (normal mi, lognormal mi, bimodal mi?)
- Çeyreklik (Q1, Q3, IQR) ve çarpıklık (skewness) hesaplama
- Kolon-kolon korelasyon matrisi
- String uzunluk dağılımı ve pattern tespiti
- Outlier (aykırı değer) analizi

#### SemanticClassifier (`classifier.py` — 34 satır)

**Yapabildiği:**
- 10 adet regex pattern ile kolon adından semantik sınıflandırma
- PII/non-PII etiketleme

**Yapamadığı:**
- Değer bazlı sınıflandırma (kolon adı "col_1" olsa bile değerleri inceleyerek TCKN olduğunu anlama)
- Fuzzy matching (örn. "musteri_ismi" → "name" eşleşmesi)
- Birden fazla dilin desteklenmesi
- Güven skoru (confidence) — tüm eşleşmeler eşit ağırlıklı

#### RuleEngine (`rule_engine.py` — 54 satır)

**Yapabildiği:**
- Semantik sınıftan üretim kuralı çıkarma (5 kural tipi)
- İstatistiklerden range kuralı oluşturma
- Top values'dan enum + ağırlık çıkarma

**Yapamadığı:**
- Koşullu kural çıkarma (segment=Premium → bakiye yüksek)
- Dağılım tipi belirleme (her sayısal kolon "range" = normal dağılım varsayılıyor)
- Kolon bağımlılık grafiği oluşturma
- NOT_NULL, UNIQUE, REGEX gibi kısıt kuralları

#### SyntheticGenerator (`generator.py` — 65 satır)

**Yapabildiği:**
- 5 üretim tipi: faker, sequential, enum, range, date_range
- Faker tr_TR ile Türkçe isim/adres/telefon
- Normal dağılım + clip ile sayısal veri üretimi
- Ağırlıklı seçim ile kategorik veri

**Yapamadığı:**
- Lognormal, Poisson, Pareto gibi alternatif dağılımlar
- KDE/Histogram bazlı gerçek dağılım replikasyonu
- Koşullu üretim (bir kolonun değerine göre başka kolonu üretme)
- İlişkisel üretim (FK koruma)
- Batch üretim ve ilerleme takibi
- Algoritmik TCKN, mod-97 IBAN üretimi

### 2.3 Güçlü-Zayıf Yön Matrisi

| Boyut | Durum | Puan (1-5) | Açıklama |
|-------|-------|------------|----------|
| Temel üretim | Çalışıyor | 3/5 | 5 tip, faker entegrasyonu mevcut |
| Dağılım sadakati | Zayıf | 1/5 | Sadece N(μ,σ) + clip, gerçek dağılım öğrenilmiyor |
| Korelasyon | Yok | 0/5 | Her kolon bağımsız üretiliyor |
| İlişkisel | Yok | 0/5 | FK koruma yok, tablolar arası bağlantı yok |
| Gizlilik | Kısmi | 1/5 | PII tespiti var ama gizlilik garantisi yok |
| Kalite ölçümü | Yok | 0/5 | Üretilen veri doğrulanmıyor |
| Dış kaynak | Sadece CSV | 1/5 | DB, API, Excel desteği yok |
| Bankacılık domain | Temel | 2/5 | Türk bankacılık modelleri var ama kurallar basit |

---

## 3. Dış Veri Kaynağı Entegrasyonu

### 3.1 Desteklenmesi Gereken Kaynaklar

| Kaynak Tipi | Öncelik | Kullanım Senaryosu | Gerekli Kütüphane |
|-------------|---------|--------------------|--------------------|
| **PostgreSQL** | P0 — Kritik | Üretim veritabanından tablo profilleme | `sqlalchemy`, `asyncpg` (mevcut) |
| **MySQL** | P1 — Yüksek | Legacy bankacılık sistemleri | `sqlalchemy`, `pymysql` |
| **Oracle** | P1 — Yüksek | Core banking (Temenos, Finacle) | `sqlalchemy`, `cx_Oracle` |
| **CSV/Excel** | P0 — Mevcut | Dosya bazlı veri aktarımı | `pandas` (mevcut) |
| **REST API** | P2 — Orta | Microservice veri çekme | `httpx` |
| **SQL Dump** | P2 — Orta | DDL'den şema çıkarma | Custom parser |

### 3.2 DB Connector Mimarisi

Önerilen mimari, mevcut pipeline'ın başına bir **DataSource** soyutlama katmanı ekler:

```
┌──────────────────────────────────────────────────┐
│                  DataSourceManager                │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │PostgreSQL│ │  MySQL   │ │  Oracle  │ ...      │
│  │Connector │ │Connector │ │Connector │         │
│  └─────┬────┘ └─────┬────┘ └─────┬────┘         │
│        └─────────────┼───────────┘               │
│                      ▼                           │
│              pandas DataFrame                    │
│                      │                           │
│              ┌───────▼────────┐                  │
│              │ SchemaAnalyzer │  ← mevcut pipeline│
│              └────────────────┘                  │
└──────────────────────────────────────────────────┘
```

### 3.3 DB Schema Discovery

Veritabanına bağlanıldığında otomatik olarak:

1. **Tablo listesi çıkarma** — `information_schema.tables` sorgusu
2. **Kolon metadata çıkarma** — `information_schema.columns` (tip, nullable, default)
3. **FK ilişki keşfi** — `information_schema.key_column_usage` + `referential_constraints`
4. **İndeks bilgisi** — Unique constraint'ler → UNIQUE kural çıkarımı
5. **Örnekleme** — `SELECT * FROM table TABLESAMPLE BERNOULLI(10)` ile büyük tablolarda hızlı profilleme
6. **Sayım** — `SELECT COUNT(*)` ile tablo boyutu tahmini

### 3.4 Incremental Profiling

Büyük tablolarda (10M+ satır) tam profilleme pratik değildir. Incremental yaklaşım:

1. **İlk Profil:** %1 örnekle (TABLESAMPLE veya LIMIT + ORDER BY RANDOM())
2. **İstatistik Güncelleme:** Yeni batch geldiğinde running mean/std güncelle
3. **Histogram Birleştirme:** t-digest veya DDSketch ile approximate quantile hesaplama
4. **Cache:** Profil sonuçlarını JSON olarak saklayarak tekrar hesaplamayı önle

---

## 4. İstatistiksel Tahminleme Yöntemleri

### 4.1 Yöntem Karşılaştırma Tablosu

| Yöntem | Dağılım Sadakati | Korelasyon | Hız | Karmaşıklık | Bankacılık Uygunluğu |
|--------|-------------------|------------|-----|-------------|---------------------|
| **Normal (N(μ,σ))** — mevcut | Düşük | Yok | Çok hızlı | Çok basit | Yetersiz |
| **Histogram Binning** | Orta | Yok | Hızlı | Basit | Temel ihtiyaçlar |
| **KDE (Kernel Density)** | Yüksek | Yok (tek kolon) | Hızlı | Orta | İyi |
| **GMM (Gaussian Mixture)** | Yüksek | Kısmi | Orta | Orta | İyi |
| **Copula** | Yüksek | Tam (2D+) | Orta | Yüksek | Çok iyi |
| **Bayesian Network** | Yüksek | Tam (koşullu) | Yavaş | Yüksek | Çok iyi |

### 4.2 Normal Dağılım (Mevcut Yöntem)

**Çalışma prensibi:** Orijinal veriden mean ve std hesapla, `N(μ, σ)` dağılımından örnekle, min-max ile kırp.

**Sorunlar:**
- Tek tepeli (unimodal) varsayımı — bankacılık bakiyeleri genellikle çift tepeli (bireysel ~15K, kurumsal ~2M)
- Simetrik varsayımı — bakiye/tutar verileri genellikle sağa çarpık (right-skewed)
- Clip ile kenar kaybı — min/max'ta yapay yığılma oluşur

**Ne zaman yeterli:** Sadece gerçekten normal dağılan veriler için (örn. yaş, kredi skoru)

### 4.3 Histogram Binning

**Çalışma prensibi:** Orijinal veriyi N adet bin'e (kova) böl, her bin'in frekansını öğren, bin içinden uniform örnekle.

```python
# Histogram öğrenme
counts, bin_edges = np.histogram(original_data, bins=50)
probs = counts / counts.sum()

# Sentetik üretim
bin_indices = np.random.choice(len(probs), size=n, p=probs)
synthetic = np.array([
    np.random.uniform(bin_edges[i], bin_edges[i+1])
    for i in bin_indices
])
```

**Avantajlar:** Dağılım varsayımı gerektirmez, hızlı, anlaşılır.  
**Dezavantajlar:** Bin sayısı seçimi kritik, sürekli olmayan çıktı, yüksek boyutlu veride etkisiz.  
**Bankacılık uygunluğu:** Orta — tek kolon profilleme için yeterli, korelasyon korumaz.

### 4.4 KDE (Kernel Density Estimation)

**Çalışma prensibi:** Her veri noktasının etrafına bir kernel (genellikle Gaussian) yerleştir, tüm kernel'ların toplamından sürekli bir olasılık yoğunluk fonksiyonu (PDF) elde et.

```python
from scipy.stats import gaussian_kde

# Orijinal veriden öğren
kde = gaussian_kde(original_df["bakiye"].dropna(), bw_method="scott")

# Sentetik üret
synthetic_values = kde.resample(50_000).flatten()
```

**Avantajlar:**
- Dağılım varsayımı gerektirmez — çift tepeli, çarpık, uzun kuyruklu her şeyi yakalar
- Sürekli çıktı üretir (histogram'ın kesikli sorununu çözer)
- SciPy'da hazır implementasyon (`scipy.stats.gaussian_kde`)
- Çok hızlı training ve sampling

**Dezavantajlar:**
- Bandwidth seçimi kritik (Scott's Rule genellikle iyi çalışır)
- Çok boyutlu veride "curse of dimensionality" — 5+ kolon birlikte modellemek zorlaşır
- Korelasyonu tek başına korumaz (multivariate KDE ile kısmen mümkün)

**Bankacılık uygunluğu:** Çok iyi — bakiye, tutar, kredi skoru gibi tek boyutlu dağılımlar için ideal. **TabKDE** yaklaşımı (OpenReview 2025) copula dönüşümü ile birleştirildiğinde tam tablolar için de kullanılabilir.

### 4.5 GMM (Gaussian Mixture Model)

**Çalışma prensibi:** Veriyi K adet Gaussian bileşenin karışımı olarak modelle. Her bileşenin kendi μ, σ ve ağırlığı var. EM (Expectation-Maximization) algoritması ile öğren.

```python
from sklearn.mixture import GaussianMixture

# Orijinal veriden öğren (3 bileşen: bireysel, premium, kurumsal)
gmm = GaussianMixture(n_components=3, random_state=42)
gmm.fit(original_df[["bakiye"]].dropna())

# Sentetik üret
synthetic_values, _ = gmm.sample(50_000)
```

**Avantajlar:**
- Çok modlu (multimodal) dağılımları doğal olarak modeller
- Bileşen sayısı BIC/AIC ile otomatik seçilebilir
- Multivariate GMM ile kolonlar arası korelasyonu kısmen korur
- Yorumlanabilir: "3 müşteri segmenti var, dağılımları şöyle"

**Dezavantajlar:**
- Bileşen sayısı seçimi — fazla bileşen overfitting, az bileşen underfitting
- Gaussian varsayımı — ağır kuyruklu dağılımlarda yetersiz kalabilir
- Yüksek boyutta (10+ kolon) eğitim yavaşlar

**Bankacılık uygunluğu:** Çok iyi — müşteri segmentasyonu doğal olarak GMM'e uyar. "Bireysel müşteriler ~N(15K, 30K), Premium ~N(500K, 200K)" gibi segment bazlı modelleme.

### 4.6 Copula Tabanlı Korelasyon Koruma

**Çalışma prensibi:** Sklar teoremi gereği her çok değişkenli dağılım, marjinal dağılımlar + bir copula fonksiyonu olarak ayrıştırılabilir. Bu sayede:
1. Her kolonun marjinal dağılımını ayrı ayrı öğren (KDE, GMM, parametrik)
2. Kolonlar arası bağımlılık yapısını copula ile modelle
3. Copula'dan örnekle → marjinal tersleri ile gerçek değerlere dönüştür

**Copula tipleri:**
- **Gaussian Copula:** Normal dağılıma yakın, lineer korelasyonu iyi yakalar. SDV'nin varsayılan yöntemi.
- **t-Copula:** Kuyruk bağımlılığını (tail dependence) yakalar — finansal risk için önemli.
- **Clayton/Gumbel/Frank:** Asimetrik bağımlılık yapıları için.

```python
# SDV ile Gaussian Copula
from sdv.single_table import GaussianCopulaSynthesizer
from sdv.metadata import Metadata

metadata = Metadata.detect_from_dataframe(data=df, table_name="customers")
synth = GaussianCopulaSynthesizer(metadata)
synth.fit(df)
synthetic_df = synth.sample(num_rows=50_000)
```

**Bankacılık uygunluğu:** Mükemmel — Gaussian Copula lineer korelasyonları, t-Copula kuyruk risklerini korur. **Önerilen başlangıç noktası** olarak Gaussian Copula + KDE marjinaller kombinasyonu.

---

## 5. Derin Öğrenme Tabanlı Yöntemler

### 5.1 Yöntem Karşılaştırma

| Model | Mimari | Eğitim Süresi | Veri Sadakati | Gizlilik | Korelasyon | GPU Gereksinimi |
|-------|--------|---------------|---------------|----------|------------|-----------------|
| **CTGAN** | GAN (conditional) | Yüksek | İyi | Orta | İyi | Önerilen |
| **TVAE** | VAE | Orta | İyi-Çok İyi | İyi | İyi | Opsiyonel |
| **CopulaGAN** | GAN + Copula | Yüksek | Çok İyi | Orta | Çok İyi | Önerilen |
| **TabDDPM** | Diffusion | Çok Yüksek | Çok İyi | İyi | Çok İyi | Gerekli |
| **FinDiff** | Diffusion (finans) | Çok Yüksek | Çok İyi | İyi | Çok İyi | Gerekli |
| **TabKDE** | KDE + Copula | Çok Düşük | İyi | İyi | İyi | Gereksiz |

### 5.2 CTGAN (Conditional Tabular GAN)

**Çalışma prensibi:** İki rakip sinir ağı (Generator + Discriminator) eğitilir. Generator sentetik veri üretir, Discriminator gerçek/sahte ayırt etmeye çalışır. Koşullu eğitim (training-by-sampling) ile azınlık sınıfları da iyi öğrenir.

**Avantajlar:**
- Kategorik + sayısal karışık veride güçlü
- Koşullu üretim desteği (belirli segment için veri üret)
- SDV kütüphanesinde hazır implementasyon
- Dengesiz veri (class imbalance) ile başa çıkabilir

**Dezavantajlar:**
- Mode collapse riski — bazı modları kaçırabilir
- Eğitim kararsızlığı — hiperparametre ayarı gerekir
- 10K'dan az satırda overfitting riski
- GPU olmadan yavaş (50K satır ~30 dk CPU)

**Bankacılık deneyimi:** IEEE 2023 çalışmasında kredi teklifi verisinde CTGAN ve TVAE karşılaştırıldı; TVAE bazı metriklerde CTGAN'ı geçti. Finans verisinde sınıf dengesizliği nedeniyle conditional training kritik.

### 5.3 TVAE (Tabular Variational AutoEncoder)

**Çalışma prensibi:** Encoder veriyi düşük boyutlu latent space'e sıkıştırır, Decoder bu latent temsilden yeniden veri üretir. KL divergence ile latent space düzenlenir.

**Avantajlar:**
- GAN'dan daha kararlı eğitim — mode collapse yok
- Daha hızlı eğitim
- Latent space'de interpolasyon mümkün (senaryolar arası geçiş)
- Gizlilik açısından GAN'dan daha iyi — veriyi ezberlemez

**Dezavantajlar:**
- Üretim kalitesi bazen GAN'dan düşük (bulanık çıktı)
- Çok yüksek boyutlu tablolarda zorlanabilir

**Öneri:** TVAE, bankacılık verisinde CTGAN'a güçlü bir alternatif. **İlk implementasyon için TVAE tercih edilmeli** — daha kararlı, daha hızlı.

### 5.4 SDV (Synthetic Data Vault) Ekosistemi

SDV, Python'da sentetik veri üretimi için en kapsamlı açık kaynak kütüphanesidir:

**Desteklenen synthesizer'lar:**
- `GaussianCopulaSynthesizer` — İstatistiksel, hızlı, iyi başlangıç
- `CTGANSynthesizer` — GAN tabanlı, korelasyon koruma
- `TVAESynthesizer` — VAE tabanlı, kararlı
- `CopulaGANSynthesizer` — Copula + GAN hibrit
- `HMASynthesizer` — Çoklu tablo, FK koruma

**Önemli Not:** SDV, 2023'ten itibaren Business Source License (BSL) altına geçmiştir. Ticari kullanımda lisans koşullarına dikkat edilmelidir. Alternatif olarak `sdv==1.x` sürümleri MIT lisanslıdır.

### 5.5 Diğer Yaklaşımlar

**FinDiff (Financial Diffusion Model):** Özellikle finansal işlem verileri için tasarlanmış diffusion modeli. Zaman serisi ve işlem pattern'larını korumada güçlü. Henüz erken aşamada.

**MostlyAI:** Ticari platform, web arayüzü ile kolay kullanım. SDV karşılaştırmasında FK korumada farklı sonuçlar — veri setine bağlı. On-premise deployment bankalar için önemli.

**Gretel.ai:** Ticari, API tabanlı. Diferansiyel gizlilik entegrasyonu güçlü. Cloud-native yapısı bazı bankalar için uyumsuz olabilir (veri çıkışı kısıtları).

---

## 6. Korelasyon ve İlişki Koruma

### 6.1 Kolonlar Arası Korelasyon

Bankacılık verisinde kritik korelasyonlar:

| Kolon A | Kolon B | İlişki Tipi | Örnek |
|---------|---------|-------------|-------|
| segment | bakiye | Koşullu dağılım | Premium → yüksek bakiye |
| yaş | kredi_skoru | Pozitif korelasyon | Yaşlı → daha yüksek skor eğilimi |
| hesap_tipi | faiz_oranı | Deterministik | Vadesiz → %0, Vadeli → %15-50 |
| şehir | segment | Dağılım farkı | İstanbul'da Premium oranı %25, Erzurum'da %5 |
| işlem_tutarı | kanal | Koşullu aralık | ATM → max 5000 TL, EFT → max 5M TL |

**Mevcut durum:** Tüm bu ilişkiler kaybolmuş. Her kolon bağımsız üretiliyor.

**Çözüm yöntemleri (kolaydan zora):**

1. **Koşullu kural tablosu (Seviye 1):** Segment bazlı bakiye dağılımlarını hardcode
2. **Copula (Seviye 2):** Gaussian/t-Copula ile otomatik korelasyon öğrenme
3. **CTGAN/TVAE (Seviye 3):** Derin öğrenme ile tüm korelasyonları otomatik öğrenme

### 6.2 Tablolar Arası FK İlişki Koruma

Bankacılık veri modelinde tipik ilişki zinciri:

```
Branch (1) ──→ (N) Customer (1) ──→ (N) Account (1) ──→ (N) Transaction
                     │                     │
                     └──→ (N) Card         └──→ (N) Deposit
```

**Doğru üretim sırası (Topological Sort):**
1. Branch tablosunu üret
2. Customer üret — branch_id'leri mevcut branch'lerden seç
3. Account üret — customer_id'leri mevcut customer'lardan seç
4. Transaction üret — account_id'leri mevcut account'lardan seç

**Kardinalite koruma:**
- Her customer'a 1-5 hesap (lognormal dağılım)
- Her hesaba 0-100 işlem/ay (Poisson dağılım)
- Her customer'a 0-3 kart (geometric dağılım)

**SDV HMA (Hierarchical Modeling Algorithm):**
SDV'nin `HMASynthesizer` sınıfı bu sorunu otomatik çözer:

```python
from sdv.multi_table import HMASynthesizer

metadata = Metadata.detect_from_dataframes(
    dataframes={"customers": df_cust, "accounts": df_acc, "transactions": df_txn},
    relationships=[
        {"parent": "customers", "child": "accounts", "parent_key": "id", "child_key": "customer_id"},
        {"parent": "accounts", "child": "transactions", "parent_key": "id", "child_key": "account_id"},
    ]
)
synth = HMASynthesizer(metadata)
synth.fit(dataframes)
synthetic = synth.sample(scale=2)  # 2x veri üret
```

### 6.3 Zaman Serisi Pattern Koruma

Bankacılık işlem verisi güçlü temporal pattern'lar içerir:

- **Haftalık döngü:** Hafta içi işlem yoğunluğu yüksek, hafta sonu düşük
- **Aylık döngü:** Ay başı maaş girişleri, ay sonu fatura ödemeleri
- **Mevsimsellik:** Haziran-Temmuz tatil harcamaları, Kasım-Aralık bayram alışverişleri
- **Trend:** Yıllar içinde dijital kanal kullanımı artışı

**Çözüm:** SDV'nin `PARSynthesizer` (Probabilistic AutoRegressive) modeli veya özel zaman serisi decomposition (STL: Seasonal-Trend-Loess) sonrası bileşen bazlı üretim.

---

## 7. Gizlilik ve KVKK Uyumu

### 7.1 Yasal Çerçeve

| Düzenleme | Kapsam | Sentetik Veri Durumu |
|-----------|--------|---------------------|
| **KVKK 6698** | Türkiye, kişisel veri koruma | Anonimleştirilmiş veri KVKK kapsamı dışında (m.28/1) |
| **GDPR** | AB, genel veri koruma | Sentetik veri "anonim" sayılabilir ama case-by-case değerlendirilmeli |
| **BDDK** | Türk bankacılık sektörü | Test ortamlarında gerçek müşteri verisi kullanımı yasak |
| **PCI-DSS 4.0** | Kart verisi güvenliği | Test/geliştirme ortamlarında gerçek PAN kullanılamaz (Req. 6.5.3) |

**Kritik soru:** Sentetik veri gerçekten "anonim" mi?

Cevap: **Her zaman değil.** Eğer sentetik veri üretim modeli orijinal veriyi "ezberlediyse" (memorization), sentetik kayıtlardan gerçek kişilere ulaşılabilir. Bu yüzden **gizlilik garantisi** gerekir.

### 7.2 Diferansiyel Gizlilik (ε-Differential Privacy)

**Tanım:** Bir algoritma ε-DP sağlar eğer tek bir kişinin verideki varlığı/yokluğu, algoritmanın çıktısını en fazla e^ε kat değiştiriyorsa.

**Epsilon (ε) değerleri:**

| ε Değeri | Gizlilik | Veri Kalitesi | Kullanım |
|----------|----------|---------------|----------|
| 0.1 - 1.0 | Çok güçlü | Düşük | Hassas sağlık/finans verisi |
| 1.0 - 5.0 | Güçlü | Orta | Bankacılık test verisi (önerilen) |
| 5.0 - 10.0 | Orta | İyi | İç kullanım, demo verisi |
| 10.0+ | Zayıf | Çok iyi | Sadece istatistiksel kullanım |

**Bankacılık için önerilen:** ε = 3.0 — gizlilik ile kullanılabilirlik arasında iyi denge.

**Uygulama yöntemi:**
1. **DPSGD (Differentially Private SGD):** CTGAN/TVAE eğitiminde gradient'lara noise ekle
2. **DP Histogram:** Histogram bin'lerine Laplace noise ekle
3. **PATE (Private Aggregation of Teacher Ensembles):** Birden fazla modelin "oy" mekanizması

### 7.3 PII Maskeleme Stratejileri

| PII Tipi | Mevcut Tespit | Maskeleme Stratejisi | Sentetik Üretim |
|----------|---------------|---------------------|-----------------|
| TCKN | Regex ✓ | Hash → REDACT | Algoritmik (checksum geçerli, gerçek olmayan) |
| IBAN | Regex ✓ | Son 4 hane koru → MASK | Mod-97 geçerli, gerçek olmayan |
| Ad-Soyad | Regex ✓ | K-anonimlik → GENERALIZE | Faker tr_TR ile yeni isim |
| Email | Regex ✓ | Domain koru → MASK | `isim.soyisim@domain.com` üret |
| Telefon | Regex ✓ | Son 4 hane → MASK | `+90 5XX XXX XX XX` formatlı |
| Adres | Yok ✗ | İlçe seviyesine → GENERALIZE | Faker tr_TR ile yeni adres |
| Doğum Tarihi | Yok ✗ | Yıl aralığına → GENERALIZE | Yaş dağılımından türet |

### 7.4 k-Anonimlik ve l-Çeşitlilik

**k-Anonimlik:** Sentetik veri setinde her quasi-identifier kombinasyonu en az k kez bulunmalı.
**l-Çeşitlilik:** Her quasi-identifier grubunda hassas kolon en az l farklı değer almalı.

**Bankacılık örneği:**
- Quasi-identifiers: yaş, cinsiyet, şehir, segment
- Hassas: bakiye, kredi_skoru
- k=5, l=3 → Her (35-yaş, Erkek, İstanbul, Bireysel) grubunda en az 5 kayıt ve en az 3 farklı bakiye aralığı

---

## 8. Kalite Metrikleri ve Değerlendirme

### 8.1 Üç Boyutlu Kalite Değerlendirmesi

Sentetik veri kalitesi 3 ana boyutta ölçülür:

```
                    SADAKAT (Fidelity)
                         ▲
                        / \
                       /   \
                      /     \
                     /       \
    FAYDALILIK ◄────/─────────\────► GİZLİLİK
    (Utility)       Optimal     (Privacy)
                    Nokta
```

**Sadakat↔Gizlilik trade-off:** Sentetik veri orijinale ne kadar benzerse o kadar faydalı ama o kadar da gizlilik riski taşır.

### 8.2 Sadakat (Fidelity) Metrikleri

| Metrik | Ne Ölçer | Formül/Yöntem | İdeal Değer |
|--------|----------|---------------|-------------|
| **KL Divergence** | Marjinal dağılım farkı | D_KL(P \|\| Q) = Σ P(x) log(P(x)/Q(x)) | 0'a yakın |
| **Jensen-Shannon Distance** | Simetrik dağılım farkı | JSD = √((KL(P\|\|M) + KL(Q\|\|M))/2), M=(P+Q)/2 | 0'a yakın |
| **Wasserstein Distance** | Dağılım taşıma maliyeti | Earth Mover's Distance | 0'a yakın |
| **Korelasyon Matrisi Farkı** | Korelasyon yapısı | \|\|Corr_real - Corr_synth\|\|_F (Frobenius norm) | 0'a yakın |
| **Kolmogorov-Smirnov** | CDF farkı | max\|F_real(x) - F_synth(x)\| | 0'a yakın |
| **χ² Testi** | Kategorik uyum | Pearson chi-squared statistic | p > 0.05 |

### 8.3 Faydalılık (Utility) Metrikleri

| Metrik | Ne Ölçer | Yöntem |
|--------|----------|--------|
| **ML Utility (TSTR)** | Sentetik veri ile eğitilen modelin performansı | Train on Synthetic, Test on Real — F1/AUC karşılaştırması |
| **ML Utility (TRTS)** | Gerçek veri ile eğitilen modelin sentetik test performansı | Train on Real, Test on Synthetic |
| **Query Fidelity** | SQL sorgularının aynı sonuçları vermesi | Aynı WHERE/GROUP BY sorgularını çalıştır, sonuçları karşılaştır |
| **Statistical Test Preservation** | İstatistiksel testlerin aynı sonuçları vermesi | t-test, χ² testi — aynı H0 kararı mı? |

### 8.4 Gizlilik Metrikleri

| Metrik | Ne Ölçer | Risk Eşiği |
|--------|----------|------------|
| **DCR (Distance to Closest Record)** | Sentetik kaydın en yakın gerçek kayda mesafesi | < %5 → yüksek risk |
| **Membership Inference Attack** | Gerçek kaydın eğitim setinde olup olmadığını tahmin etme | AUC < 0.55 → güvenli |
| **Attribute Inference Attack** | Bilinen kolonlardan hassas kolonu tahmin etme | Accuracy < random + %5 → güvenli |
| **Re-identification Risk** | Quasi-identifier'lardan kişi tespiti | Risk < %9 (regülatör eşiği) |
| **ε-DP Guarantee** | Matematiksel gizlilik garantisi | ε < 5.0 → bankacılık uygun |

### 8.5 Değerlendirme Framework'leri

| Framework | Açık Kaynak | Metrikler | Kullanım |
|-----------|------------|-----------|----------|
| **SDMetrics** (SDV) | Evet (BSL) | Sadakat + gizlilik | SDV ile entegre |
| **SynthEval** | Evet (MIT) | Kapsamlı, özelleştirilebilir | Akademik + endüstri |
| **SynthGauge** | Evet | KL, JS, utility, gizlilik | UK ONS tarafından geliştirildi |
| **FEST** | Evet | Privacy-utility tradeoff | Akademik benchmark |

---

## 9. Bankacılık Sektörü Özel Gereksinimleri

### 9.1 Düzenleyici Çerçeve

| Düzenleyici | Gereksinim | Sentetik Veri Etkisi |
|-------------|-----------|---------------------|
| **BDDK** | Test ortamında gerçek müşteri verisi kullanılamaz | Sentetik veri zorunlu hale geliyor |
| **KVKK m.12** | Veri güvenliği tedbirleri | Sentetik veride kişisel veri kalmamalı |
| **PCI-DSS 4.0 Req.6** | Test verisinde gerçek PAN yasak | Kart numarası sentetik olmalı |
| **Basel III** | Operasyonel risk modelleme | Stres testi için sentetik veri gerekli |
| **SOX** | Denetim izi | Sentetik veri üretim kaydı tutulmalı |

### 9.2 Bankacılık Verisine Özgü Dağılım Tipleri

Bankacılık verisi standart normal dağılıma **UYMAZ**. Doğru dağılım modelleri:

| Veri Tipi | Dağılım | Parametre | Neden |
|-----------|---------|-----------|-------|
| **Bakiye** | Lognormal + Pareto kuyruk | μ=10, σ=2.5 | Çoğu müşterinin düşük bakiyesi var, az sayıda çok yüksek |
| **İşlem tutarı** | Lognormal-Pareto karışımı | — | Çok sayıda küçük işlem, az sayıda büyük transfer |
| **İşlem sıklığı** | Poisson | λ=15/ay (bireysel) | Sayma verisi, bağımsız olaylar |
| **İşlem arası süre** | Exponential / Gamma | — | Bekleme süresi dağılımı |
| **Kredi skoru** | Beta (yeniden ölçeklenmiş) | α=5, β=2 | 300-900 aralığında sola çarpık |
| **Yaş** | Truncated Normal | μ=42, σ=15 | 18-90 aralığında sınırlı |
| **Vade** | Discrete categorical | — | 1, 3, 6, 12, 24, 36 ay |
| **Faiz oranı** | Log-normal (küçük) | μ=2.5, σ=0.5 | Sıfıra yakın ama negatif olamaz |

**Basel II/III Önerisi:** Operasyonel kayıp modelleri için Compound Poisson + Lognormal (sıklık × şiddet) yaklaşımı standart.

### 9.3 Türk Bankacılık Sektörüne Özel Değerler

| Parametre | Değer | Kaynak |
|-----------|-------|--------|
| Ortalama vadesiz bakiye (bireysel) | ~12.000 TL | TCMB istatistik |
| Ortalama kredi kartı limiti | ~25.000 TL | BKM verileri |
| Aylık ortalama işlem sayısı | ~18 (dijital kanal) | Sektör ortalaması |
| POS işlem ort. tutarı | ~350 TL | BKM |
| EFT ort. tutarı | ~8.500 TL | TCMB |
| Müşteri yaş ortalaması | ~38 | Sektör ortalaması |
| Segment dağılımı | Bireysel %65, KOBİ %20, Kurumsal %10, VIP %5 | Yaklaşık sektör |
| Aktif dijital kanal oranı | %72 | TBB verileri |

---

## 10. Mimari Öneri

### 10.1 Hedef Mimari

Mevcut pipeline'a minimum müdahale ile yeni katmanlar eklemek:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BGTS Synthetic Data Platform v2                 │
│                                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐              │
│  │ DataSource  │   │ DataSource  │   │ DataSource  │              │
│  │   CSV/Excel │   │  PostgreSQL │   │  REST API   │   ...        │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘              │
│         └─────────────────┼─────────────────┘                      │
│                           ▼                                         │
│  ┌──────────────────────────────────────────┐                      │
│  │         Enhanced SchemaAnalyzer           │  ← Mevcut + upgrade │
│  │  + dağılım tespiti (fit test)            │                      │
│  │  + korelasyon matrisi                    │                      │
│  │  + outlier analizi                       │                      │
│  │  + FK ilişki keşfi                       │                      │
│  └──────────────────┬───────────────────────┘                      │
│                     ▼                                               │
│  ┌──────────────────────────────────────────┐                      │
│  │       Enhanced SemanticClassifier         │  ← Mevcut + upgrade │
│  │  + değer bazlı sınıflandırma             │                      │
│  │  + güven skoru                           │                      │
│  │  + fuzzy matching                        │                      │
│  └──────────────────┬───────────────────────┘                      │
│                     ▼                                               │
│  ┌──────────────────────────────────────────┐                      │
│  │    Synthesizer Seçim Katmanı (YENİ)       │                      │
│  │                                          │                      │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ │                      │
│  │  │ Stat     │ │  KDE +   │ │ CTGAN /  │ │                      │
│  │  │(mevcut)  │ │ Copula   │ │ TVAE     │ │                      │
│  │  │ Basit    │ │ Orta     │ │ İleri    │ │                      │
│  │  └──────────┘ └──────────┘ └──────────┘ │                      │
│  └──────────────────┬───────────────────────┘                      │
│                     ▼                                               │
│  ┌──────────────────────────────────────────┐                      │
│  │      Privacy Layer (YENİ)                 │                      │
│  │  + diferansiyel gizlilik (ε-DP)          │                      │
│  │  + PII maskeleme                         │                      │
│  │  + k-anonimlik kontrolü                  │                      │
│  └──────────────────┬───────────────────────┘                      │
│                     ▼                                               │
│  ┌──────────────────────────────────────────┐                      │
│  │      Quality Evaluator (YENİ)             │                      │
│  │  + KL/JS divergence                      │                      │
│  │  + korelasyon farkı                      │                      │
│  │  + ML utility test                       │                      │
│  │  + gizlilik risk skoru                   │                      │
│  └──────────────────┬───────────────────────┘                      │
│                     ▼                                               │
│              Sentetik DataFrame / Export                            │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.2 Yeni Endpoint'ler

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/data/sources` | GET | Desteklenen veri kaynağı listesi |
| `/api/data/connect` | POST | Dış DB'ye bağlan, şemayı keşfet |
| `/api/data/profile/{table}` | POST | Tablo profilleme (istatistik + dağılım) |
| `/api/data/analyze-and-infer` | POST | Mevcut — CSV'den analiz (korunur) |
| `/api/data/generate` | POST | Mevcut — basit üretim (korunur) |
| `/api/data/generate/advanced` | POST | KDE/Copula/CTGAN ile üretim |
| `/api/data/generate/relational` | POST | Çoklu tablo, FK korumalı üretim |
| `/api/data/evaluate` | POST | Kalite metrikleri hesapla |
| `/api/data/privacy-check` | POST | Gizlilik risk değerlendirmesi |

### 10.3 Yeni Modüller

| Modül | Dosya | Bağımlılık |
|-------|-------|------------|
| DataSourceManager | `app/core/datasource.py` | `sqlalchemy`, `httpx` |
| DistributionFitter | `app/core/distribution.py` | `scipy`, `scikit-learn` |
| CorrelationAnalyzer | `app/core/correlation.py` | `numpy`, `scipy` |
| KDESynthesizer | `app/core/kde_synth.py` | `scipy` |
| CopulaSynthesizer | `app/core/copula_synth.py` | `sdv` veya custom |
| DeepSynthesizer | `app/core/deep_synth.py` | `sdv` (CTGAN/TVAE) |
| RelationalSynthesizer | `app/core/relational_synth.py` | `sdv` (HMA) |
| PrivacyGuard | `app/core/privacy.py` | `diffprivlib`, custom |
| QualityEvaluator | `app/core/quality.py` | `scipy`, `scikit-learn` |

### 10.4 Gerekli Python Kütüphaneleri

```
# Mevcut — korunacak
pandas
numpy
faker
sqlalchemy
asyncpg
fastapi
pydantic-settings

# Faz 1 — İstatistiksel
scipy>=1.11.0          # KDE, dağılım fitting, KS test
scikit-learn>=1.3.0    # GMM, korelasyon, preprocessing

# Faz 2 — Derin Öğrenme
sdv>=1.0.0             # CTGAN, TVAE, CopulaGAN, HMA (lisansa dikkat)
torch>=2.0.0           # SDV bağımlılığı

# Faz 3 — Gizlilik + Kalite
diffprivlib>=0.6.0     # IBM diferansiyel gizlilik
syntheval>=0.1.0       # Kapsamlı kalite metrikleri (opsiyonel)
```

---

## 11. Uygulama Yol Haritası

### Faz 1: İstatistiksel Güçlendirme (2 Hafta)

**Hedef:** Mevcut pipeline'ı bozmadan dağılım sadakatini artırmak.

| Hafta | Görev | Effort | Çıktı |
|-------|-------|--------|-------|
| H1 | DB connector (DataSourceManager) | 3 gün | PostgreSQL/MySQL'den DataFrame çekme |
| H1 | SchemaAnalyzer upgrade: dağılım tespiti | 2 gün | Skewness, kurtosis, histogram, best-fit test |
| H1 | KDE synthesizer implementasyonu | 1 gün | `scipy.stats.gaussian_kde` tabanlı üretim |
| H2 | Koşullu dağılım (segment→bakiye) | 2 gün | Group-by bazlı ayrı KDE/GMM |
| H2 | Bankacılık dağılımları (lognormal, Poisson) | 1 gün | Domain-specific generator fonksiyonları |
| H2 | Yeni endpoint'ler ve test | 2 gün | `/connect`, `/profile`, `/generate/advanced` |

**Faz 1 Sonucu:**
- DB'den veri çekebilir
- Gerçek dağılımı öğrenip replike edebilir (KDE)
- Segment bazlı koşullu üretim yapabilir
- 5 bankacılık dağılım tipi destekler

### Faz 2: Korelasyon ve İlişkisel Üretim (4 Hafta)

**Hedef:** Kolonlar arası ve tablolar arası ilişkileri koruyarak üretim.

| Hafta | Görev | Effort | Çıktı |
|-------|-------|--------|-------|
| H3 | Copula synthesizer (GaussianCopula) | 3 gün | Korelasyon koruyan tek tablo üretimi |
| H3 | Korelasyon matrisi analizi | 2 gün | Otomatik korelasyon keşfi ve raporlama |
| H4 | CTGAN/TVAE entegrasyonu | 3 gün | SDV tabanlı derin öğrenme üretimi |
| H4 | Synthesizer seçim katmanı | 2 gün | Veri boyutuna göre otomatik yöntem seçimi |
| H5 | İlişkisel üretim (FK koruma) | 5 gün | Topological sort, kardinalite koruma |
| H6 | Zaman serisi pattern koruma | 3 gün | İşlem tarihi döngüsellik |
| H6 | Entegrasyon testleri | 2 gün | Tüm pipeline end-to-end test |

**Faz 2 Sonucu:**
- Tüm kolonlar arası korelasyon korunur
- Customer→Account→Transaction FK zinciri korunur
- Zaman serisi pattern'ları korunur
- 3 synthesizer seçeneği (Stat/Copula/DL)

### Faz 3: Gizlilik ve Kalite (3 Hafta)

**Hedef:** Üretilen verinin güvenli ve ölçülebilir olması.

| Hafta | Görev | Effort | Çıktı |
|-------|-------|--------|-------|
| H7 | PrivacyGuard modülü | 3 gün | ε-DP noise injection, PII maskeleme |
| H7 | k-anonimlik kontrolü | 2 gün | Üretim sonrası anonimlik doğrulama |
| H8 | QualityEvaluator modülü | 3 gün | KL/JS, korelasyon farkı, ML utility |
| H8 | Privacy risk assessment | 2 gün | DCR, membership inference |
| H9 | Dashboard entegrasyonu | 3 gün | Kalite skoru kartları, dağılım grafikleri |
| H9 | Dokümantasyon ve eğitim | 2 gün | API docs, kullanım kılavuzu |

**Faz 3 Sonucu:**
- Diferansiyel gizlilik garantisi (ε parametrik)
- Her üretimde otomatik kalite raporu
- Gizlilik risk skoru
- Görsel dashboard

### Toplam Yol Haritası

```
HAFTA:  1───2───3───4───5───6───7───8───9
        ├─────────┤                         Faz 1: İstatistiksel (2 hafta)
                  ├─────────────────────┤   Faz 2: Korelasyon (4 hafta)
                                        ├──────────────┤ Faz 3: Gizlilik (3 hafta)
```

**Toplam süre:** 9 hafta  
**Minimum viable (Faz 1):** 2 hafta  
**Tam platform:** 9 hafta  

---

## 12. Referanslar

### Akademik Kaynaklar

1. Xu, L., Skoularidou, M., Cuesta-Infante, A., & Veeramachaneni, K. (2019). *Modeling Tabular Data using Conditional GAN.* NeurIPS.
2. Patki, N., Wedge, R., & Veeramachaneni, K. (2016). *The Synthetic Data Vault.* IEEE DSAA.
3. Kotelnikov, A. et al. (2023). *TabDDPM: Modelling Tabular Data with Diffusion Models.* ICML.
4. Sattarov, T. et al. (2023). *FinDiff: Diffusion Models for Financial Tabular Data Generation.* arXiv:2309.01472.
5. Faruman (2024). *Comparison of Financial Data Generation Methods.* GitHub benchmark.
6. Choi, E. et al. (2023). *Measuring Privacy Risks and Tradeoffs in Financial Synthetic Data Generation.* arXiv:2602.09288.
7. Roth, A. & Dwork, C. (2014). *The Algorithmic Foundations of Differential Privacy.* Foundations and Trends in TCS.
8. Wang, Y. et al. (2025). *TabKDE: Simple and Scalable Tabular Data Generation with KDE.* OpenReview.

### Kütüphane ve Araçlar

9. SDV — Synthetic Data Vault: https://sdv.dev
10. SynthEval: https://github.com/schneiderkamplab/syntheval
11. SynthGauge (UK ONS): https://github.com/datasciencecampus/synthgauge
12. IBM diffprivlib: https://github.com/IBM/differential-privacy-library
13. SciPy KDE: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html
14. scikit-learn GMM: https://scikit-learn.org/stable/modules/mixture.html

### Düzenleyici Kaynaklar

15. KVKK 6698 Sayılı Kanun — Kişisel Verilerin Korunması
16. BDDK — Bankaların Bilgi Sistemleri Yönetmeliği (BSEBY, 2020)
17. PCI-DSS 4.0 — Payment Card Industry Data Security Standard
18. Basel III — Operational Risk Framework
19. GDPR Recital 26 — Anonimleştirilmiş veri tanımı

---

*Bu doküman, BGTS Test Dönüşüm platformunun sentetik veri üretim yeteneklerini güçlendirmek için hazırlanmış kapsamlı bir araştırma ve analiz raporudur. Web araştırması, akademik kaynaklar ve mevcut kod analizi temel alınmıştır.*
