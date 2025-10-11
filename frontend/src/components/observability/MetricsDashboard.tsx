'use client';

import { useState } from 'react';
import { useMetrics } from '@/lib/hooks/useMetrics';
import MetricsCard from './MetricsCard';
import ExecutionTrendChart from './ExecutionTrendChart';
import ErrorsList from './ErrorsList';
import TimeRangeFilter from './TimeRangeFilter';

export default function MetricsDashboard() {
  const [timeRange, setTimeRange] = useState('24h');
  const [activeTab, setActiveTab] = useState<'tasks' | 'tools' | 'flows' | 'crews'>('tasks');
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

      {/* Execution Type Breakdown */}
      {summary.executionsByType && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Executions by Type</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {summary.executionsByType.flow >= 0 && (
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-3xl mb-2">🔀</div>
                <div className="text-2xl font-bold text-gray-900">{summary.executionsByType.flow}</div>
                <div className="text-sm text-gray-600">Flows</div>
              </div>
            )}
            {summary.executionsByType.crew > 0 && (
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-3xl mb-2">👥</div>
                <div className="text-2xl font-bold text-gray-900">{summary.executionsByType.crew}</div>
                <div className="text-sm text-gray-600">Crews</div>
              </div>
            )}
            {summary.executionsByType.agent > 0 && (
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-3xl mb-2">🤖</div>
                <div className="text-2xl font-bold text-gray-900">{summary.executionsByType.agent}</div>
                <div className="text-sm text-gray-600">Agents</div>
              </div>
            )}
            {summary.executionsByType.tool >= 0 && (
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <div className="text-3xl mb-2">🔧</div>
                <div className="text-2xl font-bold text-gray-900">{summary.executionsByType.tool}</div>
                <div className="text-sm text-gray-600">Tools</div>
              </div>
            )}
            {summary.executionsByType.task >= 0 && (
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <div className="text-3xl mb-2">📋</div>
                <div className="text-2xl font-bold text-gray-900">{summary.executionsByType.task}</div>
                <div className="text-sm text-gray-600">Tasks</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stats Tabs: Tasks, Tools, Flows, Crews */}
      <div className="bg-white rounded-lg border border-gray-200 p-0">
        <div
          className="border-b border-gray-200 flex items-center gap-2 px-3 pt-2 bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800"
        >
          {[
            { key: 'tasks', label: 'Task Stats', icon: '📋' },
            { key: 'tools', label: 'Tool Stats', icon: '🔧' },
            { key: 'flows', label: 'Flow Stats', icon: '🔀' },
            { key: 'crews', label: 'Crew Stats', icon: '👥' },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key as any)}
              className={`relative inline-flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-t-lg border transition-all duration-150 select-none
                ${
                  activeTab === t.key
                    ? 'bg-gradient-to-b from-gray-100 to-white dark:from-gray-700 dark:to-gray-800 text-blue-700 dark:text-blue-300 border-blue-600 dark:border-blue-500 shadow-inner translate-y-[2px]'
                    : 'bg-gradient-to-b from-white to-gray-100 dark:from-gray-800 dark:to-gray-700 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-600 shadow-md hover:shadow-lg hover:-translate-y-0.5 active:translate-y-[1px]'
                }
              `}
            >
              <span className="mr-1">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>
        <div className="p-6">
          {activeTab === 'tasks' && summary.taskStats && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-yellow-50 rounded-lg">
                  <div className="text-3xl mb-2">📋</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.taskStats.total}</div>
                  <div className="text-sm text-gray-600">Total Task Runs</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-3xl mb-2">✅</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.taskStats.success}</div>
                  <div className="text-sm text-gray-600">Succeeded</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-3xl mb-2">❌</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.taskStats.failed}</div>
                  <div className="text-sm text-gray-600">Failed</div>
                </div>
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-3xl mb-2">⏱️</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.taskStats.avgDurationSec.toFixed(1)}s</div>
                  <div className="text-sm text-gray-600">Avg Duration</div>
                </div>
              </div>
            </>
          )}

          {activeTab === 'tools' && summary.toolStats && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <div className="text-3xl mb-2">🔧</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.toolStats.total}</div>
                  <div className="text-sm text-gray-600">Total Tool Runs</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-3xl mb-2">✅</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.toolStats.success}</div>
                  <div className="text-sm text-gray-600">Succeeded</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-3xl mb-2">❌</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.toolStats.failed}</div>
                  <div className="text-sm text-gray-600">Failed</div>
                </div>
                <div className="text-center p-4 bg-yellow-50 rounded-lg">
                  <div className="text-3xl mb-2">⏱️</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.toolStats.avgDurationSec.toFixed(1)}s</div>
                  <div className="text-sm text-gray-600">Avg Duration</div>
                </div>
              </div>
            </>
          )}

          {activeTab === 'flows' && summary.flowStats && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-3xl mb-2">🔀</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.flowStats.total}</div>
                  <div className="text-sm text-gray-600">Total Flow Runs</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-3xl mb-2">✅</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.flowStats.success}</div>
                  <div className="text-sm text-gray-600">Succeeded</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-3xl mb-2">❌</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.flowStats.failed}</div>
                  <div className="text-sm text-gray-600">Failed</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-3xl mb-2">⏱️</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.flowStats.avgDurationSec.toFixed(1)}s</div>
                  <div className="text-sm text-gray-600">Avg Duration</div>
                </div>
              </div>
            </>
          )}

          {activeTab === 'crews' && summary.crewStats && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-3xl mb-2">👥</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.crewStats.total}</div>
                  <div className="text-sm text-gray-600">Total Crew Runs</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-3xl mb-2">✅</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.crewStats.success}</div>
                  <div className="text-sm text-gray-600">Succeeded</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-3xl mb-2">❌</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.crewStats.failed}</div>
                  <div className="text-sm text-gray-600">Failed</div>
                </div>
                <div className="text-center p-4 bg-yellow-50 rounded-lg">
                  <div className="text-3xl mb-2">⏱️</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.crewStats.avgDurationSec.toFixed(1)}s</div>
                  <div className="text-sm text-gray-600">Avg Duration</div>
                </div>
              </div>
            </>
          )}
        </div>
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
