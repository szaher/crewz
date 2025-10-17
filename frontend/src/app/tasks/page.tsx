'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { useTasks } from '@/lib/hooks/useTasks';
import { useAgents } from '@/lib/hooks/useAgents';
import { useCrews } from '@/lib/hooks/useCrews';
import type { Task } from '@/types/task';

export default function TasksPage() {
  const router = useRouter();
  const { tasks, loading, error, fetchTasks, deleteTask, unassignFromCrew } = useTasks();
  const { agents, refetch: refetchAgents } = useAgents();
  const { crews, refetch: refetchCrews } = useCrews();

  const [filterCrew, setFilterCrew] = useState<string | 'all'>('all');
  const [filterAgent, setFilterAgent] = useState<string | 'all'>('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchTasks();
    refetchAgents();
    refetchCrews();
  }, [fetchTasks, refetchAgents, refetchCrews]);

  const handleCreateTask = () => {
    router.push('/tasks/new');
  };

  const handleEditTask = (task: Task) => {
    router.push(`/tasks/${task.id}`);
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm('Are you sure you want to delete this task?')) return;

    try {
      await deleteTask(taskId);
      fetchTasks();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete task');
    }
  };

  const handleUnassignTask = async (taskId: string) => {
    if (!confirm('Remove this task from its crew? The task will not be deleted.')) return;

    try {
      await unassignFromCrew(taskId);
      fetchTasks();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to unassign task from crew');
    }
  };

  // Build agent and crew names maps
  const agentNames = agents.reduce((acc, agent) => {
    acc[agent.id] = agent.name;
    return acc;
  }, {} as Record<string, string>);

  const crewNames = crews.reduce((acc, crew) => {
    acc[crew.id] = crew.name;
    return acc;
  }, {} as Record<string, string>);

  // Filter tasks
  const filteredTasks = tasks.filter(task => {
    if (search && !task.name.toLowerCase().includes(search.toLowerCase()) &&
        !task.description.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (filterCrew !== 'all' && task.crew_id !== filterCrew) return false;
    if (filterAgent !== 'all' && task.agent_id !== filterAgent) return false;
    return true;
  });

  const hasActiveFilters = search || filterCrew !== 'all' || filterAgent !== 'all';

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <Breadcrumbs />

            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Tasks</h1>
                <p className="text-sm text-gray-600 mt-1">
                  Manage tasks for your crews and agents
                </p>
              </div>
              <button
                onClick={handleCreateTask}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                + Create Task
              </button>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Search */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Search
                  </label>
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search tasks..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Crew Filter */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Filter by Crew
                  </label>
                  <select
                    value={filterCrew}
                    onChange={(e) => setFilterCrew(e.target.value === 'all' ? 'all' : e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All Crews</option>
                    {crews.map(crew => (
                      <option key={crew.id} value={crew.id}>{crew.name}</option>
                    ))}
                  </select>
                </div>

                {/* Agent Filter */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Filter by Agent
                  </label>
                  <select
                    value={filterAgent}
                    onChange={(e) => setFilterAgent(e.target.value === 'all' ? 'all' : e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All Agents</option>
                    {agents.map(agent => (
                      <option key={agent.id} value={agent.id}>{agent.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Clear Filters */}
              {hasActiveFilters && (
                <div className="mt-4">
                  <button
                    onClick={() => {
                      setSearch('');
                      setFilterCrew('all');
                      setFilterAgent('all');
                    }}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    Clear all filters
                  </button>
                </div>
              )}
            </div>

            {/* Content */}
            {error ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="text-center max-w-md">
                  <p className="text-red-600 mb-4">Failed to load tasks: {error}</p>
                  <button
                    onClick={() => fetchTasks()}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Retry
                  </button>
                </div>
              </div>
            ) : loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : filteredTasks.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <p className="text-gray-500 mb-4">
                  {hasActiveFilters
                    ? 'No tasks match your filters.'
                    : 'No tasks yet. Create your first task to get started.'}
                </p>
                {!hasActiveFilters && (
                  <button
                    onClick={handleCreateTask}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Create Task
                  </button>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredTasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    agentName={task.agent_id ? agentNames[task.agent_id] : undefined}
                    crewName={task.crew_id ? crewNames[task.crew_id] : undefined}
                    onEdit={() => handleEditTask(task)}
                    onDelete={() => handleDeleteTask(task.id)}
                    onUnassign={task.crew_id ? () => handleUnassignTask(task.id) : undefined}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

// Task Card Component
function TaskCard({
  task,
  agentName,
  crewName,
  onEdit,
  onDelete,
  onUnassign
}: {
  task: Task;
  agentName?: string;
  crewName?: string;
  onEdit: () => void;
  onDelete: () => void;
  onUnassign?: () => void;
}) {
  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-900 flex-1">
          {task.name}
        </h3>
        <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800">
          Order: {task.order}
        </span>
      </div>

      <p className="text-sm text-gray-600 mt-2 line-clamp-2">
        {task.description}
      </p>

      {/* Expected Output */}
      <div className="mt-3">
        <span className="text-xs font-medium text-gray-500">Expected Output:</span>
        <p className="text-sm text-gray-700 line-clamp-2">{task.expected_output}</p>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-2 mt-4">
        {task.async_execution && (
          <span className="px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-800">
            Async
          </span>
        )}
        <span className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">
          {task.output_format}
        </span>
        {task.output_file && (
          <span className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">
            📄 {task.output_file}
          </span>
        )}
      </div>

      {/* Assignments */}
      {(agentName || crewName) && (
        <div className="mt-4 space-y-1 text-xs text-gray-600">
          {agentName && (
            <div>
              <span className="font-medium">Agent:</span> {agentName}
            </div>
          )}
          {crewName && (
            <div>
              <span className="font-medium">Crew:</span> {crewName}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="mt-4 flex gap-2">
        <button
          onClick={onEdit}
          className="flex-1 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
        >
          Edit
        </button>
        {onUnassign ? (
          <button
            onClick={onUnassign}
            className="px-4 py-2 text-sm font-medium text-orange-600 bg-orange-50 rounded-md hover:bg-orange-100"
            title="Remove from crew"
          >
            Unassign
          </button>
        ) : (
          <button
            onClick={onDelete}
            className="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  );
}
