import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function OutputNode({ data, selected }: NodeProps) {
  const outputs = data.outputs || [];

  return (
    <div
      className={`
        relative shadow-lg rounded-2xl border-2 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-emerald-900/10 dark:to-emerald-900/5 min-w-[260px] max-w-none overflow-auto ${data?.__ui?.readOnly ? '' : 'resize-x'}
        ${selected ? 'border-green-600 ring-2 ring-green-200' : 'border-green-400 dark:border-green-700'}
      `}
      style={data?.width ? { width: data.width } : undefined}
    >
      {/* Only target handle - output nodes are end points */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-10 h-10 bg-green-500 border-2 border-white shadow-md rounded-full"
      />

      {/* Card Content - properly contained */}
      <div className="p-4 space-y-3">
        {/* Header with icon and title */}
        <div className="flex items-center gap-3">
          <div className="bg-green-500 rounded-full p-2 flex items-center justify-center w-10 h-10 flex-shrink-0">
            <span className="text-xl">📤</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-bold text-gray-900 text-sm uppercase tracking-wide truncate">
              {data.label || 'Flow Output'}
            </div>
          </div>
        </div>

        {/* Description */}
        {data.description && (
          <div className="text-xs text-gray-600 italic leading-relaxed">
            {data.description}
          </div>
        )}

        {/* Output Variables Section */}
        {outputs.length > 0 ? (
          <div className="bg-white/50 rounded-lg p-3 border border-green-200">
            <div className="text-xs font-semibold text-green-700 mb-2">Output Variables:</div>
            <div className="space-y-1.5">
              {outputs.map((output: any, idx: number) => (
                <div key={idx} className="flex items-center gap-2 text-xs">
                  <span className="text-green-600 font-mono">•</span>
                  <span className="font-medium text-gray-700 truncate flex-1">
                    {output.name || `output_${idx}`}
                  </span>
                  {output.type && (
                    <span className="text-gray-500 text-[10px] flex-shrink-0">({output.type})</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-xs text-gray-500 bg-white/30 rounded-lg p-3 text-center">
            No outputs configured
          </div>
        )}
      </div>

      {/* No source handle - output nodes are terminal */}
    </div>
  );
});
