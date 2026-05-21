# Paribu Test Otomasyon Framework

> ⚠️ **ROL NOTU (ADR-0006):** Bu dizin TestwrightAI ürün E2E testleri için
> **kullanılmaz**. BGTS (`apps/web`) için Playwright testleri
> [`../../e2e/`](../../e2e/) altındadır ve ana Playwright runner'ı ile koşar.
>
> Bu ağaç iki amaca hizmet eder:
> 1. **DSL katalog / AI test üretici referansı** — Agents v2 ve NL-Test
>    üreticileri buradaki step modüllerini "Gherkin → kod eşleşmesi nasıl
>    yazılır" örneği olarak kullanır (bkz. `packages/dsl/catalog/`).
> 2. **Paribu + DummyJSON demo senaryoları** — framework'ün Cucumber ile
>    web + API test yazımında nasıl kullanılabileceğini gösterir.
>
> Yeni BGTS özelliği için test eklemek istiyorsanız `../../e2e/` içine
> Playwright Test native spec yazın. Karar gerekçesi: **ADR-0006**.

Playwright, Cucumber (BDD) ve TypeScript kullanılarak geliştirilmiş, Page Object Model (POM) tasarım deseni ve SOLID prensiplerini takip eden kapsamlı bir test otomasyon framework'ü. Bu framework hem **Web Otomasyon** hem de **API Otomasyon** testlerini desteklemektedir.

## Teknoloji Stack

- **Dil**: TypeScript
- **Test Framework**: Playwright (Web ve API testleri için)
- **BDD Framework**: Cucumber
- **Tasarım Deseni**: Page Object Model (POM)
- **Raporlama**: Cucumber HTML Reporter
- **Loglama**: Sistematik test yürütme logları

## Proje Yapısı

```
Paribu/
├── config/                    # Yapılandırma dosyaları
│   ├── config.ts             # Tarayıcı ve ortam yapılandırmaları (birleştirilmiş)
│   └── constants.ts          # Framework sabitleri ve yapılandırma değerleri
├── features/                  # Cucumber feature dosyaları
│   ├── api_tests.feature    # API otomasyon testleri
│   └── web_tests.feature    # Web otomasyon testleri
├── pages/                     # Page Object Model sınıfları
│   ├── BasePage.ts          # Temel sayfa sınıfı (yeniden kullanılabilir metodlar)
│   ├── ParibuHomePage.ts    # Paribu ana sayfa page object
│   ├── MarketsPage.ts       # Markets sayfası page object
│   ├── CryptocurrencyDetailPage.ts # Kripto para detay sayfası
│   └── LoginPage.ts         # Giriş sayfası page object
├── steps/                     # Step definitions ve hooks
│   ├── api.steps.ts         # API test step definitions
│   ├── web.steps.ts         # Web test step definitions
│   ├── hooks.ts             # Before/After hooks + rapor oluşturma
│   └── playwright-world.ts  # Özel world constructor
├── test-data/                 # Statik test verileri (JSON)
│   ├── api-credentials.json # API kimlik bilgileri
│   ├── api-endpoints.json   # API endpoint yapılandırması
│   └── web-selectors.json  # Web element selector'ları
├── utils/                     # Yardımcı fonksiyonlar
│   ├── ApiClient.ts        # Genel HTTP client
│   ├── DummyJsonApi.ts     # DummyJSON API wrapper
│   ├── TestDataLoader.ts   # Test verisi yükleme yardımcısı
│   ├── Logger.ts           # Loglama yardımcısı
│   ├── CustomErrors.ts     # Özel hata sınıfları
│   └── generate-report.js  # HTML rapor oluşturucu
├── logs/                     # Test yürütme logları (gitignore)
├── reports/                   # Test raporları (oluşturulan, gitignore)
│   ├── cucumber_report.html # HTML test raporu
│   ├── cucumber-report.json # JSON test raporu
│   └── screenshots/         # Hata durumunda ekran görüntüleri
├── cucumber.js               # Cucumber yapılandırması
├── tsconfig.json             # TypeScript yapılandırması
├── package.json              # Bağımlılıklar ve script'ler
└── README.md                 # Bu dosya
```

## Kurulum

### Ön Gereksinimler

- Node.js (v16 veya üzeri)
- npm veya yarn

### Adım 1: Bağımlılıkları Yükle

```bash
npm install
```

Bu komut tüm gerekli bağımlılıkları yükler:
- Playwright
- Cucumber
- TypeScript
- Cucumber HTML Reporter
- Diğer dev bağımlılıklar

### Adım 2: Playwright Tarayıcılarını Yükle

```bash
npm run install:browsers
```

Bu komut Playwright için gerekli Chromium, Firefox ve WebKit tarayıcılarını yükler.

### Adım 3: Ortam Değişkenlerini Yapılandır

Kök dizinde bir `.env` dosyası oluşturun (varsa `.env.example` dosyasından kopyalayabilirsiniz):

```bash
# Ortam Yapılandırması
ENVIRONMENT=paribu
HEADLESS=false
LOG_LEVEL=INFO

# Paribu Ortamı
PARIBU_BASE_URL=https://paribu.com

# Diğer ortam URL'leri (gerekirse)
QA_BASE_URL=https://qa.example.com
STAGE_BASE_URL=https://stage.example.com
PROD_BASE_URL=https://prod.example.com
```

## Test Çalıştırma

### Kapsamlı Test Runner (Önerilen)

Framework, gelişmiş seçeneklerle **kapsamlı bir test runner** içerir:

```bash
npm run test:runner [seçenekler]
```

#### Test Runner Seçenekleri

```bash
# Belirli tag'lerle çalıştır
npm run test:runner -- --tags @api
npm run test:runner -- --tags @api,@login
npm run test:runner -- --tags @web

# Belirli tarayıcıda çalıştır
npm run test:runner -- --browser firefox
npm run test:runner -- --browser chromium
npm run test:runner -- --browser webkit

# Belirli ortamda çalıştır
npm run test:runner -- --env paribu
npm run test:runner -- --env qa
npm run test:runner -- --env stage
npm run test:runner -- --env prod

# Paralel çalıştır
npm run test:runner -- --parallel 4

# Seçenekleri birleştir
npm run test:runner -- --tags @api --browser firefox --env paribu --parallel 4

# Headed modda çalıştır (tarayıcıyı gör)
npm run test:runner -- --headed

# Detaylı çıktı
npm run test:runner -- --verbose

# Özel timeout
npm run test:runner -- --timeout 120000

# Rapor oluşturmayı atla
npm run test:runner -- --no-report

# Yardım göster
npm run test:runner -- --help
```

#### Gelişmiş Kullanım Örnekleri

```bash
# Paribu ortamında Firefox'ta 4 worker ile API testlerini çalıştır
npm run test:runner -- --tags @api --browser firefox --env paribu --parallel 4

# Headed modda web testlerini çalıştır (tarayıcıyı gör)
npm run test:runner -- --tags @web --headed

# Özel timeout ile tüm testleri çalıştır
npm run test:runner -- --timeout 120000

# Belirli senaryo tag'lerini çalıştır
npm run test:runner -- --tags "@api and @login"
npm run test:runner -- --tags "@web and @calculation"
```

### Hızlı Komutlar

#### Tüm Testleri Çalıştır
```bash
npm test
```

#### Kategoriye Göre Test Çalıştır
```bash
npm run test:api      # Tüm API testleri
npm run test:web      # Tüm Web testleri
```

#### Belirli Tarayıcıda Test Çalıştır
```bash
npm run test:chrome    # Chromium/Chrome
npm run test:firefox   # Firefox
npm run test:edge      # WebKit (Safari/Edge)
```

#### Belirli Ortamda Test Çalıştır
```bash
npm run test:qa        # QA ortamı
npm run test:stage     # Staging ortamı
npm run test:prod      # Production ortamı
npm run test:paribu    # Paribu ortamı
```

#### Test Çalıştır ve HTML Rapor Oluştur
```bash
npm run test:report
```

#### Paralel Test Çalıştır
```bash
npm run test:parallel  # 4 paralel worker
```

#### Sadece Rapor Oluştur
```bash
npm run report
```

## Test Türleri

### API Otomasyon Testleri

`features/api_tests.feature` dosyasında bulunan bu testler, REST API'lerini test etmek için Playwright'un `APIRequestContext`'ini kullanır.

**Senaryolar:**
1. **Login & Token Management** - Geçerli/geçersiz kimlik bilgileri ile giriş, token saklama
2. **Scenario Outline** - Farklı kullanıcılar ile login testleri
3. **Product List Assertion** - Kimlik doğrulamalı ürün listesi testleri
4. **Update & Delete Flow** - Sıralı güncelleme ve silme işlemleri testleri
5. **isDeleted Field Update** - Ürün isDeleted alanını güncelleme
6. **Categories Verification** - Tüm kategoriler için 200 OK kontrolü
7. **Performance/Timeout** - Login response time kontrolü (< 2000ms)

**API Base URL**: `https://dummyjson.com`

### Web Otomasyon Testleri

`features/web_tests.feature` dosyasında bulunan bu testler, web UI'ı test etmek için Playwright'un tarayıcı otomasyonunu kullanır.

**Senaryolar:**
1. **Filtreleme ve Hesaplama** - FAN filtresi, 12 saat zaman filtresi, güncel fiyat butonu, toplam fiyat hesaplaması
2. **Invalid Login** - Geçersiz giriş denemeleri için hata yönetimini test eder
3. **Sıralama ve Form Kontrolü** - Fiyata göre azalan sıralama, pozitif 24h değişimli coin seçimi, emir transfer kontrolü
   - **Önemli Not**: Quantity input, seçilen satıra kadar olan tüm emirlerin toplam miktarını gösterir (Case Study gereksinimi)

**Website**: `https://paribu.com`

**Not**: Selector'lar `test-data/web-selectors.json` dosyasında yönetilir ve kolayca güncellenebilir.

## Yapılandırma

### Ortamlar

Ortamları `config/config.ts` dosyasında yapılandırın. Mevcut ortamlar:
- `qa` - QA ortamı
- `stage` - Staging ortamı
- `prod` - Production ortamı
- `paribu` - Paribu production web sitesi

### Tarayıcılar

Desteklenen tarayıcılar (`config/config.ts` dosyasında yapılandırılmıştır):
- `chromium` - Chrome/Chromium
- `firefox` - Firefox
- `webkit` - Safari/Edge

**Tarayıcı Özellikleri:**
- **Incognito Modu**: Her test izole bir context'te çalışır (Playwright'un varsayılan davranışı)
- **Fullscreen**: Tarayıcı fullscreen modda çalışır (`viewport: null`)
- **Maximized**: Tarayıcı penceresi maksimize edilmiş olarak başlar

### World Parametreleri

Tarayıcı ve ortamı world parametreleri ile geçebilirsiniz:

```bash
cucumber-js --world-parameters '{"browser":"firefox","environment":"paribu"}'
```

## Raporlama ve Loglama

### HTML Rapor

Test çalıştırmasından sonra, HTML raporu otomatik olarak şu konumda oluşturulur:
```
reports/cucumber_report.html
```

Rapor şunları içerir:
- ✅ Test çalıştırma özeti
- 📊 Başarılı/başarısız durumlu senaryo sonuçları
- 📸 Ekran görüntüleri (hata durumunda yakalanan)
- 📋 Metadata (ortam, tarayıcı, platform, çalıştırma süresi)
- 🔍 Detaylı adım adım çalıştırma logları

### Test Yürütme Logları

Test yürütme logları sistematik olarak kaydedilir:
```
logs/test-execution-YYYY-MM-DD.log
```

Log seviyeleri:
- **DEBUG**: Detaylı debug bilgileri
- **INFO**: Genel bilgilendirme mesajları
- **WARN**: Uyarı mesajları
- **ERROR**: Hata mesajları

Log seviyesini `.env` dosyasında ayarlayın:
```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARN, ERROR
```

### Rapor Oluşturma

Raporlar otomatik olarak oluşturulur:
- **Test çalıştırmasından sonra**: `npm run test:report` kullanın
- **Hook ile**: `steps/hooks.ts` hook'u tüm senaryolar tamamlandıktan sonra raporları oluşturur
- **Manuel olarak**: Mevcut JSON raporundan yeniden oluşturmak için `npm run report` çalıştırın

## Test Yazma

### Feature Dosyaları

`features/` dizininde Gherkin syntax'ı kullanarak feature dosyaları oluşturun:

```gherkin
Feature: Örnek Feature
  Scenario: Örnek senaryo
    Given ana sayfaya gidiyorum
    When bir işlem gerçekleştiriyorum
    Then beklenen sonucu görmeliyim
```

### Page Objects

`BasePage`'i genişleterek page object'ler oluşturun:

```typescript
import { Page } from 'playwright';
import { BasePage } from './BasePage';

export class MyPage extends BasePage {
  private readonly myButton = this.page.locator('#my-button');

  async clickMyButton(): Promise<void> {
    await this.clickElement(this.myButton);
  }
}
```

### Step Definitions

`steps/` dizininde step definition'lar oluşturun:

```typescript
import { Given, When, Then } from '@cucumber/cucumber';
import { PlaywrightWorld } from './playwright-world';
import { MyPage } from '../pages/MyPage';

Given('ana sayfaya gidiyorum', async function (this: PlaywrightWorld) {
  const myPage = new MyPage(this.page, this.environment);
  await myPage.navigateTo('/');
});
```

## Mimari Özellikler

- ✅ **SOLID Prensipleri**: Clean Code standartlarına tam uyum
- ✅ **Test Verileri**: Statik JSON dosyalarında yönetilebilir test verileri (`test-data/`)
- ✅ **Çoklu Ortam**: QA, Staging, Prod, Paribu ortamları
- ✅ **Çoklu Tarayıcı**: Chrome, Firefox, Edge (WebKit) desteği
- ✅ **Random Browser Selection**: Opsiyonel rastgele tarayıcı seçimi
- ✅ **Dinamik Beklemeler**: Statik wait komutları yok, Playwright'un otomatik bekleme mekanizması
- ✅ **Page Load Assertions**: Sayfa yüklemesi explicit olarak doğrulanır
- ✅ **Background Keyword**: Tekrarlayan işlemler için Background kullanımı (cookie notice)
- ✅ **Incognito & Fullscreen**: Web testleri için tarayıcı yapılandırması
- ✅ **HTML Raporlama**: Detaylı test sonuç raporları
- ✅ **Sistematik Loglama**: Test yürütme logları
- ✅ **Case Study 2025 Uyumlu**: Tüm gereksinimler karşılanmıştır

## Case Study 2025 Uyumluluk

Bu framework, **QA Case Study 2025** gereksinimlerine tam uyumludur:

### ✅ Genel Gereksinimler
- TypeScript kullanımı
- Playwright + Cucumber entegrasyonu
- BDD metodolojisi (Gherkin keywords doğru kullanımı)
- Background keyword kullanımı
- Cucumber hooks implementasyonu
- Çoklu ortam desteği (QA, Stage, Prod, Paribu)
- Sistematik test execution logs
- Statik test verileri (JSON dosyaları)
- Clean Code + SOLID prensipleri
- HTML test raporu
- README ve .gitignore güncel

### ✅ API Otomasyon
- DummyJSON API endpoint'leri
- Senaryo sonunda assertions
- Parallel execution desteği (opsiyonel)

### ✅ Web Otomasyon
- Page Object Model (POM) tasarım deseni
- Sayfa yükleme doğrulaması (explicit assertions)
- Static wait yok (Playwright otomatik bekleme)
- Maintainable selectors (fallback selector'lar)
- Çoklu tarayıcı desteği (Chrome, Firefox, Edge)
- Incognito mode + Fullscreen
- Random browser selection (opsiyonel)

### 📝 Özel Notlar
- **Quantity Input**: Web Case Study 3'te, quantity input'un seçilen satıra kadar olan tüm emirlerin toplam miktarını gösterdiği doğrulanır
- **Background**: Cookie notice kapatma işlemi Background'da tanımlanmıştır
- **Page Load**: Her navigasyon sonrası sayfa başlığı ve URL explicit olarak doğrulanır

## En İyi Uygulamalar

1. **Page Object Model**: Sayfa özel mantığını page sınıflarında tutun
2. **Yeniden Kullanılabilirlik**: Ortak işlemler için base sınıflar ve yardımcılar kullanın
3. **Temiz Kod**: SOLID prensiplerini takip edin ve okunabilir kod yazın
4. **Ortam Yönetimi**: Farklı test ortamları için ortam yapılandırması kullanın
5. **Hata Yönetimi**: Uygun hata yönetimi ve loglama uygulayın
6. **JSDoc Yorumları**: Tüm public metodlar için JSDoc yorumları ekleyin
7. **Background Kullanımı**: Tekrarlayan işlemler için Background keyword'ünü kullanın
6. **Ekran Görüntüleri**: Hata ayıklama için otomatik ekran görüntüleri
7. **Statik Beklemeler Yok**: `sleep()` veya `waitForTimeout()` yerine Playwright'un otomatik bekleme mekanizmalarını kullanın
8. **Assertion'lar**: Assertion'ları her zaman senaryoların sonuna yerleştirin
9. **Test Verileri**: Test verilerini statik dosyalarda tutun ve kolayca yönetin (`TestDataLoader` kullanın)
10. **Loglama**: Test yürütme sırasında sistematik loglama yapın (`Logger` kullanın)

## Sorun Giderme

### Tarayıcılar yüklenmemiş
```bash
npm run install:browsers
```

### TypeScript derleme hataları
- `tsconfig.json` yapılandırmasını kontrol edin
- Tüm bağımlılıkların yüklü olduğundan emin olun: `npm install`
- Node.js sürümünü doğrulayın (v16+)

### Ortam bulunamadı
- `config/environments.ts` dosyasındaki ortam adını doğrulayın
- `.env` dosyası yapılandırmasını kontrol edin
- Ortam değişkeninin doğru ayarlandığından emin olun

### Selector hataları ile testler başarısız oluyor
- Page Object'lerdeki placeholder selector'ları güncelleyin
- Doğru selector'ları bulmak için tarayıcı DevTools'u kullanın
- Selector'ların benzersiz ve kararlı olduğunu doğrulayın

### Rapor oluşturulmuyor
- `reports/cucumber-report.json` dosyasının var olduğundan emin olun (test çalıştırmasından sonra oluşturulur)
- `reports/` dizinindeki dosya izinlerini kontrol edin
- `npm run report` komutunu manuel olarak çalıştırın

### Paralel çalıştırma sorunları
- Testler başarısız olursa paralel worker sayısını azaltın
- Testlerin bağımsız olduğundan emin olun (paylaşılan durum yok)
- Sistem kaynaklarını kontrol edin (CPU, bellek)

## Git Yapılandırması

`.gitignore` dosyası şunları hariç tutacak şekilde yapılandırılmıştır:
- `node_modules/` - Bağımlılıklar
- `reports/` - Test raporları
- `logs/` - Test yürütme logları
- `.env` - Ortam değişkenleri
- `*.log` - Log dosyaları
- `target/` - Maven build çıktıları (varsa)
- Build artifact'ları ve IDE dosyaları

## Lisans

ISC
