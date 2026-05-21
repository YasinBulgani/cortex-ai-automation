@all
Feature: absence

  Background: Giris
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'

  # =====================================================
  # POZITIF SENARYOLAR - Izin Olusturma ve Silme
  # =====================================================

  Scenario: Yıllık_İzin_Oluşturma_Silme_Kontrol
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıIzinTipiSelectBox'
    And I enter '@absenceTypeYearlyLeave' into the input 'izinTalepEtSayfasıIzinTipiFiltreInput'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I clear the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I enter 'dateformatnow dd/MM/yyyy - dd/MM/yyyy' into the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I press the 'enter' key
    And I enter '+-izinAciklama' into the input 'izinTalepEtSayfasıİzinAçıklaması'
    And I click on 'izinTalepEtSayfasıİzinOnayFormuCheckBox'
    Then I see the element 'izinTalepEtSayfasıİzinOnayFormuModal'
    And I press the 'escape' key
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    And I see the element 'izinTalepEtSayfasıİzinTalebiİşlemBaşarılıText'
    And I refresh the page
    And I enter '+-izinAciklama' into the input 'izinlerimSayfasıİzinAramaInput'
    Then I verify element 'izinlerimSayfasıTalepEdilenIzınText' text is '+-izinAciklama'
    And I click on 'izinlerimSayfasıTalepEdilenIzınUcNoktaButon'
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilButon'
    And I wait for element 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon' to be clickable
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon'
    Then I see the element 'izinlerimSayfasıTalepEdilenIzınSilmeIslemBasarılıUyarıText'

  Scenario: Evlilik_İzni_Oluşturma_Silme_Kontrol
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıIzinTipiSelectBox'
    And I enter '@absenceTypeMarriageLeave' into the input 'izinTalepEtSayfasıIzinTipiFiltreInput'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I clear the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I enter 'dateformatnow dd/MM/yyyy - dd/MM/yyyy +2' into the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I press the 'enter' key
    And I enter '+-izinAciklama' into the input 'izinTalepEtSayfasıİzinAçıklaması'
    And I upload the file 'pdf' to the input 'izinTalepEtSayfasıDosyaYüklemeAlanıInput'
    And I click on 'izinTalepEtSayfasıİzinOnayFormuCheckBox'
    Then I see the element 'izinTalepEtSayfasıİzinOnayFormuModal'
    And I press the 'escape' key
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    And I see the element 'izinTalepEtSayfasıİzinTalebiİşlemBaşarılıText'
    And I refresh the page
    And I enter '+-izinAciklama' into the input 'izinlerimSayfasıİzinAramaInput'
    Then I verify element 'izinlerimSayfasıTalepEdilenIzınText' text is '+-izinAciklama'
    And I click on 'izinlerimSayfasıTalepEdilenIzınUcNoktaButon'
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilButon'
    And I wait for element 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon' to be clickable
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon'
    Then I see the element 'izinlerimSayfasıTalepEdilenIzınSilmeIslemBasarılıUyarıText'

  Scenario: Vefat_İzni_Birinci_Derece_Oluşturma_Silme_Kontrol
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıIzinTipiSelectBox'
    And I enter '@absenceTypeDeathLeaveFirstDegree' into the input 'izinTalepEtSayfasıIzinTipiFiltreInput'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I clear the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I enter 'dateformatnow dd/MM/yyyy - dd/MM/yyyy +2' into the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I press the 'enter' key
    And I enter '+-izinAciklama' into the input 'izinTalepEtSayfasıİzinAçıklaması'
    And I upload the file 'pdf' to the input 'izinTalepEtSayfasıDosyaYüklemeAlanıInput'
    And I click on 'izinTalepEtSayfasıİzinOnayFormuCheckBox'
    Then I see the element 'izinTalepEtSayfasıİzinOnayFormuModal'
    And I press the 'escape' key
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    And I see the element 'izinTalepEtSayfasıİzinTalebiİşlemBaşarılıText'
    And I refresh the page
    And I enter '+-izinAciklama' into the input 'izinlerimSayfasıİzinAramaInput'
    Then I verify element 'izinlerimSayfasıTalepEdilenIzınText' text is '+-izinAciklama'
    And I click on 'izinlerimSayfasıTalepEdilenIzınUcNoktaButon'
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilButon'
    And I wait for element 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon' to be clickable
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon'
    Then I see the element 'izinlerimSayfasıTalepEdilenIzınSilmeIslemBasarılıUyarıText'

  Scenario: Vefat_İzni_İkinci_Derece_Oluşturma_Silme_Kontrol
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıIzinTipiSelectBox'
    And I enter '@absenceTypeDeathLeaveSecondDegree' into the input 'izinTalepEtSayfasıIzinTipiFiltreInput'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I clear the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I enter 'dateformatnow dd/MM/yyyy - dd/MM/yyyy' into the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I press the 'enter' key
    And I enter '+-izinAciklama' into the input 'izinTalepEtSayfasıİzinAçıklaması'
    And I upload the file 'pdf' to the input 'izinTalepEtSayfasıDosyaYüklemeAlanıInput'
    And I click on 'izinTalepEtSayfasıİzinOnayFormuCheckBox'
    Then I see the element 'izinTalepEtSayfasıİzinOnayFormuModal'
    And I press the 'escape' key
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    And I see the element 'izinTalepEtSayfasıİzinTalebiİşlemBaşarılıText'
    And I refresh the page
    And I enter '+-izinAciklama' into the input 'izinlerimSayfasıİzinAramaInput'
    Then I verify element 'izinlerimSayfasıTalepEdilenIzınText' text is '+-izinAciklama'
    And I click on 'izinlerimSayfasıTalepEdilenIzınUcNoktaButon'
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilButon'
    And I wait for element 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon' to be clickable
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon'
    Then I see the element 'izinlerimSayfasıTalepEdilenIzınSilmeIslemBasarılıUyarıText'

  Scenario: Sınav_İzni_Oluşturma_Silme_Kontrol
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıIzinTipiSelectBox'
    And I enter '@absenceTypeExamLeave' into the input 'izinTalepEtSayfasıIzinTipiFiltreInput'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I clear the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I enter 'dateformatnow dd/MM/yyyy - dd/MM/yyyy' into the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I press the 'enter' key
    And I enter '+-izinAciklama' into the input 'izinTalepEtSayfasıİzinAçıklaması'
    And I upload the file 'pdf' to the input 'izinTalepEtSayfasıDosyaYüklemeAlanıInput'
    And I click on 'izinTalepEtSayfasıİzinOnayFormuCheckBox'
    Then I see the element 'izinTalepEtSayfasıİzinOnayFormuModal'
    And I press the 'escape' key
    And I click on 'izinTalepEtSayfasıSınavİzniBilgilendirmeFormuButon'
    Then I see the element 'izinTalepEtSayfasıİzinBilgilendirmeFormuModal'
    And I press the 'escape' key
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    And I see the element 'izinTalepEtSayfasıİzinTalebiİşlemBaşarılıText'
    And I refresh the page
    And I enter '+-izinAciklama' into the input 'izinlerimSayfasıİzinAramaInput'
    Then I verify element 'izinlerimSayfasıTalepEdilenIzınText' text is '+-izinAciklama'
    And I click on 'izinlerimSayfasıTalepEdilenIzınUcNoktaButon'
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilButon'
    And I wait for element 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon' to be clickable
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon'
    Then I see the element 'izinlerimSayfasıTalepEdilenIzınSilmeIslemBasarılıUyarıText'

  Scenario: Sağlık_Raporu_İzni_Oluşturma_Silme_Kontrol
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıIzinTipiSelectBox'
    And I enter '@absenceTypeMedicalReportLeave' into the input 'izinTalepEtSayfasıIzinTipiFiltreInput'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I clear the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I enter 'dateformatnow dd/MM/yyyy - dd/MM/yyyy +2' into the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I press the 'enter' key
    And I enter '+-izinAciklama' into the input 'izinTalepEtSayfasıİzinAçıklaması'
    And I upload the file 'pdf' to the input 'izinTalepEtSayfasıDosyaYüklemeAlanıInput'
    And I click on 'izinTalepEtSayfasıİzinOnayFormuCheckBox'
    Then I see the element 'izinTalepEtSayfasıİzinOnayFormuModal'
    And I press the 'escape' key
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    And I see the element 'izinTalepEtSayfasıİzinTalebiİşlemBaşarılıText'
    And I refresh the page
    And I enter '+-izinAciklama' into the input 'izinlerimSayfasıİzinAramaInput'
    Then I verify element 'izinlerimSayfasıTalepEdilenIzınText' text is '+-izinAciklama'
    And I click on 'izinlerimSayfasıTalepEdilenIzınUcNoktaButon'
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilButon'
    And I wait for element 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon' to be clickable
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon'
    Then I see the element 'izinlerimSayfasıTalepEdilenIzınSilmeIslemBasarılıUyarıText'

  Scenario: Refakatçi_İzni_Oluşturma_Silme_Kontrol
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıIzinTipiSelectBox'
    And I enter '@absenceTypeCompanionLeave' into the input 'izinTalepEtSayfasıIzinTipiFiltreInput'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I clear the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I enter 'dateformatnow dd/MM/yyyy - dd/MM/yyyy' into the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I press the 'enter' key
    And I enter '+-izinAciklama' into the input 'izinTalepEtSayfasıİzinAçıklaması'
    And I upload the file 'pdf' to the input 'izinTalepEtSayfasıDosyaYüklemeAlanıInput'
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    And I see the element 'izinTalepEtSayfasıİzinTalebiİşlemBaşarılıText'
    And I refresh the page
    And I enter '+-izinAciklama' into the input 'izinlerimSayfasıİzinAramaInput'
    Then I verify element 'izinlerimSayfasıTalepEdilenIzınText' text is '+-izinAciklama'
    And I click on 'izinlerimSayfasıTalepEdilenIzınUcNoktaButon'
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilButon'
    And I wait for element 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon' to be clickable
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon'
    Then I see the element 'izinlerimSayfasıTalepEdilenIzınSilmeIslemBasarılıUyarıText'

  Scenario: Taşınma_İzni_Oluşturma_Silme_Kontrol
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıIzinTipiSelectBox'
    And I enter '@absenceTypeRelocationLeave' into the input 'izinTalepEtSayfasıIzinTipiFiltreInput'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I clear the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I enter 'dateformatnow dd/MM/yyyy - dd/MM/yyyy' into the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I press the 'enter' key
    And I enter '+-izinAciklama' into the input 'izinTalepEtSayfasıİzinAçıklaması'
    And I upload the file 'pdf' to the input 'izinTalepEtSayfasıDosyaYüklemeAlanıInput'
    And I click on 'izinTalepEtSayfasıİzinOnayFormuCheckBox'
    Then I see the element 'izinTalepEtSayfasıİzinOnayFormuModal'
    And I press the 'escape' key
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    And I see the element 'izinTalepEtSayfasıİzinTalebiİşlemBaşarılıText'
    And I refresh the page
    And I enter '+-izinAciklama' into the input 'izinlerimSayfasıİzinAramaInput'
    Then I verify element 'izinlerimSayfasıTalepEdilenIzınText' text is '+-izinAciklama'
    And I click on 'izinlerimSayfasıTalepEdilenIzınUcNoktaButon'
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilButon'
    And I wait for element 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon' to be clickable
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon'
    Then I see the element 'izinlerimSayfasıTalepEdilenIzınSilmeIslemBasarılıUyarıText'

  Scenario: Ücretsiz_İzin_Oluşturma_Silme_Kontrol
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıIzinTipiSelectBox'
    And I enter '@absenceTypeUnpaidLeave' into the input 'izinTalepEtSayfasıIzinTipiFiltreInput'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I clear the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I enter 'dateformatnow dd/MM/yyyy - dd/MM/yyyy' into the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I press the 'enter' key
    And I enter '+-izinAciklama' into the input 'izinTalepEtSayfasıİzinAçıklaması'
    And I upload the file 'pdf' to the input 'izinTalepEtSayfasıDosyaYüklemeAlanıInput'
    And I click on 'izinTalepEtSayfasıÜcretsizİzniBilgilendirmeButon'
    Then I see the element 'izinTalepEtSayfasıİzinBilgilendirmeFormuModal'
    And I press the 'escape' key
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    And I see the element 'izinTalepEtSayfasıİzinTalebiİşlemBaşarılıText'
    And I refresh the page
    And I enter '+-izinAciklama' into the input 'izinlerimSayfasıİzinAramaInput'
    Then I verify element 'izinlerimSayfasıTalepEdilenIzınText' text is '+-izinAciklama'
    And I click on 'izinlerimSayfasıTalepEdilenIzınUcNoktaButon'
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilButon'
    And I wait for element 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon' to be clickable
    And I click on 'izinlerimSayfasıTalepEdilenIzınSilmeOnayButon'
    Then I see the element 'izinlerimSayfasıTalepEdilenIzınSilmeIslemBasarılıUyarıText'

  # =====================================================
  # NEGATIF SENARYOLAR - Zorunlu Alan ve Validasyon
  # =====================================================

  Scenario: İzin_Talebi_Zorunlu_Alan_Kontrolü_Tüm_Alanlar_Boş
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    Then I see the element 'izinTalepEtSayfasıZorunluAlanlarUyarıText'

  Scenario: İzin_Talebi_Sadece_Tip_Seçili_Diğer_Alanlar_Boş
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıIzinTipiSelectBox'
    And I enter '@absenceTypeYearlyLeave' into the input 'izinTalepEtSayfasıIzinTipiFiltreInput'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    Then I see the element 'izinTalepEtSayfasıAçıklamaAlanıZorunlulukUyarısıInput'

  Scenario: İzin_Talebi_Açıklama_Girilmeden_Gönderim_Kontrolü
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I click on 'izinTalepEtSayfasıIzinTipiSelectBox'
    And I enter '@absenceTypeYearlyLeave' into the input 'izinTalepEtSayfasıIzinTipiFiltreInput'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I clear the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I enter 'dateformatnow dd/MM/yyyy - dd/MM/yyyy' into the input 'izinTalepEtSayfasıTarihAralığıSeçmeDatePicker'
    And I press the 'enter' key
    And I click on 'izinTalepEtSayfasıİzinTalepEtButon'
    Then I see the element 'izinTalepEtSayfasıAçıklamaAlanıZorunlulukUyarısıInput'
