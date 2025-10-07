import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api-client';

export interface LLMProvider {
  id: number;
  name: string;
  provider_type: 'openai' | 'anthropic' | 'local' | 'azure';
  api_key?: string;
  base_url?: string;
  model: string;
  temperature?: number;
  max_tokens?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateLLMProviderData {
  name: string;
  provider_type: 'openai' | 'anthropic' | 'local' | 'azure';
  api_key?: string;
  base_url?: string;
  model: string;
  temperature?: number;
  max_tokens?: number;
  is_active?: boolean;
}

export interface UpdateLLMProviderData {
  name?: string;
  provider_type?: 'openai' | 'anthropic' | 'local' | 'azure';
  api_key?: string;
  base_url?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  is_active?: boolean;
}

export function useLLMProviders() {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProviders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/v1/llm-providers');
      if (response.error) throw new Error(response.error);
      setProviders(response.data?.providers || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch LLM providers';
      setError(message);
      console.error('Failed to fetch LLM providers:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createProvider = async (data: CreateLLMProviderData): Promise<LLMProvider> => {
    const response = await apiClient.post('/api/v1/llm-providers', data);
    if (response.error) throw new Error(response.error);

    const newProvider = response.data;
    setProviders(prev => [...prev, newProvider]);

    return newProvider;
  };

  const updateProvider = async (id: number, data: UpdateLLMProviderData): Promise<LLMProvider> => {
    const response = await apiClient.put(`/api/v1/llm-providers/${id}`, data);
    if (response.error) throw new Error(response.error);

    const updatedProvider = response.data;
    setProviders(prev => prev.map(p => p.id === id ? updatedProvider : p));

    return updatedProvider;
  };

  const deleteProvider = async (id: number): Promise<void> => {
    const response = await apiClient.delete(`/api/v1/llm-providers/${id}`);
    if (response.error) throw new Error(response.error);

    setProviders(prev => prev.filter(p => p.id !== id));
  };

  const getProvider = async (id: number): Promise<LLMProvider> => {
    const response = await apiClient.get(`/api/v1/llm-providers/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  const testConnection = async (id: number): Promise<{ success: boolean; message?: string }> => {
    const response = await apiClient.post(`/api/v1/llm-providers/${id}/test`, {});
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  return {
    providers,
    loading,
    error,
    createProvider,
    updateProvider,
    deleteProvider,
    getProvider,
    testConnection,
    refetch: fetchProviders,
  };
}
