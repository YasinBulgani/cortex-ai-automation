Feature: Performance Testing
  As a performance engineer
  I want to measure and monitor page performance metrics
  So that I can ensure the application meets performance requirements

  @performance
  Scenario: Measure page load time
    Given I am on the Paribu home page
    When I measure the page load time
    Then the page load time should be less than 5000 milliseconds

  @performance
  Scenario: Check DOM content load time
    Given I am on the Paribu home page
    When I measure the page load time
    Then the DOM content should load in less than 4000 milliseconds

  @performance
  Scenario: Monitor first contentful paint
    Given I am on the Paribu home page
    When I measure the page load time
    Then the first contentful paint should be less than 2000 milliseconds

  @performance
  Scenario: Monitor largest contentful paint
    Given I am on the Paribu home page
    When I measure the page load time
    Then the largest contentful paint should be less than 3000 milliseconds

  @performance
  Scenario: Check cumulative layout shift
    Given I am on the Paribu home page
    When I measure the page load time
    Then the cumulative layout shift should be less than 0.15

  @performance
  Scenario: Verify core web vitals are good
    Given I am on the Paribu home page
    When I check the core web vitals
    Then the core web vitals should be good

  @performance
  Scenario: Monitor network performance
    Given I am on the Paribu home page
    When I check the network performance
    Then the total network requests should be less than 50
    And the total network size should be less than 5000 KB

  @performance
  Scenario: Check slowest network request
    Given I am on the Paribu home page
    When I check the network performance
    Then the slowest network request should be "recorded"

  @performance
  Scenario: Test with custom performance threshold
    Given I am on the Paribu home page
    When I set performance threshold for page load to 3000 milliseconds
    And I assert performance with default thresholds
    Then the performance report should have no violations

  @performance
  Scenario: Markets page performance
    Given I am on the Paribu home page
    When I go to markets page
    And I measure the page load time
    Then the page load time should be less than 4000 milliseconds
    And the DOM content should load in less than 3000 milliseconds

  @performance
  Scenario: Login page performance
    Given I navigate to Paribu login page
    When I measure the page load time
    Then the first contentful paint should be less than 1500 milliseconds
    And the page load time should be less than 3000 milliseconds

  @performance @critical
  Scenario: Home page meets all performance requirements
    Given I am on the Paribu home page
    When I measure the page load time
    And I check the core web vitals
    And I check the network performance
    Then the page load time should be less than 4000 milliseconds
    And the first contentful paint should be less than 2000 milliseconds
    And the core web vitals should be good
    And the total network requests should be less than 60
    And the total network size should be less than 5500 KB
