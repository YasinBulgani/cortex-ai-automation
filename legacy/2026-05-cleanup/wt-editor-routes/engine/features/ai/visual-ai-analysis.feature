Feature: Visual AI Analysis & Anomaly Detection
  As a QA engineer
  I want to use AI-powered visual analysis to detect anomalies
  So that I can identify visual regressions with intelligent insights

  @visual-ai @smoke
  Scenario: Analyze visual difference with AI
    Given I am on the Paribu home page
    When I analyze the visual difference with AI
    Then the visual analysis should identify anomalies

  @visual-ai @anomaly-detection
  Scenario: Detect color shifts in visual comparison
    Given I am on the Paribu home page
    When I take a full page screenshot named "paribu-colors"
    And I analyze the visual difference with AI
    Then the analysis should report color shifts

  @visual-ai @anomaly-detection
  Scenario: Detect layout changes in visual comparison
    Given I am on the Paribu home page
    When I take a full page screenshot named "paribu-layout"
    And I analyze the visual difference with AI
    Then the analysis should report layout changes

  @visual-ai @thresholds
  Scenario: Check visual similarity threshold
    Given I am on the Paribu home page
    When I take a full page screenshot named "paribu-similarity"
    And I analyze the visual difference with AI
    Then the visual similarity should be above 0.75

  @visual-ai @thresholds @critical
  Scenario: Verify exact visual similarity with tolerance
    Given I am on the Paribu home page
    When I take a full page screenshot named "paribu-exact-similarity"
    And I analyze the visual difference with AI
    Then the visual similarity should be exactly 1.0 with tolerance 0.05

  @visual-ai @anomalies
  Scenario: Limit detected anomalies
    Given I am on the Paribu home page
    When I take a full page screenshot named "paribu-anomalies"
    And I analyze the visual difference with AI
    Then the visual analysis should detect 5 or fewer anomalies

  @visual-ai @anomalies @critical
  Scenario: Ensure no critical visual anomalies
    Given I am on the Paribu home page
    When I take a full page screenshot named "paribu-critical"
    And I analyze the visual difference with AI
    Then there should be no critical visual anomalies

  @visual-ai @smart-baseline
  Scenario: Perform smart baseline analysis
    Given I am on the Paribu home page
    When I take a full page screenshot named "paribu-smart"
    And I perform smart baseline analysis
    Then the baseline should be updated

  @visual-ai @smart-baseline
  Scenario: Smart baseline provides recommendations
    Given I am on the Paribu home page
    When I take a full page screenshot named "paribu-smart-rec"
    And I perform smart baseline analysis
    Then the baseline analysis should provide recommendations

  @visual-ai @reporting
  Scenario: Generate visual analysis report
    Given I am on the Paribu home page
    When I take a full page screenshot named "paribu-report"
    And I analyze the visual difference with AI
    And I generate visual analysis report
    Then the visual analysis report should contain anomaly details
    And the visual analysis report should contain recommendations

  @visual-ai @baseline-status
  Scenario: Check baseline status
    Given I am on the Paribu home page
    When I check baseline status for "paribu-home"
    Then the baseline should have 10 or fewer update cycles

  @visual-ai @comprehensive @critical
  Scenario: Comprehensive visual AI workflow
    Given I have visual AI analysis enabled
    And I am on the Paribu home page
    When I perform comprehensive visual AI analysis
    Then the visual AI workflow should complete successfully
    And there should be no critical visual anomalies

  @visual-ai @markets-page
  Scenario: Analyze market page visual consistency
    Given I am on the Paribu home page
    When I go to markets page
    And I take a full page screenshot named "markets-page"
    And I analyze the visual difference with AI
    Then the visual similarity should be above 0.80
    And the visual analysis should detect 3 or fewer anomalies

  @visual-ai @login-page
  Scenario: Analyze login page for visual anomalies
    Given I navigate to Paribu login page
    When I take a full page screenshot named "login-visual"
    And I analyze the visual difference with AI
    Then there should be no critical visual anomalies
    And the visual analysis should identify anomalies

  @visual-ai @integration
  Scenario: Visual AI with smart baseline updates
    Given I have visual AI analysis enabled
    And I am on the Paribu home page
    When I take a full page screenshot named "paribu-integration"
    And I perform smart baseline analysis
    Then the baseline analysis should provide recommendations
    And I should see the recommended action

  @visual-ai @workflow @smoke
  Scenario: Complete visual AI testing workflow
    Given I have visual AI analysis enabled
    And I am on the Paribu home page
    When I perform comprehensive visual AI analysis
    And I generate visual analysis report
    Then the visual AI workflow should complete successfully
    And the visual analysis report should contain anomaly details
