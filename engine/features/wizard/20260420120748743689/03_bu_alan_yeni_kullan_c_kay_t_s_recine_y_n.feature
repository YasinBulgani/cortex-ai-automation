Feature: Bu alan yeni kullanıcı kayıt sürecine yönlendirir

  Scenario: Bu alan yeni kullanıcı kayıt sürecine yönlendirir
    Given I open the application url "http://linkedin.com/uas/login?session_redirect=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2F"
    # TODO: locator eşleşmedi — Step 7'deki 'AI öner' ile bu adıma locator ata
    When I click on "Element"
    # TODO: locator eşleşmedi — Step 7'deki 'AI öner' ile bu adıma locator ata
    When I click on "Element"
    # TODO: locator eşleşmedi — Step 7'deki 'AI öner' ile bu adıma locator ata
    Then I see the element "Element"
