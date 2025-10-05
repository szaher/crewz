'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import FlowCanvas from '@/components/flows/FlowCanvas';
import FlowToolbar from '@/components/flows/FlowToolbar';
import NodePalette from '@/components/flows/NodePalette';
import PropertyPanel from '@/components/flows/PropertyPanel';
import { useFlowStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';

export default function FlowEditorPage() {
  const params = useParams();
  const flowId = Number(params.id);
  const { setCurrentFlow } = useFlowStore();
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadFlow = async () => {
      try {
        const response = await apiClient.get(`/api/v1/flows/${flowId}`);
        if (response.data) {
          setCurrentFlow(response.data.flow);
        }
      } catch (error) {
        console.error('Failed to load flow:', error);
      } finally {
        setLoading(false);
      }
    };

    loadFlow();
  }, [flowId, setCurrentFlow]);

  const handleUpdateNode = (nodeId: string, data: any) => {
    // Node updates are handled by FlowCanvas and PropertyPanel
    console.log('Node updated:', nodeId, data);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <ProtectedRoute>
      <div className="h-screen flex flex-col">
        <FlowToolbar flowId={flowId} />

        <div className="flex-1 flex overflow-hidden">
          <NodePalette />

          <div className="flex-1">
            <FlowCanvas flowId={flowId} />
          </div>

          <PropertyPanel
            selectedNode={selectedNode}
            onUpdateNode={handleUpdateNode}
          />
        </div>
      </div>
    </ProtectedRoute>
  );
}
