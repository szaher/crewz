'use client';

import { useEffect, useState } from 'react';
import { useAgents } from '@/lib/hooks/useAgents';
import { useToolStore } from '@/lib/store';
import { useLLMProviders } from '@/lib/hooks/useLLMProviders';
import type { AgentCreate, AgentUpdate } from '@/types/api';

interface AgentFormProps {
  agentId?: number;
  onSave?: (agentId: number) => void;
  onCancel?: () => void;
}

export default function AgentForm({ agentId, onSave, onCancel }: AgentFormProps) {
  const { agents, createAgent, updateAgent: updateAgentHook } = useAgents();
  const { tools } = useToolStore();
  const { providers, refetch: refetchProviders } = useLLMProviders();

  const existingAgent = agentId ? agents.find((a) => a.id === agentId) : null;

  const [formData, setFormData] = useState<AgentCreate>({
    name: existingAgent?.name || '',
    role: existingAgent?.role || '',
    goal: existingAgent?.goal || '',
    backstory: existingAgent?.backstory || '',
    llm_provider_id: existingAgent?.llm_provider_id || (providers[0]?.id ?? 0),
    temperature: existingAgent?.temperature ?? 0.7,
    max_tokens: existingAgent?.max_tokens,
    allow_delegation: existingAgent?.allow_delegation ?? true,
    verbose: existingAgent?.verbose ?? false,
    cache: existingAgent?.cache ?? true,
    max_iter: existingAgent?.max_iter ?? 15,
    max_rpm: existingAgent?.max_rpm,
    max_execution_time: existingAgent?.max_execution_time,
    allow_code_execution: existingAgent?.allow_code_execution ?? false,
    respect_context_window: existingAgent?.respect_context_window ?? true,
    max_retry_limit: existingAgent?.max_retry_limit ?? 2,
    tool_ids: [],
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Ensure providers list is available
    refetchProviders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // Default the provider if not set and providers loaded
    if (!formData.llm_provider_id && providers.length > 0) {
      setFormData((prev) => ({ ...prev, llm_provider_id: providers[0].id }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [providers]);

  const handleChange = (key: keyof (AgentCreate & AgentUpdate), value: any) => {
    setFormData({ ...formData, [key]: value } as AgentCreate);
  };

  const handleToolToggle = (toolId: number) => {
    const newTools = formData.tool_ids?.includes(toolId)
      ? formData.tool_ids.filter((id) => id !== toolId)
      : [...(formData.tool_ids || []), toolId];

    setFormData({ ...formData, tool_ids: newTools });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (agentId) {
        const payload: AgentUpdate = { ...formData };
        const updatedAgent = await updateAgentHook(agentId, payload);
        onSave?.(updatedAgent.id);
      } else {
        const payload: AgentCreate = { ...formData };
        // Ensure required fields
        if (!payload.llm_provider_id || payload.llm_provider_id === 0) {
          throw new Error('Please select an LLM provider.');
        }
        const newAgent = await createAgent(payload);
        onSave?.(newAgent.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save agent');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Information */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Agent Details</h3>

        <div className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700">
              Agent Name
            </label>
            <input
              id="name"
              type="text"
              required
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
              placeholder="e.g., Research Analyst"
            />
          </div>

          <div>
            <label htmlFor="role" className="block text-sm font-medium text-gray-700">
              Role
            </label>
            <input
              id="role"
              type="text"
              required
              value={formData.role}
              onChange={(e) => handleChange('role', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
              placeholder="e.g., Senior Research Analyst"
            />
          </div>

          <div>
            <label htmlFor="goal" className="block text-sm font-medium text-gray-700">
              Goal
            </label>
            <textarea
              id="goal"
              required
              rows={2}
              value={formData.goal}
              onChange={(e) => handleChange('goal', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
              placeholder="What is this agent's primary objective?"
            />
          </div>

          <div>
            <label htmlFor="backstory" className="block text-sm font-medium text-gray-700">
              Backstory
            </label>
            <textarea
              id="backstory"
              required
              rows={3}
              value={formData.backstory}
              onChange={(e) => handleChange('backstory', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
              placeholder="Provide context and personality for the agent"
            />
          </div>
        </div>
      </div>

      {/* LLM Configuration */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">LLM Configuration</h3>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="provider" className="block text-sm font-medium text-gray-700">
              Provider
            </label>
            <select
              id="provider"
              required
              value={formData.llm_provider_id || 0}
              onChange={(e) => handleChange('llm_provider_id', Number(e.target.value))}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
            >
              <option value={0}>Select provider...</option>
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.provider_type})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="temperature" className="block text-sm font-medium text-gray-700">
              Temperature
            </label>
            <input
              id="temperature"
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={formData.temperature ?? 0.7}
              onChange={(e) => handleChange('temperature', parseFloat(e.target.value))}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="max_tokens" className="block text-sm font-medium text-gray-700">
              Max Tokens
            </label>
            <input
              id="max_tokens"
              type="number"
              value={formData.max_tokens ?? ''}
              onChange={(e) => handleChange('max_tokens', e.target.value === '' ? undefined : parseInt(e.target.value))}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Tools */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Tools ({formData.tool_ids?.length || 0} selected)
        </h3>

        {tools.length === 0 ? (
          <p className="text-sm text-gray-500">No tools available</p>
        ) : (
          <div className="space-y-2">
            {tools.map((tool) => (
              <label key={tool.id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.tool_ids?.includes(tool.id) || false}
                  onChange={() => handleToolToggle(tool.id)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{tool.name}</p>
                  <p className="text-sm text-gray-500">{tool.description}</p>
                </div>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Options */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="grid grid-cols-2 gap-3">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!formData.allow_delegation}
              onChange={(e) => handleChange('allow_delegation', e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Allow delegation</span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!formData.verbose}
              onChange={(e) => handleChange('verbose', e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Verbose logging</span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!formData.cache}
              onChange={(e) => handleChange('cache', e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Enable cache</span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!formData.allow_code_execution}
              onChange={(e) => handleChange('allow_code_execution', e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Allow code execution</span>
          </label>

          <label className="flex items-center gap-2 col-span-2">
            <input
              type="checkbox"
              checked={!!formData.respect_context_window}
              onChange={(e) => handleChange('respect_context_window', e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Respect context window</span>
          </label>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Submit Buttons */}
      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Saving...' : agentId ? 'Update Agent' : 'Create Agent'}
        </button>
      </div>
    </form>
  );
}
