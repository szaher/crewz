import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function ToolNode({ data, selected }: NodeProps) {
  return (
    <div className={`
      px-4 py-3 shadow-md rounded-lg border-2 bg-purple-50 min-w-[200px]
      ${selected ? 'border-purple-500' : 'border-purple-300'}
    `}>
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-purple-500" />

      <div className="flex items-center gap-2">
        <span className="text-2xl">🔧</span>
        <div className="flex-1">
          <div className="font-semibold text-gray-900">{data.label || 'Tool'}</div>
          {data.tool_id && (
            <div className="text-xs text-gray-500">ID: {data.tool_id}</div>
          )}
        </div>
      </div>

      {data.inputs && (
        <div className="mt-2 text-xs text-gray-600">
          {Object.keys(data.inputs).length} input(s)
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-purple-500" />
    </div>
  );
});
