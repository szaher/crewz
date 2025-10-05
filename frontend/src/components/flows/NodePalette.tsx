'use client';

import { DragEvent } from 'react';

interface NodeType {
  type: string;
  label: string;
  icon: string;
  description: string;
}

const nodeTypes: NodeType[] = [
  { type: 'agent', label: 'Agent', icon: '🤖', description: 'AI agent node' },
  { type: 'crew', label: 'Crew', icon: '👥', description: 'Agent crew node' },
  { type: 'tool', label: 'Tool', icon: '🔧', description: 'Tool execution node' },
  { type: 'input', label: 'Input', icon: '📥', description: 'Flow input node' },
  { type: 'output', label: 'Output', icon: '📤', description: 'Flow output node' },
  { type: 'decision', label: 'Decision', icon: '🔀', description: 'Conditional branch' },
];

export default function NodePalette() {
  const onDragStart = (event: DragEvent<HTMLDivElement>, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="bg-white border-r border-gray-200 p-4 w-64 overflow-y-auto">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Node Palette</h3>

      <div className="space-y-2">
        {nodeTypes.map((nodeType) => (
          <div
            key={nodeType.type}
            draggable
            onDragStart={(e) => onDragStart(e, nodeType.type)}
            className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200 cursor-move hover:bg-gray-100 hover:border-blue-300 transition-colors"
          >
            <span className="text-2xl">{nodeType.icon}</span>
            <div className="flex-1">
              <p className="font-medium text-gray-900 text-sm">{nodeType.label}</p>
              <p className="text-xs text-gray-500">{nodeType.description}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-3 bg-blue-50 rounded-lg border border-blue-200">
        <p className="text-xs text-blue-800">
          Drag nodes onto the canvas to build your flow. Connect them to create a workflow.
        </p>
      </div>
    </div>
  );
}
