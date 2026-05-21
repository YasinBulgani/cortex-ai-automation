Feature: API Automation Tests
  As a QA automation engineer
  I want to test the DummyJSON API endpoints
  So that I can verify API functionality and authentication flows

  @api @login
  Scenario: Login with valid credentials - Happy Path
    Given I have valid login credentials
    When I perform a login request
    Then the login response status code should be 200
    And the response should contain an access token
    And I store the access token for subsequent requests

  @api @login @negative
  Scenario: Login with invalid credentials - Negative Path
    Given I have invalid login credentials
    When I perform a login request
    Then the login response status code should be 400
    And the response should not contain an access token

  @api @products @authenticated
  Scenario: Get products list with authentication
    Given I have a valid access token
    When I request the products list with limit {int}
    Then the response status code should be 200
    And the products array length should match the limit {int}

  @api @products @update @delete @sequential
  Scenario: Update and delete product flow - Sequential
    Given I have a valid access token
    And I request the products list with limit 1
    And I store the first product ID
    When I update the title of the first product to "Updated Product Title"
    Then the update response status code should be 200
    When I delete the first product
    Then the delete response status code should be 200

  @api @login @scenario-outline
  Scenario Outline: Login with different credentials - Scenario Outline
    Given I have login credentials with username "<username>" and password "<password>"
    When I perform a login request
    Then the login response status code should be <statusCode>
    And the response should <tokenStatus> contain an access token

    Examples:
      | username   | password      | statusCode | tokenStatus |
      | emilys     | emilyspass    | 200        |             |
      | invalid    | wrongpass      | 400        | not         |

  @api @products @update @isDeleted
  Scenario: Update product isDeleted field to true
    Given I have a valid access token
    And I request the products list with limit 1
    And I store the first product ID
    When I update the isDeleted field of the first product to true
    Then the update response status code should be 200
    And the response should contain isDeleted field as true

  @api @products @categories
  Scenario: Verify all categories return 200 OK
    When I request the products categories list
    Then the response status code should be 200
    And I verify each category endpoint returns 200 OK

  @api @performance @timeout
  Scenario: Verify login response time is under 2000ms
    Given I have valid login credentials
    When I perform a login request with delay parameter 0
    Then the login response time should be less than 2000 milliseconds
    And the login response status code should be 200






