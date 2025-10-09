import { useState } from 'react';
import { useToast } from '@/components/shared/Toast';
import {
  parseErrorResponse,
  parseValidationErrors,
  retryWithBackoff,
  getErrorMessage,
} from '../error-handler';

interface UseFormSubmitOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: any) => void;
  successMessage?: string;
  errorMessage?: string;
  enableRetry?: boolean;
  maxRetries?: number;
}

/**
 * Custom hook for handling form submissions with comprehensive error handling
 *
 * Features:
 * - Automatic loading state management
 * - Backend validation error parsing
 * - Toast notifications for success/error
 * - Retry logic for network errors
 * - Field-level error state
 * - Form-level error state
 *
 * @example
 * ```tsx
 * const { handleSubmit, loading, errors, formError } = useFormSubmit({
 *   onSuccess: (data) => router.push('/success'),
 *   successMessage: 'Item created successfully!',
 *   enableRetry: true,
 * });
 *
 * const onSubmit = handleSubmit(async (formData) => {
 *   return await apiClient.post('/api/items', formData);
 * });
 * ```
 */
export function useFormSubmit<T = any>(options: UseFormSubmitOptions<T> = {}) {
  const {
    onSuccess,
    onError,
    successMessage,
    errorMessage,
    enableRetry = true,
    maxRetries = 3,
  } = options;

  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const clearErrors = () => {
    setErrors({});
    setFormError(null);
  };

  const handleSubmit = (submitFn: (data: any) => Promise<{ data?: T; error?: any }>) => {
    return async (formData: any) => {
      setLoading(true);
      clearErrors();

      try {
        let response;

        if (enableRetry) {
          // Retry with exponential backoff for network errors
          response = await retryWithBackoff(
            () => submitFn(formData),
            {
              maxRetries,
              shouldRetry: (error) => {
                const errorDetail = parseErrorResponse(error);
                return errorDetail.retryable && errorDetail.type === 'network';
              },
            }
          );
        } else {
          response = await submitFn(formData);
        }

        // Handle API client error format
        if (response.error) {
          throw response.error;
        }

        // Success
        if (successMessage) {
          showToast(successMessage, 'success');
        }

        if (onSuccess) {
          onSuccess(response.data as T);
        }

        return response.data;
      } catch (error) {
        console.error('Form submission error:', error);

        const errorDetail = parseErrorResponse(error);

        // Parse validation errors for form fields
        if (errorDetail.type === 'validation') {
          const fieldErrors = parseValidationErrors(error);
          setErrors(fieldErrors);

          // If no specific field errors, set form-level error
          if (Object.keys(fieldErrors).length === 0) {
            setFormError(errorDetail.message);
          }
        } else {
          // Non-validation errors (network, server, etc.)
          setFormError(errorDetail.message);
        }

        // Show toast notification
        const toastMessage = errorMessage || errorDetail.message;
        showToast(toastMessage, 'error');

        if (onError) {
          onError(error);
        }

        throw error;
      } finally {
        setLoading(false);
      }
    };
  };

  return {
    handleSubmit,
    loading,
    errors,
    formError,
    clearErrors,
    setErrors,
    setFormError,
  };
}

/**
 * Simpler hook for API operations without form context
 *
 * @example
 * ```tsx
 * const { execute, loading } = useApiOperation({
 *   successMessage: 'Operation completed!',
 *   enableRetry: true,
 * });
 *
 * const handleDelete = async () => {
 *   await execute(() => apiClient.delete(`/api/items/${id}`));
 * };
 * ```
 */
export function useApiOperation<T = any>(options: UseFormSubmitOptions<T> = {}) {
  const {
    onSuccess,
    onError,
    successMessage,
    errorMessage,
    enableRetry = true,
    maxRetries = 3,
  } = options;

  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = async (
    operationFn: () => Promise<{ data?: T; error?: any }>
  ): Promise<T | undefined> => {
    setLoading(true);
    setError(null);

    try {
      let response;

      if (enableRetry) {
        response = await retryWithBackoff(() => operationFn(), {
          maxRetries,
          shouldRetry: (err) => {
            const errorDetail = parseErrorResponse(err);
            return errorDetail.retryable;
          },
        });
      } else {
        response = await operationFn();
      }

      if (response.error) {
        throw response.error;
      }

      if (successMessage) {
        showToast(successMessage, 'success');
      }

      if (onSuccess && response.data) {
        onSuccess(response.data);
      }

      return response.data;
    } catch (err) {
      console.error('API operation error:', err);

      const errorMsg = errorMessage || getErrorMessage(err);
      setError(errorMsg);
      showToast(errorMsg, 'error');

      if (onError) {
        onError(err);
      }

      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    execute,
    loading,
    error,
    setError,
  };
}
