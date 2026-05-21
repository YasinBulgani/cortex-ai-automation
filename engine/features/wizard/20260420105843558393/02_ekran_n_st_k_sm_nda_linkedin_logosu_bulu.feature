Feature: Ekranın üst kısmında LinkedIn logosu bulunur ve bu alan marka güveni oluşturur

  Scenario: Ekranın üst kısmında LinkedIn logosu bulunur ve bu alan marka güveni oluşturur
    Given I open the application url "https://www.linkedin.com/uas/login?session_redirect=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2F"
    When I click on "Element"
    When I click on "Element"
    Then I see the element "Element"
