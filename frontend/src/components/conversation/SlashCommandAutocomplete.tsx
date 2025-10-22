/**
 * Slash Command Autocomplete Dropdown
 * Shows available prompt commands when user types '/'
 */

'use client';

import { useEffect, useRef, useState } from 'react';
import type { CommandInfo } from '@/lib/api/prompts';

interface SlashCommandAutocompleteProps {
  commands: CommandInfo[];
  selectedIndex: number;
  onSelect: (command: CommandInfo) => void;
  onClose: () => void;
  inputRef: React.RefObject<HTMLTextAreaElement>;
}

export default function SlashCommandAutocomplete({
  commands,
  selectedIndex,
  onSelect,
  onClose,
  inputRef,
}: SlashCommandAutocompleteProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const selectedItemRef = useRef<HTMLButtonElement>(null);

  // Scroll selected item into view
  useEffect(() => {
    if (selectedItemRef.current) {
      selectedItemRef.current.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
      });
    }
  }, [selectedIndex]);

  // Position dropdown above input
  const [position, setPosition] = useState({ bottom: 0, left: 0 });

  useEffect(() => {
    if (inputRef.current) {
      const rect = inputRef.current.getBoundingClientRect();
      setPosition({
        bottom: window.innerHeight - rect.top + 8, // 8px gap above input
        left: rect.left,
      });
    }
  }, [inputRef]);

  if (commands.length === 0) {
    return null;
  }

  return (
    <>
      {/* Backdrop to close on click */}
      <div
        className="fixed inset-0 z-40"
        onClick={onClose}
      />

      {/* Dropdown */}
      <div
        ref={listRef}
        className="fixed z-50 w-96 max-h-80 overflow-y-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg"
        style={{
          bottom: `${position.bottom}px`,
          left: `${position.left}px`,
        }}
      >
        {/* Header */}
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Slash Commands
          </span>
          <span className="text-xs text-gray-400 dark:text-gray-500">
            ↑↓ Navigate • Enter Select • Esc Close
          </span>
        </div>

        {/* Command List */}
        <div className="py-1">
          {commands.map((command, index) => (
            <button
              key={command.slug}
              ref={index === selectedIndex ? selectedItemRef : null}
              onClick={() => onSelect(command)}
              className={`w-full px-3 py-2 text-left transition-colors ${
                index === selectedIndex
                  ? 'bg-blue-50 dark:bg-blue-900/20'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Command Icon */}
                <div className={`mt-0.5 w-8 h-8 rounded flex items-center justify-center flex-shrink-0 ${
                  index === selectedIndex
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                }`}>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="w-4 h-4"
                  >
                    <path
                      fillRule="evenodd"
                      d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zM2 10a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 10zm0 5.25a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>

                {/* Command Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <code className={`text-sm font-mono ${
                      index === selectedIndex
                        ? 'text-blue-600 dark:text-blue-400'
                        : 'text-gray-900 dark:text-gray-100'
                    }`}>
                      /{command.slug}
                    </code>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {command.name}
                    </span>
                  </div>
                  {command.description && (
                    <p className="mt-0.5 text-xs text-gray-600 dark:text-gray-400 line-clamp-1">
                      {command.description}
                    </p>
                  )}
                  {command.variables && command.variables.length > 0 && (
                    <div className="mt-1 flex items-center gap-1 flex-wrap">
                      {command.variables.slice(0, 3).map((variable) => (
                        <span
                          key={variable.name}
                          className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                        >
                          {variable.name}
                          {variable.required && <span className="ml-0.5 text-red-500">*</span>}
                        </span>
                      ))}
                      {command.variables.length > 3 && (
                        <span className="text-xs text-gray-400">
                          +{command.variables.length - 3} more
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
