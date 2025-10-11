'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
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

      console.log('Create flow response:', response);

      // The backend returns the flow object in .data
      const flowId = response.data?.id;

      if (flowId) {
        console.log('Redirecting to flow:', flowId);
        router.push(`/flows/${flowId}`);
      } else {
        console.error('No flow ID in response:', response);
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
      await loadFlows(); // Reload the list
    } catch (err: any) {
      console.error('Failed to delete flow:', err);
      alert('Failed to delete flow: ' + (err.message || 'Unknown error'));
    }
  };

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Flows</h1>
              <p className="mt-2 text-gray-600">
                Create and manage your AI workflow automations
              </p>
            </div>
            <button
              onClick={handleCreateFlow}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              + Create Flow
            </button>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800">{error}</p>
            </div>
          )}

          {flows.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No flows</h3>
              <p className="mt-1 text-sm text-gray-500">
                Get started by creating a new flow.
              </p>
              <div className="mt-6">
                <button
                  onClick={handleCreateFlow}
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  + Create Flow
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {flows.map((flow) => (
                <div
                  key={flow.id}
                  className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow border border-gray-200"
                >
                  <div className="p-6">
                    <div className="flex items-start justify-between">
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {flow.name}
                      </h3>
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
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
                    <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                      {flow.description || 'No description'}
                    </p>
                    <div className="text-xs text-gray-500 mb-4">
                      Updated: {new Date(flow.updated_at).toLocaleDateString()}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => router.push(`/flows/${flow.id}`)}
                        className="flex-1 px-3 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteFlow(flow.id)}
                        className="px-3 py-2 bg-red-100 text-red-700 text-sm rounded hover:bg-red-200 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
