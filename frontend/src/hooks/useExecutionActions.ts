'use client';

import { useMutation, useQueryClient } from '@tantml:query';
import { apiClient } from '@/lib/api-client';
import { useRouter } from 'next/navigation';

export interface CancelExecutionOptions {
  executionId: string;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export interface ReExecuteOptions {
  executionId: string;
  onSuccess?: (newExecutionId: string) => void;
  onError?: (error: Error) => void;
}

export interface UseExecutionActionsReturn {
  cancelExecution: (options: CancelExecutionOptions) => Promise<void>;
  reExecute: (options: ReExecuteOptions) => Promise<void>;
  isCancelling: boolean;
  isReExecuting: boolean;
  cancelError: Error | null;
  reExecuteError: Error | null;
}

/**
 * useExecutionActions Hook
 *
 * Provides cancel and re-execute mutations for executions.
 * - Cancel mutation sets cancellation_requested=True
 * - Re-execute mutation clones execution with incremented version
 * - Invalidates React Query cache on success
 * - Provides loading states and error handling
 *
 * @example
 * ```tsx
 * const { cancelExecution, reExecute, isCancelling } = useExecutionActions();
 *
 * await cancelExecution({
 *   executionId: 'abc-123',
 *   onSuccess: () => console.log('Cancelled')
 * });
 * ```
 */
export function useExecutionActions(): UseExecutionActionsReturn {
  const queryClient = useQueryClient();
  const router = useRouter();

  // Cancel execution mutation
  const {
    mutateAsync: cancelMutation,
    isPending: isCancelling,
    error: cancelError
  } = useMutation({
    mutationFn: async (executionId: string) => {
      const response = await apiClient.post(`/api/v1/executions/${executionId}/cancel`);
      return response.data;
    },
    onSuccess: (data, executionId) => {
      // Invalidate execution queries
      queryClient.invalidateQueries({ queryKey: ['execution', executionId] });
      queryClient.invalidateQueries({ queryKey: ['executions'] });
      queryClient.invalidateQueries({ queryKey: ['queue-position', executionId] });
    }
  });

  // Re-execute mutation
  const {
    mutateAsync: reExecuteMutation,
    isPending: isReExecuting,
    error: reExecuteError
  } = useMutation({
    mutationFn: async (executionId: string) => {
      const response = await apiClient.post(`/api/v1/executions/${executionId}/re-execute`);
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate execution queries
      queryClient.invalidateQueries({ queryKey: ['executions'] });

      // Navigate to new execution if provided
      if (data.new_job_id) {
        router.push(`/executions/${data.new_job_id}`);
      }
    }
  });

  const cancelExecution = async (options: CancelExecutionOptions): Promise<void> => {
    const { executionId, onSuccess, onError } = options;

    try {
      await cancelMutation(executionId);
      if (onSuccess) {
        onSuccess();
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to cancel execution');
      console.error('[useExecutionActions] Cancel failed:', err);
      if (onError) {
        onError(err);
      }
      throw err;
    }
  };

  const reExecute = async (options: ReExecuteOptions): Promise<void> => {
    const { executionId, onSuccess, onError } = options;

    try {
      const result = await reExecuteMutation(executionId);
      if (onSuccess && result.new_job_id) {
        onSuccess(result.new_job_id);
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to re-execute');
      console.error('[useExecutionActions] Re-execute failed:', err);
      if (onError) {
        onError(err);
      }
      throw err;
    }
  };

  return {
    cancelExecution,
    reExecute,
    isCancelling,
    isReExecuting,
    cancelError: cancelError as Error | null,
    reExecuteError: reExecuteError as Error | null
  };
}
