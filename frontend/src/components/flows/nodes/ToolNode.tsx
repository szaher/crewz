import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function ToolNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 shadow-lg rounded-2xl border-2 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-900/10 min-w-[260px] max-w-none overflow-auto ${data?.__ui?.readOnly ? '' : 'resize-x'}
        ${selected ? 'border-purple-600 ring-2 ring-purple-200' : 'border-purple-400 dark:border-purple-700'}
      `}
      style={data?.width ? { width: data.width } : undefined}
    >
      <Handle type="target" position={Position.Top} className="w-4 h-4 bg-purple-500 border-2 border-white shadow-md" />

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

      <Handle type="source" position={Position.Bottom} className="w-4 h-4 bg-purple-500 border-2 border-white shadow-md" />
    </div>
  );
});
