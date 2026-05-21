# Recorder — IntelliJ Run

Cortex sitesini gezerken yaptıklarınızı **Cucumber feature** + **locator JSON** dosyasına otomatik çeviren araç.
Dashboard'dan **bağımsız**, tamamen IntelliJ üzerinden yönetilir.

## Mimari

```
IntelliJ Run > Recorder
        │
        ▼
RecorderMain  ─── system properties (-Drecorder.*) ─── RecorderConfig
        │
        ├─► RecorderServer  (127.0.0.1:7700, jdk.httpserver)
        │       ├── POST /action
        │       ├── POST /stop
        │       ├── GET  /status
        │       └── GET  /actions
        │
        └─► Playwright Chromium
                ├── addInitScript:  recorder.js + recorder.css
                └── kullanıcı gezerken her olay POST /action ediliyor

User clicks "Durdur ve Kaydet" ─► POST /stop ─► stopSignal.complete()
IntelliJ Stop                  ─► shutdown hook ─► persist()

persist():
        ActionTranslator  →  Gherkin satırları + locator havuzu
        FeatureWriter     →  *.feature + locators/*.json
```

## Çalıştırma

### Yöntem 1 — IntelliJ
1. **Run → Edit Configurations** menüsünden `Recorder` (Maven) veya `Recorder (custom URL)` seçili.
2. **Run** ▶
3. Chromium açılır → cortex-test.bgtsai.com'a gider → sağ alt köşede kayıt toolbar'ı belirir.
4. Kayda almak istemediğin adımlar varsa **Duraklat**.
5. Doğrulama (assertion) eklemek için **Dogrulama** moduna gir → istediğin elemana tıkla.
6. Bittiğinde **Durdur ve Kaydet** veya IntelliJ **Stop** ▣ butonu.
7. Konsola dosya yolu yazılır:
   ```
   Feature:  src/test/resources/recordings/recorded_20260520_184312.feature
   Locator:  src/test/resources/recordings/locators/recorded_20260520_184312.json
   ```

### Yöntem 2 — Komut satırı
```bash
mvn -Precorder compile exec:java \
    -Drecorder.url=https://cortex-test.bgtsai.com/login \
    -Drecorder.feature.name=cortex_login_yeni \
    -Drecorder.output.dir=src/test/resources/cortex
```

## Konfigürasyon (`recorder.properties` veya `-D`)

| Anahtar | Varsayılan | Açıklama |
|---|---|---|
| `recorder.url` | `https://cortex-test.bgtsai.com/` | Açılacak URL |
| `recorder.port` | `7700` | RecorderServer HTTP portu |
| `recorder.output.dir` | `src/test/resources/recordings` | Çıktı klasörü |
| `recorder.feature.name` | (boş = otomatik timestamp) | Feature dosya adı |
| `recorder.browser` | `chromium` | `chromium` / `firefox` / `webkit` |
| `recorder.headless` | `false` | Görünmez modda |
| `recorder.viewport.width` | `1440` | |
| `recorder.viewport.height` | `900` | |

## Yakalanan olaylar

| Browser olayı | Üretilen Gherkin |
|---|---|
| Sayfa yükleme | `Given I open the recorded url "<url>"` |
| Tıklama | `When I click "<key>"` |
| Input/Yazma | `* I write "<text>" into "<key>"` |
| Şifre input (type=password) | `* I enter encrypted password alias "recordedPassword" into "<key>"` |
| Select değişimi | `* I write "<value>" into "<key>"` |
| Enter/Esc/Tab | `* I press "<KEY>"` |
| Scroll | `* I scroll to "<key>"` |
| Hover | `* I hover over "<key>"` |
| Bekleme (toolbar'dan) | `* I wait for <n> seconds` |
| Görünür (assert mode) | `Then I see "<key>"` |
| Metin içerir (assert mode) | `Then I verify "<key>" contains "<text>"` |

## Locator strategy

`LocatorBuilder.java` (öncelik sırası):
1. `data-testid` / `data-cy` / `data-qa`
2. Sabit `id` (auto-generated formatlar `:r0:`, `mui-12`, UUID elenir)
3. `name` attribute
4. `aria-label`
5. Görünür metin (button/a için XPath)
6. `placeholder` (input için)
7. Recorder.js'in ürettiği CSS path
8. XPath fallback

Key türetme: Türkçe karakterler sadeleştirilir, camelCase olur, deduplikasyon `_2`, `_3` ile.

## Kayıt sonrası test çalıştırma

Recorder çıkışında üretilen feature **doğrudan Selenium veya Playwright runner'la** çalışır:

```bash
# Selenium
mvn test -Dcucumber.features=src/test/resources/recordings/recorded_20260520_184312.feature

# Playwright (paralel değil)
mvn -Pplaywright test -Dcucumber.features=src/test/resources/recordings/recorded_20260520_184312.feature
```

Locator JSON otomatik yüklenir (`PwLocatorReader` ve `JsonReader` `recordings/locators/` yolunu da tarar).
