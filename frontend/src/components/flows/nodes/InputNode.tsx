import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function InputNode({ data, selected }: NodeProps) {
  const inputs = data.inputs || [];

  return (
    <div className={`
      px-4 py-3 shadow-lg rounded-2xl border-2 bg-gradient-to-br from-blue-50 to-indigo-50 min-w-[220px]
      ${selected ? 'border-blue-600 ring-2 ring-blue-200' : 'border-blue-400'}
    `}>
      {/* No target handle - input nodes are entry points */}

      <div className="flex items-center gap-2 mb-2">
        <div className="bg-blue-500 rounded-full p-1.5">
          <span className="text-xl">📥</span>
        </div>
        <div className="flex-1">
          <div className="font-bold text-gray-900 text-sm uppercase tracking-wide">
            {data.label || 'Flow Input'}
          </div>
        </div>
      </div>

      {data.description && (
        <div className="text-xs text-gray-600 mb-2 italic">
          {data.description}
        </div>
      )}

      {inputs.length > 0 ? (
        <div className="mt-2 space-y-1.5 bg-white/50 rounded-lg p-2 border border-blue-200">
          <div className="text-xs font-semibold text-blue-700 mb-1">Input Variables:</div>
          {inputs.map((input: any, idx: number) => (
            <div key={idx} className="flex items-center gap-1.5 text-xs">
              <span className="text-blue-600 font-mono">•</span>
              <span className="font-medium text-gray-700">{input.name || `input_${idx}`}</span>
              {input.type && (
                <span className="text-gray-500 text-[10px]">({input.type})</span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-2 text-xs text-gray-500 bg-white/30 rounded p-2 text-center">
          No inputs configured
        </div>
      )}

      {/* Only source handle - output to next nodes */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-4 h-4 bg-blue-500 border-2 border-white shadow-md"
      />
    </div>
  );
});
