'use client';

import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import ToolRegistry from '@/components/tools/ToolRegistry';
import { useTools } from '@/lib/hooks/useTools';

export default function ToolsPage() {
  const router = useRouter();
  const { tools, loading, error, refetch } = useTools();

  const handleCreateTool = () => {
    router.push('/tools/new');
  };

  const handleEditTool = (toolId: string) => {
    router.push(`/tools/${toolId}`);
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <Breadcrumbs />
            {error ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="text-center max-w-md">
                  <p className="text-red-600 mb-4">Failed to load tools: {error}</p>
                  <button
                    onClick={refetch}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Retry
                  </button>
                </div>
              </div>
            ) : loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : tools.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <p className="text-gray-500 mb-4">No tools registered yet. Create your first tool to get started.</p>
                <button
                  onClick={handleCreateTool}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                >
                  Create Tool
                </button>
              </div>
            ) : (
              <ToolRegistry
                tools={tools}
                onCreateTool={handleCreateTool}
                onEditTool={handleEditTool}
              />
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
