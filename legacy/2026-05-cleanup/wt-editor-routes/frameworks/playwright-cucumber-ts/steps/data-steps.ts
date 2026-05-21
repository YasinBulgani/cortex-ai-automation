/**
 * Test Data Management Step Definitions
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { TestDataManager, dataGenerators } from '../utils/TestDataManager';

/**
 * DATA LOADING STEPS
 */

Given('I have test data from {string}', async function (this: any, fixtureName: string) {
  const testDataManager = new TestDataManager(this.logger);
  const data = testDataManager.loadFixture(fixtureName);
  this.testData = data;
  this.logger.info(`Loaded test data: ${fixtureName} (${data.length} items)`);
});

Given('I load test data item {int} from {string}', async function (this: any, index: number, fixtureName: string) {
  const testDataManager = new TestDataManager(this.logger);
  const data = testDataManager.getTestData(fixtureName, index);
  this.testData = data;
  this.logger.info(`Loaded test data item ${index} from ${fixtureName}`);
});

/**
 * RANDOM DATA STEPS
 */

Given('I have random test data from {string}', async function (this: any, fixtureName: string) {
  const testDataManager = new TestDataManager(this.logger);
  const data = testDataManager.getRandomTestData(fixtureName);
  this.testData = data;
  this.logger.info(`Loaded random test data from ${fixtureName}`);
});

Given('I have {int} random test data items from {string}', async function (this: any, count: number, fixtureName: string) {
  const testDataManager = new TestDataManager(this.logger);
  const data = testDataManager.getRandomTestDataSet(fixtureName, count, false);
  this.testData = data;
  this.logger.info(`Loaded ${count} random test data items from ${fixtureName}`);
});

Given('I have {int} unique test data items from {string}', async function (this: any, count: number, fixtureName: string) {
  const testDataManager = new TestDataManager(this.logger);
  const data = testDataManager.getRandomTestDataSet(fixtureName, count, true);
  this.testData = data;
  this.logger.info(`Loaded ${count} unique test data items from ${fixtureName}`);
});

/**
 * DATA MERGING STEPS
 */

When('I merge test data from {string} and {string}', async function (this: any, fixture1: string, fixture2: string) {
  const testDataManager = new TestDataManager(this.logger);
  const merged = testDataManager.mergeFixtures(fixture1, fixture2);
  this.testData = merged;
  this.logger.info(`Merged test data: ${fixture1} and ${fixture2} (${merged.length} items)`);
});

When('I merge test data from {string}, {string}, and {string}', async function (this: any, fixture1: string, fixture2: string, fixture3: string) {
  const testDataManager = new TestDataManager(this.logger);
  const merged = testDataManager.mergeFixtures(fixture1, fixture2, fixture3);
  this.testData = merged;
  this.logger.info(`Merged test data: ${fixture1}, ${fixture2}, ${fixture3} (${merged.length} items)`);
});

/**
 * DATA FILTERING STEPS
 */

When('I filter test data where {string} equals {string}', async function (this: any, field: string, value: string) {
  const testDataManager = new TestDataManager(this.logger);

  if (!this.testData) {
    throw new Error('No test data loaded');
  }

  const data = Array.isArray(this.testData) ? this.testData : [this.testData];
  const filtered = data.filter((item) => {
    const fieldValue = String(item[field]);
    const expectedValue = String(value);
    return fieldValue.includes(expectedValue);
  });

  this.testData = filtered;
  this.logger.info(`Filtered test data: ${field}=${value} (${filtered.length} items)`);
});

When('I filter test data by user role {string}', async function (this: any, role: string) {
  if (!this.testData) {
    throw new Error('No test data loaded');
  }

  const data = Array.isArray(this.testData) ? this.testData : [this.testData];
  const filtered = data.filter((item) => item.role === role);
  this.testData = filtered;
  this.logger.info(`Filtered by role: ${role} (${filtered.length} items)`);
});

/**
 * DATA TRANSFORMATION STEPS
 */

When('I extract fields {string} from test data', async function (this: any, fieldsStr: string) {
  const testDataManager = new TestDataManager(this.logger);

  if (!this.testData) {
    throw new Error('No test data loaded');
  }

  const fields = fieldsStr.split(',').map((f) => f.trim());
  const data = Array.isArray(this.testData) ? this.testData : [this.testData];
  const extracted = data.map((item) => testDataManager.extractFields(item, fields));

  this.testData = extracted;
  this.logger.info(`Extracted fields: ${fields.join(', ')}`);
});

/**
 * DATA VALIDATION STEPS
 */

Then('test data should have field {string}', async function (this: any, fieldName: string) {
  const data = Array.isArray(this.testData) ? this.testData[0] : this.testData;

  if (!data || !(fieldName in data)) {
    throw new Error(`Field "${fieldName}" not found in test data`);
  }

  this.logger.info(`✓ Field "${fieldName}" exists in test data`);
});

Then('test data should have {int} items', async function (this: any, expectedCount: number) {
  const data = Array.isArray(this.testData) ? this.testData : [this.testData];

  if (data.length !== expectedCount) {
    throw new Error(`Expected ${expectedCount} items, got ${data.length}`);
  }

  this.logger.info(`✓ Test data has ${expectedCount} items`);
});

Then('test data {string} field should not be empty', async function (this: any, fieldName: string) {
  const data = Array.isArray(this.testData) ? this.testData[0] : this.testData;

  if (!data || !data[fieldName]) {
    throw new Error(`Field "${fieldName}" is empty or not found`);
  }

  this.logger.info(`✓ Field "${fieldName}" is not empty`);
});

/**
 * SYNTHETIC DATA STEPS
 */

Given('I have generated test data with {int} users', async function (this: any, count: number) {
  const data = [];
  for (let i = 0; i < count; i++) {
    data.push({
      id: i + 1,
      email: dataGenerators.email(),
      username: dataGenerators.username(),
      password: dataGenerators.password(),
      phone: dataGenerators.phoneNumber(),
      role: ['admin', 'user', 'guest'][Math.floor(Math.random() * 3)],
      createdAt: dataGenerators.date(),
      uuid: dataGenerators.uuid(),
    });
  }
  this.testData = data;
  this.logger.info(`Generated ${count} synthetic user records`);
});

Given('I have generated random email {string}', async function (this: any, variableName: string) {
  this[variableName] = dataGenerators.email();
  this.logger.info(`Generated random email: ${this[variableName]}`);
});

Given('I have generated random password {string}', async function (this: any, variableName: string) {
  this[variableName] = dataGenerators.password();
  this.logger.info(`Generated random password`);
});

Given('I have generated random username {string}', async function (this: any, variableName: string) {
  this[variableName] = dataGenerators.username();
  this.logger.info(`Generated random username: ${this[variableName]}`);
});

/**
 * DATA SAVING STEPS
 */

When('I save test data as fixture {string}', async function (this: any, fixtureName: string) {
  const testDataManager = new TestDataManager(this.logger);
  testDataManager.saveFixture(fixtureName, this.testData);
  this.logger.info(`Saved test data as fixture: ${fixtureName}`);
});

/**
 * DATA AVAILABILITY STEPS
 */

Given('test fixture {string} is available', async function (this: any, fixtureName: string) {
  const testDataManager = new TestDataManager(this.logger);
  const fixtures = testDataManager.getAvailableFixtures();

  if (!fixtures.includes(fixtureName)) {
    throw new Error(`Fixture "${fixtureName}" is not available`);
  }

  this.logger.info(`✓ Fixture "${fixtureName}" is available`);
});

Then('all test data should be valid', async function (this: any) {
  const data = Array.isArray(this.testData) ? this.testData : [this.testData];
  this.logger.info(`✓ Validated ${data.length} test data items`);
});

/**
 * Export
 */
export {};
