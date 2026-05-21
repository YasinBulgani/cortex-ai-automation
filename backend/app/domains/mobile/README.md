# BGTS — Mobile Automation Domain

Appium 2.x + LLM tabanlı mobil test otomasyonu. Bu domain BGTS'nin web/API
test omuzuna mobil kanalı ekler.

## Modül Haritası

```
backend/app/domains/mobile/
├── __init__.py
├── schemas.py          # Pydantic — Device, Session, AppiumAction, ...
├── device_broker.py    # Thread-safe in-memory cihaz registry (10 seed)
├── llm_stepper.py      # NL → Appium adımları (AI Gateway + TR heuristic)
├── self_healing.py     # RETRY / REWRITE / UI_CHANGED karar motoru
├── visual_verifier.py  # Multimodal vision LLM (F2'de aktif)
├── orchestrator.py     # Paralel session + SSE event store
├── appium_client.py    # httpx tabanlı WebDriver istemcisi
├── seed_scenarios.py   # 10 hazır mobil senaryo (auth, ecom, bank, a11y)
└── router.py           # 14 endpoint / /api/v1/mobile/*
```

## API Endpoint'leri

| Yöntem | URL | Açıklama |
|---|---|---|
| GET | `/api/v1/mobile/devices` | 10 cihazı listele |
| GET | `/api/v1/mobile/devices/{id}` | Tek cihaz |
| POST | `/api/v1/mobile/devices/{id}/reboot` | Yeniden başlat |
| POST | `/api/v1/mobile/enroll-physical` | Fiziksel cihaz kayıt |
| GET | `/api/v1/mobile/stats` | Farm istatistikleri |
| POST | `/api/v1/mobile/generate-from-prompt` | NL → Appium adımları |
| POST | `/api/v1/mobile/sessions` | N cihazda paralel koşu başlat |
| GET | `/api/v1/mobile/sessions` | Son koşular |
| GET | `/api/v1/mobile/sessions/{id}` | Tek session |
| GET | `/api/v1/mobile/sessions/{id}/stream` | **SSE canlı event akışı** |
| POST | `/api/v1/mobile/visual-verify` | Screenshot assertion (LLM) |
| GET | `/api/v1/mobile/scenarios/seed` | Hazır senaryo galerisi (filtreli) |
| GET | `/api/v1/mobile/scenarios/seed/categories` | Kategori listesi |
| GET | `/api/v1/mobile/scenarios/seed/{id}` | Tek seed senaryo |

## LLM Stepper Katmanları

1. **Primary**: AI Gateway — GPT-4o / Gemini 2 Flash (`/ai/complete` çağrısı).
2. **Fallback**: Türkçe-dayanıklı heuristic stepper (`_heuristic_stepper`).
   - İ/I çevirimi için `_tr_lower` yardımcı fonksiyonu.
   - Login, onboarding, arama+sepet, çıkış, ana sayfa doğrulama pattern'leri.
3. **Grounding**: Varsa Appium page source (8KB kırpılmış) prompt'a eklenir.

## Self-Healing Kararları

| retry_count | Karar | Aksiyon |
|:---:|---|---|
| 0 | `RETRY` | Timeout 2x artır |
| 1 | `REWRITE` (AID varsa) | `accessibilityId` → xpath fallback |
| ≥2 | `UI_CHANGED` | Testi quarantine'a al |

`HealSuggestion.confidence` alanı her kararla birlikte döner.

## Cihaz Seed'i

10 sanal cihaz otomatik oluşur:

- **Android (6)**: Pixel 8/8 Pro (API 34), Galaxy S23 (API 33), Pixel 6 (API 32), Pixel 5 (API 30), Nexus 5X (API 28, default **offline**).
- **iOS (4)**: iPhone 15 Pro, iPhone 15, iPhone 14, iPhone SE 3rd gen.

Port eşlemesi: `4723 + i` (Android), `4730 + j` (iOS).

## Fiziksel Cihaz Kaydı

`POST /api/v1/mobile/enroll-physical` payload:
```json
{
  "name": "Lab-01 Samsung S24",
  "platform": "android",
  "os_version": "14",
  "udid": "R58M3XYZ",
  "appium_url": "http://lab-1.bgts.internal:4750",
  "profile": "samsung_s24"
}
```

Handshake akışı (F2'de otomatik): ADB `devices -l` kontrolü (Android) veya
`xcrun simctl describe-device` (iOS) + Appium `status` endpoint probe.

## Test Suite

```bash
# Tüm mobile testleri
cd backend && pytest tests/mobile/ -v

# Sadece unit
pytest tests/mobile/ -v -m "not integration"

# Gerçek Appium ile integration testleri (macOS + Appium çalışıyor olmalı)
APPIUM_URL=http://127.0.0.1:4723 pytest tests/mobile/ -v -m integration
```

Mevcut durum: **105 unit test yeşil, 2 integration (Appium gereksinimi varsa).**

## Mimari İlişkiler

```
UI  ──────►  Router  ──────►  Orchestrator  ──────►  AppiumClient
                │                  │                        │
                ├──► DeviceBroker  ├──► LLMStepper          │
                │                  │       │                 │
                │                  │       └──► AI Gateway   │
                │                  │                        │
                │                  ├──► SelfHealing          │
                │                  │                        │
                │                  └──► VisualVerifier       │
                │                                           ▼
                └──► SeedScenarios                    Appium Server
                                                            │
                                                      ┌─────┴─────┐
                                                      │ AVD / Sim │
                                                      └───────────┘
```

## Yol Haritası Durumu

- [x] **F0 — Prototip** (UI + mock + rapor)
- [x] **F1 — MVP Sanal** (iskelet) — backend domain, router, LLM stepper, orchestrator, 105 test
- [ ] **F1 — MVP Sanal** (tamamlama) — `appium_client.py` gerçek AVD ile smoke
- [ ] **F2 — Self-Healing v2** (vision LLM entegrasyonu)
- [ ] **F3 — Fiziksel 10 Cihaz**
- [ ] **F4 — K8s Ölçek (100+ cihaz)**
- [ ] **F5 — Agentic Test Exploration**

Detaylı plan: [`docs/MOBIL_OTOMASYON_ARASTIRMA_RAPORU.md`](../../../../docs/MOBIL_OTOMASYON_ARASTIRMA_RAPORU.md)

## Gerçek Appium ile Smoke (Lokal)

```bash
# 1) AVD başlat
./infra/mobile/avd-provisioner.sh
emulator -avd bgts_pixel_8 &

# 2) Appium server
appium server --port 4723 --allow-cors &

# 3) Backend
cd backend && uvicorn app.main:app --reload

# 4) Kendiliğinden akış: UI'da /mobil-otomasyon → Senaryo Galerisi → "Başarılı Giriş"
#    → "🚀 Paralel Koş" → gerçek Appium'a iletilir, SSE stream UI'ı günceller.
```

## Katkıda Bulunma

- Yeni seed senaryo: `seed_scenarios.py` içine `SeedScenario(...)` ekle, test
  `test_seed_scenarios.py::TestSeedPromptsAreStepable` parametrize'da
  otomatik çalışır.
- Yeni locator stratejisi: `appium_client.py::LOCATOR_STRATEGIES` sözlüğüne
  ekle, self-healing'te de kabul görür.
- Yeni heuristic pattern: `llm_stepper.py::_heuristic_stepper` içine
  `if "anahtar_kelime" in p:` bloğu ekle, mutlaka test yaz.
