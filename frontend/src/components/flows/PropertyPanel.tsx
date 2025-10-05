'use client';

import { useState, useEffect } from 'react';
import { useAgentStore, useCrewStore, useToolStore } from '@/lib/store';

interface PropertyPanelProps {
  selectedNode: any | null;
  onUpdateNode: (nodeId: string, data: any) => void;
}

export default function PropertyPanel({ selectedNode, onUpdateNode }: PropertyPanelProps) {
  const { agents } = useAgentStore();
  const { crews } = useCrewStore();
  const { tools } = useToolStore();

  const [nodeData, setNodeData] = useState<any>({});

  useEffect(() => {
    if (selectedNode) {
      setNodeData(selectedNode.data || {});
    }
  }, [selectedNode]);

  if (!selectedNode) {
    return (
      <div className="bg-white border-l border-gray-200 p-4 w-80">
        <div className="text-center text-gray-500 mt-8">
          <p className="text-sm">Select a node to view properties</p>
        </div>
      </div>
    );
  }

  const handleUpdate = (key: string, value: any) => {
    const updatedData = { ...nodeData, [key]: value };
    setNodeData(updatedData);
    onUpdateNode(selectedNode.id, updatedData);
  };

  const renderAgentProperties = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Select Agent
        </label>
        <select
          value={nodeData.agent_id || ''}
          onChange={(e) => handleUpdate('agent_id', Number(e.target.value))}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        >
          <option value="">Choose an agent...</option>
          {agents.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Node Label
        </label>
        <input
          type="text"
          value={nodeData.label || ''}
          onChange={(e) => handleUpdate('label', e.target.value)}
          placeholder="Agent Node"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>
    </div>
  );

  const renderCrewProperties = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Select Crew
        </label>
        <select
          value={nodeData.crew_id || ''}
          onChange={(e) => handleUpdate('crew_id', Number(e.target.value))}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        >
          <option value="">Choose a crew...</option>
          {crews.map((crew) => (
            <option key={crew.id} value={crew.id}>
              {crew.name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Node Label
        </label>
        <input
          type="text"
          value={nodeData.label || ''}
          onChange={(e) => handleUpdate('label', e.target.value)}
          placeholder="Crew Node"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>
    </div>
  );

  const renderToolProperties = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Select Tool
        </label>
        <select
          value={nodeData.tool_id || ''}
          onChange={(e) => handleUpdate('tool_id', Number(e.target.value))}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        >
          <option value="">Choose a tool...</option>
          {tools.map((tool) => (
            <option key={tool.id} value={tool.id}>
              {tool.name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Node Label
        </label>
        <input
          type="text"
          value={nodeData.label || ''}
          onChange={(e) => handleUpdate('label', e.target.value)}
          placeholder="Tool Node"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>
    </div>
  );

  const renderGenericProperties = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Node Label
        </label>
        <input
          type="text"
          value={nodeData.label || ''}
          onChange={(e) => handleUpdate('label', e.target.value)}
          placeholder="Node Label"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Configuration (JSON)
        </label>
        <textarea
          value={JSON.stringify(nodeData.config || {}, null, 2)}
          onChange={(e) => {
            try {
              const config = JSON.parse(e.target.value);
              handleUpdate('config', config);
            } catch (err) {
              // Invalid JSON, ignore
            }
          }}
          rows={6}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none focus:ring-blue-500"
        />
      </div>
    </div>
  );

  return (
    <div className="bg-white border-l border-gray-200 p-4 w-80 overflow-y-auto">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Node Properties
      </h3>

      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
        <p className="text-sm font-medium text-gray-700">
          Type: <span className="text-blue-600">{selectedNode.type}</span>
        </p>
        <p className="text-xs text-gray-500 mt-1">
          ID: {selectedNode.id}
        </p>
      </div>

      {selectedNode.type === 'agent' && renderAgentProperties()}
      {selectedNode.type === 'crew' && renderCrewProperties()}
      {selectedNode.type === 'tool' && renderToolProperties()}
      {!['agent', 'crew', 'tool'].includes(selectedNode.type) && renderGenericProperties()}
    </div>
  );
}
