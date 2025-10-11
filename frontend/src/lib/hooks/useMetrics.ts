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
  executionsByType?: {
    flow: number;
    crew: number;
    agent: number;
    tool: number;
    task: number;
  };
  toolStats?: {
    total: number;
    success: number;
    failed: number;
    avgDurationSec: number;
  };
  taskStats?: {
    total: number;
    success: number;
    failed: number;
    avgDurationSec: number;
  };
  flowStats?: {
    total: number;
    success: number;
    failed: number;
    avgDurationSec: number;
  };
  crewStats?: {
    total: number;
    success: number;
    failed: number;
    avgDurationSec: number;
  };
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
  const [toolTrend, setToolTrend] = useState<ExecutionTrend[]>([]);
  const [taskTrend, setTaskTrend] = useState<ExecutionTrend[]>([]);
  const [flowTrend, setFlowTrend] = useState<ExecutionTrend[]>([]);
  const [crewTrend, setCrewTrend] = useState<ExecutionTrend[]>([]);
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
        e.status === 'completed' && (e.execution_time_ms || (e.created_at && e.updated_at))
      );
      const avgExecutionTime = completedExecutions.length > 0
        ? completedExecutions.reduce((sum: number, e: any) => {
            // Use execution_time_ms if available, otherwise calculate from timestamps
            if (e.execution_time_ms) {
              return sum + e.execution_time_ms;
            }
            const start = new Date(e.created_at).getTime();
            const end = new Date(e.updated_at).getTime();
            return sum + (end - start);
          }, 0) / completedExecutions.length / 1000 // Convert to seconds
        : 0;

      // Count executions by type
      const executionsByType = {
        flow: filteredExecutions.filter((e: any) => e.execution_type === 'flow').length,
        crew: filteredExecutions.filter((e: any) => e.execution_type === 'crew').length,
        agent: filteredExecutions.filter((e: any) => e.execution_type === 'agent').length,
        tool: filteredExecutions.filter((e: any) => e.execution_type === 'tool').length,
        task: filteredExecutions.filter((e: any) => e.execution_type === 'task').length,
      };

      // Tool execution stats
      const toolExecs = filteredExecutions.filter((e: any) => e.execution_type === 'tool');
      const toolSuccess = toolExecs.filter((e: any) => e.status === 'completed');
      const toolFailed = toolExecs.filter((e: any) => e.status === 'failed');
      const toolAvgDurationSec = toolSuccess.length > 0
        ? toolSuccess.reduce((sum: number, e: any) => {
            if (e.execution_time_ms) return sum + e.execution_time_ms;
            const start = e.created_at ? new Date(e.created_at).getTime() : 0;
            const end = e.updated_at ? new Date(e.updated_at).getTime() : 0;
            return sum + Math.max(0, end - start);
          }, 0) / toolSuccess.length / 1000
        : 0;

      // Task stats
      const taskExecs = filteredExecutions.filter((e: any) => e.execution_type === 'task');
      const taskSuccess = taskExecs.filter((e: any) => e.status === 'completed');
      const taskFailed = taskExecs.filter((e: any) => e.status === 'failed');
      const taskAvgDurationSec = taskSuccess.length > 0
        ? taskSuccess.reduce((sum: number, e: any) => {
            if (e.execution_time_ms) return sum + e.execution_time_ms;
            const start = e.created_at ? new Date(e.created_at).getTime() : 0;
            const end = e.updated_at ? new Date(e.updated_at).getTime() : 0;
            return sum + Math.max(0, end - start);
          }, 0) / taskSuccess.length / 1000
        : 0;

      // Flow stats
      const flowExecs = filteredExecutions.filter((e: any) => e.execution_type === 'flow');
      const flowSuccess = flowExecs.filter((e: any) => e.status === 'completed');
      const flowFailed = flowExecs.filter((e: any) => e.status === 'failed');
      const flowAvgDurationSec = flowSuccess.length > 0
        ? flowSuccess.reduce((sum: number, e: any) => {
            if (e.execution_time_ms) return sum + e.execution_time_ms;
            const start = e.created_at ? new Date(e.created_at).getTime() : 0;
            const end = e.updated_at ? new Date(e.updated_at).getTime() : 0;
            return sum + Math.max(0, end - start);
          }, 0) / flowSuccess.length / 1000
        : 0;

      // Crew stats
      const crewExecs = filteredExecutions.filter((e: any) => e.execution_type === 'crew');
      const crewSuccess = crewExecs.filter((e: any) => e.status === 'completed');
      const crewFailed = crewExecs.filter((e: any) => e.status === 'failed');
      const crewAvgDurationSec = crewSuccess.length > 0
        ? crewSuccess.reduce((sum: number, e: any) => {
            if (e.execution_time_ms) return sum + e.execution_time_ms;
            const start = e.created_at ? new Date(e.created_at).getTime() : 0;
            const end = e.updated_at ? new Date(e.updated_at).getTime() : 0;
            return sum + Math.max(0, end - start);
          }, 0) / crewSuccess.length / 1000
        : 0;

      setSummary({
        totalExecutions,
        successCount,
        failedCount,
        runningCount,
        successRate,
        errorRate,
        avgExecutionTime,
        executionsByType,
        toolStats: {
          total: toolExecs.length,
          success: toolSuccess.length,
          failed: toolFailed.length,
          avgDurationSec: toolAvgDurationSec,
        },
        taskStats: {
          total: taskExecs.length,
          success: taskSuccess.length,
          failed: taskFailed.length,
          avgDurationSec: taskAvgDurationSec,
        },
        flowStats: {
          total: flowExecs.length,
          success: flowSuccess.length,
          failed: flowFailed.length,
          avgDurationSec: flowAvgDurationSec,
        },
        crewStats: {
          total: crewExecs.length,
          success: crewSuccess.length,
          failed: crewFailed.length,
          avgDurationSec: crewAvgDurationSec,
        },
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

      // Tool-only trend
      const toolBuckets = new Map<string, { count: number; success: number; failed: number }>();
      filteredExecutions
        .filter((e: any) => e.execution_type === 'tool')
        .forEach((e: any) => {
          const timestamp = new Date(e.created_at);
          const bucketKey = new Date(
            timestamp.getFullYear(),
            timestamp.getMonth(),
            timestamp.getDate(),
            bucketSize === 1 ? timestamp.getHours() : 0
          ).toISOString();
          const existing = toolBuckets.get(bucketKey) || { count: 0, success: 0, failed: 0 };
          existing.count++;
          if (e.status === 'completed') existing.success++;
          if (e.status === 'failed') existing.failed++;
          toolBuckets.set(bucketKey, existing);
        });

      const toolTrendData = Array.from(toolBuckets.entries())
        .map(([timestamp, data]) => ({
          timestamp,
          count: data.count,
          successCount: data.success,
          failedCount: data.failed,
        }))
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

      setToolTrend(toolTrendData);

      // Task-only trend
      const taskBuckets = new Map<string, { count: number; success: number; failed: number }>();
      filteredExecutions
        .filter((e: any) => e.execution_type === 'task')
        .forEach((e: any) => {
          const timestamp = new Date(e.created_at);
          const bucketKey = new Date(
            timestamp.getFullYear(),
            timestamp.getMonth(),
            timestamp.getDate(),
            bucketSize === 1 ? timestamp.getHours() : 0
          ).toISOString();
          const existing = taskBuckets.get(bucketKey) || { count: 0, success: 0, failed: 0 };
          existing.count++;
          if (e.status === 'completed') existing.success++;
          if (e.status === 'failed') existing.failed++;
          taskBuckets.set(bucketKey, existing);
        });

      const taskTrendData = Array.from(taskBuckets.entries())
        .map(([timestamp, data]) => ({
          timestamp,
          count: data.count,
          successCount: data.success,
          failedCount: data.failed,
        }))
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
      setTaskTrend(taskTrendData);

      // Flow-only trend
      const flowBuckets = new Map<string, { count: number; success: number; failed: number }>();
      filteredExecutions
        .filter((e: any) => e.execution_type === 'flow')
        .forEach((e: any) => {
          const timestamp = new Date(e.created_at);
          const bucketKey = new Date(
            timestamp.getFullYear(),
            timestamp.getMonth(),
            timestamp.getDate(),
            bucketSize === 1 ? timestamp.getHours() : 0
          ).toISOString();
          const existing = flowBuckets.get(bucketKey) || { count: 0, success: 0, failed: 0 };
          existing.count++;
          if (e.status === 'completed') existing.success++;
          if (e.status === 'failed') existing.failed++;
          flowBuckets.set(bucketKey, existing);
        });

      const flowTrendData = Array.from(flowBuckets.entries())
        .map(([timestamp, data]) => ({
          timestamp,
          count: data.count,
          successCount: data.success,
          failedCount: data.failed,
        }))
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
      setFlowTrend(flowTrendData);

      // Crew-only trend
      const crewBuckets = new Map<string, { count: number; success: number; failed: number }>();
      filteredExecutions
        .filter((e: any) => e.execution_type === 'crew')
        .forEach((e: any) => {
          const timestamp = new Date(e.created_at);
          const bucketKey = new Date(
            timestamp.getFullYear(),
            timestamp.getMonth(),
            timestamp.getDate(),
            bucketSize === 1 ? timestamp.getHours() : 0
          ).toISOString();
          const existing = crewBuckets.get(bucketKey) || { count: 0, success: 0, failed: 0 };
          existing.count++;
          if (e.status === 'completed') existing.success++;
          if (e.status === 'failed') existing.failed++;
          crewBuckets.set(bucketKey, existing);
        });

      const crewTrendData = Array.from(crewBuckets.entries())
        .map(([timestamp, data]) => ({
          timestamp,
          count: data.count,
          successCount: data.success,
          failedCount: data.failed,
        }))
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
      setCrewTrend(crewTrendData);
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
    toolTrend,
    taskTrend,
    flowTrend,
    crewTrend,
    loading,
    error,
    refetch: fetchMetrics,
  };
}
