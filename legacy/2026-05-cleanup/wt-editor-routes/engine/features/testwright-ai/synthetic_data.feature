# Platform: BGTS Test Dönüşüm
# URL: http://localhost:3000
# Modül: Sentetik Veri Üretimi
# API: /api/v1/upload, /api/v1/analyze, /api/v1/generate, /api/v1/tspm/projects/{id}/test-data*

Feature: Sentetik Veri Üretimi ve Test Verisi Yönetimi
  Bankacılık test verisi üretimi, dosya yükleme, analiz, PII tespiti,
  sentetik veri oluşturma ve proje bazlı test verisi yönetimi test edilir.

  Background:
    Given kullanıcı ana sayfadadır
    Given kullanıcı "/login" sayfasındadır
    When kullanıcı "[data-testid='email-input']" kutusuna "admin@example.com" yazar
    When kullanıcı "[data-testid='password-input']" kutusuna "admin123" yazar
    When kullanıcı "Giriş Yap" metnine tıklar

  # ─── VERİ SETİ YÜKLEME ─────────────────────────────────────────────

  Scenario: CSV dosyası yükleme
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='upload-area']" seçicisini tıklar
    When kullanıcı "1000" milisaniye bekler
    Then "[data-testid='upload-status']" elementi görünür olmalıdır

  Scenario: JSON dosyası yükleme
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='upload-area']" seçicisini tıklar
    When kullanıcı "1000" milisaniye bekler
    Then "[data-testid='upload-status']" elementi görünür olmalıdır

  # ─── VERİ ANALİZİ ──────────────────────────────────────────────────

  Scenario: Yüklenen verinin yapı analizini görüntüleme
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='dataset-row']" seçicisini tıklar
    When kullanıcı "Analiz Et" metnine tıklar
    When kullanıcı "3000" milisaniye bekler
    Then "[data-testid='analysis-result']" elementi görünür olmalıdır

  Scenario: Sütun tip tespiti sonuçlarını inceleme
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='dataset-row']" seçicisini tıklar
    When kullanıcı "Analiz Et" metnine tıklar
    When kullanıcı "3000" milisaniye bekler
    Then "[data-testid='column-types']" elementi görünür olmalıdır

  # ─── PII TESPİTİ ───────────────────────────────────────────────────

  Scenario: Kişisel veri (PII) tespiti
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='dataset-row']" seçicisini tıklar
    When kullanıcı "PII Tara" metnine tıklar
    When kullanıcı "3000" milisaniye bekler
    Then "[data-testid='pii-results']" elementi görünür olmalıdır

  Scenario: TCKN ve telefon alanlarının PII olarak işaretlenmesi
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='dataset-row']" seçicisini tıklar
    When kullanıcı "PII Tara" metnine tıklar
    When kullanıcı "3000" milisaniye bekler
    Then "[data-testid='pii-results']" elementi görünür olmalıdır

  # ─── SENTETİK VERİ ÜRETİMİ ─────────────────────────────────────────

  Scenario: Sentetik veri üretimini başlatma
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='dataset-row']" seçicisini tıklar
    When kullanıcı "Sentetik Üret" metnine tıklar
    When kullanıcı "[data-testid='row-count']" kutusuna "1000" yazar
    When kullanıcı "Üret" metnine tıklar
    When kullanıcı "5000" milisaniye bekler
    Then "[data-testid='generation-status']" elementi görünür olmalıdır

  Scenario: Üretim iş durumunu takip etme
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='jobs-tab']" seçicisini tıklar
    Then "[data-testid='job-list']" elementi görünür olmalıdır

  # ─── DIŞA AKTARMA ──────────────────────────────────────────────────

  Scenario: Üretilen veri setini CSV olarak dışa aktarma
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='dataset-row']" seçicisini tıklar
    When kullanıcı "Dışa Aktar" metnine tıklar
    When kullanıcı "CSV" metnine tıklar
    Then "[data-testid='download-link'], [data-testid='export-status']" elementi görünür olmalıdır

  Scenario: Üretilen veri setini JSON olarak dışa aktarma
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='dataset-row']" seçicisini tıklar
    When kullanıcı "Dışa Aktar" metnine tıklar
    When kullanıcı "JSON" metnine tıklar
    Then "[data-testid='download-link'], [data-testid='export-status']" elementi görünür olmalıdır

  # ─── PROJE TEST VERİSİ ─────────────────────────────────────────────

  Scenario: Proje bazlı test veri seti oluşturma
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "Test Verisi" metnine tıklar
    When kullanıcı "Yeni Veri Seti" metnine tıklar
    When kullanıcı "[data-testid='dataset-name']" kutusuna "Login Test Verileri" yazar
    When kullanıcı "Kaydet" metnine tıklar
    Then "[data-testid='dataset-list']" elementi görünür olmalıdır

  Scenario: Senaryoya test verisi bağlama
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid='scenario-row']" seçicisini tıklar
    When kullanıcı "Veri Bağla" metnine tıklar
    Then "[data-testid='data-binding-form']" elementi görünür olmalıdır

  # ─── VERİ SINIFLANDIRMA ────────────────────────────────────────────

  Scenario: Veri seti sınıflandırma
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='dataset-row']" seçicisini tıklar
    When kullanıcı "Sınıflandır" metnine tıklar
    When kullanıcı "3000" milisaniye bekler
    Then "[data-testid='classification-result']" elementi görünür olmalıdır

  # ─── KURAL ÇIKARIMI ────────────────────────────────────────────────

  Scenario: Veri kuralları çıkarımı
    Given kullanıcı "/datasets" sayfasındadır
    When kullanıcı "[data-testid='dataset-row']" seçicisini tıklar
    When kullanıcı "Kural Çıkar" metnine tıklar
    When kullanıcı "3000" milisaniye bekler
    Then "[data-testid='rules-result']" elementi görünür olmalıdır
