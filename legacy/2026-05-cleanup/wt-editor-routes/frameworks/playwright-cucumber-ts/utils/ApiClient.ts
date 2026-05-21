/**
 * API Client
 * Generic HTTP client wrapper for API testing
 */

import { APIRequestContext, APIResponse } from 'playwright';

export interface ApiRequestOptions {
  headers?: Record<string, string>;
  params?: Record<string, string | number>;
  data?: Record<string, unknown> | unknown[];
  token?: string | null;
}

export class ApiClient {
  private apiContext: APIRequestContext;
  private baseUrl: string;

  constructor(apiContext: APIRequestContext, baseUrl: string = 'https://dummyjson.com') {
    this.apiContext = apiContext;
    this.baseUrl = baseUrl;
  }

  private buildUrl(endpoint: string, params?: Record<string, string | number>): string {
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
    
    if (params && Object.keys(params).length > 0) {
      const queryString = new URLSearchParams(
        Object.entries(params).reduce((acc, [key, value]) => {
          acc[key] = String(value);
          return acc;
        }, {} as Record<string, string>)
      ).toString();
      return `${url}?${queryString}`;
    }
    
    return url;
  }

  private buildHeaders(customHeaders?: Record<string, string>, token?: string | null): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...customHeaders
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  async get(endpoint: string, options: ApiRequestOptions = {}): Promise<APIResponse> {
    const url = this.buildUrl(endpoint, options.params);
    const headers = this.buildHeaders(options.headers, options.token);
    return await this.apiContext.get(url, { headers });
  }

  async post(endpoint: string, options: ApiRequestOptions = {}): Promise<APIResponse> {
    const url = this.buildUrl(endpoint, options.params);
    const headers = this.buildHeaders(options.headers, options.token);
    return await this.apiContext.post(url, {
      headers,
      data: options.data
    });
  }

  async put(endpoint: string, options: ApiRequestOptions = {}): Promise<APIResponse> {
    const url = this.buildUrl(endpoint, options.params);
    const headers = this.buildHeaders(options.headers, options.token);
    return await this.apiContext.put(url, {
      headers,
      data: options.data
    });
  }

  async delete(endpoint: string, options: ApiRequestOptions = {}): Promise<APIResponse> {
    const url = this.buildUrl(endpoint, options.params);
    const headers = this.buildHeaders(options.headers, options.token);
    return await this.apiContext.delete(url, { headers });
  }

  async parseJsonResponse<T = unknown>(response: APIResponse): Promise<T> {
    return await response.json() as T;
  }

  assertStatusCode(response: APIResponse, expectedStatusCode: number): void {
    const actualStatusCode = response.status();
    if (actualStatusCode !== expectedStatusCode) {
      throw new Error(
        `Expected status code ${expectedStatusCode}, but got ${actualStatusCode}. ` +
        `URL: ${response.url()}`
      );
    }
  }
}
