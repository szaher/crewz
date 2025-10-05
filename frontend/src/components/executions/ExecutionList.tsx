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

  const formatDuration = (startedAt?: string, completedAt?: string) => {
    if (!startedAt) return '-';
    if (!completedAt) return 'Running...';

    const start = new Date(startedAt).getTime();
    const end = new Date(completedAt).getTime();
    const duration = (end - start) / 1000; // seconds

    if (duration < 60) return `${Math.round(duration)}s`;
    if (duration < 3600) return `${Math.round(duration / 60)}m`;
    return `${Math.round(duration / 3600)}h`;
  };

  if (executions.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
        <p className="text-gray-500">No executions found</p>
      </div>
    );
  }

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
          {executions.map((execution) => (
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
                {formatDuration(execution.started_at, execution.completed_at)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {execution.started_at
                  ? new Date(execution.started_at).toLocaleString()
                  : 'Not started'}
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
