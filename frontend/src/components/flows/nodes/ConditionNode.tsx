import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function ConditionNode({ data, selected }: NodeProps) {
  return (
    <div className={`
      px-4 py-3 shadow-md rounded-lg border-2 bg-yellow-50 min-w-[200px]
      ${selected ? 'border-yellow-500' : 'border-yellow-300'}
    `}>
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-yellow-500" />

      <div className="flex items-center gap-2">
        <span className="text-2xl">🔀</span>
        <div className="flex-1">
          <div className="font-semibold text-gray-900">{data.label || 'Condition'}</div>
        </div>
      </div>

      {data.expression && (
        <div className="mt-2 text-xs font-mono text-gray-600 truncate max-w-[180px]">
          {data.expression}
        </div>
      )}

      <div className="flex justify-between mt-2">
        <Handle
          type="source"
          position={Position.Bottom}
          id="true"
          className="w-3 h-3 bg-green-500"
          style={{ left: '30%' }}
        />
        <Handle
          type="source"
          position={Position.Bottom}
          id="false"
          className="w-3 h-3 bg-red-500"
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
