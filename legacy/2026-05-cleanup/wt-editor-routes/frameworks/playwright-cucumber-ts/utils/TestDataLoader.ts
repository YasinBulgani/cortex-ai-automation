/**
 * Test Data Loader
 * Utility for loading and managing test data from JSON files
 */

import * as fs from 'fs';
import * as path from 'path';
import { TestDataLoadError } from './CustomErrors';
import { Logger } from './Logger';

export class TestDataLoader {
  private static readonly TEST_DATA_DIR = path.join(__dirname, '../test-data');

  /**
   * Load JSON data from file
   */
  static loadJson<T>(filename: string, validator?: (data: unknown) => data is T): T {
    const filePath = path.join(this.TEST_DATA_DIR, filename);
    
    if (!fs.existsSync(filePath)) {
      throw new TestDataLoadError(filename, `File not found: ${filePath}`);
    }

    try {
      const fileContent = fs.readFileSync(filePath, 'utf-8');
      const parsed = JSON.parse(fileContent) as T;
      
      if (validator && !validator(parsed)) {
        throw new TestDataLoadError(filename, 'Data validation failed');
      }
      
      Logger.debug(`Test data loaded successfully: ${filename}`);
      return parsed;
    } catch (error) {
      if (error instanceof TestDataLoadError) {
        throw error;
      }
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new TestDataLoadError(filename, errorMessage);
    }
  }

  /**
   * Load API credentials
   */
  static loadApiCredentials(): {
    validUsers: Array<{ username: string; password: string; description: string }>;
    invalidUsers: Array<{ username: string; password: string; description: string }>;
  } {
    return this.loadJson<{
      validUsers: Array<{ username: string; password: string; description: string }>;
      invalidUsers: Array<{ username: string; password: string; description: string }>;
    }>('api-credentials.json');
  }

  /**
   * Load API endpoints configuration
   */
  static loadApiEndpoints(): {
    baseUrl: string;
    endpoints: Record<string, string>;
    timeouts: Record<string, number>;
    performanceThresholds: Record<string, number>;
  } {
    return this.loadJson<{
      baseUrl: string;
      endpoints: Record<string, string>;
      timeouts: Record<string, number>;
      performanceThresholds: Record<string, number>;
    }>('api-endpoints.json');
  }

  /**
   * Load web selectors
   */
  static loadWebSelectors(): Record<string, unknown> {
    const data = this.loadJson<Record<string, unknown>>('web-selectors.json');
    
    if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
      throw new TestDataLoadError('web-selectors.json', 'Empty or invalid selector data');
    }
    
    return data;
  }

  /**
   * Get random valid user
   */
  static getRandomValidUser(): { username: string; password: string } {
    const credentials = this.loadApiCredentials();
    const users = credentials.validUsers;
    const randomIndex = Math.floor(Math.random() * users.length);
    return {
      username: users[randomIndex].username,
      password: users[randomIndex].password
    };
  }

  /**
   * Get random invalid user
   */
  static getRandomInvalidUser(): { username: string; password: string } {
    const credentials = this.loadApiCredentials();
    const users = credentials.invalidUsers;
    const randomIndex = Math.floor(Math.random() * users.length);
    return {
      username: users[randomIndex].username,
      password: users[randomIndex].password
    };
  }
}
