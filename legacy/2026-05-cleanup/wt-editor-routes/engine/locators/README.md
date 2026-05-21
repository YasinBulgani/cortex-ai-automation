# BGTS Locator Stratejisi

## Genel Bakış

Bu dizin, BGTS Test Dönüşüm projesinin tüm UI element seçicilerini merkezi olarak yönetir.
Locator'lar JSON dosyasında tanımlanır ve `LocatorManager` sınıfı aracılığıyla Page Object'ler
tarafından tüketilir.

## Dosya Yapısı

```
engine/locators/
├── README.md                  # Bu döküman
├── __init__.py                # Paket tanımı
├── locator_repository.json    # Tüm sayfa locator'ları (tek kaynak)
└── locator_manager.py         # LocatorManager sınıfı
```

## Locator Repository Yapısı

`locator_repository.json` dosyası her sayfa için şu yapıyı kullanır:

```json
{
  "sayfa_adı": {
    "url_pattern": "/route",
    "elements": {
      "element_adı": {
        "css": "CSS seçici",
        "xpath": "XPath seçici",
        "test_id": "data-testid değeri",
        "description": "Türkçe açıklama",
        "wait_strategy": "visible | attached | domcontentloaded"
      }
    }
  }
}
```

## Seçici Öncelik Sırası (Fallback Chain)

LocatorManager şu sırayla element bulmayı dener:

1. **test_id** — `[data-testid="..."]` en güvenilir, değişime en dayanıklı
2. **css** — CSS seçici, genellikle sınıf veya öznitelik tabanlı
3. **xpath** — XPath, karmaşık DOM yapıları için son çare

## Self-Healing Mekanizması

Birincil seçici başarısız olduğunda `LocatorManager.self_heal()` metodu
otomatik olarak alternatif seçicileri dener. Başarılı bulunan seçici loglanır
ve rapor olarak dışa aktarılabilir.

## Kullanım

```python
from locators import LocatorManager

lm = LocatorManager()

# Tek seçici al
selector = lm.get_locator("login", "email_input", strategy="test_id")

# Self-heal ile element bul (otomatik fallback)
selector = lm.self_heal("login", "email_input", playwright_page)

# Tüm locator'ların sağlık raporunu oluştur
report = lm.export_report()
```

## Page Object Entegrasyonu

Tüm Page Object sınıfları `LocatorManager` üzerinden seçici alır.
Hardcoded seçici kullanılmaz:

```python
class LoginPage(BasePage):
    def __init__(self, page, locator_manager):
        super().__init__(page)
        self.lm = locator_manager

    def login(self, email, password):
        self.fill(self.lm.get_locator("login", "email_input"), email)
        self.fill(self.lm.get_locator("login", "password_input"), password)
        self.click(self.lm.get_locator("login", "submit_button"))
```

## Yeni Locator Ekleme

1. `locator_repository.json` dosyasına ilgili sayfanın `elements` bölümüne yeni element ekleyin
2. Mutlaka `css`, `xpath` ve `test_id` alanlarının üçünü de doldurun
3. `description` alanını Türkçe yazın
4. İlgili Page Object'te metot ekleyin
