@api @projects @TS-02
Feature: Proje Yonetimi
  Test ekipleri projelerini olusturur, listeler ve yonetir.
  Proje ismi zorunludur ve projeler olusturma tarihine gore ters sirada listelenir.

  Arka plan: Oturum acilmis
    Given kullanici oturum acmis

  # -- TC-0201 --
  @critical @positive @TC-0201
  Scenario: Gecerli bilgilerle yeni proje olusturma
    When "Test Projesi" ismi ve "Aciklama" ile proje olusturma istegi gonderilir
    Then HTTP yanit kodu 201 olmalidir
    And yanit "name" alani "Test Projesi" olmalidir
    And yanit "archived" alani false olmalidir

  # -- TC-0202 --
  @high @boundary @TC-0202
  Scenario: Bos isim ile proje olusturulamaz
    When "" ismi ile proje olusturma istegi gonderilir
    Then HTTP yanit kodu 422 olmalidir

  # -- TC-0203 --
  @medium @boundary @TC-0203
  Scenario: Tek karakterli proje ismi kabul edilir
    When "A" ismi ile proje olusturma istegi gonderilir
    Then HTTP yanit kodu 201 olmalidir

  # -- TC-0204 --
  @low @boundary @TC-0204
  Scenario: 200 karakterden uzun proje ismi reddedilir
    When 201 karakter uzunlugunda isim ile proje olusturma istegi gonderilir
    Then HTTP yanit kodu 422 olmalidir

  # -- TC-0205 --
  @medium @positive @TC-0205
  Scenario: Projeler olusturma tarihine gore ters sirada listelenir
    Given "Proje-Eski" isimli proje olusturulmus
    And "Proje-Yeni" isimli proje olusturulmus
    When proje listesi istenir
    Then listenin ilk elemani "Proje-Yeni" olmalidir

  # -- TC-0206 --
  @high @negative @TC-0206
  Scenario: Var olmayan proje ID ile erisim 404 doner
    When var olmayan proje ID ile dashboard istegi gonderilir
    Then HTTP yanit kodu 404 olmalidir
