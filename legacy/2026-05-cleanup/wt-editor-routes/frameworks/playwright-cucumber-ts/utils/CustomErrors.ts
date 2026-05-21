/**
 * Custom Error Classes
 * Provides descriptive error messages for better debugging
 */

export class ElementNotFoundError extends Error {
  constructor(element: string, page: string, selector?: string) {
    const message = selector
      ? `Element "${element}" not found on ${page} using selector: ${selector}`
      : `Element "${element}" not found on ${page}`;
    super(message);
    this.name = 'ElementNotFoundError';
    Object.setPrototypeOf(this, ElementNotFoundError.prototype);
  }
}

export class PageNotInitializedError extends Error {
  constructor(pageName: string, action: string) {
    super(`${pageName} is not initialized. Please ${action} first.`);
    this.name = 'PageNotInitializedError';
    Object.setPrototypeOf(this, PageNotInitializedError.prototype);
  }
}

export class InvalidDataError extends Error {
  constructor(field: string, value: unknown, expected: string) {
    super(`Invalid ${field}: ${String(value)}. ${expected}`);
    this.name = 'InvalidDataError';
    Object.setPrototypeOf(this, InvalidDataError.prototype);
  }
}

export class ApiRequestError extends Error {
  constructor(method: string, url: string, statusCode: number, message?: string) {
    const errorMessage = message || `API request failed: ${method} ${url} returned ${statusCode}`;
    super(errorMessage);
    this.name = 'ApiRequestError';
    Object.setPrototypeOf(this, ApiRequestError.prototype);
  }
}

export class TestDataLoadError extends Error {
  constructor(fileName: string, reason: string) {
    super(`Failed to load test data from ${fileName}: ${reason}`);
    this.name = 'TestDataLoadError';
    Object.setPrototypeOf(this, TestDataLoadError.prototype);
  }
}

export class MissingEnvironmentVariableError extends Error {
  constructor(variableName: string) {
    super(`Missing required environment variable: ${variableName}`);
    this.name = 'MissingEnvironmentVariableError';
    Object.setPrototypeOf(this, MissingEnvironmentVariableError.prototype);
  }
}
