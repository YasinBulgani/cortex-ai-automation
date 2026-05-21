Feature: Bu seçenek, kullanıcıların şifrelerini sıfırlayabilmesini sağlar

  Scenario: Bu seçenek, kullanıcıların şifrelerini sıfırlayabilmesini sağlar
    Given I open the application url "https://www.linkedin.com/uas/login?session_redirect=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2F"
    When I click on "Element"
    When I enter "+-value" into the input "Element"
    Then I see the element "Element"
