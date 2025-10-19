'use client';

import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import FlowFormBuilder from '@/components/flows/FlowFormBuilder';
import { convertStepsToNodesAndEdges } from '@/lib/utils/flowConverter';
import { apiClient } from '@/lib/api-client';

export default function NewFlowPage() {
  const router = useRouter();

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

    // Create flow payload with metadata indicating form creation
    const flowPayload = {
      name: formData.name,
      description: formData.description,
      nodes,
      edges,
      variables: variables, // Only use inferred variables, not merged with formData.variables
      config: {
        created_with: 'form', // Track creation method
        steps: formData.steps, // Store original step data for form editing
      },
    };

    // Submit to API
    const response = await apiClient.post('/api/v1/flows', flowPayload);

    if (response.error) {
      throw new Error(response.error);
    }

    // Navigate back to flows list
    router.push('/flows');
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto p-6">
            <Breadcrumbs />
            <h1 className="text-3xl font-bold text-gray-900 mb-6">
              Create New Flow
            </h1>
            <p className="text-sm text-gray-600 mb-6">
              Build your flow by adding steps sequentially. Each step can be an agent or tool.
            </p>
            <FlowFormBuilder
              onSubmit={handleSubmit}
              onCancel={() => router.push('/flows')}
            />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
