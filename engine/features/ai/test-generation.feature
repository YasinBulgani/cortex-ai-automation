Feature: AI-Powered Test Generation
  As a test engineer
  I want to use AI to generate and optimize test scenarios
  So that I can accelerate test creation and improve coverage

  @ai @smoke
  Scenario: Generate test scenarios from user story
    Given I have AI test generation enabled
    When I generate test scenarios for "User wants to search for cryptocurrencies and view prices"
    Then I should have generated test scenarios
    And the generated scenarios should have 3 or more steps

  @ai @generation
  Scenario: Generate multiple scenarios with various test cases
    Given I have AI test generation enabled
    When I generate test scenarios for "User completes authentication workflow with email and password"
    Then I should have generated test scenarios
    And the generated scenarios should have 4 or more steps

  @ai @data
  Scenario: Generate test data suggestions
    Given I have AI test generation enabled
    When I generate test scenarios for "User logs in with valid credentials"
    And I generate test data for the scenario
    Then the suggested test data should include required fields

  @ai @coverage
  Scenario: Analyze test coverage for generated scenarios
    Given I have AI test generation enabled
    When I generate test scenarios for "Market data display and filtering"
    And I analyze test coverage for the generated scenarios
    Then the test coverage should be at least 50 percent

  @ai @coverage
  Scenario: Identify coverage gaps
    Given I have AI test generation enabled
    When I generate test scenarios for "User profile management and settings"
    And I analyze test coverage for the generated scenarios
    Then I should see coverage gaps identified

  @ai @coverage @critical
  Scenario: Get recommendations for test improvements
    Given I have AI test generation enabled
    When I generate test scenarios for "Shopping cart and checkout process"
    And I analyze test coverage for the generated scenarios
    Then I should see recommendations for improvement
    And the test coverage should be at least 40 percent

  @ai @debug
  Scenario: Debug failing test with AI assistance
    Given I have AI test generation enabled
    When I debug the failing test "login_with_invalid_credentials"
    Then I should receive debugging suggestions

  @ai @performance
  Scenario: Get performance optimization suggestions
    Given I have AI test generation enabled
    When I analyze performance for optimization
    Then I should receive optimization suggestions

  @ai @stats
  Scenario: Track AI usage statistics
    Given I have AI test generation enabled
    When I generate test scenarios for "Basic search functionality"
    And I check AI client statistics
    Then I should see the AI provider and model used
    And the AI client should have made 1 or more requests
    And the token usage should be tracked

  @ai @workflow @critical
  Scenario: Execute complete AI test generation workflow
    Given I have a comprehensive AI test generation setup
    When I execute a complete AI test generation workflow
    Then the AI workflow should complete successfully
    And the AI workflow results should be comprehensive

  @ai @data-generation
  Scenario: Generate test data for multiple scenarios
    Given I have AI test generation enabled
    When I generate test scenarios for "User registration with email verification"
    And I generate test data for the scenario
    Then the suggested test data should include required fields

  @ai @coverage-gap
  Scenario: Assess coverage gaps in generated scenarios
    Given I have a comprehensive AI test generation setup
    When I execute a complete AI test generation workflow
    And I analyze test coverage for the generated scenarios
    Then I should see coverage gaps identified
    And I should see recommendations for improvement

  @ai @integration @smoke
  Scenario: AI-assisted test scenario creation workflow
    Given I have AI test generation enabled
    And I am on the Paribu home page
    When I generate test scenarios for "Viewing cryptocurrency market data"
    And I generate test data for the scenario
    And I analyze test coverage for the generated scenarios
    Then I should have generated test scenarios
    And the suggested test data should include required fields
    And the test coverage should be at least 40 percent

  @ai @comprehensive
  Scenario: Complete AI testing pipeline
    Given I have a comprehensive AI test generation setup
    When I generate test scenarios for "Complete user journey from login to trading"
    And I generate test data for the scenario
    And I analyze test coverage for the generated scenarios
    And I check AI client statistics
    Then the AI workflow should complete successfully
    And the AI client should have made 3 or more requests
    And the test coverage should be at least 50 percent
