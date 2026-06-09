# CI/CD Test Automation Pipeline

Cortex AI Automation platform için GitHub Actions tabanlı test otomasyonu pipeline'ı.

## Pipeline Özeti

- **Workflow File**: `.github/workflows/test-automation.yml`
- **Trigger**: Push (main, develop, feature/qa-system-bootstrap) ve Pull Request
- **Toplam Süre**: ~15-20 dakika
- **Parallelization**: E2E testleri 2 shard'da parallel çalışır

## Pipeline Aşamaları

### Stage 1: Unit Tests (3 dakika)
- Backend unit tests (pytest)
  - Coverage: minimum 70%
  - Markers: `not ai and not slow and not requires_docker`
- Engine unit tests (Flask service)
  - Markers: `not ai and not integration`
- **Artifacts**: 
  - `backend/coverage.xml`
  - Coverage report HTML

**Run Komutu**:
```bash
make test-unit-ci
```

### Stage 2: API Tests (5 dakika)
- Contract tests (OpenAPI spec compliance)
- Integration tests (endpoint functionality)
- Database: PostgreSQL 16
- Cache: Redis 7
- **Run Komutu**:
```bash
make test-api-ci
```

### Stage 3: Frontend Tests (5 dakika)
- TypeScript type check (`tsc --noEmit`)
- ESLint style check
- Jest unit tests with coverage
- Next.js build verification
- **Run Komutu**:
```bash
make test-ui-ci
```

### Stage 4: E2E Tests (10 dakika)
- Playwright tests (Chromium)
- 2 shard'da parallel execution (shard 1/2 ve 2/2)
- Backend + Frontend entegrasyonu
- **Artifacts**:
  - Playwright HTML reports
  - Test results (XML)
- **Run Komutu**:
```bash
make test-ui-ci
```

### Stage 5: Smoke Tests (3 dakika)
- Hızlı sanity check (PR'lar için)
- Backend smoke markers
- Frontend smoke E2E testleri
- **Run Komutu**:
```bash
make test-smoke-ci
```

### Stage 6: Test Summary & Notifications
- Tüm job'ların durumunu topla
- Slack bildirimi gönder (başarı/başarısızlık)
- Test artifact'larını rapor et

## Slack Notification Kurulumu

### 1. Slack App Oluştur

1. [api.slack.com](https://api.slack.com) adresine git
2. **Create New App** → **From scratch** seç
3. App name: `Cortex CI/CD` (veya istediğin ad)
4. Workspace seç

### 2. Incoming Webhooks Aktifleştir

1. Sol menüden **Incoming Webhooks** seç
2. **Activate Incoming Webhooks** aç
3. **Add New Webhook to Workspace** tıkla
4. Notification göndermek istediğin channel'ı seç (örn: `#ci-deployments`)
5. **Allow** tıkla
6. Webhook URL'yi kopyala (şu formatı taşıyacak):
   ```
   https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
   ```

### 3. GitHub Secrets'a Ekle

1. Repository → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** tıkla
3. Name: `SLACK_WEBHOOK_URL`
4. Value: Yukarıda kopyladığın Webhook URL
5. **Add secret** tıkla

### 4. Webhook URL'nin Format Doğrulama

```bash
curl -X POST https://hooks.slack.com/services/T00000000/B00000000/XXXX \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test message from GitHub Actions"}'
```

## Lokal Çalıştırma

Aynı test setlerini CI olmadan lokal geliştirme sırasında çalıştırmak için:

### Tüm Test Otomasyonunu Çalıştır
```bash
make test-automation
```

### Tek Tek Aşamaları Çalıştır
```bash
# Unit tests
make test-unit-ci

# API tests (gerektirir: running backend)
make test-api-ci

# Frontend + E2E tests
make test-ui-ci

# Smoke tests
make test-smoke-ci
```

### Altyapıyı Kurarak Çalıştır
```bash
# PostgreSQL + Redis başlat
make docker-up

# Backend API başlat
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend başlat (başka terminal)
cd apps/web && npm run dev

# Testleri çalıştır
make test-automation
```

## Artifacts

Pipeline'ın ürettiği artifacts:

### Backend Coverage
- **Path**: `backend/coverage.xml`
- **Name**: `backend-coverage-<run_id>`
- **Retention**: 14 gün
- **Format**: Cobertura XML

### Jest Coverage
- **Path**: `apps/web/coverage/`
- **Name**: `jest-coverage-<run_id>`
- **Retention**: 14 gün

### Playwright Reports
- **Path**: `playwright-report/`
- **Name**: `playwright-report-<run_id>-shard-<n>`
- **Format**: HTML (interaktif)
- **Retention**: 14 gün

### E2E Test Results
- **Path**: `test-results/`
- **Name**: `e2e-results-<run_id>-shard-<n>`
- **Format**: JUnit XML

## Konfigürasyon

### Coverage Thresholds

Backend unit tests minimum coverage'ı: **70%**
```yaml
--cov-fail-under=70
```

Düşük gibi görünüyorsa, mevcut coverage'ı kontrol et:
```bash
cd backend && python -m pytest tests/unit/ --cov=app --cov-report=term-missing
```

### Timeout'lar

- Unit Tests: 15 dakika
- API Tests: 15 dakika
- Frontend Tests: 15 dakika
- E2E Tests: 25 dakika (2 shard parallel)
- Smoke Tests: 10 dakika

Bir stage timeout'a uğrarsa, Makefile'daki `timeout` parameter'lerini artır.

### Test Markers

Workflow'ün kullandığı pytest markers:

```python
@pytest.mark.smoke            # Hızlı sanity check
@pytest.mark.ai               # AI integration gerektirir (skip)
@pytest.mark.slow             # Uzun çalışan (skip)
@pytest.mark.requires_docker  # Docker gerektirir (skip)
@pytest.mark.requires_db      # Database gerektirir (skip)
@pytest.mark.requires_redis   # Redis gerektirir (skip)
```

## Troubleshooting

### "Frontend timeout" — Hata

```
Error: Timeout waiting for frontend on port 3000
```

**Çözüm**: Next.js build hatasını kontrol et
```bash
cd apps/web && npm run build
```

### "Database connection refused" — Hata

```
postgresql://postgres:postgres@localhost:5432/test_db: connection refused
```

**Çözüm**: PostgreSQL image'inin healthy olmasını bekle
```bash
docker ps -a | grep postgres
```

### Slack bildirimi alınmıyor

1. Webhook URL'nin doğru olup olmadığını kontrol et:
   - Repository Settings → Secrets → SLACK_WEBHOOK_URL
2. URL'nin format'ını doğrula (https://hooks.slack.com/services/...)
3. Channel'ın app'e invite edilmiş olup olmadığını kontrol et

### Test flakiness'i

E2E testleri timeout'a uğrarsa:
1. **Parallelization'ı azalt** (`--shard=1/1` yap)
2. **Timeout'ları artır** (test dosyalarında `timeout: 30s`)
3. **Wait'leri ekle** (busy-wait yerine polling)

## GitHub Actions Secrets Checklist

Repository secrets'ında şunlar olmalı:

- [ ] `SLACK_WEBHOOK_URL` — Slack incoming webhook URL
- [ ] (Opsiyonel) `SENTRY_DSN` — Error tracking
- [ ] (Opsiyonel) `CODECOV_TOKEN` — Coverage upload

## Monitoring

### Real-time Logs

GitHub Actions UI'dan:
1. Repository → **Actions** sekmesi
2. Son workflow run'ını tıkla
3. Job'ı tıkla → **Run** stepsini genişlet

### Coverage Trends

```bash
# Local'de Coverage raporu aç
make report
```

HTML reports:
- Backend: `reports/backend-coverage/index.html`
- Jest: `apps/web/coverage/index.html`

### Slack Notifications

**Başarılı pipeline**:
```
Test Pipeline Passed ✅
Branch: main
Commit: a1b2c3d...
```

**Başarısız pipeline**:
```
Test Pipeline Failed 🔴
Branch: feature/qa-system-bootstrap
Commit: x9y8z7w...
Author: @developer

Unit Tests: failure
API Tests: success
Frontend Tests: success
E2E Tests: failure
```

## Best Practices

1. **Test markers'ı doğru kullan** — AI testleri `@pytest.mark.ai` ile işaretle
2. **Coverage'ı 70% üzerinde tut** — Critical path'ler için 80%+ hedefle
3. **E2E testleri deterministic yaz** — Timing assumptions yap'ma
4. **Timeout'ları realistik set et** — CI'da 2x hızlı değildir
5. **Artifacts'ları kontrol et** — Failed test'ler her zaman rapor yapılandır

## Repository Workflow Status

Workflow'un aktif olup olmadığını kontrol et:

```bash
# GitHub CLI
gh workflow list

# Web UI
Repository → Actions → "Test Automation Pipeline"
```

## Kaynaklar

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Slack Webhooks API](https://api.slack.com/messaging/webhooks)
- [Playwright Documentation](https://playwright.dev/)
- [pytest Documentation](https://docs.pytest.org/)

---

**Son Güncelleme**: 2026-06-09
**Maintained By**: Cortex AI Team
