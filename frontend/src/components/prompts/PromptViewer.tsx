'use client';

import { useState, useEffect } from 'react';
import { promptApi } from '@/lib/api/prompts';
import type { PromptTemplate } from '@/lib/store';

interface PromptViewerProps {
  promptId: string;
  onEdit?: () => void;
  onDelete?: () => void;
}

export default function PromptViewer({ promptId, onEdit, onDelete }: PromptViewerProps) {
  const [prompt, setPrompt] = useState<PromptTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'execute' | 'rating'>('overview');

  // Execute state
  const [variables, setVariables] = useState<Record<string, any>>({});
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<string | null>(null);

  // Rating state
  const [userRating, setUserRating] = useState<number>(0);
  const [hoveredRating, setHoveredRating] = useState<number>(0);

  useEffect(() => {
    loadPrompt();
  }, [promptId]);

  const loadPrompt = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await promptApi.get(promptId);
      if (response.error) throw new Error(response.error);

      setPrompt(response.data!);

      // Initialize variables with defaults
      const defaultVars: Record<string, any> = {};
      response.data!.variables?.forEach(v => {
        if (v.default) {
          defaultVars[v.name] = v.default;
        }
      });
      setVariables(defaultVars);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompt');
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!prompt) return;

    setExecuting(true);
    setExecutionResult(null);
    try {
      const response = await promptApi.execute(promptId, {
        variables,
        context_type: 'direct',
      });

      if (response.error) throw new Error(response.error);
      setExecutionResult(response.data!.rendered_content);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to execute prompt');
    } finally {
      setExecuting(false);
    }
  };

  const handleRate = async (rating: number) => {
    try {
      const response = await promptApi.rate(promptId, rating);
      if (response.error) throw new Error(response.error);

      setUserRating(rating);
      // Reload to get updated average
      loadPrompt();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to submit rating');
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this prompt?')) return;

    try {
      const response = await promptApi.delete(promptId);
      if (response.error) throw new Error(response.error);

      if (onDelete) {
        onDelete();
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete prompt');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !prompt) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <p className="text-red-600">{error || 'Prompt not found'}</p>
      </div>
    );
  }

  const renderStars = (rating: number, interactive: boolean = false) => {
    return (
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            disabled={!interactive}
            onClick={() => interactive && handleRate(star)}
            onMouseEnter={() => interactive && setHoveredRating(star)}
            onMouseLeave={() => interactive && setHoveredRating(0)}
            className={`text-2xl ${interactive ? 'cursor-pointer' : 'cursor-default'} ${
              star <= (interactive ? (hoveredRating || userRating) : rating)
                ? 'text-yellow-400'
                : 'text-gray-300'
            }`}
          >
            ★
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">{prompt.name}</h1>
              {prompt.is_command_enabled && (
                <span className="text-sm bg-purple-100 text-purple-700 px-3 py-1 rounded">
                  /{prompt.slug}
                </span>
              )}
              {prompt.is_public && (
                <span className="text-sm bg-green-100 text-green-700 px-3 py-1 rounded">
                  Public
                </span>
              )}
            </div>
            {prompt.description && (
              <p className="text-gray-600 mb-4">{prompt.description}</p>
            )}

            {/* Tags */}
            {prompt.tags && prompt.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {prompt.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* Stats */}
            <div className="flex items-center gap-6 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                {renderStars(Math.round(prompt.average_rating))}
                <span>({prompt.total_ratings} ratings)</span>
              </div>
              <span>🔄 {prompt.total_executions} executions</span>
            </div>
          </div>

          <div className="flex gap-2">
            {onEdit && (
              <button
                onClick={onEdit}
                className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
              >
                Edit
              </button>
            )}
            <button
              onClick={handleDelete}
              className="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100"
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="border-b border-gray-200">
          <div className="flex gap-4 px-6">
            {(['overview', 'execute', 'rating'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">Content</h3>
                <div className="bg-gray-50 p-4 rounded-md">
                  <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono">
                    {prompt.content}
                  </pre>
                </div>
              </div>

              {prompt.variables && prompt.variables.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Variables</h3>
                  <div className="space-y-3">
                    {prompt.variables.map((variable) => (
                      <div key={variable.name} className="border border-gray-200 rounded-md p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <code className="text-sm font-medium text-blue-600">
                            {'{' + variable.name + '}'}
                          </code>
                          {variable.required && (
                            <span className="text-xs text-red-600">Required</span>
                          )}
                        </div>
                        {variable.description && (
                          <p className="text-sm text-gray-600">{variable.description}</p>
                        )}
                        {variable.default && (
                          <p className="text-xs text-gray-500 mt-1">
                            Default: {variable.default}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {prompt.suggested_model && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Suggested Model</h3>
                  <p className="text-sm text-gray-600">{prompt.suggested_model}</p>
                </div>
              )}

              {prompt.model_parameters && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Model Parameters</h3>
                  <div className="grid grid-cols-2 gap-4">
                    {Object.entries(prompt.model_parameters).map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-gray-600">{key}:</span>
                        <span className="font-medium text-gray-900">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Execute Tab */}
          {activeTab === 'execute' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Execute Prompt</h3>

                {prompt.variables && prompt.variables.length > 0 ? (
                  <div className="space-y-4 mb-6">
                    {prompt.variables.map((variable) => (
                      <div key={variable.name}>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {variable.name}
                          {variable.required && <span className="text-red-600 ml-1">*</span>}
                        </label>
                        {variable.description && (
                          <p className="text-xs text-gray-500 mb-1">{variable.description}</p>
                        )}
                        <input
                          type="text"
                          value={variables[variable.name] || ''}
                          onChange={(e) => setVariables({ ...variables, [variable.name]: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder={variable.default || `Enter ${variable.name}...`}
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-600 mb-6">This prompt has no variables to configure.</p>
                )}

                <button
                  onClick={handleExecute}
                  disabled={executing}
                  className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {executing ? 'Executing...' : 'Execute'}
                </button>
              </div>

              {executionResult && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Result</h3>
                  <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
                    <pre className="text-sm text-gray-800 whitespace-pre-wrap">
                      {executionResult}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Rating Tab */}
          {activeTab === 'rating' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">Rate This Prompt</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Help others by rating the quality and usefulness of this prompt
                </p>
                <div className="flex items-center gap-4">
                  {renderStars(userRating, true)}
                  {userRating > 0 && (
                    <span className="text-sm text-gray-600">
                      You rated: {userRating} star{userRating !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              </div>

              <div className="border-t border-gray-200 pt-6">
                <h3 className="text-lg font-medium text-gray-900 mb-2">Overall Rating</h3>
                <div className="flex items-center gap-3">
                  {renderStars(Math.round(prompt.average_rating))}
                  <span className="text-lg font-medium text-gray-900">
                    {prompt.average_rating.toFixed(1)}
                  </span>
                  <span className="text-sm text-gray-600">
                    ({prompt.total_ratings} rating{prompt.total_ratings !== 1 ? 's' : ''})
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
