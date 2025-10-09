import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function ConditionNode({ data, selected }: NodeProps) {
  return (
    <div
      className={`
        px-4 py-3 shadow-lg rounded-2xl border-2 bg-gradient-to-br from-yellow-50 to-amber-100 dark:from-amber-900/20 dark:to-amber-900/10 min-w-[260px] max-w-none overflow-auto ${data?.__ui?.readOnly ? '' : 'resize-x'}
        ${selected ? 'border-yellow-600 ring-2 ring-yellow-200' : 'border-yellow-400 dark:border-amber-700'}
      `}
      style={data?.width ? { width: data.width } : undefined}
    >
      <Handle type="target" position={Position.Top} className="w-4 h-4 bg-yellow-500 border-2 border-white shadow-md" />

      <div className="flex items-center gap-2">
        <span className="text-2xl">🔀</span>
        <div className="flex-1">
          <div className="font-semibold text-gray-900">{data.label || 'Condition'}</div>
        </div>
      </div>

      {data.expression && (
        <div className="mt-2 text-xs font-mono text-gray-600 truncate">
          {data.expression}
        </div>
      )}

      <div className="flex justify-between mt-2">
        <Handle
          type="source"
          position={Position.Bottom}
          id="true"
          className="w-4 h-4 bg-green-500 border-2 border-white shadow-md"
          style={{ left: '30%' }}
        />
        <Handle
          type="source"
          position={Position.Bottom}
          id="false"
          className="w-4 h-4 bg-red-500 border-2 border-white shadow-md"
          style={{ left: '70%' }}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-500 mt-1">
        <span className="ml-2">True</span>
        <span className="mr-2">False</span>
      </div>
    </div>
  );
});
