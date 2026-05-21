@api @test-data @TS-12
Feature: Test Verisi Yonetimi
  Veri setleri olusturulur, senaryolara parametrik olarak
  baglanir ve adimlar genisletilir.

  Arka plan: Proje hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus

  # -- TC-1201 --
  @high @positive @TC-1201
  Scenario: Kolonlar ve satirlarla test veri seti olusturulur
    When asagidaki yapiyla test veri seti olusturulur:
      | name     | columns          | rows                              |
      | Login    | username,password | user1:pass1,user2:pass2           |
    Then HTTP yanit kodu 201 olmalidir
    And yanit "name" alani "Login" olmalidir

  # -- TC-1202 --
  @high @positive @TC-1202
  Scenario: Senaryoya veri seti parametreleri baglanir
    Given projede bir senaryo ve veri seti olusturulmus
    When senaryo ile veri seti parametre eslesimiyle baglanir
    Then HTTP yanit kodu 201 olmalidir

  # -- TC-1203 --
  @high @positive @TC-1203
  Scenario: Veri satirlari ile senaryo adimlari genisletilir
    Given senaryo adimlari "{{kullanici}}" yer tutucusu icerir
    And veri seti baglanmis
    When genisletilmis senaryo istenir
    Then her veri satiri icin adimlar genisletilmis donmelidir
    And "{{kullanici}}" yerine gercek degerler yerlestirilmis olmalidir

  # -- TC-1204 --
  @medium @negative @TC-1204
  Scenario: Var olmayan veri seti ID ile baglama 404 doner
    Given projede bir senaryo mevcut
    When var olmayan veri seti ID ile baglama istegi gonderilir
    Then HTTP yanit kodu 404 olmalidir
