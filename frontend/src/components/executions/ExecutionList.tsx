'use client';

import { useRouter } from 'next/navigation';
import type { Execution } from '@/types/api';

interface ExecutionListProps {
  executions: Execution[];
}

export default function ExecutionList({ executions }: ExecutionListProps) {
  const router = useRouter();

  const getStatusColor = (status: Execution['status']) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'running': return 'bg-blue-100 text-blue-800';
      case 'failed': return 'bg-red-100 text-red-800';
      case 'cancelled': return 'bg-gray-100 text-gray-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getExecutionTypeIcon = (type: Execution['execution_type']) => {
    switch (type) {
      case 'flow': return '🔀';
      case 'crew': return '👥';
      case 'agent': return '🤖';
      default: return '⚙️';
    }
  };

  const formatDuration = (execution: Execution) => {
    // Use execution_time_ms if available (this is the primary source)
    if (execution.execution_time_ms) {
      const seconds = execution.execution_time_ms / 1000;
      if (seconds < 60) return `${Math.round(seconds)}s`;
      if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
      return `${Math.round(seconds / 3600)}h`;
    }

    // For running executions, calculate from created_at to now
    if (execution.status === 'running') {
      const start = new Date(execution.created_at).getTime();
      const now = Date.now();
      if (!isNaN(start)) {
        const duration = (now - start) / 1000;
        if (duration < 60) return `${Math.round(duration)}s`;
        if (duration < 3600) return `${Math.round(duration / 60)}m`;
        return `${Math.round(duration / 3600)}h`;
      }
    }

    // For completed/failed executions without execution_time_ms, try to calculate from timestamps
    if (execution.completed_at && execution.started_at) {
      const start = new Date(execution.started_at).getTime();
      const end = new Date(execution.completed_at).getTime();

      if (!isNaN(start) && !isNaN(end)) {
        const duration = (end - start) / 1000;
        if (duration < 60) return `${Math.round(duration)}s`;
        if (duration < 3600) return `${Math.round(duration / 60)}m`;
        return `${Math.round(duration / 3600)}h`;
      }
    }

    return '-';
  };

  const formatStartedAt = (execution: Execution) => {
    // Use started_at if available, otherwise use created_at
    const dateStr = execution.started_at || execution.created_at;
    if (!dateStr) return '-';

    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '-';

    return date.toLocaleString();
  };

  if (executions.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
        <p className="text-gray-500">No executions found</p>
      </div>
    );
  }

  // Sort executions by ID descending (newest first)
  const sortedExecutions = [...executions].sort((a, b) => b.id - a.id);

  return (
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
          {sortedExecutions.map((execution) => (
            <tr
              key={execution.id}
              className="hover:bg-gray-50 cursor-pointer"
              onClick={() => router.push(`/executions/${execution.id}`)}
            >
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                #{execution.id}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <div className="flex items-center gap-2">
                  <span>{getExecutionTypeIcon(execution.execution_type)}</span>
                  <span className="capitalize">{execution.execution_type}</span>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(execution.status)}`}>
                  {execution.status}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatDuration(execution)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatStartedAt(execution)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/executions/${execution.id}`);
                  }}
                  className="text-blue-600 hover:text-blue-900"
                >
                  View Details
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
