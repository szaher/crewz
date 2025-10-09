'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';

interface FailedExecution {
  id: number;
  flow_id: number;
  flow_name?: string;
  error: string;
  created_at: string;
  completed_at?: string;
}

export default function ErrorsList() {
  const router = useRouter();
  const [errors, setErrors] = useState<FailedExecution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchErrors = async () => {
      setLoading(true);
      try {
        const response = await apiClient.get('/api/v1/executions');
        if (response.error) throw new Error(response.error);

        const executions = response.data?.executions || [];
        const failedExecutions = executions
          .filter((e: any) => e.status === 'failed')
          .slice(0, 10)
          .map((e: any) => ({
            id: e.id,
            flow_id: e.flow_id,
            flow_name: e.flow_name,
            error: e.error || 'Unknown error',
            created_at: e.created_at,
            completed_at: e.completed_at,
          }));

        setErrors(failedExecutions);
      } catch (err) {
        console.error('Failed to fetch errors:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchErrors();
  }, []);

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Errors</h3>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-gray-200 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (errors.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Errors</h3>
        <div className="text-center py-8">
          <p className="text-sm text-gray-500">No errors found</p>
          <p className="text-xs text-gray-400 mt-1">All executions completed successfully</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Errors</h3>
      <div className="space-y-3">
        {errors.map((error) => (
          <div
            key={error.id}
            onClick={() => router.push(`/executions/${error.id}`)}
            className="p-4 border border-red-200 bg-red-50 rounded-lg hover:bg-red-100 cursor-pointer transition-colors"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900">
                  Execution #{error.id}
                </span>
                {error.flow_name && (
                  <span className="text-sm text-gray-600">
                    {error.flow_name}
                  </span>
                )}
              </div>
              <span className="text-xs text-gray-500">
                {new Date(error.created_at).toLocaleString()}
              </span>
            </div>
            <p className="text-sm text-red-800 line-clamp-2">{error.error}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
