@all
Feature: dashboard

  Background: Giris
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'

  # =====================================================
  # ANA SAYFA DOGRULAMA
  # =====================================================

  Scenario: Ana_Sayfa_İzin_Widget_Görünürlük_Kontrolü
    Then I see the element 'anaSayfaIzinWidget'
    And I see the element 'anaSayfaIzinUcNoktaButon'

  Scenario: Ana_Sayfa_Avans_Widget_Görünürlük_Kontrolü
    Then I see the element 'anaSayfaAvansWidget'
    And I see the element 'anaSayfaAvansUcNoktaButon'

  Scenario: Ana_Sayfa_İzin_Menü_Erişim_Kontrolü
    When I click on 'anaSayfaIzinUcNoktaButon'
    Then I see the element 'anaSayfaIzinlerimButon'
    And I see the element 'anaSayfaIzinTalepEtButon'

  Scenario: Ana_Sayfa_Avans_Menü_Erişim_Kontrolü
    When I click on 'anaSayfaAvansUcNoktaButon'
    Then I see the element 'anaSayfaAvansLarımButon'
    And I see the element 'anaSayfaAvansTalepEtButon'

  Scenario: Sayfa_Yenileme_Sonrası_Oturum_Devam_Kontrolü
    And I refresh the page
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'
