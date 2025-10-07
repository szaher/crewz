import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api-client';

export type ProviderType = 'openai' | 'anthropic' | 'ollama' | 'vllm' | 'custom';

export interface LLMProvider {
  id: number;
  name: string;
  provider_type: ProviderType;
  model_name: string;
  api_base?: string;
  config?: Record<string, any>;
  is_active: boolean;
  is_default: boolean;
  api_key_set?: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateLLMProviderData {
  name: string;
  provider_type: ProviderType;
  model_name: string;
  api_key?: string;
  api_base?: string;
  config?: Record<string, any>;
  is_default?: boolean;
  is_active?: boolean;
}

export interface UpdateLLMProviderData {
  name?: string;
  provider_type?: ProviderType;
  model_name?: string;
  api_key?: string;
  api_base?: string;
  config?: Record<string, any>;
  is_default?: boolean;
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
      // eslint-disable-next-line no-console
      console.error('Failed to fetch LLM providers:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createProvider = async (data: CreateLLMProviderData): Promise<LLMProvider> => {
    const response = await apiClient.post('/api/v1/llm-providers', data);
    if (response.error) throw new Error(response.error);
    const newProvider = response.data?.provider || response.data;
    setProviders(prev => [...prev, newProvider]);
    return newProvider;
  };

  const updateProvider = async (id: number, data: UpdateLLMProviderData): Promise<LLMProvider> => {
    const response = await apiClient.put(`/api/v1/llm-providers/${id}`, data);
    if (response.error) throw new Error(response.error);
    const updated = response.data?.provider || response.data;
    setProviders(prev => prev.map(p => (p.id === id ? updated : p)));
    return updated;
  };

  const deleteProvider = async (id: number): Promise<void> => {
    const response = await apiClient.delete(`/api/v1/llm-providers/${id}`);
    if (response.error) {
      const err: any = new Error(response.error);
      (err as any).status = response.status;
      throw err;
    }
    setProviders(prev => prev.filter(p => p.id !== id));
  };

  const getProvider = async (id: number): Promise<LLMProvider> => {
    const response = await apiClient.get(`/api/v1/llm-providers/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data?.provider || response.data;
  };

  const testConnection = async (id: number): Promise<{ success: boolean; message?: string }> => {
    const response = await apiClient.post(`/api/v1/llm-providers/${id}/test`, {});
    if (response.error) throw new Error(response.error);
    return response.data;
  };

  const setDefault = async (id: number): Promise<LLMProvider> => {
    const response = await apiClient.post(`/api/v1/llm-providers/${id}/set-default`, {});
    if (response.error) throw new Error(response.error);
    const updated = response.data?.provider || response.data;
    await fetchProviders();
    return updated;
  };

  const reassignDependents = async (
    sourceId: number,
    targetId: number,
    scope: 'agents' | 'crews' | 'all' = 'all'
  ): Promise<{ agents_reassigned: number; crews_reassigned: number }> => {
    const response = await apiClient.post(`/api/v1/llm-providers/${sourceId}/reassign`, {
      target_provider_id: targetId,
      scope,
    });
    if (response.error) throw new Error(response.error);
    // Refresh provider list after reassignment
    await fetchProviders();
    return {
      agents_reassigned: response.data?.agents_reassigned ?? 0,
      crews_reassigned: response.data?.crews_reassigned ?? 0,
    };
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
    setDefault,
    reassignDependents,
    refetch: fetchProviders,
  };
}
