Feature: Bu sayede hızlı ve tek tıkla giriş sağlanır

  Scenario: Bu sayede hızlı ve tek tıkla giriş sağlanır
    Given I open the application url "http://linkedin.com/uas/login?session_redirect=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2F"
    # TODO: locator eşleşmedi — Step 7'deki 'AI öner' ile bu adıma locator ata
    When I click on "Element"
    # xpath=/div/header/a · warn (70/100)
    When I click on "LinkedInLink"
    # TODO: locator eşleşmedi — Step 7'deki 'AI öner' ile bu adıma locator ata
    Then I see the element "Element"
