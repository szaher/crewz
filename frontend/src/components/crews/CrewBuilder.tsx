"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useCrews } from '@/lib/hooks/useCrews';
import { useAgents } from '@/lib/hooks/useAgents';
import { useLLMProviders } from '@/lib/hooks/useLLMProviders';
import { useTasks } from '@/lib/hooks/useTasks';
import type { CrewCreate, CrewUpdate } from '@/types/api';
import type { Task, TaskCreate, TaskUpdate } from '@/types/task';
import AgentCard from './AgentCard';
import TaskForm from '../tasks/TaskForm';
import TaskList from '../tasks/TaskList';
import TaskTemplateSelector from '../tasks/TaskTemplateSelector';

interface CrewBuilderProps {
  crewId?: number;
  onSave?: (crewId: number) => void;
}

export default function CrewBuilder({ crewId, onSave }: CrewBuilderProps) {
  const router = useRouter();
  const { crews, createCrew, updateCrew: updateCrewHook, getCrew } = useCrews();
  const { agents, loading: agentsLoading, error: agentsError, refetch: refetchAgents } = useAgents();
  const { providers, loading: providersLoading } = useLLMProviders();
  const { tasks, fetchTasks, createTask, updateTask, deleteTask } = useTasks();

  const existingCrew = crewId ? crews.find((c) => c.id === crewId) : null;

  const [formData, setFormData] = useState<CrewCreate>({
    name: existingCrew?.name || '',
    description: existingCrew?.description || '',
    process_type: existingCrew?.process_type || 'sequential',
    agent_ids: existingCrew?.agent_ids || [],
    task_ids: [],
    task_delegation_enabled: existingCrew?.task_delegation_enabled ?? true,
    verbose: existingCrew?.verbose ?? false,
    config: existingCrew?.config || {},
  });

  const [selectedAgents, setSelectedAgents] = useState<number[]>(existingCrew?.agent_ids || []);
  const [selectedTasks, setSelectedTasks] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [providerFilter, setProviderFilter] = useState<number | 'all'>('all');

  // Task management state
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | undefined>(undefined);
  const [showTaskSelector, setShowTaskSelector] = useState(false);

  useEffect(() => {
    // Ensure agents are loaded when opening the builder
    refetchAgents();
  }, [refetchAgents]);

  useEffect(() => {
    if (existingCrew) {
      setFormData({
        name: existingCrew.name,
        description: existingCrew.description,
        process_type: existingCrew.process_type,
        agent_ids: existingCrew.agent_ids,
        task_delegation_enabled: existingCrew.task_delegation_enabled,
        verbose: existingCrew.verbose,
        config: existingCrew.config,
      });
      setSelectedAgents(existingCrew.agent_ids);
    }
  }, [existingCrew]);

  useEffect(() => {
    // Fetch ALL tasks (not just crew tasks) so we can select from existing tasks
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    // Set selected tasks when editing an existing crew
    if (crewId && tasks.length > 0) {
      const crewTaskIds = tasks.filter(t => t.crew_id === crewId).map(t => t.id);
      setSelectedTasks(crewTaskIds);
      setFormData(prev => ({ ...prev, task_ids: crewTaskIds }));
    }
  }, [crewId, tasks]);

  const handleAgentToggle = (agentId: number) => {
    const newSelection = selectedAgents.includes(agentId)
      ? selectedAgents.filter((id) => id !== agentId)
      : [...selectedAgents, agentId];

    setSelectedAgents(newSelection);
    setFormData({ ...formData, agent_ids: newSelection });
  };

  const handleTaskToggle = (taskId: number) => {
    const newSelection = selectedTasks.includes(taskId)
      ? selectedTasks.filter((id) => id !== taskId)
      : [...selectedTasks, taskId];

    setSelectedTasks(newSelection);
    setFormData({ ...formData, task_ids: newSelection });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (formData.agent_ids.length === 0) {
      setError('Please select at least one agent');
      return;
    }

    setLoading(true);

    try {
      if (crewId) {
        // Update existing crew
        const updatedCrew = await updateCrewHook(crewId, formData);
        onSave?.(updatedCrew.id);
      } else {
        // Create new crew
        const newCrew = await createCrew(formData);
        onSave?.(newCrew.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save crew');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = () => {
    setEditingTask(undefined);
    setShowTaskForm(true);
  };

  const handleEditTask = (task: Task) => {
    setEditingTask(task);
    setShowTaskForm(true);
  };

  const handleSaveTask = async (taskData: TaskCreate | TaskUpdate) => {
    if (!crewId) {
      alert('Please save the crew before adding tasks');
      return;
    }

    try {
      if (editingTask) {
        await updateTask(editingTask.id, taskData as TaskUpdate);
      } else {
        await createTask({ ...taskData, crew_id: crewId } as TaskCreate);
      }
      setShowTaskForm(false);
      setEditingTask(undefined);
      fetchTasks(crewId);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save task');
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    try {
      await deleteTask(taskId);
      fetchTasks();
      // Remove from selected tasks if it was selected
      setSelectedTasks(prev => prev.filter(id => id !== taskId));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete task');
    }
  };

  const handleUnassignTask = async (taskId: number) => {
    try {
      // This will be handled by the unassign button in TaskList
      fetchTasks();
      setSelectedTasks(prev => prev.filter(id => id !== taskId));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to unassign task');
    }
  };

  // Build agent names map for task list
  const agentNames = agents.reduce((acc, agent) => {
    acc[agent.id] = agent.name;
    return acc;
  }, {} as Record<number, string>);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        {crewId ? 'Edit Crew' : 'Create New Crew'}
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h3>

          <div className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                Crew Name
              </label>
              <input
                id="name"
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                placeholder="e.g., Research Team"
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                Description
              </label>
              <textarea
                id="description"
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                placeholder="What does this crew do?"
              />
            </div>

            <div>
              <label htmlFor="process_type" className="block text-sm font-medium text-gray-700">
                Collaboration Pattern
              </label>
              <select
                id="process_type"
                value={formData.process_type}
                onChange={(e) => setFormData({ ...formData, process_type: e.target.value as 'sequential' | 'hierarchical' })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
              >
                <option value="sequential">Sequential (agents work in order)</option>
                <option value="hierarchical">Hierarchical (manager assigns tasks)</option>
              </select>
            </div>

            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.task_delegation_enabled}
                  onChange={(e) => setFormData({ ...formData, task_delegation_enabled: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Enable task delegation</span>
              </label>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.verbose}
                  onChange={(e) => setFormData({ ...formData, verbose: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Verbose logging</span>
              </label>
            </div>
          </div>
        </div>

        {/* Agent Selection */}
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Select Agents ({selectedAgents.length} selected)
          </h3>

          {/* Provider Filter */}
          <div className="flex items-center gap-3 mb-4">
            <label className="text-sm text-gray-700">Filter by provider</label>
            <select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
            >
              <option value="all">All providers</option>
              {!providersLoading && providers.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.provider_type})</option>
              ))}
            </select>
          </div>

          {agentsError ? (
            <div className="text-sm text-red-600">Failed to load agents: {agentsError}</div>
          ) : agentsLoading ? (
            <div className="text-sm text-gray-500">Loading agents…</div>
          ) : agents.length === 0 ? (
            <div>
              <p className="text-sm text-gray-500 mb-3">No agents available. Create your first agent to get started.</p>
              <button
                type="button"
                onClick={() => router.push('/agents')}
                className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                Create Agent
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(providerFilter === 'all'
                ? agents
                : agents.filter((a: any) => (a as any).llm_provider_id === Number(providerFilter))
              ).map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  selected={selectedAgents.includes(agent.id)}
                  onToggle={() => handleAgentToggle(agent.id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Task Assignment - Select Existing Tasks */}
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Assign Tasks ({selectedTasks.length} selected)
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                Select existing tasks to assign to this crew
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowTaskSelector(!showTaskSelector)}
              className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
            >
              {showTaskSelector ? 'Hide' : 'Show'} Task Selector
            </button>
          </div>

          {showTaskSelector && (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {tasks.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-sm text-gray-500">No tasks available. Create tasks first in the Tasks page.</p>
                  <button
                    type="button"
                    onClick={() => router.push('/tasks')}
                    className="mt-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Go to Tasks
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-2">
                  {tasks.map((task) => (
                    <div
                      key={task.id}
                      onClick={() => handleTaskToggle(task.id)}
                      className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                        selectedTasks.includes(task.id)
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={selectedTasks.includes(task.id)}
                              onChange={() => handleTaskToggle(task.id)}
                              className="h-4 w-4 text-blue-600 rounded border-gray-300"
                              onClick={(e) => e.stopPropagation()}
                            />
                            <h4 className="font-medium text-gray-900">{task.name}</h4>
                            {task.crew_id && task.crew_id !== crewId && (
                              <span className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded">
                                Assigned to another crew
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mt-1 ml-6">{task.description}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {selectedTasks.length > 0 && !showTaskSelector && (
            <div className="mt-2">
              <p className="text-sm text-gray-600">
                {selectedTasks.length} task{selectedTasks.length !== 1 ? 's' : ''} assigned
              </p>
            </div>
          )}
        </div>

        {/* Tasks Management */}
        {crewId && (
          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Manage Tasks ({tasks.filter(t => t.crew_id === crewId).length})
              </h3>
              <div className="flex gap-2">
                <TaskTemplateSelector
                  crewId={crewId}
                  agentIds={selectedAgents}
                  onTasksCreated={() => fetchTasks()}
                />
                <button
                  type="button"
                  onClick={handleCreateTask}
                  className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
                >
                  Create New Task
                </button>
              </div>
            </div>

            {showTaskForm ? (
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="text-md font-semibold text-gray-900 mb-4">
                  {editingTask ? 'Edit Task' : 'Create New Task'}
                </h4>
                <TaskForm
                  task={editingTask}
                  crewId={crewId}
                  onSave={handleSaveTask}
                  onCancel={() => {
                    setShowTaskForm(false);
                    setEditingTask(undefined);
                  }}
                />
              </div>
            ) : (
              <TaskList
                tasks={tasks.filter(t => t.crew_id === crewId)}
                onEdit={handleEditTask}
                onDelete={handleDeleteTask}
                onUnassign={handleUnassignTask}
                agentNames={agentNames}
              />
            )}
          </div>
        )}

        {!crewId && (
          <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
            <p className="text-sm text-blue-800">
              💡 Save the crew first to add tasks. Tasks will help define what work this crew should perform.
            </p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => window.history.back()}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Saving...' : crewId ? 'Update Crew' : 'Create Crew'}
          </button>
        </div>
      </form>
    </div>
  );
}
