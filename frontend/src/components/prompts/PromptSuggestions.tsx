'use client';

import { useState, useEffect } from 'react';
import { suggestionApi, type PromptSuggestionItem } from '@/lib/api/prompts';

interface PromptSuggestionsProps {
  context: 'agent' | 'crew' | 'task' | 'flow';
  contextData: {
    name: string;
    role?: string;
    goal?: string;
    backstory?: string;
    description?: string;
    processType?: string;
    expectedOutput?: string;
  };
  onSelect?: (suggestion: PromptSuggestionItem) => void;
  limit?: number;
  minConfidence?: number;
}

export default function PromptSuggestions({
  context,
  contextData,
  onSelect,
  limit = 5,
  minConfidence = 0.1,
}: PromptSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<PromptSuggestionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    // Only fetch if we have enough context data
    if (!contextData.name || (!contextData.role && !contextData.description)) {
      setSuggestions([]);
      return;
    }

    fetchSuggestions();
  }, [
    context,
    contextData.name,
    contextData.role,
    contextData.goal,
    contextData.description,
    contextData.processType,
  ]);

  const fetchSuggestions = async () => {
    setLoading(true);
    setError(null);

    try {
      let response;

      switch (context) {
        case 'agent':
          response = await suggestionApi.suggestForAgent(
            contextData.name,
            contextData.role || '',
            contextData.goal || '',
            contextData.backstory,
            limit,
            minConfidence
          );
          break;

        case 'crew':
          response = await suggestionApi.suggestForCrew(
            contextData.name,
            contextData.description || '',
            contextData.processType || 'sequential',
            limit,
            minConfidence
          );
          break;

        case 'task':
          response = await suggestionApi.suggestForTask(
            contextData.name,
            contextData.description || '',
            contextData.expectedOutput,
            limit,
            minConfidence
          );
          break;

        case 'flow':
          response = await suggestionApi.suggestForFlow(
            contextData.name,
            contextData.description || '',
            limit,
            minConfidence
          );
          break;

        default:
          throw new Error(`Unknown context: ${context}`);
      }

      if (response.error) {
        throw new Error(response.error);
      }

      setSuggestions(response.data?.suggestions || []);
    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch suggestions');
    } finally {
      setLoading(false);
    }
  };

  const renderConfidenceBar = (confidence: number) => {
    const percentage = Math.round(confidence * 100);
    let colorClass = 'bg-gray-400';

    if (confidence >= 0.7) {
      colorClass = 'bg-green-500';
    } else if (confidence >= 0.4) {
      colorClass = 'bg-yellow-500';
    } else if (confidence >= 0.2) {
      colorClass = 'bg-orange-500';
    }

    return (
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full ${colorClass} transition-all`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    );
  };

  const renderStars = (rating: number) => {
    return (
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <span
            key={star}
            className={`text-xs ${
              star <= rating ? 'text-yellow-400' : 'text-gray-300'
            }`}
          >
            ★
          </span>
        ))}
      </div>
    );
  };

  if (!suggestions.length && !loading && !error) {
    return null;
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">💡</span>
          <div>
            <h3 className="text-sm font-medium text-blue-900">
              Suggested Prompts
            </h3>
            <p className="text-xs text-blue-700">
              Based on your {context} configuration
            </p>
          </div>
        </div>
        {suggestions.length > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-blue-600 hover:text-blue-700"
          >
            {expanded ? 'Hide' : 'Show'} {suggestions.length}
          </button>
        )}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
        </div>
      )}

      {error && (
        <div className="text-sm text-red-600 py-2">
          {error}
        </div>
      )}

      {expanded && suggestions.length > 0 && (
        <div className="space-y-3 mt-3">
          {suggestions.map((suggestion) => (
            <div
              key={suggestion.prompt_id}
              className="bg-white p-3 rounded-md border border-blue-100 hover:border-blue-300 transition-colors"
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex-1">
                  <h4 className="text-sm font-medium text-gray-900">
                    {suggestion.name}
                  </h4>
                  {suggestion.description && (
                    <p className="text-xs text-gray-600 mt-1">
                      {suggestion.description}
                    </p>
                  )}
                </div>
                {onSelect && (
                  <button
                    onClick={() => onSelect(suggestion)}
                    className="px-3 py-1 text-xs font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100 whitespace-nowrap"
                  >
                    Use This
                  </button>
                )}
              </div>

              <div className="space-y-2">
                {/* Confidence */}
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-gray-600">Confidence</span>
                    <span className="font-medium text-gray-900">
                      {Math.round(suggestion.confidence * 100)}%
                    </span>
                  </div>
                  {renderConfidenceBar(suggestion.confidence)}
                </div>

                {/* Reason */}
                <div className="text-xs text-gray-600">
                  <span className="font-medium">Why: </span>
                  {suggestion.reason}
                </div>

                {/* Metadata */}
                <div className="flex items-center gap-3 text-xs">
                  {renderStars(Math.round(suggestion.average_rating))}
                  <span className="text-gray-500">
                    {suggestion.total_executions} uses
                  </span>
                  <code className="text-purple-600 bg-purple-50 px-2 py-0.5 rounded">
                    /{suggestion.slug}
                  </code>
                </div>

                {/* Tags */}
                {suggestion.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {suggestion.tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                    {suggestion.tags.length > 3 && (
                      <span className="text-xs text-gray-500">
                        +{suggestion.tags.length - 3}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {!expanded && suggestions.length > 0 && (
        <div className="text-xs text-blue-600 mt-2">
          Click "Show {suggestions.length}" to view suggestions
        </div>
      )}
    </div>
  );
}
