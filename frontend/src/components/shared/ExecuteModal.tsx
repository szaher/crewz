'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api-client';

interface ExecutionInput {
  label: string;
  key: string;
  type: 'text' | 'textarea';
  placeholder?: string;
  required?: boolean;
}

interface ExecuteModalProps {
  title: string;
  description: string;
  entityType: 'agent' | 'crew' | 'tool';
  entityId: number;
  entityName: string;
  inputs: ExecutionInput[];
  isOpen: boolean;
  onClose: () => void;
}

interface ExecutionResult {
  status: 'success' | 'failed';
  output?: string;
  error?: string;
  execution_time_ms: number;
}

export default function ExecuteModal({
  title,
  description,
  entityType,
  entityId,
  entityName,
  inputs,
  isOpen,
  onClose
}: ExecuteModalProps) {
  const [inputData, setInputData] = useState<Record<string, string | string[]>>({});
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<ExecutionResult | null>(null);

  if (!isOpen) return null;

  const handleInputChange = (key: string, value: string) => {
    setInputData({ ...inputData, [key]: value });
  };

  const handleExecute = async () => {
    setExecuting(true);
    setResult(null);

    try {
      // Process input data - convert tasks string to array for crews
      const processedData = { ...inputData };
      if (entityType === 'crew' && processedData.tasks && typeof processedData.tasks === 'string') {
        // Split by newlines or commas, trim and filter empty
        const tasksArray = (processedData.tasks as string)
          .split(/[\n,]/)
          .map(t => t.trim())
          .filter(t => t.length > 0);
        processedData.tasks = tasksArray;
      }

      const endpoint = `/api/v1/${entityType}s/${entityId}/execute`;
      const response = await apiClient.post(endpoint, processedData);

      if (response.data) {
        setResult(response.data as ExecutionResult);
      } else if (response.error) {
        setResult({
          status: 'failed',
          error: response.error,
          execution_time_ms: 0
        });
      }
    } catch (error) {
      setResult({
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
        execution_time_ms: 0
      });
    } finally {
      setExecuting(false);
    }
  };

  const handleClose = () => {
    setInputData({});
    setResult(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
              <p className="text-sm text-gray-500 mt-1">{entityName}</p>
            </div>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-500"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-4">
          {/* Description */}
          <div className="mb-6">
            <p className="text-sm text-gray-700">{description}</p>
          </div>

          {/* Input Fields */}
          <div className="space-y-4 mb-6">
            <h3 className="text-sm font-medium text-gray-900">Input Parameters</h3>
            {inputs.map((input) => (
              <div key={input.key}>
                <label htmlFor={input.key} className="block text-sm font-medium text-gray-700 mb-1">
                  {input.label} {input.required && <span className="text-red-500">*</span>}
                </label>
                {input.type === 'textarea' ? (
                  <textarea
                    id={input.key}
                    rows={4}
                    value={(inputData[input.key] as string) || ''}
                    onChange={(e) => handleInputChange(input.key, e.target.value)}
                    placeholder={input.placeholder}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  />
                ) : (
                  <input
                    type="text"
                    id={input.key}
                    value={(inputData[input.key] as string) || ''}
                    onChange={(e) => handleInputChange(input.key, e.target.value)}
                    placeholder={input.placeholder}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  />
                )}
              </div>
            ))}
          </div>

          {/* Execute Button */}
          <button
            onClick={handleExecute}
            disabled={executing}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {executing ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Executing...
              </>
            ) : (
              <>▶ Execute {entityType}</>
            )}
          </button>

          {/* Results */}
          {result && (
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-900 mb-2">Result</h3>
              <div className={`p-4 rounded-md ${result.status === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                {/* Status Header */}
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm font-medium ${result.status === 'success' ? 'text-green-800' : 'text-red-800'}`}>
                    {result.status === 'success' ? '✓ Success' : '✗ Failed'}
                  </span>
                  <span className="text-xs text-gray-500">
                    {result.execution_time_ms}ms
                  </span>
                </div>

                {/* Output/Error */}
                <div className="mt-2">
                  {result.status === 'success' ? (
                    <pre className="text-sm text-gray-800 whitespace-pre-wrap break-words font-mono bg-white p-3 rounded border border-green-200 max-h-96 overflow-y-auto">
                      {result.output}
                    </pre>
                  ) : (
                    <div className="text-sm text-red-800">
                      <p className="font-medium">Error:</p>
                      <pre className="mt-1 whitespace-pre-wrap break-words font-mono bg-white p-3 rounded border border-red-200 max-h-96 overflow-y-auto">
                        {result.error}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-6 py-4 flex justify-end">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
