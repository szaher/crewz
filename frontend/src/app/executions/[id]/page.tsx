'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import ExecutionDetail from '@/components/executions/ExecutionDetail';
import ExecutionLogs from '@/components/executions/ExecutionLogs';
import LiveExecutionStream from '@/components/executions/LiveExecutionStream';
import QueuePosition from '@/components/executions/QueuePosition';
import ArtifactList from '@/components/executions/ArtifactList';
import ExecutionActions from '@/components/executions/ExecutionActions';
import { useExecutions } from '@/lib/hooks/useExecutions';
import type { Execution } from '@/types/api';

export default function ExecutionPage() {
  const params = useParams();
  const router = useRouter();

  // Safely parse execution ID (UUID string)
  const rawId = params.id;
  const executionId = rawId && rawId !== 'undefined' ? String(rawId) : null;

  const { getExecution } = useExecutions();
  const [execution, setExecution] = useState<Execution | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadExecution = useCallback(async () => {
    // Validate executionId before making API call
    if (!executionId) {
      setError('Invalid execution ID');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await getExecution(executionId);
      setExecution(data as Execution);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load execution';
      setError(message);
      console.error('Failed to load execution:', err);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [executionId]); // Only depend on executionId, not getExecution

  useEffect(() => {
    void loadExecution();
  }, [loadExecution]);

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
        </div>

        {/* Execution Detail */}
        {execution && <ExecutionDetail execution={execution} />}

        {/* ===== NEW WORKER ARCHITECTURE COMPONENTS (Phase 004) ===== */}

        {/* Queue Position (only shown if execution is queued) */}
        {execution && execution.queue_position !== undefined && execution.queue_position !== null && (
          <div className="mt-6">
            <QueuePosition
              executionId={executionId}
              initialPosition={execution.queue_position}
              initialEstimatedWait={execution.estimated_start_seconds || null}
            />
          </div>
        )}

        {/* Execution Actions (Cancel/Re-execute) */}
        {execution && (
          <div className="mt-6">
            <ExecutionActions
              executionId={executionId}
              status={execution.status}
              onActionComplete={loadExecution}
            />
          </div>
        )}

        {/* Live Execution Stream (WebSocket) - Feature flag controlled */}
        {execution && (execution.status === 'running' || execution.status === 'queued') && (
          <div className="mt-6">
            <LiveExecutionStream
              executionId={executionId}
              enabled={true} // Enabled for live streaming
            />
          </div>
        )}

        {/* Artifacts List (downloads) */}
        {execution && execution.artifacts && execution.artifacts.length > 0 && (
          <div className="mt-6">
            <ArtifactList
              executionId={executionId}
              artifacts={execution.artifacts}
            />
          </div>
        )}

        {/* Live Logs (existing) */}
        <div className="mt-6">
          <ExecutionLogs executionId={executionId} />
        </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
