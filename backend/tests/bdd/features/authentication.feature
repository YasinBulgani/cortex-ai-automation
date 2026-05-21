# language: en

Feature: Kimlik Doğrulama ve Oturum Yönetimi
  Platform kullanıcıları JWT tabanlı token ile oturum açar,
  korumalı kaynaklara erişir ve oturumlarını yönetir.

  Background:
    Given backend API "http://127.0.0.1:8000" adresinde çalışıyor
    And admin kullanıcısı "admin@example.com" / "admin123" olarak mevcut

  @critical @pozitif
  Scenario: Geçerli bilgilerle başarılı oturum açma
    Given kullanıcı login endpoint'ine istek hazırlıyor
    And e-posta alanına "admin@example.com" yazıyor
    And parola alanına "admin123" yazıyor
    When POST "/api/v1/auth/login" isteği gönderilir
    Then yanıt kodu 200 olmalı
    And yanıtta "access_token" alanı dolu olmalı
    And yanıtta "token_type" değeri "bearer" olmalı
    And token JWT formatında (3 nokta-ayrılmış segment) olmalı

  @critical @negatif
  Scenario: Hatalı parola ile oturum açma reddedilir
    Given kullanıcı login endpoint'ine istek hazırlıyor
    And e-posta alanına "admin@example.com" yazıyor
    And parola alanına "yanlis_parola" yazıyor
    When POST "/api/v1/auth/login" isteği gönderilir
    Then yanıt kodu 401 olmalı
    And yanıtta "E-posta veya parola hatalı" mesajı olmalı

  @high @negatif
  Scenario: Kayıtlı olmayan e-posta ile oturum açma reddedilir
    Given kullanıcı login endpoint'ine istek hazırlıyor
    And e-posta alanına "yok@test.com" yazıyor
    And parola alanına "herhangi" yazıyor
    When POST "/api/v1/auth/login" isteği gönderilir
    Then yanıt kodu 401 olmalı

  @high @negatif
  Scenario: Devre dışı bırakılmış hesap oturum açamaz
    Given "devre_disi@test.com" kullanıcısı devre dışı bırakılmış
    When bu kullanıcının bilgileriyle login isteği gönderilir
    Then yanıt kodu 403 olmalı
    And yanıtta "Hesap devre dışı" mesajı olmalı

  @boundary
  Scenario Outline: Geçersiz giriş verileri ile validation hatası
    Given kullanıcı login endpoint'ine istek hazırlıyor
    And e-posta alanına "<email>" yazıyor
    And parola alanına "<parola>" yazıyor
    When POST "/api/v1/auth/login" isteği gönderilir
    Then yanıt kodu <kod> olmalı

    Examples:
      | email              | parola   | kod |
      |                    | admin123 | 422 |
      | admin@example.com  |          | 422 |
      | gecersiz-format    | admin123 | 422 |

  @high @pozitif
  Scenario: Geçerli token ile kullanıcı bilgileri alınır
    Given admin kullanıcısı oturum açmış ve token almış
    When GET "/api/v1/auth/me" isteği token ile gönderilir
    Then yanıt kodu 200 olmalı
    And yanıtta "id" alanı dolu olmalı
    And yanıtta "email" değeri "admin@example.com" olmalı
    And yanıtta "roles" listesi boş olmamalı

  @critical @negatif
  Scenario: Token olmadan korumalı endpoint'e erişim engellenir
    Given Authorization header gönderilmiyor
    When GET "/api/v1/tspm/projects" isteği gönderilir
    Then yanıt kodu 401 veya 403 olmalı

  @medium @pozitif
  Scenario: Başarılı login sonrası audit log kaydı oluşturulur
    Given admin kullanıcısı başarılı login yapmış
    When veritabanında audit_logs tablosu kontrol edilir
    Then "auth.login" aksiyonlu kayıt bulunmalı
    And actor_user_id admin kullanıcısının ID'si olmalı
