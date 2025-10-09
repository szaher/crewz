import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function LLMNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 shadow-lg rounded-2xl border-2 bg-gradient-to-br from-green-50 to-emerald-100 dark:from-emerald-900/20 dark:to-emerald-900/10 min-w-[260px] max-w-none overflow-auto ${data?.__ui?.readOnly ? '' : 'resize-x'}
        ${selected ? 'border-green-600 ring-2 ring-green-200' : 'border-green-400 dark:border-green-700'}
      `}
      style={data?.width ? { width: data.width } : undefined}
    >
      <Handle type="target" position={Position.Top} className="w-4 h-4 bg-green-500 border-2 border-white shadow-md" />

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
        <div className="mt-2 text-xs text-gray-600 truncate">
          {data.prompt}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-4 h-4 bg-green-500 border-2 border-white shadow-md" />
    </div>
  );
});
