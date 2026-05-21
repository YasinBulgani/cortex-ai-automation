@manual @setup
Feature: Setup encrypted credentials

  Run once to register encrypted passwords for the framework.
  Requires .env (CORTEX_AES_KEY + CORTEX_PASSWORD).

  Scenario: Register cortex test user password
    * I encrypt password "${ENV:CORTEX_PASSWORD}" and save as alias "cortexUser" with overwrite

  Scenario: Register the DB password
    * I encrypt password "${ENV:DB1_PASSWORD}" and save as alias "db1" with overwrite