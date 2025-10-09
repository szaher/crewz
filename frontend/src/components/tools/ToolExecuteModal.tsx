'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api-client';

interface Tool {
  id: number;
  name: string;
  description: string;
  tool_type: string;
  schema?: Record<string, any>;
}

interface ToolExecuteModalProps {
  tool: Tool;
  isOpen: boolean;
  onClose: () => void;
}

interface ExecutionResult {
  tool_id: number;
  tool_name: string;
  tool_type: string;
  input_data: Record<string, any>;
  status: 'success' | 'failed';
  output?: string;
  error?: string;
  execution_time_ms: number;
}

export default function ToolExecuteModal({ tool, isOpen, onClose }: ToolExecuteModalProps) {
  const [inputData, setInputData] = useState<Record<string, string>>({});
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<ExecutionResult | null>(null);

  if (!isOpen) return null;

  const inputFields = tool.schema?.input ? Object.entries(tool.schema.input) : [];

  const handleExecute = async () => {
    setExecuting(true);
    setResult(null);

    try {
      const response = await apiClient.post(`/api/v1/tools/${tool.id}/execute`, inputData);

      if (response.data) {
        setResult(response.data as ExecutionResult);
      } else if (response.error) {
        setResult({
          tool_id: tool.id,
          tool_name: tool.name,
          tool_type: tool.tool_type,
          input_data: inputData,
          status: 'failed',
          error: response.error,
          execution_time_ms: 0
        });
      }
    } catch (error) {
      setResult({
        tool_id: tool.id,
        tool_name: tool.name,
        tool_type: tool.tool_type,
        input_data: inputData,
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
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Execute Tool</h2>
              <p className="text-sm text-gray-500 mt-1">{tool.name}</p>
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
          {/* Tool Description */}
          <div className="mb-6">
            <p className="text-sm text-gray-700">{tool.description}</p>
            <div className="mt-2">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                {tool.tool_type}
              </span>
            </div>
          </div>

          {/* Input Fields */}
          <div className="space-y-4 mb-6">
            <h3 className="text-sm font-medium text-gray-900">Input Parameters</h3>
            {inputFields.length > 0 ? (
              inputFields.map(([key, description]) => (
                <div key={key}>
                  <label htmlFor={key} className="block text-sm font-medium text-gray-700 mb-1">
                    {key}
                  </label>
                  <input
                    type="text"
                    id={key}
                    value={inputData[key] || ''}
                    onChange={(e) => setInputData({ ...inputData, [key]: e.target.value })}
                    placeholder={typeof description === 'string' ? description : key}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500">No input parameters required</p>
            )}
          </div>

          {/* Execute Button */}
          <button
            onClick={handleExecute}
            disabled={executing}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {executing ? 'Executing...' : 'Execute Tool'}
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
                    <pre className="text-sm text-gray-800 whitespace-pre-wrap break-words font-mono bg-white p-3 rounded border border-green-200 max-h-64 overflow-y-auto">
                      {result.output}
                    </pre>
                  ) : (
                    <div className="text-sm text-red-800">
                      <p className="font-medium">Error:</p>
                      <pre className="mt-1 whitespace-pre-wrap break-words font-mono bg-white p-3 rounded border border-red-200">
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
