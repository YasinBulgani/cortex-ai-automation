Feature: Bu formda iki temel alan vardır: biri email veya telefon numarası girişi, diğeri

  Scenario: Bu formda iki temel alan vardır: biri email veya telefon numarası girişi, diğeri
    Given I open the application url "https://www.linkedin.com/uas/login?session_redirect=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2F"
    When I click on "Element"
    When I click on "Element"
    Then I see the element "Element"
