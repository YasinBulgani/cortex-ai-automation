# Test Automation Framework - Project Structure

## 📁 Complete Directory Structure

```
Paribu/
├── config/                    # Configuration files
│   ├── config.ts             # Browser and environment configurations (combined)
│   └── constants.ts          # Framework constants and configuration values
│
├── features/                  # Cucumber feature files (BDD scenarios)
│   ├── api_tests.feature    # API automation test scenarios
│   └── web_tests.feature    # Web automation test scenarios
│
├── pages/                     # Page Object Model (POM) classes
│   ├── BasePage.ts          # Base page class with common methods
│   ├── ParibuHomePage.ts    # Paribu homepage page object
│   ├── MarketsPage.ts       # Markets page page object
│   ├── CryptocurrencyDetailPage.ts # Cryptocurrency detail page object
│   └── LoginPage.ts         # Login page page object
│
├── steps/                     # Cucumber step definitions and hooks
│   ├── api.steps.ts        # API test step implementations
│   ├── web.steps.ts        # Web test step implementations
│   ├── hooks.ts             # Before/After hooks for test lifecycle
│   └── playwright-world.ts  # Custom Cucumber World for Playwright
│
├── test-data/                 # Static test data files (JSON)
│   ├── api-credentials.json # API authentication credentials
│   ├── api-endpoints.json   # API endpoint configurations
│   └── web-selectors.json   # Web element selectors
│
├── utils/                     # Utility classes and helper functions
│   ├── ApiClient.ts        # Generic HTTP client wrapper
│   ├── DummyJsonApi.ts     # DummyJSON API specific wrapper
│   ├── Logger.ts            # Logging utility class
│   ├── TestDataLoader.ts    # Test data loading utility
│   ├── CustomErrors.ts      # Custom error classes
│   └── generate-report.js   # HTML report generator script
│
├── logs/                     # Test execution logs (generated, gitignore)
│   └── test-execution-*.log # Daily log files
│
├── reports/                   # Test reports (generated, gitignore)
│   ├── cucumber_report.html # HTML test report
│   ├── cucumber-report.json # JSON test report
│   └── screenshots/         # Screenshots on test failures
│
├── .vscode/                   # VS Code IDE configuration
│   ├── extensions.json      # Recommended extensions
│   ├── launch.json          # Debug configurations
│   └── settings.json        # Workspace settings
│
├── .editorconfig             # Editor configuration
├── .gitignore                # Git ignore rules
├── .npmrc                    # NPM configuration
├── .env.example              # Environment variables example
├── cucumber.js               # Cucumber configuration
├── package.json              # NPM dependencies and scripts
├── README.md                 # Project documentation
├── SETUP_GUIDE.md            # Setup and installation guide
├── test-runner.ts            # Advanced test runner CLI
└── tsconfig.json             # TypeScript configuration
```

## 📋 File Descriptions

### Core Configuration Files

#### `package.json`
- **Purpose**: NPM dependencies, scripts, and project metadata
- **Key Dependencies**:
  - `@playwright/test`: Browser automation
  - `@cucumber/cucumber`: BDD framework
  - `ts-node`: TypeScript execution
  - `typescript`: TypeScript compiler
  - `cucumber-html-reporter`: HTML report generation

#### `tsconfig.json`
- **Purpose**: TypeScript compiler configuration
- **Key Features**:
  - Strict mode enabled
  - Path mappings for clean imports
  - Source maps for debugging
  - ES2020 target

#### `cucumber.js`
- **Purpose**: Cucumber BDD framework configuration
- **Features**:
  - TypeScript support via ts-node
  - Step definitions auto-loading
  - Multiple report formats
  - Async/await snippet interface

### Directory Structure

#### `config/`
Contains all configuration files:
- **browsers.ts**: Browser launch options and context configurations
- **environments.ts**: Environment-specific settings (URLs, timeouts)
- **index.ts**: Centralized exports

#### `features/`
Cucumber feature files written in Gherkin syntax:
- **api_tests.feature**: API test scenarios
- **web_tests.feature**: Web UI test scenarios

#### `pages/`
Page Object Model classes:
- **BasePage.ts**: Abstract base class with common methods
- **ParibuHomePage.ts**: Homepage interactions
- **MarketsPage.ts**: Markets page interactions
- **CryptocurrencyDetailPage.ts**: Detail page interactions
- **LoginPage.ts**: Login page interactions

#### `steps/`
Cucumber step definitions:
- **api.steps.ts**: API test step implementations
- **web.steps.ts**: Web test step implementations
- **hooks.ts**: Test lifecycle hooks
- **playwright-world.ts**: Custom World for Playwright integration

#### `test-data/`
Static JSON test data:
- **api-credentials.json**: API authentication data
- **api-endpoints.json**: API endpoint configurations
- **web-selectors.json**: Web element selectors

#### `utils/`
Utility classes and helpers:
- **ApiClient.ts**: Generic HTTP client wrapper
- **DummyJsonApi.ts**: DummyJSON API specific wrapper
- **Logger.ts**: Logging utility
- **TestDataLoader.ts**: Test data management
- **CustomErrors.ts**: Custom error classes
- **generate-report.js**: Report generation

## 🎯 Design Patterns

1. **Page Object Model (POM)**: Encapsulates page interactions
2. **SOLID Principles**: Single Responsibility, Dependency Inversion
3. **DRY**: Reusable base classes and utilities
4. **Separation of Concerns**: Clear separation of config, pages, steps, utils

## 📝 Naming Conventions

- **Files**: PascalCase for classes, camelCase for utilities
- **Folders**: lowercase
- **Variables**: camelCase
- **Constants**: UPPER_SNAKE_CASE
- **Classes**: PascalCase

