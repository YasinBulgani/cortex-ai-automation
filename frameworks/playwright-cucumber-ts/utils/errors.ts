/**
 * Custom Error Classes for BGTS_Test_Donusum
 *
 * Provides a hierarchy of custom error types for better error handling
 * and debugging throughout the test framework.
 */

/**
 * Base custom error class
 * All framework errors should extend this class
 */
export class TestError extends Error {
  readonly code: string;
  readonly timestamp: Date;
  readonly context: Record<string, any>;

  constructor(code: string, message: string, context?: Record<string, any>) {
    super(message);
    this.code = code;
    this.timestamp = new Date();
    this.context = context || {};

    // Maintain proper prototype chain
    Object.setPrototypeOf(this, TestError.prototype);

    // Capture stack trace
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }

  /**
   * Serialize error to JSON for logging
   */
  toJSON() {
    return {
      code: this.code,
      message: this.message,
      timestamp: this.timestamp.toISOString(),
      stack: this.stack,
      context: this.context,
    };
  }

  /**
   * Get formatted error message
   */
  toString(): string {
    return `[${this.code}] ${this.message}`;
  }
}

/**
 * Page load errors
 * Thrown when page fails to load or navigate
 */
export class PageLoadError extends TestError {
  constructor(url: string, reason?: string) {
    super(
      'PAGE_LOAD_FAILED',
      `Failed to load page: ${url}${reason ? ` (${reason})` : ''}`,
      { url, reason }
    );
    Object.setPrototypeOf(this, PageLoadError.prototype);
  }
}

/**
 * Element not found errors
 * Thrown when element selector doesn't match any element
 */
export class ElementNotFoundError extends TestError {
  constructor(selector: string, context?: string) {
    super(
      'ELEMENT_NOT_FOUND',
      `Element not found with selector: ${selector}${context ? ` in ${context}` : ''}`,
      { selector, context }
    );
    Object.setPrototypeOf(this, ElementNotFoundError.prototype);
  }
}

/**
 * Timeout errors
 * Thrown when action exceeds timeout threshold
 */
export class TimeoutError extends TestError {
  readonly timeoutMs: number;
  readonly action: string;

  constructor(action: string, timeoutMs: number) {
    super(
      'TIMEOUT',
      `Timeout waiting for "${action}" after ${timeoutMs}ms`,
      { action, timeoutMs }
    );
    this.timeoutMs = timeoutMs;
    this.action = action;
    Object.setPrototypeOf(this, TimeoutError.prototype);
  }
}

/**
 * Assertion errors
 * Thrown when test assertion fails
 */
export class AssertionError extends TestError {
  readonly actual: any;
  readonly expected: any;

  constructor(message: string, expected?: any, actual?: any) {
    super(
      'ASSERTION_FAILED',
      message,
      { expected, actual }
    );
    this.expected = expected;
    this.actual = actual;
    Object.setPrototypeOf(this, AssertionError.prototype);
  }
}

/**
 * Configuration errors
 * Thrown when configuration is missing or invalid
 */
export class ConfigError extends TestError {
  constructor(configKey: string, reason?: string) {
    super(
      'CONFIG_ERROR',
      `Configuration error for key "${configKey}"${reason ? `: ${reason}` : ''}`,
      { configKey, reason }
    );
    Object.setPrototypeOf(this, ConfigError.prototype);
  }
}

/**
 * API errors
 * Thrown when API request fails
 */
export class APIError extends TestError {
  readonly statusCode?: number;
  readonly endpoint: string;
  readonly method: string;

  constructor(endpoint: string, method: string, statusCode?: number, message?: string) {
    super(
      'API_ERROR',
      `API ${method} ${endpoint} failed${statusCode ? ` with status ${statusCode}` : ''}${message ? `: ${message}` : ''}`,
      { endpoint, method, statusCode, message }
    );
    this.statusCode = statusCode;
    this.endpoint = endpoint;
    this.method = method;
    Object.setPrototypeOf(this, APIError.prototype);
  }
}

/**
 * Database errors
 * Thrown when database operation fails
 */
export class DatabaseError extends TestError {
  readonly query?: string;
  readonly operation: string;

  constructor(operation: string, message: string, query?: string) {
    super(
      'DATABASE_ERROR',
      `Database error during ${operation}: ${message}`,
      { operation, query }
    );
    this.operation = operation;
    this.query = query;
    Object.setPrototypeOf(this, DatabaseError.prototype);
  }
}

/**
 * Browser errors
 * Thrown when browser/playwright operation fails
 */
export class BrowserError extends TestError {
  readonly action: string;

  constructor(action: string, message: string) {
    super(
      'BROWSER_ERROR',
      `Browser error during ${action}: ${message}`,
      { action }
    );
    this.action = action;
    Object.setPrototypeOf(this, BrowserError.prototype);
  }
}

/**
 * Step definition errors
 * Thrown when step definition is missing or invalid
 */
export class StepDefinitionError extends TestError {
  readonly stepText: string;

  constructor(stepText: string, reason: string) {
    super(
      'STEP_DEFINITION_ERROR',
      `Step definition error for "${stepText}": ${reason}`,
      { stepText, reason }
    );
    this.stepText = stepText;
    Object.setPrototypeOf(this, StepDefinitionError.prototype);
  }
}

/**
 * Data validation errors
 * Thrown when test data validation fails
 */
export class DataValidationError extends TestError {
  readonly dataType: string;
  readonly invalidFields: string[];

  constructor(dataType: string, invalidFields: string[], message?: string) {
    super(
      'DATA_VALIDATION_ERROR',
      `Data validation failed for ${dataType}${message ? `: ${message}` : ''}`,
      { dataType, invalidFields, message }
    );
    this.dataType = dataType;
    this.invalidFields = invalidFields;
    Object.setPrototypeOf(this, DataValidationError.prototype);
  }
}

/**
 * Screenshot capture errors
 * Thrown when screenshot capture fails
 */
export class ScreenshotError extends TestError {
  readonly filepath?: string;

  constructor(reason: string, filepath?: string) {
    super(
      'SCREENSHOT_ERROR',
      `Screenshot capture failed: ${reason}${filepath ? ` (${filepath})` : ''}`,
      { reason, filepath }
    );
    this.filepath = filepath;
    Object.setPrototypeOf(this, ScreenshotError.prototype);
  }
}

/**
 * Test execution errors
 * Thrown when test execution fails
 */
export class TestExecutionError extends TestError {
  readonly testName: string;
  readonly phase: 'setup' | 'execution' | 'teardown';

  constructor(testName: string, phase: 'setup' | 'execution' | 'teardown', message: string) {
    super(
      'TEST_EXECUTION_ERROR',
      `Test execution error in ${phase} phase for "${testName}": ${message}`,
      { testName, phase }
    );
    this.testName = testName;
    this.phase = phase;
    Object.setPrototypeOf(this, TestExecutionError.prototype);
  }
}

/**
 * Error type guard functions
 */

export function isTestError(error: unknown): error is TestError {
  return error instanceof TestError;
}

export function isPageLoadError(error: unknown): error is PageLoadError {
  return error instanceof PageLoadError;
}

export function isElementNotFoundError(error: unknown): error is ElementNotFoundError {
  return error instanceof ElementNotFoundError;
}

export function isTimeoutError(error: unknown): error is TimeoutError {
  return error instanceof TimeoutError;
}

export function isAssertionError(error: unknown): error is AssertionError {
  return error instanceof AssertionError;
}

export function isAPIError(error: unknown): error is APIError {
  return error instanceof APIError;
}

/**
 * Error handler helper
 * Converts unknown errors to TestError if needed
 */
export function normalizeError(error: unknown): TestError {
  if (error instanceof TestError) {
    return error;
  }

  if (error instanceof Error) {
    return new TestError('UNKNOWN_ERROR', error.message, {
      originalError: error.constructor.name,
      stack: error.stack,
    });
  }

  return new TestError('UNKNOWN_ERROR', String(error));
}
