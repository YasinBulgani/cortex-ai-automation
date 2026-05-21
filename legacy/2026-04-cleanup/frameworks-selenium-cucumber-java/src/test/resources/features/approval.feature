@all
Feature: approval

  Scenario: Yönetici_Girişi_Ve_Bekleyen_Talepler_Listesi
    Given I open the application url from config 'url'
    And I enter '@managerUsername' into the input 'GirisAlanıInput'
    And I enter '@managerPassword' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@managerExpectedName'
    When I click on 'onayBekleyenlerMenuButon'
    Then I see the element 'onayBekleyenlerSayfasıBaslık'

  Scenario: İzin_Talebini_Onaylama
    Given I open the application url from config 'url'
    And I enter '@managerUsername' into the input 'GirisAlanıInput'
    And I enter '@managerPassword' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@managerExpectedName'
    When I click on 'onayBekleyenlerMenuButon'
    And I see the element 'onayBekleyenlerIlkTalepSatırı'
    And I click on 'onayBekleyenlerIlkTalepDetayButon'
    And I see the element 'talepDetayOnaylaButon'
    And I click on 'talepDetayOnaylaButon'
    And I wait for element 'talepDetayOnayOnayButon' to be clickable
    And I click on 'talepDetayOnayOnayButon'
    Then I see the element 'talepOnayBasariliText'

  Scenario: İzin_Talebini_Reddetme
    Given I open the application url from config 'url'
    And I enter '@managerUsername' into the input 'GirisAlanıInput'
    And I enter '@managerPassword' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@managerExpectedName'
    When I click on 'onayBekleyenlerMenuButon'
    And I see the element 'onayBekleyenlerIlkTalepSatırı'
    And I click on 'onayBekleyenlerIlkTalepDetayButon'
    And I see the element 'talepDetayReddetButon'
    And I click on 'talepDetayReddetButon'
    And I enter 'Otomasyon test reddi' into the input 'talepDetayRedNedeniInput'
    And I wait for element 'talepDetayRedOnayButon' to be clickable
    And I click on 'talepDetayRedOnayButon'
    Then I see the element 'talepRedBasariliText'

  Scenario: Onay_Geçmişi_Görüntüleme
    Given I open the application url from config 'url'
    And I enter '@managerUsername' into the input 'GirisAlanıInput'
    And I enter '@managerPassword' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@managerExpectedName'
    When I click on 'onayGecmisiMenuButon'
    Then I see the element 'onayGecmisiSayfasıBaslık'
    And I see the element 'onayGecmisiIlkKayıtSatırı'
