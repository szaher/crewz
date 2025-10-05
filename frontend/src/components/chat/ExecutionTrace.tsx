'use client';

import { useState } from 'react';

interface ToolInvocation {
  tool_id: string;
  tool_name?: string;
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  duration_ms?: number;
}

interface ExecutionTraceProps {
  toolInvocations: ToolInvocation[];
}

export default function ExecutionTrace({ toolInvocations }: ExecutionTraceProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const toggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium opacity-75">Tool Invocations:</p>

      {toolInvocations.map((invocation, index) => (
        <div
          key={index}
          className="bg-white bg-opacity-50 rounded border border-gray-300 overflow-hidden"
        >
          {/* Header */}
          <button
            onClick={() => toggleExpand(index)}
            className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-gray-50 hover:bg-opacity-50"
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900">
                🔧 {invocation.tool_name || `Tool ${invocation.tool_id}`}
              </span>
              {invocation.duration_ms && (
                <span className="text-xs text-gray-500">
                  ({invocation.duration_ms}ms)
                </span>
              )}
            </div>
            <svg
              className={`w-4 h-4 transform transition-transform ${
                expandedIndex === index ? 'rotate-180' : ''
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Expanded Details */}
          {expandedIndex === index && (
            <div className="px-3 py-2 space-y-2 border-t border-gray-300">
              {/* Inputs */}
              <div>
                <p className="text-xs font-medium text-gray-700 mb-1">Inputs:</p>
                <pre className="text-xs bg-gray-100 rounded p-2 overflow-x-auto">
                  {JSON.stringify(invocation.inputs, null, 2)}
                </pre>
              </div>

              {/* Outputs */}
              <div>
                <p className="text-xs font-medium text-gray-700 mb-1">Outputs:</p>
                <pre className="text-xs bg-gray-100 rounded p-2 overflow-x-auto">
                  {JSON.stringify(invocation.outputs, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
