'use client';

import { useState, useEffect } from 'react';
import { Task, TaskCreate, TaskUpdate, TaskOutputFormat } from '@/types/task';
import { useAgents } from '@/lib/hooks/useAgents';

interface TaskFormProps {
  task?: Task;
  crewId?: number;
  onSave: (task: TaskCreate | TaskUpdate) => Promise<void>;
  onCancel: () => void;
}

export default function TaskForm({ task, crewId, onSave, onCancel }: TaskFormProps) {
  const { agents, fetchAgents } = useAgents();
  const [formData, setFormData] = useState<TaskCreate | TaskUpdate>({
    name: task?.name || '',
    description: task?.description || '',
    expected_output: task?.expected_output || '',
    agent_id: task?.agent_id,
    crew_id: task?.crew_id || crewId,
    order: task?.order || 0,
    async_execution: task?.async_execution || false,
    // Backend expects lowercase values: 'text' | 'json' | 'pydantic'
    output_format: (task?.output_format as TaskOutputFormat) || 'text',
    output_file: task?.output_file || '',
    context: task?.context || '',
  });

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      await onSave(formData);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Task Name */}
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700">
          Task Name *
        </label>
        <input
          type="text"
          id="name"
          value={formData.name}
          onChange={(e) => handleChange('name', e.target.value)}
          required
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="e.g., Research market trends"
        />
      </div>

      {/* Description */}
      <div>
        <label htmlFor="description" className="block text-sm font-medium text-gray-700">
          Description *
        </label>
        <textarea
          id="description"
          value={formData.description}
          onChange={(e) => handleChange('description', e.target.value)}
          required
          rows={4}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="Detailed description of what the task should accomplish..."
        />
      </div>

      {/* Expected Output */}
      <div>
        <label htmlFor="expected_output" className="block text-sm font-medium text-gray-700">
          Expected Output *
        </label>
        <textarea
          id="expected_output"
          value={formData.expected_output}
          onChange={(e) => handleChange('expected_output', e.target.value)}
          required
          rows={3}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="Describe what output you expect from this task..."
        />
      </div>

      {/* Agent Assignment */}
      <div>
        <label htmlFor="agent_id" className="block text-sm font-medium text-gray-700">
          Assign to Agent
        </label>
        <select
          id="agent_id"
          value={formData.agent_id || ''}
          onChange={(e) => handleChange('agent_id', e.target.value ? Number(e.target.value) : undefined)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
        >
          <option value="">No specific agent (auto-assign)</option>
          {agents.map(agent => (
            <option key={agent.id} value={agent.id}>
              {agent.name} - {agent.role}
            </option>
          ))}
        </select>
      </div>

      {/* Order */}
      <div>
        <label htmlFor="order" className="block text-sm font-medium text-gray-700">
          Task Order
        </label>
        <input
          type="number"
          id="order"
          value={formData.order}
          onChange={(e) => handleChange('order', Number(e.target.value))}
          min="0"
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">Lower numbers execute first</p>
      </div>

      {/* Output Format */}
      <div>
        <label htmlFor="output_format" className="block text-sm font-medium text-gray-700">
          Output Format
        </label>
        <select
          id="output_format"
          value={formData.output_format}
          onChange={(e) => handleChange('output_format', e.target.value as TaskOutputFormat)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
        >
          <option value="text">Text</option>
          <option value="json">JSON</option>
          <option value="pydantic">Pydantic</option>
        </select>
      </div>

      {/* Async Execution */}
      <div className="flex items-center">
        <input
          type="checkbox"
          id="async_execution"
          checked={formData.async_execution}
          onChange={(e) => handleChange('async_execution', e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <label htmlFor="async_execution" className="ml-2 block text-sm text-gray-700">
          Execute Asynchronously
        </label>
      </div>

      {/* Context */}
      <div>
        <label htmlFor="context" className="block text-sm font-medium text-gray-700">
          Context (Optional)
        </label>
        <textarea
          id="context"
          value={formData.context}
          onChange={(e) => handleChange('context', e.target.value)}
          rows={3}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="Additional context or information for this task..."
        />
      </div>

      {/* Output File */}
      <div>
        <label htmlFor="output_file" className="block text-sm font-medium text-gray-700">
          Output File (Optional)
        </label>
        <input
          type="text"
          id="output_file"
          value={formData.output_file}
          onChange={(e) => handleChange('output_file', e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="e.g., output/report.txt"
        />
      </div>

      {/* Form Actions */}
      <div className="flex gap-3 pt-4">
        <button
          type="submit"
          disabled={saving}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : task ? 'Update Task' : 'Create Task'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
