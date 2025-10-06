'use client';

import { useState, useEffect } from 'react';
import { useFlows } from '@/lib/hooks/useFlows';

interface FlowPropertiesPanelProps {
  flowId: number;
  initialData: {
    name: string;
    description?: string;
    variables?: Record<string, any>;
    timeout?: number;
    retry_policy?: {
      max_retries: number;
      retry_delay: number;
    };
    created_at?: string;
    updated_at?: string;
    version?: string;
  };
  isOpen: boolean;
  onClose: () => void;
}

export default function FlowPropertiesPanel({
  flowId,
  initialData,
  isOpen,
  onClose,
}: FlowPropertiesPanelProps) {
  const { updateFlow } = useFlows();

  const [formData, setFormData] = useState({
    name: initialData.name,
    description: initialData.description || '',
    variables: JSON.stringify(initialData.variables || {}, null, 2),
    timeout: initialData.timeout || 3600,
    maxRetries: initialData.retry_policy?.max_retries || 0,
    retryDelay: initialData.retry_policy?.retry_delay || 60,
  });

  const [activeTab, setActiveTab] = useState<'general' | 'variables' | 'settings' | 'metadata'>('general');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [variablesError, setVariablesError] = useState<string | null>(null);

  // Update hasChanges when formData changes
  useEffect(() => {
    const changed =
      formData.name !== initialData.name ||
      formData.description !== (initialData.description || '') ||
      formData.variables !== JSON.stringify(initialData.variables || {}, null, 2) ||
      formData.timeout !== (initialData.timeout || 3600) ||
      formData.maxRetries !== (initialData.retry_policy?.max_retries || 0) ||
      formData.retryDelay !== (initialData.retry_policy?.retry_delay || 60);

    setHasChanges(changed);
  }, [formData, initialData]);

  // Validate JSON variables
  const validateVariables = (jsonString: string): boolean => {
    try {
      JSON.parse(jsonString);
      setVariablesError(null);
      return true;
    } catch (err) {
      setVariablesError(err instanceof Error ? err.message : 'Invalid JSON');
      return false;
    }
  };

  const handleSave = async () => {
    setError(null);

    // Validate variables JSON
    if (!validateVariables(formData.variables)) {
      setActiveTab('variables');
      return;
    }

    setIsSaving(true);

    try {
      const parsedVariables = JSON.parse(formData.variables);

      await updateFlow(flowId, {
        name: formData.name,
        description: formData.description,
        variables: parsedVariables,
        // Note: timeout and retry_policy might not be supported by the API yet
        // Uncomment when backend supports them:
        // timeout: formData.timeout,
        // retry_policy: {
        //   max_retries: formData.maxRetries,
        //   retry_delay: formData.retryDelay,
        // },
      });

      setHasChanges(false);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update flow';
      setError(message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    if (hasChanges) {
      if (confirm('You have unsaved changes. Are you sure you want to close?')) {
        onClose();
      }
    } else {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
        onClick={handleCancel}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 bottom-0 w-96 bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Flow Properties</h2>
          <button
            onClick={handleCancel}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
            title="Close"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          {[
            { id: 'general', label: 'General' },
            { id: 'variables', label: 'Variables' },
            { id: 'settings', label: 'Settings' },
            { id: 'metadata', label: 'Metadata' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* General Tab */}
          {activeTab === 'general' && (
            <>
              <div>
                <label htmlFor="flow-name" className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  id="flow-name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Flow name"
                />
              </div>

              <div>
                <label htmlFor="flow-description" className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  id="flow-description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Describe this flow..."
                  rows={4}
                />
              </div>
            </>
          )}

          {/* Variables Tab */}
          {activeTab === 'variables' && (
            <div>
              <label htmlFor="flow-variables" className="block text-sm font-medium text-gray-700 mb-1">
                Variables (JSON)
              </label>
              <textarea
                id="flow-variables"
                value={formData.variables}
                onChange={(e) => {
                  setFormData({ ...formData, variables: e.target.value });
                  validateVariables(e.target.value);
                }}
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm ${
                  variablesError ? 'border-red-500' : 'border-gray-300'
                }`}
                placeholder='{"key": "value"}'
                rows={15}
              />
              {variablesError && (
                <p className="mt-2 text-sm text-red-600">{variablesError}</p>
              )}
              <p className="mt-2 text-xs text-gray-500">
                Define flow variables as JSON key-value pairs
              </p>
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <>
              <div>
                <label htmlFor="flow-timeout" className="block text-sm font-medium text-gray-700 mb-1">
                  Timeout (seconds)
                </label>
                <input
                  id="flow-timeout"
                  type="number"
                  value={formData.timeout}
                  onChange={(e) => setFormData({ ...formData, timeout: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="0"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Maximum execution time (0 = no limit)
                </p>
              </div>

              <div>
                <label htmlFor="flow-max-retries" className="block text-sm font-medium text-gray-700 mb-1">
                  Max Retries
                </label>
                <input
                  id="flow-max-retries"
                  type="number"
                  value={formData.maxRetries}
                  onChange={(e) => setFormData({ ...formData, maxRetries: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="0"
                  max="10"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Number of retry attempts on failure
                </p>
              </div>

              <div>
                <label htmlFor="flow-retry-delay" className="block text-sm font-medium text-gray-700 mb-1">
                  Retry Delay (seconds)
                </label>
                <input
                  id="flow-retry-delay"
                  type="number"
                  value={formData.retryDelay}
                  onChange={(e) => setFormData({ ...formData, retryDelay: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="0"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Delay between retry attempts
                </p>
              </div>
            </>
          )}

          {/* Metadata Tab */}
          {activeTab === 'metadata' && (
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Flow ID</label>
                <p className="text-sm text-gray-900 font-mono">{flowId}</p>
              </div>

              {initialData.version && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
                  <p className="text-sm text-gray-900">{initialData.version}</p>
                </div>
              )}

              {initialData.created_at && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Created</label>
                  <p className="text-sm text-gray-900">
                    {new Date(initialData.created_at).toLocaleString()}
                  </p>
                </div>
              )}

              {initialData.updated_at && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Last Updated</label>
                  <p className="text-sm text-gray-900">
                    {new Date(initialData.updated_at).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          {error && (
            <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleCancel}
              disabled={isSaving}
              className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving || !hasChanges}
              className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSaving && (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              )}
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes slide-in-right {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }

        .animate-slide-in-right {
          animation: slide-in-right 0.3s ease-out;
        }
      `}</style>
    </>
  );
}
