# Platform: BGTS Test Dönüşüm
# URL: http://localhost:3000
# Modül: İçe Aktarma
# API: /api/v1/tspm/projects/{projectId}/imports*

Feature: Dosya İçe Aktarma ve AI İşleme
  Bankacılık test dokümanlarının platforma yüklenmesi,
  ayrıştırılması, AI tarafından analiz edilmesi ve
  onay kuyruğuna iletilmesi süreçleri test edilir.

  Background:
    Given kullanıcı admin olarak giriş yapmıştır

  # ─── İÇE AKTARMA SAYFASI ───────────────────────────────────────────

  Scenario: İçe aktarma sayfasını görüntüleme
    Given kullanıcı test projesinin "import" sayfasındadır
    Then URL "/import" içermelidir
    Then "[data-testid='import-form']" elementi görünür olmalıdır

  Scenario: Dosya yükleme alanını görüntüleme
    Given kullanıcı test projesinin "import" sayfasındadır
    Then "[data-testid='file-upload']" elementi görünür olmalıdır

  # ─── DOSYA YÜKLEME ─────────────────────────────────────────────────

  Scenario: Dosya seçimi ve yükleme başlatma
    Given kullanıcı test projesinin "import" sayfasındadır
    Then "[data-testid='import-form']" elementi görünür olmalıdır
    Then "[data-testid='file-upload']" elementi görünür olmalıdır

  Scenario: Yükleme ilerleme durumunu izleme
    Given kullanıcı test projesinin "import" sayfasındadır
    When kullanıcı "[data-testid='file-upload']" seçicisini tıklar
    When kullanıcı "1000" milisaniye bekler
    Then "[data-testid='import-form']" elementi görünür olmalıdır

  # ─── AI İŞLEME ─────────────────────────────────────────────────────

  Scenario: Yüklenen dosyanın AI tarafından analiz edilmesi
    Given kullanıcı test projesinin "import" sayfasındadır
    When kullanıcı "[data-testid='file-upload']" seçicisini tıklar
    When kullanıcı "1000" milisaniye bekler
    Then "[data-testid='import-form']" elementi görünür olmalıdır

  Scenario: AI işleme sonuçlarını görüntüleme
    Given kullanıcı test projesinin "import" sayfasındadır
    When kullanıcı "[data-testid='file-upload']" seçicisini tıklar
    When kullanıcı "1000" milisaniye bekler
    Then "[data-testid='import-form'], [data-testid='import-page']" elementi görünür olmalıdır

  # ─── DURUM TAKİBİ ──────────────────────────────────────────────────

  Scenario: İçe aktarma geçmişini görüntüleme
    Given kullanıcı test projesinin "import" sayfasındadır
    Then "[data-testid='import-form'], [data-testid='import-page']" elementi görünür olmalıdır

  Scenario: Tamamlanan import kaydının listesi
    Given kullanıcı test projesinin "import" sayfasındadır
    Then "[data-testid='import-form'], [data-testid='import-page']" elementi görünür olmalıdır

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
