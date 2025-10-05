import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function LLMNode({ data, selected }: NodeProps) {
  return (
    <div className={`
      px-4 py-3 shadow-md rounded-lg border-2 bg-green-50 min-w-[200px]
      ${selected ? 'border-green-500' : 'border-green-300'}
    `}>
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-green-500" />

      <div className="flex items-center gap-2">
        <span className="text-2xl">🧠</span>
        <div className="flex-1">
          <div className="font-semibold text-gray-900">{data.label || 'LLM'}</div>
          {data.llm_provider_id && (
            <div className="text-xs text-gray-500">Provider: {data.llm_provider_id}</div>
          )}
        </div>
      </div>

      {data.prompt && (
        <div className="mt-2 text-xs text-gray-600 truncate max-w-[180px]">
          {data.prompt}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-green-500" />
    </div>
  );
});
