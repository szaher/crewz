'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import CrewBuilder from '@/components/crews/CrewBuilder';
import AgentForm from '@/components/crews/AgentForm';
import { useCrewStore, useAgentStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';

export default function CrewsPage() {
  const router = useRouter();
  const { crews, setCrews } = useCrewStore();
  const { agents, setAgents } = useAgentStore();

  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'crews' | 'agents'>('crews');
  const [showCrewBuilder, setShowCrewBuilder] = useState(false);
  const [showAgentForm, setShowAgentForm] = useState(false);
  const [editingCrewId, setEditingCrewId] = useState<number | undefined>();
  const [editingAgentId, setEditingAgentId] = useState<number | undefined>();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [crewsResponse, agentsResponse] = await Promise.all([
        apiClient.get('/api/v1/crews'),
        apiClient.get('/api/v1/agents'),
      ]);

      if (crewsResponse.data) {
        setCrews(crewsResponse.data.crews || []);
      }
      if (agentsResponse.data) {
        setAgents(agentsResponse.data.agents || []);
      }
    } catch (error) {
      console.error('Failed to load crews and agents:', error);
    } finally {
      setLoading(false);
    }
  }, [setAgents, setCrews]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

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
        <CrewBuilder
          crewId={editingCrewId}
          onSave={handleSaveCrew}
        />
      </ProtectedRoute>
    );
  }

  if (showAgentForm) {
    return (
      <ProtectedRoute>
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
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="max-w-7xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
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
              Crews ({crews.length})
            </button>
            <button
              onClick={() => setActiveTab('agents')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'agents'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Agents ({agents.length})
            </button>
          </nav>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : activeTab === 'crews' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {crews.map((crew) => (
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
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents.map((agent) => (
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
        )}
      </div>
    </ProtectedRoute>
  );
}
