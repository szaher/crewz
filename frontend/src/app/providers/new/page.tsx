'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { useLLMProviders, type CreateLLMProviderData, type ProviderType } from '@/lib/hooks/useLLMProviders';

export default function ProviderNewPage() {
  const router = useRouter();
  const { createProvider } = useLLMProviders();

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    provider_type: 'openai' as ProviderType,
    model_name: '',
    api_key: '',
    api_base: '',
    is_active: true,
    is_default: false,
    config: '',
  });

  const [showApiKey, setShowApiKey] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);

    try {
      // Parse config JSON if provided
      let configObj: Record<string, any> | undefined;
      if (formData.config.trim()) {
        try {
          configObj = JSON.parse(formData.config);
        } catch {
          setSaveError('Invalid JSON in config field');
          setSaving(false);
          return;
        }
      }

      // Build create data
      const createData: CreateLLMProviderData = {
        name: formData.name,
        provider_type: formData.provider_type,
        model_name: formData.model_name,
        is_active: formData.is_active,
        is_default: formData.is_default,
      };

      // Only include api_key if user entered one
      if (formData.api_key) {
        createData.api_key = formData.api_key;
      }

      // Only include api_base if provided
      if (formData.api_base) {
        createData.api_base = formData.api_base;
      }

      // Only include config if provided
      if (configObj) {
        createData.config = configObj;
      }

      await createProvider(createData);

      // Navigate back to providers list on success
      router.push('/providers');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create provider';
      setSaveError(message);
      console.error('Failed to create provider:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    router.push('/providers');
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto p-6">
            <Breadcrumbs />

            {/* Header */}
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-gray-900">New Provider</h1>
              <p className="text-sm text-gray-600 mt-1">
                Add a new LLM provider configuration
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="bg-white rounded-lg border border-gray-200 p-6">
              {saveError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
                  {saveError}
                </div>
              )}

              <div className="space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., My OpenAI Provider"
                    required
                  />
                </div>

                {/* Provider Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Provider Type <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.provider_type}
                    onChange={(e) => setFormData({ ...formData, provider_type: e.target.value as ProviderType })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="ollama">Ollama</option>
                    <option value="vllm">vLLM</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>

                {/* Model Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Model Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.model_name}
                    onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., gpt-4, claude-3-opus-20240229"
                    required
                  />
                </div>

                {/* API Key */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    API Key
                  </label>
                  <div className="flex gap-2">
                    <input
                      type={showApiKey ? 'text' : 'password'}
                      value={formData.api_key}
                      onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="sk-..."
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                      {showApiKey ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>

                {/* API Base URL */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    API Base URL (Optional)
                  </label>
                  <input
                    type="text"
                    value={formData.api_base}
                    onChange={(e) => setFormData({ ...formData, api_base: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="https://api.openai.com/v1"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Custom base URL for API requests. Leave empty to use provider default.
                  </p>
                </div>

                {/* Config JSON */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Additional Config (JSON)
                  </label>
                  <textarea
                    value={formData.config}
                    onChange={(e) => setFormData({ ...formData, config: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                    rows={6}
                    placeholder='{"temperature": 0.7, "max_tokens": 1000}'
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Additional configuration as JSON. Must be valid JSON format.
                  </p>
                </div>

                {/* Is Active */}
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="is_active" className="ml-2 block text-sm text-gray-700">
                    Active
                  </label>
                </div>

                {/* Is Default */}
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="is_default"
                    checked={formData.is_default}
                    onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="is_default" className="ml-2 block text-sm text-gray-700">
                    Set as default provider
                  </label>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-6 flex gap-3">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Creating...' : 'Create Provider'}
                </button>
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
