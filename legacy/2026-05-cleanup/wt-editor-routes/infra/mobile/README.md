# BGTS Mobil Otomasyon Altyapısı

Bu klasör, mobil test otomasyon grid'inin lokal / stage / prod provisioning dosyalarını içerir.

## İçerik

- `docker-compose.mobile.yml` — Linux host'ta 3 Android emulator + Appium (budtmo/docker-android).
- `avd-provisioner.sh` — macOS/Linux'ta 6 Android AVD + 4 iOS Simulator oluşturur / siler.

## Hızlı Başlangıç

### macOS (iOS + Android, BGTS dev ortamı)

```bash
# 1. AVD + iOS Sim oluştur (~10–20 dk, system image'ları indirir)
./infra/mobile/avd-provisioner.sh

# 2. İlk Android AVD'yi başlat (yeni terminal)
emulator -avd bgts_pixel_8 -no-snapshot-load &

# 3. İlk iOS Simulator'ü başlat
xcrun simctl boot bgts_iphone_15_pro
open -a Simulator

# 4. Appium 2'yi kur (ilk kez)
npm install -g appium@2
appium driver install xcuitest
appium driver install uiautomator2

# 5. Appium server başlat (port 4723)
appium server --port 4723 --allow-cors &

# 6. BGTS backend zaten /api/v1/mobile/* endpoint'lerini sağlıyor.
# Frontend: http://localhost:3000/mobil-otomasyon
```

### Linux (sadece Android, prod grid önizleme)

```bash
docker compose -f infra/mobile/docker-compose.mobile.yml up -d
# 3 Android emulator container açılır:
#   appium: http://localhost:4723, :4724, :4725
#   noVNC:  http://localhost:6080, :6081, :6082 (cihazı tarayıcıdan izle)
```

## Portlar ve Cihaz Eşleme

| Cihaz ID (BGTS) | Appium Port | Tip | OS |
|---|---|---|---|
| `and-pixel_8` | 4723 | AVD | Android 14 |
| `and-pixel_8_pro` | 4724 | AVD | Android 14 |
| `and-galaxy_s23` | 4725 | AVD | Android 13 |
| `and-pixel_6` | 4726 | AVD | Android 12 |
| `and-pixel_5` | 4727 | AVD | Android 11 |
| `and-nexus_5x` | 4728 | AVD | Android 9 (legacy, default offline) |
| `ios-iphone_15_pro` | 4730 | Sim | iOS 17 |
| `ios-iphone_15` | 4731 | Sim | iOS 17 |
| `ios-iphone_14` | 4732 | Sim | iOS 16 |
| `ios-iphone_se_3` | 4733 | Sim | iOS 15 |

## Fiziksel Cihaz Eklemek (Faz 3)

1. Android: USB debugging aç, cihazı USB hub'a tak, `adb devices` ile doğrula.
2. iOS: Apple Developer hesabı, UDID kayıtlı provisioning, WDA imzalı.
3. BGTS UI → Mobil Otomasyon → `+ Fiziksel Cihaz Kaydet` modal'ını doldur.
4. Backend `POST /api/v1/mobile/enroll-physical` handshake yapar.

## İleri Adımlar

- **F1**: `appium_client.py` gerçek HTTP istemci ile doldurulacak.
- **F2**: `visual_verifier.py` vision LLM endpoint'ine bağlanacak.
- **F3**: Bu dosyalar fiziksel cihaz MDM (Headwind / Jamf) ile eşleşecek.
- **F4**: Kubernetes operator ile 100+ cihaza ölçek.

Tam mimari ve araştırma için: [`docs/MOBIL_OTOMASYON_ARASTIRMA_RAPORU.md`](../../docs/MOBIL_OTOMASYON_ARASTIRMA_RAPORU.md)
