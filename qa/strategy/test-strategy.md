# Test Stratejisi — TestwrightAI

Bu doküman **"yeni bir test nereye yazılır?"** sorusunun tek cevabıdır.

## Test taksonomisi

Her test tipi için **tek bir doğru yer** var. Buradaki karar ağacını izle.

### Karar ağacı

```
Yeni test yazıyorum, neyi test ediyorum?
│
├─ Tek bir Python fonksiyon/class (DB/HTTP yok)
│  └─ backend/tests/unit/        (backend kodu için)
│     engine/tests/unit/         (engine kodu için)
│
├─ Backend API endpoint'i (DB + Redis + auth)
│  └─ backend/tests/integration/
│
├─ Engine API endpoint'i (Flask blueprint)
│  └─ engine/tests/integration/
│
├─ Backend ↔ Engine arası kontrat
│  └─ api-tests/contracts/
│
├─ HTTP-level API regression (external bakış)
│  └─ api-tests/
│
├─ Frontend component / hook
│  └─ apps/web/app/__tests__/
│
├─ Full user journey (frontend × backend × engine × DB)
│  └─ e2e/
│
├─ BDD scenario (müşteri okunur feature file)
│  └─ frameworks/playwright-cucumber-ts/features/
│
└─ Sentetik veri üretimi doğrulama
   └─ backend/tests/integration/synthetic/
```

## Her katmanın resmi yeri

| # | Kategori | Konum | Araç | Süre | Çalıştırma |
|---|---|---|---|---|---|
| 1 | Backend unit | `backend/tests/unit/` | pytest | < 100 ms / test | `make test-backend-unit` |
| 2 | Backend integration | `backend/tests/integration/` | pytest + testcontainers | < 5 s / test | `make test-backend-integration` |
| 3 | Engine unit | `engine/tests/unit/` | pytest | < 100 ms / test | `make test-engine-unit` |
| 4 | Engine integration | `engine/tests/integration/` | pytest + Flask test client | < 5 s / test | `make test-engine-integration` |
| 5 | API contract | `api-tests/contracts/` | pytest + schemathesis | < 10 s / test | `make test-contracts` |
| 6 | API regression | `api-tests/` | pytest + requests | < 30 s / test | `make test-service` |
| 7 | Frontend component | `apps/web/app/__tests__/` | Vitest + React Testing Library | < 1 s / test | `cd apps/web && npm test` |
| 8 | E2E full-stack | `e2e/` | Playwright | < 60 s / test | `make test-e2e` |
| 9 | BDD scenarios | `frameworks/playwright-cucumber-ts/features/` | Cucumber.js + Playwright | < 90 s / scenario | `cd frameworks/playwright-cucumber-ts && npx cucumber-js` |
| 10 | Smoke (critical paths) | karma — tag ile | hepsi | < 2 dk toplam | `make test-smoke` |

## Piramit

Hedef oran:

```
       /\         E2E + BDD       %5  (en az)
      /  \        (e2e/, frameworks/)
     /----\
    /      \      Integration     %25
   /--------\     (backend/tests/integration, engine/tests/integration, api-tests)
  /          \
 /------------\   Unit            %70 (en çok)
/______________\  (backend/tests/unit, engine/tests/unit, apps/web/__tests__)
```

## Tag'leme

Tüm testler pytest/playwright marker/tag'lerinden birini almalı:

### Pytest markers (`backend/`, `engine/`, `api-tests/`)

```python
# pyproject.toml / pytest.ini'de kayıtlı olmalı
markers = [
    "smoke: kritik yol, her PR'da çalışır",
    "regression: mevcut özellik koruması",
    "slow: >5s süren testler",
    "ai: LLM çağrısı yapan testler (ücret üretir)",
    "requires_db: PostgreSQL gerektirir",
    "requires_redis: Redis gerektirir",
]
```

Kullanım:

```python
@pytest.mark.smoke
def test_login_happy_path():
    ...

@pytest.mark.ai
@pytest.mark.slow
def test_llm_generates_valid_gherkin():
    ...
```

### Playwright tags (`e2e/`, `frameworks/playwright-cucumber-ts/`)

```typescript
test("@smoke login flow", async ({ page }) => { ... });
test("@regression password reset", async ({ page }) => { ... });
```

```gherkin
@smoke @auth
Scenario: Kullanıcı giriş yapar
  Given ...
```

## Make hedefleri (özet)

```bash
make test-smoke         # ~2 dk — her PR'da
make test-regression    # ~10 dk — nightly + pre-merge
make test-full          # ~20 dk — release öncesi
make test-backend       # backend/tests/ — unit + integration
make test-backend-unit  # sadece unit
make test-engine        # engine/tests/
make test-e2e           # e2e/
make test-service       # api-tests/
make test-contracts     # api-tests/contracts/
```

## Naming conventions

- **Dosya:** `test_<işin_konusu>.py` (pytest) / `<özellik>.spec.ts` (Playwright) / `<özellik>.feature` (Cucumber)
- **Fonksiyon:** `test_<davranış>_when_<durum>` → `test_login_returns_401_when_password_wrong`
- **Fixture:** `conftest.py`'de, module-scoped ise `_module`, session ise `_session` sonek

## Test data

| Veri türü | Nerede | Not |
|---|---|---|
| Fixture (statik) | `tests/fixtures/` | Check-in'lenir |
| Factory (dinamik) | `tests/factories/` | `factory_boy` veya plain funcs |
| Synthetic bank data | `synthetic-data/banking/` | Canlı servis, read-only |
| Allure attachments | `reports/allure/` | CI artifact, gitignored |
| Credentials | `frameworks/playwright-cucumber-ts/test-data/api-credentials.json` | **.gitignore'da**, kimse commit etmez |

## Flaky test politikası

1. Flaky olarak işaretlenen testler `@pytest.mark.flaky` veya `@flaky` tag'i alır
2. `backend/app/domains/tspm/` içindeki flaky karantina servisi bunları takip eder
3. 3 ardışık başarılı run'dan sonra karantinadan çıkar
4. 7 gün karantinada kalan testler sahibine atanır → düzelt veya sil

## Yeni bir test eklerken checklist

- [ ] Doğru konuma yazdım (yukarıdaki karar ağacına göre)
- [ ] Bir marker/tag verdim (en az `smoke` veya `regression`)
- [ ] Isolated (dış servis bağımlılığı yok veya mocked)
- [ ] Deterministik (zaman, rastgele, sıralama bağımsız)
- [ ] İsim davranışı anlatıyor, implementasyonu değil
- [ ] Assert sayısı test başına < 5 (ideal: 1)
- [ ] Teardown temiz (DB, dosya, cache)

## Pre-commit testleri

```yaml
# .pre-commit-config.yaml'da
- id: pytest-check
  stages: [pre-push]
  entry: bash -c 'cd backend && pytest -m "smoke" --timeout=60'
```

Pre-push'ta sadece smoke. Tam suite CI'da.

## Çakışma çözümü

Eğer bir test **birden fazla kategoriye** uyuyorsa:

1. **En üst piramit katmanında** başla (unit > integration > E2E)
2. Aynı kapsamı birden fazla katmanda test **ETME** (örn. login'i hem unit hem E2E)
3. E2E sadece "altyapı ve entegrasyon çalışıyor mu?" sorusunu yanıtlar — iş mantığını E2E ile doğrulama

## Eski test dizinlerinin taşınma planı

Root'taki `tests/` dizini eski, karışık içerik. Temizlik:

| Mevcut | Hedef | Tarih |
|---|---|---|
| `tests/test_faz0_3_integration.py` | `backend/tests/integration/` | 2026-05 |
| `tests/test_faz0_5_integration.py` | `backend/tests/integration/` | 2026-05 |

`tests/` dizini taşıma sonrası **silinecek**.

## Yardım

Bu karar ağacı bir davayı çözmüyorsa:

1. `#testing` Slack kanalı
2. Bu dokümana PR aç
3. Bir ADR yaz: `docs/adr/NNNN-test-karari.md`
