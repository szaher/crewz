'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useFlows, CreateFlowData } from '@/lib/hooks/useFlows';

interface CreateFlowModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CreateFlowModal({ isOpen, onClose }: CreateFlowModalProps) {
  const router = useRouter();
  const { createFlow } = useFlows();

  const [formData, setFormData] = useState<CreateFlowData>({
    name: '',
    description: '',
    variables: {},
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      setError('Flow name is required');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const newFlow = await createFlow({
        name: formData.name.trim(),
        description: formData.description?.trim(),
        variables: formData.variables,
      });

      // Success: redirect to flow editor
      router.push(`/flows/${newFlow.id}/edit`);
      onClose();

      // Reset form
      setFormData({ name: '', description: '', variables: {} });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create flow';
      setError(message);
      console.error('Flow creation error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setFormData({ name: '', description: '', variables: {} });
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleCancel}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
          {/* Header */}
          <div className="mb-4">
            <h2 className="text-xl font-bold text-gray-900">Create New Flow</h2>
            <p className="mt-1 text-sm text-gray-500">
              Create a workflow to orchestrate your AI agents
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit}>
            {/* Name Field */}
            <div className="mb-4">
              <label htmlFor="flow-name" className="block text-sm font-medium text-gray-700 mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                id="flow-name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., Customer Onboarding Flow"
                autoFocus
                disabled={isSubmitting}
              />
            </div>

            {/* Description Field */}
            <div className="mb-4">
              <label htmlFor="flow-description" className="block text-sm font-medium text-gray-700 mb-1">
                Description (optional)
              </label>
              <textarea
                id="flow-description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Describe what this flow does..."
                rows={3}
                disabled={isSubmitting}
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={handleCancel}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !formData.name.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSubmitting && (
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                )}
                {isSubmitting ? 'Creating...' : 'Create Flow'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
