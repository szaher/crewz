'use client';

import { useEffect, useState } from 'react';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import ToolRegistry from '@/components/tools/ToolRegistry';
import ToolForm from '@/components/tools/ToolForm';
import { useToolStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';

export default function ToolsPage() {
  const { setTools } = useToolStore();
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingToolId, setEditingToolId] = useState<number | undefined>();

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/api/v1/tools');
      if (response.data) {
        setTools(response.data.tools || []);
      }
    } catch (error) {
      console.error('Failed to load tools:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTool = () => {
    setEditingToolId(undefined);
    setShowForm(true);
  };

  const handleEditTool = (toolId: number) => {
    setEditingToolId(toolId);
    setShowForm(true);
  };

  const handleSaveTool = () => {
    setShowForm(false);
    loadTools();
  };

  if (showForm) {
    return (
      <ProtectedRoute>
        <div className="max-w-4xl mx-auto p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            {editingToolId ? 'Edit Tool' : 'Create New Tool'}
          </h2>
          <ToolForm
            toolId={editingToolId}
            onSave={handleSaveTool}
            onCancel={() => setShowForm(false)}
          />
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="max-w-7xl mx-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <ToolRegistry
            onCreateTool={handleCreateTool}
            onEditTool={handleEditTool}
          />
        )}
      </div>
    </ProtectedRoute>
  );
}
