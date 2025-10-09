'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';

interface TaskTemplate {
  name: string;
  description: string;
  expected_output: string;
  order: number;
  async_execution: boolean;
  output_format: string;
}

interface Workflow {
  name: string;
  tasks: TaskTemplate[];
}

interface TaskTemplateSelectorProps {
  crewId: number;
  agentIds?: number[];
  onTasksCreated: () => void;
}

export default function TaskTemplateSelector({ crewId, agentIds = [], onTasksCreated }: TaskTemplateSelectorProps) {
  const [templates, setTemplates] = useState<TaskTemplate[]>([]);
  const [workflows, setWorkflows] = useState<Record<string, TaskTemplate[]>>({});
  const [loading, setLoading] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const [templatesRes, workflowsRes] = await Promise.all([
        apiClient.get<TaskTemplate[]>('/api/v1/tasks/templates'),
        apiClient.get<Record<string, TaskTemplate[]>>('/api/v1/tasks/templates/workflows'),
      ]);

      if (templatesRes.data) {
        setTemplates(templatesRes.data);
      }
      if (workflowsRes.data) {
        setWorkflows(workflowsRes.data);
      }
    } catch (error) {
      console.error('Failed to fetch templates:', error);
    }
  };

  const createFromTemplate = async (templateName: string, agentId?: number) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('template_name', templateName);
      if (agentId) {
        params.append('agent_id', agentId.toString());
      }

      const response = await apiClient.post(
        `/api/v1/tasks/crew/${crewId}/from-template?${params.toString()}`,
        {}
      );

      if (response.data) {
        onTasksCreated();
        setShowTemplates(false);
      }
    } catch (error) {
      console.error('Failed to create task from template:', error);
      alert('Failed to create task from template');
    } finally {
      setLoading(false);
    }
  };

  const createFromWorkflow = async (workflowName: string) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('workflow_name', workflowName);
      if (agentIds.length > 0) {
        agentIds.forEach(id => params.append('agent_ids', id.toString()));
      }

      const response = await apiClient.post(
        `/api/v1/tasks/crew/${crewId}/from-workflow?${params.toString()}`,
        {}
      );

      if (response.data) {
        onTasksCreated();
        setShowTemplates(false);
      }
    } catch (error) {
      console.error('Failed to create tasks from workflow:', error);
      alert('Failed to create tasks from workflow');
    } finally {
      setLoading(false);
    }
  };

  const workflowDisplayNames: Record<string, string> = {
    research_and_report: 'Research & Report',
    code_development: 'Code Development',
    data_pipeline: 'Data Pipeline',
    content_creation: 'Content Creation',
  };

  const templateNames: Record<string, string> = {
    'Research Task': 'research',
    'Analysis Task': 'analysis',
    'Writing Task': 'writing',
    'Code Generation Task': 'code',
    'Review Task': 'review',
    'Planning Task': 'planning',
    'Data Extraction Task': 'data_extraction',
    'Summarization Task': 'summarization',
  };

  if (!showTemplates) {
    return (
      <button
        onClick={() => setShowTemplates(true)}
        className="px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
      >
        📋 Use Template
      </button>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Task Templates</h3>
        <button
          onClick={() => setShowTemplates(false)}
          className="text-gray-400 hover:text-gray-500"
        >
          ✕
        </button>
      </div>

      {/* Workflows */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Complete Workflows</h4>
        <p className="text-xs text-gray-500 mb-3">
          Create multiple tasks that work together as a complete workflow
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(workflows).map(([key, tasks]) => (
            <div
              key={key}
              className="border border-gray-200 rounded-lg p-3 hover:border-blue-300 hover:bg-blue-50 cursor-pointer transition-colors"
              onClick={() => !loading && createFromWorkflow(key)}
            >
              <div className="flex items-center justify-between mb-2">
                <h5 className="font-medium text-gray-900">
                  {workflowDisplayNames[key] || key}
                </h5>
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                  {tasks.length} tasks
                </span>
              </div>
              <p className="text-xs text-gray-600">
                {tasks.map(t => t.name.replace(' Task', '')).join(' → ')}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Individual Templates */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">Individual Task Templates</h4>
        <p className="text-xs text-gray-500 mb-3">
          Create a single task from a template
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {templates.map((template) => (
            <button
              key={template.name}
              onClick={() => !loading && createFromTemplate(templateNames[template.name])}
              disabled={loading}
              className="text-left border border-gray-200 rounded-lg p-3 hover:border-blue-300 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <h5 className="font-medium text-gray-900 text-sm mb-1">{template.name}</h5>
              <p className="text-xs text-gray-600 line-clamp-2">{template.description}</p>
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="mt-4 flex items-center justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-sm text-gray-600">Creating tasks...</span>
        </div>
      )}
    </div>
  );
}
