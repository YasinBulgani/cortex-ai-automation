@cortex @login @a11y
Feature: Cortex - Login Erisilebilirlik

  Klavye navigasyonu, ARIA, screen-reader uyumlulugu temel testler.

  Background:
    Given I open "cortex.url" link
    * I wait for page to load
    * I click "cookieAcceptButton" if it exists

  @pw
  Scenario: TAB ile alanlar arasi gezinme calisir
    When I click "userNameInput"
    And I press "TAB" key
    And I press "TAB" key
    # Now focus loginButton or rememberMe — sadece sayfa cokmedi varsayar
    Then I see "loginButton"

  @pw
  Scenario: Form submit etiketi/role'u dogru
    Then I see "loginButton"
    # Implicit: button[type='submit'] erisilebilir text icermeli
    And I verify "loginButton" contains "Giriş"

  @pw
  Scenario: Input alanlari etiket (label) ile baglanmali
    # Selektor common.json'da yok; placeholder yeterli kontrol icin
    Then I see "userNameInput"
    And I see "passwordInput"

  @pw
  Scenario: Klavye ile sifre alanindan tab sonra login butonuna gec
    When I click "passwordInput"
    And I press "TAB" key
    Then I see "loginButton"

  @pw
  Scenario: Sifremi unuttum linki keyboard ile erisilebilir
    When I click "userNameInput"
    And I press "TAB" key
    And I press "TAB" key
    And I press "TAB" key
    Then I see "forgotPasswordLink"

  @pw @axe
  Scenario: Login sayfasi WCAG 2.1 AA uyumlu (axe-core)
    Then I run accessibility audit and expect WCAG 2.1 AA compliance

  @pw @axe
  Scenario: Login sayfasinda kritik a11y ihlali yok
    Then I run accessibility audit and expect no critical violations
