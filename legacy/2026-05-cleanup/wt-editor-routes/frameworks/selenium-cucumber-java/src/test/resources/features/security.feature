@all
Feature: security

  # =====================================================
  # XSS ve INJECTION TESTLERI
  # =====================================================

  Scenario: Login_XSS_Injection_Denemesi
    Given I open the application url from config 'url'
    And I enter '@xssPayload' into the input 'GirisAlanıInput'
    And I enter '@xssPayload' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I see the element 'girisHataMesajıText'

  Scenario: Login_SQL_Injection_Denemesi
    Given I open the application url from config 'url'
    And I enter '@sqlPayload' into the input 'GirisAlanıInput'
    And I enter '@sqlPayload' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I see the element 'girisHataMesajıText'

  # =====================================================
  # BOUNDARY TESTLERI
  # =====================================================

  Scenario: İzin_Açıklama_Alanı_Uzun_Metin_Girişi
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I enter '@longText' into the input 'izinTalepEtSayfasıİzinAçıklaması'
    Then I see the element 'izinTalepEtSayfasıİzinAçıklaması'

  Scenario: İzin_Açıklama_Alanı_Özel_Karakter_Girişi
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'
    When I click on 'anaSayfaIzinUcNoktaButon'
    And I click on 'anaSayfaIzinlerimButon'
    And I click on 'izinlerimSayfasıİzinTalepEtButon'
    And I enter '@specialChars' into the input 'izinTalepEtSayfasıİzinAçıklaması'
    Then I see the element 'izinTalepEtSayfasıİzinAçıklaması'

  Scenario: Yetkisiz_Sayfa_Erişim_Kontrolü
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'
    Given I open the application url '@unauthorizedUrl'
    Then I don't see element 'onayBekleyenlerSayfasıBaslık'
