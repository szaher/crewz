'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import type { Agent, Tool } from '@/types/api';

interface Crew {
  id: string;
  name: string;
  description?: string;
}

interface FlowReference {
  id: string;
  name: string;
  description?: string;
}

interface FlowStep {
  id: string;
  name: string;
  description: string;
  type: 'agent' | 'crew' | 'tool' | 'flow' | 'router';
  // Agent step
  agent_id?: string;
  task_description?: string;
  // Crew step
  crew_id?: string;
  // Tool step
  tool_id?: string;
  // Flow step (hierarchical)
  flow_id?: string;
  // Router step (conditional)
  condition?: string;
  router_paths?: Array<{ condition: string; next_step_id?: string }>;
  // Common
  config?: Record<string, any>;
}

interface FlowFormData {
  name: string;
  description: string;
  steps: FlowStep[];
  variables?: Record<string, any>;
}

interface FlowFormBuilderProps {
  initialData?: Partial<FlowFormData>;
  onSubmit: (data: FlowFormData) => Promise<void>;
  onCancel?: () => void;
}

export default function FlowFormBuilder({ initialData, onSubmit, onCancel }: FlowFormBuilderProps) {
  const [formData, setFormData] = useState<FlowFormData>({
    name: initialData?.name || '',
    description: initialData?.description || '',
    steps: initialData?.steps || [],
    variables: initialData?.variables || {},
  });

  const [agents, setAgents] = useState<Agent[]>([]);
  const [crews, setCrews] = useState<Crew[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [flows, setFlows] = useState<FlowReference[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch agents, crews, tools, and flows
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [agentsRes, crewsRes, toolsRes, flowsRes] = await Promise.all([
          apiClient.get('/api/v1/agents'),
          apiClient.get('/api/v1/crews'),
          apiClient.get('/api/v1/tools'),
          apiClient.get('/api/v1/flows'),
        ]);

        if (agentsRes.data) setAgents(agentsRes.data.agents || agentsRes.data || []);
        if (crewsRes.data) setCrews(crewsRes.data.crews || crewsRes.data || []);
        if (toolsRes.data) setTools(toolsRes.data.tools || toolsRes.data || []);
        if (flowsRes.data) setFlows(flowsRes.data.flows || flowsRes.data || []);
      } catch (err) {
        console.error('Failed to fetch data:', err);
        setError('Failed to load agents, crews, tools, and flows');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const addStep = () => {
    const newStep: FlowStep = {
      id: `step-${Date.now()}`,
      name: `Step ${formData.steps.length + 1}`,
      description: '',
      type: 'agent',
    };

    setFormData({
      ...formData,
      steps: [...formData.steps, newStep],
    });
  };

  const removeStep = (stepId: string) => {
    setFormData({
      ...formData,
      steps: formData.steps.filter(s => s.id !== stepId),
    });
  };

  const moveStep = (index: number, direction: 'up' | 'down') => {
    const newSteps = [...formData.steps];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;

    if (targetIndex < 0 || targetIndex >= newSteps.length) return;

    [newSteps[index], newSteps[targetIndex]] = [newSteps[targetIndex], newSteps[index]];

    setFormData({ ...formData, steps: newSteps });
  };

  const updateStep = (stepId: string, updates: Partial<FlowStep>) => {
    setFormData({
      ...formData,
      steps: formData.steps.map(s => s.id === stepId ? { ...s, ...updates } : s),
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      await onSubmit(formData);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save flow';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Flow Metadata */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Flow Information</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Flow Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Customer Support Flow"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Describe what this flow does..."
              rows={3}
            />
          </div>
        </div>
      </div>

      {/* Flow Steps */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Flow Steps (Sequential)</h3>
          <button
            type="button"
            onClick={addStep}
            className="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
          >
            + Add Step
          </button>
        </div>

        {formData.steps.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No steps yet. Click &quot;+ Add Step&quot; to get started.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {formData.steps.map((step, index) => (
              <div key={step.id} className="p-4 border border-gray-200 rounded-md bg-gray-50">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold">
                      {index + 1}
                    </span>
                    <input
                      type="text"
                      value={step.name}
                      onChange={(e) => updateStep(step.id, { name: e.target.value })}
                      className="px-2 py-1 text-sm font-medium border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Step name"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => moveStep(index, 'up')}
                      disabled={index === 0}
                      className="p-1 text-gray-600 hover:text-gray-900 disabled:opacity-30 disabled:cursor-not-allowed"
                      title="Move up"
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      onClick={() => moveStep(index, 'down')}
                      disabled={index === formData.steps.length - 1}
                      className="p-1 text-gray-600 hover:text-gray-900 disabled:opacity-30 disabled:cursor-not-allowed"
                      title="Move down"
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      onClick={() => removeStep(step.id)}
                      className="p-1 text-red-600 hover:text-red-700"
                      title="Remove step"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Step Type</label>
                    <select
                      value={step.type}
                      onChange={(e) => {
                        const newType = e.target.value as FlowStep['type'];
                        updateStep(step.id, {
                          type: newType,
                          agent_id: undefined,
                          crew_id: undefined,
                          tool_id: undefined,
                          flow_id: undefined,
                          condition: undefined,
                        });
                      }}
                      className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="agent">🤖 Agent (single agent with task)</option>
                      <option value="crew">👥 Crew (team of agents)</option>
                      <option value="tool">🔧 Tool (execute tool)</option>
                      <option value="flow">🔄 Sub-Flow (hierarchical)</option>
                      <option value="router">🔀 Router (conditional branch)</option>
                    </select>
                  </div>

                  {/* Agent Step */}
                  {step.type === 'agent' && (
                    <>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Select Agent <span className="text-red-500">*</span>
                        </label>
                        <select
                          value={step.agent_id || ''}
                          onChange={(e) => updateStep(step.id, { agent_id: e.target.value })}
                          className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                          required
                        >
                          <option value="">-- Select Agent --</option>
                          {agents.map(agent => (
                            <option key={agent.id} value={agent.id}>{agent.name} - {agent.role}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Task Description <span className="text-red-500">*</span>
                        </label>
                        <textarea
                          value={step.task_description || ''}
                          onChange={(e) => updateStep(step.id, { task_description: e.target.value })}
                          className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="What task should this agent perform?"
                          rows={2}
                          required
                        />
                      </div>
                    </>
                  )}

                  {/* Crew Step */}
                  {step.type === 'crew' && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Select Crew <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={step.crew_id || ''}
                        onChange={(e) => updateStep(step.id, { crew_id: e.target.value })}
                        className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      >
                        <option value="">-- Select Crew --</option>
                        {crews.map(crew => (
                          <option key={crew.id} value={crew.id}>{crew.name}</option>
                        ))}
                      </select>
                      <p className="mt-1 text-xs text-gray-500">
                        Crew executes with all its configured agents and tasks
                      </p>
                    </div>
                  )}

                  {/* Tool Step */}
                  {step.type === 'tool' && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Select Tool <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={step.tool_id || ''}
                        onChange={(e) => updateStep(step.id, { tool_id: e.target.value })}
                        className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      >
                        <option value="">-- Select Tool --</option>
                        {tools.map(tool => (
                          <option key={tool.id} value={tool.id}>{tool.name}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* Sub-Flow Step (Hierarchical) */}
                  {step.type === 'flow' && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Select Sub-Flow <span className="text-red-500">*</span>
                      </label>
                      <select
                        value={step.flow_id || ''}
                        onChange={(e) => updateStep(step.id, { flow_id: e.target.value })}
                        className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      >
                        <option value="">-- Select Flow --</option>
                        {flows.map(flow => (
                          <option key={flow.id} value={flow.id}>{flow.name}</option>
                        ))}
                      </select>
                      <p className="mt-1 text-xs text-gray-500">
                        Executes another flow as a sub-workflow (hierarchical flows)
                      </p>
                    </div>
                  )}

                  {/* Router Step (Conditional) */}
                  {step.type === 'router' && (
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Condition Logic <span className="text-red-500">*</span>
                      </label>
                      <textarea
                        value={step.condition || ''}
                        onChange={(e) => updateStep(step.id, { condition: e.target.value })}
                        className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder='e.g., result.status == "approved"'
                        rows={2}
                        required
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        Conditional branching based on previous step output
                      </p>
                    </div>
                  )}

                  {/* Description (common to all types) */}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                    <textarea
                      value={step.description}
                      onChange={(e) => updateStep(step.id, { description: e.target.value })}
                      className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="What does this step do?"
                      rows={2}
                    />
                  </div>
                </div>

                {index < formData.steps.length - 1 && (
                  <div className="mt-2 text-center">
                    <div className="inline-block text-gray-400">↓</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3 justify-end">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={saving || formData.steps.length === 0}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save Flow'}
        </button>
      </div>
    </form>
  );
}
