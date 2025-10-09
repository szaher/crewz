import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api-client';

export interface MetricsSummary {
  totalExecutions: number;
  successCount: number;
  failedCount: number;
  runningCount: number;
  successRate: number;
  errorRate: number;
  avgExecutionTime: number;
}

export interface ExecutionTrend {
  timestamp: string;
  count: number;
  successCount: number;
  failedCount: number;
}

export interface TimeRange {
  label: string;
  value: string;
  hours: number;
}

export const TIME_RANGES: TimeRange[] = [
  { label: 'Last Hour', value: '1h', hours: 1 },
  { label: 'Last 24 Hours', value: '24h', hours: 24 },
  { label: 'Last 7 Days', value: '7d', hours: 168 },
  { label: 'Last 30 Days', value: '30d', hours: 720 },
];

export function useMetrics(timeRange: string = '24h', autoRefresh: boolean = true) {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [trends, setTrends] = useState<ExecutionTrend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Calculate time range
      const range = TIME_RANGES.find(r => r.value === timeRange) || TIME_RANGES[1];
      const now = new Date();
      const startTime = new Date(now.getTime() - range.hours * 60 * 60 * 1000);

      // Fetch all executions
      const response = await apiClient.get('/api/v1/executions');
      if (response.error) throw new Error(response.error);

      const executions = response.data?.executions || [];

      // Filter by time range
      const filteredExecutions = executions.filter((e: any) => {
        const createdAt = new Date(e.created_at);
        return createdAt >= startTime;
      });

      // Calculate summary metrics
      const totalExecutions = filteredExecutions.length;
      const successCount = filteredExecutions.filter((e: any) => e.status === 'completed').length;
      const failedCount = filteredExecutions.filter((e: any) => e.status === 'failed').length;
      const runningCount = filteredExecutions.filter((e: any) => e.status === 'running').length;
      const successRate = totalExecutions > 0 ? (successCount / totalExecutions) * 100 : 0;
      const errorRate = totalExecutions > 0 ? (failedCount / totalExecutions) * 100 : 0;

      // Calculate average execution time for completed executions
      const completedExecutions = filteredExecutions.filter((e: any) =>
        e.status === 'completed' && e.started_at && e.completed_at
      );
      const avgExecutionTime = completedExecutions.length > 0
        ? completedExecutions.reduce((sum: number, e: any) => {
            const start = new Date(e.started_at).getTime();
            const end = new Date(e.completed_at).getTime();
            return sum + (end - start);
          }, 0) / completedExecutions.length / 1000 // Convert to seconds
        : 0;

      setSummary({
        totalExecutions,
        successCount,
        failedCount,
        runningCount,
        successRate,
        errorRate,
        avgExecutionTime,
      });

      // Calculate hourly trends
      const bucketSize = range.hours <= 24 ? 1 : 24; // 1 hour for short ranges, 1 day for longer
      const buckets = new Map<string, { count: number; success: number; failed: number }>();

      filteredExecutions.forEach((e: any) => {
        const timestamp = new Date(e.created_at);
        const bucketKey = new Date(
          timestamp.getFullYear(),
          timestamp.getMonth(),
          timestamp.getDate(),
          bucketSize === 1 ? timestamp.getHours() : 0
        ).toISOString();

        const existing = buckets.get(bucketKey) || { count: 0, success: 0, failed: 0 };
        existing.count++;
        if (e.status === 'completed') existing.success++;
        if (e.status === 'failed') existing.failed++;
        buckets.set(bucketKey, existing);
      });

      const trendData = Array.from(buckets.entries())
        .map(([timestamp, data]) => ({
          timestamp,
          count: data.count,
          successCount: data.success,
          failedCount: data.failed,
        }))
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

      setTrends(trendData);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch metrics';
      setError(message);
      console.error('Failed to fetch metrics:', err);
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  // Initial fetch
  useEffect(() => {
    fetchMetrics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeRange]); // Only re-fetch when timeRange changes

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchMetrics();
    }, 30000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, timeRange]); // Depend on timeRange, not fetchMetrics

  return {
    summary,
    trends,
    loading,
    error,
    refetch: fetchMetrics,
  };
}
