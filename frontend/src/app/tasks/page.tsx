'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import TaskForm from '@/components/tasks/TaskForm';
import TaskList from '@/components/tasks/TaskList';
import { useTasks } from '@/lib/hooks/useTasks';
import { useAgents } from '@/lib/hooks/useAgents';
import { useCrews } from '@/lib/hooks/useCrews';
import type { Task, TaskCreate, TaskUpdate } from '@/types/task';

export default function TasksPage() {
  const router = useRouter();
  const { tasks, loading, error, fetchTasks, createTask, updateTask, deleteTask, unassignFromCrew } = useTasks();
  const { agents, refetch: refetchAgents } = useAgents();
  const { crews, refetch: refetchCrews } = useCrews();

  const [showTaskForm, setShowTaskForm] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | undefined>(undefined);
  const [filterCrew, setFilterCrew] = useState<number | 'all'>('all');
  const [filterAgent, setFilterAgent] = useState<number | 'all'>('all');

  useEffect(() => {
    fetchTasks();
    refetchAgents();
    refetchCrews();
  }, [fetchTasks, refetchAgents, refetchCrews]);

  const handleCreateTask = () => {
    setEditingTask(undefined);
    setShowTaskForm(true);
  };

  const handleEditTask = (task: Task) => {
    setEditingTask(task);
    setShowTaskForm(true);
  };

  const handleSaveTask = async (taskData: TaskCreate | TaskUpdate) => {
    try {
      if (editingTask) {
        await updateTask(editingTask.id, taskData as TaskUpdate);
      } else {
        await createTask(taskData as TaskCreate);
      }
      setShowTaskForm(false);
      setEditingTask(undefined);
      fetchTasks();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save task');
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    try {
      await deleteTask(taskId);
      fetchTasks();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete task');
    }
  };

  const handleUnassignTask = async (taskId: number) => {
    try {
      await unassignFromCrew(taskId);
      fetchTasks();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to unassign task from crew');
    }
  };

  // Build agent names map for task list
  const agentNames = agents.reduce((acc, agent) => {
    acc[agent.id] = agent.name;
    return acc;
  }, {} as Record<number, string>);

  // Filter tasks
  const filteredTasks = tasks.filter(task => {
    if (filterCrew !== 'all' && task.crew_id !== filterCrew) return false;
    if (filterAgent !== 'all' && task.agent_id !== filterAgent) return false;
    return true;
  });

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
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
              >
                + Create Task
              </button>
            </div>

            {/* Filters */}
            <div className="bg-white p-4 rounded-lg border border-gray-200 mb-6">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium text-gray-700">Filter by Crew:</label>
                  <select
                    value={filterCrew}
                    onChange={(e) => setFilterCrew(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                    className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:border-blue-500 focus:ring-blue-500"
                  >
                    <option value="all">All Crews</option>
                    {crews.map(crew => (
                      <option key={crew.id} value={crew.id}>{crew.name}</option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium text-gray-700">Filter by Agent:</label>
                  <select
                    value={filterAgent}
                    onChange={(e) => setFilterAgent(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                    className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:border-blue-500 focus:ring-blue-500"
                  >
                    <option value="all">All Agents</option>
                    {agents.map(agent => (
                      <option key={agent.id} value={agent.id}>{agent.name}</option>
                    ))}
                  </select>
                </div>

                {(filterCrew !== 'all' || filterAgent !== 'all') && (
                  <button
                    onClick={() => {
                      setFilterCrew('all');
                      setFilterAgent('all');
                    }}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    Clear Filters
                  </button>
                )}
              </div>
            </div>

            {/* Task Form */}
            {showTaskForm && (
              <div className="bg-white p-6 rounded-lg border border-gray-200 mb-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  {editingTask ? 'Edit Task' : 'Create New Task'}
                </h2>
                <TaskForm
                  task={editingTask}
                  onSave={handleSaveTask}
                  onCancel={() => {
                    setShowTaskForm(false);
                    setEditingTask(undefined);
                  }}
                />
              </div>
            )}

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
              <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                <p className="text-gray-500 mb-4">
                  {tasks.length === 0
                    ? 'No tasks yet. Create your first task to get started.'
                    : 'No tasks match your filters.'}
                </p>
                {tasks.length === 0 && (
                  <button
                    onClick={handleCreateTask}
                    className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
                  >
                    Create Task
                  </button>
                )}
              </div>
            ) : (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm text-gray-600">
                    Showing {filteredTasks.length} of {tasks.length} tasks
                  </p>
                </div>
                <TaskList
                  tasks={filteredTasks}
                  onEdit={handleEditTask}
                  onDelete={handleDeleteTask}
                  onUnassign={handleUnassignTask}
                  agentNames={agentNames}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
