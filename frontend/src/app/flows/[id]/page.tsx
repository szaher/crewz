'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import FlowCanvas from '@/components/flows/FlowCanvas';
import FlowToolbar from '@/components/flows/FlowToolbar';
import NodePalette from '@/components/flows/NodePalette';
import PropertyPanel from '@/components/flows/PropertyPanel';
import { useFlowStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';

export default function FlowEditorPage() {
  const params = useParams();
  const router = useRouter();
  const isNew = params.id === 'new';
  const flowId = !isNew && params.id ? Number(params.id) : null;
  const { setCurrentFlow } = useFlowStore();
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    // Handle /flows/new - create a new flow
    if (isNew && !creating) {
      setCreating(true);
      const createNewFlow = async () => {
        try {
          const response = await apiClient.post('/api/v1/flows', {
            name: 'New Flow',
            description: 'A new workflow',
            nodes: [],
            edges: [],
            tags: [],
          });

          const newFlowId = response.data?.id || response.id;
          if (newFlowId) {
            // Redirect to the actual flow ID
            router.replace(`/flows/${newFlowId}`);
          } else {
            console.error('No flow ID in response:', response);
            setLoading(false);
          }
        } catch (error) {
          console.error('Failed to create flow:', error);
          setLoading(false);
        }
      };

      createNewFlow();
      return;
    }

    // Don't load if flowId is invalid
    if (!flowId || isNaN(flowId)) {
      setLoading(false);
      return;
    }

    const loadFlow = async () => {
      try {
        const response = await apiClient.get(`/api/v1/flows/${flowId}`);
        if (response.data) {
          setCurrentFlow(response.data);
        }
      } catch (error) {
        console.error('Failed to load flow:', error);
      } finally {
        setLoading(false);
      }
    };

    loadFlow();
  }, [flowId, isNew, creating, setCurrentFlow, router]);

  const handleUpdateNode = (nodeId: string, data: any) => {
    // Node updates are handled by FlowCanvas and PropertyPanel
    console.log('Node updated:', nodeId, data);
  };

  const handleNodeSelect = (node: any) => {
    setSelectedNode(node);
  };

  const handleDiscard = async () => {
    if (!flowId) {
      // If no flow ID, just navigate back
      setCurrentFlow(null);
      setSelectedNode(null);
      router.push('/flows');
      return;
    }

    // Reload the flow from the backend to discard local changes
    setLoading(true);
    try {
      const response = await apiClient.get(`/api/v1/flows/${flowId}`);
      if (response.data) {
        setCurrentFlow(response.data);
        setSelectedNode(null);
      }
    } catch (error) {
      console.error('Failed to reload flow:', error);
      // If reload fails, navigate away
      router.push('/flows');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </ProtectedRoute>
    );
  }

  if (!isNew && (!flowId || isNaN(flowId))) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Invalid Flow ID</h1>
            <p className="text-gray-600">The flow ID in the URL is invalid.</p>
            <button
              onClick={() => router.push('/flows')}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Back to Flows
            </button>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="h-screen flex flex-col">
        <FlowToolbar flowId={flowId} onDiscard={handleDiscard} />

        <div className="flex-1 flex overflow-hidden">
          <NodePalette />

          <div className="flex-1">
            <FlowCanvas flowId={flowId} onNodeSelect={handleNodeSelect} />
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
