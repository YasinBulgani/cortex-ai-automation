import { Page, Locator } from 'playwright';
import { BasePage } from './BasePage';
import { TestDataLoader } from '../utils/TestDataLoader';
import { Logger } from '../utils/Logger';
import { SELECTOR_FALLBACKS, LIMITS } from '../config/constants';
import { InvalidDataError } from '../utils/CustomErrors';

export class MarketsPage extends BasePage {
  
  private readonly fanFilter: Locator;
  private readonly timeFilter12Hours: Locator;
  private readonly cryptocurrencyItems: Locator;
  private readonly sortByPriceButton: Locator;
  private readonly sortDescendingButton: Locator;

  constructor(page: Page, environment: string = 'paribu') {
    super(page, environment);
    
    // Selector'ları test data'dan yükle
    const selectors = TestDataLoader.loadWebSelectors();
    const paribuSelectors = selectors.paribu as Record<string, unknown> | undefined;
    const marketsSelectors = (paribuSelectors?.markets as Record<string, string> | undefined) || {};
    
    // Filtre selector'ları
    this.fanFilter = page.locator(marketsSelectors.fanFilter || 'button:has-text("FAN"), [data-filter="FAN"]').first();
    this.timeFilter12Hours = page.locator(marketsSelectors.timeFilter12Hours || '[data-time="12h"], button:has-text("12 Saat")').first();
    
    // Kripto para listesi selector'ları
    this.cryptocurrencyItems = page.locator(marketsSelectors.cryptocurrencyList ? `${marketsSelectors.cryptocurrencyList} > *` : '[data-testid="crypto-item"], .crypto-item, tr[class*="crypto"]').filter({ hasNotText: 'Başlık' });
    
    // Sıralama selector'ları
    this.sortByPriceButton = page.locator(marketsSelectors.sortByPrice || 'button:has-text("Fiyat"), [data-sort="price"]').first();
    this.sortDescendingButton = page.locator(marketsSelectors.sortDescending || '[data-order="desc"], button:has-text("Azalan")').first();
  }

  /**
   * FAN filtresini seç
   * Playwright'un otomatik bekleme mekanizmasını kullanır - statik bekleme gerekmez
   */
  async selectFanFilter(): Promise<void> {
    await this.clickElement(this.fanFilter);
    // Filtrenin uygulanmasını ve listenin güncellenmesini bekle
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Listede n. sıradaki kripto paraya tıkla (1'den başlar)
   * @param index - Listedeki pozisyon (1, 2, 3, vb.)
   * @throws {InvalidDataError} Eğer index geçersizse
   * @throws {Error} Eğer liste boşsa veya index sınırları aşıyorsa
   */
  async clickCryptocurrencyByIndex(index: number): Promise<void> {
    if (index < 1) {
      throw new InvalidDataError('index', index, 'Index must start from 1');
    }

    try {
      // Tüm kripto para öğelerini al
      const items = this.cryptocurrencyItems;
      const count = await items.count();
        
      if (count === 0) {
        throw new Error('Kripto para listesi boş');
      }
    
      if (count < index) {
        throw new InvalidDataError('index', index, `List has only ${count} items`);
      }
    
      // Belirtilen indeksteki öğeye tıkla (dahili olarak 0'dan başlar)
      const targetItem = items.nth(index - 1);
      await this.clickElement(targetItem);
    
      // Detay sayfasına navigasyonu bekle
      await this.page.waitForLoadState('networkidle');
    } catch (error) {
      if (error instanceof InvalidDataError || error instanceof Error) {
        throw error;
      }
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Kripto para seçilemedi: ${errorMessage}`);
    }
  }

  /**
   * Listedeki kripto para öğelerinin sayısını al
   */
  async getCryptocurrencyCount(): Promise<number> {
    return await this.cryptocurrencyItems.count();
  }

  /**
   * Zaman filtresini "12 Saat" olarak ayarla
   */
  async setTimeFilterTo12Hours(): Promise<void> {
    await this.clickElement(this.timeFilter12Hours);
    // Filtrenin uygulanmasını bekle
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Fiyata göre azalan sıralama yap
   */
  async sortByPriceDescending(): Promise<void> {
    // Önce sıralama butonuna tıkla
    await this.clickElement(this.sortByPriceButton);
    // Azalan sıralamayı seç
    await this.clickElement(this.sortDescendingButton);
    // Sıralamanın uygulanmasını bekle
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * 24 saat değişimi pozitif olan coin'leri filtrele
   * @param count - Kaç coin seçilecek (1-100 arası)
   * @returns Seçilen coin'lerin indeksleri (1'den başlar)
   * @throws {InvalidDataError} Eğer count geçersizse
   * @throws {Error} Eğer liste boşsa
   * @example
   * const indices = await marketsPage.selectRandomCoinsWithPositive24hChange(3);
   * // Returns: [1, 5, 12]
   */
  async selectRandomCoinsWithPositive24hChange(count: number): Promise<number[]> {
    if (count < LIMITS.PRODUCT_LIMIT_MIN || count > LIMITS.PRODUCT_LIMIT_MAX) {
      throw new InvalidDataError('count', count, `Count must be between ${LIMITS.PRODUCT_LIMIT_MIN} and ${LIMITS.PRODUCT_LIMIT_MAX}`);
    }

    const items = this.cryptocurrencyItems;
    const itemCount = await items.count();
    const selectedIndices: number[] = [];
    
    if (itemCount === 0) {
      throw new Error('Kripto para listesi boş');
    }
    
    // Her coin için 24 saat değişim değerini kontrol et
    for (let i = 0; i < itemCount && selectedIndices.length < count; i++) {
      try {
        const item = items.nth(i);
        
        // Fallback selector'ları kullanarak 24h değişim elementini bul
        const changeElement = await this.findElementWithFallbacks(
          SELECTOR_FALLBACKS.CHANGE_24H,
          item,
          `24h change for coin ${i + 1}`
        );
        
        if (changeElement) {
          const change24hText = await changeElement.textContent();
          
          if (change24hText && this.isPositiveChange(change24hText)) {
            selectedIndices.push(i + 1); // 1'den başlayan indeks
          }
        }
      } catch (error) {
        // Bu coin'i atla ve devam et
        Logger.debug(`Coin ${i + 1} için 24h değişim kontrolü başarısız`, { error });
      }
    }
    
    if (selectedIndices.length === 0) {
      // Eğer hiç pozitif değişimli coin bulunamazsa, ilk coin'leri seç
      Logger.warn('Pozitif 24h değişimli coin bulunamadı, ilk coin\'ler seçiliyor', { count });
      const fallbackCount = Math.min(count, itemCount, LIMITS.DEFAULT_COIN_SELECTION_COUNT);
      for (let i = 0; i < fallbackCount; i++) {
        selectedIndices.push(i + 1);
      }
    } else if (selectedIndices.length < count) {
      Logger.warn('Yeterli pozitif değişimli coin bulunamadı', { 
        found: selectedIndices.length, 
        requested: count 
      });
    }
    
    return selectedIndices;
  }

  /**
   * Değişim metninin pozitif olup olmadığını kontrol et
   * @param changeText - Değişim metni (örn: "+5.2%", "5.2", "-3.1%")
   * @returns Pozitif ise true
   */
  private isPositiveChange(changeText: string): boolean {
    // Metinden sayıyı çıkar (%, +, - işaretlerini de dahil et)
    const cleanText = changeText.replace(/[^\d.+]/g, '').replace(/-/g, '');
    const changeValue = parseFloat(cleanText);
    
    // Eğer sayı bulunursa ve pozitifse
    if (!isNaN(changeValue) && changeValue > 0) {
      return true;
    }
    
    // + işareti varsa pozitif kabul et
    return changeText.includes('+') || changeText.trim().startsWith('+');
  }
}

