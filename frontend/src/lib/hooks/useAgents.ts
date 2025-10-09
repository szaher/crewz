import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api-client';

export interface Agent {
  id: number;
  name: string;
  role: string;
  goal: string;
  backstory?: string;
  llm_provider_id?: number;
  tools: number[];
  allow_delegation: boolean;
  verbose: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateAgentData {
  name: string;
  role: string;
  goal: string;
  backstory?: string;
  llm_provider_id?: number;
  tools?: number[];
  allow_delegation?: boolean;
  verbose?: boolean;
}

export interface UpdateAgentData {
  name?: string;
  role?: string;
  goal?: string;
  backstory?: string;
  llm_provider_id?: number;
  tools?: number[];
  allow_delegation?: boolean;
  verbose?: boolean;
}

export function useAgents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/v1/agents');
      if (response.error) throw new Error(response.error);
      setAgents(response.data?.agents || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch agents';
      setError(message);
      console.error('Failed to fetch agents:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createAgent = async (data: CreateAgentData): Promise<Agent> => {
    const response = await apiClient.post('/api/v1/agents', data);
    if (response.error) throw new Error(response.error);

    const newAgent = response.data;
    setAgents(prev => [...prev, newAgent]);

    return newAgent;
  };

  const updateAgent = async (id: number, data: UpdateAgentData): Promise<Agent> => {
    const response = await apiClient.put(`/api/v1/agents/${id}`, data);
    if (response.error) throw new Error(response.error);

    const updatedAgent = response.data;
    setAgents(prev => prev.map(a => a.id === id ? updatedAgent : a));

    return updatedAgent;
  };

  const deleteAgent = async (id: number): Promise<void> => {
    const response = await apiClient.delete(`/api/v1/agents/${id}`);
    if (response.error) throw new Error(response.error);

    setAgents(prev => prev.filter(a => a.id !== id));
  };

  const getAgent = async (id: number): Promise<Agent> => {
    const response = await apiClient.get(`/api/v1/agents/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  return {
    agents,
    loading,
    error,
    // Keep both names for backward compatibility across components
    fetchAgents,
    createAgent,
    updateAgent,
    deleteAgent,
    getAgent,
    refetch: fetchAgents,
  };
}
