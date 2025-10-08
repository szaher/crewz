'use client';

import { useCallback, useEffect, useState } from 'react';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Dashboard from '@/components/dashboard/Dashboard';
import { apiClient } from '@/lib/api-client';
import { useFlowStore, useExecutionStore, useCrewStore, useAgentStore, useToolStore } from '@/lib/store';

export default function DashboardPage() {
  const { setFlows } = useFlowStore();
  const { setExecutions } = useExecutionStore();
  const { setCrews } = useCrewStore();
  const { setAgents } = useAgentStore();
  const { setTools } = useToolStore();

  const [loading, setLoading] = useState(true);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    try {
      // Load all data in parallel
      const [flowsRes, crewsRes, agentsRes, toolsRes, executionsRes] = await Promise.all([
        apiClient.get('/api/v1/flows'),
        apiClient.get('/api/v1/crews'),
        apiClient.get('/api/v1/agents'),
        apiClient.get('/api/v1/tools'),
        apiClient.get('/api/v1/executions'),
      ]);

      if (flowsRes.data) setFlows(flowsRes.data.flows || []);
      if (crewsRes.data) setCrews(crewsRes.data.crews || []);
      if (agentsRes.data) setAgents(agentsRes.data.agents || []);
      if (toolsRes.data) setTools(toolsRes.data.tools || []);
      if (executionsRes.data) setExecutions(executionsRes.data.executions || []);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, [setAgents, setCrews, setExecutions, setFlows, setTools]);

  useEffect(() => {
    void loadDashboardData();
  }, [loadDashboardData]);

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : (
              <Dashboard />
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
