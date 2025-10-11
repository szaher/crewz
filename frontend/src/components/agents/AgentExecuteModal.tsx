'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { useLLMProviders } from '@/lib/hooks/useLLMProviders';

interface Task {
  id: number;
  name: string;
  description: string;
  expected_output: string;
  variables: string[] | null;
}

interface Agent {
  id: number;
  name: string;
  llm_provider_id: number;
  role: string;
}

interface AgentExecuteModalProps {
  agentId: number;
  agentName: string;
  isOpen: boolean;
  onClose: () => void;
}

interface ExecutionResult {
  status: 'success' | 'failed';
  output?: string;
  error?: string;
  execution_time_ms: number;
}

export default function AgentExecuteModal({
  agentId,
  agentName,
  isOpen,
  onClose
}: AgentExecuteModalProps) {
  const { providers } = useLLMProviders();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [useNewTask, setUseNewTask] = useState(false);
  const [newTaskDescription, setNewTaskDescription] = useState('');
  const [newTaskExpectedOutput, setNewTaskExpectedOutput] = useState('');
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  const [selectedProviderId, setSelectedProviderId] = useState<number | null>(null);
  const [context, setContext] = useState('');
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<ExecutionResult | null>(null);

  // Fetch agent details and tasks when modal opens
  useEffect(() => {
    if (isOpen) {
      const fetchData = async () => {
        // Fetch agent details
        const agentResponse = await apiClient.get(`/api/v1/agents/${agentId}`);
        if (agentResponse.data) {
          setAgent(agentResponse.data);
          // Set default provider to agent's provider
          setSelectedProviderId(agentResponse.data.llm_provider_id);
        }

        // Fetch tasks
        const tasksResponse = await apiClient.get(`/api/v1/agents/${agentId}/tasks`);
        if (tasksResponse.data && tasksResponse.data.tasks) {
          setTasks(tasksResponse.data.tasks);
        }
      };
      void fetchData();
    } else {
      // Reset state when closing
      setSelectedTaskId(null);
      setUseNewTask(false);
      setNewTaskDescription('');
      setNewTaskExpectedOutput('');
      setVariableValues({});
      setSelectedProviderId(null);
      setContext('');
      setResult(null);
    }
  }, [isOpen, agentId]);

  if (!isOpen) return null;

  const selectedTask = tasks.find(t => t.id === selectedTaskId);
  const variables = selectedTask?.variables || [];

  const handleExecute = async () => {
    setExecuting(true);
    setResult(null);

    try {
      const executionData: any = {};

      if (useNewTask) {
        // Use new task description
        executionData.task = newTaskDescription;
        executionData.expected_output = newTaskExpectedOutput;
      } else if (selectedTaskId) {
        // Use existing task
        executionData.task_id = selectedTaskId;
      } else {
        throw new Error('Please select a task or create a new one');
      }

      // Add variables if any
      if (Object.keys(variableValues).length > 0) {
        executionData.variables = variableValues;
      }

      // Add context if provided
      if (context) {
        executionData.context = context;
      }

      // Add provider override only if different from agent's default
      if (selectedProviderId && agent && selectedProviderId !== agent.llm_provider_id) {
        executionData.provider_id = selectedProviderId;
      }

      const response = await apiClient.post(`/api/v1/agents/${agentId}/execute`, executionData);

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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Execute Agent</h2>
              <p className="text-sm text-gray-500 mt-1">{agentName}</p>
            </div>
            <button
              onClick={onClose}
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
          {/* Task Selection */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Select Task</h3>

            {/* Existing tasks */}
            {tasks.length > 0 && !useNewTask && (
              <div className="space-y-2 mb-4">
                {tasks.map((task) => (
                  <div
                    key={task.id}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedTaskId === task.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => {
                      setSelectedTaskId(task.id);
                      setVariableValues({});
                    }}
                  >
                    <div className="font-medium text-gray-900">{task.name}</div>
                    <div className="text-sm text-gray-600 mt-1">{task.description}</div>
                    {task.variables && task.variables.length > 0 && (
                      <div className="mt-2 flex gap-1 flex-wrap">
                        {task.variables.map((v) => (
                          <span key={v} className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                            {`{${v}}`}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* New task toggle */}
            <button
              onClick={() => {
                setUseNewTask(!useNewTask);
                setSelectedTaskId(null);
                setVariableValues({});
              }}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              {useNewTask ? '← Use existing task' : '+ Create new task'}
            </button>

            {/* New task form */}
            {useNewTask && (
              <div className="mt-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Task Description <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    rows={4}
                    value={newTaskDescription}
                    onChange={(e) => setNewTaskDescription(e.target.value)}
                    placeholder="Describe what the agent should do. Use {variable_name} for variables."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Expected Output <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    rows={2}
                    value={newTaskExpectedOutput}
                    onChange={(e) => setNewTaskExpectedOutput(e.target.value)}
                    placeholder="Describe what output you expect from the agent"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Variables (for selected existing task) */}
          {!useNewTask && selectedTask && variables.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Task Variables</h3>
              <p className="text-xs text-gray-500 mb-3">Fill in the values for variables in the task</p>
              <div className="space-y-3">
                {variables.map((varName) => (
                  <div key={varName}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {varName} <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={variableValues[varName] || ''}
                      onChange={(e) => setVariableValues({ ...variableValues, [varName]: e.target.value })}
                      placeholder={`Enter value for {${varName}}`}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* LLM Provider Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              LLM Provider
            </label>
            {agent && (
              <p className="text-xs text-gray-500 mb-2">
                Agent&apos;s default: {providers.find((p: any) => p.id === agent.llm_provider_id)?.name || 'Unknown'}
              </p>
            )}
            <select
              value={selectedProviderId || ''}
              onChange={(e) => setSelectedProviderId(e.target.value ? Number(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              {providers.map((provider: any) => (
                <option key={provider.id} value={provider.id}>
                  {provider.name} ({provider.provider_type})
                  {agent && provider.id === agent.llm_provider_id ? ' - Default' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Context */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Context (optional)
            </label>
            <textarea
              rows={3}
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Any additional context or information..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Execute Button */}
          <button
            onClick={handleExecute}
            disabled={executing || (!useNewTask && !selectedTaskId) || (useNewTask && (!newTaskDescription || !newTaskExpectedOutput))}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {executing ? 'Executing...' : 'Execute Agent'}
          </button>

          {/* Result */}
          {result && (
            <div className={`mt-6 p-4 rounded-lg ${result.status === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              <div className="flex items-center justify-between mb-2">
                <h4 className={`font-medium ${result.status === 'success' ? 'text-green-900' : 'text-red-900'}`}>
                  {result.status === 'success' ? '✓ Execution Complete' : '✗ Execution Failed'}
                </h4>
                <span className="text-xs text-gray-500">
                  {result.execution_time_ms}ms
                </span>
              </div>
              {result.output && (
                <div className="mt-2">
                  <p className="text-sm font-medium text-gray-700 mb-1">Output:</p>
                  <pre className="text-sm text-gray-800 whitespace-pre-wrap bg-white p-3 rounded border border-gray-200 max-h-96 overflow-y-auto">
                    {result.output}
                  </pre>
                </div>
              )}
              {result.error && (
                <div className="mt-2">
                  <p className="text-sm font-medium text-red-700 mb-1">Error:</p>
                  <p className="text-sm text-red-600">{result.error}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
