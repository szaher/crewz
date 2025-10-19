'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import ToolForm from '@/components/tools/ToolForm';
import { useTools, type Tool } from '@/lib/hooks/useTools';

export default function ToolEditPage() {
  const params = useParams();
  const router = useRouter();
  const toolId = params.id as string;
  const { getTool } = useTools();

  const [tool, setTool] = useState<Tool | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTool = async () => {
      if (!toolId || typeof toolId !== 'string') {
        setError('Invalid tool ID');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const data = await getTool(toolId);
        setTool(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load tool';
        setError(message);
        console.error('Failed to fetch tool:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTool();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toolId]);

  const handleSave = () => {
    router.push('/tools');
  };

  const handleCancel = () => {
    router.push('/tools');
  };

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-4xl mx-auto p-6">
              <Breadcrumbs />
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  if (error || !tool) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-4xl mx-auto p-6">
              <Breadcrumbs />
              <div className="flex flex-col items-center justify-center py-12">
                <div className="text-center max-w-md">
                  <p className="text-red-600 mb-4">{error || 'Tool not found'}</p>
                  <button
                    onClick={() => router.push('/tools')}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Back to Tools
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
          <div className="max-w-4xl mx-auto p-6">
            <Breadcrumbs />
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              Edit Tool: {tool.name}
            </h2>
            <ToolForm
              toolId={toolId}
              initialData={tool}
              onSave={handleSave}
              onCancel={handleCancel}
            />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
