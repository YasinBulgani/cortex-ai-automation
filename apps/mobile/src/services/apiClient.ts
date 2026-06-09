import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';
import * as SecureStore from 'expo-secure-store';
import { useAppStore } from '@hooks/useAppStore';

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

class ApiClient {
  private client: AxiosInstance;
  private refreshTokenPromise: Promise<string> | null = null;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 15000,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      async config => {
        const token = await SecureStore.getItemAsync('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      error => Promise.reject(error),
    );

    // Response interceptor
    this.client.interceptors.response.use(
      response => response,
      async error => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const newToken = await this.refreshAccessToken();
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            // Refresh failed - logout user
            await this.logout();
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      },
    );
  }

  private async refreshAccessToken(): Promise<string> {
    if (this.refreshTokenPromise) {
      return this.refreshTokenPromise;
    }

    this.refreshTokenPromise = (async () => {
      const refreshToken = await SecureStore.getItemAsync('refresh_token');
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await this.client.post<TokenResponse>('/auth/refresh', {
        refresh_token: refreshToken,
      });

      const { access_token, refresh_token: newRefreshToken } = response.data;

      await Promise.all([
        SecureStore.setItemAsync('access_token', access_token),
        SecureStore.setItemAsync('refresh_token', newRefreshToken),
      ]);

      return access_token;
    })();

    try {
      return await this.refreshTokenPromise;
    } finally {
      this.refreshTokenPromise = null;
    }
  }

  private async logout(): Promise<void> {
    await Promise.all([
      SecureStore.deleteItemAsync('access_token'),
      SecureStore.deleteItemAsync('refresh_token'),
    ]);
    // Dispatch logout action to Redux
  }

  public async get<T>(url: string, config?: any): Promise<AxiosResponse<T>> {
    return this.client.get<T>(url, config);
  }

  public async post<T>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return this.client.post<T>(url, data, config);
  }

  public async put<T>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return this.client.put<T>(url, data, config);
  }

  public async patch<T>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return this.client.patch<T>(url, data, config);
  }

  public async delete<T>(url: string, config?: any): Promise<AxiosResponse<T>> {
    return this.client.delete<T>(url, config);
  }
}

const apiClient = new ApiClient(
  process.env.REACT_APP_API_URL || 'https://api.neurex.com/api/v1',
);

export default apiClient;
