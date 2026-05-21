/**
 * Test Data Loader Utility
 *
 * Loads test data from JSON fixtures
 * Provides typed access to test data
 */

import * as fs from 'fs';
import * as path from 'path';
import { DataValidationError } from './errors';

/**
 * Test data interface
 */
export interface TestData {
  [key: string]: any;
}

/**
 * Test Data Loader Class
 */
export class TestDataLoader {
  private dataCache: Map<string, TestData> = new Map();
  private fixturesDir: string;

  constructor(fixturesDir: string = './data/fixtures') {
    this.fixturesDir = fixturesDir;
  }

  /**
   * Load fixture file
   */
  loadFixture(filename: string): TestData {
    // Check cache first
    if (this.dataCache.has(filename)) {
      return this.dataCache.get(filename)!;
    }

    // Load from file
    const filepath = path.join(this.fixturesDir, `${filename}.json`);

    if (!fs.existsSync(filepath)) {
      throw new DataValidationError(filename, [], `Fixture file not found: ${filepath}`);
    }

    try {
      const content = fs.readFileSync(filepath, 'utf-8');
      const data = JSON.parse(content);

      // Cache for future use
      this.dataCache.set(filename, data);

      return data;
    } catch (error) {
      throw new DataValidationError(filename, [], `Failed to parse fixture: ${String(error)}`);
    }
  }

  /**
   * Get specific data from fixture
   */
  get<T = any>(fixture: string, key: string): T {
    const data = this.loadFixture(fixture);

    if (!(key in data)) {
      throw new DataValidationError(fixture, [key], `Key not found: ${key}`);
    }

    return data[key] as T;
  }

    /**
   * Get all data from fixture
   */
  getAll<T = any>(fixture: string): T {
    return this.loadFixture(fixture) as T;
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.dataCache.clear();
  }

  /**
   * Merge fixture data
   */
  merge(...fixtures: string[]): TestData {
    const merged: TestData = {};

    for (const fixture of fixtures) {
      const data = this.loadFixture(fixture);
      Object.assign(merged, data);
    }

    return merged;
  }

  /**
   * Get random item from array
   */
  getRandomFromArray<T = any>(fixture: string, key: string): T {
    const array = this.get<any[]>(fixture, key);

    if (!Array.isArray(array)) {
      throw new DataValidationError(fixture, [key], `Value is not an array: ${key}`);
    }

    return array[Math.floor(Math.random() * array.length)] as T;
  }
}

/**
 * Global test data loader instance
 */
let globalLoader: TestDataLoader | null = null;

/**
 * Get global loader instance
 */
export function getTestDataLoader(fixturesDir?: string): TestDataLoader {
  if (!globalLoader) {
    globalLoader = new TestDataLoader(fixturesDir);
  }
  return globalLoader;
}

/**
 * Reset loader (useful for testing)
 */
export function resetTestDataLoader(): void {
  if (globalLoader) {
    globalLoader.clearCache();
    globalLoader = null;
  }
}

/**
 * Export singleton
 */
export const testDataLoader = getTestDataLoader();
