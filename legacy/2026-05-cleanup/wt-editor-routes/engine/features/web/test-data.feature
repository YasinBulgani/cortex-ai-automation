Feature: Test Data Management
  As a test automation engineer
  I want to manage and manipulate test data efficiently
  So that I can run flexible and parametrized tests

  @data
  Scenario: Load test data from fixture
    Given I have test data from "users"
    Then test data should have field "email"
    And test data should have field "password"

  @data
  Scenario: Load specific test data item
    Given I load test data item 0 from "users"
    Then test data should have field "email"
    And test data "email" field should not be empty

  @data
  Scenario: Get random test data
    Given I have random test data from "users"
    Then test data should have field "username"

  @data
  Scenario: Get multiple random items
    Given I have 5 random test data items from "users"
    Then test data should have 5 items

  @data
  Scenario: Get unique test data items
    Given I have 3 unique test data items from "users"
    Then test data should have 3 items

  @data
  Scenario: Merge multiple fixtures
    When I merge test data from "users" and "products"
    Then test data should have field "email"

  @data
  Scenario: Filter test data by field
    Given I have test data from "users"
    When I filter test data where "role" equals "admin"
    Then all test data should be valid

  @data
  Scenario: Filter test data by user role
    Given I have test data from "users"
    When I filter test data by user role "user"
    Then all test data should be valid

  @data
  Scenario: Extract specific fields from test data
    Given I have test data from "users"
    When I extract fields "email, username" from test data
    Then test data should have field "email"

  @data
  Scenario: Generate synthetic test data
    Given I have generated test data with 10 users
    Then test data should have 10 items

  @data
  Scenario: Generate random email
    Given I have generated random email "randomEmail"
    Then test data should have field "randomEmail"

  @data
  Scenario: Generate random password
    Given I have generated random password "testPassword"
    Then test data should have field "testPassword"

  @data
  Scenario: Generate random username
    Given I have generated random username "testUser"
    Then test data should have field "testUser"

  @data
  Scenario: Verify fixture availability
    Given test fixture "users" is available
    Then test fixture "users" is available

  @data
  Scenario: Save test data as fixture
    Given I have generated test data with 5 users
    When I save test data as fixture "generated_users"
    Then test fixture "generated_users" is available

  @data
  Scenario: Work with users fixture
    Given test fixture "users" is available
    And I have test data from "users"
    When I filter test data where "email" equals "test@example.com"
    Then all test data should be valid

  @data @smoke
  Scenario: Complete data workflow
    Given I have generated test data with 10 users
    When I save test data as fixture "smoke_users"
    And I load test data from "smoke_users"
    Then test data should have 10 items
    And test data should have field "email"
    And test data should have field "username"
