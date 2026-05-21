Feature: Şifre alanının yakınında veya altında “Forgot password” (şifremi unuttum) seçene

  Scenario: Şifre alanının yakınında veya altında “Forgot password” (şifremi unuttum) seçene
    Given I open the application url "https://www.linkedin.com/uas/login?session_redirect=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2F"
    When I click on "Element"
    When I enter "+-value" into the input "Element"
    Then I see the element "Element"
