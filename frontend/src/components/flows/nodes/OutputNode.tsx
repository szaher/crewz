import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function OutputNode({ data, selected }: NodeProps) {
  const outputs = data.outputs || [];

  return (
    <div className={`
      px-4 py-3 shadow-lg rounded-2xl border-2 bg-gradient-to-br from-green-50 to-emerald-50 min-w-[220px]
      ${selected ? 'border-green-600 ring-2 ring-green-200' : 'border-green-400'}
    `}>
      {/* Only target handle - output nodes are end points */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-4 h-4 bg-green-500 border-2 border-white shadow-md"
      />

      <div className="flex items-center gap-2 mb-2">
        <div className="bg-green-500 rounded-full p-1.5">
          <span className="text-xl">📤</span>
        </div>
        <div className="flex-1">
          <div className="font-bold text-gray-900 text-sm uppercase tracking-wide">
            {data.label || 'Flow Output'}
          </div>
        </div>
      </div>

      {data.description && (
        <div className="text-xs text-gray-600 mb-2 italic">
          {data.description}
        </div>
      )}

      {outputs.length > 0 ? (
        <div className="mt-2 space-y-1.5 bg-white/50 rounded-lg p-2 border border-green-200">
          <div className="text-xs font-semibold text-green-700 mb-1">Output Variables:</div>
          {outputs.map((output: any, idx: number) => (
            <div key={idx} className="flex items-center gap-1.5 text-xs">
              <span className="text-green-600 font-mono">•</span>
              <span className="font-medium text-gray-700">{output.name || `output_${idx}`}</span>
              {output.type && (
                <span className="text-gray-500 text-[10px]">({output.type})</span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-2 text-xs text-gray-500 bg-white/30 rounded p-2 text-center">
          No outputs configured
        </div>
      )}

      {/* No source handle - output nodes are terminal */}
    </div>
  );
});
