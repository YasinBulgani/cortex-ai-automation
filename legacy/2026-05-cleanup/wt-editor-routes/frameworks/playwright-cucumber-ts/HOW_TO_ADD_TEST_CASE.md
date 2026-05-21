# Yeni Test Case Ekleme Rehberi

Bu doküman, projeye yeni bir test case (test senaryosu) nasıl ekleneceğini adım adım açıklar.

## 📋 Genel Süreç

1. **Feature dosyasına senaryo ekle** (Gherkin syntax)
2. **Step definitions ekle** (TypeScript)
3. **Gerekirse Page Object ekle/düzenle**
4. **Gerekirse test verilerini ekle/düzenle**

---

## 🎯 Senaryo 1: API Test Case Ekleme

### Adım 1: Feature Dosyasına Senaryo Ekle

`features/api_tests.feature` dosyasını açın ve yeni senaryo ekleyin:

```gherkin
@api @products @search
Scenario: Search products by title
  Given I have a valid access token
  When I search for products with query "laptop"
  Then the response status code should be 200
  And the search results should contain "laptop" in product titles
```

**Tag'ler:**
- `@api` - API testleri için zorunlu
- `@products` - Ürünle ilgili testler
- `@search` - Arama fonksiyonelliği (opsiyonel, kendi tag'iniz)

### Adım 2: Step Definitions Ekle

`steps/api.steps.ts` dosyasını açın ve yeni step'leri ekleyin:

```typescript
/**
 * Step: I search for products with query {string}
 * Ürün arama isteği gönderir
 */
When('I search for products with query {string}', async function (this: PlaywrightWorld, query: string) {
  apiClient = new DummyJsonApi(this.request);
  const response = await apiClient.searchProducts(query);
  // Response'u sakla (global değişken veya world'e ekle)
  this.attach(`Arama sorgusu: ${query}`, 'text/plain');
});

/**
 * Step: the search results should contain {string} in product titles
 * Arama sonuçlarında ürün başlıklarında aranan kelimeyi kontrol eder
 */
Then('the search results should contain {string} in product titles', async function (this: PlaywrightWorld, expectedText: string) {
  const products = this.searchResults?.products || [];
  expect(products.length).toBeGreaterThan(0);
  
  for (const product of products) {
    expect(product.title.toLowerCase()).toContain(expectedText.toLowerCase());
  }
});
```

### Adım 3: API Client'a Yeni Metod Ekle (Gerekirse)

`utils/DummyJsonApi.ts` dosyasını açın:

```typescript
/**
 * Ürün arama yapar
 */
async searchProducts(query: string): Promise<ProductsResponse> {
  const response = await this.client.get(`/products/search?q=${query}`);
  return await response.json();
}
```

---

## 🌐 Senaryo 2: Web Test Case Ekleme

### Adım 1: Feature Dosyasına Senaryo Ekle

`features/web_tests.feature` dosyasını açın:

```gherkin
@web @navigation
Scenario: Navigate to About Page
  When I navigate to the About page
  Then the page title should contain "Hakkımızda"
  And the URL should contain "hakkimizda"
```

### Adım 2: Selector'ları Test Data'ya Ekle

`test-data/web-selectors.json` dosyasını açın ve selector'ları ekleyin:

```json
{
  "paribu": {
    "homepage": {
      "aboutLink": "a:has-text('Hakkımızda'), a[href*='hakkimizda'], a[href*='about']"
    }
  }
}
```

### Adım 3: Page Object'e Metod Ekle

`pages/ParibuHomePage.ts` dosyasını açın:

```typescript
private readonly aboutLink: Locator;

constructor(page: Page, environment: string = 'paribu') {
  super(page, environment);
  // ... mevcut kodlar
  this.aboutLink = page.locator('a:has-text("Hakkımızda"), a[href*="hakkimizda"]').first();
}

/**
 * Hakkımızda sayfasına git
 */
async navigateToAbout(): Promise<void> {
  await this.clickElement(this.aboutLink);
  await this.page.waitForLoadState('networkidle');
}
```

### Adım 4: Step Definitions Ekle

`steps/web.steps.ts` dosyasını açın:

```typescript
/**
 * Step: I navigate to the About page
 */
When('I navigate to the About page', async function (this: PlaywrightWorld) {
  await homePage.navigateToAbout();
});

/**
 * Step: the page title should contain {string}
 */
Then('the page title should contain {string}', async function (this: PlaywrightWorld, expectedText: string) {
  const title = await this.page.title();
  expect(title).toContain(expectedText);
});

/**
 * Step: the URL should contain {string}
 */
Then('the URL should contain {string}', async function (this: PlaywrightWorld, expectedPath: string) {
  const url = this.page.url();
  expect(url).toContain(expectedPath);
});
```

---

## 📝 Gherkin Syntax Örnekleri

### Temel Senaryo

```gherkin
@web @example
Scenario: Basit senaryo örneği
  Given bir önkoşul
  When bir aksiyon gerçekleştiriyorum
  Then beklenen sonucu görmeliyim
```

### Senaryo Outline (Parametreli Test)

```gherkin
@api @scenario-outline
Scenario Outline: Farklı ürünlerle test
  Given I have a valid access token
  When I request product with ID <productId>
  Then the response status code should be <statusCode>

  Examples:
    | productId | statusCode |
    | 1         | 200        |
    | 999999    | 404        |
```

### Background Kullanımı

Background, feature içindeki tüm senaryolar için önkoşul oluşturur:

```gherkin
Feature: My Feature
  Background:
    Given I navigate to Paribu homepage
    And I close the cookie notice if present

  Scenario: Test 1
    # Background otomatik çalışır
    
  Scenario: Test 2
    # Background otomatik çalışır
```

---

## 🔧 Step Definition Parametre Tipleri

### String Parametresi

```typescript
Given('kullanıcı adı {string} ile giriş yapıyor', async function (this: PlaywrightWorld, username: string) {
  // username değişkeni string olarak gelir
});
```

**Gherkin:**
```gherkin
Given kullanıcı adı "testuser" ile giriş yapıyor
```

### Integer Parametresi

```typescript
When('limit {int} ile ürün listesi alıyorum', async function (this: PlaywrightWorld, limit: number) {
  // limit değişkeni number olarak gelir
});
```

**Gherkin:**
```gherkin
When limit 10 ile ürün listesi alıyorum
```

### Data Table

```typescript
Given('kullanıcı bilgileri:', async function (this: PlaywrightWorld, dataTable: DataTable) {
  const data = dataTable.rowsHash();
  const username = data['username'];
  const password = data['password'];
});
```

**Gherkin:**
```gherkin
Given kullanıcı bilgileri:
  | username | password    |
  | testuser | testpass123 |
```

---

## 📦 Örnek: Tam Bir Test Case Ekleme

### Senaryo: Kullanıcı arama yapıp sonuçları filtreler

### 1. Feature Dosyası (`features/web_tests.feature`)

```gherkin
@web @search @filter
Scenario: Search and filter cryptocurrencies
  When I navigate to the Markets page
  And I search for "Bitcoin"
  Then search results should be displayed
  When I apply price filter "min 50000" and "max 100000"
  Then filtered results should match price range
```

### 2. Page Object (`pages/MarketsPage.ts`)

```typescript
private readonly searchInput: Locator;
private readonly minPriceInput: Locator;
private readonly maxPriceInput: Locator;

async searchCryptocurrency(query: string): Promise<void> {
  await this.fillInput(this.searchInput, query);
  await this.page.waitForLoadState('networkidle');
}

async applyPriceFilter(min: number, max: number): Promise<void> {
  await this.fillInput(this.minPriceInput, min.toString());
  await this.fillInput(this.maxPriceInput, max.toString());
  await this.page.keyboard.press('Enter');
}
```

### 3. Step Definitions (`steps/web.steps.ts`)

```typescript
When('I search for {string}', async function (this: PlaywrightWorld, query: string) {
  await marketsPage.searchCryptocurrency(query);
});

Then('search results should be displayed', async function (this: PlaywrightWorld) {
  // Assertion kodları
});

When('I apply price filter {string} and {string}', async function (this: PlaywrightWorld, min: string, max: string) {
  const minPrice = parseInt(min.replace('min ', ''));
  const maxPrice = parseInt(max.replace('max ', ''));
  await marketsPage.applyPriceFilter(minPrice, maxPrice);
});
```

---

## ✅ Checklist

Yeni test case eklerken şunları kontrol edin:

- [ ] Feature dosyasında senaryo eklendi
- [ ] Doğru tag'ler kullanıldı (`@api` veya `@web` zorunlu)
- [ ] Step definitions eklendi/düzenlendi
- [ ] Page Object metodları eklendi (web testleri için)
- [ ] Selector'lar `test-data/web-selectors.json`'a eklendi (web testleri için)
- [ ] API client metodları eklendi (API testleri için)
- [ ] Test verileri eklendi (gerekirse)
- [ ] Test çalıştırıldı ve doğrulandı

---

## 🚀 Test Çalıştırma

### Tek bir senaryoyu çalıştır:

```bash
npm run test:runner -- --tags "@search"
```

### Belirli bir test case'i çalıştır:

```bash
npm run test:runner -- --tags "@web and @search"
```

### Tüm testleri çalıştır:

```bash
npm test
```

---

## 💡 İpuçları

1. **Mevcut step'leri tekrar kullanın**: Aynı step'i farklı senaryolarda kullanabilirsiniz
2. **Tag'leri mantıklı kullanın**: Testleri kategorize etmek için tag'leri kullanın
3. **Page Object Model'e uyun**: Web testlerinde sayfa mantığını Page Object'lerde tutun
4. **Assertion'ları senaryo sonuna koyun**: Test adımlarının sonunda doğrulamalar yapın
5. **JSDoc yorumları ekleyin**: Her step definition için açıklayıcı yorum ekleyin
6. **Logger kullanın**: Önemli adımlarda loglama yapın

---

## 📚 Referans Dosyalar

- Feature dosyaları: `features/`
- Step definitions: `steps/`
- Page Objects: `pages/`
- Test verileri: `test-data/`
- Yardımcı sınıflar: `utils/`
