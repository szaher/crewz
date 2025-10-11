'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { useExecutions } from '@/lib/hooks/useExecutions';

export default function ExecutionsPage() {
  const router = useRouter();
  const { executions, loading, error, refetch } = useExecutions();
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');

  const getNormalizedType = (e: any): string => {
    const rawCandidates = [
      e.execution_type,
      e.type,
      e.kind,
      e.entity_type,
      e.target_type,
      e.resource_type,
      e.subject_type,
      e.category,
      e.context?.type,
      e.metadata?.type,
    ]
      .filter(Boolean)
      .map((v: any) => String(v).toLowerCase());

    const normalizeToken = (t: string): string => {
      if (!t) return '';
      // Strip suffixes and plural forms
      t = t.replace(/_?execution$/, '');
      t = t.replace(/-?execution$/, '');
      if (t.endsWith('s')) t = t.slice(0, -1);
      // Map common synonyms
      if (t.includes('flow')) return 'flow';
      if (t.includes('crew')) return 'crew';
      if (t.includes('agent')) return 'agent';
      if (t.includes('tool')) return 'tool';
      if (t.includes('task')) return 'task';
      return t;
    };

    for (const r of rawCandidates) {
      const n = normalizeToken(r);
      if (['flow', 'crew', 'agent', 'tool', 'task'].includes(n)) return n;
    }

    // Infer from available IDs / names
    const has = (prop: string) => Object.prototype.hasOwnProperty.call(e, prop) && e[prop] != null;
    if (has('flow_id') || has('flowId') || has('flow') || e.flow_name) return 'flow';
    if (has('crew_id') || has('crewId') || has('crew') || e.crew_name) return 'crew';
    if (has('agent_id') || has('agentId') || has('agent') || e.agent_name) return 'agent';
    if (has('tool_id') || has('toolId') || has('tool') || e.tool_name) return 'tool';
    if (has('task_id') || has('taskId') || has('task') || e.task_name) return 'task';

    // Heuristic: scan keys for '*agent*id' or '*crew*id' etc.
    const keys = Object.keys(e).map((k) => k.toLowerCase());
    if (keys.some((k) => k.includes('agent') && k.includes('id'))) return 'agent';
    if (keys.some((k) => k.includes('crew') && k.includes('id'))) return 'crew';
    if (keys.some((k) => k.includes('flow') && k.includes('id'))) return 'flow';
    if (keys.some((k) => k.includes('tool') && k.includes('id'))) return 'tool';
    if (keys.some((k) => k.includes('task') && k.includes('id'))) return 'task';

    return 'execution';
  };

  const filteredExecutions = executions.filter((execution) => {
    if (filterStatus !== 'all' && execution.status !== filterStatus) return false;
    if (filterType !== 'all' && getNormalizedType(execution) !== filterType) return false;
    return true;
  })
  // Sort by id descending (newest first)
  .sort((a: any, b: any) => b.id - a.id);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'flow':
        return '🔀';
      case 'crew':
        return '👥';
      case 'agent':
        return '🤖';
      case 'tool':
        return '🔧';
      case 'task':
        return '📋';
      default:
        return '⚙️';
    }
  };

  const safeDate = (value: any): Date | null => {
    if (!value) return null;
    const d = new Date(value);
    return isNaN(d.getTime()) ? null : d;
  };

  const formatDuration = (execution: any) => {
    // Check if execution_time_ms is available
    if (typeof execution.execution_time_ms === 'number' && execution.execution_time_ms >= 0) {
      const seconds = Math.floor(execution.execution_time_ms / 1000);
      const ms = execution.execution_time_ms % 1000;
      if (seconds < 60) return `${seconds}.${Math.floor(ms / 100)}s`;
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s`;
    }

    // Fallback: compute from created_at -> updated_at (API may not return started_at/completed_at)
    const startDate = safeDate(execution.created_at);
    const endDate = safeDate(execution.updated_at);
    if (!startDate) return '-';
    const start = startDate.getTime();
    const end = endDate ? endDate.getTime() : Date.now();
    const durationSeconds = Math.round((end - start) / 1000);

    if (durationSeconds < 60) return `${durationSeconds}s`;
    const minutes = Math.floor(durationSeconds / 60);
    const seconds = durationSeconds % 60;
    return `${minutes}m ${seconds}s`;
  };

  const getEntityName = (execution: any) => {
    // Prefer generic entity name if provided by API
    if (execution.entity_name) return execution.entity_name;
    // Return entity name based on execution type
    switch (getNormalizedType(execution)) {
      case 'flow':
        return execution.flow_name || `Flow #${execution.flow_id}`;
      case 'crew':
        return execution.crew_name || `Crew #${execution.crew_id}`;
      case 'agent':
        return execution.agent_name || `Agent #${execution.agent_id}`;
      case 'tool':
        return execution.tool_name || `Tool #${execution.tool_id}`;
      case 'task':
        return execution.task_name || `Task #${execution.task_id}`;
      default:
        // Try best-effort fallback
        if (execution.name) return execution.name;
        return execution.title || `#${execution.id}`;
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <Breadcrumbs />

            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Executions</h1>
                <p className="text-gray-500 mt-1">Monitor and review all execution types: flows, crews, agents, tools, and tasks</p>
              </div>
              <button
                onClick={refetch}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                🔄 Refresh
              </button>
            </div>

            {/* Filters */}
            <div className="bg-white p-4 rounded-lg border border-gray-200 mb-6">
              <div className="flex gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                  >
                    <option value="all">All Statuses</option>
                    <option value="pending">Pending</option>
                    <option value="running">Running</option>
                    <option value="completed">Completed</option>
                    <option value="failed">Failed</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                  <select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                  >
                    <option value="all">All Types</option>
                    <option value="flow">🔀 Flow</option>
                    <option value="crew">👥 Crew</option>
                    <option value="agent">🤖 Agent</option>
                    <option value="tool">🔧 Tool</option>
                    <option value="task">📋 Task</option>
                  </select>
                </div>

                <div className="flex-1 flex items-end">
                  <div className="text-sm text-gray-600">
                    Showing {filteredExecutions.length} of {executions.length} executions
                  </div>
                </div>
              </div>
            </div>

            {/* Content */}
            {error ? (
              <div className="flex flex-col items-center justify-center py-12 bg-white rounded-lg border border-gray-200">
                <div className="text-center max-w-md">
                  <p className="text-red-600 mb-4">Failed to load executions: {error}</p>
                  <button
                    onClick={refetch}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Retry
                  </button>
                </div>
              </div>
            ) : loading ? (
              <div className="flex items-center justify-center py-12 bg-white rounded-lg border border-gray-200">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : filteredExecutions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 bg-white rounded-lg border border-gray-200">
                <div className="text-5xl mb-4">⚙️</div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {executions.length === 0 ? 'No executions yet' : 'No matching executions'}
                </h3>
                <p className="text-sm text-gray-500 mb-4">
                  {executions.length === 0
                    ? 'Execute a flow or crew to see it here'
                    : 'Try adjusting your filters'}
                </p>
                {executions.length === 0 && (
                  <button
                    onClick={() => router.push('/flows')}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Go to Flows
                  </button>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Type
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Duration
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Started
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredExecutions.map((execution) => (
                      <tr
                        key={execution.id}
                        className="hover:bg-gray-50 cursor-pointer"
                        onClick={() => router.push(`/executions/${execution.id}`)}
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          #{execution.id}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span className="flex items-center gap-2">
                            <span className="text-lg">{getTypeIcon(getNormalizedType(execution))}</span>
                            <span>{(() => {
                              const t = getNormalizedType(execution);
                              if (!t || t === 'unknown') return 'Unknown';
                              return t.charAt(0).toUpperCase() + t.slice(1);
                            })()}</span>
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(
                              execution.status
                            )}`}
                          >
                            {execution.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDuration(execution)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {(() => {
                            const d = safeDate(execution.created_at);
                            return d ? d.toLocaleString() : '-';
                          })()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(`/executions/${execution.id}`);
                            }}
                            className="text-blue-600 hover:text-blue-700 font-medium"
                          >
                            View Details →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
