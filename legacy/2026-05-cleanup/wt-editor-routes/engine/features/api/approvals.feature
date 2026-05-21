@api @approvals @TS-05
Feature: Onay Kuyrugu
  AI taslaklari onay kuyruguna duser, yetkili kullanici
  taslaklari onaylar veya reddeder.

  Arka plan: Proje ve onay kaydi hazir
    Given kullanici oturum acmis
    And bir test projesi olusturulmus

  # -- TC-0501 --
  @high @positive @TC-0501
  Scenario: Projeye ait onaylar listelenir
    Given projede onay kayitlari mevcut
    When onay listesi istenir
    Then HTTP yanit kodu 200 olmalidir
    And yanit listesinde her onay "id", "title", "status" alanlarini icermelidir

  # -- TC-0502 --
  @critical @positive @TC-0502
  Scenario: Bekleyen onay kabul edilir
    Given projede "pending" statusunde bir onay mevcut
    When onay icin "approved" karari verilir
    Then HTTP yanit kodu 200 olmalidir
    And onay statusu "approved" olmalidir
    And onay "decided_at" alani dolu olmalidir

  # -- TC-0503 --
  @high @positive @TC-0503
  Scenario: Bekleyen onay reddedilir
    Given projede "pending" statusunde bir onay mevcut
    When onay icin "rejected" karari verilir
    Then HTTP yanit kodu 200 olmalidir
    And onay statusu "rejected" olmalidir
    And onay "decided_at" alani dolu olmalidir

  # -- TC-0504 --
  @medium @negative @TC-0504
  Scenario: Var olmayan onay ID ile karar 404 doner
    When var olmayan onay ID ile karar istegi gonderilir
    Then HTTP yanit kodu 404 olmalidir
