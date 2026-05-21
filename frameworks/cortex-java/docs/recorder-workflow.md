# Recorder Workflow — Cortex login akışını yakalama

Bu doküman, framework'ün generic CSS fallback'leri yerine **gerçek Cortex selektörleri** ile çalışması için gereken adım-adım iş akışıdır.

## Önkoşul: env hazır mı?

```bash
cd frameworks/cortex-java
./scripts/setup-env.sh        # .env üretir + AES key oluşturur
$EDITOR .env                  # CORTEX_USERNAME / CORTEX_PASSWORD doldur

# Şifreli alias kaydı (bir kez)
./mvnw test \
  -Dcucumber.features=src/test/resources/scratch/setup-password.feature \
  -Dcucumber.filter.tags="@setup"

# Kontrol
ls src/main/resources/password.properties   # var olmalı
```

## Yöntem A — IntelliJ Run > Recorder ▶ (önerilen)

### 1. Run config'i seç
IntelliJ sağ-üst dropdown → **`Cortex_Recorder`** seç → **▶ Run**

Konsolu izle:
```
============================================================
 Cortex Recorder
============================================================
RecorderConfig {
  targetUrl     = https://cortex-test.bgtsai.com/
  serverPort    = 7700
  outputDir     = .../recordings
  featureName   = recorded_20260520_213456
  browser       = chromium
  ...
}
[Recorder] HTTP server listening on http://127.0.0.1:7700
[Recorder] Browser launched. Recording started.
```

### 2. Tarayıcıda gez
Açılan Chromium penceresinde:

| İşlem | Beklenen |
|---|---|
| Sayfanın yüklenmesini bekle | Sağ alt köşede 🔴 REC toolbar belirir |
| Username alanına tıkla → kullanıcı adını yaz | recorder.js her keystroke'u 350ms debounce ile yakalar |
| Şifre alanına tıkla → **prompt çıkar**: *"Bu şifre alanını hangi alias ile saklayalım?"* → `cortexUser` yaz | Şifre value'su `recorded_password` ile değiştirilir (güvenlik) |
| "Giriş Yap" butonuna tıkla | Click event → action |
| **Dashboard yüklendi mi?** → Toolbar'da **"Doğrulama"** modu aç → dashboard elemanına tıkla | Assert action eklenir |

### 3. Bittiğinde
İki yol:
- **Toolbar'da "Durdur ve Kaydet"** (önerilen — temiz exit)
- **IntelliJ Stop ▣** (JVM shutdown hook devreye girer)

Konsol:
```
============================================================
 RECORDING COMPLETE
============================================================
 Feature:  .../recordings/recorded_20260520_213456.feature
 Locator:  .../recordings/locators/recorded_20260520_213456.json
 Actions:  12
 Locators: 8
============================================================
 Run with:
   mvn test -Dcucumber.features=.../recorded_20260520_213456.feature
```

### 4. Selektörleri kalıcı locator'lara aktar

Aç: `src/test/resources/recordings/locators/recorded_20260520_213456.json`

Tipik içerik:
```json
[
  { "key": "kullaniciAdiInput", "type": "name", "value": "username" },
  { "key": "girisYapButton",    "type": "xpath", "value": "//button[normalize-space()='Giriş Yap']" },
  { "key": "dashboardHome",     "type": "css", "value": "[data-testid='dashboard-main']" }
]
```

**Bu selektörler gerçek!** Şimdi `projects/cortex/locators/login.json`'a aktarmak için 2 yol:

#### Yol A — Direkt aktarma (önerilen)
1. Recordings JSON'undaki entry'leri `projects/cortex/locators/login.json` **başına** koy
2. Existing key isimleri (`userNameInput`, `loginButton`, `dashboardHome`) ile eşle:
   ```json
   { "key": "userNameInput", "type": "name", "value": "username" },
   { "key": "loginButton",   "type": "xpath", "value": "//button[normalize-space()='Giriş Yap']" },
   { "key": "dashboardHome", "type": "css",   "value": "[data-testid='dashboard-main']" },
   ```
3. Mevcut generic CSS fallback'ler aşağıda kalır (multi-fallback safety net)

#### Yol B — Recordings dosyasını project locator'a rename
1. `recordings/recorded_20260520_213456.json` → `projects/cortex/locators/login.json` (mevcutu yedekle)
2. Key isimlerini kontrol et (recorder camelCase Türkçe → ASCII yapar)

### 5. Doğrula

```bash
# Cortex smoke tekrar dene
./scripts/cortex smoke

# Beklenen: önceki 0 pass → şimdi N pass
```

## Yöntem B — CLI ile

```bash
# Default URL
./scripts/cortex record

# Özel URL
./scripts/cortex record https://cortex-test.bgtsai.com/login

# Özel feature adı
./mvnw -Precorder compile exec:java \
  -Drecorder.url=https://cortex-test.bgtsai.com/login \
  -Drecorder.feature.name=cortex_login_v2
```

## Toolbar referansı

Sağ-alt köşede sabit toolbar:

```
🔴 REC  [3]  [Duraklat] [↶ Geri Al] [Doğrulama] [+ Bekleme] [Durdur ve Kaydet]
                                                              recent: nav, click, fill...
```

| Buton | İşlev |
|---|---|
| **Duraklat / Devam et** | Olay yakalamayı askıya al |
| **↶ Geri Al** | Son aksiyonu sil (yanlış tıklama vs.) |
| **Doğrulama** | Tıklanacak eleman = assertion (görünür mü?) |
| **+ Bekleme** | Manuel `I wait for N seconds` ekle |
| **Durdur ve Kaydet** | Graceful exit, dosyaları yaz |

## Yakalanan event'ler

| Browser olayı | Üretilen Gherkin |
|---|---|
| Sayfa yükleme (SPA route dahil) | `Given I open the recorded url "<url>"` |
| Tıklama | `When I click "<key>"` |
| Input/Yazma (debounced 350ms) | `* I write "<text>" into "<key>"` |
| Şifre input | `* I enter encrypted password alias "<alias>" into "<key>"` |
| Enter/Esc/Tab | `* I press "<KEY>"` |
| Doğrulama modu | `Then I see "<key>"` |
| + Bekleme butonu | `* I wait for <n> seconds` |

## Locator key türetme algoritması

`LocatorBuilder.toCamelKey()`:
- "Giriş Yap" → `girisYap` (Türkçe sadeleştirilir)
- "kullanici_adi" → `kullaniciAdi`
- Tag bazlı suffix: button → `Button`, input → `Input`, a → `Link`
- Dedup: aynı key 2. kez gelirse `_2`, `_3`...

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Browser açılıyor ama recorder.js enjekte olmuyor | Console'da `[Cortex Recorder] aktif` mesajı görmelisin. Yoksa: log4j2 + Playwright init script'ler yüklü mü? |
| Toolbar görünmüyor | recorder.css inject edildi mi? Network tab → 127.0.0.1:7700 reachable mı? |
| Stop'a bastım ama dosya yazılmadı | Konsol'da `RECORDING COMPLETE` görünmüyorsa: `actions` boş gelmiş. En az 1 click yap. |
| Port 7700 dolu | Recorder otomatik 7701, 7702… dener (max 10 retry). Konsol'da `Port 7700 was busy, using 7701` görünür. |
| Cortex sitesi `net::ERR_ABORTED` | Site SPA redirect yapıyor — `PwCommonMethods.open` zaten tolerate ediyor, smoke'da problem yok |

## Kayıt sonrası test çalıştırma

```bash
# Yeni feature'ı dene
./mvnw test -Dcucumber.features=src/test/resources/recordings/recorded_*.feature

# Veya CLI
./scripts/cortex feature src/test/resources/recordings/recorded_*.feature
```

Pass ediyorsa selektörler doğru. Edit/rename ile resmi yere taşı (Yol A/B yukarıda).
