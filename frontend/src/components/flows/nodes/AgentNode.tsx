import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function AgentNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 shadow-lg rounded-2xl border-2 bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 min-w-[260px] max-w-none overflow-auto ${data?.__ui?.readOnly ? '' : 'resize-x'}
        ${selected ? 'border-blue-600 ring-2 ring-blue-200' : 'border-gray-400 dark:border-gray-600'}
      `}
      style={data?.width ? { width: data.width } : undefined}
    >
      <Handle type="target" position={Position.Top} className="w-4 h-4 bg-gray-500 border-2 border-white shadow-md" />

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

      <Handle type="source" position={Position.Bottom} className="w-4 h-4 bg-gray-500 border-2 border-white shadow-md" />
    </div>
  );
});
