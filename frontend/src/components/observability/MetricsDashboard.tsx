'use client';

import { useState } from 'react';
import { useMetrics } from '@/lib/hooks/useMetrics';
import MetricsCard from './MetricsCard';
import ExecutionTrendChart from './ExecutionTrendChart';
import ErrorsList from './ErrorsList';
import TimeRangeFilter from './TimeRangeFilter';

export default function MetricsDashboard() {
  const [timeRange, setTimeRange] = useState('24h');
  const { summary, trends, loading, error, refetch } = useMetrics(timeRange, true);

  if (loading && !summary) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Observability</h1>
        </div>

        {/* Loading skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white p-6 rounded-lg border border-gray-200 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
              <div className="h-8 bg-gray-200 rounded w-3/4" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Observability</h1>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <p className="text-red-800 mb-4">{error}</p>
          <button
            onClick={refetch}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Observability</h1>
        <div className="bg-white p-12 rounded-lg border border-gray-200 text-center">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Execution Data Yet</h2>
          <p className="text-gray-600 mb-6">
            Execute a flow to start seeing metrics and analytics
          </p>
          <button
            onClick={() => window.location.href = '/flows'}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Go to Flows
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Observability</h1>
          <p className="text-gray-500 mt-1">Monitor your workflow executions and performance</p>
        </div>
        <div className="flex items-center gap-4">
          <TimeRangeFilter value={timeRange} onChange={setTimeRange} />
          <button
            onClick={refetch}
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh metrics"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricsCard
          title="Total Executions"
          value={summary.totalExecutions}
          icon="⚙️"
          color="blue"
          subtitle={`${summary.runningCount} running`}
        />
        <MetricsCard
          title="Success Rate"
          value={`${summary.successRate.toFixed(1)}%`}
          icon="✅"
          color="green"
          subtitle={`${summary.successCount} successful`}
        />
        <MetricsCard
          title="Error Rate"
          value={`${summary.errorRate.toFixed(1)}%`}
          icon="❌"
          color="red"
          subtitle={`${summary.failedCount} failed`}
        />
        <MetricsCard
          title="Avg Execution Time"
          value={summary.avgExecutionTime > 0 ? `${summary.avgExecutionTime.toFixed(1)}s` : 'N/A'}
          icon="⏱️"
          color="yellow"
          subtitle="For completed executions"
        />
      </div>

      {/* Execution Trend Chart */}
      <ExecutionTrendChart data={trends} />

      {/* Recent Errors */}
      <ErrorsList />

      {/* Auto-refresh indicator */}
      <div className="text-center text-xs text-gray-500">
        Auto-refreshing every 30 seconds
      </div>
    </div>
  );
}
