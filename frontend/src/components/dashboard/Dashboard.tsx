'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { useFlowStore, useExecutionStore, useCrewStore } from '@/lib/store';

export default function Dashboard() {
  const router = useRouter();
  const { flows } = useFlowStore();
  const { executions } = useExecutionStore();
  const { crews } = useCrewStore();

  const [stats, setStats] = useState({
    totalFlows: 0,
    totalCrews: 0,
    totalExecutions: 0,
    runningExecutions: 0,
  });

  useEffect(() => {
    setStats({
      totalFlows: flows.length,
      totalCrews: crews.length,
      totalExecutions: executions.length,
      runningExecutions: executions.filter((e) => e.status === 'running').length,
    });
  }, [flows, crews, executions]);

  const recentExecutions = executions
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Welcome to your CrewAI orchestration platform</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Flows</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{stats.totalFlows}</p>
            </div>
            <div className="text-4xl">🔀</div>
          </div>
          <button
            onClick={() => router.push('/flows')}
            className="mt-4 text-sm text-blue-600 hover:text-blue-700"
          >
            View all →
          </button>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Crews</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{stats.totalCrews}</p>
            </div>
            <div className="text-4xl">👥</div>
          </div>
          <button
            onClick={() => router.push('/crews')}
            className="mt-4 text-sm text-blue-600 hover:text-blue-700"
          >
            View all →
          </button>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Executions</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{stats.totalExecutions}</p>
            </div>
            <div className="text-4xl">⚙️</div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Running Now</p>
              <p className="text-3xl font-bold text-blue-600 mt-2">{stats.runningExecutions}</p>
            </div>
            <div className="text-4xl">▶️</div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button
            onClick={() => router.push('/flows/new')}
            className="p-4 text-center border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="text-2xl mb-2">➕</div>
            <p className="text-sm font-medium text-gray-700">Create Flow</p>
          </button>

          <button
            onClick={() => router.push('/crews')}
            className="p-4 text-center border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="text-2xl mb-2">👥</div>
            <p className="text-sm font-medium text-gray-700">Create Crew</p>
          </button>

          <button
            onClick={() => router.push('/tools')}
            className="p-4 text-center border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="text-2xl mb-2">🔧</div>
            <p className="text-sm font-medium text-gray-700">Add Tool</p>
          </button>

          <button
            onClick={() => router.push('/chat')}
            className="p-4 text-center border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
          >
            <div className="text-2xl mb-2">💬</div>
            <p className="text-sm font-medium text-gray-700">Start Chat</p>
          </button>
        </div>
      </div>

      {/* Recent Executions */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Recent Executions</h2>
          <button
            onClick={() => router.push('/executions')}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            View all →
          </button>
        </div>

        {recentExecutions.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">No executions yet</p>
        ) : (
          <div className="space-y-3">
            {recentExecutions.map((execution) => (
              <div
                key={execution.id}
                onClick={() => router.push(`/executions/${execution.id}`)}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium text-gray-900">
                    #{execution.id}
                  </span>
                  <span className="text-sm text-gray-500 capitalize">
                    {execution.execution_type}
                  </span>
                  <span className={`px-2 py-1 text-xs font-medium rounded ${
                    execution.status === 'completed' ? 'bg-green-100 text-green-800' :
                    execution.status === 'running' ? 'bg-blue-100 text-blue-800' :
                    execution.status === 'failed' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {execution.status}
                  </span>
                </div>
                <span className="text-sm text-gray-500">
                  {new Date(execution.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
