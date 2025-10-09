'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useFlowStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';
import type { FlowUpdate } from '@/types/api';
import FlowNameEditor from './FlowNameEditor';
import Breadcrumbs from '../navigation/Breadcrumbs';
import ExecuteFlowModal from './ExecuteFlowModal';

interface FlowToolbarProps {
  flowId?: number;
  onSave?: () => void;
  onExecute?: () => void;
  onDiscard?: () => void;
  onOpenProperties?: () => void;
}

export default function FlowToolbar({ flowId, onSave, onExecute, onDiscard, onOpenProperties }: FlowToolbarProps) {
  const router = useRouter();
  const { currentFlow, updateFlow } = useFlowStore();
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [showExecuteModal, setShowExecuteModal] = useState(false);

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
        // Navigate back to flows list after successful save
        router.push('/flows');
      }
    } catch (error) {
      console.error('Save error:', error);
      alert('Failed to save flow');
    } finally {
      setSaving(false);
    }
  };

  const getInputVariables = () => {
    if (!currentFlow) return [];

    // Find input nodes in the flow
    const inputNodes = currentFlow.nodes.filter((node) => node.type === 'input');

    // Collect all input variables from input nodes
    const allInputs: Array<{ name: string; type: string; required?: boolean }> = [];
    inputNodes.forEach((node) => {
      if (node.data.inputs && Array.isArray(node.data.inputs)) {
        allInputs.push(...node.data.inputs);
      }
    });

    return allInputs;
  };

  const handleExecuteWithInputs = async (inputs: Record<string, any>) => {
    if (!currentFlow) return;

    setExecuting(true);
    setShowExecuteModal(false);

    try {
      const response = await apiClient.post(`/api/v1/flows/${currentFlow.id}/execute`, {
        inputs,
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

  const handleNameUpdate = (newName: string) => {
    if (currentFlow) {
      updateFlow(currentFlow.id, { name: newName });
    }
  };

  return (
    <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-4 py-3">
      <Breadcrumbs />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
        {currentFlow && flowId ? (
          <FlowNameEditor
            flowId={flowId}
            initialName={currentFlow.name}
            onUpdate={handleNameUpdate}
          />
        ) : (
          <h2 className="text-lg font-semibold text-gray-900">
            {currentFlow?.name || 'Untitled Flow'}
          </h2>
        )}
        {currentFlow?.status && (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
            {currentFlow.status}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onOpenProperties}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center gap-2"
          title="Flow Properties"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Properties
        </button>

        <button
          onClick={() => {
            if (confirm('Are you sure you want to delete this workflow? This action cannot be undone.')) {
              onDiscard?.();
            }
          }}
          className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
        >
          Delete
        </button>

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
          onClick={() => setShowExecuteModal(true)}
          disabled={executing}
          className="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {executing ? 'Executing...' : 'Execute'}
        </button>
        </div>
      </div>

      {/* Execute Flow Modal */}
      <ExecuteFlowModal
        isOpen={showExecuteModal}
        onClose={() => setShowExecuteModal(false)}
        onExecute={handleExecuteWithInputs}
        inputVariables={getInputVariables()}
        flowName={currentFlow?.name}
      />
    </div>
  );
}
