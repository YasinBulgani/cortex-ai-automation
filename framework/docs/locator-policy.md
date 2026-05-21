# Locator Policy

> **XPath başlangıç değil, son çare.** Bu dosya hangi locator tipini ne zaman kullanacağını anlatır.

## Öncelik zinciri (her zaman bu sırayla dene)

```
┌──────────────────────────────────────────────────────────────────┐
│  1. data-testid / data-cy / data-test                             │  ALTIN
│     Geliştirici ekip test için özel attribute koyduysa            │
│     Örnek: <button data-testid="login-submit">                    │
│     JSON: { "type": "css", "value": "[data-testid='login-submit']"│
└──────────────────────────────────────────────────────────────────┘
                              ↓ yoksa
┌──────────────────────────────────────────────────────────────────┐
│  2. id (stable, auto-generated değil)                             │  GÜMÜŞ
│     `:r0:`, `mui-12`, `ant-1`, UUID değil                         │
│     JSON: { "type": "id", "value": "btnLogin" }                   │
└──────────────────────────────────────────────────────────────────┘
                              ↓ yoksa
┌──────────────────────────────────────────────────────────────────┐
│  3. name attribute (form input için)                              │
│     JSON: { "type": "name", "value": "username" }                 │
└──────────────────────────────────────────────────────────────────┘
                              ↓ yoksa
┌──────────────────────────────────────────────────────────────────┐
│  4. aria-label / role (erişilebilirlik, stabil)                   │
│     JSON: { "type": "css",                                        │
│             "value": "button[aria-label='Giriş yap']" }           │
└──────────────────────────────────────────────────────────────────┘
                              ↓ yoksa
┌──────────────────────────────────────────────────────────────────┐
│  5. CSS selector (kısa, attribute-based)                          │
│     JSON: { "type": "css",                                        │
│             "value": "form.login button[type='submit']" }         │
└──────────────────────────────────────────────────────────────────┘
                              ↓ yoksa
┌──────────────────────────────────────────────────────────────────┐
│  6. text= / linkText (görünür metni stabilse)                     │
│     JSON: { "type": "linktext", "value": "Şifremi unuttum" }      │
└──────────────────────────────────────────────────────────────────┘
                              ↓ son çare
┌──────────────────────────────────────────────────────────────────┐
│  7. XPath — sadece üç durumda:                                   │  KIRMIZI
│     a) Ancestor/sibling traversal gerekiyor                       │
│        //label[text()='Email']/following::input[1]                │
│     b) Text-based contains() gerekiyor                            │
│        //button[contains(.,'Giriş')]                              │
│     c) Diğer hiçbiri çalışmadığı zaman                            │
└──────────────────────────────────────────────────────────────────┘
```

## YASAK pattern'ler

| Pattern | Neden kötü? | Alternatif |
|---|---|---|
| Absolute XPath `/html/body/...` | DOM her değiştiğinde kırılır | Attribute-based relative |
| Index `[3]`, `[last()]` | Eleman sırası değişince | `contains(text(),'X')` |
| Dinamik class: `.tooltipstered`, `.pulseWarning`, `.active`, `.hover` | JS state'ine bağlı, sayfa yenilenince yok | Static parent + attribute |
| Auto-generated id: `:r0:`, `mui-12`, `ant-1`, UUID | Her render farklı | Parent attribute + child role |
| 5+ seviye CSS path: `div > div > div > section > div > a` | DOM yapısına sıkı bağ | `data-testid` veya text-based |
| 150+ karakter selector | Okunmaz, refactor riski yüksek | Kısalt veya data-testid ekle |

## Multi-locator fallback

**Framework çoklu locator destekler.** Aynı key birden fazla entry ile tanımlanabilir, framework birinci başarısız olursa ikinciyi dener:

```json
[
  { "key": "loginButton", "type": "css",   "value": "[data-testid='login']" },
  { "key": "loginButton", "type": "id",    "value": "btnLogin" },
  { "key": "loginButton", "type": "css",   "value": "form.login button[type='submit']" },
  { "key": "loginButton", "type": "xpath", "value": "//button[normalize-space()='Giriş']" }
]
```

Hem Selenium (`MultiBy`) hem Playwright (`Locator.or()`) bunu destekler.

**Ne zaman kullan?**
- Site sürüm değişikliklerinde DOM değişikliği yapıyor (data-testid eklenmemiş ama eklenebilir)
- Geçici "şu an çalışan + ideal" iki seçenek tutmak istiyorsun
- A/B test variantları

**Ne zaman kullanma?**
- Bir locator zaten stabil çalışıyor → tek satır yeterli
- Fallback olarak 5+ XPath dizilmesi → kök sorunu çöz (data-testid iste)

## Naming convention (locator key)

- **camelCase**, Türkçe karakter yok
- Eleman tipini suffix yap: `userNameInput`, `loginButton`, `forgotPasswordLink`, `errorMessage`
- Yer/bağlam belirten prefix: `headerSearchInput`, `modalCloseButton`
- Çakışma: `_2`, `_3` (recorder otomatik)

İyi:
```json
{ "key": "loginButton",          ... }
{ "key": "userNameInput",        ... }
{ "key": "headerSearchInput",    ... }
{ "key": "forgotPasswordLink",   ... }
{ "key": "kvkkAcceptCheckbox",   ... }
```

Kötü:
```json
{ "key": "btn1",                 ... }    // anlamsız
{ "key": "Giriş Yap Butonu",     ... }    // Türkçe + boşluk
{ "key": "click_here_button_v2", ... }    // snake_case + versiyon
```

## Locator dosya organizasyonu

```
src/test/resources/
├── projects/
│   ├── cortex/locators/
│   │   ├── login.json
│   │   ├── dashboard.json
│   │   └── settings.json
│   ├── hcm/locators/
│   │   ├── login.json
│   │   ├── ilan.json
│   │   └── fazla-eksik-calisma.json
│   ├── linkedin/locators/
│   └── trendyol/locators/
├── shared/locators/         # birden fazla projede ortak (ör. cookie-banner)
└── recordings/locators/     # recorder çıktıları
```

**Kural**: locator dosya adı = feature dosya adı. `cortex/features/login.feature` → `cortex/locators/login.json`.

## Linter

Her commit öncesi çalıştır:

```bash
mvn exec:java -Dexec.mainClass=utils.LocatorLinter
```

veya IntelliJ Run > **Locator Linter** ▶

Çıktı örneği:
```
==============================================================================
 LocatorLinter raporu: 0 ERROR / 12 WARN / 3 INFO
==============================================================================

 src/main/resources/locators/login.json
   [!] key='asgariIndirim'
       Dinamik class (tooltipster/pulse/active/hover) -> JS state'ine bagli
       -> div.sa-icon.sa-warning.pulseWarning

   [i] key='loginButton'
       Bu XPath '#id' CSS ile yazilabilir
       -> //button[@id='btnLogin']
```

CI'da exit code 1 (ERROR) ise build kırılır, WARN'ları sadece raporlar.

## Recorder ile uyum

Recorder ([RecorderMain](../src/main/java/recorder/RecorderMain.java)) bu policy'yi otomatik uygular — `LocatorBuilder.java` aynı sıralamayı kullanır:

1. `data-testid` / `data-cy` / `data-qa`
2. Sabit `id`
3. `name`
4. `aria-label`
5. Görünür metin (button/a için XPath `normalize-space()`)
6. `placeholder` (input için)
7. CSS path
8. XPath fallback

Yani recorder ile üretilen locator'lar zaten policy uyumludur.

## Migrasyon (mevcut XPath'leri CSS'e çevirme)

Hızlı çevriler:

| XPath | CSS karşılığı |
|---|---|
| `//*[@id='x']` | `#x` |
| `//div[@class='y']` | `div.y` |
| `//input[@name='z']` | `input[name='z']` |
| `//a[@href='/login']` | `a[href='/login']` |
| `//button[contains(@class,'submit')]` | `button[class*='submit']` |
| `//input[@id='x' and @name='y']` | `input#x[name='y']` |

Karmaşık olanlar (text-based, sibling) XPath olarak kalsın, ama `normalize-space()` ile:

| Eski (kırılgan) | Yeni (sağlam) |
|---|---|
| `//button[text()='Giriş ']` | `//button[normalize-space()='Giriş']` |
| `(//div[@class='item'])[3]` | `//div[contains(@class,'item') and @data-id='3']` |
