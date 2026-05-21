Feature: Test Recording & Automatic Code Generation
  As a test engineer
  I want to record user actions and automatically generate test code
  So that I can accelerate test creation without manual coding

  @recording @smoke
  Scenario: Start and stop test recording
    Given I am on the Paribu home page
    And I start recording user actions
    When I navigate to markets page
    And I stop recording
    Then the recording should capture all user actions

  @recording @generation
  Scenario: Convert recorded actions to BDD steps
    Given I am on the Paribu home page
    And I start recording user actions
    When I navigate to markets page
    And I stop recording
    And I convert recorded actions to test steps
    Then the generated steps should follow BDD format

  @recording @codegen
  Scenario: Generate TypeScript step definitions
    Given I am on the Paribu home page
    And I start recording user actions
    When I navigate to markets page
    And I stop recording
    And I convert recorded actions to test steps
    And I generate step definitions from the recording
    Then the generated step definitions should be valid TypeScript

  @recording @export
  Scenario: Export recording as JSON
    Given I am on the Paribu home page
    And I start recording user actions
    When I search for "Bitcoin"
    And I stop recording
    And I export the recording as JSON
    Then the exported JSON should contain all recorded actions

  @recording @export
  Scenario: Export recording as Gherkin feature
    Given I am on the Paribu home page
    And I start recording user actions
    When I navigate to markets page
    And I stop recording
    And I convert recorded actions to test steps
    And I export the recording as Gherkin
    Then the exported Gherkin should be a valid feature file

  @recording @replay
  Scenario: Replay recorded actions
    Given I am on the Paribu home page
    And I start recording user actions
    When I navigate to markets page
    And I stop recording
    And I replay the recorded actions
    Then the replay should complete successfully

  @recording @stats
  Scenario: Track recording statistics
    Given I am on the Paribu home page
    And I start recording user actions
    When I navigate to markets page
    And I search for "Ethereum"
    And I stop recording
    And I check recording statistics
    Then the recording should have 2 or more actions
    And the recording should have generated 1 or more steps

  @recording @comprehensive
  Scenario: Complete test recording workflow
    Given I have a test recording setup
    And I am on the Paribu home page
    When I perform a complete recording workflow
    Then the recording workflow should produce valid output

  @recording @codegen @critical
  Scenario: Generate step definitions from complex interactions
    Given I am on the Paribu home page
    And I start recording user actions
    When I navigate to Paribu login page
    And I stop recording
    And I convert recorded actions to test steps
    And I generate step definitions from the recording
    Then the generated step definitions should be valid TypeScript
    And the generated steps should follow BDD format

  @recording @export @smoke
  Scenario: Export complete workflow as feature file
    Given I have a test recording setup
    And I am on the Paribu home page
    When I perform a complete recording workflow
    And I export the recording as Gherkin
    Then the exported Gherkin should be a valid feature file

  @recording @integration
  Scenario: Record and convert authentication workflow
    Given I am on the Paribu home page
    And I start recording user actions
    When I navigate to Paribu login page
    And I stop recording
    And I convert recorded actions to test steps
    Then the generated steps should follow BDD format
    And I export the recording as Gherkin

  @recording @workflow @critical
  Scenario: Complete test creation from recording
    Given I have a test recording setup
    When I perform a complete recording workflow
    Then the recording workflow should produce valid output
    And the recording should have 1 or more actions
    And the recording should have generated 1 or more steps
