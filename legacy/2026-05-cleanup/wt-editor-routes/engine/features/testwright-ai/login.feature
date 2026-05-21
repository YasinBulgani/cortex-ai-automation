# Platform: BGTS Test Dönüşüm
# Modül: Kimlik Doğrulama
# Step: steps/bgts_login_steps.py

@login
Feature: Kimlik Doğrulama ve Oturum Yönetimi
  Bankacılık test platformunda kullanıcıların güvenli bir şekilde
  giriş yapması, oturum bilgilerini sorgulaması ve çıkış yapması
  test edilir.

  Background:
    Given kullanıcı giriş sayfasında bekliyor

  # ── BAŞARILI GİRİŞ ──────────────────────────────────────────────

  @smoke @critical
  Scenario: Geçerli kimlik bilgileri ile başarılı giriş
    Given kullanıcı "admin" rolüyle giriş yapmıştır
    Then kullanıcı başarıyla giriş yapmış olmalıdır
    Then kullanıcı projeler sayfasına yönlendirilmelidir

  @smoke
  Scenario: Giriş sonrası projeler sayfasına yönlendirme
    Given kullanıcı "admin" rolüyle giriş yapmıştır
    Then kullanıcı projeler sayfasına yönlendirilmelidir

  # ── BAŞARISIZ GİRİŞ ─────────────────────────────────────────────

  @negative
  Scenario: Hatalı parola ile giriş reddi
    When kullanıcı "admin@example.com" e-postası ve "yanlis_parola" parolası ile giriş yapar
    Then hata mesajı görünür olmalıdır
    Then kullanıcı giriş sayfasına yönlendirilmelidir

  @negative
  Scenario: Kayıtlı olmayan e-posta ile giriş reddi
    When kullanıcı "bilinmeyen@bgts.com" e-postası ve "admin123" parolası ile giriş yapar
    Then hata mesajı görünür olmalıdır
    Then kullanıcı giriş sayfasına yönlendirilmelidir

  @boundary
  Scenario: Boş e-posta alanı ile giriş denemesi
    When kullanıcı giriş formunu boş bırakıp gönderir
    Then kullanıcı giriş sayfasına yönlendirilmelidir

  @boundary
  Scenario: Boş parola alanı ile giriş denemesi
    When kullanıcı "admin@example.com" e-postası ve "" parolası ile giriş yapar
    Then kullanıcı giriş sayfasına yönlendirilmelidir

  # ── DEVRE DIŞI HESAP ────────────────────────────────────────────

  @negative
  Scenario: Devre dışı hesap ile giriş engeli
    When kullanıcı "locked@bgts.com" e-postası ve "Locked1234!" parolası ile giriş yapar
    Then hata mesajı görünür olmalıdır
    Then kullanıcı giriş sayfasına yönlendirilmelidir

  # ── OTURUM BİLGİSİ ─────────────────────────────────────────────

  @smoke
  Scenario: Oturum açmış kullanıcı bilgilerini görüntüleme
    Given kullanıcı "admin" rolüyle giriş yapmıştır
    Then kullanıcı başarıyla giriş yapmış olmalıdır

  # ── ÇIKIŞ ───────────────────────────────────────────────────────

  @smoke
  Scenario: Başarılı oturum kapatma
    Given kullanıcı "admin" rolüyle giriş yapmıştır
    When kullanıcı oturumu kapatır
    Then kullanıcı giriş sayfasına yönlendirilmelidir

  # ── GÜVENLİK ────────────────────────────────────────────────────

  @security @negative
  Scenario: Token olmadan korumalı sayfaya erişim engeli
    Given kullanıcı "/projects" sayfasındadır
    Then URL "/login" içermelidir

  @security @negative
  Scenario: SQL injection koruması
    When kullanıcı "' OR '1'='1" e-postası ve "' OR '1'='1" parolası ile giriş yapar
    Then kullanıcı giriş sayfasına yönlendirilmelidir

  # ── FORM DOĞRULAMA ──────────────────────────────────────────────

  @smoke
  Scenario: Giriş formu görünür olmalıdır
    Then giriş formu görünür olmalıdır
