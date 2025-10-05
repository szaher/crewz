'use client';

import type { Execution } from '@/types/api';

interface ExecutionDetailProps {
  execution: Execution;
}

export default function ExecutionDetail({ execution }: ExecutionDetailProps) {
  const getStatusColor = (status: Execution['status']) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800 border-green-200';
      case 'running': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'failed': return 'bg-red-100 text-red-800 border-red-200';
      case 'cancelled': return 'bg-gray-100 text-gray-800 border-gray-200';
      case 'pending': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Execution #{execution.id}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Type: <span className="capitalize">{execution.execution_type}</span>
            </p>
          </div>
          <span className={`px-3 py-1 text-sm font-medium rounded border ${getStatusColor(execution.status)}`}>
            {execution.status}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-500 uppercase">Started</p>
            <p className="mt-1 text-sm font-medium text-gray-900">
              {execution.started_at
                ? new Date(execution.started_at).toLocaleString()
                : 'Not started'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Completed</p>
            <p className="mt-1 text-sm font-medium text-gray-900">
              {execution.completed_at
                ? new Date(execution.completed_at).toLocaleString()
                : '-'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Duration</p>
            <p className="mt-1 text-sm font-medium text-gray-900">
              {execution.started_at && execution.completed_at
                ? `${Math.round((new Date(execution.completed_at).getTime() - new Date(execution.started_at).getTime()) / 1000)}s`
                : '-'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Created</p>
            <p className="mt-1 text-sm font-medium text-gray-900">
              {new Date(execution.created_at).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Input Data */}
      {execution.input_data && Object.keys(execution.input_data).length > 0 && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Input Data</h3>
          <pre className="bg-gray-50 rounded p-4 overflow-x-auto text-sm">
            {JSON.stringify(execution.input_data, null, 2)}
          </pre>
        </div>
      )}

      {/* Output Data */}
      {execution.output_data && Object.keys(execution.output_data).length > 0 && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Output Data</h3>
          <pre className="bg-gray-50 rounded p-4 overflow-x-auto text-sm">
            {JSON.stringify(execution.output_data, null, 2)}
          </pre>
        </div>
      )}

      {/* Error */}
      {execution.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-900 mb-2">Error</h3>
          <p className="text-sm text-red-800">{execution.error}</p>
        </div>
      )}
    </div>
  );
}
