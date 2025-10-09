'use client';

import { useState, useEffect } from 'react';

interface ExecuteFlowModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExecute: (inputs: Record<string, any>) => void;
  inputVariables: Array<{ name: string; type: string; required?: boolean }>;
  flowName?: string;
}

export default function ExecuteFlowModal({
  isOpen,
  onClose,
  onExecute,
  inputVariables,
  flowName,
}: ExecuteFlowModalProps) {
  const [inputs, setInputs] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    // Initialize inputs with empty values
    const initialInputs: Record<string, any> = {};
    inputVariables.forEach((input) => {
      initialInputs[input.name] = '';
    });
    setInputs(initialInputs);
    setErrors({});
  }, [inputVariables, isOpen]);

  const handleInputChange = (name: string, value: string, type: string) => {
    let parsedValue: any = value;

    // Parse based on type
    try {
      if (type === 'number') {
        parsedValue = value ? parseFloat(value) : '';
      } else if (type === 'boolean') {
        parsedValue = value === 'true';
      } else if (type === 'object' || type === 'array') {
        // Try to parse JSON
        if (value.trim()) {
          parsedValue = JSON.parse(value);
        } else {
          parsedValue = type === 'array' ? [] : {};
        }
      }

      setInputs((prev) => ({ ...prev, [name]: parsedValue }));
      // Clear error for this field
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    } catch (error) {
      // JSON parse error
      setErrors((prev) => ({ ...prev, [name]: 'Invalid JSON format' }));
    }
  };

  const validateInputs = () => {
    const newErrors: Record<string, string> = {};

    inputVariables.forEach((input) => {
      if (input.required) {
        const value = inputs[input.name];
        if (value === '' || value === null || value === undefined) {
          newErrors[input.name] = 'This field is required';
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateInputs()) {
      return;
    }

    // Clean up empty values
    const cleanedInputs: Record<string, any> = {};
    Object.entries(inputs).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        cleanedInputs[key] = value;
      }
    });

    onExecute(cleanedInputs);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
          {/* Header */}
          <div className="mb-4">
            <h2 className="text-xl font-bold text-gray-900">
              Execute Flow{flowName ? `: ${flowName}` : ''}
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              {inputVariables.length > 0
                ? 'Provide input values for the flow execution'
                : 'This flow has no input variables. Click Execute to start.'}
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Input Fields */}
            {inputVariables.length > 0 && (
              <div className="space-y-4 mb-6 max-h-96 overflow-y-auto">
                {inputVariables.map((input) => (
                  <div key={input.name}>
                    <label
                      htmlFor={`input-${input.name}`}
                      className="block text-sm font-medium text-gray-700 mb-1"
                    >
                      {input.name}
                      {input.required && <span className="text-red-500 ml-1">*</span>}
                      {input.type && (
                        <span className="ml-2 text-xs text-gray-500">({input.type})</span>
                      )}
                    </label>

                    {input.type === 'boolean' ? (
                      <select
                        id={`input-${input.name}`}
                        value={inputs[input.name]?.toString() || ''}
                        onChange={(e) =>
                          handleInputChange(input.name, e.target.value, input.type)
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="">Select...</option>
                        <option value="true">True</option>
                        <option value="false">False</option>
                      </select>
                    ) : input.type === 'object' || input.type === 'array' ? (
                      <textarea
                        id={`input-${input.name}`}
                        value={
                          typeof inputs[input.name] === 'object'
                            ? JSON.stringify(inputs[input.name], null, 2)
                            : inputs[input.name] || ''
                        }
                        onChange={(e) =>
                          handleInputChange(input.name, e.target.value, input.type)
                        }
                        rows={4}
                        placeholder={
                          input.type === 'array' ? '["item1", "item2"]' : '{"key": "value"}'
                        }
                        className={`w-full px-3 py-2 border rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          errors[input.name] ? 'border-red-300 bg-red-50' : 'border-gray-300'
                        }`}
                      />
                    ) : (
                      <input
                        id={`input-${input.name}`}
                        type={input.type === 'number' ? 'number' : 'text'}
                        value={inputs[input.name] || ''}
                        onChange={(e) =>
                          handleInputChange(input.name, e.target.value, input.type)
                        }
                        placeholder={`Enter ${input.name}...`}
                        className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          errors[input.name] ? 'border-red-300 bg-red-50' : 'border-gray-300'
                        }`}
                      />
                    )}

                    {errors[input.name] && (
                      <p className="mt-1 text-sm text-red-600">{errors[input.name]}</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 justify-end pt-4 border-t border-gray-200">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
              >
                Execute Flow
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
