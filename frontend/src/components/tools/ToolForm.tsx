'use client';

import { useState } from 'react';
import { useToolStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';
import type { ToolCreate } from '@/types/api';

interface ToolFormProps {
  toolId?: number;
  onSave?: (toolId: number) => void;
  onCancel?: () => void;
}

export default function ToolForm({ toolId, onSave, onCancel }: ToolFormProps) {
  const { tools, addTool, updateTool } = useToolStore();
  const existingTool = toolId ? tools.find((t) => t.id === toolId) : null;

  const [formData, setFormData] = useState<ToolCreate>({
    name: existingTool?.name || '',
    description: existingTool?.description || '',
    tool_type: existingTool?.tool_type || 'function',
    input_schema: existingTool?.input_schema || {},
    output_schema: existingTool?.output_schema || {},
    docker_image: existingTool?.docker_image,
    docker_command: existingTool?.docker_command,
    function_code: existingTool?.function_code,
    api_endpoint: existingTool?.api_endpoint,
    api_method: existingTool?.api_method,
    api_headers: existingTool?.api_headers,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (toolId) {
        const response = await apiClient.put(`/api/v1/tools/${toolId}`, formData);
        if (response.error) {
          setError(response.error);
        } else if (response.data) {
          updateTool(toolId, response.data.tool);
          onSave?.(toolId);
        }
      } else {
        const response = await apiClient.post('/api/v1/tools', formData);
        if (response.error) {
          setError(response.error);
        } else if (response.data) {
          addTool(response.data.tool);
          onSave?.(response.data.tool.id);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save tool');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Info */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Tool Name</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
              placeholder="e.g., Web Search"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <textarea
              required
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
              placeholder="What does this tool do?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Tool Type</label>
            <select
              value={formData.tool_type}
              onChange={(e) => setFormData({ ...formData, tool_type: e.target.value as any })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            >
              <option value="function">Function (Python code)</option>
              <option value="api">API Endpoint</option>
              <option value="docker">Docker Container</option>
            </select>
          </div>
        </div>
      </div>

      {/* Type-Specific Configuration */}
      {formData.tool_type === 'docker' && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Docker Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Docker Image</label>
              <input
                type="text"
                value={formData.docker_image || ''}
                onChange={(e) => setFormData({ ...formData, docker_image: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm"
                placeholder="python:3.11-slim"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Command</label>
              <input
                type="text"
                value={formData.docker_command || ''}
                onChange={(e) => setFormData({ ...formData, docker_command: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm"
                placeholder="/app/tool.py"
              />
            </div>
          </div>
        </div>
      )}

      {formData.tool_type === 'api' && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">API Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">API Endpoint</label>
              <input
                type="url"
                value={formData.api_endpoint || ''}
                onChange={(e) => setFormData({ ...formData, api_endpoint: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm"
                placeholder="https://api.example.com/search"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">HTTP Method</label>
              <select
                value={formData.api_method || 'GET'}
                onChange={(e) => setFormData({ ...formData, api_method: e.target.value as any })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {formData.tool_type === 'function' && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Function Code</h3>
          <textarea
            rows={12}
            value={formData.function_code || ''}
            onChange={(e) => setFormData({ ...formData, function_code: e.target.value })}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm"
            placeholder="def execute(input_data):\n    # Your code here\n    return output"
          />
        </div>
      )}

      {/* Schemas */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Input/Output Schemas</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Input Schema (JSON)</label>
            <textarea
              rows={8}
              value={JSON.stringify(formData.input_schema, null, 2)}
              onChange={(e) => {
                try {
                  setFormData({ ...formData, input_schema: JSON.parse(e.target.value) });
                } catch {}
              }}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Output Schema (JSON)</label>
            <textarea
              rows={8}
              value={JSON.stringify(formData.output_schema, null, 2)}
              onChange={(e) => {
                try {
                  setFormData({ ...formData, output_schema: JSON.parse(e.target.value) });
                } catch {}
              }}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-xs"
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

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
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Saving...' : toolId ? 'Update Tool' : 'Create Tool'}
        </button>
      </div>
    </form>
  );
}
