@api @scenarios @TS-03
Feature: Senaryo Yonetimi
  Senaryolar olusturulur, guncellenir, versiyonlanir,
  aranir ve toplu islem yapilir.

  Arka plan: Proje hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus

  # -- TC-0301 --
  @critical @positive @TC-0301
  Scenario: Gecerli bilgilerle yeni senaryo olusturma
    When "Login Testi" baslikli yeni senaryo olusturulur
    Then HTTP yanit kodu 201 olmalidir
    And yanit "status" alani "draft" olmalidir
    And yanit "current_version" alani 1 olmalidir

  # -- TC-0302 --
  @high @boundary @TC-0302
  Scenario: Bos baslikli senaryo olusturulamaz
    When "" baslikli yeni senaryo olusturulur
    Then HTTP yanit kodu 422 olmalidir

  # -- TC-0303 --
  @critical @positive @TC-0303
  Scenario: Senaryo guncellendiginde versiyon numarasi artar
    Given projede bir senaryo olusturulmus
    When senaryonun basligi "Guncellenmis Baslik" olarak guncellenir
    Then yanit "current_version" alani 2 olmalidir
    And versiyon listesinde eski baslik versiyon 1 olarak saklanmalidir

  # -- TC-0304 --
  @high @negative @TC-0304
  Scenario: Farkli projeye ait senaryoya erisilemez
    Given baska bir projede bir senaryo olusturulmus
    When bu senaryoya mevcut proje uzerinden erisim denenir
    Then HTTP yanit kodu 404 olmalidir

  # -- TC-0305 --
  @medium @positive @TC-0305
  Scenario: Senaryolar baslik ile aranabilir
    Given projede "Login Akisi" baslikli senaryo olusturulmus
    And projede "Odeme Akisi" baslikli senaryo olusturulmus
    When senaryolar "Login" arama terimiyle filtrelenir
    Then sonuc listesinde yalnizca "Login" iceren senaryolar bulunmalidir

  # -- TC-0306 --
  @high @positive @TC-0306
  Scenario: Birden fazla senaryo toplu silinebilir
    Given projede 3 senaryo olusturulmus
    When ilk 2 senaryonun ID'leri ile toplu silme istegi gonderilir
    Then HTTP yanit kodu 204 olmalidir
    And senaryo listesinde yalnizca silinmeyen senaryo kalmalidir

  # -- TC-0307 --
  @high @negative @TC-0307
  Scenario: Toplu silmede farkli projeye ait ID'ler yok sayilir
    Given baska bir projede bir senaryo olusturulmus
    When o senaryonun ID'si ile mevcut projede toplu silme denenir
    Then diger projenin senaryosu silinmemis olmalidir

  # -- TC-0308 --
  @medium @positive @TC-0308
  Scenario: Iki versiyon arasindaki farklar dogru raporlanir
    Given projede bir senaryo olusturulmus
    And senaryo basligi guncellenmis
    When versiyon 1 ve versiyon 2 karsilastirilir
    Then diff sonucunda "title_changed" true olmalidir

  # -- TC-0309 --
  @medium @negative @TC-0309
  Scenario: Var olmayan versiyon numarasi ile diff 404 doner
    Given projede bir senaryo olusturulmus
    When versiyon 1 ve versiyon 999 karsilastirilir
    Then HTTP yanit kodu 404 olmalidir
