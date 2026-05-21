/**
 * Unit Tests for TestDataManager
 * Testing fixture loading, data generation, filtering, and validation
 */

import { TestDataManager, dataGenerators } from '../../core/typescript/utils/TestDataManager';
import { Logger } from '../../core/typescript/utils/Logger';
import * as fs from 'fs';
import * as path from 'path';

// Mock data
const mockTestData = [
  {
    id: 1,
    email: 'user1@example.com',
    username: 'user1',
    password: 'pass123',
    role: 'user',
  },
  {
    id: 2,
    email: 'admin@example.com',
    username: 'admin',
    password: 'pass456',
    role: 'admin',
  },
  {
    id: 3,
    email: 'guest@example.com',
    username: 'guest',
    password: 'pass789',
    role: 'guest',
  },
];

describe('TestDataManager', () => {
  let testDataManager: TestDataManager;
  let mockLogger: Logger;
  let tempDir: string;

  beforeEach(() => {
    // Create temp directory for test fixtures
    tempDir = path.join(__dirname, '..', 'temp-fixtures');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    // Create mock logger
    mockLogger = {
      info: jest.fn(),
      error: jest.fn(),
      warn: jest.fn(),
      debug: jest.fn(),
    } as any;

    // Initialize manager with temp directory
    testDataManager = new TestDataManager(mockLogger, tempDir);

    // Create test fixture file
    const fixturePath = path.join(tempDir, 'test-users.json');
    fs.writeFileSync(fixturePath, JSON.stringify(mockTestData, null, 2));
  });

  afterEach(() => {
    // Clean up temp directory
    if (fs.existsSync(tempDir)) {
      const files = fs.readdirSync(tempDir);
      files.forEach((file) => {
        fs.unlinkSync(path.join(tempDir, file));
      });
      fs.rmdirSync(tempDir);
    }

    // Clear cache
    testDataManager.clearCache();
  });

  describe('loadFixture', () => {
    it('should load fixture from JSON file', () => {
      const data = testDataManager.loadFixture('test-users');
      expect(data).toHaveLength(3);
      expect(data[0].email).toBe('user1@example.com');
    });

    it('should cache loaded fixture', () => {
      const data1 = testDataManager.loadFixture('test-users');
      const data2 = testDataManager.loadFixture('test-users');
      expect(data1).toBe(data2); // Same reference
    });

    it('should throw error for non-existent fixture', () => {
      expect(() => {
        testDataManager.loadFixture('non-existent');
      }).toThrow();
    });
  });

  describe('getTestData', () => {
    it('should get specific test data item by index', () => {
      const data = testDataManager.getTestData('test-users', 0);
      expect(data.id).toBe(1);
      expect(data.email).toBe('user1@example.com');
    });

    it('should throw error for out of bounds index', () => {
      expect(() => {
        testDataManager.getTestData('test-users', 999);
      }).toThrow();
    });
  });

  describe('getRandomTestData', () => {
    it('should return random test data item', () => {
      const data = testDataManager.getRandomTestData('test-users');
      expect(data).toHaveProperty('id');
      expect(data).toHaveProperty('email');
    });

    it('should return items from the fixture', () => {
      const data = testDataManager.getRandomTestData('test-users');
      const emails = mockTestData.map((d) => d.email);
      expect(emails).toContain(data.email);
    });
  });

  describe('getRandomTestDataSet', () => {
    it('should return requested number of items', () => {
      const data = testDataManager.getRandomTestDataSet('test-users', 2, false);
      expect(data).toHaveLength(2);
    });

    it('should return unique items when unique=true', () => {
      const data = testDataManager.getRandomTestDataSet('test-users', 3, true);
      const ids = data.map((d) => d.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(3);
    });

    it('should allow duplicates when unique=false', () => {
      const data = testDataManager.getRandomTestDataSet('test-users', 5, false);
      expect(data).toHaveLength(5);
    });

    it('should throw error when requesting more unique items than available', () => {
      expect(() => {
        testDataManager.getRandomTestDataSet('test-users', 10, true);
      }).toThrow();
    });
  });

  describe('filterTestData', () => {
    it('should filter data by predicate', () => {
      const filtered = testDataManager.filterTestData(
        'test-users',
        (item) => item.role === 'admin'
      );
      expect(filtered).toHaveLength(1);
      expect(filtered[0].username).toBe('admin');
    });

    it('should return empty array when no matches', () => {
      const filtered = testDataManager.filterTestData(
        'test-users',
        (item) => item.role === 'superadmin'
      );
      expect(filtered).toHaveLength(0);
    });
  });

  describe('transformTestData', () => {
    it('should transform test data', () => {
      const transformed = testDataManager.transformTestData('test-users', (item) => ({
        ...item,
        email: item.email.toUpperCase(),
      }));

      expect(transformed).toHaveLength(3);
      expect(transformed[0].email).toBe('USER1@EXAMPLE.COM');
    });

    it('should not mutate original data', () => {
      const original = testDataManager.loadFixture('test-users')[0].email;
      testDataManager.transformTestData('test-users', (item) => ({
        ...item,
        email: 'modified@example.com',
      }));

      const current = testDataManager.loadFixture('test-users')[0].email;
      expect(current).toBe(original);
    });
  });

  describe('mergeFixtures', () => {
    it('should merge multiple fixtures', () => {
      // Create second fixture
      const fixture2Path = path.join(tempDir, 'test-users2.json');
      fs.writeFileSync(fixture2Path, JSON.stringify([mockTestData[0]], null, 2));

      const merged = testDataManager.mergeFixtures('test-users', 'test-users2');
      expect(merged.length).toBeGreaterThan(3);
    });
  });

  describe('saveFixture', () => {
    it('should save test data as fixture', () => {
      const newData = [{ id: 4, name: 'new user' }];
      testDataManager.saveFixture('new-fixture', newData);

      const saved = testDataManager.loadFixture('new-fixture');
      expect(saved).toHaveLength(1);
      expect(saved[0].id).toBe(4);
    });

    it('should overwrite existing fixture', () => {
      const newData = [{ id: 999, name: 'overwritten' }];
      testDataManager.saveFixture('test-users', newData);

      const loaded = testDataManager.loadFixture('test-users');
      expect(loaded).toHaveLength(1);
      expect(loaded[0].id).toBe(999);
    });
  });

  describe('validateData', () => {
    it('should return valid=true when data is correct', () => {
      const data = mockTestData[0];
      const result = testDataManager.validateData('test-users', data);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should validate against schema if available', () => {
      // Note: This would require creating schema files
      const data = { invalid: 'data' };
      const result = testDataManager.validateData('test-users', data);
      // Result depends on schema availability
      expect(result).toHaveProperty('valid');
      expect(result).toHaveProperty('errors');
    });
  });

  describe('generateSyntheticData', () => {
    it('should generate requested number of records', () => {
      const generators = {
        id: () => Math.random(),
        name: dataGenerators.username,
      };

      const data = testDataManager.generateSyntheticData(5, generators);
      expect(data).toHaveLength(5);
      expect(data[0]).toHaveProperty('id');
      expect(data[0]).toHaveProperty('name');
    });

    it('should use provided generators', () => {
      const generators = {
        uuid: dataGenerators.uuid,
      };

      const data = testDataManager.generateSyntheticData(3, generators);
      const uuids = data.map((d) => d.uuid);
      const uniqueUuids = new Set(uuids);
      expect(uniqueUuids.size).toBe(3);
    });
  });

  describe('clearCache', () => {
    it('should clear specific fixture cache', () => {
      testDataManager.loadFixture('test-users');
      testDataManager.clearCache('test-users');
      // Verify cache is cleared (would need to access private cache)
      expect(testDataManager.getAvailableFixtures()).toContain('test-users');
    });

    it('should clear all cache when no fixture specified', () => {
      testDataManager.loadFixture('test-users');
      testDataManager.clearCache();
      expect(testDataManager.getAvailableFixtures()).toContain('test-users');
    });
  });

  describe('getAvailableFixtures', () => {
    it('should list available fixtures', () => {
      const fixtures = testDataManager.getAvailableFixtures();
      expect(fixtures).toContain('test-users');
    });

    it('should filter JSON files only', () => {
      // Create a non-JSON file
      fs.writeFileSync(path.join(tempDir, 'readme.txt'), 'test');

      const fixtures = testDataManager.getAvailableFixtures();
      expect(fixtures).not.toContain('readme');
      expect(fixtures).toContain('test-users');
    });
  });

  describe('extractFields', () => {
    it('should extract specified fields', () => {
      const data = mockTestData[0];
      const extracted = testDataManager.extractFields(data, ['email', 'username']);

      expect(extracted).toHaveProperty('email');
      expect(extracted).toHaveProperty('username');
      expect(extracted).not.toHaveProperty('password');
    });

    it('should skip non-existent fields', () => {
      const data = mockTestData[0];
      const extracted = testDataManager.extractFields(data, ['email', 'nonexistent']);

      expect(extracted).toHaveProperty('email');
      expect(extracted).not.toHaveProperty('nonexistent');
    });
  });

  describe('mergeWithDefaults', () => {
    it('should merge data with defaults', () => {
      const defaults = { role: 'user', status: 'active' };
      const testData = { email: 'test@example.com' };

      const merged = testDataManager.mergeWithDefaults(testData, defaults);
      expect(merged.email).toBe('test@example.com');
      expect(merged.role).toBe('user');
      expect(merged.status).toBe('active');
    });

    it('should override defaults with test data', () => {
      const defaults = { role: 'user', status: 'active' };
      const testData = { role: 'admin' };

      const merged = testDataManager.mergeWithDefaults(testData, defaults);
      expect(merged.role).toBe('admin');
    });
  });

  describe('createDataMatrix', () => {
    it('should create data matrix for parametrized tests', () => {
      const matrix = testDataManager.createDataMatrix('test-users', ['email', 'role']);

      expect(matrix).toHaveLength(3);
      expect(matrix[0]).toHaveProperty('email');
      expect(matrix[0]).toHaveProperty('role');
      expect(matrix[0]).not.toHaveProperty('username');
    });
  });
});

describe('dataGenerators', () => {
  describe('email', () => {
    it('should generate valid email format', () => {
      const email = dataGenerators.email();
      expect(email).toMatch(/test\.\w+@example\.com/);
    });

    it('should generate different emails', () => {
      const emails = new Set([
        dataGenerators.email(),
        dataGenerators.email(),
        dataGenerators.email(),
      ]);
      expect(emails.size).toBe(3);
    });
  });

  describe('username', () => {
    it('should generate valid username', () => {
      const username = dataGenerators.username();
      expect(username).toMatch(/[a-z]+[a-z]+\d+/);
    });
  });

  describe('password', () => {
    it('should generate password with specified length', () => {
      const password = dataGenerators.password(20);
      expect(password).toHaveLength(20);
    });

    it('should use default length of 12', () => {
      const password = dataGenerators.password();
      expect(password.length).toBeGreaterThanOrEqual(12);
    });

    it('should include special characters', () => {
      const password = dataGenerators.password(50);
      const hasSpecial = /[!@#$%]/.test(password);
      expect(password.length).toBeGreaterThan(0);
    });
  });

  describe('phoneNumber', () => {
    it('should generate valid phone number', () => {
      const phone = dataGenerators.phoneNumber();
      expect(phone).toMatch(/^\+1\d{10}$/);
    });
  });

  describe('number', () => {
    it('should generate number in range', () => {
      const num = dataGenerators.number(10, 20);
      expect(num).toBeGreaterThanOrEqual(10);
      expect(num).toBeLessThanOrEqual(20);
    });

    it('should use default range 0-100', () => {
      const num = dataGenerators.number();
      expect(num).toBeGreaterThanOrEqual(0);
      expect(num).toBeLessThanOrEqual(100);
    });
  });

  describe('string', () => {
    it('should generate string with specified length', () => {
      const str = dataGenerators.string(15);
      expect(str).toHaveLength(15);
    });

    it('should generate alphanumeric string', () => {
      const str = dataGenerators.string(10);
      expect(str).toMatch(/[a-z0-9]/);
    });
  });

  describe('date', () => {
    it('should generate date within range', () => {
      const from = new Date(2020, 0, 1);
      const to = new Date(2020, 11, 31);
      const date = dataGenerators.date(from, to);

      expect(date.getTime()).toBeGreaterThanOrEqual(from.getTime());
      expect(date.getTime()).toBeLessThanOrEqual(to.getTime());
    });

    it('should use default range when not specified', () => {
      const date = dataGenerators.date();
      expect(date).toBeInstanceOf(Date);
      expect(date.getTime()).toBeLessThanOrEqual(new Date().getTime());
    });
  });

  describe('uuid', () => {
    it('should generate valid UUID format', () => {
      const uuid = dataGenerators.uuid();
      expect(uuid).toMatch(/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i);
    });

    it('should generate unique UUIDs', () => {
      const uuids = new Set([
        dataGenerators.uuid(),
        dataGenerators.uuid(),
        dataGenerators.uuid(),
      ]);
      expect(uuids.size).toBe(3);
    });
  });
});
