# BGTS Projeler Birleştirme Analizi
**Tarih:** 2026-04-06
**Hedef:** Üç BGTS projesini tek, üretim kalitesinde bir platform altında birleştirmek

---

## 1. Proje Envanteri

| # | Proje | Yol | Boyut | Durum |
|---|-------|-----|-------|-------|
| A | **BGTS Test Dönüşüm (Desktop)** | `/Users/yasin_bulgan/Desktop/BGTS_Test_Donusum` | 3 GB | Ana platform — en olgun |
| B | **BGTS Test Dönüşüm (Home)** | `/Users/yasin_bulgan/BGTS_Test_Donusum` | 34 MB | Yeni mimari temeli — bu repo |
| C | **BGTS Test Otomasyon (BGTSFLo)** | `/Users/yasin_bulgan/BGTSFLo/.claude/worktrees/*/test-automation` | ~1.2 MB | Hafif Python motoru |

**Karar:** Proje A birleşmenin **hedef reposu**, B ve C'nin benzersiz bileşenleri ona taşınacak.

---

## 2. Bileşen Karşılaştırma Matrisi

### 2.1 Backend / Core Katmanı

| Bileşen | Desktop (A) | Home (B) | Otomasyon (C) | Öneri |
|---------|------------|----------|---------------|-------|
| FastAPI Backend | ✅ Tam (13 domain) | ❌ | ❌ | A korunur |
| Flask Engine | ✅ Tam | Kısmi | ✅ Hafif | A korunur |
| AI Engine | ✅ Genişletilmiş | Kısmi | ✅ Temel | A korunur |
| Self-Healing Locator | ✅ (`self_healing/`) | ❌ | ❌ | A korunur |
| AI BDD Generator | ✅ (`ai_bdd/`) | ❌ | ❌ | A korunur |
| AI Security (ZAP) | ✅ (`ai_security/`) | ❌ | ❌ | A korunur |
| Analytics Engine | ✅ | ❌ | ❌ | A korunur |
| Banking Data Generator | ✅ | ❌ | ✅ | A korunur |
| Visual Regression | ✅ | ❌ | ❌ | A korunur |
| Monkey Test Engine | ✅ | ❌ | ❌ | A korunur |
| TypeScript Core (hooks, utils) | ❌ | ✅ | ❌ | **B'den ekle** |
| Multi-Agent Mimari | ❌ | ✅ (`services/agents/`) | ❌ | **B'den ekle** |

### 2.2 Test Framework Katmanı

| Framework | Desktop (A) | Home (B) | Otomasyon (C) | Öneri |
|-----------|------------|----------|---------------|-------|
| Playwright + TypeScript | ✅ (`playwright-cucumber-ts`) | ✅ | ❌ | A korunur, B'den hooks/utils ekle |
| Selenium + Java | ✅ (`selenium-cucumber-java`) | ❌ | ❌ | A korunur |
| pytest-bdd (Python) | ✅ | Kısmi | ✅ | A korunur |
| **Mobile Test Framework** | ❌ | ✅ (`frameworks/mobile`) | ❌ | **B'den ekle** |
| **Performance Test Framework** | ❌ | ✅ (`frameworks/performance`) | ❌ | **B'den ekle** |
| API Test Framework | Kısmi | ✅ (`frameworks/api`) | ❌ | **B'den genişlet** |

### 2.3 BDD / Feature Dosyaları

| Kategori | Desktop (A) | Home (B) | Öneri |
|----------|------------|----------|-------|
| BGTS senaryoları | ✅ | ❌ | A korunur |
| Otomasyonlar (TR) | ✅ | ❌ | A korunur |
| AI Generated | ✅ | ❌ | A korunur |
| API features | ✅ | ✅ | Birleştir |
| **Dönüşüm senaryoları** | ❌ | ✅ (`features/donusum`) | **B'den ekle** |
| **Data-Driven senaryolar** | ❌ | ✅ (`features/data_driven`) | **B'den ekle** |
| **Raporlama senaryoları** | ❌ | ✅ (`features/reporting`) | **B'den ekle** |
| **Web E2E senaryoları** | Var | ✅ (`features/web`, `e2e`) | **B'den ekle** |

### 2.4 Altyapı / DevOps

| Bileşen | Desktop (A) | Home (B) | Öneri |
|---------|------------|----------|-------|
| Docker Compose | ✅ Tam | Kısmi | A korunur |
| GitHub Actions CI/CD | ✅ | ✅ | A korunur, B'den ek step'ler ekle |
| **GitLab CI Pipeline** | ❌ | ✅ (`ci_cd/`) | **B'den ekle** |
| **Kubernetes (K8s)** | ❌ | ✅ (`k8s/deployment.yaml`) | **B'den ekle** |
| n8n Workflow | ✅ | ❌ | A korunur |
| Redis + RQ | ✅ | ❌ | A korunur |

---

## 3. Benzersiz Bileşenler (Eksik olan şeyler)

### Desktop'ta (A) OLMAYAN — Home (B)'den Eklenecekler

```
frameworks/mobile/          → engine/frameworks/mobile/
frameworks/performance/     → engine/frameworks/performance/
frameworks/api/             → engine/frameworks/api/ (genişletme)
core/typescript/            → ai-engine/src/core/ veya apps/web/lib/
services/agents/            → backend/app/domains/agents/ (zaten var? kontrol et)
features/donusum/           → engine/features/donusum/
features/data_driven/       → engine/features/data_driven/
features/reporting/         → engine/features/reporting/
features/web/               → engine/features/web/ (mevcut ile birleştir)
k8s/                        → infra/k8s/
ci_cd/ (GitLab CI)          → .gitlab-ci.yml
```

### Desktop'ta (A) OLMAYAN — Otomasyon (C)'den Eklenecekler

```
(BGTSFLo worktrees içeriği büyük ölçüde zaten Desktop'a taşınmış durumda)
(MERGER_PLAN.md'ye göre önceki birleştirme tamamlanmış)
→ Fark analizi için BGTSFLo README ile Desktop engine/core karşılaştırılmalı
```

---

## 4. Birleştirme Eylem Planı

### AŞAMA 1 — Framework Genişletme (Yüksek Öncelik)

**Hedef:** Desktop'a mobil ve performans test desteği ekle

```bash
# Mobile framework taşıma
cp -r /Users/yasin_bulgan/BGTS_Test_Donusum/frameworks/mobile/ \
      /Users/yasin_bulgan/Desktop/BGTS_Test_Donusum/engine/frameworks/mobile/

# Performance framework taşıma
cp -r /Users/yasin_bulgan/BGTS_Test_Donusum/frameworks/performance/ \
      /Users/yasin_bulgan/Desktop/BGTS_Test_Donusum/engine/frameworks/performance/

# API framework genişletme
cp -r /Users/yasin_bulgan/BGTS_Test_Donusum/frameworks/api/ \
      /Users/yasin_bulgan/Desktop/BGTS_Test_Donusum/engine/frameworks/api-extended/
```

**Gerekli değişiklik:**
- `engine/app.py`'a yeni framework blueprint'lerini kaydet
- `engine/requirements.txt`'e mobil/performans bağımlılıklarını ekle (Appium, Locust vb.)

---

### AŞAMA 2 — BDD Senaryoları Birleştirme (Yüksek Öncelik)

**Hedef:** Home'un BDD feature kategorilerini Desktop'a ekle

```bash
# Dönüşüm senaryoları
cp -r /Users/yasin_bulgan/BGTS_Test_Donusum/features/donusum/ \
      /Users/yasin_bulgan/Desktop/BGTS_Test_Donusum/engine/features/donusum/

# Data-driven senaryolar
cp -r /Users/yasin_bulgan/BGTS_Test_Donusum/features/data_driven/ \
      /Users/yasin_bulgan/Desktop/BGTS_Test_Donusum/engine/features/data_driven/

# Raporlama senaryoları
cp -r /Users/yasin_bulgan/BGTS_Test_Donusum/features/reporting/ \
      /Users/yasin_bulgan/Desktop/BGTS_Test_Donusum/engine/features/reporting/
```

---

### AŞAMA 3 — TypeScript Core Entegrasyonu (Orta Öncelik)

**Hedef:** Home'un TypeScript yardımcılarını `ai-engine` altına taşı

```
core/typescript/hooks.ts  → ai-engine/src/hooks/
core/typescript/utils/    → ai-engine/src/utils/
core/typescript/pages/    → ai-engine/src/pages/
core/typescript/steps/    → ai-engine/src/steps/
```

**Not:** `ai-engine/package.json`'a gerekli bağımlılıklar eklenmeli.

---

### AŞAMA 4 — Kubernetes Altyapısı (Orta Öncelik)

**Hedef:** K8s deployment desteği ekle

```bash
mkdir -p /Users/yasin_bulgan/Desktop/BGTS_Test_Donusum/infra/k8s/

cp /Users/yasin_bulgan/BGTS_Test_Donusum/k8s/deployment.yaml \
   /Users/yasin_bulgan/Desktop/BGTS_Test_Donusum/infra/k8s/deployment.yaml

cp /Users/yasin_bulgan/BGTS_Test_Donusum/k8s/service.yaml \
   /Users/yasin_bulgan/Desktop/BGTS_Test_Donusum/infra/k8s/service.yaml
```

**Gerekli güncellemeler:**
- K8s manifestlerindeki image adlarını Desktop docker-compose servisleriyle eşleştir
- `backend`, `engine`, `frontend` için ayrı Deployment + Service tanımla
- Gizli bilgiler için Kubernetes Secret ekle

---

### AŞAMA 5 — GitLab CI Ekle (Düşük Öncelik)

**Hedef:** Mevcut GitHub Actions'a ek olarak GitLab CI desteği

```bash
cp /Users/yasin_bulgan/BGTS_Test_Donusum/ci_cd/.gitlab-ci.yml \
   /Users/yasin_bulgan/Desktop/BGTS_Test_Donusum/.gitlab-ci.yml
```

**Gerekli güncellemeler:**
- GitLab CI dosyasındaki stage'leri Desktop'ın proje yapısına göre güncelle
- Docker image build adımlarını Desktop'ın Dockerfile'larına yönlendir

---

### AŞAMA 6 — Multi-Agent Mimari (Düşük Öncelik)

**Hedef:** Home'un agent mimarisini değerlendir ve Desktop backend'e entegre et

```
services/agents/  → backend/app/domains/agents/ ile karşılaştır
```

Desktop'ta zaten `backend/app/domains/agents/` mevcut.
Home'dakinin farklı/ek logic içerip içermediği incelenmeli.

---

## 5. Çakışma / Risk Matrisi

| Risk | Etki | Çözüm |
|------|------|-------|
| Mobile framework bağımlılıkları (Appium) Docker image boyutunu artırır | Orta | Ayrı `engine-mobile` Dockerfile |
| Performance framework (Locust) engine portunu kullanıyor olabilir | Düşük | Ayrı port (5003) veya servis |
| BDD feature dosyalarındaki step tanımları çakışabilir | Düşük | `conftest.py` merge edilmeli |
| K8s manifestlerindeki port değerleri docker-compose ile uyumsuz olabilir | Orta | `.env` ile parametre haline getir |
| TypeScript core, ai-engine'deki mevcut utils ile çakışabilir | Düşük | Namespace altında topla |

---

## 6. Hedef Mimari (Birleştirme Sonrası)

```
BGTS_Test_Donusum/ (Desktop — Hedef Repo)
├── apps/web/                    # Next.js 14 (mevcut)
├── backend/                     # FastAPI + 13 domain (mevcut)
├── engine/                      # Flask Test Motoru
│   ├── core/                    # 30+ AI/test modülü (mevcut)
│   ├── frameworks/
│   │   ├── playwright-cucumber-ts/   # Mevcut
│   │   ├── selenium-cucumber-java/   # Mevcut
│   │   ├── mobile/              # ← B'den EKLENECEKile
│   │   ├── performance/         # ← B'den EKLENECEKile
│   │   └── api-extended/        # ← B'den EKLENECEKile
│   └── features/
│       ├── BGTS/                # Mevcut
│       ├── Otomasyonlar/        # Mevcut
│       ├── donusum/             # ← B'den EKLENECEKile
│       ├── data_driven/         # ← B'den EKLENECEKile
│       └── reporting/           # ← B'den EKLENECEKile
├── ai-engine/                   # TypeScript CLI
│   └── src/
│       ├── core/                # Mevcut + ← B'den hooks/utils
│       └── ...
├── infra/
│   ├── docker-compose.yml       # Mevcut
│   ├── k8s/                     # ← B'den EKLENECEKile
│   └── ...
├── .github/workflows/           # Mevcut
├── .gitlab-ci.yml               # ← B'den EKLENECEKile
└── ...
```

---

## 7. Yürütme Sırası ve Tahmini Çaba

| Aşama | İş | Çaba | Öncelik |
|-------|-----|------|---------|
| 1 | Framework taşıma (mobile + performance) | 2 saat | Yüksek |
| 2 | BDD feature birleştirme | 1 saat | Yüksek |
| 3 | TypeScript core entegrasyonu | 2 saat | Orta |
| 4 | Kubernetes altyapısı | 3 saat | Orta |
| 5 | GitLab CI ekleme | 30 dk | Düşük |
| 6 | Multi-agent inceleme | 1 saat | Düşük |
| **Toplam** | | **~9.5 saat** | |

---

## 8. Sonraki Adım

Birleştirmeye başlamak için hangi aşamayı önce ele alalım?

- **[ ] Aşama 1** — Mobile + Performance frameworks ekle
- **[ ] Aşama 2** — BDD senaryoları birleştir
- **[ ] Aşama 3** — TypeScript core entegrasyonu
- **[ ] Aşama 4** — Kubernetes altyapısı
- **[ ] Tümü**  — Sırayla hepsini uygula
