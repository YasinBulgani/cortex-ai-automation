# Platform: BGTS Test Dönüşüm
# Modül: Smoke Test Seti
# Step: steps/bgts_smoke_steps.py + steps/bgts_login_steps.py

@smoke
Feature: Smoke Test Seti
  Her deployment sonrasında çalıştırılacak minimum doğrulama seti.
  Platformun temel fonksiyonlarının çalışır durumda olduğunu hızlıca doğrular.

  # ═══════════════════════════════════════════════════════════════════
  # ALTYAPI SAĞLIK KONTROLLERİ
  # ═══════════════════════════════════════════════════════════════════

  @critical
  Scenario: SMOKE-01 Backend sağlık kontrolü
    When API sağlık kontrolü yapılır
    Then API yanıt kodu 200 olmalıdır

  @critical
  Scenario: SMOKE-02 Veritabanı bağlantı kontrolü
    When API hazırlık kontrolü yapılır
    Then API yanıt kodu 200 olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # KİMLİK DOĞRULAMA
  # ═══════════════════════════════════════════════════════════════════

  @critical
  Scenario: SMOKE-03 Başarılı kullanıcı girişi
    Given kullanıcı "admin" rolüyle giriş yapmıştır
    Then kullanıcı başarıyla giriş yapmış olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # PROJE İŞLEMLERİ
  # ═══════════════════════════════════════════════════════════════════

  Scenario: SMOKE-04 Proje listesi görüntüleme
    Given kullanıcı "admin" rolüyle giriş yapmıştır
    Given kullanıcı "/projects" sayfasındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # SENARYO İŞLEMLERİ
  # ═══════════════════════════════════════════════════════════════════

  Scenario: SMOKE-06 Senaryo oluşturma formu erişimi
    Given kullanıcı admin olarak giriş yapmıştır
    Given kullanıcı test projesinin dashboard'ındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  Scenario: SMOKE-05 Senaryo listesi görüntüleme
    Given kullanıcı "admin" rolüyle giriş yapmıştır
    Given kullanıcı test projesinin "scenarios" sayfasındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # ONAY KUYRUĞU
  # ═══════════════════════════════════════════════════════════════════

  Scenario: SMOKE-07 Onay kuyruğu erişimi
    Given kullanıcı "admin" rolüyle giriş yapmıştır
    Given kullanıcı test projesinin "approvals" sayfasındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # İÇE AKTARMA
  # ═══════════════════════════════════════════════════════════════════

  Scenario: SMOKE-08 İçe aktarma sayfası erişimi
    Given kullanıcı "admin" rolüyle giriş yapmıştır
    Given kullanıcı test projesinin "import" sayfasındadır
    Then sayfa başarıyla yüklenmiş olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # DASHBOARD
  # ═══════════════════════════════════════════════════════════════════

  Scenario: SMOKE-09 Dashboard istatistikleri
    Given kullanıcı "admin" rolüyle giriş yapmıştır
    Given kullanıcı test projesinin dashboard'ındadır
    Then "[data-testid='dashboard-stat-scenario-count']" elementi görünür olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # ENGINE API
  # ═══════════════════════════════════════════════════════════════════

  Scenario: SMOKE-10 Engine feature listesi erişimi
    When Engine ile feature listesi sorgulanır
    Then API yanıtı başarılı olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # AUTH API
  # ═══════════════════════════════════════════════════════════════════

  Scenario: SMOKE-11 Auth API erişimi
    When API ile geçerli kimlik bilgileriyle giriş yapılır
    Then API yanıt kodu 200 olmalıdır

  # ═══════════════════════════════════════════════════════════════════
  # ÇIKIŞ VE GÜVENLİK
  # ═══════════════════════════════════════════════════════════════════

  Scenario: SMOKE-13 Kullanıcı çıkış işlemi
    Given kullanıcı "admin" rolüyle giriş yapmıştır
    When kullanıcı oturumu kapatır
    Then kullanıcı giriş sayfasına yönlendirilmelidir

  @security
  Scenario: SMOKE-14 Token olmadan korumalı sayfa erişim engeli
    Given kullanıcı "/projects" sayfasındadır
    Then URL "/login" içermelidir
