'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import CrewBuilder from '@/components/crews/CrewBuilder';
import AgentForm from '@/components/crews/AgentForm';
import { useCrews } from '@/lib/hooks/useCrews';
import { useAgents } from '@/lib/hooks/useAgents';

export default function CrewsPage() {
  const router = useRouter();
  const { crews, loading: crewsLoading, error: crewsError, refetch: refetchCrews } = useCrews();
  const { agents, loading: agentsLoading, error: agentsError, refetch: refetchAgents } = useAgents();
  const searchParams = useSearchParams();

  const loading = crewsLoading || agentsLoading;
  const error = crewsError || agentsError;

  const [activeTab, setActiveTab] = useState<'crews' | 'agents'>('crews');
  const [showCrewBuilder, setShowCrewBuilder] = useState(false);
  const [showAgentForm, setShowAgentForm] = useState(false);
  const [editingCrewId, setEditingCrewId] = useState<number | undefined>();
  const [editingAgentId, setEditingAgentId] = useState<number | undefined>();

  const loadData = () => {
    refetchCrews();
    refetchAgents();
  };

  // Apply deep-linking filters via query params
  const providerFilter = searchParams?.get('llm_provider_id');
  const managerFilter = searchParams?.get('manager_llm_provider_id');

  useEffect(() => {
    if (providerFilter) {
      setActiveTab('agents');
    } else if (managerFilter) {
      setActiveTab('crews');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [providerFilter, managerFilter]);

  const clearFilter = () => {
    // Remove query params by navigating to base route
    router.push('/crews');
  };

  const handleCreateCrew = () => {
    setEditingCrewId(undefined);
    setShowCrewBuilder(true);
  };

  const handleEditCrew = (crewId: number) => {
    setEditingCrewId(crewId);
    setShowCrewBuilder(true);
  };

  const handleCreateAgent = () => {
    setEditingAgentId(undefined);
    setShowAgentForm(true);
  };

  const handleEditAgent = (agentId: number) => {
    setEditingAgentId(agentId);
    setShowAgentForm(true);
  };

  const handleSaveCrew = (crewId: number) => {
    setShowCrewBuilder(false);
    void loadData();
  };

  const handleSaveAgent = (agentId: number) => {
    setShowAgentForm(false);
    void loadData();
  };

  if (showCrewBuilder) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <CrewBuilder
              crewId={editingCrewId}
              onSave={handleSaveCrew}
            />
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  if (showAgentForm) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-4xl mx-auto p-6">
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
      <div className="flex h-screen bg-gray-50">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
        <Breadcrumbs />
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-gray-900">Crews & Agents</h1>
          <div className="flex gap-2">
            {activeTab === 'crews' ? (
              <button
                onClick={handleCreateCrew}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                Create Crew
              </button>
            ) : (
              <button
                onClick={handleCreateAgent}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                Create Agent
              </button>
            )}
          </div>
        </div>

        {(providerFilter || managerFilter) && (
          <div className="mb-4 flex items-center gap-3">
            <span className="text-sm text-gray-600">Active filter:</span>
            {providerFilter && (
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
            )}
            {managerFilter && (
              <span className="inline-flex items-center gap-2 text-xs bg-purple-50 text-purple-700 border border-purple-200 px-2 py-1 rounded">
                Crews · manager provider #{managerFilter}
                <button
                  onClick={clearFilter}
                  className="ml-1 text-purple-700 hover:text-purple-900"
                  aria-label="Clear filter"
                  title="Clear filter"
                >
                  ✕
                </button>
              </span>
            )}
          </div>
        )}

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="flex gap-8">
            <button
              onClick={() => setActiveTab('crews')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'crews'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {(() => {
                const count = managerFilter
                  ? crews.filter((c: any) => (c as any).manager_llm_provider_id === Number(managerFilter)).length
                  : crews.length;
                return <>Crews ({count})</>;
              })()}
            </button>
            <button
              onClick={() => setActiveTab('agents')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'agents'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {(() => {
                const count = providerFilter
                  ? agents.filter((a: any) => (a as any).llm_provider_id === Number(providerFilter)).length
                  : agents.length;
                return <>Agents ({count})</>;
              })()}
            </button>
          </nav>
        </div>

        {/* Content */}
        {error ? (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="text-center max-w-md">
              <p className="text-red-600 mb-4">Failed to load data: {error}</p>
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
        ) : activeTab === 'crews' ? (
          crews.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <p className="text-gray-500 mb-4">No crews yet. Create your first crew to get started.</p>
              <button
                onClick={handleCreateCrew}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                Create Crew
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {(managerFilter
                ? crews.filter((c: any) => (c as any).manager_llm_provider_id === Number(managerFilter))
                : crews
              ).map((crew) => (
              <div
                key={crew.id}
                className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow"
              >
                <h3 className="text-lg font-semibold text-gray-900">{crew.name}</h3>
                <p className="text-sm text-gray-600 mt-2">{crew.description}</p>
                <div className="mt-4 flex items-center gap-2">
                  <span className="px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-800">
                    {crew.process_type}
                  </span>
                  <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800">
                    {crew.agent_ids.length} agent{crew.agent_ids.length !== 1 ? 's' : ''}
                  </span>
                </div>
                <button
                  onClick={() => handleEditCrew(crew.id)}
                  className="mt-4 w-full px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
                >
                  Edit Crew
                </button>
              </div>
            ))}
          </div>
          )
        ) : (
          agents.length === 0 ? (
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
                    agent.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {agent.is_active ? 'Active' : 'Inactive'}
                  </span>
                  {agent.tools && agent.tools.length > 0 && (
                    <span className="px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-800">
                      {agent.tools.length} tool{agent.tools.length !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => handleEditAgent(agent.id)}
                  className="mt-4 w-full px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
                >
                  Edit Agent
                </button>
              </div>
            ))}
          </div>
          )
        )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
