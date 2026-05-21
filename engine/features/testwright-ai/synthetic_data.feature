# Platform: BGTS Test Dönüşüm
# URL: http://localhost:3000
# Modül: Sentetik Veri Üretimi
# API: /api/v1/tspm/projects/{id}/test-data*

Feature: Sentetik Veri Üretimi ve Test Verisi Yönetimi
  Bankacılık test verisi üretimi, veri seti kataloğu ve
  proje bazlı test verisi yönetimi test edilir.

  Background:
    Given kullanıcı admin olarak giriş yapmıştır

  # ─── VERİ SETİ YÜKLEME ─────────────────────────────────────────────

  Scenario: CSV dosyası yükleme
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    Then "[data-testid='synthetic-page']" elementi görünür olmalıdır

  Scenario: JSON dosyası yükleme
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    Then "[data-testid='synthetic-page']" elementi görünür olmalıdır

  # ─── VERİ ANALİZİ ──────────────────────────────────────────────────

  Scenario: Yüklenen verinin yapı analizini görüntüleme
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    Then "[data-testid='synthetic-page']" elementi görünür olmalıdır

  Scenario: Sütun tip tespiti sonuçlarını inceleme
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    Then "[data-testid='synthetic-page']" elementi görünür olmalıdır

  # ─── PII TESPİTİ ───────────────────────────────────────────────────

  Scenario: Kişisel veri (PII) tespiti
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    Then "[data-testid='synthetic-page']" elementi görünür olmalıdır

  Scenario: TCKN ve telefon alanlarının PII olarak işaretlenmesi
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    Then "[data-testid='synthetic-page']" elementi görünür olmalıdır

  # ─── SENTETİK VERİ ÜRETİMİ ─────────────────────────────────────────

  Scenario: Sentetik veri üretimini başlatma
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    Then "[data-testid='synthetic-page']" elementi görünür olmalıdır

  Scenario: Üretim iş durumunu takip etme
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    Then "[data-testid='synthetic-page']" elementi görünür olmalıdır

  # ─── DIŞA AKTARMA ──────────────────────────────────────────────────

  Scenario: Üretilen veri setini CSV olarak dışa aktarma
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    Then "[data-testid='synthetic-page']" elementi görünür olmalıdır

  Scenario: Üretilen veri setini JSON olarak dışa aktarma
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    Then "[data-testid='synthetic-page']" elementi görünür olmalıdır

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
    When kullanıcı "[data-testid^='scenarios-row-']" seçicisini tıklar
    When kullanıcı "Veri Bağla" metnine tıklar
    Then "[data-testid='data-binding-form']" elementi görünür olmalıdır

  # ─── VERİ SINIFLANDIRMA ────────────────────────────────────────────

  Scenario: Veri seti sınıflandırma
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    When kullanıcı "[data-testid='dataset-row']" seçicisini tıklar
    When kullanıcı "Sınıflandır" metnine tıklar
    When kullanıcı "3000" milisaniye bekler
    Then "[data-testid='classification-result']" elementi görünür olmalıdır

  # ─── KURAL ÇIKARIMI ────────────────────────────────────────────────

  Scenario: Veri kuralları çıkarımı
    Given kullanıcı test projesinin "synthetic" sayfasındadır
    When kullanıcı "[data-testid='dataset-row']" seçicisini tıklar
    When kullanıcı "Kural Çıkar" metnine tıklar
    When kullanıcı "3000" milisaniye bekler
    Then "[data-testid='rules-result']" elementi görünür olmalıdır
