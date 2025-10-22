import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api-client';

export interface Execution {
  id: string; // UUID
  flow_id: string; // UUID
  flow_name?: string;
  execution_type: 'flow' | 'crew';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  inputs?: Record<string, any>;
  outputs?: Record<string, any>;
  error?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ExecutionDetails extends Execution {
  logs?: ExecutionLog[];
  metrics?: ExecutionMetrics;
}

export interface ExecutionLog {
  id: string; // UUID
  execution_id: string; // UUID
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface ExecutionMetrics {
  duration_ms?: number;
  tokens_used?: number;
  api_calls?: number;
  memory_peak_mb?: number;
}

export interface UseExecutionsOptions {
  skip?: number;
  limit?: number;
}

export function useExecutions(options: UseExecutionsOptions = {}) {
  const { skip = 0, limit = 20 } = options;
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchExecutions = useCallback(async (customSkip?: number, customLimit?: number) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        skip: String(customSkip ?? skip),
        limit: String(customLimit ?? limit),
      });
      const response = await apiClient.get(`/api/v1/executions?${params}`);
      if (response.error) throw new Error(response.error);
      setExecutions(response.data?.executions || []);
      setTotal(response.data?.total || 0);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch executions';
      setError(message);
      console.error('Failed to fetch executions:', err);
    } finally {
      setLoading(false);
    }
  }, [skip, limit]);

  const getExecution = async (id: string): Promise<Execution> => {
    const response = await apiClient.get(`/api/v1/executions/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  const getExecutionDetails = async (id: string): Promise<ExecutionDetails> => {
    const response = await apiClient.get(`/api/v1/executions/${id}/details`);
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  const getExecutionLogs = async (id: string): Promise<ExecutionLog[]> => {
    const response = await apiClient.get(`/api/v1/executions/${id}/logs`);
    if (response.error) throw new Error(response.error);
    return response.data?.logs || [];
  };

  const cancelExecution = async (id: string): Promise<void> => {
    const response = await apiClient.post(`/api/v1/executions/${id}/cancel`, {});
    if (response.error) throw new Error(response.error);

    // Update local state
    setExecutions(prev =>
      prev.map(e => (e.id === id ? { ...e, status: 'cancelled' as const } : e))
    );
  };

  const executeFlow = async (flowId: string, inputs?: Record<string, any>): Promise<Execution> => {
    const response = await apiClient.post(`/api/v1/flows/${flowId}/execute`, { inputs });
    if (response.error) throw new Error(response.error);

    const newExecution = response.data;
    setExecutions(prev => [newExecution, ...prev]);

    return newExecution;
  };

  useEffect(() => {
    fetchExecutions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skip, limit]); // Refetch when pagination changes

  // SSE streaming for live logs
  const streamExecutionLogs = (
    executionId: string,
    onLog: (log: ExecutionLog) => void,
    onError?: (error: Error) => void
  ): (() => void) => {
    const eventSource = new EventSource(
      `${apiClient['baseURL']}/api/v1/executions/${executionId}/logs/stream`
    );

    eventSource.onmessage = (event) => {
      try {
        const log = JSON.parse(event.data);
        onLog(log);
      } catch (err) {
        console.error('Failed to parse log event:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('EventSource error:', err);
      onError?.(new Error('Log stream error'));
      eventSource.close();
    };

    // Return cleanup function
    return () => {
      eventSource.close();
    };
  };

  return {
    executions,
    total,
    loading,
    error,
    getExecution,
    getExecutionDetails,
    getExecutionLogs,
    cancelExecution,
    executeFlow,
    streamExecutionLogs,
    refetch: fetchExecutions,
  };
}
