@all
Feature: login

  # =====================================================
  # POZITIF SENARYOLAR
  # =====================================================

  Scenario: Başarılı_Giriş_Ve_Kullanıcı_Adı_Doğrulama
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'

  Scenario: Başarılı_Giriş_Sonrası_Çıkış_Yapma
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I verify element 'AnaSayfaKullanıcıAdıText' text is '@expectedName'
    When I click on 'AnaSayfaKullanıcıAdıText'
    And I click on 'cikisYapButon'
    Then I see the element 'GirisAlanıInput'

  # =====================================================
  # NEGATIF SENARYOLAR
  # =====================================================

  Scenario: Yanlış_Şifre_İle_Giriş_Denemesi
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I enter 'yanlisSifre123!' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I see the element 'girisHataMesajıText'

  Scenario: Yanlış_Kullanıcı_Adı_İle_Giriş_Denemesi
    Given I open the application url from config 'url'
    And I enter 'yanlisKullanici999' into the input 'GirisAlanıInput'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I see the element 'girisHataMesajıText'

  Scenario: Boş_Kullanıcı_Adı_İle_Giriş_Denemesi
    Given I open the application url from config 'url'
    And I enter '@password' into the input 'SifreAlanıInput'
    And I click on 'GirisYapButon'
    Then I see the element 'girisHataMesajıText'

  Scenario: Boş_Şifre_İle_Giriş_Denemesi
    Given I open the application url from config 'url'
    And I enter '@username' into the input 'GirisAlanıInput'
    And I click on 'GirisYapButon'
    Then I see the element 'girisHataMesajıText'

  Scenario: Her_İki_Alan_Boş_Giriş_Denemesi
    Given I open the application url from config 'url'
    And I click on 'GirisYapButon'
    Then I see the element 'girisHataMesajıText'
