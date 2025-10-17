'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { apiClient } from '@/lib/api-client';
import { useAgents } from '@/lib/hooks/useAgents';
import type { Crew, CrewUpdate } from '@/types/api';

export default function CrewEditPage() {
  const params = useParams();
  const router = useRouter();
  const crewId = params.id as string;

  const [crew, setCrew] = useState<Crew | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { agents } = useAgents();

  const [formData, setFormData] = useState<CrewUpdate>({
    name: '',
    description: '',
    process_type: 'sequential',
    agent_ids: [],
    task_ids: [],
    task_delegation_enabled: false,
    verbose: false,
    config: {},
    is_active: true,
  });

  // Load crew data
  useEffect(() => {
    const loadCrew = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get(`/api/v1/crews/${crewId}`);
        const crewData = response.data as Crew;
        setCrew(crewData);

        // Populate form with crew data
        setFormData({
          name: crewData.name,
          description: crewData.description,
          process_type: crewData.process_type,
          agent_ids: crewData.agent_ids || [],
          task_delegation_enabled: crewData.task_delegation_enabled,
          verbose: crewData.verbose,
          config: crewData.config || {},
          is_active: crewData.is_active,
        });
      } catch (err) {
        console.error('Failed to load crew:', err);
        setError('Failed to load crew data');
      } finally {
        setLoading(false);
      }
    };

    loadCrew();
  }, [crewId]);

  const handleChange = (key: keyof CrewUpdate, value: any) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleAgentToggle = (agentId: string) => {
    setFormData(prev => {
      const agentIds = prev.agent_ids || [];
      const newAgentIds = agentIds.includes(agentId)
        ? agentIds.filter(id => id !== agentId)
        : [...agentIds, agentId];
      return { ...prev, agent_ids: newAgentIds };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);

    try {
      await apiClient.put(`/api/v1/crews/${crewId}`, formData);
      router.push('/crews');
    } catch (err) {
      console.error('Failed to update crew:', err);
      setError(err instanceof Error ? err.message : 'Failed to update crew');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-4xl mx-auto p-6">
              <div className="mb-4">
                <Breadcrumbs />
              </div>
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  if (error && !crew) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-4xl mx-auto p-6">
              <div className="mb-4">
                <Breadcrumbs />
              </div>
              <div className="text-center py-12">
                <p className="text-red-600 mb-4">{error}</p>
                <button
                  onClick={() => router.push('/crews')}
                  className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                >
                  Back to Crews
                </button>
              </div>
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
          <div className="max-w-4xl mx-auto p-6">
            <div className="mb-4">
              <Breadcrumbs />
            </div>

            <h2 className="text-2xl font-bold text-gray-900 mb-6">Edit Crew</h2>

            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Basic Information */}
              <div className="bg-white p-6 rounded-lg border border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Name *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => handleChange('name', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Description
                    </label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => handleChange('description', e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Describe the purpose of this crew"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Process Type *
                    </label>
                    <select
                      value={formData.process_type}
                      onChange={(e) => handleChange('process_type', e.target.value as 'sequential' | 'hierarchical' | 'consensus')}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    >
                      <option value="sequential">Sequential - Tasks run one after another</option>
                      <option value="hierarchical">Hierarchical - Manager delegates to agents</option>
                      <option value="consensus">Consensus - Agents collaborate on decisions</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Agent Assignment */}
              <div className="bg-white p-6 rounded-lg border border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Agents</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Select agents to include in this crew. Agents will execute tasks in the order they are listed.
                </p>

                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {agents.length === 0 ? (
                    <p className="text-sm text-gray-500">No agents available. Create agents first.</p>
                  ) : (
                    agents.map((agent) => (
                      <div key={agent.id} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={formData.agent_ids?.includes(agent.id) || false}
                          onChange={() => handleAgentToggle(agent.id)}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <label className="ml-2 block text-sm text-gray-700">
                          {agent.name} - {agent.role}
                        </label>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Behavior Settings */}
              <div className="bg-white p-6 rounded-lg border border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Behavior Settings</h3>

                <div className="space-y-4">
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.task_delegation_enabled}
                      onChange={(e) => handleChange('task_delegation_enabled', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label className="ml-2 block text-sm text-gray-700">
                      Enable Task Delegation
                    </label>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.verbose}
                      onChange={(e) => handleChange('verbose', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label className="ml-2 block text-sm text-gray-700">
                      Verbose Output
                    </label>
                  </div>

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.is_active}
                      onChange={(e) => handleChange('is_active', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label className="ml-2 block text-sm text-gray-700">
                      Active
                    </label>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => router.push('/crews')}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-blue-300"
                  disabled={saving}
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
