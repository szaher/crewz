'use client';

import { useRef, useEffect, useState } from 'react';
import type { CommandInfo } from '@/lib/api/prompts';
import SlashCommandAutocomplete from '../SlashCommandAutocomplete';

interface MessageInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  sending: boolean;
  streaming: boolean;
  onCancel: () => void;
  placeholder?: string;
  filteredCommands?: CommandInfo[];
  onCommandSelect?: (command: CommandInfo) => void;
  showAutocomplete?: boolean;
  onAutocompleteClose?: () => void;
}

export default function MessageInput({
  value,
  onChange,
  onSend,
  sending,
  streaming,
  onCancel,
  placeholder = 'Type your message...',
  filteredCommands = [],
  onCommandSelect,
  showAutocomplete = false,
  onAutocompleteClose,
}: MessageInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0);
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<any>(null);

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognitionInstance = new SpeechRecognition();
        recognitionInstance.continuous = false;
        recognitionInstance.interimResults = false;
        recognitionInstance.lang = 'en-US';

        let startValue = '';

        recognitionInstance.onstart = () => {
          startValue = value;
        };

        recognitionInstance.onresult = (event: any) => {
          const transcript = event.results[event.results.length - 1][0].transcript;
          const newValue = startValue ? `${startValue} ${transcript}` : transcript;
          onChange(newValue);
        };

        recognitionInstance.onend = () => {
          setIsListening(false);
        };

        recognitionInstance.onerror = (event: any) => {
          console.error('Speech recognition error:', event.error);
          setIsListening(false);
        };

        setRecognition(recognitionInstance);
      }
    }
  }, [value, onChange]);

  const toggleVoiceInput = () => {
    if (!recognition) {
      alert('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    if (isListening) {
      recognition.stop();
      setIsListening(false);
    } else {
      recognition.start();
      setIsListening(true);
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  }, [value]);

  // Reset selected index when commands change
  useEffect(() => {
    setSelectedCommandIndex(0);
  }, [filteredCommands]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Handle autocomplete navigation
    if (showAutocomplete && filteredCommands.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedCommandIndex(prev =>
          prev < filteredCommands.length - 1 ? prev + 1 : 0
        );
        return;
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedCommandIndex(prev =>
          prev > 0 ? prev - 1 : filteredCommands.length - 1
        );
        return;
      }

      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (onCommandSelect && filteredCommands[selectedCommandIndex]) {
          onCommandSelect(filteredCommands[selectedCommandIndex]);
        }
        return;
      }

      if (e.key === 'Escape') {
        e.preventDefault();
        onAutocompleteClose?.();
        return;
      }

      // Tab to autocomplete first command
      if (e.key === 'Tab' && filteredCommands.length > 0) {
        e.preventDefault();
        if (onCommandSelect && filteredCommands[0]) {
          onCommandSelect(filteredCommands[0]);
        }
        return;
      }
    }

    // Normal send on Enter
    if (e.key === 'Enter' && !e.shiftKey && !showAutocomplete) {
      e.preventDefault();
      if (!sending && value.trim()) {
        onSend();
      }
    }
  };

  return (
    <div className="flex gap-2 items-end">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          disabled={sending}
          className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ maxHeight: '200px' }}
        />
      </div>

      {/* Voice Input Button */}
      <button
        onClick={toggleVoiceInput}
        disabled={sending || streaming}
        className={`px-4 py-3 rounded-lg font-medium transition-colors flex items-center gap-2 ${
          isListening
            ? 'bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-400 border-2 border-red-500 animate-pulse'
            : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
        } disabled:opacity-50 disabled:cursor-not-allowed`}
        title={isListening ? 'Stop recording' : 'Voice input'}
        aria-label={isListening ? 'Stop recording' : 'Voice input'}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="w-5 h-5"
        >
          <path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
          <path d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z" />
        </svg>
      </button>

      {streaming ? (
        <button
          onClick={onCancel}
          className="px-6 py-3 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors flex items-center gap-2"
          aria-label="Stop generating"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-5 h-5"
          >
            <rect x="5" y="5" width="10" height="10" rx="1" />
          </svg>
          Stop
        </button>
      ) : (
        <button
          onClick={onSend}
          disabled={sending || !value.trim()}
          className="px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium transition-colors flex items-center gap-2"
          aria-label="Send message"
        >
          {sending ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Sending...
            </>
          ) : (
            <>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path d="M3.105 2.289a.75.75 0 00-.826.95l1.414 4.925A1.5 1.5 0 005.135 9.25h6.115a.75.75 0 010 1.5H5.135a1.5 1.5 0 00-1.442 1.086l-1.414 4.926a.75.75 0 00.826.95 28.896 28.896 0 0015.293-7.154.75.75 0 000-1.115A28.897 28.897 0 003.105 2.289z" />
              </svg>
              Send
            </>
          )}
        </button>
      )}

      {/* Slash Command Autocomplete */}
      {showAutocomplete && onCommandSelect && onAutocompleteClose && (
        <SlashCommandAutocomplete
          commands={filteredCommands}
          selectedIndex={selectedCommandIndex}
          onSelect={onCommandSelect}
          onClose={onAutocompleteClose}
          inputRef={textareaRef}
        />
      )}
    </div>
  );
}
