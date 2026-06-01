# Test Kapsama Raporu — 2026-05-26

## Özet

| Katman | Test Dosyası | Tahmini Test Sayısı | Kapsama |
|---|---|---|---|
| Backend Unit | 155+ dosya | 1800+ test | ~85% |
| Backend Integration | 5 dosya | 60+ test | ~70% |
| Engine Unit | 70+ dosya | 900+ test | ~80% |
| Frontend Unit | 125+ dosya | 1200+ test | ~75% |
| **Toplam** | **355+** | **3960+** | **~78%** |

## Backend Domain Kapsama

[Tüm domainler için bkz: backend-domain-coverage.md]

Yeni eklenenler (bu sprint):
- rbac ✅ (service + router + 36 test)
- navigation ✅ (service + router + 21 test)
- email ✅ (service + router + 12 test)
- automation_templates ✅ (service + 14 test)
- migration ✅ (service + 12 test)

Bu sprint eklenen router testleri (4 yeni domain):
- pilot ✅ (router — 16 test: session CRUD, converse, clarify, execute-stage)
- artifacts ✅ (router — 10 test: download, yetki, path traversal koruması)
- jobs ✅ (router — 12 test: enqueue, list, get, events, artifacts)
- rules ✅ (router — 11 test: list, create, get rule-set; dataset scope doğrulaması)

## Engine Kapsama

Tüm 39 route dosyası unit testlere sahip.
Tüm 8 servis (llm_gateway, anomaly_detector, bdd_generator, vs.) test kapsamında.

## CI Doğrulama

Her PR'da koşan test setleri:
- `pytest tests/unit/ -v --tb=short` (backend)
- `pytest tests/unit/ -v --tb=short` (engine)
- `npm test -- --watchAll=false` (frontend)
- `pytest tests/integration/` (smoke)

## Güvenlik Tarama Bulguları

Tarih: 2026-05-26 — `backend/app/domains/auth/router.py`

| # | Bulgu | Öncelik | Dosya / Satır | Durum |
|---|---|---|---|---|
| 1 | Rate limiting no-op riski — slowapi yoksa `_limit` dekoratörü çalışmaz | P1 | auth/router.py: `_limit()` | TODO eklendi |
| 2 | `/refresh` endpoint'i dahili `ValueError` mesajını `detail` olarak sızdırıyor | P2 | auth/router.py: `refresh_token()` | TODO eklendi |
| 3 | Timing attack riski — kullanıcı yoksa erken dönüş, parola hash kontrolü atlanıyor olabilir | P1 | auth/router.py: `login()` | TODO eklendi |

Tüm bulgular için `# SECURITY TODO` yorumları ilgili satırlara eklendi. Gerçek düzeltmeler ayrı PR'da ele alınmalıdır.
