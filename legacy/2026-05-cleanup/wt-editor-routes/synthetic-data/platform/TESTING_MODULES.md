# SyntheticBankData - Test Otomasyonu Modülleri

Bu dokümantasyon, SyntheticBankData projesinde test otomasyonu için oluşturulan modülleri açıklamaktadır.

## Dosya Yapısı

```
app/
├── services/
│   ├── visual_regression.py      # Görsel regresyon testi hizmetleri
│   ├── accessibility_tester.py   # Erişilebilirlik testi (WCAG 2.1)
│   └── test_recorder.py          # Test kaydı ve oynatma hizmetleri
├── schemas/
│   └── testing_schemas.py        # Pydantic v2 test şemaları
└── api/
    └── testing_routes.py         # FastAPI test otomasyonu endpoints
```

## Modüllerin Açıklaması

### 1. Visual Regression Module (`app/services/visual_regression.py`)
**Amaç:** Üretilen veri çıktılarının görsel regresyon testini yönetir.

**Ana Sınıf:** `VisualRegressionTester`
- **capture_baseline()**: Temel görüntüleri yakalar ve depolar
- **compare_screenshots()**: İki görüntüyü karşılaştırır ve benzerlik oranını hesaplar
- **detect_visual_changes()**: Görsel değişiklikleri tespit eder ve rapor oluşturur
- **generate_diff_report()**: Fark raporunu görsel olarak oluşturur
- **generate_json_report()**: JSON formatında detaylı rapor oluşturur

**Özellikler:**
- PIL/Pillow tabanlı görüntü işleme
- Piksel tabanlı fark hesaplaması
- Otomatik değişim türü sınıflandırması (identical, minor, significant, critical)
- Türkçe dokstrings ve log mesajları

### 2. Accessibility Tester Module (`app/services/accessibility_tester.py`)
**Amaç:** WCAG 2.1 erişilebilirlik standartlarına uygunluğu kontrol eder.

**Ana Sınıf:** `AccessibilityTester`
- **check_color_contrast()**: Renk kontrastı WCAG 2.1'e göre doğrular
- **validate_aria_labels()**: ARIA etiketlerinin varlığını ve geçerliliğini doğrular
- **check_keyboard_navigation()**: Klavye navigasyonunun erişilebilirliğini kontrol eder
- **check_screen_reader_compatibility()**: Ekran okuyucu uyumluluğunu kontrol eder
- **generate_a11y_report()**: Kapsamlı erişilebilirlik raporu oluşturur
- **export_report_to_json()**: Raporu JSON formatında dışa aktarır

**Özellikleri:**
- WCAG 2.1 seviye kontrolü (A, AA, AAA)
- Renk kontrastı matematiksel hesaplaması
- ARIA rol doğrulaması
- Kontrast seviyeleri: PASS_AAA, PASS_AA, PASS_LARGE_AA, FAIL
- Türkçe öneriler ve hata mesajları

### 3. Test Recorder Module (`app/services/test_recorder.py`)
**Amaç:** Test oturumlarını kaydeder ve oynatır.

**Ana Sınıf:** `TestRecorder`
- **start_recording()**: Yeni test kaydını başlatır
- **add_step()**: Kaydedilen oturuma test adımı ekler
- **add_assertion()**: Adıma onaylama ekler
- **stop_recording()**: Test kaydını durdurur ve kaydeder
- **replay_session()**: Kaydedilen oturumu oynatır
- **export_recording()**: Kaydı JSON formatında dışa aktarır
- **import_recording()**: JSON kaydını içe aktarır
- **list_recordings()**: Tüm kaydedilmiş oturumları listeler
- **delete_recording()**: Kaydedilmiş oturumu siler

**Özellikler:**
- JSON tabanlı seri depolama
- UUID ile benzersiz tanımlama
- 15+ adım türü (click, type, navigate, wait, vb.)
- 6+ onaylama türü (element_visible, text_contains, vb.)
- Başarı oranı ve süre hesaplaması
- Oturum döngüsü yönetimi (created → recording → completed)

### 4. Testing Schemas Module (`app/schemas/testing_schemas.py`)
**Amaç:** Tüm test modülleri için Pydantic v2 şemaları tanımlar.

**Ana Şemalar:**
- `VisualRegressionRequest/Result`: Görsel test istekleri ve sonuçları
- `AccessibilityCheckRequest/Report`: Erişilebilirlik testi istekleri ve raporları
- `TestStepSchema/TestRecording`: Test adımları ve kayıtları
- `TestRunRequest/Result`: Test çalıştırma istekleri ve sonuçları
- `TestSessionSummary`: Oturum özeti
- `A11yIssueDetail`: Erişilebilirlik sorunu detayları

**Enum Türleri:**
- `ChangeTypeEnum`: identical, minor, significant, critical
- `A11yIssueSeverity`: critical, major, minor
- `ActionTypeEnum`: click, type, navigate, wait, screenshot, assert, hover, scroll, select, submit
- `AssertionTypeEnum`: element_visible, element_hidden, text_contains, value_equals, url_equals, element_count

### 5. Testing Routes Module (`app/api/testing_routes.py`)
**Amaç:** Test otomasyonu için FastAPI endpoints sağlar.

**Endpoints:**

#### Görsel Regresyon
- `POST /api/v1/testing/visual-regression/run`: Görsel regresyon testini çalıştırır
- `GET /api/v1/testing/visual-regression/results`: Test sonuçlarını listeler

#### Erişilebilirlik
- `POST /api/v1/testing/accessibility/check`: Erişilebilirlik kontrolünü çalıştırır
- `GET /api/v1/testing/accessibility/report/{test_id}`: Raporu getirir

#### Test Kaydı
- `POST /api/v1/testing/recorder/start`: Test kaydını başlatır
- `POST /api/v1/testing/recorder/stop`: Test kaydını durdurur
- `GET /api/v1/testing/recorder/sessions`: Oturumları listeler
- `GET /api/v1/testing/recorder/sessions/{session_id}`: Belirli oturumu getirir
- `POST /api/v1/testing/recorder/export`: Oturumu dışa aktarır
- `POST /api/v1/testing/recorder/import`: Oturumu içe aktarır

#### Sağlık
- `GET /api/v1/testing/health`: API sağlık kontrolü

**Özellikler:**
- Lazy initialization (singleton pattern)
- Arka plan görevleri (BackgroundTasks)
- Dosya indirme desteği (FileResponse)
- Kapsamlı hata yönetimi
- Turkish dokumentasyon ve açıklamalar

## Kullanım Örnekleri

### Görsel Regresyon Testi
```python
from app.services.visual_regression import VisualRegressionTester

tester = VisualRegressionTester(
    baseline_dir="/tmp/baselines",
    current_dir="/tmp/current",
    diff_dir="/tmp/diffs"
)

# Temel görüntüyü yakala
baseline_path = tester.capture_baseline(image_bytes, "login_page")

# Karşılaştır
identical, similarity = tester.compare_screenshots(baseline_path, current_path)

# Değişiklikleri tespit et
report = tester.detect_visual_changes(baseline_path, current_path)
```

### Erişilebilirlik Testi
```python
from app.services.accessibility_tester import AccessibilityTester

tester = AccessibilityTester(min_contrast_ratio=4.5)

# Renk kontrastı kontrolü
passed, level, ratio = tester.check_color_contrast(
    foreground_color="#000000",
    background_color="#FFFFFF",
    text_size=14
)

# Rapor oluştur
report = tester.generate_a11y_report("test_name", wcag_level="AA")
```

### Test Kaydı
```python
from app.services.test_recorder import TestRecorder, ActionType

recorder = TestRecorder(recordings_dir="/tmp/recordings")

# Kaydı başlat
session_id = recorder.start_recording("Login Test", "Testing login functionality")

# Adımlar ekle
recorder.add_step(ActionType.CLICK, selector="#login_button", duration_ms=100)
recorder.add_step(ActionType.TYPE, selector="#email", value="test@example.com")

# Kaydı durdur ve kaydet
session = recorder.stop_recording()

# Oturumu oynat
results = recorder.replay_session(session_id)
```

## Gereksinimler

- Python 3.8+
- FastAPI 0.100+
- Pydantic 2.0+
- Pillow (PIL) 9.0+
- pytest (test için)

## Teknik Detaylar

- **Dokstrings:** Tüm modüller Türkçe dokstring ile belgelenmiştir
- **Type Hints:** Tam type hint desteği (Python 3.8+)
- **Error Handling:** Kapsamlı try-except blokları ve özel hata mesajları
- **Logging:** Python logging modülü ile tüm operasyonlar loglanır
- **JSON Serialization:** Tüm şemalar JSON ile uyumludur
- **Async Support:** FastAPI endpoints async/await destekler

## İstatistikler

- **Toplam Satır Kodu:** 2,444 satır
- **Visual Regression:** 305 satır
- **Accessibility Tester:** 492 satır
- **Test Recorder:** 616 satır
- **Testing Schemas:** 353 satır
- **Testing Routes:** 678 satır

## Lisans ve Notlar

Tüm dosyalar SyntheticBankData projesinin bir parçasıdır ve Turkish banking synthetic data platformu için geliştirilmiştir.
