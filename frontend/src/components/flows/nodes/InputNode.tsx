import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

export default memo(function InputNode({ data, selected }: NodeProps) {
  const inputs = data.inputs || [];

  return (
    <div
      className={`
        relative shadow-lg rounded-2xl border-2 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/10 min-w-[260px] max-w-none overflow-auto ${data?.__ui?.readOnly ? '' : 'resize-x'}
        ${selected ? 'border-blue-600 ring-2 ring-blue-200' : 'border-blue-400 dark:border-blue-700'}
      `}
      style={data?.width ? { width: data.width } : undefined}
    >
      {/* No target handle - input nodes are entry points */}

      {/* Card Content - properly contained */}
      <div className="p-4 space-y-3">
        {/* Header with icon and title */}
        <div className="flex items-center gap-3">
          <div className="bg-blue-500 rounded-full p-2 flex items-center justify-center w-10 h-10 flex-shrink-0">
            <span className="text-xl">📥</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-bold text-gray-900 text-sm uppercase tracking-wide truncate">
              {data.label || 'Flow Input'}
            </div>
          </div>
        </div>

        {/* Description */}
        {data.description && (
          <div className="text-xs text-gray-600 italic leading-relaxed">
            {data.description}
          </div>
        )}

        {/* Input Variables Section */}
        {inputs.length > 0 ? (
          <div className="bg-white/50 rounded-lg p-3 border border-blue-200">
            <div className="text-xs font-semibold text-blue-700 mb-2">Input Variables:</div>
            <div className="space-y-1.5">
              {inputs.map((input: any, idx: number) => (
                <div key={idx} className="flex items-center gap-2 text-xs">
                  <span className="text-blue-600 font-mono">•</span>
                  <span className="font-medium text-gray-700 truncate flex-1">
                    {input.name || `input_${idx}`}
                  </span>
                  {input.type && (
                    <span className="text-gray-500 text-[10px] flex-shrink-0">({input.type})</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-xs text-gray-500 bg-white/30 rounded-lg p-3 text-center">
            No inputs configured
          </div>
        )}
      </div>

      {/* Only source handle - output to next nodes */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-10 h-10 bg-blue-500 border-2 border-white shadow-md rounded-full"
      />
    </div>
  );
});
