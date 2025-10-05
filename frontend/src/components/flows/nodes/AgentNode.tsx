import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function AgentNode({ data, selected }: NodeProps) {
  return (
    <div className={`
      px-4 py-3 shadow-md rounded-lg border-2 bg-white min-w-[200px]
      ${selected ? 'border-blue-500' : 'border-gray-300'}
    `}>
      <Handle type="target" position={Position.Top} className="w-3 h-3" />

      <div className="flex items-center gap-2">
        <span className="text-2xl">🤖</span>
        <div className="flex-1">
          <div className="font-semibold text-gray-900">{data.label || 'Agent'}</div>
          {data.agent_id && (
            <div className="text-xs text-gray-500">ID: {data.agent_id}</div>
          )}
        </div>
      </div>

      {data.config && Object.keys(data.config).length > 0 && (
        <div className="mt-2 text-xs text-gray-600">
          {Object.keys(data.config).length} config(s)
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
    </div>
  );
});
