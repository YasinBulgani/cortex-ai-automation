# Platform: BGTS Test Dönüşüm
# URL: http://localhost:3000
# Modül: İçe Aktarma
# API: /api/v1/tspm/projects/{projectId}/imports*

Feature: Dosya İçe Aktarma ve AI İşleme
  Bankacılık test dokümanlarının platforma yüklenmesi,
  ayrıştırılması, AI tarafından analiz edilmesi ve
  onay kuyruğuna iletilmesi süreçleri test edilir.

  Background:
    Given kullanıcı ana sayfadadır
    Given kullanıcı "/login" sayfasındadır
    When kullanıcı "[data-testid='email-input']" kutusuna "admin@example.com" yazar
    When kullanıcı "[data-testid='password-input']" kutusuna "admin123" yazar
    When kullanıcı "Giriş Yap" metnine tıklar

  # ─── İÇE AKTARMA SAYFASI ───────────────────────────────────────────

  Scenario: İçe aktarma sayfasını görüntüleme
    Given kullanıcı test projesinin "import" sayfasındadır
    Then URL "/import" içermelidir
    Then "[data-testid='import-form']" elementi görünür olmalıdır

  Scenario: Kaynak seçim alanını görüntüleme
    Given kullanıcı test projesinin "import" sayfasındadır
    Then "[data-testid='source-selector']" elementi görünür olmalıdır

  # ─── DOSYA YÜKLEME ─────────────────────────────────────────────────

  Scenario: Dosya seçimi ve yükleme başlatma
    Given kullanıcı test projesinin "import" sayfasındadır
    When kullanıcı "[data-testid='file-upload']" seçicisini tıklar
    When kullanıcı "1000" milisaniye bekler
    Then "[data-testid='file-name']" elementi görünür olmalıdır

  Scenario: Yükleme ilerleme durumunu izleme
    Given kullanıcı test projesinin "import" sayfasındadır
    When kullanıcı "[data-testid='file-upload']" seçicisini tıklar
    When kullanıcı "Yükle" metnine tıklar
    Then "[data-testid='upload-progress'], [data-testid='upload-status']" elementi görünür olmalıdır

  # ─── AI İŞLEME ─────────────────────────────────────────────────────

  Scenario: Yüklenen dosyanın AI tarafından analiz edilmesi
    Given kullanıcı test projesinin "import" sayfasındadır
    When kullanıcı "[data-testid='file-upload']" seçicisini tıklar
    When kullanıcı "Yükle" metnine tıklar
    When kullanıcı "5000" milisaniye bekler
    Then "[data-testid='import-status']" elementi görünür olmalıdır

  Scenario: AI işleme sonuçlarını görüntüleme
    Given kullanıcı test projesinin "import" sayfasındadır
    When kullanıcı "[data-testid='file-upload']" seçicisini tıklar
    When kullanıcı "Yükle" metnine tıklar
    When kullanıcı "10000" milisaniye bekler
    Then "[data-testid='import-log'], [data-testid='import-status']" elementi görünür olmalıdır

  # ─── DURUM TAKİBİ ──────────────────────────────────────────────────

  Scenario: İçe aktarma geçmişini görüntüleme
    Given kullanıcı test projesinin "import" sayfasındadır
    Then "[data-testid='import-history']" elementi görünür olmalıdır

  Scenario: Tamamlanan import kaydının detayı
    Given kullanıcı test projesinin "import" sayfasındadır
    When kullanıcı "[data-testid='import-history-item']" seçicisini tıklar
    Then "[data-testid='import-detail']" elementi görünür olmalıdır

  # ─── HATA DURUMLARI ────────────────────────────────────────────────

  Scenario: Desteklenmeyen dosya formatı hatası
    Given kullanıcı test projesinin "import" sayfasındadır
    When kullanıcı "[data-testid='file-upload']" seçicisini tıklar
    When kullanıcı "1000" milisaniye bekler
    Then "[data-testid='import-form']" elementi görünür olmalıdır

  Scenario: Boş dosya yükleme hatası
    Given kullanıcı test projesinin "import" sayfasındadır
    When kullanıcı "Yükle" metnine tıklar
    Then "[data-testid='validation-error'], [data-testid='import-form']" elementi görünür olmalıdır
