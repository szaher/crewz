'use client';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  hyperparams?: {
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
    frequency_penalty?: number;
    presence_penalty?: number;
  };
  onUpdateHyperparams: (params: any) => void;
}

export default function SettingsPanel({
  isOpen,
  onClose,
  sessionId,
  hyperparams = {},
  onUpdateHyperparams,
}: SettingsPanelProps) {
  if (!isOpen) return null;

  return (
    <div className="absolute right-0 top-0 h-full w-80 bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 shadow-xl z-40 flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Settings</h3>
        <button
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
          aria-label="Close settings"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-5 h-5"
          >
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div>
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
            Model Parameters
          </h4>
          <div className="space-y-4">
            {/* Temperature */}
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                Temperature
              </label>
              <input
                type="number"
                step="0.1"
                min={0}
                max={2}
                value={hyperparams.temperature ?? ''}
                onChange={(e) =>
                  onUpdateHyperparams({
                    ...hyperparams,
                    temperature: e.target.value === '' ? undefined : Number(e.target.value),
                  })
                }
                placeholder="0.7"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm bg-white dark:bg-gray-900"
              />
              <p className="mt-1 text-xs text-gray-500">Controls randomness (0-2)</p>
            </div>

            {/* Max Tokens */}
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                Max Tokens
              </label>
              <input
                type="number"
                min={1}
                value={hyperparams.max_tokens ?? ''}
                onChange={(e) =>
                  onUpdateHyperparams({
                    ...hyperparams,
                    max_tokens: e.target.value === '' ? undefined : Number(e.target.value),
                  })
                }
                placeholder="2048"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm bg-white dark:bg-gray-900"
              />
              <p className="mt-1 text-xs text-gray-500">Maximum response length</p>
            </div>

            {/* Top P */}
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                Top P
              </label>
              <input
                type="number"
                step="0.05"
                min={0}
                max={1}
                value={hyperparams.top_p ?? ''}
                onChange={(e) =>
                  onUpdateHyperparams({
                    ...hyperparams,
                    top_p: e.target.value === '' ? undefined : Number(e.target.value),
                  })
                }
                placeholder="1.0"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm bg-white dark:bg-gray-900"
              />
              <p className="mt-1 text-xs text-gray-500">Nucleus sampling (0-1)</p>
            </div>

            {/* Frequency Penalty */}
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                Frequency Penalty
              </label>
              <input
                type="number"
                step="0.1"
                min={-2}
                max={2}
                value={hyperparams.frequency_penalty ?? ''}
                onChange={(e) =>
                  onUpdateHyperparams({
                    ...hyperparams,
                    frequency_penalty: e.target.value === '' ? undefined : Number(e.target.value),
                  })
                }
                placeholder="0.0"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm bg-white dark:bg-gray-900"
              />
              <p className="mt-1 text-xs text-gray-500">Reduces repetition (-2 to 2)</p>
            </div>

            {/* Presence Penalty */}
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                Presence Penalty
              </label>
              <input
                type="number"
                step="0.1"
                min={-2}
                max={2}
                value={hyperparams.presence_penalty ?? ''}
                onChange={(e) =>
                  onUpdateHyperparams({
                    ...hyperparams,
                    presence_penalty: e.target.value === '' ? undefined : Number(e.target.value),
                  })
                }
                placeholder="0.0"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm bg-white dark:bg-gray-900"
              />
              <p className="mt-1 text-xs text-gray-500">Encourages new topics (-2 to 2)</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
