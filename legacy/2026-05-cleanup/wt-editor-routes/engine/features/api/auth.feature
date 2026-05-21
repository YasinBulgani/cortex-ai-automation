@api @auth @TS-01
Feature: Kimlik Dogrulama ve Oturum Yonetimi
  Kullanicilar JWT tabanli token ile oturum acar,
  korunmus kaynaklara erisir ve yetkisiz erisim engellenir.

  Arka plan: Sistem hazir
    Given backend servisi ayakta
    And admin kullanicisi seed edilmis

  # -- TC-0101 --
  @critical @positive @TC-0101
  Scenario: Gecerli kullanici basarili login
    When "admin@example.com" ve "admin123" ile login istegi gonderilir
    Then HTTP yanit kodu 200 olmalidir
    And yanit "access_token" alani dolu olmalidir
    And yanit "token_type" alani "bearer" olmalidir

  # -- TC-0102 --
  @critical @negative @TC-0102
  Scenario: Hatali parola ile login reddi
    When "admin@example.com" ve "wrongpass" ile login istegi gonderilir
    Then HTTP yanit kodu 401 olmalidir
    And yanit hata mesaji "E-posta veya parola hatalı" icermelidir

  # -- TC-0103 --
  @high @negative @TC-0103
  Scenario: Kayitli olmayan e-posta ile login reddi
    When "nonexistent@test.com" ve "admin123" ile login istegi gonderilir
    Then HTTP yanit kodu 401 olmalidir
    And yanit hata mesaji "E-posta veya parola hatalı" icermelidir

  # -- TC-0104 --
  @high @negative @TC-0104
  Scenario: Devre disi hesap ile login
    Given devre disi birakilmis bir kullanici mevcut
    When devre disi kullanicinin bilgileriyle login istegi gonderilir
    Then HTTP yanit kodu 403 olmalidir
    And yanit hata mesaji "Hesap devre dışı" icermelidir

  # -- TC-0105 / TC-0106 / TC-0107 --
  @medium @boundary @TC-0105 @TC-0106 @TC-0107
  Scenario Outline: Gecersiz login parametreleri ile dogrulama hatasi
    When "<email>" ve "<password>" ile login istegi gonderilir
    Then HTTP yanit kodu <code> olmalidir

    Examples: Gecersiz giris bilgileri
      | email              | password  | code |
      |                    | admin123  | 422  |
      | admin@example.com  |           | 422  |
      | not-an-email       | admin123  | 422  |

  # -- TC-0108 --
  @high @positive @TC-0108
  Scenario: Gecerli token ile kullanici bilgileri alinir
    Given kullanici oturum acmis
    When /api/v1/auth/me endpoint'ine GET istegi gonderilir
    Then HTTP yanit kodu 200 olmalidir
    And yanit "id" alani dolu olmalidir
    And yanit "email" alani dolu olmalidir
    And yanit "roles" alani dolu olmalidir

  # -- TC-0109 --
  @critical @negative @TC-0109
  Scenario: Token olmadan korumali endpoint erisimi engellenir
    Given kullanici oturum acmamis
    When /api/v1/tspm/projects endpoint'ine token olmadan GET istegi gonderilir
    Then HTTP yanit kodu 401 veya 403 olmalidir

  # -- TC-0110 --
  @medium @positive @TC-0110
  Scenario: Basarili login sonrasi audit log kaydi olusur
    When "admin@example.com" ve "admin123" ile login istegi gonderilir
    Then HTTP yanit kodu 200 olmalidir
    And veritabaninda "auth.login" aksiyonlu audit log kaydi bulunmalidir
