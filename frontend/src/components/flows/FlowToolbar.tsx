'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useFlowStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';
import type { FlowUpdate } from '@/types/api';

interface FlowToolbarProps {
  flowId?: number;
  onSave?: () => void;
  onExecute?: () => void;
}

export default function FlowToolbar({ flowId, onSave, onExecute }: FlowToolbarProps) {
  const router = useRouter();
  const { currentFlow, updateFlow } = useFlowStore();
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(false);

  const handleSave = async () => {
    if (!currentFlow) return;

    setSaving(true);
    try {
      const updateData: FlowUpdate = {
        name: currentFlow.name,
        description: currentFlow.description,
        nodes: currentFlow.nodes,
        edges: currentFlow.edges,
      };

      const response = await apiClient.put(`/api/v1/flows/${currentFlow.id}`, updateData);

      if (response.error) {
        alert(`Save failed: ${response.error}`);
      } else {
        onSave?.();
      }
    } catch (error) {
      console.error('Save error:', error);
      alert('Failed to save flow');
    } finally {
      setSaving(false);
    }
  };

  const handleExecute = async () => {
    if (!currentFlow) return;

    setExecuting(true);
    try {
      const response = await apiClient.post(`/api/v1/flows/${currentFlow.id}/execute`, {
        inputs: {},
      });

      if (response.error) {
        alert(`Execution failed: ${response.error}`);
      } else if (response.data) {
        router.push(`/executions/${response.data.execution_id}`);
        onExecute?.();
      }
    } catch (error) {
      console.error('Execution error:', error);
      alert('Failed to execute flow');
    } finally {
      setExecuting(false);
    }
  };

  const handleValidate = async () => {
    if (!currentFlow) return;

    try {
      const response = await apiClient.post(`/api/v1/flows/${currentFlow.id}/validate`, {
        nodes: currentFlow.nodes,
        edges: currentFlow.edges,
      });

      if (response.error) {
        alert(`Validation failed: ${response.error}`);
      } else if (response.data) {
        if (response.data.valid) {
          alert('Flow is valid!');
        } else {
          alert(`Validation errors:\n${response.data.errors.join('\n')}`);
        }
      }
    } catch (error) {
      console.error('Validation error:', error);
      alert('Failed to validate flow');
    }
  };

  return (
    <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold text-gray-900">
          {currentFlow?.name || 'Untitled Flow'}
        </h2>
        {currentFlow?.status && (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
            {currentFlow.status}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={handleValidate}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Validate
        </button>

        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>

        <button
          onClick={handleExecute}
          disabled={executing}
          className="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {executing ? 'Executing...' : 'Execute'}
        </button>
      </div>
    </div>
  );
}
