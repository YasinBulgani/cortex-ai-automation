# Engine Test Data

Bu dizin, BGTS Test Dönüşüm platformunun test otomasyon motorunda kullanılan
sabit (fixture) ve dinamik test verilerini barındırır.

## Dosya Yapısı

| Dosya | Açıklama |
|---|---|
| `users.json` | Kimlik doğrulama testleri için kullanıcı verileri (admin, lider, QA, viewer, negatif) |
| `projects.json` | Türk bankacılık sektörüne ait örnek proje verileri |
| `scenarios.json` | 20 farklı modülü kapsayan test senaryoları (P0-P3 öncelik) |
| `api_payloads.json` | API endpoint testleri için yeniden kullanılabilir istek gövdeleri |
| `synthetic_data_config.json` | Sentetik veri üretimi konfigürasyonları (müşteri, hesap, işlem profilleri) |
| `locator_test_data.json` | UI element doğrulama için CSS/XPath seçiciler |
| `environments.json` | Dev, staging ve production ortam konfigürasyonları |
| `fixtures.py` | Python yardımcı fonksiyonları: veri yükleme, rastgele TCKN/IBAN/telefon üretimi |
| `__init__.py` | Fixtures modülünden tüm fonksiyonların export'u |

## Kullanım

```python
from engine.test_data import load_test_data, get_admin_user, random_tckn

# JSON dosyasından veri yükle
users = load_test_data("users.json")

# Hazır admin kullanıcısını al
admin = get_admin_user()

# Algoritmik olarak geçerli TCKN üret
tckn = random_tckn()
```

## Veri Kuralları

- Tüm TCKN numaraları 11 haneli algoritmaya uygundur (sentetik, gerçek değil)
- IBAN değerleri TR formatında geçerli kontrol basamaklarına sahiptir
- Telefon numaraları `+90 5XX XXX XX XX` formatındadır
- Türkçe karakterler doğru kullanılır (ş, ç, ğ, ı, ö, ü, İ, Ş, Ç, Ğ, Ö, Ü)
