/**
 * API Client utility for backend communication
 * Handles JWT authentication, tenant context, and error handling
 */

import { getApiBaseUrl } from './api-url';

interface ApiClientOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  body?: any;
  headers?: Record<string, string>;
  skipAuth?: boolean;
  timeout?: number; // ms
}

interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: number;
}

class ApiClient {
  private token: string | null = null;
  private onUnauthorized: (() => void) | null = null;

  constructor() {
    // Remove baseUrl from constructor - get it dynamically on each request

    // Load token from localStorage on initialization
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('access_token');
    }
  }

  /**
   * Set callback for handling unauthorized (401) responses
   */
  setUnauthorizedHandler(handler: () => void) {
    this.onUnauthorized = handler;
  }

  /**
   * Set authentication token
   */
  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
    }
  }

  /**
   * Clear authentication token
   */
  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
    }
  }

  /**
   * Get current token
   */
  getToken(): string | null {
    return this.token;
  }

  /**
   * Make HTTP request
   */
  async request<T = any>(
    endpoint: string,
    options: ApiClientOptions = {}
  ): Promise<ApiResponse<T>> {
    const { method = 'GET', body, headers = {}, skipAuth = false, timeout } = options;

    // Get base URL dynamically on each request (browser-aware)
    const baseUrl = getApiBaseUrl();
    const url = `${baseUrl}${endpoint}`;

    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...headers,
    };

    // Add authorization header if token exists and not skipped
    if (!skipAuth && this.token) {
      requestHeaders['Authorization'] = `Bearer ${this.token}`;
    }

    const controller = new AbortController();
    const requestOptions: RequestInit = {
      method,
      headers: requestHeaders,
      signal: controller.signal,
    };

    if (body && method !== 'GET') {
      requestOptions.body = JSON.stringify(body);
    }

    try {
      // Apply timeout if provided
      let to: number | undefined;
      if (typeof timeout === 'number' && timeout > 0) {
        to = window.setTimeout(() => controller.abort(), timeout);
      }

      const response = await fetch(url, requestOptions);
      if (to) window.clearTimeout(to);

      const contentType = response.headers.get('content-type') || '';
      const isNoContent = response.status === 204 || response.status === 205 || response.headers.get('content-length') === '0';

      let data: any = null;
      if (!isNoContent) {
        if (contentType.includes('application/json')) {
          try {
            data = await response.json();
          } catch {
            // Empty or invalid JSON; leave data as null
            data = null;
          }
        } else {
          try {
            const text = await response.text();
            data = text || null;
          } catch {
            data = null;
          }
        }
      }

      if (!response.ok) {
        // Handle 401 Unauthorized - token expired or invalid
        if (response.status === 401 && !skipAuth) {
          this.clearToken();

          // Call the unauthorized handler if set (will trigger logout)
          if (this.onUnauthorized) {
            this.onUnauthorized();
          }
        }

        const errorMessage = (typeof data === 'string' && data) || data?.detail || data?.message || 'Request failed';
        return {
          error: errorMessage,
          status: response.status,
        };
      }

      return {
        data,
        status: response.status,
      };
    } catch (error) {
      return {
        error: error instanceof Error ? (error.name === 'AbortError' ? 'Request timed out' : error.message) : 'Network error',
        status: 0,
      };
    }
  }

  // Convenience methods
  async get<T = any>(endpoint: string, options?: Omit<ApiClientOptions, 'method'>): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  async post<T = any>(endpoint: string, body?: any, options?: Omit<ApiClientOptions, 'method' | 'body'>): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, method: 'POST', body });
  }

  async put<T = any>(endpoint: string, body?: any, options?: Omit<ApiClientOptions, 'method' | 'body'>): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, method: 'PUT', body });
  }

  async delete<T = any>(endpoint: string, options?: Omit<ApiClientOptions, 'method'>): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for testing or custom instances
export default ApiClient;
