'use client';

import { useState, useEffect } from 'react';
import { useAgentStore, useCrewStore, useToolStore, useFlowStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';

interface PropertyPanelProps {
  selectedNode: any | null;
  onUpdateNode: (nodeId: string, data: any) => void;
  onClearSelection?: () => void;
}

export default function PropertyPanel({ selectedNode, onUpdateNode, onClearSelection }: PropertyPanelProps) {
  const { agents, addAgent } = useAgentStore();
  const { crews } = useCrewStore();
  const { tools } = useToolStore();
  const { currentFlow, updateFlow } = useFlowStore();

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

  const handleDeleteNode = () => {
    if (!currentFlow || !selectedNode) return;
    if (!confirm('Delete this node? Connected edges will be removed.')) return;

    const nodeId = selectedNode.id;
    const newNodes = (currentFlow.nodes || []).filter((n: any) => n.id !== nodeId);
    const newEdges = (currentFlow.edges || []).filter(
      (e: any) => e.source !== nodeId && e.target !== nodeId
    );
    updateFlow(currentFlow.id, { nodes: newNodes, edges: newEdges });
    // clear selection in editor
    onClearSelection?.();
  };

  // Layout controls (width slider) — available for all node types
  const minWidth = 260;
  const defaultWidth = selectedNode?.type === 'input' ? 300 : 260;
  const effectiveWidth = (typeof nodeData.width === 'number'
    ? nodeData.width
    : (selectedNode?.style?.width as number | undefined)) ?? defaultWidth;
  const maxWidth = 1000;

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

  const renderInputNodeProperties = () => {
    const inputs = nodeData.inputs || [];

    const addInput = () => {
      const newInputs = [...inputs, { name: `input_${inputs.length + 1}`, type: 'string', required: false }];
      handleUpdate('inputs', newInputs);
    };

    const removeInput = (index: number) => {
      const newInputs = inputs.filter((_: any, i: number) => i !== index);
      handleUpdate('inputs', newInputs);
    };

    const updateInput = (index: number, field: string, value: any) => {
      const newInputs = [...inputs];
      newInputs[index] = { ...newInputs[index], [field]: value };
      handleUpdate('inputs', newInputs);
    };

    return (
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Node Label
          </label>
          <input
            type="text"
            value={nodeData.label || ''}
            onChange={(e) => handleUpdate('label', e.target.value)}
            placeholder="Flow Input"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            value={nodeData.description || ''}
            onChange={(e) => handleUpdate('description', e.target.value)}
            rows={2}
            placeholder="Describe what inputs this flow expects..."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">
              Input Variables
            </label>
            <button
              onClick={addInput}
              className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              + Add Input
            </button>
          </div>

          <div className="space-y-2">
            {inputs.map((input: any, index: number) => (
              <div key={index} className="p-3 bg-gray-50 rounded border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-gray-600">Input {index + 1}</span>
                  <button
                    onClick={() => removeInput(index)}
                    className="text-xs text-red-600 hover:text-red-800"
                  >
                    Remove
                  </button>
                </div>
                <div className="space-y-2">
                  <input
                    type="text"
                    value={input.name || ''}
                    onChange={(e) => updateInput(index, 'name', e.target.value)}
                    placeholder="Variable name"
                    className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={input.type || 'string'}
                      onChange={(e) => updateInput(index, 'type', e.target.value)}
                      className="rounded border border-gray-300 px-2 py-1 text-xs"
                    >
                      <option value="string">String</option>
                      <option value="number">Number</option>
                      <option value="boolean">Boolean</option>
                      <option value="object">Object</option>
                      <option value="array">Array</option>
                    </select>
                    <label className="flex items-center text-xs">
                      <input
                        type="checkbox"
                        checked={input.required || false}
                        onChange={(e) => updateInput(index, 'required', e.target.checked)}
                        className="mr-1"
                      />
                      Required
                    </label>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {inputs.length === 0 && (
            <p className="text-xs text-gray-500 text-center py-4">
              No input variables defined. Click "Add Input" to add one.
            </p>
          )}
        </div>
      </div>
    );
  };

  const renderOutputNodeProperties = () => {
    const outputs = nodeData.outputs || [];

    const addOutput = () => {
      const newOutputs = [...outputs, { name: `output_${outputs.length + 1}`, type: 'string' }];
      handleUpdate('outputs', newOutputs);
    };

    const removeOutput = (index: number) => {
      const newOutputs = outputs.filter((_: any, i: number) => i !== index);
      handleUpdate('outputs', newOutputs);
    };

    const updateOutput = (index: number, field: string, value: any) => {
      const newOutputs = [...outputs];
      newOutputs[index] = { ...newOutputs[index], [field]: value };
      handleUpdate('outputs', newOutputs);
    };

    return (
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Node Label
          </label>
          <input
            type="text"
            value={nodeData.label || ''}
            onChange={(e) => handleUpdate('label', e.target.value)}
            placeholder="Flow Output"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            value={nodeData.description || ''}
            onChange={(e) => handleUpdate('description', e.target.value)}
            rows={2}
            placeholder="Describe what outputs this flow produces..."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">
              Output Variables
            </label>
            <button
              onClick={addOutput}
              className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700"
            >
              + Add Output
            </button>
          </div>

          <div className="space-y-2">
            {outputs.map((output: any, index: number) => (
              <div key={index} className="p-3 bg-gray-50 rounded border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-gray-600">Output {index + 1}</span>
                  <button
                    onClick={() => removeOutput(index)}
                    className="text-xs text-red-600 hover:text-red-800"
                  >
                    Remove
                  </button>
                </div>
                <div className="space-y-2">
                  <input
                    type="text"
                    value={output.name || ''}
                    onChange={(e) => updateOutput(index, 'name', e.target.value)}
                    placeholder="Variable name"
                    className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                  />
                  <select
                    value={output.type || 'string'}
                    onChange={(e) => updateOutput(index, 'type', e.target.value)}
                    className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
                  >
                    <option value="string">String</option>
                    <option value="number">Number</option>
                    <option value="boolean">Boolean</option>
                    <option value="object">Object</option>
                    <option value="array">Array</option>
                  </select>
                </div>
              </div>
            ))}
          </div>

          {outputs.length === 0 && (
            <p className="text-xs text-gray-500 text-center py-4">
              No output variables defined. Click "Add Output" to add one.
            </p>
          )}
        </div>
      </div>
    );
  };

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
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm font-medium text-gray-700">
              Type: <span className="text-blue-600">{selectedNode.type}</span>
            </p>
            <p className="text-xs text-gray-500 mt-1">ID: {selectedNode.id}</p>
          </div>
          <button
            onClick={handleDeleteNode}
            className="inline-flex items-center justify-center text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700"
            title="Delete node"
            aria-label="Delete node"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
              <path d="M9 3a1 1 0 0 0-1 1v1H5.5a1 1 0 1 0 0 2H6v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7h.5a1 1 0 1 0 0-2H16V4a1 1 0 0 0-1-1H9zm2 4a1 1 0 1 0-2 0v10a1 1 0 1 0 2 0V7zm4 0a1 1 0 1 0-2 0v10a1 1 0 1 0 2 0V7zM9 5h6v1H9V5z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Layout */}
      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Width: <span className="text-gray-600">{effectiveWidth}px</span>
        </label>
        <input
          type="range"
          min={minWidth}
          max={maxWidth}
          step={10}
          value={effectiveWidth}
          onChange={(e) => handleUpdate('width', parseInt(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between text-[10px] text-gray-500 mt-1">
          <span>{minWidth}px</span>
          <span>{maxWidth}px</span>
        </div>
      </div>

      {selectedNode.type === 'agent' && renderAgentProperties()}
      {selectedNode.type === 'crew' && renderCrewProperties()}
      {selectedNode.type === 'tool' && renderToolProperties()}
      {selectedNode.type === 'input' && renderInputNodeProperties()}
      {selectedNode.type === 'output' && renderOutputNodeProperties()}
      {!['agent', 'crew', 'tool', 'input', 'output'].includes(selectedNode.type) && renderGenericProperties()}
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
