/**
 * Test Data Management Utility
 * Comprehensive test data handling, generation, and validation
 */

import * as fs from 'fs';
import * as path from 'path';
import { Logger } from './Logger';

interface TestData {
  [key: string]: any;
}

interface TestDataSchema {
  name: string;
  properties: Record<string, any>;
  required?: string[];
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
}

interface DataGeneratorOptions {
  count?: number;
  unique?: boolean;
  seed?: number;
}

/**
 * Test Data Manager Class
 */
export class TestDataManager {
  private dataDir: string;
  private logger: Logger;
  private cache: Map<string, TestData[]> = new Map();
  private schemas: Map<string, TestDataSchema> = new Map();

  constructor(logger: Logger, dataDir?: string) {
    this.logger = logger;
    this.dataDir = dataDir || path.join(process.cwd(), 'data', 'fixtures');
    this.ensureDirectory();
    this.loadSchemas();
  }

  /**
   * Ensure data directory exists
   */
  private ensureDirectory(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
      this.logger.info(`Created data directory: ${this.dataDir}`);
    }
  }

  /**
   * Load data schemas
   */
  private loadSchemas(): void {
    const schemasDir = path.join(this.dataDir, 'schemas');
    if (!fs.existsSync(schemasDir)) {
      return;
    }

    try {
      const files = fs.readdirSync(schemasDir).filter((f) => f.endsWith('.json'));
      for (const file of files) {
        const schemaPath = path.join(schemasDir, file);
        const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf-8'));
        const schemaName = file.replace('.json', '');
        this.schemas.set(schemaName, schema);
      }
      this.logger.debug(`Loaded ${this.schemas.size} data schemas`);
    } catch (error) {
      this.logger.warn('Failed to load schemas', { error });
    }
  }

  /**
   * Load test data from fixture file
   */
  loadFixture(fixtureName: string): TestData[] {
    // Check cache first
    if (this.cache.has(fixtureName)) {
      return this.cache.get(fixtureName)!;
    }

    const fixturePath = path.join(this.dataDir, `${fixtureName}.json`);

    try {
      if (!fs.existsSync(fixturePath)) {
        throw new Error(`Fixture file not found: ${fixturePath}`);
      }

      const data = JSON.parse(fs.readFileSync(fixturePath, 'utf-8'));
      const dataArray = Array.isArray(data) ? data : [data];

      this.cache.set(fixtureName, dataArray);
      this.logger.debug(`Loaded fixture: ${fixtureName} (${dataArray.length} items)`);

      return dataArray;
    } catch (error) {
      this.logger.error(`Failed to load fixture: ${fixtureName}`, { error });
      throw error;
    }
  }

  /**
   * Get single test data item
   */
  getTestData(fixtureName: string, index: number = 0): TestData {
    const data = this.loadFixture(fixtureName);
    if (index >= data.length) {
      throw new Error(`Index ${index} out of bounds for fixture ${fixtureName}`);
    }
    return data[index];
  }

  /**
   * Get random test data item
   */
  getRandomTestData(fixtureName: string): TestData {
    const data = this.loadFixture(fixtureName);
    const randomIndex = Math.floor(Math.random() * data.length);
    return data[randomIndex];
  }

  /**
   * Get multiple random items
   */
  getRandomTestDataSet(fixtureName: string, count: number, unique: boolean = false): TestData[] {
    const data = this.loadFixture(fixtureName);

    if (unique && count > data.length) {
      throw new Error(
        `Cannot get ${count} unique items from ${fixtureName} (only ${data.length} available)`
      );
    }

    const result: TestData[] = [];
    const usedIndices = new Set<number>();

    for (let i = 0; i < count; i++) {
      let randomIndex: number;

      if (unique) {
        do {
          randomIndex = Math.floor(Math.random() * data.length);
        } while (usedIndices.has(randomIndex));
        usedIndices.add(randomIndex);
      } else {
        randomIndex = Math.floor(Math.random() * data.length);
      }

      result.push(data[randomIndex]);
    }

    return result;
  }

  /**
   * Filter test data
   */
  filterTestData(fixtureName: string, predicate: (item: TestData) => boolean): TestData[] {
    const data = this.loadFixture(fixtureName);
    return data.filter(predicate);
  }

  /**
   * Transform test data
   */
  transformTestData(
    fixtureName: string,
    transformer: (item: TestData) => TestData
  ): TestData[] {
    const data = this.loadFixture(fixtureName);
    return data.map(transformer);
  }

  /**
   * Merge multiple fixtures
   */
  mergeFixtures(...fixtureNames: string[]): TestData[] {
    const merged: TestData[] = [];

    for (const fixtureName of fixtureNames) {
      const data = this.loadFixture(fixtureName);
      merged.push(...data);
    }

    this.logger.debug(`Merged ${fixtureNames.length} fixtures (${merged.length} total items)`);
    return merged;
  }

  /**
   * Save test data to fixture file
   */
  saveFixture(fixtureName: string, data: TestData | TestData[]): void {
    const fixturePath = path.join(this.dataDir, `${fixtureName}.json`);

    try {
      fs.writeFileSync(fixturePath, JSON.stringify(data, null, 2));
      this.cache.set(fixtureName, Array.isArray(data) ? data : [data]);
      this.logger.info(`Fixture saved: ${fixtureName}`);
    } catch (error) {
      this.logger.error(`Failed to save fixture: ${fixtureName}`, { error });
      throw error;
    }
  }

  /**
   * Validate test data against schema
   */
  validateData(fixtureName: string, data: TestData): ValidationResult {
    const schema = this.schemas.get(fixtureName);

    if (!schema) {
      return { valid: true, errors: [] };
    }

    const errors: string[] = [];

    // Check required fields
    if (schema.required) {
      for (const field of schema.required) {
        if (!(field in data)) {
          errors.push(`Missing required field: ${field}`);
        }
      }
    }

    // Check field types
    for (const [key, value] of Object.entries(data)) {
      const fieldSchema = schema.properties[key];
      if (!fieldSchema) {
        continue;
      }

      const expectedType = fieldSchema.type;
      const actualType = typeof value;

      if (expectedType && actualType !== expectedType) {
        errors.push(`Field ${key}: expected ${expectedType}, got ${actualType}`);
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Generate synthetic test data
   */
  generateSyntheticData(
    count: number = 10,
    generators: Record<string, () => any>
  ): TestData[] {
    const data: TestData[] = [];

    for (let i = 0; i < count; i++) {
      const item: TestData = {};
      for (const [key, generator] of Object.entries(generators)) {
        item[key] = generator();
      }
      data.push(item);
    }

    this.logger.debug(`Generated ${count} synthetic test data items`);
    return data;
  }

  /**
   * Clear cache
   */
  clearCache(fixtureName?: string): void {
    if (fixtureName) {
      this.cache.delete(fixtureName);
      this.logger.debug(`Cleared cache for fixture: ${fixtureName}`);
    } else {
      this.cache.clear();
      this.logger.debug('Cleared all fixture cache');
    }
  }

  /**
   * Get list of available fixtures
   */
  getAvailableFixtures(): string[] {
    try {
      const files = fs.readdirSync(this.dataDir).filter((f) => f.endsWith('.json'));
      return files.map((f) => f.replace('.json', ''));
    } catch (error) {
      this.logger.error('Failed to list fixtures', { error });
      return [];
    }
  }

  /**
   * Get data directory
   */
  getDataDir(): string {
    return this.dataDir;
  }

  /**
   * Combine test data with defaults
   */
  mergeWithDefaults(testData: TestData, defaults: TestData): TestData {
    return { ...defaults, ...testData };
  }

  /**
   * Extract specific fields from data
   */
  extractFields(data: TestData, fields: string[]): TestData {
    const extracted: TestData = {};
    for (const field of fields) {
      if (field in data) {
        extracted[field] = data[field];
      }
    }
    return extracted;
  }

  /**
   * Create data matrix for parametrized tests
   */
  createDataMatrix(
    fixtureName: string,
    parameterNames: string[]
  ): Record<string, any>[] {
    const data = this.loadFixture(fixtureName);
    return data.map((item) => {
      const matrixItem: Record<string, any> = {};
      for (const param of parameterNames) {
        matrixItem[param] = item[param];
      }
      return matrixItem;
    });
  }
}

/**
 * Common data generators
 */
export const dataGenerators = {
  /**
   * Generate random email
   */
  email(): string {
    const random = Math.random().toString(36).substring(7);
    return `test.${random}@example.com`;
  },

  /**
   * Generate random username
   */
  username(): string {
    const adjectives = ['happy', 'lazy', 'sad', 'quick', 'slow'];
    const nouns = ['cat', 'dog', 'fox', 'bear', 'wolf'];
    const adj = adjectives[Math.floor(Math.random() * adjectives.length)];
    const noun = nouns[Math.floor(Math.random() * nouns.length)];
    const num = Math.floor(Math.random() * 10000);
    return `${adj}${noun}${num}`;
  },

  /**
   * Generate random password
   */
  password(length: number = 12): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%';
    let password = '';
    for (let i = 0; i < length; i++) {
      password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return password;
  },

  /**
   * Generate random phone number
   */
  phoneNumber(): string {
    return `+1${Math.floor(Math.random() * 9000000000) + 1000000000}`;
  },

  /**
   * Generate random number
   */
  number(min: number = 0, max: number = 100): number {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  },

  /**
   * Generate random string
   */
  string(length: number = 10): string {
    return Math.random().toString(36).substring(2, 2 + length);
  },

  /**
   * Generate random date
   */
  date(from: Date = new Date(2020, 0, 1), to: Date = new Date()): Date {
    return new Date(from.getTime() + Math.random() * (to.getTime() - from.getTime()));
  },

  /**
   * Generate UUID
   */
  uuid(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  },
};

/**
 * Helper function
 */
export function createTestDataManager(logger: Logger): TestDataManager {
  return new TestDataManager(logger);
}
