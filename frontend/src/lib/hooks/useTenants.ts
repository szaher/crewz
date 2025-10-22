import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api-client';

export interface Tenant {
  id: string;
  name: string;
  schema_name: string;
  status: string;
  max_users: number;
  max_agents: number;
  max_flows: number;
  user_count: number;
  created_at: string;
  updated_at: string;
}

export interface TenantDetail extends Tenant {
  api_key: string;
  settings: Record<string, any>;
}

export interface UseTenantsOptions {
  skip?: number;
  limit?: number;
  status?: string;
}

export function useTenants(options: UseTenantsOptions = {}) {
  const { skip = 0, limit = 20, status } = options;
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTenants = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        skip: String(skip),
        limit: String(limit),
      });
      if (status) {
        params.append('status', status);
      }
      const response = await apiClient.get(`/api/v1/tenants?${params}`);
      if (response.error) throw new Error(response.error);
      setTenants(response.data?.tenants || []);
      setTotal(response.data?.total || 0);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch tenants';
      setError(message);
      console.error('Failed to fetch tenants:', err);
    } finally {
      setLoading(false);
    }
  }, [skip, limit, status]);

  const approveTenant = async (id: string): Promise<void> => {
    const response = await apiClient.post(`/api/v1/tenants/${id}/approve`, {});
    if (response.error) throw new Error(response.error);
  };

  const suspendTenant = async (id: string): Promise<void> => {
    const response = await apiClient.post(`/api/v1/tenants/${id}/suspend`, {});
    if (response.error) throw new Error(response.error);
  };

  const activateTenant = async (id: string): Promise<void> => {
    const response = await apiClient.post(`/api/v1/tenants/${id}/activate`, {});
    if (response.error) throw new Error(response.error);
  };

  const deleteTenant = async (id: string): Promise<void> => {
    const response = await apiClient.delete(`/api/v1/tenants/${id}`);
    if (response.error) throw new Error(response.error);
  };

  const getTenant = async (id: string): Promise<TenantDetail> => {
    const response = await apiClient.get(`/api/v1/tenants/${id}`);
    if (response.error) throw new Error(response.error);
    return response.data as TenantDetail;
  };

  const updateTenant = async (id: string, data: Partial<Omit<TenantDetail, 'id' | 'schema_name' | 'api_key' | 'user_count' | 'created_at' | 'updated_at'>>): Promise<TenantDetail> => {
    const response = await apiClient.put(`/api/v1/tenants/${id}`, data);
    if (response.error) throw new Error(response.error);
    return response.data as TenantDetail;
  };

  useEffect(() => {
    fetchTenants();
  }, [skip, limit, status]);

  return {
    tenants,
    total,
    loading,
    error,
    refetch: fetchTenants,
    approveTenant,
    suspendTenant,
    activateTenant,
    deleteTenant,
    getTenant,
    updateTenant,
  };
}
