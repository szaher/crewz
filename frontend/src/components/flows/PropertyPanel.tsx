'use client';

import { useState, useEffect } from 'react';
import { useAgentStore, useCrewStore, useToolStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';

interface PropertyPanelProps {
  selectedNode: any | null;
  onUpdateNode: (nodeId: string, data: any) => void;
}

export default function PropertyPanel({ selectedNode, onUpdateNode }: PropertyPanelProps) {
  const { agents, addAgent } = useAgentStore();
  const { crews } = useCrewStore();
  const { tools } = useToolStore();

  const [nodeData, setNodeData] = useState<any>({});
  const [showCreateAgent, setShowCreateAgent] = useState(false);
  const [showCreateLlmProvider, setShowCreateLlmProvider] = useState(false);
  const [llmProviders, setLlmProviders] = useState<any[]>([]);

  useEffect(() => {
    if (selectedNode) {
      setNodeData(selectedNode.data || {});
    }
  }, [selectedNode]);

  const loadLlmProviders = async () => {
    try {
      const response = await apiClient.get('/api/v1/llm-providers');
      setLlmProviders(response.data?.providers || []);
    } catch (error) {
      console.error('Failed to load LLM providers:', error);
    }
  };

  useEffect(() => {
    loadLlmProviders();
  }, []);

  if (!selectedNode) {
    return (
      <div className="bg-white border-l border-gray-200 p-4 w-80">
        <div className="text-center text-gray-500 mt-8">
          <p className="text-sm">Select a node to view properties</p>
        </div>
      </div>
    );
  }

  const handleUpdate = (key: string, value: any) => {
    const updatedData = { ...nodeData, [key]: value };
    setNodeData(updatedData);
    onUpdateNode(selectedNode.id, updatedData);
  };

  const handleCreateAgent = async (formData: any) => {
    try {
      const response = await apiClient.post('/api/v1/agents', formData);
      const newAgent = response.data;

      // Add to store
      addAgent(newAgent);

      // Select the new agent
      handleUpdate('agent_id', newAgent.id);

      // Close form
      setShowCreateAgent(false);
    } catch (error: any) {
      console.error('Failed to create agent:', error);
      alert('Failed to create agent: ' + (error.response?.data?.detail || error.message || 'Unknown error'));
    }
  };

  const handleCreateLlmProvider = async (formData: any) => {
    try {
      const response = await apiClient.post('/api/v1/llm-providers', formData);
      const newProvider = response.data?.provider || response.data;

      // Reload providers list
      await loadLlmProviders();

      // Close form
      setShowCreateLlmProvider(false);

      alert('LLM Provider created successfully!');
    } catch (error: any) {
      console.error('Failed to create LLM provider:', error);
      alert('Failed to create LLM provider: ' + (error.response?.data?.detail || error.message || 'Unknown error'));
    }
  };

  const renderAgentProperties = () => {
    const agent = agents.find(a => a.id === nodeData.agent_id);

    if (showCreateAgent) {
      if (showCreateLlmProvider) {
        return <LlmProviderCreateForm
          onSubmit={handleCreateLlmProvider}
          onCancel={() => setShowCreateLlmProvider(false)}
        />;
      }

      return <AgentCreateForm
        llmProviders={llmProviders}
        onSubmit={handleCreateAgent}
        onCancel={() => setShowCreateAgent(false)}
        onCreateProvider={() => setShowCreateLlmProvider(true)}
      />;
    }

    return (
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Select Agent
          </label>
          <div className="flex gap-2">
            <select
              value={nodeData.agent_id || ''}
              onChange={(e) => handleUpdate('agent_id', Number(e.target.value))}
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
            >
              <option value="">Choose an agent...</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name} - {agent.role}
                </option>
              ))}
            </select>
            <button
              onClick={() => setShowCreateAgent(true)}
              className="px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              title="Create new agent"
            >
              +
            </button>
          </div>
        </div>

        {agent && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg space-y-2">
            <h4 className="font-medium text-gray-900 text-sm">Agent Details</h4>
            <div className="space-y-1 text-xs">
              <p><span className="font-medium">Role:</span> {agent.role}</p>
              <p><span className="font-medium">Goal:</span> {agent.goal}</p>
              <p><span className="font-medium">Backstory:</span> {agent.backstory}</p>
            </div>

            <div className="mt-3 pt-3 border-t border-gray-200">
              <h5 className="font-medium text-gray-700 text-xs mb-2">Configuration</h5>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-600">Delegation:</span>
                  <span className="ml-1">{agent.allow_delegation ? '✓' : '✗'}</span>
                </div>
                <div>
                  <span className="text-gray-600">Verbose:</span>
                  <span className="ml-1">{agent.verbose ? '✓' : '✗'}</span>
                </div>
                <div>
                  <span className="text-gray-600">Cache:</span>
                  <span className="ml-1">{agent.cache ? '✓' : '✗'}</span>
                </div>
                <div>
                  <span className="text-gray-600">Max Iter:</span>
                  <span className="ml-1">{agent.max_iter}</span>
                </div>
                {agent.max_rpm && (
                  <div>
                    <span className="text-gray-600">Max RPM:</span>
                    <span className="ml-1">{agent.max_rpm}</span>
                  </div>
                )}
                {agent.max_execution_time && (
                  <div>
                    <span className="text-gray-600">Max Time:</span>
                    <span className="ml-1">{agent.max_execution_time}s</span>
                  </div>
                )}
                <div>
                  <span className="text-gray-600">Code Exec:</span>
                  <span className="ml-1">{agent.allow_code_execution ? '✓' : '✗'}</span>
                </div>
                <div>
                  <span className="text-gray-600">Retry Limit:</span>
                  <span className="ml-1">{agent.max_retry_limit}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Node Label
          </label>
          <input
            type="text"
            value={nodeData.label || ''}
            onChange={(e) => handleUpdate('label', e.target.value)}
            placeholder="Agent Node"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
          />
        </div>
      </div>
    );
  };

  const renderCrewProperties = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Select Crew
        </label>
        <select
          value={nodeData.crew_id || ''}
          onChange={(e) => handleUpdate('crew_id', Number(e.target.value))}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        >
          <option value="">Choose a crew...</option>
          {crews.map((crew) => (
            <option key={crew.id} value={crew.id}>
              {crew.name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Node Label
        </label>
        <input
          type="text"
          value={nodeData.label || ''}
          onChange={(e) => handleUpdate('label', e.target.value)}
          placeholder="Crew Node"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>
    </div>
  );

  const renderToolProperties = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Select Tool
        </label>
        <select
          value={nodeData.tool_id || ''}
          onChange={(e) => handleUpdate('tool_id', Number(e.target.value))}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        >
          <option value="">Choose a tool...</option>
          {tools.map((tool) => (
            <option key={tool.id} value={tool.id}>
              {tool.name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Node Label
        </label>
        <input
          type="text"
          value={nodeData.label || ''}
          onChange={(e) => handleUpdate('label', e.target.value)}
          placeholder="Tool Node"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>
    </div>
  );

  const renderGenericProperties = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Node Label
        </label>
        <input
          type="text"
          value={nodeData.label || ''}
          onChange={(e) => handleUpdate('label', e.target.value)}
          placeholder="Node Label"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Configuration (JSON)
        </label>
        <textarea
          value={JSON.stringify(nodeData.config || {}, null, 2)}
          onChange={(e) => {
            try {
              const config = JSON.parse(e.target.value);
              handleUpdate('config', config);
            } catch (err) {
              // Invalid JSON, ignore
            }
          }}
          rows={6}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>
    </div>
  );

  return (
    <div className="bg-white border-l border-gray-200 p-4 w-80 overflow-y-auto">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Node Properties
      </h3>

      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
        <p className="text-sm font-medium text-gray-700">
          Type: <span className="text-blue-600">{selectedNode.type}</span>
        </p>
        <p className="text-xs text-gray-500 mt-1">
          ID: {selectedNode.id}
        </p>
      </div>

      {selectedNode.type === 'agent' && renderAgentProperties()}
      {selectedNode.type === 'crew' && renderCrewProperties()}
      {selectedNode.type === 'tool' && renderToolProperties()}
      {!['agent', 'crew', 'tool'].includes(selectedNode.type) && renderGenericProperties()}
    </div>
  );
}

// Agent Creation Form Component
function AgentCreateForm({ llmProviders, onSubmit, onCancel, onCreateProvider }: {
  llmProviders: any[];
  onSubmit: (data: any) => void;
  onCancel: () => void;
  onCreateProvider: () => void;
}) {
  const [formData, setFormData] = useState({
    name: '',
    role: '',
    goal: '',
    backstory: '',
    llm_provider_id: '',
    temperature: 0.7,
    max_tokens: '',
    allow_delegation: true,
    verbose: false,
    cache: true,
    max_iter: 15,
    max_rpm: '',
    max_execution_time: '',
    allow_code_execution: false,
    respect_context_window: true,
    max_retry_limit: 2,
    tool_ids: [],
  });

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Clean up data
    const submitData = {
      ...formData,
      llm_provider_id: Number(formData.llm_provider_id),
      max_tokens: formData.max_tokens ? Number(formData.max_tokens) : undefined,
      max_rpm: formData.max_rpm ? Number(formData.max_rpm) : undefined,
      max_execution_time: formData.max_execution_time ? Number(formData.max_execution_time) : undefined,
    };

    onSubmit(submitData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-medium text-gray-900">Create New Agent</h4>
        <button
          type="button"
          onClick={onCancel}
          className="text-gray-400 hover:text-gray-600"
        >
          ✕
        </button>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
        <input
          type="text"
          required
          value={formData.name}
          onChange={(e) => handleChange('name', e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Role *</label>
        <input
          type="text"
          required
          value={formData.role}
          onChange={(e) => handleChange('role', e.target.value)}
          placeholder="e.g., Senior Data Analyst"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Goal *</label>
        <textarea
          required
          value={formData.goal}
          onChange={(e) => handleChange('goal', e.target.value)}
          rows={2}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Backstory *</label>
        <textarea
          required
          value={formData.backstory}
          onChange={(e) => handleChange('backstory', e.target.value)}
          rows={2}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">LLM Provider *</label>
        <div className="flex gap-2">
          <select
            required
            value={formData.llm_provider_id}
            onChange={(e) => handleChange('llm_provider_id', e.target.value)}
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
          >
            <option value="">Select provider...</option>
            {llmProviders.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.name} ({provider.provider_type})
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={onCreateProvider}
            className="px-3 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
            title="Create new LLM provider"
          >
            +
          </button>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
        <input
          type="number"
          step="0.1"
          min="0"
          max="2"
          value={formData.temperature}
          onChange={(e) => handleChange('temperature', parseFloat(e.target.value))}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Max Iterations</label>
          <input
            type="number"
            min="1"
            value={formData.max_iter}
            onChange={(e) => handleChange('max_iter', parseInt(e.target.value))}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Retry Limit</label>
          <input
            type="number"
            min="0"
            value={formData.max_retry_limit}
            onChange={(e) => handleChange('max_retry_limit', parseInt(e.target.value))}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={formData.allow_delegation}
            onChange={(e) => handleChange('allow_delegation', e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="ml-2 text-sm text-gray-700">Allow Delegation</span>
        </label>

        <label className="flex items-center">
          <input
            type="checkbox"
            checked={formData.cache}
            onChange={(e) => handleChange('cache', e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="ml-2 text-sm text-gray-700">Enable Cache</span>
        </label>

        <label className="flex items-center">
          <input
            type="checkbox"
            checked={formData.verbose}
            onChange={(e) => handleChange('verbose', e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="ml-2 text-sm text-gray-700">Verbose Logging</span>
        </label>

        <label className="flex items-center">
          <input
            type="checkbox"
            checked={formData.allow_code_execution}
            onChange={(e) => handleChange('allow_code_execution', e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="ml-2 text-sm text-gray-700">Allow Code Execution</span>
        </label>
      </div>

      <div className="flex gap-2 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="flex-1 px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Create Agent
        </button>
      </div>
    </form>
  );
}

// LLM Provider Creation Form Component
function LlmProviderCreateForm({ onSubmit, onCancel }: {
  onSubmit: (data: any) => void;
  onCancel: () => void;
}) {
  const [formData, setFormData] = useState({
    name: '',
    provider_type: 'openai',
    model_name: '',
    api_key: '',
    api_base: '',
    config: {},
    is_default: false,
  });

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Clean up data
    const submitData = {
      ...formData,
      api_key: formData.api_key || undefined,
      api_base: formData.api_base || undefined,
    };

    onSubmit(submitData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-medium text-gray-900">Create LLM Provider</h4>
        <button
          type="button"
          onClick={onCancel}
          className="text-gray-400 hover:text-gray-600"
        >
          ✕
        </button>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Provider Name *</label>
        <input
          type="text"
          required
          value={formData.name}
          onChange={(e) => handleChange('name', e.target.value)}
          placeholder="e.g., My OpenAI Provider"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Provider Type *</label>
        <select
          required
          value={formData.provider_type}
          onChange={(e) => handleChange('provider_type', e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        >
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="ollama">Ollama</option>
          <option value="vllm">vLLM</option>
          <option value="custom">Custom</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Model Name *</label>
        <input
          type="text"
          required
          value={formData.model_name}
          onChange={(e) => handleChange('model_name', e.target.value)}
          placeholder="e.g., gpt-4, claude-3-opus-20240229"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Examples: gpt-4, gpt-3.5-turbo, claude-3-opus-20240229, llama2
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
        <input
          type="password"
          value={formData.api_key}
          onChange={(e) => handleChange('api_key', e.target.value)}
          placeholder="sk-..."
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Optional for local models (Ollama, vLLM)
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">API Base URL</label>
        <input
          type="text"
          value={formData.api_base}
          onChange={(e) => handleChange('api_base', e.target.value)}
          placeholder="https://api.openai.com/v1"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Optional. For custom endpoints or local models.
        </p>
      </div>

      <div>
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={formData.is_default}
            onChange={(e) => handleChange('is_default', e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="ml-2 text-sm text-gray-700">Set as default provider</span>
        </label>
      </div>

      <div className="flex gap-2 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="flex-1 px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          Create Provider
        </button>
      </div>
    </form>
  );
}
