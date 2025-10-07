import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api-client';

export interface Tool {
  id: number;
  name: string;
  description?: string;
  implementation_type: 'python' | 'api' | 'builtin';
  code?: string;
  api_endpoint?: string;
  parameters_schema?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CreateToolData {
  name: string;
  description?: string;
  implementation_type: 'python' | 'api' | 'builtin';
  code?: string;
  api_endpoint?: string;
  parameters_schema?: Record<string, any>;
}

export interface UpdateToolData {
  name?: string;
  description?: string;
  implementation_type?: 'python' | 'api' | 'builtin';
  code?: string;
  api_endpoint?: string;
  parameters_schema?: Record<string, any>;
}

export function useTools() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTools = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/v1/tools');
      if (response.error) throw new Error(response.error);
      setTools(response.data?.tools || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch tools';
      setError(message);
      console.error('Failed to fetch tools:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createTool = async (data: CreateToolData): Promise<Tool> => {
    const response = await apiClient.post('/api/v1/tools', data);
    if (response.error) throw new Error(response.error);

    const newTool = response.data;
    setTools(prev => [...prev, newTool]);

    return newTool;
  };

  const updateTool = async (id: number, data: UpdateToolData): Promise<Tool> => {
    const response = await apiClient.put(`/api/v1/tools/${id}`, data);
    if (response.error) throw new Error(response.error);

    const updatedTool = response.data;
    setTools(prev => prev.map(t => t.id === id ? updatedTool : t));

    return updatedTool;
  };

  const deleteTool = async (id: number): Promise<void> => {
    const response = await apiClient.delete(`/api/v1/tools/${id}`);
    if (response.error) throw new Error(response.error);

    setTools(prev => prev.filter(t => t.id !== id));
  };

  const getTool = async (id: number): Promise<Tool> => {
    const response = await apiClient.get(`/api/v1/tools/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  const validateTool = async (id: number): Promise<{ valid: boolean; errors?: string[] }> => {
    const response = await apiClient.post(`/api/v1/tools/${id}/validate`, {});
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  return {
    tools,
    loading,
    error,
    createTool,
    updateTool,
    deleteTool,
    getTool,
    validateTool,
    refetch: fetchTools,
  };
}
