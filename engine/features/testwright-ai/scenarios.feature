# Platform: BGTS Test Dönüşüm
# URL: http://localhost:3000
# Modül: Senaryo Yönetimi
# API: /api/v1/tspm/projects/{projectId}/scenarios*

Feature: Test Senaryosu Yönetimi
  Bankacılık test platformunda test senaryolarının oluşturulması,
  düzenlenmesi, aranması, filtrelenmesi, toplu işlemleri,
  versiyon yönetimi ve BDD senaryo üretimi test edilir.

  Background:
    Given kullanıcı admin olarak giriş yapmıştır

  # ─── SENARYO LİSTELEME ─────────────────────────────────────────────

  Scenario: Senaryo listesi sayfasını görüntüleme
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    Then URL "/scenarios" içermelidir
    Then "[data-testid='scenario-table']" elementi görünür olmalıdır

  Scenario: Senaryo listesinde arama yapma
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid='search-input']" kutusuna "login" yazar
    When kullanıcı "500" milisaniye bekler
    Then "[data-testid='scenario-table']" elementi görünür olmalıdır

  Scenario: Boş arama sonucu gösterimi
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid='search-input']" kutusuna "olmayan_senaryo_xyz" yazar
    When kullanıcı "500" milisaniye bekler
    Then "[data-testid='empty-state'], [data-testid='scenario-table']" elementi görünür olmalıdır

  # ─── SENARYO OLUŞTURMA ─────────────────────────────────────────────

  Scenario: Yeni test senaryosu oluşturma
    Given kullanıcı test projesinin "scenarios/new" sayfasındadır
    When kullanıcı "[data-testid='scenario-title']" kutusuna "Kullanıcı Giriş Testi" yazar
    When kullanıcı "[data-testid='scenario-description']" kutusuna "Bankacılık uygulamasına giriş akışı testi" yazar
    When kullanıcı "Kaydet" metnine tıklar
    Then URL "/scenarios" içermelidir

  Scenario: Senaryo başlığı olmadan kaydetme denemesi
    Given kullanıcı test projesinin "scenarios/new" sayfasındadır
    When kullanıcı "Kaydet" metnine tıklar
    Then "[data-testid='validation-error'], [data-testid='scenario-title']" elementi görünür olmalıdır

  Scenario: Senaryo oluşturma formunda adım ekleme
    Given kullanıcı test projesinin "scenarios/new" sayfasındadır
    When kullanıcı "[data-testid='scenario-title']" kutusuna "Adımlı Senaryo" yazar
    When kullanıcı "[data-testid='scenario-description']" kutusuna "Adım içeren senaryo açıklaması" yazar
    When kullanıcı "Kaydet" metnine tıklar
    Then URL "/scenarios" içermelidir

  # ─── SENARYO DÜZENLEME ─────────────────────────────────────────────

  Scenario: Mevcut senaryoyu düzenleme
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid^='scenarios-link-']" seçicisini tıklar
    When kullanıcı "Düzenle" metnine tıklar
    When kullanıcı "[data-testid='scenario-edit-input-title']" kutusuna "Güncellenmiş Senaryo Başlığı" yazar
    When kullanıcı "Kaydet" metnine tıklar
    Then URL "/scenarios" içermelidir

  # ─── SENARYO DETAY ─────────────────────────────────────────────────

  Scenario: Senaryo detay sayfasını görüntüleme
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid^='scenarios-link-']" seçicisini tıklar
    Then "[data-testid='scenario-detail-page']" elementi görünür olmalıdır
    Then "[data-testid='scenario-steps']" elementi görünür olmalıdır

  Scenario: Senaryo versiyon geçmişi görüntüleme
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid^='scenarios-link-']" seçicisini tıklar
    When kullanıcı "Versiyon Geçmişi" metnine tıklar
    Then "[data-testid='version-list']" elementi görünür olmalıdır

  # ─── TOPLU İŞLEMLER ────────────────────────────────────────────────

  Scenario: Birden fazla senaryo seçme
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid='select-all-checkbox']" seçicisini tıklar
    Then "[data-testid='bulk-actions']" elementi görünür olmalıdır

  Scenario: Seçili senaryoları toplu silme
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "[data-testid='select-all-checkbox']" seçicisini tıklar
    When kullanıcı "Seçilenleri sil" metnine tıklar
    When kullanıcı "Onayla" metnine tıklar
    Then "[data-testid='scenario-table']" elementi görünür olmalıdır

  # ─── BDD SENARYO ÜRETİMİ ───────────────────────────────────────────

  Scenario: AI ile BDD senaryo üretimi
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "BDD Üret" metnine tıklar
    When kullanıcı "[data-testid='analysis-text']" kutusuna "Kullanıcı bankacılık uygulamasına giriş yapar ve hesap bakiyesini görüntüler" yazar
    When kullanıcı "Senaryoları Üret" metnine tıklar
    When kullanıcı "5000" milisaniye bekler
    Then "[data-testid='generated-scenarios'], [data-testid='scenario-generate-page']" elementi görünür olmalıdır

  Scenario: Üretilen BDD senaryolarını kaydetme
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    When kullanıcı "BDD Üret" metnine tıklar
    When kullanıcı "[data-testid='analysis-text']" kutusuna "Para transferi akışı" yazar
    When kullanıcı "Senaryoları Üret" metnine tıklar
    When kullanıcı "5000" milisaniye bekler
    Then "[data-testid='generated-scenarios'], [data-testid='scenario-generate-page']" elementi görünür olmalıdır

  # ─── GEREKSİNİM BAĞLAMA ────────────────────────────────────────────

  Scenario: Senaryoya gereksinim bağlama
    Given kullanıcı test projesinin "scenarios/new" sayfasındadır
    When kullanıcı "[data-testid='scenario-title']" kutusuna "Gereksinim Bağlama Testi" yazar
    When kullanıcı "[data-testid='scenario-description']" kutusuna "Gereksinim bağlama test senaryosu" yazar
    When kullanıcı "Kaydet" metnine tıklar
    When kullanıcı "1000" milisaniye bekler
    Then "[data-testid='scenario-table'], [data-testid='scenario-detail-page']" elementi görünür olmalıdır
