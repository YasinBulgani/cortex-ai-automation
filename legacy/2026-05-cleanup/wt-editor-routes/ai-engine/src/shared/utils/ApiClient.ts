/**
 * Generic HTTP API Client
 * Handles REST API requests with retry logic and error handling
 */

import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import { Logger } from './Logger';
import { APIError, TimeoutError } from './errors';
import { getConfigValue } from '../config';

interface ApiRequestOptions {
  timeout?: number;
  retries?: number;
  headers?: Record<string, string>;
  params?: Record<string, any>;
}

interface ApiResponse<T = any> {
  status: number;
  data: T;
  headers: Record<string, any>;
}

/**
 * API Client class
 */
export class ApiClient {
  private client: AxiosInstance;
  private logger: Logger;
  private baseURL: string;
  private timeout: number;
  private retries: number;
  private retryDelay: number;

  constructor(logger: Logger, baseURL?: string) {
    this.logger = logger;
    this.baseURL = baseURL || getConfigValue<string>('api.baseUrl');
    this.timeout = getConfigValue<number>('api.timeout');
    this.retries = getConfigValue<number>('api.retries');
    this.retryDelay = getConfigValue<number>('api.retryDelay');

    // Create axios instance
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: this.timeout,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'BGTS-Test-Donusum/1.0',
      },
    });

    // Setup interceptors
    this.setupInterceptors();
  }

  /**
   * Setup request/response interceptors
   */
  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        this.logger.debug(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        this.logger.error('Request interceptor error', { error });
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        this.logger.debug(`API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        if (error.response) {
          this.logger.warn(`API Error: ${error.response.status} ${error.config.url}`, {
            status: error.response.status,
            data: error.response.data,
          });
        } else if (error.request) {
          this.logger.error('No response from server', { error });
        } else {
          this.logger.error('Request setup error', { error });
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * GET request
   */
  async get<T = any>(endpoint: string, options?: ApiRequestOptions): Promise<ApiResponse<T>> {
    return this.request<T>('GET', endpoint, undefined, options);
  }

  /**
   * POST request
   */
  async post<T = any>(endpoint: string, data?: any, options?: ApiRequestOptions): Promise<ApiResponse<T>> {
    return this.request<T>('POST', endpoint, data, options);
  }

  /**
   * PUT request
   */
  async put<T = any>(endpoint: string, data?: any, options?: ApiRequestOptions): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', endpoint, data, options);
  }

  /**
   * PATCH request
   */
  async patch<T = any>(endpoint: string, data?: any, options?: ApiRequestOptions): Promise<ApiResponse<T>> {
    return this.request<T>('PATCH', endpoint, data, options);
  }

  /**
   * DELETE request
   */
  async delete<T = any>(endpoint: string, options?: ApiRequestOptions): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', endpoint, undefined, options);
  }

  /**
   * Generic request with retry logic
   */
  private async request<T = any>(
    method: string,
    endpoint: string,
    data?: any,
    options?: ApiRequestOptions
  ): Promise<ApiResponse<T>> {
    const maxRetries = options?.retries ?? this.retries;
    let lastError: AxiosError | Error | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await this.client.request<T>({
          method,
          url: endpoint,
          data,
          timeout: options?.timeout || this.timeout,
          headers: options?.headers,
          params: options?.params,
        });

        return {
          status: response.status,
          data: response.data,
          headers: response.headers,
        };
      } catch (error) {
        lastError = error as AxiosError | Error;

        // Don't retry on client errors (4xx) except 429 and 503
        if (axios.isAxiosError(error) && error.response) {
          const status = error.response.status;
          if (status >= 400 && status < 500 && status !== 429 && status !== 503) {
            throw new APIError(endpoint, method, status, (error.response.data as any)?.message);
          }
        }

        // Check if should retry
        if (attempt < maxRetries) {
          const delay = this.retryDelay * Math.pow(2, attempt); // Exponential backoff
          this.logger.warn(`Request failed, retrying in ${delay}ms (attempt ${attempt + 1}/${maxRetries})`);
          await this.sleep(delay);
          continue;
        }

        // All retries exhausted
        break;
      }
    }

    // All attempts failed
    if (axios.isAxiosError(lastError)) {
      const status = lastError.response?.status;
      const message = (lastError.response?.data as any)?.message || lastError.message;
      throw new APIError(endpoint, method, status, message);
    }

    throw lastError || new Error('Unknown API error');
  }

  /**
   * Set authentication token
   */
  setAuthToken(token: string): void {
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    this.logger.debug('Authorization token set');
  }

  /**
   * Clear authentication token
   */
  clearAuthToken(): void {
    delete this.client.defaults.headers.common['Authorization'];
    this.logger.debug('Authorization token cleared');
  }

  /**
   * Set default header
   */
  setHeader(key: string, value: string): void {
    this.client.defaults.headers.common[key] = value;
  }

  /**
   * Remove header
   */
  removeHeader(key: string): void {
    delete this.client.defaults.headers.common[key];
  }

  /**
   * Sleep utility
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Get base URL
   */
  getBaseURL(): string {
    return this.baseURL;
  }

  /**
   * Set base URL
   */
  setBaseURL(url: string): void {
    this.baseURL = url;
    this.client.defaults.baseURL = url;
  }
}

/**
 * Global API client instance
 */
let globalApiClient: ApiClient | null = null;

/**
 * Get or create global API client
 */
export function getApiClient(logger?: Logger): ApiClient {
  if (!globalApiClient) {
    globalApiClient = new ApiClient(logger || new Logger());
  }
  return globalApiClient;
}

/**
 * Reset API client
 */
export function resetApiClient(): void {
  globalApiClient = null;
}

/**
 * Export singleton
 */
export const apiClient = getApiClient();
