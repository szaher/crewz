'use client';

import type { ModelParameters } from '@/lib/store';

interface ModelParametersEditorProps {
  parameters: ModelParameters;
  onChange: (parameters: ModelParameters) => void;
}

export default function ModelParametersEditor({
  parameters,
  onChange,
}: ModelParametersEditorProps) {
  const handleChange = (key: keyof ModelParameters, value: number) => {
    onChange({ ...parameters, [key]: value });
  };

  return (
    <div className="space-y-6">
      {/* Temperature */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">
            Temperature
          </label>
          <span className="text-sm text-gray-600">
            {parameters.temperature?.toFixed(2) ?? '0.70'}
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="2"
          step="0.1"
          value={parameters.temperature ?? 0.7}
          onChange={(e) => handleChange('temperature', parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <p className="text-xs text-gray-500 mt-1">
          Controls randomness: lower is more focused, higher is more creative
        </p>
      </div>

      {/* Top P */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">
            Top P (Nucleus Sampling)
          </label>
          <span className="text-sm text-gray-600">
            {parameters.top_p?.toFixed(2) ?? '1.00'}
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={parameters.top_p ?? 1.0}
          onChange={(e) => handleChange('top_p', parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <p className="text-xs text-gray-500 mt-1">
          Alternative to temperature. The model considers tokens with top_p probability mass
        </p>
      </div>

      {/* Top K */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">
            Top K
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={parameters.top_k ?? 0}
            onChange={(e) => handleChange('top_k', parseInt(e.target.value) || 0)}
            className="w-20 px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <p className="text-xs text-gray-500">
          Only sample from the top K most likely tokens (0 = disabled)
        </p>
      </div>

      {/* Max Tokens */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">
            Max Tokens
          </label>
          <input
            type="number"
            min="1"
            max="32000"
            step="100"
            value={parameters.max_tokens ?? 2000}
            onChange={(e) => handleChange('max_tokens', parseInt(e.target.value) || 2000)}
            className="w-24 px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <input
          type="range"
          min="100"
          max="8000"
          step="100"
          value={Math.min(parameters.max_tokens ?? 2000, 8000)}
          onChange={(e) => handleChange('max_tokens', parseInt(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <p className="text-xs text-gray-500 mt-1">
          Maximum number of tokens to generate in the response
        </p>
      </div>

      {/* Frequency Penalty */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">
            Frequency Penalty
          </label>
          <span className="text-sm text-gray-600">
            {parameters.frequency_penalty?.toFixed(2) ?? '0.00'}
          </span>
        </div>
        <input
          type="range"
          min="-2"
          max="2"
          step="0.1"
          value={parameters.frequency_penalty ?? 0}
          onChange={(e) => handleChange('frequency_penalty', parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <p className="text-xs text-gray-500 mt-1">
          Penalizes tokens based on frequency: positive values reduce repetition
        </p>
      </div>

      {/* Presence Penalty */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">
            Presence Penalty
          </label>
          <span className="text-sm text-gray-600">
            {parameters.presence_penalty?.toFixed(2) ?? '0.00'}
          </span>
        </div>
        <input
          type="range"
          min="-2"
          max="2"
          step="0.1"
          value={parameters.presence_penalty ?? 0}
          onChange={(e) => handleChange('presence_penalty', parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <p className="text-xs text-gray-500 mt-1">
          Penalizes tokens based on presence: positive values encourage new topics
        </p>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <h4 className="text-sm font-medium text-blue-900 mb-2">
          Model Parameter Tips
        </h4>
        <ul className="text-xs text-blue-800 space-y-1">
          <li>• Start with temperature 0.7 for balanced responses</li>
          <li>• Use lower temperature (0.2-0.5) for factual, focused outputs</li>
          <li>• Use higher temperature (0.8-1.2) for creative, varied outputs</li>
          <li>• Generally, use either temperature OR top_p, not both</li>
          <li>• Adjust max_tokens based on expected response length</li>
        </ul>
      </div>
    </div>
  );
}
