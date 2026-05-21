Feature: Web Application Login Functionality
  As a user
  I want to log in to the application
  So that I can access my account

  Background:
    Given the application is started
    And I navigate to "https://paribu.com/login"

  Scenario: Successful login with valid credentials
    When I log in with "test@example.com" and "TestPassword123!"
    Then page should contain "Dashboard"

  Scenario: Login fails with invalid credentials
    When I log in with "invalid@example.com" and "WrongPassword"
    Then I should see an error message
    And page URL should contain "login"

  Scenario: Password field is masked
    When I fill "email" with "test@example.com"
    And I fill "password" with "TestPassword123!"
    Then "input[type='password']" should be visible

  Scenario: Logout functionality
    Given I am logged in as "test@example.com"
    When I click "Logout"
    Then page URL should contain "login"
