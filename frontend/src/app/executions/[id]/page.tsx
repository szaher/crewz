'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import ExecutionDetail from '@/components/executions/ExecutionDetail';
import ExecutionLogs from '@/components/executions/ExecutionLogs';
import { useExecutions, type Execution } from '@/lib/hooks/useExecutions';

export default function ExecutionPage() {
  const params = useParams();
  const router = useRouter();
  const executionId = Number(params.id);

  const { getExecution, cancelExecution } = useExecutions();
  const [execution, setExecution] = useState<Execution | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const loadExecution = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getExecution(executionId);
      setExecution(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load execution';
      setError(message);
      console.error('Failed to load execution:', err);
    } finally {
      setLoading(false);
    }
  }, [executionId, getExecution]);

  useEffect(() => {
    void loadExecution();
  }, [loadExecution]);

  const handleCancel = async () => {
    if (!execution || execution.status !== 'running') return;

    setCancelling(true);
    try {
      await cancelExecution(executionId);
      // Reload execution to get updated status
      await loadExecution();
    } catch (err) {
      console.error('Failed to cancel execution:', err);
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="min-h-screen flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  if (error || (!loading && !execution)) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="min-h-screen flex items-center justify-center">
              <div className="text-center max-w-md">
                <div className="text-5xl mb-4">⚠️</div>
                <p className="text-red-600 mb-4">
                  {error || 'Execution not found'}
                </p>
                <div className="flex gap-2 justify-center">
                  <button
                    onClick={() => loadExecution()}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Retry
                  </button>
                  <button
                    onClick={() => router.push('/executions')}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Go to Executions
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <Breadcrumbs />
        {/* Actions Bar */}
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={() => router.back()}
            className="text-gray-600 hover:text-gray-900 flex items-center gap-2"
          >
            ← Back
          </button>

          {execution.status === 'running' && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
            >
              {cancelling ? 'Cancelling...' : 'Cancel Execution'}
            </button>
          )}
        </div>

        {/* Execution Detail */}
        <ExecutionDetail execution={execution} />

        {/* Live Logs */}
        <div className="mt-6">
          <ExecutionLogs executionId={executionId} />
        </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
