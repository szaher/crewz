/**
 * Comprehensive error handling utilities
 *
 * Features:
 * - Parse backend validation errors (Pydantic, FastAPI)
 * - Network error detection and retry logic
 * - User-friendly error messages
 * - Structured error formatting
 */

export interface ValidationError {
  field: string;
  message: string;
  type?: string;
}

export interface ErrorDetail {
  message: string;
  field?: string;
  type: 'validation' | 'network' | 'server' | 'client' | 'unknown';
  retryable: boolean;
  statusCode?: number;
}

/**
 * Parse backend error response into structured format
 */
export function parseErrorResponse(error: any): ErrorDetail {
  // Network errors (no response)
  if (!error.response && error.request) {
    return {
      message: 'Network error. Please check your internet connection.',
      type: 'network',
      retryable: true,
    };
  }

  // No error object
  if (!error) {
    return {
      message: 'An unknown error occurred',
      type: 'unknown',
      retryable: false,
    };
  }

  const response = error.response;
  const status = response?.status || error.status;
  const data = response?.data || error.data || error;

  // Validation errors (400) - Pydantic format
  if (status === 400 && Array.isArray(data.detail)) {
    const firstError = data.detail[0];
    const field = firstError.loc?.join('.') || 'field';
    const message = firstError.msg || 'Validation error';

    return {
      message: `${field}: ${message}`,
      field,
      type: 'validation',
      retryable: false,
      statusCode: 400,
    };
  }

  // Validation errors (422) - FastAPI format
  if (status === 422) {
    if (Array.isArray(data.detail)) {
      const firstError = data.detail[0];
      return {
        message: firstError.msg || 'Validation error',
        field: firstError.loc?.join('.'),
        type: 'validation',
        retryable: false,
        statusCode: 422,
      };
    }
    return {
      message: data.detail || 'Validation error',
      type: 'validation',
      retryable: false,
      statusCode: 422,
    };
  }

  // Authentication errors (401)
  if (status === 401) {
    return {
      message: 'Session expired. Please log in again.',
      type: 'client',
      retryable: false,
      statusCode: 401,
    };
  }

  // Authorization errors (403)
  if (status === 403) {
    return {
      message: 'You do not have permission to perform this action.',
      type: 'client',
      retryable: false,
      statusCode: 403,
    };
  }

  // Not found (404)
  if (status === 404) {
    return {
      message: 'Resource not found.',
      type: 'client',
      retryable: false,
      statusCode: 404,
    };
  }

  // Server errors (500+)
  if (status >= 500) {
    return {
      message: data.detail || 'Server error. Please try again later.',
      type: 'server',
      retryable: true,
      statusCode: status,
    };
  }

  // Timeout
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    return {
      message: 'Request timed out. Please try again.',
      type: 'network',
      retryable: true,
    };
  }

  // String error
  if (typeof data === 'string') {
    return {
      message: data,
      type: 'unknown',
      retryable: false,
    };
  }

  // Detail field
  if (data.detail) {
    return {
      message: typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail),
      type: 'server',
      retryable: false,
      statusCode: status,
    };
  }

  // Message field
  if (data.message) {
    return {
      message: data.message,
      type: 'unknown',
      retryable: false,
    };
  }

  // Error instance
  if (error instanceof Error) {
    return {
      message: error.message,
      type: 'client',
      retryable: false,
    };
  }

  // Fallback
  return {
    message: 'An unexpected error occurred',
    type: 'unknown',
    retryable: false,
  };
}

/**
 * Parse validation errors into field-keyed object
 */
export function parseValidationErrors(error: any): Record<string, string> {
  const data = error.response?.data || error.data || error;

  // Pydantic validation errors
  if (Array.isArray(data.detail)) {
    const errors: Record<string, string> = {};
    data.detail.forEach((err: any) => {
      const field = err.loc?.join('.') || 'general';
      const message = err.msg || 'Invalid value';
      errors[field] = message;
    });
    return errors;
  }

  // FastAPI validation errors
  if (data.detail && typeof data.detail === 'object' && !Array.isArray(data.detail)) {
    return data.detail;
  }

  // Single error
  if (data.detail && typeof data.detail === 'string') {
    return { general: data.detail };
  }

  return {};
}

/**
 * Retry function with exponential backoff
 *
 * @param fn Function to retry
 * @param options Retry configuration
 * @returns Promise with function result
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: {
    maxRetries?: number;
    initialDelay?: number;
    maxDelay?: number;
    shouldRetry?: (error: any) => boolean;
  } = {}
): Promise<T> {
  const {
    maxRetries = 3,
    initialDelay = 1000,
    maxDelay = 10000,
    shouldRetry = (error) => parseErrorResponse(error).retryable,
  } = options;

  let lastError: any;
  let delay = initialDelay;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      // Don't retry if not retryable or last attempt
      if (attempt === maxRetries || !shouldRetry(error)) {
        throw error;
      }

      // Wait before retrying with exponential backoff
      await new Promise((resolve) => setTimeout(resolve, delay));
      delay = Math.min(delay * 2, maxDelay);
    }
  }

  throw lastError;
}

/**
 * Check if error is network-related
 */
export function isNetworkError(error: any): boolean {
  return parseErrorResponse(error).type === 'network';
}

/**
 * Check if error is retryable
 */
export function isRetryableError(error: any): boolean {
  return parseErrorResponse(error).retryable;
}

/**
 * Get user-friendly error message
 */
export function getErrorMessage(error: any): string {
  return parseErrorResponse(error).message;
}

/**
 * Format error for logging
 */
export function formatErrorForLogging(error: any): string {
  const detail = parseErrorResponse(error);
  return JSON.stringify(
    {
      message: detail.message,
      type: detail.type,
      statusCode: detail.statusCode,
      retryable: detail.retryable,
      timestamp: new Date().toISOString(),
    },
    null,
    2
  );
}
