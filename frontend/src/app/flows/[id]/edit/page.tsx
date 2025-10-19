'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import FlowFormBuilder from '@/components/flows/FlowFormBuilder';
import { convertNodesToSteps, convertStepsToNodesAndEdges } from '@/lib/utils/flowConverter';
import { apiClient } from '@/lib/api-client';

export default function FlowEditPage() {
  const params = useParams();
  const router = useRouter();
  const flowId = params.id as string;

  const [flow, setFlow] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadFlow = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get(`/api/v1/flows/${flowId}`);
        if (response.data) {
          setFlow(response.data);
        } else {
          setError('Flow not found');
        }
      } catch (err) {
        console.error('Failed to load flow:', err);
        setError('Failed to load flow');
      } finally {
        setLoading(false);
      }
    };

    loadFlow();
  }, [flowId]);

  const handleSubmit = async (formData: any) => {
    // Convert steps to nodes and edges
    const { nodes, edges } = convertStepsToNodesAndEdges(formData.steps);

    // Infer input variables from agent task descriptions ONLY
    // DO NOT create variables from step names or crew names
    const variables: Record<string, any> = {};
    formData.steps.forEach((step: any) => {
      // Only extract variables from agent task descriptions that use {variable} syntax
      if (step.type === 'agent' && step.task_description) {
        const variableMatches = step.task_description.match(/\{(\w+)\}/g);
        if (variableMatches) {
          variableMatches.forEach((match: string) => {
            const varName = match.replace(/\{|\}/g, '');
            variables[varName] = '';
          });
        }
      }
      // For crew/tool/flow steps: variables will be extracted at execution time
      // from the actual crew tasks, not from step names
    });

    // Update flow payload
    const flowPayload = {
      name: formData.name,
      description: formData.description,
      nodes,
      edges,
      variables: variables, // Only use inferred variables
      config: {
        created_with: 'form',
        steps: formData.steps,
      },
    };

    // Submit to API
    const response = await apiClient.put(`/api/v1/flows/${flowId}`, flowPayload);

    if (response.error) {
      throw new Error(response.error);
    }

    // Navigate back to flows list
    router.push('/flows');
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

  if (error || !flow) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-4xl mx-auto p-6">
              <Breadcrumbs />
              <div className="flex flex-col items-center justify-center py-12">
                <div className="text-center max-w-md">
                  <p className="text-red-600 mb-4">{error || 'Flow not found'}</p>
                  <button
                    onClick={() => router.push('/flows')}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Back to Flows
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  // Convert nodes/edges back to steps for editing
  const initialSteps = flow.config?.steps || convertNodesToSteps(flow.nodes || [], flow.edges || []);

  const initialData = {
    name: flow.name,
    description: flow.description,
    steps: initialSteps,
    variables: flow.variables || {},
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto p-6">
            <Breadcrumbs />
            <h1 className="text-3xl font-bold text-gray-900 mb-6">
              Edit Flow: {flow.name}
            </h1>
            <p className="text-sm text-gray-600 mb-6">
              Update your flow configuration using the form builder.
            </p>
            <FlowFormBuilder
              initialData={initialData}
              onSubmit={handleSubmit}
              onCancel={() => router.push('/flows')}
            />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
