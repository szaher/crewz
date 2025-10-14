'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { PermissionGate } from '@/components/PermissionGate';
import { apiClient } from '@/lib/api-client';

interface Flow {
  id: number;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export default function FlowsPage() {
  const router = useRouter();
  const [flows, setFlows] = useState<Flow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    loadFlows();
  }, []);

  const loadFlows = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/flows');
      if (response.data) {
        setFlows(response.data.flows || []);
      }
    } catch (err: any) {
      console.error('Failed to load flows:', err);
      setError(err.message || 'Failed to load flows');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateFlow = async () => {
    try {
      const response = await apiClient.post('/api/v1/flows', {
        name: 'New Flow',
        description: 'A new workflow',
        nodes: [],
        edges: [],
        tags: [],
      });

      const flowId = response.data?.id;

      if (flowId) {
        router.push(`/flows/${flowId}`);
      } else {
        alert('Flow created but no ID returned');
      }
    } catch (err: any) {
      console.error('Failed to create flow:', err);
      alert('Failed to create flow: ' + (err.message || 'Unknown error'));
    }
  };

  const handleDeleteFlow = async (flowId: number) => {
    if (!confirm('Are you sure you want to delete this flow?')) return;

    try {
      await apiClient.delete(`/api/v1/flows/${flowId}`);
      await loadFlows();
    } catch (err: any) {
      console.error('Failed to delete flow:', err);
      alert('Failed to delete flow: ' + (err.message || 'Unknown error'));
    }
  };

  // Filter flows
  const filteredFlows = flows.filter(flow => {
    if (search && !flow.name.toLowerCase().includes(search.toLowerCase()) &&
        !flow.description.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (filterStatus !== 'all' && flow.status !== filterStatus) return false;
    return true;
  });

  const hasActiveFilters = search || filterStatus !== 'all';

  // Extract unique statuses
  const statuses = Array.from(new Set(flows.map(f => f.status)));

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
                <h1 className="text-3xl font-bold text-gray-900">Flows</h1>
                <p className="text-sm text-gray-600 mt-1">
                  Create and manage your AI workflow automations
                </p>
              </div>
              <PermissionGate resourceType="flow" action="write">
                <button
                  onClick={handleCreateFlow}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                >
                  + Create Flow
                </button>
              </PermissionGate>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Search */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Search
                  </label>
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search flows..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Status Filter */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Status
                  </label>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All Status</option>
                    {statuses.map(status => (
                      <option key={status} value={status} className="capitalize">
                        {status}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Clear Filters */}
              {hasActiveFilters && (
                <div className="mt-4">
                  <button
                    onClick={() => {
                      setSearch('');
                      setFilterStatus('all');
                    }}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    Clear all filters
                  </button>
                </div>
              )}
            </div>

            {/* Content */}
            {error ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="text-center max-w-md">
                  <p className="text-red-600 mb-4">Failed to load flows: {error}</p>
                  <button
                    onClick={loadFlows}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Retry
                  </button>
                </div>
              </div>
            ) : loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : filteredFlows.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <p className="text-gray-500 mb-4">
                  {hasActiveFilters
                    ? 'No flows match your filters.'
                    : 'No flows yet. Create your first flow to get started.'}
                </p>
                {!hasActiveFilters && (
                  <PermissionGate resourceType="flow" action="write">
                    <button
                      onClick={handleCreateFlow}
                      className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                    >
                      Create Flow
                    </button>
                  </PermissionGate>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredFlows.map((flow) => (
                  <FlowCard
                    key={flow.id}
                    flow={flow}
                    onEdit={() => router.push(`/flows/${flow.id}`)}
                    onDelete={() => handleDeleteFlow(flow.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

// Flow Card Component
function FlowCard({
  flow,
  onEdit,
  onDelete
}: {
  flow: Flow;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-900 flex-1">
          {flow.name}
        </h3>
        <span
          className={`px-2 py-1 text-xs font-medium rounded ${
            flow.status === 'active'
              ? 'bg-green-100 text-green-800'
              : flow.status === 'draft'
              ? 'bg-gray-100 text-gray-800'
              : 'bg-red-100 text-red-800'
          }`}
        >
          {flow.status}
        </span>
      </div>

      <p className="text-sm text-gray-600 mt-2 line-clamp-2">
        {flow.description || 'No description'}
      </p>

      {/* Metadata */}
      <div className="mt-4 text-xs text-gray-500">
        Updated: {new Date(flow.updated_at).toLocaleDateString()}
      </div>

      {/* Actions */}
      <div className="mt-4 flex gap-2">
        <PermissionGate resourceType="flow" action="write" resourceId={flow.id.toString()}>
          <button
            onClick={onEdit}
            className="flex-1 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
          >
            Edit
          </button>
        </PermissionGate>
        <PermissionGate resourceType="flow" action="delete" resourceId={flow.id.toString()}>
          <button
            onClick={onDelete}
            className="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100"
          >
            Delete
          </button>
        </PermissionGate>
      </div>
    </div>
  );
}
