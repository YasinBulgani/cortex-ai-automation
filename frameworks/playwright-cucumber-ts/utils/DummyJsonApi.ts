/**
 * DummyJSON API Client
 * Specific wrapper for DummyJSON API endpoints
 */

import { APIRequestContext, APIResponse } from 'playwright';
import { ApiClient } from './ApiClient';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface LoginResponse {
  id: number;
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  gender: string;
  image: string;
  token?: string;
  accessToken?: string;
  refreshToken?: string;
}

export interface Product {
  id: number;
  title: string;
  description: string;
  price: number;
  discountPercentage: number;
  rating: number;
  stock: number;
  brand: string;
  category: string;
  thumbnail: string;
  images: string[];
}

export interface ProductsResponse {
  products: Product[];
  total: number;
  skip: number;
  limit: number;
}

export class DummyJsonApi {
  private apiClient: ApiClient;

  constructor(apiContext: APIRequestContext) {
    this.apiClient = new ApiClient(apiContext, 'https://dummyjson.com');
  }

  async login(credentials: LoginCredentials): Promise<APIResponse> {
    return await this.apiClient.post('/auth/login', {
      data: {
        username: credentials.username,
        password: credentials.password
      }
    });
  }

  async getProducts(token: string, limit: number = 30, skip: number = 0): Promise<APIResponse> {
    return await this.apiClient.get('/auth/products', {
      params: { limit, skip },
      token: token
    });
  }

  async updateProduct(productId: number, token: string, updateData: Partial<Product>): Promise<APIResponse> {
    return await this.apiClient.put(`/auth/products/${productId}`, {
      data: updateData,
      token: token
    });
  }

  async deleteProduct(productId: number, token: string): Promise<APIResponse> {
    return await this.apiClient.delete(`/auth/products/${productId}`, {
      token: token
    });
  }

  async updateProductIsDeleted(productId: number, token: string, isDeleted: boolean): Promise<APIResponse> {
    return await this.apiClient.put(`/auth/products/${productId}`, {
      data: { isDeleted },
      token: token
    });
  }

  async getCategories(): Promise<APIResponse> {
    return await this.apiClient.get('/products/categories');
  }

  async getProductsByCategory(category: string, limit: number = 10): Promise<APIResponse> {
    return await this.apiClient.get(`/products/category/${category}`, {
      params: { limit }
    });
  }

  async loginWithDelay(credentials: LoginCredentials, delay: number): Promise<APIResponse> {
    return await this.apiClient.post('/auth/login', {
      data: {
        username: credentials.username,
        password: credentials.password,
        delay: delay
      }
    });
  }
}
