'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import FlowCanvas from '@/components/flows/FlowCanvas';
import FlowToolbar from '@/components/flows/FlowToolbar';
import NodePalette from '@/components/flows/NodePalette';
import PropertyPanel from '@/components/flows/PropertyPanel';
import FlowPropertiesPanel from '@/components/flows/FlowPropertiesPanel';
import { useFlowStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';

export default function FlowEditorPage() {
  const params = useParams();
  const router = useRouter();
  const isNew = params.id === 'new';
  const flowId = !isNew && params.id ? Number(params.id) : null;
  const { setCurrentFlow, currentFlow } = useFlowStore();
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [isPropertiesPanelOpen, setIsPropertiesPanelOpen] = useState(false);

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
    if (!currentFlow) return;

    // Update the node in the current flow
    const updatedNodes = currentFlow.nodes.map((node) =>
      node.id === nodeId ? { ...node, data } : node
    );

    setCurrentFlow({
      ...currentFlow,
      nodes: updatedNodes,
    });
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

    // Delete the flow from the backend
    if (!confirm('Are you sure you want to delete this workflow? This action cannot be undone.')) {
      return;
    }

    setLoading(true);
    try {
      await apiClient.delete(`/api/v1/flows/${flowId}`);
      setCurrentFlow(null);
      setSelectedNode(null);
      router.push('/flows');
    } catch (error) {
      console.error('Failed to delete flow:', error);
      alert('Failed to delete workflow. Please try again.');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="px-6 pt-4">
              <Breadcrumbs />
            </div>
            <div className="min-h-screen flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  if (!isNew && (!flowId || isNaN(flowId))) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="px-6 pt-4">
              <Breadcrumbs />
            </div>
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
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        {/* Keep menu visible for normal editing, hidden only during creation/loading */}
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="h-screen flex flex-col">
        <FlowToolbar
          flowId={flowId}
          onDiscard={handleDiscard}
          onOpenProperties={() => setIsPropertiesPanelOpen(true)}
        />

        <div className="flex-1 flex overflow-hidden">
          <NodePalette />

          <div className="flex-1">
            <FlowCanvas flowId={flowId} onNodeSelect={handleNodeSelect} />
          </div>

          <PropertyPanel
            selectedNode={selectedNode}
            onUpdateNode={handleUpdateNode}
            onClearSelection={() => setSelectedNode(null)}
          />
        </div>

        {/* Flow Properties Panel */}
        {currentFlow && flowId && (
          <FlowPropertiesPanel
            flowId={flowId}
            initialData={currentFlow}
            isOpen={isPropertiesPanelOpen}
            onClose={() => setIsPropertiesPanelOpen(false)}
          />
        )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
