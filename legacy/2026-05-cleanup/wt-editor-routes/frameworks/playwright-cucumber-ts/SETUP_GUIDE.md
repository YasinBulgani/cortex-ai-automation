# Test Automation Framework Setup Guide

## 🚀 Quick Start

### Prerequisites
- Node.js >= 16.0.0
- npm >= 8.0.0

### Installation Steps

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Install Playwright Browsers**
   ```bash
   npm run install:browsers
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

4. **Run Tests**
   ```bash
   npm test
   ```

## 📁 Project Structure

```
Paribu/
├── config/              # Configuration files
│   ├── browsers.ts     # Browser configurations
│   └── environments.ts # Environment configurations
├── features/            # Cucumber feature files
│   ├── api_tests.feature
│   └── web_tests.feature
├── pages/               # Page Object Model classes
│   ├── BasePage.ts
│   ├── ParibuHomePage.ts
│   ├── MarketsPage.ts
│   ├── CryptocurrencyDetailPage.ts
│   └── LoginPage.ts
├── steps/               # Step definitions
│   ├── api/
│   │   └── api.steps.ts
│   ├── web/
│   │   └── web.steps.ts
│   ├── hooks.ts
│   └── playwright-world.ts
├── utils/               # Helper utilities
│   ├── api/
│   │   ├── ApiClient.ts
│   │   └── DummyJsonApi.ts
│   ├── Logger.ts
│   ├── TestDataLoader.ts
│   └── generate-report.js
├── test-data/           # Test data files (JSON)
│   ├── api-credentials.json
│   ├── api-endpoints.json
│   └── web-selectors.json
├── cucumber.js          # Cucumber configuration
├── tsconfig.json        # TypeScript configuration
└── package.json        # Dependencies and scripts
```

## 🔧 Configuration Files

### package.json
Contains all project dependencies and npm scripts.

### tsconfig.json
TypeScript compiler configuration with path mappings.

### cucumber.js
Cucumber BDD framework configuration.

### .env
Environment variables (copy from .env.example).

## 📝 Writing Tests

### Feature Files
Create `.feature` files in `features/` directory using Gherkin syntax.

### Step Definitions
Create step definitions in `steps/` directory.

### Page Objects
Create page object classes in `pages/` directory extending `BasePage`.

## 🎯 Running Tests

See `README.md` for detailed test execution commands.

