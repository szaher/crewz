'use client';

import { useState } from 'react';
import { useAgents } from '@/lib/hooks/useAgents';
import { useToolStore } from '@/lib/store';
import type { AgentCreate, LLMConfig } from '@/types/api';

interface AgentFormProps {
  agentId?: number;
  onSave?: (agentId: number) => void;
  onCancel?: () => void;
}

export default function AgentForm({ agentId, onSave, onCancel }: AgentFormProps) {
  const { agents, createAgent, updateAgent: updateAgentHook } = useAgents();
  const { tools } = useToolStore();

  const existingAgent = agentId ? agents.find((a) => a.id === agentId) : null;

  const [formData, setFormData] = useState<AgentCreate>({
    name: existingAgent?.name || '',
    role: existingAgent?.role || '',
    goal: existingAgent?.goal || '',
    backstory: existingAgent?.backstory || '',
    llm_config: existingAgent?.llm_config || {
      provider: 'openai',
      model: 'gpt-4',
      temperature: 0.7,
      max_tokens: 2000,
    },
    tools: existingAgent?.tools || [],
    allow_delegation: existingAgent?.allow_delegation ?? true,
    verbose: existingAgent?.verbose ?? false,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLLMConfigChange = (key: keyof LLMConfig, value: any) => {
    setFormData({
      ...formData,
      llm_config: { ...formData.llm_config, [key]: value },
    });
  };

  const handleToolToggle = (toolId: number) => {
    const newTools = formData.tools?.includes(toolId)
      ? formData.tools.filter((id) => id !== toolId)
      : [...(formData.tools || []), toolId];

    setFormData({ ...formData, tools: newTools });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (agentId) {
        // Update existing agent
        const updatedAgent = await updateAgentHook(agentId, formData);
        onSave?.(updatedAgent.id);
      } else {
        // Create new agent
        const newAgent = await createAgent(formData);
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
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
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
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
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
              onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
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
              onChange={(e) => setFormData({ ...formData, backstory: e.target.value })}
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
              value={formData.llm_config.provider}
              onChange={(e) => handleLLMConfigChange('provider', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
            >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="ollama">Ollama (Local)</option>
              <option value="vllm">vLLM</option>
            </select>
          </div>

          <div>
            <label htmlFor="model" className="block text-sm font-medium text-gray-700">
              Model
            </label>
            <input
              id="model"
              type="text"
              value={formData.llm_config.model}
              onChange={(e) => handleLLMConfigChange('model', e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
              placeholder="e.g., gpt-4"
            />
          </div>

          <div>
            <label htmlFor="temperature" className="block text-sm font-medium text-gray-700">
              Temperature ({formData.llm_config.temperature})
            </label>
            <input
              id="temperature"
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={formData.llm_config.temperature}
              onChange={(e) => handleLLMConfigChange('temperature', parseFloat(e.target.value))}
              className="mt-1 block w-full"
            />
          </div>

          <div>
            <label htmlFor="max_tokens" className="block text-sm font-medium text-gray-700">
              Max Tokens
            </label>
            <input
              id="max_tokens"
              type="number"
              value={formData.llm_config.max_tokens}
              onChange={(e) => handleLLMConfigChange('max_tokens', parseInt(e.target.value))}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Tools */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Tools ({formData.tools?.length || 0} selected)
        </h3>

        {tools.length === 0 ? (
          <p className="text-sm text-gray-500">No tools available</p>
        ) : (
          <div className="space-y-2">
            {tools.map((tool) => (
              <label key={tool.id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.tools?.includes(tool.id)}
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
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.allow_delegation}
              onChange={(e) => setFormData({ ...formData, allow_delegation: e.target.checked })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Allow delegation</span>
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
