'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useToolStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';
import type { ToolCreate } from '@/types/api';

// Dynamically import CodeMirror to avoid SSR issues
const CodeMirror = dynamic(() => import('@uiw/react-codemirror'), { ssr: false });
const python = dynamic(() => import('@codemirror/lang-python').then(mod => mod.python), { ssr: false });

interface ToolFormProps {
  toolId?: number;
  onSave?: (toolId: number) => void;
  onCancel?: () => void;
}

export default function ToolForm({ toolId, onSave, onCancel }: ToolFormProps) {
  const { tools, addTool, updateTool } = useToolStore();
  const existingTool = toolId ? tools.find((t) => t.id === toolId) : null;

  const [formData, setFormData] = useState<ToolCreate>({
    name: existingTool?.name || '',
    description: existingTool?.description || '',
    tool_type: existingTool?.tool_type || 'function',
    input_schema: existingTool?.input_schema || {},
    output_schema: existingTool?.output_schema || {},
    docker_image: existingTool?.docker_image,
    docker_command: existingTool?.docker_command,
    function_code: existingTool?.function_code,
    api_endpoint: existingTool?.api_endpoint,
    api_method: existingTool?.api_method,
    api_headers: existingTool?.api_headers,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [codeError, setCodeError] = useState<string | null>(null);
  const [showExampleModal, setShowExampleModal] = useState(false);

  const formatError = (err: any): string => {
    if (typeof err === 'string') return err;
    if (err instanceof Error) return err.message;
    if (err && typeof err === 'object') {
      // Handle Pydantic validation errors
      if (Array.isArray(err)) {
        return err.map(e => `${e.loc?.join('.') || 'field'}: ${e.msg || 'Invalid'}`).join(', ');
      }
      if (err.detail) return typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
      if (err.message) return err.message;
      if (err.msg) return err.msg;
      return JSON.stringify(err);
    }
    return 'Failed to save tool';
  };

  const validatePythonCode = (code: string): boolean => {
    setCodeError(null);

    if (!code || code.trim() === '') {
      setCodeError('Function code is required for function-type tools');
      return false;
    }

    // Basic Python syntax validation
    const lines = code.split('\n');
    let hasDefStatement = false;
    let indentationError = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim().startsWith('def ')) {
        hasDefStatement = true;
      }

      // Check for common indentation issues (mixing tabs and spaces)
      if (line.match(/^\s*\t/) && line.match(/^ /)) {
        indentationError = true;
        break;
      }
    }

    if (!hasDefStatement) {
      setCodeError('Code must contain at least one function definition (def ...)');
      return false;
    }

    if (indentationError) {
      setCodeError('Indentation error: Do not mix tabs and spaces');
      return false;
    }

    // Check for balanced brackets
    const openBrackets = (code.match(/[\(\[\{]/g) || []).length;
    const closeBrackets = (code.match(/[\)\]\}]/g) || []).length;
    if (openBrackets !== closeBrackets) {
      setCodeError('Unbalanced brackets in code');
      return false;
    }

    return true;
  };

  const exampleCode = `def execute(params: dict) -> dict:
    """
    Execute the tool with the given parameters.

    Args:
        params (dict): Input parameters defined by input_schema

    Returns:
        dict: Output data matching output_schema
    """
    # Example: Web search tool
    query = params.get('query', '')
    max_results = params.get('max_results', 10)

    # Your tool logic here
    results = perform_search(query, max_results)

    return {
        'results': results,
        'count': len(results),
        'query': query
    }

def perform_search(query: str, limit: int) -> list:
    """Helper function for the tool."""
    # Implementation here
    return []
`;

  const loadExampleCode = () => {
    setFormData({ ...formData, function_code: exampleCode });
    setShowExampleModal(false);
    setCodeError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setCodeError(null);

    // Validate Python code for function-type tools
    if (formData.tool_type === 'function') {
      if (!validatePythonCode(formData.function_code || '')) {
        return; // Validation error is already set by validatePythonCode
      }
    }

    setLoading(true);

    try {
      if (toolId) {
        const response = await apiClient.put(`/api/v1/tools/${toolId}`, formData);
        if (response.error) {
          setError(formatError(response.error));
        } else if (response.data) {
          updateTool(toolId, response.data.tool);
          onSave?.(toolId);
        }
      } else {
        const response = await apiClient.post('/api/v1/tools', formData);
        if (response.error) {
          setError(formatError(response.error));
        } else if (response.data) {
          addTool(response.data.tool);
          onSave?.(response.data.tool.id);
        }
      }
    } catch (err) {
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Info */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Tool Name</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
              placeholder="e.g., Web Search"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <textarea
              required
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
              placeholder="What does this tool do?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Tool Type</label>
            <select
              value={formData.tool_type}
              onChange={(e) => setFormData({ ...formData, tool_type: e.target.value as any })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            >
              <option value="function">Function (Python code)</option>
              <option value="api">API Endpoint</option>
              <option value="docker">Docker Container</option>
            </select>
          </div>
        </div>
      </div>

      {/* Type-Specific Configuration */}
      {formData.tool_type === 'docker' && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Docker Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Docker Image</label>
              <input
                type="text"
                value={formData.docker_image || ''}
                onChange={(e) => setFormData({ ...formData, docker_image: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm"
                placeholder="python:3.11-slim"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Command</label>
              <input
                type="text"
                value={formData.docker_command || ''}
                onChange={(e) => setFormData({ ...formData, docker_command: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm"
                placeholder="/app/tool.py"
              />
            </div>
          </div>
        </div>
      )}

      {formData.tool_type === 'api' && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">API Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">API Endpoint</label>
              <input
                type="url"
                value={formData.api_endpoint || ''}
                onChange={(e) => setFormData({ ...formData, api_endpoint: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm"
                placeholder="https://api.example.com/search"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">HTTP Method</label>
              <select
                value={formData.api_method || 'GET'}
                onChange={(e) => setFormData({ ...formData, api_method: e.target.value as any })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {formData.tool_type === 'function' && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Function Code</h3>
            <button
              type="button"
              onClick={() => setShowExampleModal(true)}
              className="px-3 py-1 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
            >
              View Example
            </button>
          </div>
          <div className="border border-gray-300 rounded-md overflow-hidden">
            <CodeMirror
              value={formData.function_code || ''}
              height="400px"
              extensions={[python()]}
              onChange={(value) => {
                setFormData({ ...formData, function_code: value });
                setCodeError(null);
              }}
              theme="light"
              basicSetup={{
                lineNumbers: true,
                highlightActiveLineGutter: true,
                highlightSpecialChars: true,
                foldGutter: true,
                drawSelection: true,
                dropCursor: true,
                allowMultipleSelections: true,
                indentOnInput: true,
                bracketMatching: true,
                closeBrackets: true,
                autocompletion: true,
                rectangularSelection: true,
                crosshairCursor: true,
                highlightActiveLine: true,
                highlightSelectionMatches: true,
                closeBracketsKeymap: true,
                searchKeymap: true,
                foldKeymap: true,
                completionKeymap: true,
                lintKeymap: true,
              }}
            />
          </div>
          {codeError && (
            <div className="mt-2 text-sm text-red-600">
              {codeError}
            </div>
          )}
          <p className="mt-2 text-xs text-gray-500">
            Code must contain at least one function definition. The main entry point should be named <code className="px-1 py-0.5 bg-gray-100 rounded">execute(params: dict) → dict</code>
          </p>
        </div>
      )}

      {/* Schemas */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Input/Output Schemas</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Input Schema (JSON)</label>
            <textarea
              rows={8}
              value={JSON.stringify(formData.input_schema, null, 2)}
              onChange={(e) => {
                try {
                  setFormData({ ...formData, input_schema: JSON.parse(e.target.value) });
                } catch {}
              }}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Output Schema (JSON)</label>
            <textarea
              rows={8}
              value={JSON.stringify(formData.output_schema, null, 2)}
              onChange={(e) => {
                try {
                  setFormData({ ...formData, output_schema: JSON.parse(e.target.value) });
                } catch {}
              }}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-xs"
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Saving...' : toolId ? 'Update Tool' : 'Create Tool'}
        </button>
      </div>

      {/* Example Code Modal */}
      {showExampleModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-xl font-semibold text-gray-900">Example Tool Function</h3>
              <button
                type="button"
                onClick={() => setShowExampleModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
              <div className="mb-4">
                <h4 className="font-semibold text-gray-900 mb-2">Function Requirements:</h4>
                <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                  <li>Must contain an <code className="px-1 py-0.5 bg-gray-100 rounded">execute(params: dict)</code> function</li>
                  <li>The execute function should accept a dictionary of parameters</li>
                  <li>Must return a dictionary matching your output schema</li>
                  <li>Can include helper functions as needed</li>
                  <li>Should include proper type hints and docstrings</li>
                </ul>
              </div>

              <div className="mb-4">
                <h4 className="font-semibold text-gray-900 mb-2">Example Code:</h4>
                <div className="border border-gray-300 rounded-md overflow-hidden">
                  <CodeMirror
                    value={exampleCode}
                    height="400px"
                    extensions={[python()]}
                    editable={false}
                    theme="light"
                    basicSetup={{
                      lineNumbers: true,
                      highlightActiveLineGutter: false,
                      highlightSpecialChars: true,
                      foldGutter: true,
                      drawSelection: false,
                      dropCursor: false,
                      allowMultipleSelections: false,
                      indentOnInput: false,
                      bracketMatching: true,
                      closeBrackets: false,
                      autocompletion: false,
                      rectangularSelection: false,
                      crosshairCursor: false,
                      highlightActiveLine: false,
                      highlightSelectionMatches: false,
                    }}
                  />
                </div>
              </div>

              <div className="bg-blue-50 p-4 rounded-md">
                <p className="text-sm text-blue-800">
                  <strong>Tip:</strong> Your input_schema defines what parameters are available in the <code className="px-1 py-0.5 bg-blue-100 rounded">params</code> dictionary. Your output_schema defines what your function should return.
                </p>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowExampleModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Close
              </button>
              <button
                type="button"
                onClick={loadExampleCode}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                Use This Example
              </button>
            </div>
          </div>
        </div>
      )}
    </form>
  );
}
