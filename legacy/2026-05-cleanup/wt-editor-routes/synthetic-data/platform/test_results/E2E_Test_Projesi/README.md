# E2E_Test_Projesi

Test Otomasyon Projesi - Playwright ile Async Testler

## Proje Hakkında

Bu proje, Playwright kullanarak web uygulamalarının test otomasyon için tam bir yapı sağlar.
Async/await desenini kullanarak hızlı ve güvenilir testler yazmanıza olanak tanır.

## Gereksinimler

- Python 3.9+
- pip
- Git

## Kurulum

1. Projeyi klonla:
```bash
git clone <repository-url>
cd E2E_Test_Projesi
```

2. Virtual ortam oluştur:
```bash
python -m venv venv
```

3. Virtual ortamı aktifleştir:
```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

4. Bağımlılıkları yükle:
```bash
pip install -r requirements.txt
```

5. Playwright tarayıcılarını yükle:
```bash
playwright install
```

6. Ortam değişkenlerini yapılandır:
```bash
cp .env.example .env
# .env dosyasını düzenle
```

## Test Çalıştırma

### Tüm testleri çalıştır:
```bash
pytest
```

### Belirli bir test dosyasını çalıştır:
```bash
pytest tests/test_login.py
```

### Belirli bir test sınıfını çalıştır:
```bash
pytest tests/test_login.py::TestLogin
```

### Belirli bir test metodunu çalıştır:
```bash
pytest tests/test_login.py::TestLogin::test_successful_login
```

### İşaretlere göre testleri çalıştır:
```bash
pytest -m smoke
pytest -m critical
```

### Paralel testleri çalıştır:
```bash
pytest -n 4
```

### HTML raporu ile çalıştır:
```bash
pytest --html=report.html --self-contained-html
```

### Allure raporu ile çalıştır:
```bash
pytest --alluredir=allure-results
allure serve allure-results
```

### Verbose çıkış ile çalıştır:
```bash
pytest -v
```

### Yavaş testleri hariç tut:
```bash
pytest -m "not slow"
```

## Proje Yapısı

```
E2E_Test_Projesi/
├── tests/                 # Test dosyaları
│   ├── __init__.py
│   ├── conftest.py       # Test-spesifik fixture'lar
│   ├── test_login.py     # Giriş testleri
│   └── test_homepage.py  # Ana sayfa testleri
├── pages/                 # Sayfa Nesneleri (POM)
│   ├── __init__.py
│   ├── base_page.py      # Temel sayfa sınıfı
│   ├── login_page.py     # Giriş sayfası
│   └── home_page.py      # Ana sayfa
├── utils/                 # Yardımcı modüller
│   ├── __init__.py
│   ├── helpers.py        # Yardımcı fonksiyonlar
│   └── test_data.py      # Test verileri
├── config/                # Konfigürasyon
│   ├── __init__.py
│   └── settings.py       # Ayarlar
├── fixtures/              # Özel fixture'lar
│   ├── __init__.py
│   └── test_fixtures.py  # Fixture tanımları
├── reports/              # Test raporları
├── screenshots/          # Hata screenshot'ları
├── conftest.py          # Kök seviye konfigürasyon
├── pytest.ini           # Pytest konfigürasyonu
├── pyproject.toml       # Proje konfigürasyonu
├── requirements.txt     # Python bağımlılıkları
├── .env.example         # Ortam değişkenleri şablonu
├── .gitignore          # Git hariç tutma
└── README.md           # Bu dosya
```

## Sayfa Nesneleri Modeli (POM)

Proje, Sayfa Nesneleri Modeli desenini kullanır. Her sayfa, bir sayfa nesnesi sınıfı tarafından
temsil edilir ve sayfaya özgü etkileşimleri kapsüller.

### Örnek Kullanım:

```python
from pages.login_page import LoginPage

async def test_login(page):
    login_page = LoginPage(page)
    await login_page.navigate('http://localhost:3000/login')
    await login_page.login('username', 'password')
    assert await login_page.is_logged_in()
```

## Fixture'lar

Projede şu fixture'lar mevcuttur:

- `browser`: Browser instance'ı
- `context`: Browser context'i
- `page`: Sayfa nesnesi
- `base_url`: Temel URL
- `authenticated_page`: Kimlik doğrulanmış sayfa
- `test_user`: Test kullanıcı verisi
- `api_client`: API istemci

## Logging

Testler otomatik olarak loglanır. Log dosyaları `logs/` dizininde saklanır.

## Raporlama

### Pytest HTML Raporu:
```bash
pytest --html=report.html --self-contained-html
```

### Allure Raporu:
```bash
pytest --alluredir=allure-results
allure serve allure-results
```

## Katkı

Bu projede katkıda bulunmak için:

1. Fork yapın
2. Feature branch'i oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişikleri commit edin (`git commit -m 'Add AmazingFeature'`)
4. Push yapın (`git push origin feature/AmazingFeature`)
5. Pull Request açın

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır.

## İletişim

Test Takımı - test@example.com

---

Son güncelleme: dev
