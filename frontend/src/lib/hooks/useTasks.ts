import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api-client';
import { Task, TaskCreate, TaskUpdate } from '@/types/task';

interface UseTasksResult {
  tasks: Task[];
  loading: boolean;
  error: string | null;
  fetchTasks: (crewId?: number, agentId?: number) => Promise<void>;
  createTask: (task: TaskCreate) => Promise<Task | null>;
  updateTask: (id: number, task: TaskUpdate) => Promise<Task | null>;
  deleteTask: (id: number) => Promise<boolean>;
  unassignFromCrew: (id: number) => Promise<Task | null>;
  reorderCrewTasks: (crewId: number, taskOrders: Record<number, number>) => Promise<Task[]>;
}

export function useTasks(): UseTasksResult {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTasks = useCallback(async (crewId?: number, agentId?: number) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (crewId !== undefined) params.append('crew_id', crewId.toString());
      if (agentId !== undefined) params.append('agent_id', agentId.toString());
      params.append('page_size', '100');

      const response = await apiClient.get<{ tasks: Task[]; total: number }>(
        `/api/v1/tasks?${params.toString()}`
      );

      if (response.data) {
        setTasks(response.data.tasks);
      } else if (response.error) {
        setError(response.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tasks');
    } finally {
      setLoading(false);
    }
  }, []);

  const createTask = useCallback(async (task: TaskCreate): Promise<Task | null> => {
    setError(null);

    try {
      const response = await apiClient.post<Task>('/api/v1/tasks', task);

      if (response.data) {
        setTasks(prev => [...prev, response.data!]);
        return response.data;
      } else if (response.error) {
        setError(response.error);
        return null;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create task');
      return null;
    }

    return null;
  }, []);

  const updateTask = useCallback(async (id: number, task: TaskUpdate): Promise<Task | null> => {
    setError(null);

    try {
      const response = await apiClient.put<Task>(`/api/v1/tasks/${id}`, task);

      if (response.data) {
        setTasks(prev => prev.map(t => (t.id === id ? response.data! : t)));
        return response.data;
      } else if (response.error) {
        setError(response.error);
        return null;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update task');
      return null;
    }

    return null;
  }, []);

  const deleteTask = useCallback(async (id: number): Promise<boolean> => {
    setError(null);

    try {
      const response = await apiClient.delete(`/api/v1/tasks/${id}`);

      if (response.error) {
        setError(response.error);
        return false;
      }

      setTasks(prev => prev.filter(t => t.id !== id));
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete task');
      return false;
    }
  }, []);

  const unassignFromCrew = useCallback(async (id: number): Promise<Task | null> => {
    setError(null);

    try {
      const response = await apiClient.put<Task>(`/api/v1/tasks/${id}/unassign`, {});

      if (response.data) {
        setTasks(prev => prev.map(t => (t.id === id ? response.data! : t)));
        return response.data;
      } else if (response.error) {
        setError(response.error);
        return null;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to unassign task from crew');
      return null;
    }

    return null;
  }, []);

  const reorderCrewTasks = useCallback(async (
    crewId: number,
    taskOrders: Record<number, number>
  ): Promise<Task[]> => {
    setError(null);

    try {
      const response = await apiClient.post<Task[]>(
        `/api/v1/tasks/crew/${crewId}/reorder`,
        taskOrders
      );

      if (response.data) {
        // Update tasks in state
        setTasks(prev => {
          const updatedTasks = [...prev];
          response.data!.forEach(updatedTask => {
            const index = updatedTasks.findIndex(t => t.id === updatedTask.id);
            if (index !== -1) {
              updatedTasks[index] = updatedTask;
            }
          });
          return updatedTasks;
        });
        return response.data;
      } else if (response.error) {
        setError(response.error);
        return [];
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reorder tasks');
      return [];
    }

    return [];
  }, []);

  return {
    tasks,
    loading,
    error,
    fetchTasks,
    createTask,
    updateTask,
    deleteTask,
    unassignFromCrew,
    reorderCrewTasks,
  };
}
