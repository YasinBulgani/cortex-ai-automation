@all
Feature: profile

  Background: Giris
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'

  Scenario: Profil_Sayfasına_Erişim_Kontrolü
    When I click on 'AnaSayfaKullanıcıAdıText'
    And I click on 'profilSayfasıButon'
    Then I see the element 'profilSayfasıAdSoyadText'

  Scenario: Profil_Bilgileri_Görüntüleme
    When I click on 'AnaSayfaKullanıcıAdıText'
    And I click on 'profilSayfasıButon'
    Then I see the element 'profilSayfasıAdSoyadText'
    And I see the element 'profilSayfasıSicilNoText'
    And I see the element 'profilSayfasıDepartmanText'

  Scenario: Profil_Fotoğrafı_Alanı_Görünürlük
    When I click on 'AnaSayfaKullanıcıAdıText'
    And I click on 'profilSayfasıButon'
    Then I see the element 'profilSayfasıFotoğrafAlanı'

  Scenario: Profil_Sayfasından_Ana_Sayfaya_Dönüş
    When I click on 'AnaSayfaKullanıcıAdıText'
    And I click on 'profilSayfasıButon'
    Then I see the element 'profilSayfasıAdSoyadText'
    When I click on 'anaSayfaLogoButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'
