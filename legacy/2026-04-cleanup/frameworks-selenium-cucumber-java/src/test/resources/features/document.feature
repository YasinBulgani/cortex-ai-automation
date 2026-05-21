@all
Feature: document

  Background: Giris
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'

  Scenario: Belgelerim_Sayfasına_Erişim
    When I click on 'anaSayfaBelgelerMenuButon'
    And I click on 'anaSayfaBelgelerimButon'
    Then I see the element 'belgelerimSayfasıBaslık'

  Scenario: PDF_Dosya_Yükleme
    When I click on 'anaSayfaBelgelerMenuButon'
    And I click on 'anaSayfaBelgelerimButon'
    And I click on 'belgelerimSayfasıYuklemeButon'
    And I upload the file 'pdf' to the input 'belgelerimSayfasıDosyaInput'
    And I click on 'belgelerimSayfasıKaydetButon'
    Then I see the element 'belgelerimSayfasıYuklemeBasariliText'

  Scenario: DOCX_Dosya_Yükleme
    When I click on 'anaSayfaBelgelerMenuButon'
    And I click on 'anaSayfaBelgelerimButon'
    And I click on 'belgelerimSayfasıYuklemeButon'
    And I upload the file 'docx' to the input 'belgelerimSayfasıDosyaInput'
    And I click on 'belgelerimSayfasıKaydetButon'
    Then I see the element 'belgelerimSayfasıYuklemeBasariliText'

  Scenario: Belge_Arama_Filtreleme
    When I click on 'anaSayfaBelgelerMenuButon'
    And I click on 'anaSayfaBelgelerimButon'
    And I enter '@documentSearchKeyword' into the input 'belgelerimSayfasıAramaInput'
    And I click on 'belgelerimSayfasıAramaButon'
    Then I see the element 'belgelerimSayfasıIlkBelgeText'

  Scenario: Yüklenen_Belge_Silme
    When I click on 'anaSayfaBelgelerMenuButon'
    And I click on 'anaSayfaBelgelerimButon'
    And I click on 'belgelerimSayfasıIlkBelgeUcNoktaButon'
    And I click on 'belgelerimSayfasıSilButon'
    And I wait for element 'belgelerimSayfasıSilmeOnayButon' to be clickable
    And I click on 'belgelerimSayfasıSilmeOnayButon'
    Then I see the element 'belgelerimSayfasıSilmeBasariliText'
