'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import AgentForm from '@/components/crews/AgentForm';
import AgentExecuteModal from '@/components/agents/AgentExecuteModal';
import { useAgents } from '@/lib/hooks/useAgents';

export default function AgentsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { agents, loading, error, refetch } = useAgents();

  const [showAgentForm, setShowAgentForm] = useState(false);
  const [editingAgentId, setEditingAgentId] = useState<number | undefined>();
  const [executingAgent, setExecutingAgent] = useState<any | null>(null);

  const providerFilter = searchParams?.get('llm_provider_id');

  const loadData = () => {
    refetch();
  };

  useEffect(() => {
    // No-op for now; placeholder if we add more deep-link behavior
  }, [providerFilter]);

  const clearFilter = () => {
    router.push('/agents');
  };

  const handleCreateAgent = () => {
    setEditingAgentId(undefined);
    setShowAgentForm(true);
  };

  const handleEditAgent = (agentId: number) => {
    setEditingAgentId(agentId);
    setShowAgentForm(true);
  };

  const handleSaveAgent = () => {
    setShowAgentForm(false);
    void loadData();
  };

  if (showAgentForm) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-4xl mx-auto p-6">
              <div className="mb-4">
                <Breadcrumbs />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {editingAgentId ? 'Edit Agent' : 'Create New Agent'}
              </h2>
              <AgentForm
                agentId={editingAgentId}
                onSave={handleSaveAgent}
                onCancel={() => setShowAgentForm(false)}
              />
            </div>
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
          <div className="max-w-7xl mx-auto p-6">
            <Breadcrumbs />
            <div className="flex items-center justify-between mb-2">
              <h1 className="text-3xl font-bold text-gray-900">Agents</h1>
              <div className="flex gap-2">
                <button
                  onClick={handleCreateAgent}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                >
                  Create Agent
                </button>
              </div>
            </div>

            {providerFilter && (
              <div className="mb-4 flex items-center gap-3">
                <span className="text-sm text-gray-600">Active filter:</span>
                <span className="inline-flex items-center gap-2 text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2 py-1 rounded">
                  Agents · provider #{providerFilter}
                  <button
                    onClick={clearFilter}
                    className="ml-1 text-blue-700 hover:text-blue-900"
                    aria-label="Clear filter"
                    title="Clear filter"
                  >
                    ✕
                  </button>
                </span>
              </div>
            )}

            {error ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="text-center max-w-md">
                  <p className="text-red-600 mb-4">Failed to load agents: {error}</p>
                  <button
                    onClick={loadData}
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
            ) : agents.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <p className="text-gray-500 mb-4">No agents yet. Create your first agent to get started.</p>
                <button
                  onClick={handleCreateAgent}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                >
                  Create Agent
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {(providerFilter
                  ? agents.filter((a: any) => (a as any).llm_provider_id === Number(providerFilter))
                  : agents
                ).map((agent) => (
                  <div
                    key={agent.id}
                    className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow"
                  >
                    <h3 className="text-lg font-semibold text-gray-900">{agent.name}</h3>
                    <p className="text-sm text-gray-600 mt-1">{agent.role}</p>
                    <p className="text-xs text-gray-500 mt-2 line-clamp-2">{agent.goal}</p>
                    <div className="mt-4 flex items-center gap-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${
                        'bg-green-100 text-green-800'
                      }`}>
                        Active
                      </span>
                    </div>
                    <div className="mt-4 flex gap-2">
                      <button
                        onClick={() => setExecutingAgent(agent)}
                        className="flex-1 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
                      >
                        ▶ Execute
                      </button>
                      <button
                        onClick={() => handleEditAgent(agent.id)}
                        className="flex-1 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
                      >
                        Edit
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Execute Modal */}
      {executingAgent && (
        <AgentExecuteModal
          agentId={executingAgent.id}
          agentName={executingAgent.name}
          isOpen={!!executingAgent}
          onClose={() => setExecutingAgent(null)}
        />
      )}
    </ProtectedRoute>
  );
}

