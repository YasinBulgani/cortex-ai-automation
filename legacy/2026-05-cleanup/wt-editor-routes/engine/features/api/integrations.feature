@api @integrations @TS-13
Feature: Entegrasyonlar
  Harici araclar (Jira, Azure, TestRail) ile
  entegrasyon kayitlari olusturulur ve senkronize edilir.

  Arka plan: Proje hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus

  # -- TC-1301 --
  @medium @positive @TC-1301
  Scenario: Yeni entegrasyon kaydi olusturulur
    When "jira" provider'i ile entegrasyon olusturulur
    Then HTTP yanit kodu 201 olmalidir
    And yanit "provider" alani "jira" olmalidir

  # -- TC-1302 --
  @medium @positive @TC-1302
  Scenario: Entegrasyon sync islemi last_sync_at gunceller
    Given projede bir entegrasyon olusturulmus
    When entegrasyon sync istegi gonderilir
    Then HTTP yanit kodu 200 olmalidir
    And yanit "last_sync_at" alani dolu olmalidir

  # -- TC-1303 --
  @low @boundary @TC-1303
  Scenario: Bos provider ile entegrasyon olusturulamaz
    When "" provider'i ile entegrasyon olusturma istegi gonderilir
    Then HTTP yanit kodu 422 olmalidir
