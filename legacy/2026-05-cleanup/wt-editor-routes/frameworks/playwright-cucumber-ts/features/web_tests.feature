Feature: Paribu Web Automation Tests
  As a QA automation engineer
  I want to test Paribu website functionality
  So that I can verify user interactions and calculations work correctly

  Background:
    Given I navigate to Paribu homepage
    And I close the cookie notice if present

  @web @calculation
  Scenario: Calculation Check - Verify Total Price Calculation
    When I navigate to the Markets page
    And I select the 'FAN' filter
    And I set the time filter to "12 Saat"
    And I click on the 3rd cryptocurrency in the list
    And I click the "Güncel Fiyat" button to fill unit price
    And I enter quantity "5" in the Buy-Sell panel
    Then the total price should display the correct calculation result

  @web @login @negative
  Scenario: Invalid Login - Verify Error Message
    When I navigate to the Login page
    And I enter invalid country code "+99"
    And I enter invalid mobile number "1234567890"
    And I enter invalid password "wrongpass"
    And I click the Login button
    Then an error message should appear
    And the error message should contain "error"

  @web @sorting @form @optional
  Scenario: Sorting and Form Control - Verify Order Transfer
    When I navigate to the Markets page
    And I sort by price in descending order
    And I select 3 random coins with positive 24h change
    And I click on the first selected cryptocurrency
    When I click on a pending buy order from the list
    Then the data should be correctly moved to the "Satış" tab
    When I click on a pending sell order from the list
    Then the data should be correctly moved to the "Alış" tab

