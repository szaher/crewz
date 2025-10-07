import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api-client';

export interface Crew {
  id: number;
  name: string;
  description?: string;
  process_type: 'sequential' | 'hierarchical';
  agents: number[];
  created_at: string;
  updated_at: string;
}

export interface CreateCrewData {
  name: string;
  description?: string;
  process_type: 'sequential' | 'hierarchical';
  agents?: number[];
}

export interface UpdateCrewData {
  name?: string;
  description?: string;
  process_type?: 'sequential' | 'hierarchical';
  agents?: number[];
}

export function useCrews() {
  const [crews, setCrews] = useState<Crew[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCrews = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/v1/crews');
      if (response.error) throw new Error(response.error);
      setCrews(response.data?.crews || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch crews';
      setError(message);
      console.error('Failed to fetch crews:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createCrew = async (data: CreateCrewData): Promise<Crew> => {
    const response = await apiClient.post('/api/v1/crews', data);
    if (response.error) throw new Error(response.error);

    const newCrew = response.data;
    setCrews(prev => [...prev, newCrew]);

    return newCrew;
  };

  const updateCrew = async (id: number, data: UpdateCrewData): Promise<Crew> => {
    const response = await apiClient.put(`/api/v1/crews/${id}`, data);
    if (response.error) throw new Error(response.error);

    const updatedCrew = response.data;
    setCrews(prev => prev.map(c => c.id === id ? updatedCrew : c));

    return updatedCrew;
  };

  const deleteCrew = async (id: number): Promise<void> => {
    const response = await apiClient.delete(`/api/v1/crews/${id}`);
    if (response.error) throw new Error(response.error);

    setCrews(prev => prev.filter(c => c.id !== id));
  };

  const getCrew = async (id: number): Promise<Crew> => {
    const response = await apiClient.get(`/api/v1/crews/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  useEffect(() => {
    fetchCrews();
  }, [fetchCrews]);

  return {
    crews,
    loading,
    error,
    createCrew,
    updateCrew,
    deleteCrew,
    getCrew,
    refetch: fetchCrews,
  };
}
