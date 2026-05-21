@all
Feature: expense

  Background: Giris
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'

  Scenario: Masraflarım_Sayfasına_Erişim
    When I click on 'anaSayfaMasrafUcNoktaButon'
    And I click on 'anaSayfaMasraflarımButon'
    Then I see the element 'masraflarımSayfasıBaslık'

  Scenario: Masraf_Talebi_Oluşturma_Silme
    When I click on 'anaSayfaMasrafUcNoktaButon'
    And I click on 'anaSayfaMasrafTalepEtButon'
    And I click on 'masrafTalepSayfasıKategoriSelectBox'
    And I enter '@expenseCategory' into the input 'masrafTalepSayfasıKategoriFiltreInput'
    And I press the 'enter' key
    And I clear the input 'masrafTalepSayfasıTutarInput'
    And I enter '@expenseAmount' into the input 'masrafTalepSayfasıTutarInput'
    And I enter '+-masrafAciklama' into the input 'masrafTalepSayfasıAciklamaInput'
    And I upload the file 'pdf' to the input 'masrafTalepSayfasıDosyaYuklemeInput'
    And I click on 'masrafTalepSayfasıKaydetButon'
    Then I see the element 'masrafTalepSayfasıBasariliText'
    And I refresh the page
    And I enter '+-masrafAciklama' into the input 'masraflarımSayfasıAramaInput'
    Then I verify element 'masraflarımSayfasıIlkMasrafText' text is '+-masrafAciklama'
    And I click on 'masraflarımSayfasıIlkMasrafUcNoktaButon'
    And I click on 'masraflarımSayfasıSilButon'
    And I wait for element 'masraflarımSayfasıSilmeOnayButon' to be clickable
    And I click on 'masraflarımSayfasıSilmeOnayButon'
    Then I see the element 'masraflarımSayfasıSilmeBasariliText'

  Scenario: Masraf_Arama_Filtreleme
    When I click on 'anaSayfaMasrafUcNoktaButon'
    And I click on 'anaSayfaMasraflarımButon'
    And I enter '@expenseAmount' into the input 'masraflarımSayfasıAramaInput'
    And I click on 'masraflarımSayfasıAramaButon'
    Then I see the element 'masraflarımSayfasıIlkMasrafText'

  Scenario: Masraf_Talebi_Zorunlu_Alan_Kontrolü
    When I click on 'anaSayfaMasrafUcNoktaButon'
    And I click on 'anaSayfaMasrafTalepEtButon'
    And I click on 'masrafTalepSayfasıKaydetButon'
    Then I see the element 'masrafTalepSayfasıZorunluAlanUyarı'

  Scenario: Masraf_Talebi_Sıfır_Tutar_Kontrolü
    When I click on 'anaSayfaMasrafUcNoktaButon'
    And I click on 'anaSayfaMasrafTalepEtButon'
    And I clear the input 'masrafTalepSayfasıTutarInput'
    And I enter '0' into the input 'masrafTalepSayfasıTutarInput'
    And I click on 'masrafTalepSayfasıKaydetButon'
    Then I see the element 'masrafTalepSayfasıZorunluAlanUyarı'
