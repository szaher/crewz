'use client';

import { useEffect, useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface QueuePositionData {
  position: number;
  estimatedWaitSeconds: number | null;
  queueLength: number;
  averageExecutionTime: number | null;
}

export interface UseQueuePositionOptions {
  executionId: string;
  enabled?: boolean;
  pollingInterval?: number; // milliseconds
}

export interface UseQueuePositionReturn {
  position: number | null;
  estimatedWaitSeconds: number | null;
  queueLength: number | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * useQueuePosition Hook
 *
 * Polls GET /api/v1/executions/{id}/status for queue_position updates.
 * - Returns position + estimated wait time
 * - Only polls if queue_position is not null
 * - Stops polling when execution starts (queue_position becomes null)
 * - Configurable polling interval (default 2s)
 *
 * @example
 * ```tsx
 * const { position, estimatedWaitSeconds, queueLength } = useQueuePosition({
 *   executionId: 'abc-123',
 *   enabled: true,
 *   pollingInterval: 2000
 * });
 * ```
 */
export function useQueuePosition(options: UseQueuePositionOptions): UseQueuePositionReturn {
  const {
    executionId,
    enabled = true,
    pollingInterval = 2000
  } = options;

  const [shouldPoll, setShouldPoll] = useState(true);

  const fetchQueuePosition = useCallback(async (): Promise<QueuePositionData | null> => {
    if (!executionId || !enabled) {
      return null;
    }

    try {
      const response = await apiClient.get(`/api/v1/executions/${executionId}/status`);
      const data = response.data;

      // If queue_position is null, execution has started
      if (data.queue_position === null || data.queue_position === undefined) {
        setShouldPoll(false);
        return null;
      }

      return {
        position: data.queue_position,
        estimatedWaitSeconds: data.estimated_start_seconds || null,
        queueLength: data.queue_length || 0,
        averageExecutionTime: data.average_execution_time || null
      };
    } catch (error) {
      console.error('[useQueuePosition] Failed to fetch queue position:', error);
      throw error;
    }
  }, [executionId, enabled]);

  const {
    data,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['queue-position', executionId],
    queryFn: fetchQueuePosition,
    enabled: enabled && shouldPoll,
    refetchInterval: shouldPoll ? pollingInterval : false,
    refetchIntervalInBackground: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000)
  });

  return {
    position: data?.position || null,
    estimatedWaitSeconds: data?.estimatedWaitSeconds || null,
    queueLength: data?.queueLength || null,
    isLoading,
    error: error as Error | null,
    refetch: () => {
      setShouldPoll(true);
      refetch();
    }
  };
}
