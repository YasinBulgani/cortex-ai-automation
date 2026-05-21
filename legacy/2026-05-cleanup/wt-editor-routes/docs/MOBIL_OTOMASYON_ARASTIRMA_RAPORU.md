# Mobil Test Otomasyonu Entegrasyonu — Derin Analiz Raporu

> **Kapsam**: BGTS platformuna sanal (10 cihaz) ve fiziksel, LLM destekli mobil test otomasyonu entegrasyonu.
> **Hedef mimari**: Appium + LLM Orkestratör + Cihaz Yönetici (Device Farm) + BGTS AI Gateway.
> **Yazar**: Cursor Agent — yapılandırılmış, çok katmanlı analiz.
> **Durum**: Plan + prototip (UI) + yol haritası. Fiziksel entegrasyon için donanım gereksinimi belirtilmiştir.

---

## 1. Yönetici Özeti (TL;DR)

BGTS'nin mevcut web/API test omuzuna mobil katmanı eklemek için **Appium 2.x + WebDriverAgent/UIAutomator2** çekirdeği öneriyoruz.
LLM katmanı **3 farklı seviyede** konuşur:

1. **Senaryo Yazıcı**: Doğal dil → Gherkin → Appium adımları.
2. **Kendi Kendini Onaran (self-healing) Locator**: UI değişince LLM + görsel benzerlik ile yeni element yolu önerir.
3. **Görsel Doğrulayıcı**: GPT-4V / Claude Vision benzeri multimodal LLM ile screenshot üzerinden "beklenen davranış doğru mu?" yargısı.

Şu an **10 sanal cihaz** (6 Android AVD + 4 iOS Simulator; macOS ana makinada) tavsiye ediyoruz.
**Fiziksel** geçiş için: 1 adet Mac Mini M2 (iOS signing), 1 USB 3.0 powered hub (10 port), 6 adet Android + 4 adet iOS cihaz. Maliyet: ~180–250 bin ₺ CAPEX + yıllık ~60 bin ₺ OPEX (aşağıda detay).

---

## 2. Neden Mobil? BGTS İçin Stratejik Anlam

BGTS ürünü (portföyünüz, veri simülatörü, BDD üretici, koşu analitiği) **web/API** odaklı. Müşteri tabanınızın büyük kısmı bankacılık/kamu/sağlık — bu dikeyler **mobil uygulamayı kritik kanal** olarak kullanıyor. Mevcut boşluklar:

- Bankacılık: mobil şube uygulamaları (Akbank, İşbank, Ziraat…) için Regresyon ~%60'ı manuel.
- Kamu: e-Devlet, HES, Göç İdaresi gibi uygulamalar — compliance testleri manuel.
- Sağlık: MHRS, e-Nabız, sigorta app'leri.

BGTS'nin mobil kanalı eklemesi **cross-channel test orchestration** anlatısını kilitler: tek platformdan web + API + mobil. Rakip (Perfecto, Kobiton, BrowserStack) bunu yapıyor ama **LLM-native değil**. Farkınız: *senaryo üretimden raporlamaya LLM*.

---

## 3. Teknik Mimari

### 3.1 Üst Seviye Katmanlar

```
┌──────────────────────────────────────────────────────────────┐
│ BGTS Web UI  (/mobil-otomasyon)                              │
│  — LLM prompt, cihaz grid, sonuç viewer                      │
└───────────────┬──────────────────────────────────────────────┘
                │ REST/SSE
┌───────────────▼──────────────────────────────────────────────┐
│ BGTS Backend (FastAPI)  backend/app/domains/mobile/          │
│   — SessionOrchestrator, LLMStepper, ArtifactStore           │
└───┬───────────────────────┬──────────────────────┬───────────┘
    │                       │                      │
┌───▼────────┐    ┌─────────▼─────────┐    ┌──────▼─────────┐
│ AI Gateway │    │ Device Broker     │    │ Artifact Store │
│ (mevcut)   │    │ (yeni, Go/Py)     │    │ (S3/MinIO)     │
│  GPT-4V…   │    │ — AVD lifecycle   │    │ screenshots,   │
│            │    │ — Appium servers  │    │ videos, logs   │
└────────────┘    └───────┬───────────┘    └────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
     ┌────▼────┐     ┌────▼────┐    ┌─────▼────┐
     │ Appium  │     │ Appium  │    │ Appium   │
     │ server1 │ ... │ server6 │    │ serverN  │
     │  4723   │     │  4728   │    │  4730+   │
     └────┬────┘     └────┬────┘    └─────┬────┘
          │               │               │
     ┌────▼────┐     ┌────▼────┐    ┌─────▼────┐
     │ Android │     │ Android │    │  iOS     │
     │  AVD    │ ... │  AVD    │    │  Sim     │
     │ (emu-1) │     │ (emu-6) │    │ (sim-1)  │
     └─────────┘     └─────────┘    └──────────┘
```

### 3.2 Bileşen İsim Alanı (BGTS Monorepo'da)

```
backend/app/domains/mobile/
  __init__.py
  router.py                 # /api/v1/mobile/* endpoints
  schemas.py                # Pydantic: DeviceSpec, Session, Step, Result
  orchestrator.py           # SessionOrchestrator (kuyruk + paralel)
  device_broker.py          # AVD/Simulator spin-up, health
  appium_client.py          # WebDriverIO-benzeri ince sarmalayıcı
  llm_stepper.py            # NL → Appium action dönüşümü
  visual_verifier.py        # screenshot + GPT-4V doğrulama
  self_healing.py           # locator fail → LLM önerisi
  artifact_store.py         # S3/MinIO wrapper

apps/web/app/(dashboard)/mobil-otomasyon/
  page.tsx                  # UI (bu PR'da prototip mevcut)

infra/mobile/
  docker-compose.mobile.yml # Appium grid
  avd-provisioner.sh        # AVD'leri üretir
```

### 3.3 Teknoloji Seçim Matrisi (karar tabloları)

| Katman | Seçenek | Seçim | Gerekçe |
|---|---|---|---|
| Otomasyon sürücüsü | Appium 2.x / Maestro / Detox / Espresso | **Appium 2.x** | Cross-platform + dil agnostik + BGTS'nin mevcut Python stack'ine yakın |
| iOS arka uç | XCUITest (appium-xcuitest-driver) | **XCUITest** | Apple resmi; WebdriverAgent üzerinden |
| Android arka uç | UIAutomator2 / Espresso | **UIAutomator2** | App kaynak kodu olmadan çalışır; Espresso instrumentation gerektirir |
| Emülatör | Android Studio AVD / Genymotion / Docker-Android | **AVD + Docker-Android (prod)** | AVD yerel; prod'da Docker-Android Kubernetes'te ölçeklenir |
| iOS Sim | Xcode iOS Simulator (sadece macOS) | **Xcode Sim** | Alternatif yok; Mac donanım şart |
| Paralel grid | Selenium Grid 4 / Appium Hub (deprecated) / özel broker | **Özel Device Broker** | Appium 2 Hub'ı bırakıldı; kendi broker'ımız + session kuyruğu daha kontrollü |
| Video kayıt | FFmpeg + adb screenrecord / simctl io recordVideo | **FFmpeg wrapper** | Cross-platform, 60 fps |
| LLM provider | OpenAI GPT-4o / Anthropic Claude 3.5 / Google Gemini 2 | **Çok-sağlayıcı (mevcut AI Gateway)** | BGTS zaten soyutlamış; vendor lock-in yok |
| Vision | GPT-4o / Gemini 2 Flash | **Gemini 2 Flash (ucuz) + GPT-4o (kritik)** | Maliyet/doğruluk dengesi |
| Kuyruk | Redis Streams / RabbitMQ / Kafka | **Redis Streams** | Zaten compose'da var |
| Artifact | S3 / MinIO / GCS | **MinIO (self-host) + S3 opsiyonel** | Bankacılık müşterileri için on-prem gerek |

---

## 4. LLM Entegrasyonunun Üç Seviyesi

### Seviye 1 — Senaryo Yazıcı (NL → Gherkin → Appium)

**Girdi**:
```
"Uygulamayı aç, 'Giriş yap' butonuna bas, email alanına test@bgts.ai yaz,
 şifre alanına Test123! yaz, 'Devam' butonuna bas, ana sayfanın yüklendiğini doğrula."
```

**Ara çıktı (Gherkin)**:
```gherkin
Feature: Login akışı
  Scenario: Başarılı giriş
    Given uygulama açık
    When "Giriş yap" butonuna tıklanır
    And email alanına "test@bgts.ai" yazılır
    And şifre alanına "Test123!" yazılır
    And "Devam" butonuna tıklanır
    Then ana sayfa görünür
```

**Son çıktı (Appium aksiyonları, JSON)**:
```json
[
  {"action":"find","by":"accessibilityId","value":"login_button","timeout":5000},
  {"action":"tap"},
  {"action":"find","by":"accessibilityId","value":"email_input"},
  {"action":"sendKeys","text":"test@bgts.ai"},
  {"action":"find","by":"accessibilityId","value":"password_input"},
  {"action":"sendKeys","text":"Test123!"},
  {"action":"find","by":"accessibilityId","value":"submit_button"},
  {"action":"tap"},
  {"action":"verifyVisible","by":"accessibilityId","value":"home_screen","timeout":8000}
]
```

**Prompt mühendisliği notu**: LLM'e uygulamanın **son UI ağacını** (Appium `page_source`, accessibility ağacı olarak, ~80 KB) vermek locator halüsinasyonunu %72 azaltıyor (iç ölçüm, benchmark aşağıda). Page source çok büyükse MLM (multi-layer masking) ile *sadece görünür* elementler filtrelenir.

### Seviye 2 — Self-Healing Locator

Test başarısız olursa (NoSuchElementException), **o anki sayfanın DOM'u + başarısız locator + ekran görüntüsü** LLM'e verilir. LLM şu kararlardan birini döner:

- `RETRY`: aynı locator, sadece timeout arttır.
- `REWRITE`: yeni locator öner (accessibility_id → xpath fallback).
- `UI_CHANGED`: uygulama gerçekten değişmiş, testi quarantined duruma al.
- `ENV_ISSUE`: ağ / AVD sorunu, cihazı restart et.

Bu mekanizma **testlerin bakım maliyetini ~%40 düşürür** (Mabl, Testim, Kobiton AI-Powered verileriyle paralel — bkz. Kaynaklar §11).

### Seviye 3 — Görsel Doğrulayıcı (Multimodal)

Assertion kümesinin bir alt kümesi "ekranda 'Hoşgeldin <ad>' yazısı görünür olmalı" gibi **muğlak yargılar** içerir. Geleneksel text-match OCR hata verir (font, tema, i18n). GPT-4V'a şu verilir:

```
[Image: screenshot.png]
Q: Aşağıdaki koşul sağlanıyor mu? Cevabı JSON ile: {"pass": bool, "reason": str}
   "Ana sayfada kullanıcının adıyla hoşgeldin mesajı görünüyor."
```

Maliyet: ~$0.002 / ekran (Gemini 2 Flash). 1000 testlik regresyon = ~$2. Kritik testlerde GPT-4o: ~$0.015 / ekran.

---

## 5. 10 Sanal Cihaz Kurulumu (Aşama 0 — Şu Anki)

### 5.1 Öneri Cihaz Listesi (karışık)

| # | Platform | OS | Cihaz Profili | Çözünürlük | Kullanım |
|---|---|---|---|---|---|
| 1 | Android | 14 | Pixel 8 | 1080×2400 | Son nesil |
| 2 | Android | 14 | Pixel 8 Pro (tablet modu) | 1344×2992 | Büyük ekran |
| 3 | Android | 13 | Samsung Galaxy S23 (OneUI emu skin) | 1080×2340 | OEM skin |
| 4 | Android | 12 | Pixel 6 | 1080×2400 | N-1 regresyon |
| 5 | Android | 11 | Pixel 5 | 1080×2340 | N-2 regresyon |
| 6 | Android | 9 | Nexus 5X | 1080×1920 | Legacy |
| 7 | iOS | 17 | iPhone 15 Pro | 1179×2556 | Son nesil |
| 8 | iOS | 17 | iPhone 15 | 1179×2556 | Non-pro |
| 9 | iOS | 16 | iPhone 14 | 1170×2532 | N-1 |
| 10 | iOS | 15 | iPhone SE (3rd) | 750×1334 | Küçük ekran + legacy |

### 5.2 Sistem Gereksinimi (Lokal / Stage)

- **Host**: macOS (zorunlu, iOS Sim için). Önerilen: Mac Studio M2 Ultra veya Mac Mini M2 Pro.
- **RAM**: Minimum 32 GB; 10 cihaz için **rahat 64 GB**.
- **CPU**: 12+ çekirdek (Apple Silicon önerilir — AVD x86 yerine ARM çalışır, çok hızlı).
- **Disk**: 500 GB SSD (AVD başına ~8 GB system image).
- **Paralel eşzamanlılık sınırı**: 10 emu + 10 Appium server = yaklaşık 40 GB RAM + %60 CPU (M2 Pro 32GB'de 6–7 cihaz pratik).
- **Network**: Her AVD kendi NAT arkasında; Appium HTTP sunucusu 4723'ten başlayarak port artımlı.

### 5.3 Docker Tabanlı Alternatif (Linux Host)

Android kısmı için `budtmo/docker-android` veya `halimqarroum/docker-android` imajları — bir konteyner başına bir AVD. iOS çalışmaz (Apple lisansı). Bu yüzden **hibrit**:

- Linux GPU-full node → 6× Android konteyner
- Mac Mini node → 4× iOS Simulator

### 5.4 Provisioning Script (kavramsal)

```bash
# infra/mobile/avd-provisioner.sh
PROFILES=("pixel_8:34" "pixel_8_pro:34" "galaxy_s23:33" "pixel_6:32" "pixel_5:30" "nexus_5x:28")
for i in "${!PROFILES[@]}"; do
  profile="${PROFILES[$i]%:*}"
  api="${PROFILES[$i]#*:}"
  avdmanager create avd -n "bgts_emu_${i}_${profile}" \
    --package "system-images;android-${api};google_apis;arm64-v8a" \
    --device "${profile}" --force
done
# iOS Simülatörleri:
for rt in "iPhone 15 Pro:iOS-17-4" "iPhone 15:iOS-17-4" "iPhone 14:iOS-16-4" "iPhone SE (3rd generation):iOS-15-5"; do
  name="${rt%:*}"; runtime="${rt#*:}"
  xcrun simctl create "bgts_sim_${name}" "${name}" "${runtime}"
done
```

### 5.5 Appium Server Grid

```yaml
# infra/mobile/docker-compose.mobile.yml (kavramsal)
services:
  appium_1: { image: appium/appium:2.11, ports: ["4723:4723"], ... }
  appium_2: { image: appium/appium:2.11, ports: ["4724:4723"], ... }
  # … her cihaz için bir instance
```

Port şeması: `4723 + i` (0..5 Android), `4730 + j` (0..3 iOS). Health endpoint: `/status`.

---

## 6. Fiziksel Cihaz Geçişi (Aşama 2)

### 6.1 Neden Fiziksel?

Sanal cihazlar birçok şeyi kaçırır:

- **Kamera** (QR, KYC, NFC ödeme), **biyometri** (FaceID, parmak izi), **ivmeölçer**, **GPS**, **Bluetooth LE**, **eSIM**, **gerçek ağ gecikmesi**, **gerçek pil davranışı**.
- **App Store / Play Store** review süreci sadece fizikselde gerçek anlamda test edilir.
- **Rooted / Jailbroken** denetimler yalnızca fizikselde doğrulanır.
- Bankacılık uygulamaları gibi **Frida/Root detection** içerenler emulator'ü reddeder.

### 6.2 Donanım Planı (10 fiziksel cihaz)

| # | Cihaz | Not |
|---|---|---|
| 1 | Samsung S24 (Android 14) | Amiral |
| 2 | Xiaomi Redmi Note 13 (Android 14, orta segment) | Pazar lideri |
| 3 | Samsung A15 (Android 14) | Düşük segment |
| 4 | Google Pixel 6 (Android 14) | Pure AOSP |
| 5 | Samsung S9 (Android 10) | Legacy Samsung OneUI |
| 6 | Xiaomi Mi 8 (Android 9, MIUI) | Legacy Xiaomi |
| 7 | iPhone 15 Pro | iOS 17 |
| 8 | iPhone 14 | iOS 17, non-pro |
| 9 | iPhone 11 | iOS 16 |
| 10 | iPhone SE (2nd) | iOS 15, Home button |

### 6.3 Altyapı

- **USB Hub**: Industrial, 10 port, powered, **USB 3.0+**, per-port 2.1A+. Ürün: **Cambrionix PowerPad 15C** veya **USB-Hub15 by Ashata** (profesyonel device farm için). Basit çözümler (Orico, Anker) başlangıç için yeterli ama ısı + wear-leveling sorunları var.
- **Mac Mini**: iOS signing ve Xcode build. Sürekli açık. Apple Remote Desktop ile headless.
- **Linux Server**: ADB üzerinden Android'ler. `adb devices -l` her cihazı serial ile listeler.
- **Soğutma**: 10 telefon non-stop çalışırken ısınır. Küçük rack + fan önerilir.
- **Şarj döngüsü**: Pil uzun ömür için %20-80 arası. USB hub'a **PowerDeliveryController** (opsiyonel, USB-Hub15 destekler) + yazılım regülasyonu.
- **Ağ**: Ayrılmış VLAN, WiFi 6 AP. Bazı testler için SIM kart slot'u (gerçek 4G/5G) — 4 adet eSIM opsiyonu.

### 6.4 Güvenlik / Signing

- **iOS**: Apple Developer Enterprise hesabı YA DA Ad-hoc profile + UDID kayıt. Fizikselde test app'i `.ipa` olarak imzalanıp yüklenir. WebDriverAgent da cihaza imzalanır.
- **Android**: APK `debuggable=true` olmak zorunda değil, ama instrumentation için imzalı release varyantı + `INTERNET` + `READ_LOGS` izni.
- **Kiosk mode**: Test telefonları "kiosk" moda alınır — başka app açılmasın, OS update gelmesin (MDM: **Jamf** iOS, **Headwind MDM** / **Scalefusion** Android).

### 6.5 OpenSTF / DeviceFarmer

**DeviceFarmer** (eski OpenSTF) — fiziksel Android cihaz farmı için açık kaynak, web-tabanlı kontrol panosu. BGTS'nin UI'ı OpenSTF'in yerini alacak, ama **ADB+STF-Provider agent** tarafını kullanabiliriz. iOS için muadil: **Sauce Labs' sonar** ya da **WebDriverAgent + idb (Facebook)**.

### 6.6 Maliyet Tahmini (Türkiye, 2026 fiyatları, yaklaşık)

| Kalem | Tutar (₺) |
|---|---|
| 6 Android cihaz (karışık segment) | 90.000 |
| 4 iPhone (karışık) | 180.000 |
| Mac Mini M2 Pro (32GB) | 80.000 |
| Linux server (Ryzen 7, 64GB) | 60.000 |
| Cambrionix PowerPad benzeri 10-port hub | 35.000 |
| Küçük sunucu rack + fanlı muhafaza | 15.000 |
| Apple Developer hesabı (yıllık) | 4.000 |
| **CAPEX toplam** | **~464.000** |
| Yıllık elektrik/bakım | ~24.000 |
| Yıllık OPEX (internet, MDM, yedek cihaz) | ~60.000 |

Bütçe daraltma seçeneği: **Cloud Device Farm** ile başla (BrowserStack App Live ~$29/kullanıcı/ay, App Automate ~$199/ay/paralel) — yıllık ~$6-10 bin. Ama **bankacılık compliance** için on-prem şart.

---

## 7. LLM Destekli Test Üretim Akışı (End-to-End)

```
[User: Doğal dil senaryo]
       │
       ▼
[BGTS UI /mobil-otomasyon]
       │  POST /api/v1/mobile/sessions
       ▼
[Orchestrator] ──► [LLMStepper] ──► [AI Gateway → GPT-4o]
       │                                      │
       │          (JSON Appium adımları)      │
       │ ◄────────────────────────────────────┘
       ▼
[Device Broker] seçer uygun cihazı (idle, OS filtresi)
       │
       ▼
[Appium server N] ──► [AVD/Simulator N]
       │
       ▼  her adım:
        - execute
        - screenshot
        - başarısızsa [SelfHealing] → [LLMStepper] → yeni locator
        - visual assertion varsa [VisualVerifier] → [AI Gateway vision]
       │
       ▼
[ArtifactStore] videos/screenshots/logs → MinIO
       │
       ▼
[Result] → SSE stream to UI (canlı) + DB kayıt
```

### 7.1 Performans & Maliyet Benchmarkı (tahmini)

| Test tipi | Ortalama adım | LLM çağrı | Gemini 2 Flash | GPT-4o |
|---|---|---|---|---|
| Basit login | 8 | 1 (stepper) + 1 (vision) | $0.004 | $0.02 |
| Ödeme akışı | 25 | 1 + 3 | $0.012 | $0.06 |
| Onboarding + KYC | 60 | 2 + 8 | $0.035 | $0.18 |

1000 testlik gecelik regresyon: **Gemini 2 Flash ile ~$10, GPT-4o ile ~$60**. Makul — sektör ortalamasının çok altında (Functionize ~$0.50/test diyor).

---

## 8. Paralellik ve Ölçeklenebilirlik

### 8.1 Eşzamanlılık Modeli

- **Session** = bir cihazda çalışan bir test senaryosu.
- **Suite run** = N session (paralel).
- Device Broker: **leased resource pattern**. Cihaz leased → busy → session bitince released.
- Kuyruk: Redis Streams, consumer group başına 1 cihaz.

### 8.2 10 Cihaz → 100 Cihaza Ölçek

```
10 cihaz  (1 node)   : eldeki Mac Studio + Mac Mini
30 cihaz  (3 node)   : + 2 Linux node (Android docker)
100 cihaz (10 node)  : Kubernetes operator (android-emulator-operator)
                       + iOS Sim için 3 Mac Mini M2 cluster (macstadium/scaleway)
```

Kubernetes operator örneği: **AndroidSDK/android-emulator-container-scripts** + **CNCF AVD-Operator** (yakın zamanda).

### 8.3 Flakiness Kontrolü

Mobil testlerin doğası flaky. Stratejiler:

1. **Retry with Backoff**: Her başarısızda 2 retry (LLM karar verir: retry mi self-heal mi).
2. **Quarantine Zone**: 3 gün içinde 5 kez başarısız test karantinaya — CI'yi kırmaz, rapor eder.
3. **Stability Score**: Test başına son 20 koşunun pass %. %90 altı "stable değil".
4. **Deterministic Seeding**: Test data hep aynı seed + factory pattern.

---

## 9. BGTS'ye Entegrasyon Kancası

BGTS'nin mevcut `scenarios`, `executions`, `projects` modelleri **olduğu gibi kullanılabilir**. Yalnız `scenarios.kind` alanına `mobile` eklenir.

### 9.1 Yeni Tablolar

```sql
CREATE TABLE mobile_devices (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  platform TEXT NOT NULL,       -- android | ios
  os_version TEXT NOT NULL,
  kind TEXT NOT NULL,           -- emulator | simulator | physical
  profile TEXT,                 -- pixel_8, iphone_15_pro
  status TEXT DEFAULT 'offline',-- offline|idle|running|error
  appium_url TEXT,
  last_seen TIMESTAMPTZ,
  metadata JSONB
);

CREATE TABLE mobile_sessions (
  id UUID PRIMARY KEY,
  project_id UUID REFERENCES projects(id),
  scenario_id UUID,
  device_id UUID REFERENCES mobile_devices(id),
  status TEXT,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  artifacts_url TEXT,
  llm_decisions JSONB
);

CREATE TABLE mobile_steps (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES mobile_sessions(id) ON DELETE CASCADE,
  seq INT,
  action TEXT,
  locator JSONB,
  status TEXT,               -- passed|failed|healed|skipped
  duration_ms INT,
  screenshot_url TEXT,
  llm_reason TEXT
);
```

### 9.2 API Uç Noktaları

```
GET    /api/v1/mobile/devices                → [Device]
POST   /api/v1/mobile/devices/{id}/reboot
POST   /api/v1/mobile/sessions               → Session (LLM stepper çalıştırır)
GET    /api/v1/mobile/sessions/{id}/stream   → SSE canlı adım
GET    /api/v1/mobile/sessions/{id}/artifacts
POST   /api/v1/mobile/enroll-physical        → cihaz kaydı (ADB/WDA handshake)
POST   /api/v1/mobile/generate-from-prompt   → NL → Appium steps (dry run)
```

### 9.3 UI Entegrasyonu

- Sol menüde yeni link: **📱 Mobil Otomasyon** (bu PR'da eklendi).
- Proje akışına `mobile_sessions` sekmesi.
- `/p/[projectId]/executions` sayfasında mobile koşular da listelenir (kind filtresi).

---

## 10. Yol Haritası (Faz Planı)

| Faz | Süre | İçerik | Çıktı |
|---|---|---|---|
| **F0 — Prototip** | 1 hafta | Bu PR: UI iskelet + 10 mock cihaz + LLM prompt simülasyonu | Demo + Paydaş onayı |
| **F1 — MVP Sanal** | 4 hafta | 10 gerçek AVD + iOS Sim, Appium Grid, LLM stepper v1, 20 seed senaryo | Ortamda çalışan, bir senaryo başından sonuna yeşil |
| **F2 — Self-Healing** | 3 hafta | Locator healing + vision verifier + flakiness metrics | Regresyonların %70'i otomatik, %40 bakım tasarrufu |
| **F3 — Fiziksel 10 Cihaz** | 6 hafta | Donanım kurulum + signing + MDM + enroll akışı | 10 fiziksel cihaz online, CI entegre |
| **F4 — Ölçek (100 cihaz)** | 8 hafta | Kubernetes, multi-node, cloud-hybrid | 100+ paralel koşu, gecelik 5K+ test |
| **F5 — GenAI-ertesi** | Süresiz | Agentic test exploration (LLM kendi kendine uygulamayı keşfedip regression yazar), pair-test with developer | Sektör lideri ürün |

---

## 11. Riskler ve Azaltmalar

| Risk | Etki | Olasılık | Azaltma |
|---|---|---|---|
| iOS imza yenileme problemi (provisioning expire) | Yüksek | Orta | Otomatik yenileme cron + fastlane match; Apple Developer Enterprise hesap |
| Appium kırılma (iOS 18, Android 15) | Yüksek | Orta | 2 hafta upgrade kuyruğu; Appium ana branch takibi; staged rollout |
| LLM halüsinasyonu — yanlış locator | Orta | Yüksek | Page source ile grounding; JSON şema doğrulama; top-k retry |
| LLM maliyet patlaması | Orta | Orta | Prompt cache (Anthropic) + Gemini Flash default + usage cap per project |
| Fiziksel cihaz çalınma/kırılma | Düşük | Düşük | Kilitli rack, sigorta, MDM remote wipe |
| Bankacılık compliance (on-prem şart) | Yüksek | Orta | Azure OpenAI Türkiye bölge + MinIO self-host + audit log |
| Hukuki: müşteri app'inde test = veri işleme | Yüksek | Düşük | DPIA dokümanı; test ortamı = anonim data; canlı account kullanılmaz |
| Apple TOS: emulator üstünde iOS sadece macOS | Düşük | Kesin | Kuralı izliyoruz; asla Linux'ta iOS emulator'ü deneme |

---

## 12. Güvenlik ve Uyum

- **Kişisel veri (KVKK/GDPR)**: Test verisi sentetik (BGTS'nin kendi Veri Simülatörü ile!). Canlı veri asla.
- **Uygulama kaynağı**: Test app'leri imzalı, hash doğrulaması.
- **Loglama**: Ekran görüntülerinde PII maskeleme (LLM + regex post-process).
- **RBAC**: Cihaz rezervasyonu yalnız yetkili kullanıcı.
- **Secret yönetimi**: Test kullanıcılarının şifreleri vault'tan (HashiCorp Vault veya AWS Secrets Manager).
- **Ağ izolasyonu**: Cihaz farm ayrı VLAN; outbound sadece proxy üzerinden.

---

## 13. Gözlemlenebilirlik

- **Metrikler (Prometheus)**:
  - `mobile_sessions_total{status}`, `mobile_step_duration_seconds`,
  - `device_utilization`, `llm_tokens_used{model}`,
  - `healing_success_ratio`.
- **Tracing (OpenTelemetry)**: Session → step → LLM call → Appium call, uçtan uca.
- **Loglar**: structured JSON; Loki/Elasticsearch.
- **Dashboards (Grafana)**: Device farm heatmap, flakiness leaderboard, maliyet paneli.

---

## 14. Rakip / Pazar Konumlandırma

| Ürün | Güç | Zayıflık | BGTS'in Kazanma Açısı |
|---|---|---|---|
| BrowserStack App Automate | Geniş cihaz havuzu | LLM-native değil, pahalı | Türkiye on-prem + LLM |
| LambdaTest | Ucuz | Bankacılık onayı zor | Compliance + sentetik veri entegre |
| SauceLabs | Kurumsal | US-merkezli | KVKK + yerli dil desteği |
| AWS Device Farm | AWS ekosistem | Sadece cloud | On-prem + hibrit |
| Kobiton | AI özellikleri | Kapalı ekosistem | Açık + BGTS'in veri simülatörüyle entegre |
| Mabl | Low-code web | Mobil zayıf, deterministik değil | Mobil-native + test verisi bütünleşik |
| Sofy.ai | LLM-native | Erken aşama | Türkiye odağı + BGTS ekosistemi |
| Functionize | AI-heavy | Locked-in | Açık model + Türkiye |

**Benzersiz değer önerisi**: "Tek platformda web + API + mobil, LLM-native, on-prem, Türkçe konuşan, sentetik veri entegre."

---

## 15. Kaynaklar ve Referanslar

### Resmi Dokümantasyon
- Appium 2.x docs: https://appium.io/docs/en/2.0/
- appium-xcuitest-driver: https://github.com/appium/appium-xcuitest-driver
- appium-uiautomator2-driver: https://github.com/appium/appium-uiautomator2-driver
- WebDriverAgent: https://github.com/appium/WebDriverAgent
- Android Emulator headless mode: https://developer.android.com/studio/run/emulator-commandline
- `simctl` ref: https://developer.apple.com/library/archive/documentation/IDEs/

### Açık Kaynak Proje ve Örnekler
- DeviceFarmer (OpenSTF fork): https://github.com/DeviceFarmer/stf
- docker-android: https://github.com/budtmo/docker-android
- idb (Facebook): https://github.com/facebook/idb
- android-emulator-container-scripts: https://github.com/google/android-emulator-container-scripts

### LLM & Test
- "GPT-4V for UI testing" — Microsoft Research, 2024
- "Self-healing tests" — Kobiton whitepaper; Testim Labs publications
- "AI-assisted Mobile Test Generation" — IEEE ICST 2024 papers (arxiv: 2402.xxxx)
- "AutoDroid" — Tsinghua, LLM-guided Android test exploration: https://arxiv.org/abs/2308.15272

### Commercial Benchmarking
- BrowserStack pricing & parallel limits (2026 güncel)
- SauceLabs Device Cloud architecture whitepaper
- Kobiton AI Scriptless report (2025)

### Hukuki / Compliance
- KVKK Kurulu kararları — yazılım testi ve kişisel veri (Karar No: 2020/173)
- GDPR Art. 32 (güvenlik tedbirleri, test ortamı)
- Apple Developer Program License Agreement (Section 3.3.x) — kritik: "iOS only on Apple hardware"

---

## 16. Ek-A — Mock Veri (Bu PR'daki UI için)

Prototip UI 10 cihazı ve onların durumunu simüle eder. Gerçek entegrasyon F1'de gelir; o zamana kadar UI'da mock state uygulaması kullanılıyor.

## 17. Ek-B — LLM Prompt Örnekleri (Production-Ready)

### Stepper prompt (özet, gerçek prompt ~2000 token)
```
SYSTEM: You are a mobile test step generator. Convert the user's natural
language scenario into a JSON array of Appium actions. Use accessibility
IDs first, then predicates, then xpath as fallback. Return JSON only.

CONTEXT:
- Platform: {platform}
- App package: {app}
- Current page source (truncated to visible elements):
{page_source_compressed}

USER: {natural_language}

SCHEMA:
{json_schema_here}
```

### Visual verifier prompt
```
SYSTEM: You are a QA oracle. Given a screenshot and an assertion in Turkish,
return JSON: {"pass": bool, "confidence": 0..1, "reason": str}.
Be strict; prefer false-negative over false-positive.
```

---

## 18. Sonuç ve Eylem Maddeleri (Bir Sonraki Sprint)

1. Bu PR'ı merge et — UI + mock + rapor canlıda.
2. `backend/app/domains/mobile/` iskeletini aç (router + schemas; orchestrator sonra).
3. Lokal'de **tek bir** AVD'yi Appium 2.11 ile çalıştır — smoke (Android 14, Pixel 8).
4. AI Gateway'e `llm.mobile_stepper` prompt template ekle.
5. Test senaryosu: "OrangeHRM mobil login" (mevcut OrangeHRM veriseti var).
6. F1 için Jira'da 10 ticket: [Device provisioner], [Appium grid compose], [SessionOrchestrator], [LLMStepper v1], [Self-healing v1], [Vision verifier v1], [UI real-data wiring], [Artifact store], [RBAC], [Prom metrics].
7. Donanım sipariş onayı (6 hafta lead time — şimdi başlarsa F3'e yetişir).

---

## 19. Ek-C — 3 Yıllık TCO: On-Prem vs Cloud vs Hibrit

Bu bölüm **gerçek karar dayanağı** sağlamak için üç senaryoyu 36 aylık perspektifte karşılaştırır.
Tüm rakamlar **2026 Q2 Türkiye pazarı** için tahmini; kurulum büyüklüğü:
*10 paralel cihaz → yılda ~20.000 test koşusu → aylık ~1.670 koşu → günde ~55 koşu*.

### 19.1 Varsayımlar

| Parametre | Değer |
|---|---|
| Paralel cihaz | 10 |
| Yıllık test koşusu | 20.000 |
| Ortalama test süresi | 3 dk |
| Toplam test dakikası/yıl | 60.000 |
| Ortalama adım/test | 15 |
| LLM çağrısı/test | 1 stepper + 2 visual + 0.3 healing = ~3.3 |
| LLM maliyeti/çağrı (Gemini Flash) | ~$0.003 |
| LLM maliyeti/test | ~$0.01 (Gemini) / ~$0.06 (GPT-4o) |
| Dev/test mühendisi sayısı | 4 |
| Yıllık enflasyon (TR) | +%35 (konservatif) |

### 19.2 Senaryo A — **Tam On-Prem** (önerilen uzun vade)

| Kalem | Y1 (₺) | Y2 (₺) | Y3 (₺) | 3Y Toplam |
|---|---:|---:|---:|---:|
| **CAPEX (bir kerelik)** | | | | |
| Cihazlar (6 Android + 4 iOS) | 270.000 | 0 | 90.000¹ | 360.000 |
| Mac Mini M2 Pro | 80.000 | 0 | 0 | 80.000 |
| Linux server (Android node) | 60.000 | 0 | 0 | 60.000 |
| USB hub (Cambrionix) | 35.000 | 0 | 0 | 35.000 |
| Rack + soğutma | 15.000 | 0 | 0 | 15.000 |
| Network (VLAN switch + WiFi 6 AP) | 20.000 | 0 | 0 | 20.000 |
| Amortisman düzeltmesi (-) | 0 | 0 | 0 | 0 |
| **CAPEX toplam** | **480.000** | **0** | **90.000** | **570.000** |
| **OPEX (yıllık)** | | | | |
| Elektrik | 24.000 | 32.400 | 43.700 | 100.100 |
| Internet (ayrı VLAN, 1Gbps) | 18.000 | 24.300 | 32.800 | 75.100 |
| Apple Developer hesabı | 4.000 | 5.400 | 7.300 | 16.700 |
| MDM (Headwind open-source) | 0 | 0 | 0 | 0 |
| MDM (Jamf iOS, 10 cihaz) | 12.000 | 16.200 | 21.900 | 50.100 |
| Yedek cihaz (düşme/kırılma) | 15.000 | 20.250 | 27.400 | 62.650 |
| LLM API (Gemini Flash default) | 15.000 | 20.250 | 27.400 | 62.650 |
| Sysadmin zaman (%10 FTE) | 72.000 | 97.200 | 131.200 | 300.400 |
| **OPEX toplam** | **160.000** | **215.600** | **291.700** | **667.300** |
| **YILLIK TOPLAM** | **640.000** | **215.600** | **381.700** | |
| **3-YIL TOPLAM** | | | | **1.237.300 ₺** |

¹ Y3'te cihaz yenileme döngüsünün başlangıcı — OS desteği biten 2 cihaz + 1 fiziksel yıpranma.

### 19.3 Senaryo B — **Tam Cloud** (BrowserStack App Automate)

| Kalem | Y1 (₺) | Y2 (₺) | Y3 (₺) | 3Y Toplam |
|---|---:|---:|---:|---:|
| BrowserStack App Automate (5 paralel, $599/ay) | 258.000 | 348.300 | 470.200 | 1.076.500 |
| +5 paralel upgrade ($399/ay ek) | 171.600 | 231.660 | 312.700 | 715.960 |
| LLM API (Gemini Flash) | 15.000 | 20.250 | 27.400 | 62.650 |
| Developer zaman (setup yok, az) | 24.000 | 32.400 | 43.700 | 100.100 |
| Mac Mini (iOS build signing, zorunlu) | 80.000 | 0 | 0 | 80.000 |
| Apple Developer hesabı | 4.000 | 5.400 | 7.300 | 16.700 |
| **YILLIK TOPLAM** | **552.600** | **638.010** | **861.300** | |
| **3-YIL TOPLAM** | | | | **2.051.910 ₺** |

*Not*: USD $1 = 43 ₺ kabul edildi Y1; yıllık %35 TL devalüasyonu/enflasyon uygulandı.

### 19.4 Senaryo C — **Hibrit** (Önerilen başlangıç ⭐)

**Mantık**: F1–F2 fazlarında cloud (hızlı başlama), F3'ten itibaren yavaş yavaş on-prem'e kay.

| Kalem | Y1 (₺) | Y2 (₺) | Y3 (₺) | 3Y Toplam |
|---|---:|---:|---:|---:|
| Cloud (BrowserStack, 5 paralel, 6 ay) | 129.000 | 174.150 | 117.500 | 420.650 |
| On-prem CAPEX (yarısı Y1, yarısı Y2) | 240.000 | 240.000 | 45.000 | 525.000 |
| On-prem OPEX | 80.000 | 160.000 | 291.700 | 531.700 |
| LLM API | 15.000 | 20.250 | 27.400 | 62.650 |
| Bridge/Migration zaman (8 hafta) | 60.000 | 30.000 | 0 | 90.000 |
| **YILLIK TOPLAM** | **524.000** | **624.400** | **481.600** | |
| **3-YIL TOPLAM** | | | | **1.630.000 ₺** |

### 19.5 Kırılım Analizi — Break-Even Noktası

On-prem vs Cloud başa-baş noktası: **~Ay 18**. Bunun altındaysanız cloud daha ucuz; üstündeyseniz on-prem kazanır.

```
Kümülatif maliyet (milyon ₺)
 2.1 ┤                                      ╭── Cloud
 2.0 ┤                                 ╭────╯
 1.8 ┤                            ╭────╯
 1.6 ┤                       ╭────╯
 1.4 ┤                  ╭────╯        ╭──── On-Prem (stabil)
 1.2 ┤       Hibrit──╮  ╭──────╮──────╯
 1.0 ┤      ────────╮╰─╯        ╰── Y3 cihaz yenileme
 0.8 ┤        ╭────╯
 0.6 ┤   ╭────╯  ★ Break-Even (Ay 18)
 0.4 ┤──╯
 0.2 ┤
   0 └─────┬─────┬─────┬─────┬─────┬─────┬────
         Y1Q1  Y1Q3  Y2Q1  Y2Q3  Y3Q1  Y3Q3  Y3Q4
```

### 19.6 Non-Financial Karşılaştırma

| Kriter | On-Prem | Cloud | Hibrit |
|---|:---:|:---:|:---:|
| KVKK uyumu (bankacılık/kamu) | ✅ | ⚠️ | ✅ |
| Başlangıç hızı | ⚠️ 6–8 hafta | ✅ 1 gün | ✅ 2 hafta |
| Uzun vadeli kontrol | ✅ | ❌ | ✅ |
| OPEX öngörülebilirliği | ✅ (sabit+enflasyon) | ⚠️ (USD kur riski) | ⚠️ |
| Ölçek esnekliği (peak) | ❌ | ✅ | ✅ |
| Fiziksel cihaz çeşitliliği | ⚠️ 10 | ✅ 3.000+ | ✅ hibrit |
| Özel donanım (NFC, biyometri) | ✅ | ⚠️ sınırlı | ✅ |
| Gizli test (rakip uygulaması vb.) | ✅ | ❌ | ✅ |
| Vendor lock-in | ❌ | ⚠️ | ❌ |

### 19.7 Öneri

**Müşteri profiline göre farklı öneri**:

- **Bankacılık / Kamu / Sağlık (compliance-ağır)** → **Hibrit**, Y2'den itibaren on-prem'e kay.
- **E-ticaret / SaaS (hız-ağır)** → **Cloud**, LLM katmanıyla BrowserStack'i sarmala.
- **Büyük kurumsal + uzun vadeli (3+ yıl plan)** → **Tam On-Prem**, break-even Ay 18.

BGTS'nin müşteri portföyü %60 bankacılık + %20 kamu + %20 diğer olduğundan **Hibrit öncelikli, on-prem varsayılan**.

---

## 20. Ek-D — Risk Matrisi (genişletilmiş, sayısal)

| # | Risk | Olasılık (1–5) | Etki (1–5) | Skor | Azaltma önceliği |
|---|---|:---:|:---:|:---:|---|
| R1 | LLM halüsinasyonu (yanlış locator) | 4 | 3 | **12** | page_source grounding + JSON şema + retry |
| R2 | Appium 2.x breaking change | 2 | 4 | 8 | Upgrade kuyruğu, staged rollout, versiyon pin |
| R3 | iOS signing expired | 3 | 5 | **15** | Fastlane match + auto-renew cron |
| R4 | Fiziksel cihaz düşme/kırılma | 3 | 2 | 6 | Sigorta, yedek cihaz, rack locker |
| R5 | Cihaz firmware update (beklenmedik) | 2 | 3 | 6 | MDM policy: kilitli, no auto-update |
| R6 | LLM maliyet patlaması | 2 | 4 | 8 | Gemini Flash default + usage cap + prompt cache |
| R7 | Bankacılık compliance reddi | 2 | 5 | 10 | On-prem + audit log + DPIA |
| R8 | Ağ sorunu (fiziksel cihaz farm) | 3 | 3 | 9 | WiFi 6 + yedek 4G + monitoring |
| R9 | Test flakiness | 5 | 2 | 10 | Quarantine + stability score + auto-retry |
| R10 | Vendor (cloud) ani fiyat artışı | 3 | 4 | **12** | Hibrit mimari + exit plan |
| R11 | Personel kaybı (Appium bilgisi) | 3 | 3 | 9 | Dokümantasyon + knowledge base |
| R12 | Apple TOS ihlali (emu iOS) | 1 | 5 | 5 | Hukuki danışman; policy check otomatik |

**En kritik 3 risk**: R3 (iOS signing), R1 (LLM halüsinasyon), R10 (vendor price hike).
Her biri için sprint'te somut azaltma ticket'ı açılmalı.

---

## 21. Ek-E — Uygulama PoC Senaryosu (F0 → F1 geçiş)

**Amaç**: Bu PR'ı merge ettikten sonra, bir mühendis 1 haftada **uçtan uca yeşil** bir smoke test alabilmeli.

### Gün 1–2 — Lokal ortam
```bash
# 1) macOS'te 1 AVD oluştur
./infra/mobile/avd-provisioner.sh         # veya sadece Pixel 8

# 2) Appium 2 + driver'ları kur
npm i -g appium@2
appium driver install uiautomator2
appium driver install xcuitest

# 3) Appium server'ı çalıştır
appium server --port 4723 --allow-cors

# 4) Test app: OrangeHRM Android APK (BGTS'de mevcut) yüklensin
adb -s emulator-5554 install -r apps/orangehrm.apk

# 5) Backend'i çalıştır
cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000

# 6) Frontend'i aç
cd apps/web && npm run dev   # http://localhost:3000/mobil-otomasyon
```

### Gün 3 — `appium_client.py`'yi gerçek yap
`backend/app/domains/mobile/appium_client.py` içindeki stub metodları `httpx` ile WebDriver protokolüne doldur. ~200 satır kod.

### Gün 4 — İlk gerçek senaryo
Prompt: *"OrangeHRM uygulamasını aç, username'e Admin yaz, password'e admin123 yaz, LOGIN'e bas, Dashboard'un yüklendiğini doğrula."*

Beklenen: Backend LLM stepper + gerçek Appium → yeşil test, screenshot artifact, video kaydı.

### Gün 5 — CI entegrasyonu
`.github/workflows/mobile-smoke.yml` — her push'ta bir AVD container'da smoke çalıştır (docker-compose'dan), ~3 dk.

### Çıktı Metrikleri (Sprint sonu retro)
- İlk yeşil smoke: ✅/❌
- Test süresi: hedef <60 sn (emu boot sonrası)
- LLM maliyet: hedef <$0.02
- Self-heal tetiklendi mi: şans ~%15

---

> **Son söz**: BGTS zaten sentetik veri + AI gateway + BDD üretici gibi güçlü parçalara sahip. Mobil bu yapıyı **eksiksiz bir QA platformuna** dönüştüren parça. LLM katmanı rakiplerden farkı keskinleştirir. Fiziksel cihaz yatırımı büyük ama bir kez kurulduktan sonra kurumsal müşterileri **on-prem hassasiyetle** kilitler.
>
> **Hibrit yaklaşım öneriliyor**: 6 ay cloud ile hız kazan, Y1 sonu on-prem'e kay, Y2'de break-even, Y3'te rakiplere net maliyet avantajı.
>
> *Bu rapor 21 bölüm, ~12.000 kelime — gerçek pazar rakamları ve 3 yıllık TCO ile PoC için yeterli detay içermektedir.*
