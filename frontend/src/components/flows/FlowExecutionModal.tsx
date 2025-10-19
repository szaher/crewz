'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';

interface FlowExecutionModalProps {
  flowId: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function FlowExecutionModal({ flowId, isOpen, onClose }: FlowExecutionModalProps) {
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [variableInputs, setVariableInputs] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [executionResult, setExecutionResult] = useState<any>(null);
  const [flow, setFlow] = useState<any>(null);

  useEffect(() => {
    if (isOpen && flowId) {
      loadFlowAndVariables();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, flowId]);

  const loadFlowAndVariables = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load flow details
      const flowResponse = await apiClient.get(`/api/v1/flows/${flowId}`);
      if (!flowResponse.data) {
        throw new Error('Flow not found');
      }

      const flowData = flowResponse.data;
      setFlow(flowData);

      // Extract variables from flow
      const allVariables: Record<string, string> = {};

      // Extract variables from crew steps and agent tasks
      // NOTE: We do NOT extract from step names, only from task descriptions and flow variables
      if (flowData.config?.steps) {
        for (const step of flowData.config.steps) {
          if (step.type === 'crew' && step.crew_id) {
            // Fetch crew details to get tasks
            try {
              const crewResponse = await apiClient.get(`/api/v1/crews/${step.crew_id}`);
              if (crewResponse.data) {
                const crew = crewResponse.data;

                // Fetch tasks for this crew
                const tasksResponse = await apiClient.get(`/api/v1/tasks/crew/${step.crew_id}/tasks`);
                if (tasksResponse.data) {
                  const tasks = Array.isArray(tasksResponse.data) ? tasksResponse.data : [];
                  tasks.forEach((task: any) => {
                    // Extract variables from task description and expected_output
                    const extractVars = (text: string) => {
                      if (!text) return;
                      const matches = text.match(/\{(\w+)\}/g);
                      if (matches) {
                        matches.forEach((match: string) => {
                          const varName = match.replace(/\{|\}/g, '');
                          allVariables[varName] = '';
                        });
                      }
                    };

                    extractVars(task.description);
                    extractVars(task.expected_output);
                  });
                }
              }
            } catch (err) {
              console.error(`Failed to load crew ${step.crew_id}:`, err);
            }
          }

          // Extract variables from agent task descriptions (not step names!)
          if (step.type === 'agent' && step.task_description) {
            const matches = step.task_description.match(/\{(\w+)\}/g);
            if (matches) {
              matches.forEach((match: string) => {
                const varName = match.replace(/\{|\}/g, '');
                allVariables[varName] = '';
              });
            }
          }
        }
      }

      // Add flow's defined variables last (so they take precedence)
      if (flowData.variables) {
        Object.keys(flowData.variables).forEach(key => {
          allVariables[key] = '';
        });
      }

      setVariables(allVariables);
      setVariableInputs(allVariables);

    } catch (err: any) {
      console.error('Failed to load flow variables:', err);
      setError(err.message || 'Failed to load flow variables');
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    try {
      setExecuting(true);
      setError(null);

      // Create execution request
      const response = await apiClient.post('/api/v1/executions', {
        execution_type: 'flow',
        flow_id: flowId,
        input_data: {
          variables: variableInputs,
        },
      });

      if (response.error) {
        throw new Error(response.error);
      }

      setExecutionResult(response.data);

      // Wait a moment then close
      setTimeout(() => {
        onClose();
        // Optionally redirect to execution details page
        if (response.data?.id) {
          window.location.href = `/executions/${response.data.id}`;
        }
      }, 1500);

    } catch (err: any) {
      console.error('Failed to execute flow:', err);
      setError(err.message || 'Failed to execute flow');
    } finally {
      setExecuting(false);
    }
  };

  const handleVariableChange = (key: string, value: string) => {
    setVariableInputs({
      ...variableInputs,
      [key]: value,
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">Execute Flow</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={executing}
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
              {error}
            </div>
          ) : executionResult ? (
            <div className="text-center py-8">
              <div className="text-green-600 text-6xl mb-4">✓</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Flow Execution Started!
              </h3>
              <p className="text-gray-600">
                Redirecting to execution details...
              </p>
            </div>
          ) : (
            <>
              {flow && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {flow.name}
                  </h3>
                  {flow.description && (
                    <p className="text-sm text-gray-600">{flow.description}</p>
                  )}
                </div>
              )}

              {Object.keys(variables).length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-600 mb-4">
                    No input variables required for this flow.
                  </p>
                  <button
                    onClick={handleExecute}
                    disabled={executing}
                    className="px-6 py-3 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {executing ? 'Executing...' : 'Execute Flow'}
                  </button>
                </div>
              ) : (
                <>
                  <div className="mb-6">
                    <h4 className="text-sm font-semibold text-gray-700 mb-4">
                      Input Variables
                    </h4>
                    <div className="space-y-4">
                      {Object.keys(variables).map((key) => (
                        <div key={key}>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            {key}
                          </label>
                          <input
                            type="text"
                            value={variableInputs[key] || ''}
                            onChange={(e) => handleVariableChange(key, e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder={`Enter value for ${key}`}
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-3 justify-end">
                    <button
                      onClick={onClose}
                      disabled={executing}
                      className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleExecute}
                      disabled={executing}
                      className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {executing ? 'Executing...' : 'Execute Flow'}
                    </button>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
