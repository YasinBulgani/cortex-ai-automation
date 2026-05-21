/**
 * Cucumber.js configuration for BDD tests.
 *
 * IntelliJ: Install "Cucumber.js" plugin, set this file as config.
 * CLI: npx cucumber-js --config cucumber.mjs
 */
export default {
  paths: ["e2e/bdd/features/**/*.feature"],
  require: [
    "e2e/bdd/support/**/*.ts",
    "e2e/bdd/steps/**/*.ts",
  ],
  requireModule: ["ts-node/register"],
  format: [
    "progress-bar",
    "json:reports/bdd/cucumber-report.json",
    "html:reports/bdd/cucumber-report.html",
  ],
  formatOptions: {
    snippetInterface: "async-await",
    snippetSyntax: "./node_modules/@cucumber/cucumber/lib/formatter/step_definition_snippet_builder/javascript_snippet_syntax.js",
  },
  language: "tr",
  publishQuiet: true,
  parallel: 1,
  worldParameters: {
    baseUrl: process.env.APP_URL || "http://127.0.0.1:3417",
    browser: process.env.BROWSER || "chromium",
    headless: process.env.HEADLESS !== "false",
  },
};
