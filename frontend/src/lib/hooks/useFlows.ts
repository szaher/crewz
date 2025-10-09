import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api-client';

export interface Flow {
  id: number;
  name: string;
  description: string;
  version: string;
  is_active: boolean;
  nodes: any[];
  edges: any[];
  variables: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CreateFlowData {
  name: string;
  description?: string;
  variables?: Record<string, any>;
}

export interface UpdateFlowData {
  name?: string;
  description?: string;
  nodes?: any[];
  edges?: any[];
  variables?: Record<string, any>;
  is_active?: boolean;
}

export function useFlows() {
  const [flows, setFlows] = useState<Flow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFlows = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/v1/flows');
      if (response.error) throw new Error(response.error);
      setFlows(response.data?.flows || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch flows';
      setError(message);
      console.error('Failed to fetch flows:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createFlow = async (data: CreateFlowData): Promise<Flow> => {
    const response = await apiClient.post('/api/v1/flows', data);
    if (response.error) throw new Error(response.error);

    // Add to local state
    const newFlow = response.data;
    setFlows(prev => [...prev, newFlow]);

    return newFlow;
  };

  const updateFlow = async (id: number, data: UpdateFlowData): Promise<Flow> => {
    const response = await apiClient.put(`/api/v1/flows/${id}`, data);
    if (response.error) throw new Error(response.error);

    // Update local state
    const updatedFlow = response.data;
    setFlows(prev => prev.map(f => f.id === id ? updatedFlow : f));

    return updatedFlow;
  };

  const deleteFlow = async (id: number): Promise<void> => {
    const response = await apiClient.delete(`/api/v1/flows/${id}`);
    if (response.error) throw new Error(response.error);

    // Remove from local state
    setFlows(prev => prev.filter(f => f.id !== id));
  };

  const getFlow = async (id: number): Promise<Flow> => {
    const response = await apiClient.get(`/api/v1/flows/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  useEffect(() => {
    fetchFlows();
  }, [fetchFlows]);

  return {
    flows,
    loading,
    error,
    createFlow,
    updateFlow,
    deleteFlow,
    getFlow,
    refetch: fetchFlows,
  };
}
