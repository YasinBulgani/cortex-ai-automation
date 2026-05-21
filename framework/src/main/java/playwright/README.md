# Playwright Paralel Test Runner

Mevcut Selenium framework'üne ek olarak **Playwright Java** tabanlı, **N-thread paralel** çalışabilen ikinci bir runner.

## Neden iki engine?

| | Selenium | Playwright |
|---|---|---|
| Olgunluk | ★★★★★ | ★★★★ |
| Hız (single) | normal | 2-3× daha hızlı |
| Auto-wait | manuel | yerleşik |
| Paralel izolasyon | driver paylaşımlı zor | `BrowserContext` ile native |
| iFrame/shadow DOM | zor | kolay |
| Hata teşhisi | screenshot | trace + video |

**Feature dosyaları ortak.** Aynı `*.feature` her iki runner'la da çalışır — sadece glue paketi farklı.

## Mimari

```
PlaywrightFactory (ThreadLocal)
   ├── Playwright   (1 per thread, lazy)
   ├── Browser      (1 per thread, lazy)
   ├── BrowserContext (1 per scenario, izole)
   └── Page         (1 per scenario)
       ▲
       │ ThreadLocal accessor
       │
   PwHooks (@Before/@After) ─── PwConfigSteps (locator map per thread)
       │
       ▼
   PwCommonSteps (Gherkin → method library)
       │
       ▼
   PwCommonMethods / PwInputMethods / PwAssertionMethods
       │
       ▼
   page().click(...) / page().fill(...) / assertThat(...)
```

## Çalıştırma

### IntelliJ Run Configurations (`.run/` klasöründe hazır)

| Konfig | Komut karşılığı |
|---|---|
| `Playwright Tests` | `mvn -Pplaywright test` |
| `Playwright Parallel (4 thread)` | `mvn -Pplaywright,parallel test` |
| `Playwright Parallel (8 thread)` | `mvn -Pplaywright,parallel -Dparallel.threads=8 test` |
| `Selenium Tests (legacy)` | `mvn test` |

### CLI

```bash
# Sequential (tek thread)
mvn -Pplaywright test

# Paralel 4 thread (default)
mvn -Pplaywright,parallel test

# Paralel 8 thread
mvn -Pplaywright,parallel -Dparallel.threads=8 test

# Belirli feature
mvn -Pplaywright test -Dcucumber.features=src/test/resources/playwright/cortex_login_pw.feature

# Tag filtresi
mvn -Pplaywright,parallel test -Dcucumber.filter.tags="@smoke"

# Browser değiştir
mvn -Pplaywright test -Dplaywright.browser=firefox

# Headless
mvn -Pplaywright,parallel test -Dplaywright.headless=true
```

### İlk kez çalıştırma — browser indirimi

Playwright, ilk çalıştırmada kendi browser binary'lerini indirir (~150 MB). Otomatik olur ama manuel tetiklemek isterseniz:

```bash
mvn compile
mvn exec:java -Dexec.mainClass=com.microsoft.playwright.CLI -Dexec.args="install"
```

## Konfigürasyon

`config.properties` veya `-D` ile:

| Anahtar | Varsayılan | Açıklama |
|---|---|---|
| `playwright.browser` | `chromium` | `chromium`/`firefox`/`webkit` |
| `playwright.headless` | `false` | |
| `playwright.slow.mo` | `0` | her aksiyon arasında bekleme (ms) |
| `playwright.viewport.width` | `1440` | |
| `playwright.viewport.height` | `900` | |
| `playwright.timeout.ms` | `15000` | locator timeout |
| `playwright.video` | `false` | `target/playwright-videos/` |
| `playwright.trace` | `false` | `target/playwright-traces/*.zip` |

## Paralel güvenliği — nasıl çalışıyor?

1. **`PlaywrightFactory`** — `ThreadLocal<Playwright/Browser/Context/Page>`. Her thread bağımsız.
2. **`PwConfigSteps.LOCATORS`** — `ThreadLocal<Map<String, String>>`. Senaryo bazında doldurulur.
3. **`BrowserContext`** her scenario için yeni — cerez, localStorage, login state izole. Senaryolar birbirine karışmaz.
4. **`Browser`** thread başına paylaşımlı — pahalı kaynak, yeniden açmaya gerek yok.
5. **Cucumber JUnit Platform `parallel.enabled=true`** → senaryolar farklı thread'lerde paralel başlar.

## Trace + video

Hata teşhisi için `playwright.trace=true` ile her senaryo için `.zip` trace üretilir.
İnceleme:

```bash
mvn exec:java -Dexec.mainClass=com.microsoft.playwright.CLI \
    -Dexec.args="show-trace target/playwright-traces/1_Login.zip"
```

Tüm DOM snapshot'lar, network call'lar, console log'lar, screenshot'lar incelenebilir.

## Locator dosyaları

Selenium ile aynı JSON formatı (`{key, type, value}`):

```json
[
  { "key": "userNameInput", "type": "css", "value": "input[name='username']" },
  { "key": "loginButton",   "type": "xpath", "value": "//button[@id='login']" }
]
```

`PwLocatorReader` bu formati Playwright selectorlerine çevirir:
- `id` → `#value`
- `name` → `[name='value']`
- `css` → `value`
- `xpath` → `xpath=value`
- `linktext` → `text='value'`

## Step phrase'leri (Selenium ile birebir uyumlu)

Tüm phrase'ler `PwCommonSteps.java`'da. Selenium tarafı `stepdefs/CommonSteps.java`. Bir feature dosyası iki runner'la da çalışır:

```gherkin
Given I open "cortex.url" link
When  I write "user" into "userNameInput"
*     I enter encrypted password alias "cortexUser" into "passwordInput"
*     I click "loginButton"
*     I wait for page to load
Then  I see "dashboardHome"
And   I verify title contains "Cortex"
```

## Performans örneği

| Engine | Mod | 20 senaryo süresi (örnek) |
|---|---|---|
| Selenium | sequential | ~6 dk |
| Playwright | sequential | ~3 dk |
| Playwright | 4 thread | ~1 dk |
| Playwright | 8 thread | ~35 sn |
