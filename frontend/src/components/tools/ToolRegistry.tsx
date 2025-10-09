'use client';

import { useState } from 'react';
import type { Tool } from '@/types/api';
import ToolExecuteModal from './ToolExecuteModal';

interface ToolRegistryProps {
  tools: Tool[];
  onEditTool: (toolId: number) => void;
  onCreateTool: () => void;
}

export default function ToolRegistry({ tools, onEditTool, onCreateTool }: ToolRegistryProps) {
  const [executingTool, setExecutingTool] = useState<Tool | null>(null);

  const getToolTypeIcon = (toolType: string) => {
    switch (toolType) {
      case 'function': return '⚙️';
      case 'api': return '🌐';
      case 'docker': return '🐳';
      default: return '🔧';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">
          Tool Registry ({tools.length} tools)
        </h2>
        <button
          onClick={onCreateTool}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
        >
          Create Tool
        </button>
      </div>

      {tools.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">No tools registered yet</p>
          <button
            onClick={onCreateTool}
            className="mt-4 text-blue-600 hover:text-blue-700 text-sm font-medium"
          >
            Create your first tool →
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tools.map((tool) => (
            <div
              key={tool.id}
              className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{getToolTypeIcon(tool.tool_type)}</span>
                  <h3 className="text-lg font-semibold text-gray-900">{tool.name}</h3>
                </div>
                <span className={`
                  px-2 py-1 text-xs font-medium rounded
                  ${tool.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}
                `}>
                  {tool.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>

              <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                {tool.description}
              </p>

              <div className="space-y-2 mb-4">
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span className="font-medium">Type:</span>
                  <span className="px-2 py-1 rounded bg-purple-100 text-purple-800">{tool.tool_type}</span>
                </div>

                {tool.docker_image && (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="font-medium">Image:</span>
                    <code className="px-2 py-1 rounded bg-gray-100 font-mono">{tool.docker_image}</code>
                  </div>
                )}

                {tool.api_endpoint && (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="font-medium">Endpoint:</span>
                    <code className="px-2 py-1 rounded bg-gray-100 font-mono truncate">{tool.api_endpoint}</code>
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setExecutingTool(tool)}
                  className="flex-1 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
                >
                  ▶ Execute
                </button>
                <button
                  onClick={() => onEditTool(tool.id)}
                  className="flex-1 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
                >
                  Edit
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Execute Modal */}
      {executingTool && (
        <ToolExecuteModal
          tool={executingTool}
          isOpen={!!executingTool}
          onClose={() => setExecutingTool(null)}
        />
      )}
    </div>
  );
}
