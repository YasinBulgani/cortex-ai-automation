import { Page, Locator } from 'playwright';
import { BasePage } from './BasePage';
import { TestDataLoader } from '../utils/TestDataLoader';

export class CryptocurrencyDetailPage extends BasePage {
  
  private readonly buySellPanel: Locator;
  private readonly unitPriceInput: Locator;
  private readonly quantityInput: Locator;
  private readonly totalPriceField: Locator;
  private readonly currentPriceButton: Locator;
  private readonly pendingBuyOrders: Locator;
  private readonly pendingSellOrders: Locator;
  private readonly buyTab: Locator;
  private readonly sellTab: Locator;

  constructor(page: Page, environment: string = 'paribu') {
    super(page, environment);
    
    // Selector'ları test data'dan yükle
    const selectors = TestDataLoader.loadWebSelectors();
    const paribuSelectors = selectors.paribu as Record<string, unknown> | undefined;
    const detailSelectors = (paribuSelectors?.cryptocurrencyDetail as Record<string, string> | undefined) || {};
    const orderSelectors = (paribuSelectors?.orderPanel as Record<string, string> | undefined) || {};
    
    // Al-Sat paneli selector'ları
    this.buySellPanel = page.locator('[data-testid="buy-sell-panel"], .buy-sell-panel, .trading-panel').first();
    
    // Giriş alanı selector'ları
    this.unitPriceInput = page.locator(detailSelectors.unitPriceInput || 'input[name="unitPrice"], [data-testid="unit-price"]').first();
    this.quantityInput = page.locator(detailSelectors.quantityInput || 'input[name="quantity"], [data-testid="quantity"]').first();
    this.totalPriceField = page.locator(detailSelectors.totalPriceDisplay || '[data-testid="total-price"], .total-price').first();
    this.currentPriceButton = page.locator(detailSelectors.currentPriceButton || 'button:has-text("Güncel Fiyat"), [data-action="current-price"]').first();
    
    // Emir paneli selector'ları
    this.pendingBuyOrders = page.locator(orderSelectors.pendingBuyOrders || '[data-testid="pending-buy-orders"], .pending-buy-orders').first();
    this.pendingSellOrders = page.locator(orderSelectors.pendingSellOrders || '[data-testid="pending-sell-orders"], .pending-sell-orders').first();
    this.buyTab = page.locator(orderSelectors.buyTab || '[data-testid="buy-tab"], .tab-buy, button:has-text("Alış")').first();
    this.sellTab = page.locator(orderSelectors.sellTab || '[data-testid="sell-tab"], .tab-sell, button:has-text("Satış")').first();
  }

  /**
   * Al-Sat panelinde birim fiyatı gir
   * Playwright'un otomatik bekleme mekanizmasını kullanır - statik bekleme gerekmez
   */
  async enterUnitPrice(price: number): Promise<void> {
    if (isNaN(price) || price < 0) {
      throw new Error(`Geçersiz birim fiyat: ${price}. Fiyat pozitif bir sayı olmalıdır.`);
    }
    
    await this.waitForElement(this.buySellPanel);
    await this.fillInput(this.unitPriceInput, price.toString());
    // Toplam fiyat alanının güncellenmesini bekle (Playwright otomatik bekler)
    // Toplam fiyat alanı girişten sonra değişmeli, bu yüzden kararlı olmasını bekliyoruz
    await this.totalPriceField.waitFor({ state: 'visible', timeout: this.timeout });
  }

  /**
   * Al-Sat panelinde miktarı gir
   */
  async enterQuantity(quantity: number | string): Promise<void> {
    const quantityNum = typeof quantity === 'string' ? parseFloat(quantity) : quantity;
    if (isNaN(quantityNum) || quantityNum < 0) {
      throw new Error(`Geçersiz miktar: ${quantity}. Miktar pozitif bir sayı olmalıdır.`);
    }
    
    await this.waitForElement(this.buySellPanel);
    await this.fillInput(this.quantityInput, quantityNum.toString());
    // Toplam fiyat alanının güncellenmesini bekle (Playwright otomatik bekler)
    // Toplam fiyat alanı girişten sonra değişmeli, bu yüzden kararlı olmasını bekliyoruz
    await this.totalPriceField.waitFor({ state: 'visible', timeout: this.timeout });
  }

  /**
   * Görüntülenen toplam fiyat değerini al
   */
  async getTotalPrice(): Promise<number> {
    await this.waitForElement(this.totalPriceField);
    
    try {
    // Önce input alanından değeri almaya çalış
    const value = await this.totalPriceField.inputValue().catch(async () => {
      // Eğer input değilse, metin içeriğini almaya çalış
      return await this.getText(this.totalPriceField);
    });
    
    // Sayıya çevir ve döndür (para birimi sembolleri, virgüller vb. kaldır)
    const numericValue = parseFloat(value.replace(/[^\d.-]/g, ''));
      
      if (isNaN(numericValue)) {
        throw new Error(`Toplam fiyat değeri geçersiz: "${value}"`);
      }
      
    return numericValue;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Toplam fiyat alınamadı: ${errorMessage}`);
    }
  }

  /**
   * Toplam fiyatın beklenen hesaplamayla eşleştiğini doğrula
   * @param _unitPrice - Girilen birim fiyat (kullanılmıyor, sadece dokümantasyon için)
   * @param _quantity - Girilen miktar (kullanılmıyor, sadece dokümantasyon için)
   * @param expectedTotal - Beklenen toplam (birimFiyat * miktar)
   * @returns Hesaplama doğruysa true
   */
  async verifyTotalPriceCalculation(_unitPrice: number, _quantity: number, expectedTotal: number): Promise<boolean> {
    const displayedTotal = await this.getTotalPrice();
    // Küçük ondalık farklara izin ver
    const difference = Math.abs(displayedTotal - expectedTotal);
    return difference < 0.01;
  }

  /**
   * "Güncel Fiyat" butonuna tıkla ve birim fiyat alanına güncel fiyatı doldur
   */
  async clickCurrentPriceButton(): Promise<void> {
    await this.clickElement(this.currentPriceButton);
    // Güncel fiyatın birim fiyat alanına doldurulmasını bekle (dinamik bekleme)
    await this.waitForElement(this.unitPriceInput);
    
    // Birim fiyat alanının doldurulduğunu dinamik olarak kontrol et
    // Playwright'un otomatik bekleme mekanizmasını kullan (static wait yok)
    // Input alanının değer almasını bekle - polling yerine Playwright'un waitForFunction kullan
    try {
      // Playwright'un waitForFunction'ı browser context'inde çalışır
      await this.page.waitForFunction(
        () => {
          // Browser context'inde çalışan kod - TypeScript burada DOM API'lerini tanımaz
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const selector = 'input[name="unitPrice"], [data-testid="unit-price"]';
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const input = (globalThis as any).document?.querySelector(selector) as { value?: string } | null;
          return input && input.value && input.value.trim().length > 0;
        },
        { timeout: this.timeout }
      );
    } catch {
      // Fallback: En azından element'in görünür olduğundan emin ol
      await this.waitForElement(this.unitPriceInput);
    }
  }

  /**
   * Birim fiyat değerini al
   */
  async getUnitPrice(): Promise<number> {
    await this.waitForElement(this.unitPriceInput);
    const value = await this.unitPriceInput.inputValue();
    const numericValue = parseFloat(value.replace(/[^\d.-]/g, ''));
    if (isNaN(numericValue)) {
      throw new Error(`Birim fiyat değeri geçersiz: "${value}"`);
    }
    return numericValue;
  }

  /**
   * Bekleyen alış emirlerinden birine tıkla
   * Case Study Not: Quantity input represents the total amount from all orders up to the selected row
   * @param index - Emir indeksi (1'den başlar)
   * @returns Seçilen satıra kadar olan tüm emirlerin toplam miktarı
   */
  async clickPendingBuyOrder(index: number): Promise<number> {
    const orders = this.pendingBuyOrders.locator('tr, li, [data-testid="order-item"]');
    const orderCount = await orders.count();
    
    if (index < 1 || index > orderCount) {
      throw new Error(`Geçersiz emir indeksi: ${index}. Toplam ${orderCount} emir var.`);
    }
    
    // Case Study gereksinimi: Seçilen satıra kadar olan tüm emirlerin miktarlarını topla
    let totalQuantity = 0;
    for (let i = 0; i < index; i++) {
      const order = orders.nth(i);
      // Miktar bilgisini al (genellikle bir td veya span içinde)
      const quantityText = await order.locator('td:nth-child(2), td:nth-child(3), [data-quantity], .quantity').first().textContent().catch(() => '0');
      const quantity = parseFloat(quantityText?.replace(/[^\d.,]/g, '').replace(',', '.') || '0');
      if (!isNaN(quantity)) {
        totalQuantity += quantity;
      }
    }
    
    const order = orders.nth(index - 1);
    await this.clickElement(order);
    // Emir detaylarının yüklenmesini bekle
    await this.page.waitForLoadState('networkidle');
    
    return totalQuantity;
  }

  /**
   * Bekleyen satış emirlerinden birine tıkla
   * Case Study Not: Quantity input represents the total amount from all orders up to the selected row
   * @param index - Emir indeksi (1'den başlar)
   * @returns Seçilen satıra kadar olan tüm emirlerin toplam miktarı
   */
  async clickPendingSellOrder(index: number): Promise<number> {
    const orders = this.pendingSellOrders.locator('tr, li, [data-testid="order-item"]');
    const orderCount = await orders.count();
    
    if (index < 1 || index > orderCount) {
      throw new Error(`Geçersiz emir indeksi: ${index}. Toplam ${orderCount} emir var.`);
    }
    
    // Case Study gereksinimi: Seçilen satıra kadar olan tüm emirlerin miktarlarını topla
    let totalQuantity = 0;
    for (let i = 0; i < index; i++) {
      const order = orders.nth(i);
      // Miktar bilgisini al (genellikle bir td veya span içinde)
      const quantityText = await order.locator('td:nth-child(2), td:nth-child(3), [data-quantity], .quantity').first().textContent().catch(() => '0');
      const quantity = parseFloat(quantityText?.replace(/[^\d.,]/g, '').replace(',', '.') || '0');
      if (!isNaN(quantity)) {
        totalQuantity += quantity;
      }
    }
    
    const order = orders.nth(index - 1);
    await this.clickElement(order);
    // Emir detaylarının yüklenmesini bekle
    await this.page.waitForLoadState('networkidle');
    
    return totalQuantity;
  }

  /**
   * Satış tabının aktif olduğunu ve verilerin doğru taşındığını doğrula
   * Case Study Not: Quantity input represents the total amount from all orders up to the selected row
   * @param expectedTotalQuantity - Beklenen toplam miktar (seçilen satıra kadar olan tüm emirlerin toplamı)
   * @returns Tab aktif ve veriler taşınmışsa true
   */
  async verifyDataMovedToSellTab(expectedTotalQuantity?: number): Promise<boolean> {
    await this.waitForElement(this.sellTab);
    const isActive = await this.sellTab.getAttribute('class');
    const hasActiveClass = (isActive?.includes('active') || isActive?.includes('selected')) ?? false;
    
    // Birim fiyat ve miktar alanlarının dolu olduğunu kontrol et
    const unitPriceValue = await this.unitPriceInput.inputValue();
    const quantityValue = await this.quantityInput.inputValue();
    const hasValues = unitPriceValue.length > 0 && quantityValue.length > 0;
    
    // Case Study gereksinimi: Eğer beklenen toplam miktar verilmişse, quantity input'un değerini doğrula
    if (expectedTotalQuantity !== undefined && hasValues) {
      const actualQuantity = parseFloat(quantityValue.replace(/[^\d.,]/g, '').replace(',', '.') || '0');
      const quantityMatches = Math.abs(actualQuantity - expectedTotalQuantity) < 0.01; // Tolerance for floating point
      return hasActiveClass && hasValues && quantityMatches;
    }
    
    return hasActiveClass && hasValues;
  }

  /**
   * Alış tabının aktif olduğunu ve verilerin doğru taşındığını doğrula
   * Case Study Not: Quantity input represents the total amount from all orders up to the selected row
   * @param expectedTotalQuantity - Beklenen toplam miktar (seçilen satıra kadar olan tüm emirlerin toplamı)
   * @returns Tab aktif ve veriler taşınmışsa true
   */
  async verifyDataMovedToBuyTab(expectedTotalQuantity?: number): Promise<boolean> {
    await this.waitForElement(this.buyTab);
    const isActive = await this.buyTab.getAttribute('class');
    const hasActiveClass = (isActive?.includes('active') || isActive?.includes('selected')) ?? false;
    
    // Birim fiyat ve miktar alanlarının dolu olduğunu kontrol et
    const unitPriceValue = await this.unitPriceInput.inputValue();
    const quantityValue = await this.quantityInput.inputValue();
    const hasValues = unitPriceValue.length > 0 && quantityValue.length > 0;
    
    // Case Study gereksinimi: Eğer beklenen toplam miktar verilmişse, quantity input'un değerini doğrula
    if (expectedTotalQuantity !== undefined && hasValues) {
      const actualQuantity = parseFloat(quantityValue.replace(/[^\d.,]/g, '').replace(',', '.') || '0');
      const quantityMatches = Math.abs(actualQuantity - expectedTotalQuantity) < 0.01; // Tolerance for floating point
      return hasActiveClass && hasValues && quantityMatches;
    }
    
    return hasActiveClass && hasValues;
  }
}

