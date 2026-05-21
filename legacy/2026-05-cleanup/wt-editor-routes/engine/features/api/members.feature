@api @members @TS-15
Feature: Proje Uyeleri
  Projelere uyeler eklenir, roller atanir ve uyeler cikarilir.

  Arka plan: Proje hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus

  # -- TC-1501 --
  @high @positive @TC-1501
  Scenario: Projeye yeni uye eklenir
    Given baska bir kullanici mevcut
    When kullanici "operator" roluyle projeye eklenir
    Then HTTP yanit kodu 201 olmalidir
    And yanit "role" alani "operator" olmalidir

  # -- TC-1502 --
  @high @positive @TC-1502
  Scenario: Proje uyesi kaldirilir
    Given projede bir uye mevcut
    When uye projeden cikarilir
    Then HTTP yanit kodu 204 olmalidir
    And uye listesinde gorulmemelidir

  # -- TC-1503 --
  @medium @positive @TC-1503
  Scenario: Rol belirtilmezse varsayilan viewer atanir
    Given baska bir kullanici mevcut
    When kullanici rol belirtilmeden projeye eklenir
    Then HTTP yanit kodu 201 olmalidir
    And yanit "role" alani "viewer" olmalidir
