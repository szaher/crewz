'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { CreateFlowData } from '@/lib/hooks/useFlows';

// Zod validation schema
const flowFormSchema = z.object({
  name: z.string().min(1, 'Flow name is required').max(100, 'Flow name must be less than 100 characters'),
  description: z.string().max(500, 'Description must be less than 500 characters').optional(),
  variables: z.record(z.string(), z.any()).optional(),
});

export type FlowFormData = z.infer<typeof flowFormSchema>;

interface FlowFormProps {
  initialData?: Partial<FlowFormData>;
  onSubmit: (data: FlowFormData) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  isSubmitting?: boolean;
}

export default function FlowForm({
  initialData,
  onSubmit,
  onCancel,
  submitLabel = 'Submit',
  isSubmitting = false,
}: FlowFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm<FlowFormData>({
    resolver: zodResolver(flowFormSchema),
    defaultValues: {
      name: initialData?.name || '',
      description: initialData?.description || '',
      variables: initialData?.variables || {},
    },
  });

  const handleFormSubmit = async (data: FlowFormData) => {
    try {
      await onSubmit(data);
    } catch (error) {
      // Error handling is managed by parent component
      console.error('Form submission error:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      {/* Name Field */}
      <div>
        <label htmlFor="flow-name" className="block text-sm font-medium text-gray-700 mb-1">
          Name <span className="text-red-500">*</span>
        </label>
        <input
          id="flow-name"
          type="text"
          {...register('name')}
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.name ? 'border-red-300 bg-red-50' : 'border-gray-300'
          }`}
          placeholder="e.g., Customer Onboarding Flow"
          autoFocus
          disabled={isSubmitting}
          aria-describedby={errors.name ? 'name-error' : undefined}
        />
        {errors.name && (
          <p id="name-error" className="mt-1 text-sm text-red-600" role="alert">
            {errors.name.message}
          </p>
        )}
      </div>

      {/* Description Field */}
      <div>
        <label htmlFor="flow-description" className="block text-sm font-medium text-gray-700 mb-1">
          Description (optional)
        </label>
        <textarea
          id="flow-description"
          {...register('description')}
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.description ? 'border-red-300 bg-red-50' : 'border-gray-300'
          }`}
          placeholder="Describe what this flow does..."
          rows={3}
          disabled={isSubmitting}
          aria-describedby={errors.description ? 'description-error' : undefined}
        />
        {errors.description && (
          <p id="description-error" className="mt-1 text-sm text-red-600" role="alert">
            {errors.description.message}
          </p>
        )}
      </div>

      {/* Variables Field (JSON Editor) */}
      <div>
        <label htmlFor="flow-variables" className="block text-sm font-medium text-gray-700 mb-1">
          Initial Variables (optional)
        </label>
        <details className="group">
          <summary className="cursor-pointer text-sm text-blue-600 hover:text-blue-700 mb-2">
            Advanced: Set initial variables
          </summary>
          <textarea
            id="flow-variables"
            {...register('variables', {
              setValueAs: (value) => {
                if (!value || value.trim() === '') return {};
                try {
                  return JSON.parse(value);
                } catch {
                  return value;
                }
              },
            })}
            className={`w-full px-3 py-2 border rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.variables ? 'border-red-300 bg-red-50' : 'border-gray-300'
            }`}
            placeholder='{"key": "value"}'
            rows={4}
            disabled={isSubmitting}
            aria-describedby={errors.variables ? 'variables-error' : undefined}
          />
        </details>
        {errors.variables && (
          <p id="variables-error" className="mt-1 text-sm text-red-600" role="alert">
            {errors.variables.message}
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3 justify-end pt-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isSubmitting && (
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          )}
          {isSubmitting ? 'Submitting...' : submitLabel}
        </button>
      </div>
    </form>
  );
}
