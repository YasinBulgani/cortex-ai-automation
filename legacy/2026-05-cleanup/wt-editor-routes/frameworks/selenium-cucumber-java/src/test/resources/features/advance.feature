@all
Feature: advance

  Background: Giris
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'


  Scenario: Avans_Talebi_Zorunlu_Alanlar_Kontrol
    When I see the element 'anaSayfaAvansUcNoktaButon'
    And I click on "anaSayfaAvansUcNoktaButon"
    And I see the element 'anaSayfaAvansTalepEtButon'
    And I click on "anaSayfaAvansTalepEtButon"
    And I see the element 'avansTalepEtSayfasıTutarInput'
    And I clear the input 'avansTalepEtSayfasıTutarInput'
    And I see the element 'avansTalepEtSayfasıTalepEtButon'
    And I click on 'avansTalepEtSayfasıTalepEtButon'
    Then I see the element 'avansTalepEtSayfasıTutarInputZorunlulukKontrol'
    And I enter '@advanceAmount' into the input 'avansTalepEtSayfasıTutarInput'
    And I click on 'avansTalepEtSayfasıTalepEtButon'
    Then I see the element 'avanslarımSayfasıAvansOnayTaahhütnamesiIsaretlenmedıUyarı'


  Scenario: Avans_Arama_Filtreleme_Kontrol
    When I see the element 'anaSayfaAvansUcNoktaButon'
    And I click on "anaSayfaAvansUcNoktaButon"
    And I see the element 'anaSayfaAvansLarımButon'
    And I click on 'anaSayfaAvansLarımButon'
    And I see the element 'avanslarımSayfasıAramaInput'
    And I click on 'avanslarımSayfasıAramaInput'
    And I see the element 'avanslarımSayfasıAramaInput'
    And I enter "@advanceAmount" into the input "avanslarımSayfasıAramaInput"
    And I see the element 'avanslarımSayfasıAramaButon'
    And I click on 'avanslarımSayfasıAramaButon'
    And I see the element 'avanslarımSayfasıAvansTutarıFiltrelemeKontrolüTutarDegeri'
    Then I verify element 'avanslarımSayfasıAvansTutarıFiltrelemeKontrolüTutarDegeri' text is '@advanceAmount'
    When I click on 'avanslarımSayfasıFiltreTemizleAlanı'

  Scenario: Avans_Tarih_Filtreleme_Kontrol
    When I see the element 'anaSayfaAvansUcNoktaButon'
    And I click on "anaSayfaAvansUcNoktaButon"
    And I see the element 'anaSayfaAvansLarımButon'
    And I click on 'anaSayfaAvansLarımButon'
    And I see the element 'avanslarımSayfasıTarihFiltrelemeInput'
    And I click on 'avanslarımSayfasıTarihFiltrelemeInput'
    And I clear the input 'avanslarımSayfasıTarihFiltrelemeInput'
    And I enter '@dateFilterValue' into the input 'avanslarımSayfasıTarihFiltrelemeInput'
    And I see the element 'avanslarımSayfasıTarihFiltrelemeDateTimePicker'
    And I click on 'avanslarımSayfasıTarihFiltrelemeDateTimePicker'
    And I click on 'avanslarımSayfasıTarihFiltrelemeDateTimePicker'
    And I see the element 'avanslarımSayfasıTarihFiltrelemeKontrolüTarihDegeri'
    Then I verify element "avanslarımSayfasıTarihFiltrelemeKontrolüTarihDegeri" text is "@dateControlValue"

  Scenario: Avans_Kutu_Gorunumu_Liste_Gorunumu_Kontrol
    When I see the element 'anaSayfaAvansUcNoktaButon'
    And I click on "anaSayfaAvansUcNoktaButon"
    And I see the element 'anaSayfaAvansLarımButon'
    And I click on 'anaSayfaAvansLarımButon'
    And I see the element 'avanslarımSayfasıListeGörünümüButon'
    And I click on 'avanslarımSayfasıListeGörünümüButon'
    Then I see the element 'avanslarımSayfasıAvanslarListeGorunumundeKontrol'
    And I see the element 'avanslarımSayfasıKutuGörünümüButon'
    And I click on 'avanslarımSayfasıKutuGörünümüButon'
    Then I don't see element 'avanslarımSayfasıAvanslarListeGorunumundeKontrol'

  Scenario: Avans_Talep_Avas_Onay_Taahhütnamesi_Kontrol
    When I see the element 'anaSayfaAvansUcNoktaButon'
    And I click on "anaSayfaAvansUcNoktaButon"
    And I see the element 'anaSayfaAvansTalepEtButon'
    And I click on "anaSayfaAvansTalepEtButon"
    And I see the element 'avansTalepEtSayfasıTutarInput'
    And I clear the input 'avansTalepEtSayfasıTutarInput'
    And I enter '@advanceAmount' into the input 'avansTalepEtSayfasıTutarInput'
    And I see the element 'avanslarımSayfasıAvansOnayTaahhütnamesiCheckBox'
    And I click on 'avanslarımSayfasıAvansOnayTaahhütnamesiCheckBox'
    Then I verify element 'avansOnayTaahhütnamesiKontrolText' text is '@advanceCommitment'

  # =====================================================
  # NEGATIF SENARYOLAR
  # =====================================================

  Scenario: Avans_Talebi_Sıfır_Tutar_Girişi_Kontrolü
    When I click on 'anaSayfaAvansUcNoktaButon'
    And I click on 'anaSayfaAvansTalepEtButon'
    And I clear the input 'avansTalepEtSayfasıTutarInput'
    And I enter '0' into the input 'avansTalepEtSayfasıTutarInput'
    And I click on 'avansTalepEtSayfasıTalepEtButon'
    Then I see the element 'avansTalepEtSayfasıTutarInputZorunlulukKontrol'

  Scenario: Avans_Talebi_Harf_Girişi_Tutar_Alanı_Kontrolü
    When I click on 'anaSayfaAvansUcNoktaButon'
    And I click on 'anaSayfaAvansTalepEtButon'
    And I clear the input 'avansTalepEtSayfasıTutarInput'
    And I enter 'abc' into the input 'avansTalepEtSayfasıTutarInput'
    And I click on 'avansTalepEtSayfasıTalepEtButon'
    Then I see the element 'avansTalepEtSayfasıTutarInputZorunlulukKontrol'
