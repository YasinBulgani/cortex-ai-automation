/**
 * HTML Report Generator
 * Generates HTML test reports from Cucumber JSON output
 */

require('dotenv').config();
const reporter = require('cucumber-html-reporter');
const path = require('path');
const fs = require('fs');

const reportOptions = {
  theme: 'bootstrap',
  jsonFile: path.join(__dirname, '../reports/cucumber-report.json'),
  output: path.join(__dirname, '../reports/cucumber_report.html'),
  reportSuiteAsScenarios: true,
  scenarioTimestamp: true,
  launchReport: false,
  metadata: {
    'App Version': process.env.APP_VERSION || '2.0.0',
    'Test Environment': process.env.ENVIRONMENT || 'QA',
    'Browser': process.env.BROWSER || 'Chromium',
    'Platform': process.platform,
    'Executed': new Date().toISOString()
  },
  screenshotsDirectory: path.join(__dirname, '../reports/screenshots'),
  storeScreenshots: true
};

// Ensure reports directory exists
const reportsDir = path.join(__dirname, '../reports');
if (!fs.existsSync(reportsDir)) {
  fs.mkdirSync(reportsDir, { recursive: true });
}

// Ensure screenshots directory exists
const screenshotsDir = path.join(__dirname, '../reports/screenshots');
if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

reporter.generate(reportOptions, () => {
  console.log('HTML report generated successfully:', reportOptions.output);
});
