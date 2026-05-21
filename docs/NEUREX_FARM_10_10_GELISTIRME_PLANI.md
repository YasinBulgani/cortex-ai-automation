# Neurex Farm 10/10 Master Gelistirme Plani

> Hedef: 2 cihazla baslayan ama urun kalitesi, guvenilirlik, kanit uretimi ve mimari netligi acisindan 10/10 seviyesinde bir mobil test farm'i kurmak.
>
> Ilke: Cihaz sayisi kalite degildir. **Iki cihazla gercek, olculebilir, tekrarlanabilir ve kanitli kosum**; on cihazlik simule dashboard'dan daha degerlidir.

---

## 0. Urun Vaadi

Neurex Farm su cumleyi gercek kilar:

> "Bir QA ekibi, mobil uygulamasini iki gercek hedef cihazda ayni anda kosturur; canli log, ekran goruntusu, adim sonucu ve kalici raporu tek yerden gorur. Sistem hata saklamaz, cihaz durumunu bilir, ayni cihaza iki is bindirmez ve run bittiginde kanit birakir."

Bu planin 10/10 tanimi budur. Ilk surumde 100 cihaz, Kubernetes operator, LLM agent, real-device lab sart degildir. Ilk surumde zorunlu olan sey **calismasidir**.

---

## 1. Basari Tanimi

Farm ancak asagidakiler dogruysa 10/10 sayilir:

| Alan | 10/10 Beklenti |
|---|---|
| Gerceklik | Run sonucu simulasyonla uretilmez; Appium/WebDriver gercek komut calistirir. |
| Kucuk kapsam | Ilk destek 2 cihazdir; her ikisi de saglam calisir. |
| Tek API | UI ve servisler tek canonical API kullanir: `/api/v1/mobile/*`. |
| Cihaz bilgisi | Sistem cihaz online/offline/busy/errored durumunu bilir. |
| Lease | Ayni cihaz ayni anda iki run alamaz. |
| Kanit | Her run log, step sonucu, screenshot ve metadata kaydeder. |
| Canli izleme | UI, SSE/WebSocket ile run'i gercek zamanli gosterir. |
| Kalicilik | Backend restart sonrasi run gecmisi ve artifact'lar gorulur. |
| Hata durusu | Appium, ADB, simulator veya app hatasi net gorunur; fake pass yoktur. |
| Testlenebilirlik | Otomatik smoke testi farm'in calistigini kanitlar. |

---

## 2. Net Strateji

### 2.1 Once 2 Cihaz

Ilk resmi hedef:

- Cihaz A: Android emulator veya fiziksel Android
- Cihaz B: iOS Simulator veya ikinci Android emulator

iOS hazir degilse 2 Android kabul edilir. Fakat mimari iOS'u dislamaz.

### 2.2 Once Deterministik Runner

LLM once degil, sonra gelir. Ilk 10/10 surumde run su sekilde baslar:

- UI veya API deterministic JSON step listesi gonderir.
- AppiumRunner bu step'leri gercek cihazda calistirir.
- LLM sadece sonraki fazda bu JSON step listesini ureten katman olur.

Bu karar kritik: AI yanlis uretirse farm suclu gibi gorunmemeli. Once runner dogru olmali.

### 2.3 Tek Canonical API

Yeni tum urun akisi:

```text
UI -> FastAPI /api/v1/mobile/* -> AppiumRunner -> Appium server -> Device
```

Engine/Flask `/api/mobile/*` gecis doneminde adapter olabilir, ama yeni UI akisi oraya dogrudan baglanmamalidir.

---

## 3. Mevcut Durumdan Cikan Ana Riskler

| Risk | Bugunku Belirti | Etki | Cozum |
|---|---|---|---|
| Iki farkli farm yuzeyi | `/api/v1/mobile/*` ve `/api/mobile/*` birlikte yasiyor | UI/Backend uyumsuzlugu | `/api/v1/mobile` canonical yap |
| Simule sonuc | Orchestrator `pass_rate` ile sonuc uretiyor | Demo guveni duser | Prod akistan simulasyonu cikar |
| In-memory state | Device/session state process icinde | Restartta veri kaybi | DB + artifact store |
| Lease yok | Cihaz secimi sadece status filtresi | Ayni cihaza iki run binebilir | DB/Redis lease |
| UI endpoint kopuklugu | `/api/mobile/run-live` izi var | Run butonu kirilabilir | UI API sozlesmesini temizle |
| Artifact eksigi | Screenshot/log kalici degil | Debug ve musteri kaniti yok | Artifact pipeline |
| Appium lifecycle belirsiz | Server/probe/driver setup net degil | Kurulum kirilgan | Health/provisioning komutlari |

---

## 4. Hedef Mimari

```text
┌─────────────────────────────────────────────────────────────┐
│ UI: /p/:projectId/mobile                                    │
│ - device list                                               │
│ - run launcher                                              │
│ - live stream                                               │
│ - history + artifact viewer                                 │
└─────────────────────────────┬───────────────────────────────┘
                              │ REST + SSE
┌─────────────────────────────▼───────────────────────────────┐
│ FastAPI Mobile Domain: /api/v1/mobile                       │
│                                                             │
│ DeviceRegistry   DB-backed cihaz ve health bilgisi          │
│ LeaseManager     TTL'li cihaz kiralama                      │
│ RunOrchestrator  paralel session yonetimi                   │
│ AppiumRunner     gercek WebDriver komutlari                 │
│ ArtifactStore    screenshot, page source, log, video        │
│ EventBus         SSE event persistence + live publish       │
└─────────────────────────────┬───────────────────────────────┘
                              │ HTTP WebDriver
┌─────────────────────────────▼───────────────────────────────┐
│ Appium Servers                                               │
│ - 4723 Android A                                             │
│ - 4724 Android B veya iOS Simulator                          │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│ Devices                                                      │
│ - Android emulator/physical                                  │
│ - iOS Simulator/physical later                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Veri Modeli

### 5.1 `mobile_devices`

Zorunlu alanlar:

- `id`
- `project_id` nullable, shared farm icin null olabilir
- `name`
- `platform`: `android | ios`
- `kind`: `emulator | simulator | physical`
- `udid`
- `appium_url`
- `os_version`
- `model`
- `status`: `offline | idle | busy | booting | error`
- `last_seen_at`
- `last_error`
- `capabilities_json`

### 5.2 `mobile_sessions`

- `id`
- `project_id`
- `run_group_id`
- `device_id`
- `status`: `queued | running | passed | failed | cancelled | timed_out`
- `scenario_name`
- `app_ref`
- `started_at`
- `finished_at`
- `duration_ms`
- `failure_category`: `appium | device | app | assertion | timeout | infrastructure`
- `failure_message`

### 5.3 `mobile_steps`

- `id`
- `session_id`
- `seq`
- `action`
- `locator_json`
- `input_json`
- `status`
- `started_at`
- `finished_at`
- `duration_ms`
- `error_message`
- `screenshot_artifact_id`
- `page_source_artifact_id`

### 5.4 `mobile_artifacts`

- `id`
- `session_id`
- `step_id` nullable
- `kind`: `screenshot | page_source | stdout | appium_log | video | junit`
- `path`
- `mime_type`
- `size_bytes`
- `created_at`
- `sha256`

### 5.5 `mobile_device_leases`

- `device_id`
- `session_id`
- `lease_owner`
- `expires_at`
- `created_at`

Lease TTL zorunludur. Process crash olursa lease kendi kendine temizlenmelidir.

---

## 6. API Sozlesmesi

Canonical endpoint'ler:

| Method | Path | Amac |
|---|---|---|
| GET | `/api/v1/mobile/devices` | Cihazlari health ve lease durumuyla listele |
| POST | `/api/v1/mobile/devices/probe` | ADB/simctl/Appium health yenile |
| POST | `/api/v1/mobile/devices/{id}/reboot` | Gercek reboot/boot islemi |
| POST | `/api/v1/mobile/sessions` | Tek veya cok cihazli run baslat |
| GET | `/api/v1/mobile/sessions` | Gecmis run listesi |
| GET | `/api/v1/mobile/sessions/{id}` | Session detay |
| GET | `/api/v1/mobile/run-groups/{id}` | Paralel run grup ozeti |
| GET | `/api/v1/mobile/sessions/{id}/stream` | Tek session SSE |
| GET | `/api/v1/mobile/run-groups/{id}/stream` | Grup SSE |
| GET | `/api/v1/mobile/artifacts/{id}` | Artifact indir/goster |
| POST | `/api/v1/mobile/steps/generate` | LLM sonra: NL -> steps |

### 6.1 Run Baslatma Payload

```json
{
  "project_id": "project-uuid",
  "scenario_name": "Smoke login",
  "device_ids": ["and-pixel-8", "and-pixel-6"],
  "app": {
    "type": "web",
    "url": "https://example.com"
  },
  "steps": [
    {"action": "openUrl", "url": "https://example.com"},
    {"action": "find", "by": "accessibilityId", "value": "login"},
    {"action": "tap"},
    {"action": "screenshot"}
  ],
  "timeouts": {
    "session_ms": 120000,
    "step_ms": 10000
  }
}
```

### 6.2 SSE Event Tipleri

```text
session.started
device.lease_acquired
step.started
step.log
step.screenshot
step.passed
step.failed
device.lease_released
session.passed
session.failed
run_group.done
```

Her event `session_id`, `device_id`, `timestamp`, `seq` ve `payload` tasimalidir.

---

## 7. Appium Runner Standardi

Runner su kurallarla yazilmali:

- Her session sonunda `quit` mutlaka cagrilir.
- Step timeout session timeout'tan ayridir.
- Her failed step'te screenshot ve page source alinmaya calisilir.
- Appium hatasi ile assertion hatasi ayrilir.
- Locator bulunamazsa bu direkt `assertion` degil, `locator` failure olarak isaretlenir.
- Device/Appium health fail ise run baslamadan `infrastructure` fail olur.
- Retry politikasi kontrolludur; sonsuz retry yoktur.

### 7.1 Desteklenecek Ilk Aksiyonlar

| Action | Aciklama |
|---|---|
| `openUrl` | Mobil web smoke icin URL ac |
| `launchApp` | Native app baslat |
| `find` | Element bul ve current element yap |
| `tap` | Current element'e dokun |
| `sendKeys` | Current element'e metin yaz |
| `verifyVisible` | Element gorunurlugunu dogrula |
| `wait` | Kontrollu bekleme |
| `back` | Geri tusu |
| `screenshot` | Kanit al |
| `pageSource` | UI source al |

Ilk surum bu kadarla sinirli kalmali. Gesture, swipe, biometric, network shaping sonraki faz.

---

## 8. Cihaz Provisioning Standardi

### 8.1 Lokal 2 Cihaz Preset

Profil A:

- Android Pixel 8
- Appium: `http://127.0.0.1:4723`
- Driver: UiAutomator2

Profil B:

- Android Pixel 6 veya iPhone 15 Pro Simulator
- Appium: `http://127.0.0.1:4724`
- Driver: UiAutomator2 veya XCUITest

### 8.2 Komutlar

Hedef komutlar:

```bash
make mobile-doctor
make mobile-start-android-1
make mobile-start-android-2
make mobile-start-appium
make mobile-smoke
```

`mobile-doctor` sunlari kontrol eder:

- Node/npm
- Appium 2
- UiAutomator2 driver
- XCUITest driver, macOS ise
- adb
- emulator
- xcrun, macOS ise
- Appium `/status`
- cihaz UDID listesi

---

## 9. UI Deneyimi

UI'nin ilk ekrani pazarlama degil, kumanda paneli olmali.

### 9.1 Ekran Bilesenleri

- Cihaz tablosu:
  - status
  - platform
  - UDID
  - Appium health
  - current run
  - last error
- Run launcher:
  - cihaz secimi
  - app/web hedefi
  - senaryo secimi
  - timeout
- Live run panel:
  - cihaz bazli kolon
  - step listesi
  - log stream
  - screenshot preview
- History:
  - run group
  - cihaz bazli sonuc
  - duration
  - artifacts

### 9.2 UI'da Yasaklar

- Gercek olmayan "ready" etiketi yok.
- Endpoint calismadan "Hazir" yazisi yok.
- Simulasyon sonucu ile gercek run ayni gosterilmez.
- Appium kapaliysa kullanici bunu net gorur.

---

## 10. Faz Plani

## Faz 0 — Mimari Sabitleme

Sure: 0.5 gun

Teslimatlar:

- `/api/v1/mobile` canonical kararinin dokumante edilmesi.
- UI'daki engine direkt cagri listesinin cikarilmasi.
- Simulasyon modunun sadece dev/demo flag arkasina alinmasi.

Kabul:

- Yeni kodun hangi API'ye yazilacagi tartismasizdir.

---

## Faz 1 — DB-backed Device Registry

Sure: 1-2 gun

Teslimatlar:

- `mobile_devices` migration.
- `DeviceRegistryService`.
- ADB probe.
- simctl probe.
- Appium status probe.
- `GET /api/v1/mobile/devices`.
- `POST /api/v1/mobile/devices/probe`.

Kabul:

- Backend restart sonrasi cihazlar kaybolmaz.
- Appium kapali cihaz `idle` degil `offline/error` gorunur.
- UI iki cihazi gercek health ile listeler.

---

## Faz 2 — Tek Cihaz Gercek Runner

Sure: 2 gun

Teslimatlar:

- `AppiumRunner`.
- `POST /api/v1/mobile/sessions`.
- Deterministik steps support.
- Screenshot ve page source artifact kaydi.
- Tek session SSE stream.

Kabul:

- Tek Android cihazda gercek Appium session acilir.
- 3-5 adimli smoke run calisir.
- Failed step screenshot birakir.
- Simule pass yoktur.

---

## Faz 3 — Iki Cihaz Paralel Run

Sure: 1-2 gun

Teslimatlar:

- `mobile_run_groups`.
- `LeaseManager`.
- Grup stream endpoint'i.
- Cihaz bazli izolasyon.
- Partial failure modeli.

Kabul:

- Iki cihaz ayni anda kosar.
- Biri fail olursa digeri etkilenmez.
- Ayni cihaza ikinci run baslatilamaz.
- Lease timeout/crash sonrasi temizlenir.

---

## Faz 4 — UI Gercek Baglanti

Sure: 2 gun

Teslimatlar:

- `/p/[projectId]/mobile` canonical API'ye tasinir.
- Run launcher gercek payload uretir.
- Live stream cihaz bazli akar.
- History sayfasi DB'den beslenir.
- Artifact preview eklenir.

Kabul:

- Kullanici UI'dan iki cihaz secip run baslatir.
- Run sirasinda log ve screenshot gorur.
- Run bittikten sonra history'den sonucu acar.

---

## Faz 5 — Operasyonel Sertlestirme

Sure: 2-3 gun

Teslimatlar:

- `make mobile-doctor`.
- `make mobile-smoke`.
- Timeouts.
- Graceful cancellation.
- Reboot/boot aksiyonlari.
- Structured logs.
- Prometheus metrikleri.

Kabul:

- Yeni makinede doktor komutu eksikleri soyler.
- Smoke komutu tek komutla farm'i kanitlar.
- Timeout lease leak birakmaz.

---

## Faz 6 — AI Katmani

Sure: 2-4 gun

Teslimatlar:

- `POST /api/v1/mobile/steps/generate`.
- NL -> deterministic step JSON.
- Page source grounding.
- Self-healing v1:
  - retry
  - locator rewrite
  - quarantine
- Vision verifier opsiyonel assertion.

Kabul:

- AI kapali modda runner calismaya devam eder.
- AI yanlis step uretirse sistem kontrollu fail olur.
- Healing event UI'da gorunur.

---

## 11. Test Stratejisi

### 11.1 Unit Test

- Step parser.
- Capability builder.
- Lease manager.
- Artifact path builder.
- Failure categorizer.

### 11.2 Contract Test

- `/api/v1/mobile/devices`.
- `/api/v1/mobile/sessions`.
- SSE event schema.
- Artifact endpoint.

### 11.3 Integration Test

Env flag ile calisir:

```bash
APPIUM_URL=http://127.0.0.1:4723 pytest backend/tests/mobile -m appium
```

### 11.4 Smoke Test

`make mobile-smoke` zorunlu olarak:

1. Appium status kontrol eder.
2. Cihaz ready kontrol eder.
3. Session baslatir.
4. Screenshot bekler.
5. Final status bekler.
6. Artifact path'i dogrular.

### 11.5 UI E2E

Playwright:

- Cihaz listesi gorunur.
- Run baslatilir.
- SSE event UI'ya duser.
- History satiri olusur.
- Artifact modal acilir.

---

## 12. Observability

Metrikler:

- `mobile_devices_total{platform,status}`
- `mobile_sessions_total{status,platform}`
- `mobile_session_duration_seconds`
- `mobile_step_duration_seconds`
- `mobile_step_failures_total{category}`
- `mobile_lease_active_total`
- `mobile_artifacts_total{kind}`
- `mobile_appium_health{device_id}`

Log alanlari:

- `run_group_id`
- `session_id`
- `device_id`
- `project_id`
- `step_seq`
- `event_type`
- `failure_category`

Dashboard:

- Device heatmap.
- Last 20 runs.
- Failure category breakdown.
- Appium health panel.
- Artifact volume.

---

## 13. Guvenlik ve Izolasyon

Ilk iki cihazlik farm icin bile kurallar:

- Uploaded APK/IPA path traversal'a kapali olacak.
- Artifact path sadece session scope icinde okunacak.
- Project authorization her mobile endpoint'te kontrol edilecek.
- Appium server halka acik olmayacak.
- Device reboot/run aksiyonlari RBAC gerektirecek.
- Appium capabilities payload'i allowlist ile sinirlanacak.
- Loglarda secret mask uygulanacak.

---

## 14. Demo Senaryosu

10/10 demo akisi:

1. `make mobile-doctor` calisir, iki cihaz hazir gorunur.
2. UI'da Neurex Farm acilir.
3. Android A ve Android B/iOS B `ready` gorunur.
4. Smoke Login senaryosu secilir.
5. Run baslatilir.
6. Iki cihaz kolonunda step'ler akar.
7. Screenshot preview gelir.
8. Bir cihazda bilerek locator fail varyanti calistirilir.
9. UI bir cihazi failed, digerini passed gosterir.
10. History'de run acilir, artifact'lar gorulur.

Bu demo, urunun guvenilir oldugunu gosterir. Her sey yesil olmak zorunda degil; hatayi dogru gostermek de 10/10'dur.

---

## 15. "Done" Tanimi

Bu plan su kosullarda tamamlanmis sayilir:

- Iki cihaz UI'da gercek health ile gorunuyor.
- UI'dan paralel run baslatiliyor.
- Appium gercek komut calistiriyor.
- Simulasyon prod akista yok.
- SSE live stream calisiyor.
- Screenshot/log/page source artifact olarak kaliyor.
- Backend restart sonrasi history korunuyor.
- Lease leak yok.
- `make mobile-smoke` yesil.
- En az bir failure senaryosu dogru kategorize ediliyor.

---

## 16. Uygulama Sirasi

En dogru sira:

1. Endpoint kararini sabitle.
2. UI'daki kirik/legacy endpoint izlerini kaldir.
3. DB-backed device registry kur.
4. Appium health probe ekle.
5. Tek cihaz gercek runner yaz.
6. Artifact kaydini ekle.
7. Iki cihaz lease + paralel run ekle.
8. UI live stream'i bagla.
9. History ve artifact viewer'i bitir.
10. `make mobile-smoke` ve CI smoke ekle.
11. LLM step generation ekle.
12. Self-healing ve vision verifier ekle.

Bu siradan sapilmamali. Ozellikle LLM, runner gercekten calismadan one alinmamali.

---

## 17. Kalite Puani

Bu plan uygulaninca Neurex Farm'in ilk surum kalite hedefi:

| Alan | Hedef |
|---|---|
| Cihaz sayisi | 2 |
| Gercek kosum | 10/10 |
| UI canli izleme | 9/10 |
| Artifact kaniti | 10/10 |
| Operasyon kolayligi | 8/10 |
| Olceklenebilir mimari | 8/10 |
| AI yetenekleri | 6/10 ilk faz, 9/10 sonraki faz |

Sonuc: Ilk surum "kucuk ama gercek" olacak. Bu dogru temel uzerine 10 cihaz, real-device lab, BrowserStack, Kubernetes ve AI self-healing eklemek dogal buyume haline gelir.

---

## 18. Tek Cumlelik Karar

**Neurex Farm 10/10, iki cihazla bile olsa gercek Appium kosumu yapan, hatayi saklamayan, kanit ureten ve tekrar acildiginda gecmisini koruyan mobil test laboratuvaridir.**

---

## 19. Gelismis Platform Vizyonu

Ilk hedef 2 cihazdir, fakat mimari bastan platform gibi kurulmalidir. Bu sayede 2 cihazdan 20 cihaza gecis yeniden yazim gerektirmez.

Platform katmanlari:

| Katman | Sorumluluk | Ilk Faz | Buyume Fazı |
|---|---|---|---|
| Control Plane | API, auth, orchestration, run state | FastAPI process | FastAPI + worker pool |
| Device Plane | Cihaz health, lease, Appium endpoint | 2 lokal cihaz | lab node agent'lari |
| Execution Plane | Step execution, retry, artifact | AppiumRunner | distributed workers |
| Evidence Plane | Screenshot, log, page source, video | local disk | MinIO/S3 |
| Intelligence Plane | LLM stepper, healing, visual verifier | opsiyonel | policy-driven AI |
| Observability Plane | metrics, logs, traces, dashboards | Prometheus logs | full Grafana/OTel |

Mimari karar: Control Plane ile Device Plane birbirine gevsek bagli olmalidir. Yani ileride cihazlar baska makinelerde olabilir; API sadece node agent ile konusur.

---

## 20. Session State Machine

Her session ayni durum makinesinden gecmelidir:

```text
created
  -> queued
  -> leasing
  -> leased
  -> appium_starting
  -> running
  -> collecting_artifacts
  -> passed

failed durumlari:

created/queued/leasing        -> failed_infrastructure
appium_starting               -> failed_appium
running                       -> failed_step | failed_assertion | failed_timeout
collecting_artifacts          -> passed_with_artifact_warning | failed_artifact
cancel requested              -> cancelling -> cancelled
lease expired/crash recovery  -> orphaned -> recovered | failed_infrastructure
```

Kurallar:

- `running` durumuna gecmeden lease alinmis olmalidir.
- `passed` veya `failed_*` durumuna gecmeden lease serbest birakilmalidir.
- `collecting_artifacts` basarisiz olursa run sonucu otomatik passed sayilmaz; `passed_with_artifact_warning` ayrimi yapilir.
- Her state transition audit event olarak kaydedilir.

---

## 21. Failure Taxonomy

Farm'in gelismis olmasi, sadece kosmasi degil, hatayi dogru adlandirmasi demektir.

| Kategori | Ornek | Kullaniciya Mesaj | Aksiyon |
|---|---|---|---|
| `device_offline` | ADB cihaz gormuyor | Cihaz offline | Probe/reboot oner |
| `appium_unreachable` | `/status` fail | Appium server kapali | Appium start komutu oner |
| `session_create_failed` | capability yanlis | Appium session acilamadi | capability diff goster |
| `app_install_failed` | APK imza/ABI sorunu | Uygulama yuklenemedi | install log artifact |
| `locator_not_found` | element yok | Element bulunamadi | screenshot + page source |
| `assertion_failed` | beklenen ekran yok | Dogrulama basarisiz | expected/actual goster |
| `step_timeout` | bekleme asildi | Adim timeout oldu | timeout ve step bilgisi |
| `device_busy` | lease var | Cihaz baska run'da | current session link |
| `artifact_failed` | screenshot alinamadi | Kanit eksik | run sonucunu warning yap |
| `cancelled_by_user` | kullanici durdurdu | Run iptal edildi | lease temizle |

Bu taxonomy raporlama, filtreleme, self-healing ve metrikler icin ortak dil olur.

---

## 22. Quality Gates

Her fazin sonunda sadece "kod yazildi" denmez; kalite kapisi gecilir.

### Gate A — Device Truth

- 2 cihaz dogru status ile listelenir.
- Appium kapaliysa cihaz ready gorunmez.
- Backend restart sonrasi cihaz kaydi korunur.

### Gate B — Single Device Reality

- Tek cihazda gercek Appium session acilir.
- Step event'leri canli akar.
- Failed step screenshot ve page source birakir.

### Gate C — Parallel Safety

- Iki cihaz ayni run group icinde paralel kosar.
- Ayni cihaza ikinci run baslatilamaz.
- Bir cihaz fail olunca digeri etkilenmez.

### Gate D — Evidence Integrity

- Artifact sha256 kaydedilir.
- Artifact dosyasi yoksa DB kaydi valid sayilmaz.
- History restart sonrasi acilir.

### Gate E — Demo Readiness

- `make mobile-doctor` yesil.
- `make mobile-smoke` yesil.
- UI'dan run baslatma ve history goruntuleme calisir.
- Bilerek fail edilen locator dogru failure category ile raporlanir.

---

## 23. SLO ve Error Budget

Ilk iki cihazlik farm icin hizmet hedefleri:

| SLO | Hedef |
|---|---|
| Device health refresh | p95 < 3 sn |
| Run start latency | p95 < 8 sn |
| Step event delivery | p95 < 750 ms |
| Screenshot capture | p95 < 2 sn |
| Session cleanup | %100 lease release |
| Artifact durability | %99.9 local dev, %99.99 S3/MinIO |
| Smoke reliability | son 20 kosuda en az 19 pass |

Error budget:

- Haftalik smoke failure toleransi: 1
- Lease leak toleransi: 0
- Fake pass toleransi: 0
- Artifact kaybi toleransi: 0 demo/release oncesi

---

## 24. Node Agent V2 Hazirligi

Ilk surum local calisir, ama ileri mimari icin node agent sozlesmesi simdiden tasarlanmalidir.

Node Agent sorumluluklari:

- local ADB/simctl probe
- Appium process lifecycle
- device boot/reboot
- screenshot/video helper
- secure artifact upload
- heartbeat

Control Plane ile Node Agent arasindaki ilerideki sozlesme:

```text
GET  /agent/health
GET  /agent/devices
POST /agent/appium/start
POST /agent/appium/stop
POST /agent/devices/{udid}/boot
POST /agent/devices/{udid}/reboot
POST /agent/sessions
GET  /agent/sessions/{id}/stream
```

Ilk fazda bu agent ayri process olmak zorunda degil. Ama servis siniflari bu ayrima hazir yazilmalidir.

---

## 25. Scheduling ve Queue Tasarimi

Iki cihazda bile siralama kurali net olmalidir.

Run priority:

1. manual interactive run
2. smoke run
3. scheduled regression
4. AI exploration

Queue kurallari:

- Cihaz seciliyse sadece o cihaza queue edilir.
- Platform seciliyse uygun idle cihaz secilir.
- Lease alinmadan run `running` olamaz.
- Queue timeout dolarsa run `failed_infrastructure` olur.
- Kullanici queue'daki run'i iptal edebilir.

Ileride Redis Streams:

```text
mobile:runs:queued
mobile:runs:events
mobile:device:{id}:lease
mobile:session:{id}:heartbeat
```

---

## 26. Release Plan

### Release 0.1 — Truthful Farm

Kapsam:

- DB-backed device registry
- Appium health probe
- tek cihaz real run
- artifact screenshot

Release notu:

> Bu surum cihazlari dogru gosterir ve tek cihazda gercek Appium smoke kosar. Paralel run henuz sinirli olabilir.

### Release 0.2 — Two Device Lab

Kapsam:

- lease manager
- iki cihaz paralel run
- group stream
- history

Release notu:

> Bu surum Neurex Farm'i iki cihazlik gercek mobil test laboratuvari yapar.

### Release 0.3 — Evidence Grade

Kapsam:

- page source
- stdout/appium log
- artifact integrity
- failure taxonomy
- UI artifact viewer

Release notu:

> Bu surum run sonucunu musteriye kanit olarak sunabilecek seviyeye getirir.

### Release 0.4 — Operable Farm

Kapsam:

- mobile-doctor
- mobile-smoke
- metrics
- reboot/boot actions
- timeout/cancel

Release notu:

> Bu surum gunluk kullanim ve demo oncesi operasyonu guvenilir hale getirir.

### Release 0.5 — Intelligent Farm

Kapsam:

- LLM step generation
- self-healing v1
- visual verifier
- quarantine

Release notu:

> Bu surum calisan farm uzerine AI destekli uretim ve onarim katmani ekler.

---

## 27. Uygulama Ticket'lari

### P0 Ticket'lar

1. `MOB-001 Canonical API Cleanup`
   - UI'daki legacy engine direkt cagri noktalarini listele.
   - Yeni run akisini `/api/v1/mobile` uzerinden tasarla.

2. `MOB-002 Mobile DB Schema`
   - `mobile_devices`, `mobile_sessions`, `mobile_steps`, `mobile_artifacts`, `mobile_device_leases`.

3. `MOB-003 Device Probe Service`
   - ADB, simctl, Appium `/status`.

4. `MOB-004 AppiumRunner Single Device`
   - Deterministik steps ile gercek run.

5. `MOB-005 Artifact Store Local`
   - Screenshot, page source, stdout.

6. `MOB-006 SSE Event Contract`
   - Event schema ve stream endpoint.

### P1 Ticket'lar

7. `MOB-007 Lease Manager`
8. `MOB-008 Parallel Run Group`
9. `MOB-009 UI Live Run Panel`
10. `MOB-010 Mobile History + Artifact Viewer`
11. `MOB-011 make mobile-doctor`
12. `MOB-012 make mobile-smoke`

### P2 Ticket'lar

13. `MOB-013 Metrics + Dashboard`
14. `MOB-014 Cancellation + Timeout Hardening`
15. `MOB-015 LLM Step Generation`
16. `MOB-016 Self-Healing V1`
17. `MOB-017 Visual Verify`

---

## 28. Implementation Guardrails

Kod yazarken korunacak sinirlar:

- Simulasyon sadece `MOBILE_SIMULATION_MODE=1` ile calisir.
- Prod/default akista `pass_rate` veya random sonuc yoktur.
- Appium capability alanlari allowlist disina cikamaz.
- Artifact path session klasoru disina cikamaz.
- UI status backend health'ten gelir; lokal tahminle ready yazilmaz.
- Her external command timeout ile calisir.
- Her background task cancellation path'ine sahiptir.
- Her session sonunda cleanup calisir.

---

## 29. Advanced Demo Mode

Gelismis demo iki akistan olusur:

### Akis A — Happy Path

- Iki cihaz ready.
- Smoke run baslar.
- Iki cihaz passed.
- Artifact viewer acilir.
- Metrics panelde run sayisi artar.

### Akis B — Honest Failure

- Bir cihazda yanlis locator kullanilir.
- O cihaz `locator_not_found` olur.
- Screenshot ve page source gorulur.
- Diger cihaz passed olur.
- Run group sonucu `partial_failed` olur.

Bu ikinci akis cok degerlidir; sistemin hatayi saklamadigini gosterir.

---

## 30. Nihai Gelismis Hedef

Bu planin gelismis hali su noktaya varir:

> Neurex Farm, iki cihazla baslayan; device truth, lease safety, real Appium execution, evidence-grade artifacts, live observability, failure taxonomy ve AI-ready extension noktalarina sahip bir mobil test platformudur.

Bu seviyeden sonra cihaz sayisi sadece kapasite meselesidir. Temel urun dogru oldugu icin 2'den 10'a, 10'dan 100'e gecis mimari borc degil, altyapi yatirimi olur.

---

## 31. Enterprise Architecture Blueprint

Neurex Farm uzun vadede uc farkli deployment modelini desteklemelidir:

| Model | Kullanici | Ozellik | Ilk Gereksinim |
|---|---|---|---|
| Local Lab | Gelistirici/QA lead | 2 cihaz, laptop/lokal Mac | hizli kurulum |
| Team Lab | QA ekibi | 5-20 cihaz, paylasimli node | lease, auth, artifact |
| Enterprise Lab | banka/kamu | on-prem, audit, network isolation | RBAC, audit, secret mgmt |

Ilk surum Local Lab'dir. Fakat kod, Team Lab ve Enterprise Lab'e gecisi bozmayacak sekilde yazilmalidir.

### 31.1 Deployment Topolojileri

Local:

```text
MacBook/Mac Mini
  - Web
  - Backend
  - Postgres
  - Appium 4723
  - Appium 4724
  - 2 devices
```

Team:

```text
Control Node
  - Web
  - Backend
  - Postgres
  - Redis
  - MinIO

Device Node A
  - Node Agent
  - Appium pool
  - Android/iOS devices

Device Node B
  - Node Agent
  - Appium pool
  - Android devices
```

Enterprise:

```text
Private Network
  - Control plane isolated
  - Device VLAN
  - outbound proxy
  - audit log sink
  - artifact retention policy
  - secrets manager
```

---

## 32. Architecture Decision Records

### ADR-FARM-001: Canonical API FastAPI olacak

Karar:

- Canonical API `/api/v1/mobile/*`.

Gerekce:

- Ana backend zaten FastAPI.
- Auth, project access, DB ve audit burada.
- UI'nin engine'e direkt baglanmasi urun sozlesmesini zayiflatiyor.

Sonuc:

- Engine sadece legacy runner veya adapter olabilir.
- Yeni endpoint FastAPI mobile domain'e yazilir.

### ADR-FARM-002: Ilk hedef iki cihazdir

Karar:

- 2 cihaz release hedefi.

Gerekce:

- Farm kalitesi cihaz sayisindan once gelir.
- Lease, artifact, run history ve Appium truth iki cihazda cozulemezse on cihazda daha kotu olur.

Sonuc:

- UI 10 cihazlik izlenim vermemeli.
- Kapasite buyumesi sonraki release'tir.

### ADR-FARM-003: Simulasyon prod akista yasak

Karar:

- Default/prod akista random pass/fail yok.

Gerekce:

- Test platformunda guven en kritik degerdir.

Sonuc:

- Simulasyon sadece explicit flag ile calisir.
- UI simule run'i gercek run gibi gostermez.

### ADR-FARM-004: Artifact evidence birinci sinif vatandas

Karar:

- Screenshot, page source ve log olmadan failed run eksik sayilir.

Gerekce:

- Mobil testte hata analizi kanitsiz yapilamaz.

Sonuc:

- Artifact pipeline MVP kapsamindadir.

---

## 33. Domain Model

Ana kavramlar:

| Kavram | Anlam |
|---|---|
| Device | Farm tarafindan bilinen test hedefi |
| Node | Cihazin bagli oldugu makine/agent |
| Lease | Cihazin belirli session icin ayrilmasi |
| RunGroup | Paralel kosunun ust kimligi |
| Session | Tek cihazdaki kosu |
| Step | Session icindeki atomik aksiyon |
| Artifact | Kosudan kalan kanit |
| Probe | Cihaz/Appium health olcumu |
| CapabilityProfile | Appium session icin onayli capability seti |

Kurallar:

- RunGroup bir veya daha fazla Session icerir.
- Session tek Device'a baglidir.
- Device ayni anda en fazla bir aktif Lease'e sahip olabilir.
- Step sirali calisir; parallelism session seviyesindedir.
- Artifact her zaman Session'a baglidir, opsiyonel olarak Step'e de baglanir.

---

## 34. API Idempotency ve Concurrency

Mobil farm'da tekrar eden istekler normaldir. Browser refresh, network retry veya UI double-click ayni run'i iki kez baslatmamalidir.

### 34.1 Idempotency Key

`POST /api/v1/mobile/sessions` su header'i desteklemelidir:

```text
Idempotency-Key: projectId:userId:clientGeneratedRunId
```

Kurallar:

- Ayni key ile ayni payload gelirse eski cevap doner.
- Ayni key ile farkli payload gelirse 409 doner.
- Key TTL: 24 saat.

### 34.2 Concurrency Control

- Lease alma DB transaction icinde yapilir.
- Unique constraint: aktif lease icin `device_id`.
- Expired lease cleanup background job ile yapilir.
- Run cancellation lease release'i transaction icinde yapar.

---

## 35. Security Threat Model

| Tehdit | Risk | Onlem |
|---|---|---|
| APK path traversal | Sunucuda dosya okuma/yazma | upload path normalize + allow directory |
| Appium public exposure | Yetkisiz cihaz kontrolu | localhost/private network, auth proxy |
| Capability injection | Appium host dosya/komut kotuye kullanim | capability allowlist |
| Artifact leakage | Proje disi screenshot erisimi | project scoped auth |
| Secret in logs | Token/sifre ifsasi | masking filter |
| Malicious app | Device/network risk | isolated lab VLAN |
| Run hijacking | Baska kullanicinin stream'ini izleme | stream token + project auth |
| Unbounded subprocess | Host kaynak tuketimi | timeout + process group cleanup |

Minimum guvenlik kapisi:

- Tum mobile endpoint'ler project auth kontrol eder.
- Artifact endpoint path yerine artifact id alir.
- Appium URL kullanici payload'indan serbest alinmaz; registry'den gelir.
- Uploaded app dosya uzantisi ve MIME kontrol edilir.

---

## 36. Compliance ve Audit

Bankacilik/kamu hedefi icin audit ilk gunden dusunulmelidir.

Audit event'leri:

- device enrolled
- device status changed
- session requested
- lease acquired/released
- app uploaded
- artifact created/read
- run cancelled
- device reboot requested
- AI healing applied

Her audit event su alanlari tasir:

- `actor_user_id`
- `project_id`
- `device_id`
- `session_id`
- `action`
- `timestamp`
- `ip`
- `user_agent`
- `result`

Retention:

- Local/dev: 7 gun
- Team: 30-90 gun
- Enterprise: policy based, genelde 1 yil+

---

## 37. Capacity Model

Iki cihaz icin bile kapasite hesabini kurmak gerekir.

Varsayimlar:

- Ortalama session: 90 sn
- Ortalama screenshot: 300 KB
- Failed step page source: 200 KB
- Ortalama run artifact: 2-5 MB
- Gunde 100 run: 200-500 MB artifact

Ilk kapasite:

| Kaynak | 2 Cihaz | 10 Cihaz |
---|---:|---:|
| CPU | 4-8 core | 12-24 core |
| RAM | 16-32 GB | 64 GB+ |
| Disk artifact/gun | 0.5 GB | 3-8 GB |
| Appium process | 2 | 10 |
| Concurrent sessions | 2 | 10 |

Kural:

- Cihaz sayisi artmadan once artifact retention ve cleanup policy gelmelidir.

---

## 38. Artifact Retention Policy

Ilk policy:

| Artifact | Passed Run | Failed Run |
|---|---:|---:|
| Screenshot | 7 gun | 30 gun |
| Page source | 3 gun | 30 gun |
| Appium log | 7 gun | 30 gun |
| Video | opsiyonel 3 gun | 14 gun |
| Summary JSON | 90 gun | 90 gun |

Enterprise policy:

- Project bazli override.
- Legal hold.
- Manual purge audit event'i.
- S3 lifecycle rules.

---

## 39. Chaos ve Resilience Testleri

10/10 farm kontrollu kaosta ayakta kalmalidir.

Chaos testleri:

1. Run sirasinda Appium server kapatilir.
   - Beklenen: session `failed_appium`, lease released.

2. Cihaz offline edilir.
   - Beklenen: `device_offline`, artifact best-effort.

3. Backend restart edilir.
   - Beklenen: running session recovered veya failed_infrastructure; stale lease temizlenir.

4. Artifact dizini readonly yapilir.
   - Beklenen: `passed_with_artifact_warning` veya `failed_artifact`.

5. UI stream kopar.
   - Beklenen: reconnect history event'leri ile devam eder.

6. Ayni cihaza iki run baslatilir.
   - Beklenen: ikinci istek 409 veya queued.

Bu testler otomatiklestikce farm kalitesi gercekten yukselir.

---

## 40. Event Replay ve Stream Reconnect

SSE sadece live pipe olmamali; event'ler DB/Redis'e yazilmalidir.

Kurallar:

- Her event incrementing `event_id` alir.
- UI reconnect ederken `Last-Event-ID` gonderebilir.
- Backend eksik event'leri replay eder.
- Event retention en az session retention kadar olmalidir.

Bu sayede tarayici yenilense bile kullanici run'i kaybetmez.

---

## 41. Advanced UI Information Architecture

Farm UI uc seviyeye bolunmelidir:

### 41.1 Command Center

Gunluk kullanim:

- cihazlar
- run baslat
- live status
- son hatalar

### 41.2 Evidence Viewer

Debug ve rapor:

- timeline
- screenshot diff
- page source
- logs
- failure category

### 41.3 Lab Operations

Operasyon:

- Appium health
- driver version
- device boot/reboot
- node health
- artifact storage
- doctor output

Bu ayrim UI'yi karmasiklastirmadan derinlestirir.

---

## 42. AI Governance

AI katmani eklenince kurallar net olmalidir.

AI modlari:

| Mod | Davranis |
|---|---|
| Off | Sadece deterministic steps |
| Assist | Step onerir, kullanici onaylar |
| Auto | Step uretir ve run baslatir |
| Heal | Fail durumunda locator onerir |
| Explore | Yeni akis kesfeder |

Ilk desteklenecek mod: `Assist`.

Kurallar:

- AI tarafindan uretilen step'ler versionlanir.
- AI healing uygulandiysa raporda belirtilir.
- AI generated locator ile human-authored locator ayrilir.
- Kritik projelerde AI auto mode default kapali olur.

---

## 43. Data Contracts

Step JSON versionlanmalidir.

```json
{
  "schema_version": "mobile-step/v1",
  "steps": [
    {
      "seq": 0,
      "action": "find",
      "target": {
        "by": "accessibilityId",
        "value": "login_button"
      },
      "timeout_ms": 10000,
      "description": "Login butonunu bul"
    }
  ]
}
```

Version kurallari:

- Breaking change yeni schema version ister.
- Runner eski schema'lari migration layer ile calistirir.
- UI kaydedilen run'i o gunun schema'siyla gosterebilir.

---

## 44. Definition of 10/10 v1

10/10 v1 icin nihai checklist:

- [ ] Canonical `/api/v1/mobile` disinda UI run akisi yok.
- [ ] 2 cihaz gercek health ile listeleniyor.
- [ ] Appium session gercek aciliyor.
- [ ] Random/simule result default kapali.
- [ ] Lease atomic ve TTL'li.
- [ ] Parallel run group calisiyor.
- [ ] SSE event replay destekli.
- [ ] Screenshot + page source + log artifact kalici.
- [ ] Failure taxonomy uygulanmis.
- [ ] `make mobile-doctor` var.
- [ ] `make mobile-smoke` var.
- [ ] Honest failure demo calisiyor.
- [ ] Auth/RBAC/artifact scope korunuyor.
- [ ] En az 1 chaos testi otomatik.

Bu liste yesil olmadan "farm bitti" denmemelidir.

---

## 45. Uygulama Durumu

### Baslanan Dikey Dilim — 2026-05-14

Tamamlanan ilk kod dilimi:

- `SessionCreate.mode` eklendi: `simulation | appium`.
- Deterministik `steps` payload'i eklendi; verilirse prompt generation bypass edilir.
- `AppiumRunner` eklendi:
  - gercek Appium session acma
  - deterministic step execution
  - `openUrl`, `find`, `tap`, `sendKeys`, `clear`, `verifyVisible`, `wait`, `back`, `screenshot`, `pageSource`
  - failure categorization
  - best-effort failure artifact toplama
- `MobileArtifactStore` eklendi:
  - local filesystem artifact
  - sha256
  - screenshot/page source kaydi
- `/api/v1/mobile/sessions/{id}/artifacts` eklendi.
- `/api/v1/mobile/artifacts/{id}` eklendi.
- `/api/v1/mobile/devices/probe` eklendi:
  - Appium `/status` ile ready/error guncellemesi
- `AppiumCapabilities` web smoke icin `browserName`, fiziksel cihaz icin `udid` tasiyabilir hale geldi.
- Mobil test paketi guncellendi:
  - Appium runner unit tests
  - artifact API tests
  - device probe tests
  - explicit steps orchestrator test

Dogrumala:

```bash
pytest backend/tests/mobile -q
# 112 passed, 2 skipped
```

Henuz tamamlanmayan kritik alanlar:

- DB-backed device/session/artifact persistence.
- Atomic lease manager.
- UI'nin `/api/v1/mobile` canonical akisa tasinmasi.
- Gercek cihazla `make mobile-smoke`.
- Event replay icin kalici event store.
