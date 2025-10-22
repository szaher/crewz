/**
 * Modal for collecting prompt variables before execution
 * Dynamically generates form fields based on variable metadata
 */

'use client';

import { useState, useEffect } from 'react';
import type { PromptVariable } from '@/lib/store';

interface PromptVariablesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExecute: (variables: Record<string, any>) => void;
  commandName: string;
  commandSlug: string;
  commandDescription?: string;
  variables: PromptVariable[];
}

export default function PromptVariablesModal({
  isOpen,
  onClose,
  onExecute,
  commandName,
  commandSlug,
  commandDescription,
  variables,
}: PromptVariablesModalProps) {
  const [values, setValues] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Initialize with default values
  useEffect(() => {
    if (isOpen) {
      const defaults: Record<string, any> = {};
      variables.forEach(variable => {
        if (variable.default !== undefined) {
          defaults[variable.name] = variable.default;
        } else if (variable.type === 'boolean') {
          defaults[variable.name] = false;
        } else if (variable.type === 'number') {
          defaults[variable.name] = '';
        } else {
          defaults[variable.name] = '';
        }
      });
      setValues(defaults);
      setErrors({});
    }
  }, [isOpen, variables]);

  const handleChange = (name: string, value: any) => {
    setValues(prev => ({ ...prev, [name]: value }));
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    variables.forEach(variable => {
      const value = values[variable.name];

      // Check required
      if (variable.required !== false) {
        if (value === undefined || value === null || value === '') {
          newErrors[variable.name] = 'This field is required';
          return;
        }
      }

      // Skip validation if empty and not required
      if (!value && variable.required === false) {
        return;
      }

      // Type validation
      if (variable.type === 'number') {
        const num = Number(value);
        if (isNaN(num)) {
          newErrors[variable.name] = 'Must be a valid number';
          return;
        }
      }

      // Regex validation
      if (variable.validation && typeof value === 'string') {
        try {
          const regex = new RegExp(variable.validation);
          if (!regex.test(value)) {
            newErrors[variable.name] = 'Invalid format';
            return;
          }
        } catch (err) {
          console.error('Invalid regex pattern:', variable.validation);
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    // Convert values to appropriate types
    const processedValues: Record<string, any> = {};
    variables.forEach(variable => {
      let value = values[variable.name];

      if (variable.type === 'number' && value !== '') {
        value = Number(value);
      } else if (variable.type === 'boolean') {
        value = Boolean(value);
      } else if (variable.type === 'json' && typeof value === 'string') {
        try {
          value = JSON.parse(value);
        } catch (err) {
          // Keep as string if can't parse
        }
      } else if (variable.type === 'array' && typeof value === 'string') {
        value = value.split(',').map(s => s.trim()).filter(s => s);
      }

      processedValues[variable.name] = value;
    });

    onExecute(processedValues);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Execute Command
              </h2>
              <div className="mt-1 flex items-center gap-2">
                <code className="text-sm font-mono text-blue-600 dark:text-blue-400">
                  /{commandSlug}
                </code>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {commandName}
                </span>
              </div>
              {commandDescription && (
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                  {commandDescription}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-6 py-4">
          <div className="space-y-4">
            {variables.map((variable) => (
              <div key={variable.name}>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {variable.name}
                  {variable.required !== false && (
                    <span className="ml-1 text-red-500">*</span>
                  )}
                  {variable.type && (
                    <span className="ml-2 text-xs text-gray-500">({variable.type})</span>
                  )}
                </label>

                {variable.description && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                    {variable.description}
                  </p>
                )}

                {/* Input based on type */}
                {variable.type === 'boolean' ? (
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={values[variable.name] || false}
                      onChange={(e) => handleChange(variable.name, e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      Enable {variable.name}
                    </span>
                  </label>
                ) : variable.type === 'number' ? (
                  <input
                    type="number"
                    value={values[variable.name] || ''}
                    onChange={(e) => handleChange(variable.name, e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                ) : (
                  <textarea
                    value={values[variable.name] || ''}
                    onChange={(e) => handleChange(variable.name, e.target.value)}
                    rows={variable.type === 'json' || variable.type === 'array' ? 4 : 3}
                    placeholder={
                      variable.type === 'array'
                        ? 'Comma-separated values'
                        : variable.type === 'json'
                        ? 'JSON object'
                        : undefined
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  />
                )}

                {errors[variable.name] && (
                  <p className="mt-1 text-xs text-red-500">
                    {errors[variable.name]}
                  </p>
                )}
              </div>
            ))}
          </div>
        </form>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-800 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            Execute Command
          </button>
        </div>
      </div>
    </div>
  );
}
