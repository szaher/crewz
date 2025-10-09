"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useCrews } from '@/lib/hooks/useCrews';
import { useAgents } from '@/lib/hooks/useAgents';
import { useLLMProviders } from '@/lib/hooks/useLLMProviders';
import type { CrewCreate, CrewUpdate } from '@/types/api';
import AgentCard from './AgentCard';

interface CrewBuilderProps {
  crewId?: number;
  onSave?: (crewId: number) => void;
}

export default function CrewBuilder({ crewId, onSave }: CrewBuilderProps) {
  const router = useRouter();
  const { crews, createCrew, updateCrew: updateCrewHook, getCrew } = useCrews();
  const { agents, loading: agentsLoading, error: agentsError, refetch: refetchAgents } = useAgents();
  const { providers, loading: providersLoading } = useLLMProviders();

  const existingCrew = crewId ? crews.find((c) => c.id === crewId) : null;

  const [formData, setFormData] = useState<CrewCreate>({
    name: existingCrew?.name || '',
    description: existingCrew?.description || '',
    process_type: existingCrew?.process_type || 'sequential',
    agent_ids: existingCrew?.agent_ids || [],
    task_delegation_enabled: existingCrew?.task_delegation_enabled ?? true,
    verbose: existingCrew?.verbose ?? false,
    config: existingCrew?.config || {},
  });

  const [selectedAgents, setSelectedAgents] = useState<number[]>(existingCrew?.agent_ids || []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [providerFilter, setProviderFilter] = useState<number | 'all'>('all');

  useEffect(() => {
    // Ensure agents are loaded when opening the builder
    refetchAgents();
  }, [refetchAgents]);

  useEffect(() => {
    if (existingCrew) {
      setFormData({
        name: existingCrew.name,
        description: existingCrew.description,
        process_type: existingCrew.process_type,
        agent_ids: existingCrew.agent_ids,
        task_delegation_enabled: existingCrew.task_delegation_enabled,
        verbose: existingCrew.verbose,
        config: existingCrew.config,
      });
      setSelectedAgents(existingCrew.agent_ids);
    }
  }, [existingCrew]);

  const handleAgentToggle = (agentId: number) => {
    const newSelection = selectedAgents.includes(agentId)
      ? selectedAgents.filter((id) => id !== agentId)
      : [...selectedAgents, agentId];

    setSelectedAgents(newSelection);
    setFormData({ ...formData, agent_ids: newSelection });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (formData.agent_ids.length === 0) {
      setError('Please select at least one agent');
      return;
    }

    setLoading(true);

    try {
      if (crewId) {
        // Update existing crew
        const updatedCrew = await updateCrewHook(crewId, formData);
        onSave?.(updatedCrew.id);
      } else {
        // Create new crew
        const newCrew = await createCrew(formData);
        onSave?.(newCrew.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save crew');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        {crewId ? 'Edit Crew' : 'Create New Crew'}
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h3>

          <div className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                Crew Name
              </label>
              <input
                id="name"
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                placeholder="e.g., Research Team"
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <textarea
                id="description"
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                placeholder="What does this crew do?"
              />
            </div>

            <div>
              <label htmlFor="process_type" className="block text-sm font-medium text-gray-700">
                Collaboration Pattern
              </label>
              <select
                id="process_type"
                value={formData.process_type}
                onChange={(e) => setFormData({ ...formData, process_type: e.target.value as 'sequential' | 'hierarchical' })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
              >
                <option value="sequential">Sequential (agents work in order)</option>
                <option value="hierarchical">Hierarchical (manager assigns tasks)</option>
              </select>
            </div>

            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.task_delegation_enabled}
                  onChange={(e) => setFormData({ ...formData, task_delegation_enabled: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Enable task delegation</span>
              </label>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.verbose}
                  onChange={(e) => setFormData({ ...formData, verbose: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Verbose logging</span>
              </label>
            </div>
          </div>
        </div>

        {/* Agent Selection */}
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Select Agents ({selectedAgents.length} selected)
          </h3>

          {/* Provider Filter */}
          <div className="flex items-center gap-3 mb-4">
            <label className="text-sm text-gray-700">Filter by provider</label>
            <select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
            >
              <option value="all">All providers</option>
              {!providersLoading && providers.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.provider_type})</option>
              ))}
            </select>
          </div>

          {agentsError ? (
            <div className="text-sm text-red-600">Failed to load agents: {agentsError}</div>
          ) : agentsLoading ? (
            <div className="text-sm text-gray-500">Loading agents…</div>
          ) : agents.length === 0 ? (
            <div>
              <p className="text-sm text-gray-500 mb-3">No agents available. Create your first agent to get started.</p>
              <button
                type="button"
                onClick={() => router.push('/agents')}
                className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                Create Agent
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(providerFilter === 'all'
                ? agents
                : agents.filter((a: any) => (a as any).llm_provider_id === Number(providerFilter))
              ).map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  selected={selectedAgents.includes(agent.id)}
                  onToggle={() => handleAgentToggle(agent.id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => window.history.back()}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Saving...' : crewId ? 'Update Crew' : 'Create Crew'}
          </button>
        </div>
      </form>
    </div>
  );
}
