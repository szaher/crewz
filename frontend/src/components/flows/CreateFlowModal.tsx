'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useFlows } from '@/lib/hooks/useFlows';
import FlowForm, { FlowFormData } from './FlowForm';

interface CreateFlowModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CreateFlowModal({ isOpen, onClose }: CreateFlowModalProps) {
  const router = useRouter();
  const { createFlow } = useFlows();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: FlowFormData) => {
    setIsSubmitting(true);
    setError(null);

    try {
      const newFlow = await createFlow({
        name: data.name.trim(),
        description: data.description?.trim(),
        variables: data.variables || {},
      });

      // Success: redirect to flow editor
      router.push(`/flows/${newFlow.id}/edit`);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create flow';
      setError(message);
      console.error('Flow creation error:', err);
      throw err; // Re-throw to let FlowForm handle it
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
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

          {/* Error Message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Reusable Form Component with Validation */}
          <FlowForm
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            submitLabel="Create Flow"
            isSubmitting={isSubmitting}
          />
        </div>
      </div>
    </div>
  );
}
