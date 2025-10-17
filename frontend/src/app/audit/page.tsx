'use client';

import { useState } from 'react';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import { useAuditLogs } from '@/lib/hooks/useAuthorization';
import type { QueryAuditLogsParams } from '@/lib/api/authorization';

/**
 * Audit Log Viewer Page
 * Displays authorization decision audit logs for compliance and debugging
 */
export default function AuditPage() {
  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <div className="mb-8">
              <h1 className="text-3xl font-bold">Authorization Audit Logs</h1>
              <p className="text-gray-600 mt-2">
                View authorization decisions and access patterns
              </p>
            </div>
            <AuditLogsContent />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

function AuditLogsContent() {
  const [filters, setFilters] = useState<QueryAuditLogsParams>({
    page: 1,
    page_size: 50,
  });
  const [selectedLog, setSelectedLog] = useState<any>(null);

  const { logs, total, loading, error, refetch } = useAuditLogs(filters);

  const totalPages = Math.ceil(total / (filters.page_size || 50));

  const handleFilterChange = (newFilters: Partial<QueryAuditLogsParams>) => {
    setFilters({ ...filters, ...newFilters, page: 1 });
  };

  const handlePageChange = (newPage: number) => {
    setFilters({ ...filters, page: newPage });
  };

  if (loading && logs.length === 0) {
    return <div className="text-center py-8">Loading audit logs...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              User ID
            </label>
            <input
              type="text"
              value={filters.user_id || ''}
              onChange={(e) =>
                handleFilterChange({ user_id: e.target.value || undefined })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="Filter by user ID"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Resource Type
            </label>
            <input
              type="text"
              value={filters.resource_type || ''}
              onChange={(e) =>
                handleFilterChange({ resource_type: e.target.value || undefined })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="crew, flow, agent..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Decision
            </label>
            <select
              value={filters.decision || ''}
              onChange={(e) =>
                handleFilterChange({
                  decision: e.target.value ? (e.target.value as 'allow' | 'deny') : undefined,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All Decisions</option>
              <option value="allow">Allow</option>
              <option value="deny">Deny</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => {
                setFilters({ page: 1, page_size: 50 });
                refetch();
              }}
              className="w-full px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Clear Filters
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Time
            </label>
            <input
              type="datetime-local"
              value={filters.start_time ? filters.start_time.slice(0, 16) : ''}
              onChange={(e) =>
                handleFilterChange({
                  start_time: e.target.value ? new Date(e.target.value).toISOString() : undefined,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Time
            </label>
            <input
              type="datetime-local"
              value={filters.end_time ? filters.end_time.slice(0, 16) : ''}
              onChange={(e) =>
                handleFilterChange({
                  end_time: e.target.value ? new Date(e.target.value).toISOString() : undefined,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Total Logs</div>
          <div className="text-2xl font-bold">{total.toLocaleString()}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Current Page</div>
          <div className="text-2xl font-bold">{logs.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Allow Decisions</div>
          <div className="text-2xl font-bold text-green-600">
            {logs.filter((log) => log.decision === 'allow').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Deny Decisions</div>
          <div className="text-2xl font-bold text-red-600">
            {logs.filter((log) => log.decision === 'deny').length}
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Resource
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Decision
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Latency
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Reason
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                    No audit logs found matching the current filters.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr
                    key={log.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => setSelectedLog(log)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 truncate max-w-[150px]" title={log.user_id}>
                        {log.user_id.slice(0, 8)}...
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">{log.resource_type}</div>
                      {log.resource_id && (
                        <div className="text-xs text-gray-500 truncate max-w-[150px]" title={log.resource_id}>
                          {log.resource_id.slice(0, 12)}...
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          log.decision === 'allow'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {log.decision}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`text-sm ${
                          log.latency_ms < 10
                            ? 'text-green-600'
                            : log.latency_ms < 50
                            ? 'text-yellow-600'
                            : 'text-red-600'
                        }`}
                      >
                        {log.latency_ms}ms
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 truncate max-w-[200px]" title={log.reason}>
                        {log.reason}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-4">
          <button
            onClick={() => handlePageChange(Math.max(1, (filters.page || 1) - 1))}
            disabled={filters.page === 1}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {filters.page || 1} of {totalPages} ({total.toLocaleString()} total)
          </span>
          <button
            onClick={() => handlePageChange(Math.min(totalPages, (filters.page || 1) + 1))}
            disabled={filters.page === totalPages}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}

      {/* Detail Sidebar */}
      {selectedLog && (
        <LogDetailSidebar log={selectedLog} onClose={() => setSelectedLog(null)} />
      )}
    </div>
  );
}

function LogDetailSidebar({ log, onClose }: { log: any; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-end z-50" onClick={onClose}>
      <div
        className="bg-white w-full max-w-md h-full overflow-y-auto shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b flex justify-between items-center">
          <h2 className="text-xl font-semibold">Audit Log Details</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Decision */}
          <div>
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">Decision</h3>
            <div className="space-y-3">
              <div>
                <div className="text-xs text-gray-500">Result</div>
                <span
                  className={`inline-block px-3 py-1 text-sm font-medium rounded ${
                    log.decision === 'allow'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {log.decision.toUpperCase()}
                </span>
              </div>
              <div>
                <div className="text-xs text-gray-500">Reason</div>
                <div className="text-sm bg-gray-50 p-3 rounded">{log.reason}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Latency</div>
                <div
                  className={`text-sm font-medium ${
                    log.latency_ms < 10
                      ? 'text-green-600'
                      : log.latency_ms < 50
                      ? 'text-yellow-600'
                      : 'text-red-600'
                  }`}
                >
                  {log.latency_ms}ms
                  {log.latency_ms < 10 && ' (cached)'}
                  {log.latency_ms >= 10 && log.latency_ms < 50 && ' (fast)'}
                  {log.latency_ms >= 50 && ' (slow)'}
                </div>
              </div>
            </div>
          </div>

          {/* Request Info */}
          <div>
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">Request</h3>
            <div className="space-y-3">
              <div>
                <div className="text-xs text-gray-500">User ID</div>
                <div className="text-sm font-mono bg-gray-50 px-2 py-1 rounded break-all">
                  {log.user_id}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Tenant ID</div>
                <div className="text-sm font-mono bg-gray-50 px-2 py-1 rounded break-all">
                  {log.tenant_id}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Resource Type</div>
                <div className="text-sm">{log.resource_type}</div>
              </div>
              {log.resource_id && (
                <div>
                  <div className="text-xs text-gray-500">Resource ID</div>
                  <div className="text-sm font-mono bg-gray-50 px-2 py-1 rounded break-all">
                    {log.resource_id}
                  </div>
                </div>
              )}
              <div>
                <div className="text-xs text-gray-500">Action</div>
                <span className="inline-block px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded">
                  {log.action}
                </span>
              </div>
            </div>
          </div>

          {/* Client Info */}
          <div>
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">Client</h3>
            <div className="space-y-3">
              {log.ip_address && (
                <div>
                  <div className="text-xs text-gray-500">IP Address</div>
                  <div className="text-sm font-mono">{log.ip_address}</div>
                </div>
              )}
              {log.user_agent && (
                <div>
                  <div className="text-xs text-gray-500">User Agent</div>
                  <div className="text-xs bg-gray-50 p-2 rounded break-all">{log.user_agent}</div>
                </div>
              )}
            </div>
          </div>

          {/* Metadata */}
          <div>
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">Metadata</h3>
            <div className="space-y-2 text-xs text-gray-600">
              <div>
                <span className="font-medium">Log ID:</span> {log.id}
              </div>
              <div>
                <span className="font-medium">Timestamp:</span>{' '}
                {new Date(log.timestamp).toLocaleString()}
              </div>
              <div>
                <span className="font-medium">ISO Timestamp:</span> {log.timestamp}
              </div>
            </div>
          </div>

          {/* Performance Indicator */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="text-sm font-medium text-blue-900 mb-2">Performance</div>
            <div className="text-xs text-blue-700">
              {log.latency_ms < 10 && (
                <>
                  ✓ Excellent - Result from cache. Target: &lt;10ms for cached results.
                </>
              )}
              {log.latency_ms >= 10 && log.latency_ms < 50 && (
                <>✓ Good - Within p95 target of &lt;50ms for authorization checks.</>
              )}
              {log.latency_ms >= 50 && (
                <>
                  ⚠ Slow - Exceeded p95 target. This may indicate cache miss or complex policy
                  evaluation.
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
