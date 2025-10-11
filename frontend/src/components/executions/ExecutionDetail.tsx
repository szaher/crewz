'use client';

import type { Execution } from '@/types/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '-';
    return date.toLocaleString();
  };

  const formatDuration = () => {
    // Use execution_time_ms if available
    if (execution.execution_time_ms) {
      const seconds = Math.floor(execution.execution_time_ms / 1000);
      const ms = execution.execution_time_ms % 1000;
      if (seconds < 60) return `${seconds}.${Math.floor(ms / 100)}s`;
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s`;
    }

    // For running executions, calculate from created_at to now
    if (execution.status === 'running' && execution.created_at) {
      const start = new Date(execution.created_at).getTime();
      const now = Date.now();
      if (!isNaN(start)) {
        const duration = (now - start) / 1000;
        if (duration < 60) return `${Math.round(duration)}s`;
        const minutes = Math.floor(duration / 60);
        const remainingSeconds = Math.round(duration % 60);
        return `${minutes}m ${remainingSeconds}s`;
      }
    }

    // Fallback: try to calculate from started_at and completed_at if they exist
    if (execution.started_at && execution.completed_at) {
      const start = new Date(execution.started_at).getTime();
      const end = new Date(execution.completed_at).getTime();
      if (!isNaN(start) && !isNaN(end)) {
        const seconds = Math.round((end - start) / 1000);
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}m ${remainingSeconds}s`;
      }
    }

    return '-';
  };

  // Extract output text from output_data for markdown rendering
  const getOutputText = () => {
    if (!execution.output_data) return null;

    // Check for common output field names
    if (typeof execution.output_data === 'string') {
      return execution.output_data;
    }

    if (execution.output_data.output) {
      return typeof execution.output_data.output === 'string'
        ? execution.output_data.output
        : JSON.stringify(execution.output_data.output, null, 2);
    }

    if (execution.output_data.result) {
      return typeof execution.output_data.result === 'string'
        ? execution.output_data.result
        : JSON.stringify(execution.output_data.result, null, 2);
    }

    // Fallback to JSON stringified output
    return JSON.stringify(execution.output_data, null, 2);
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
              {formatDate(execution.started_at || execution.created_at)}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Completed</p>
            <p className="mt-1 text-sm font-medium text-gray-900">
              {formatDate(execution.completed_at || execution.updated_at)}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Duration</p>
            <p className="mt-1 text-sm font-medium text-gray-900">
              {formatDuration()}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Created</p>
            <p className="mt-1 text-sm font-medium text-gray-900">
              {formatDate(execution.created_at)}
            </p>
          </div>
        </div>
      </div>

      {/* Input Data - Rendered as JSON */}
      {execution.input_data && Object.keys(execution.input_data).length > 0 && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Input Data</h3>
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 overflow-x-auto">
            <pre className="text-sm font-mono text-gray-800">
              <code className="language-json">
                {JSON.stringify(execution.input_data, null, 2)}
              </code>
            </pre>
          </div>
        </div>
      )}

      {/* Output Data - Rendered as Markdown */}
      {execution.output_data && Object.keys(execution.output_data).length > 0 && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Output</h3>
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 overflow-x-auto">
            <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-a:text-blue-600 prose-code:text-gray-800 prose-code:bg-gray-200 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-800 prose-pre:text-gray-100">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {getOutputText() || 'No output available'}
              </ReactMarkdown>
            </div>
          </div>
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
