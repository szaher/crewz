'use client';

import { useState, useEffect, useMemo } from 'react';
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

  // Extract variables from text using {variable_name} pattern
  const extractVariables = (text: string): string[] => {
    const regex = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
    const matches = text.matchAll(regex);
    const variables = new Set<string>();
    for (const match of matches) {
      variables.add(match[1]);
    }
    return Array.from(variables);
  };

  // Detect all variables from description, expected_output, and context
  const detectedVariables = useMemo(() => {
    const allText = `${formData.description} ${formData.expected_output} ${formData.context || ''}`;
    return extractVariables(allText);
  }, [formData.description, formData.expected_output, formData.context]);

  // Highlight variables in text
  const highlightVariables = (text: string): JSX.Element[] => {
    const regex = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
    const parts: JSX.Element[] = [];
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      // Add text before the variable
      if (match.index > lastIndex) {
        parts.push(
          <span key={`text-${lastIndex}`}>
            {text.substring(lastIndex, match.index)}
          </span>
        );
      }

      // Add highlighted variable
      parts.push(
        <span
          key={`var-${match.index}`}
          className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 px-1 rounded font-medium"
        >
          {match[0]}
        </span>
      );

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(
        <span key={`text-${lastIndex}`}>
          {text.substring(lastIndex)}
        </span>
      );
    }

    return parts.length > 0 ? parts : [<span key="empty">{text}</span>];
  };

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
      {/* Variables Detection Panel */}
      {detectedVariables.length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <svg className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100">
                Variables Detected
              </h3>
              <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                These variables will be required when executing this task
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {detectedVariables.map((variable) => (
                  <span
                    key={variable}
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                  >
                    <code>{`{${variable}}`}</code>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Task Name */}
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Task Name *
        </label>
        <input
          type="text"
          id="name"
          value={formData.name}
          onChange={(e) => handleChange('name', e.target.value)}
          required
          className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-blue-500"
          placeholder="e.g., Research market trends"
        />
      </div>

      {/* Description */}
      <div>
        <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Description *
          <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">
            Use {`{variable_name}`} to define variables
          </span>
        </label>
        <textarea
          id="description"
          value={formData.description}
          onChange={(e) => handleChange('description', e.target.value)}
          required
          rows={4}
          className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-blue-500 font-mono text-sm"
          placeholder="Research {topic} and analyze {aspect}..."
        />
        {formData.description && (
          <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded-md border border-gray-200 dark:border-gray-700">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Preview:</p>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              {highlightVariables(formData.description)}
            </p>
          </div>
        )}
      </div>

      {/* Expected Output */}
      <div>
        <label htmlFor="expected_output" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Expected Output *
          <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">
            Define expected output format
          </span>
        </label>
        <textarea
          id="expected_output"
          value={formData.expected_output}
          onChange={(e) => handleChange('expected_output', e.target.value)}
          required
          rows={3}
          className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-blue-500 font-mono text-sm"
          placeholder="A detailed report about {topic}..."
        />
        {formData.expected_output && (
          <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded-md border border-gray-200 dark:border-gray-700">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Preview:</p>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              {highlightVariables(formData.expected_output)}
            </p>
          </div>
        )}
      </div>

      {/* Agent Assignment */}
      <div>
        <label htmlFor="agent_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Assign to Agent
        </label>
        <select
          id="agent_id"
          value={formData.agent_id || ''}
          onChange={(e) => handleChange('agent_id', e.target.value ? Number(e.target.value) : undefined)}
          className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-blue-500"
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
        <label htmlFor="order" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Task Order
        </label>
        <input
          type="number"
          id="order"
          value={formData.order}
          onChange={(e) => handleChange('order', Number(e.target.value))}
          min="0"
          className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Lower numbers execute first</p>
      </div>

      {/* Output Format */}
      <div>
        <label htmlFor="output_format" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Output Format
        </label>
        <select
          id="output_format"
          value={formData.output_format}
          onChange={(e) => handleChange('output_format', e.target.value as TaskOutputFormat)}
          className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-blue-500"
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
          className="h-4 w-4 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
        />
        <label htmlFor="async_execution" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
          Execute Asynchronously
        </label>
      </div>

      {/* Context */}
      <div>
        <label htmlFor="context" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Context (Optional)
          <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">
            Can also use variables here
          </span>
        </label>
        <textarea
          id="context"
          value={formData.context}
          onChange={(e) => handleChange('context', e.target.value)}
          rows={3}
          className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-blue-500 font-mono text-sm"
          placeholder="Additional context for {topic}..."
        />
        {formData.context && (
          <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded-md border border-gray-200 dark:border-gray-700">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Preview:</p>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              {highlightVariables(formData.context)}
            </p>
          </div>
        )}
      </div>

      {/* Output File */}
      <div>
        <label htmlFor="output_file" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Output File (Optional)
        </label>
        <input
          type="text"
          id="output_file"
          value={formData.output_file}
          onChange={(e) => handleChange('output_file', e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-blue-500"
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
