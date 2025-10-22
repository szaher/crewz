'use client';

import { useRef, useEffect, useState } from 'react';
import type { ChatMessage } from '@/types/api';
import MessageList from './MessageList';
import MessageInput from './MessageArea/MessageInput';
import SettingsPanel from './MessageArea/SettingsPanel';
import PromptVariablesModal from './PromptVariablesModal';
import VoiceCallModal from './VoiceCallModal';
import { useSlashCommands } from '@/hooks/conversation/useSlashCommands';
import { promptApi } from '@/lib/api/prompts';
import type { CommandInfo } from '@/lib/api/prompts';

interface MessageAreaProps {
  sessionId: string;
  sessionTitle: string;
  messages: ChatMessage[];
  streamingContent: string;
  isThinking: boolean;
  loading: boolean;
  sending: boolean;
  streaming: boolean;
  onSendMessage: (content: string) => Promise<void>;
  onCancelStreaming: () => void;
  onOpenSettings: () => void;
  settingsOpen: boolean;
  onCloseSettings: () => void;
  hyperparams?: {
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
    frequency_penalty?: number;
    presence_penalty?: number;
  };
  onUpdateHyperparams: (params: any) => void;
}

export default function MessageArea({
  sessionId,
  sessionTitle,
  messages,
  streamingContent,
  isThinking,
  loading,
  sending,
  streaming,
  onSendMessage,
  onCancelStreaming,
  onOpenSettings,
  settingsOpen,
  onCloseSettings,
  hyperparams,
  onUpdateHyperparams,
}: MessageAreaProps) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevMessagesLengthRef = useRef(0);
  const prevSessionIdRef = useRef(sessionId);

  // Slash commands
  const slashCommands = useSlashCommands();
  const { filterCommands } = slashCommands; // Destructure to get stable reference
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [filteredCommands, setFilteredCommands] = useState<CommandInfo[]>([]);
  const [selectedCommand, setSelectedCommand] = useState<CommandInfo | null>(null);
  const [showVariablesModal, setShowVariablesModal] = useState(false);
  const [showVoiceCallModal, setShowVoiceCallModal] = useState(false);

  // Reset message count when session changes
  useEffect(() => {
    if (prevSessionIdRef.current !== sessionId) {
      prevMessagesLengthRef.current = 0;
      prevSessionIdRef.current = sessionId;
    }
  }, [sessionId]);

  // Auto-scroll ONLY when sending new messages, NOT when loading conversations
  useEffect(() => {
    // Only scroll if messages increased AND we're not on initial load
    if (messages.length > prevMessagesLengthRef.current && prevMessagesLengthRef.current > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' });
    }
    prevMessagesLengthRef.current = messages.length;
  }, [messages.length]);

  // Detect slash commands in input
  useEffect(() => {
    if (inputValue.startsWith('/') && !sending) {
      const filtered = filterCommands(inputValue);
      setFilteredCommands(filtered);
      setShowAutocomplete(filtered.length > 0);
    } else {
      setShowAutocomplete(false);
      setFilteredCommands([]);
    }
  }, [inputValue, filterCommands, sending]);

  // Handle input change
  const handleInputChange = (value: string) => {
    setInputValue(value);
  };

  // Handle command selection from autocomplete
  const handleCommandSelect = (command: CommandInfo) => {
    setSelectedCommand(command);
    setShowAutocomplete(false);
    setInputValue(''); // Clear input

    // If command has variables, show modal. Otherwise execute directly
    if (command.variables && command.variables.length > 0) {
      setShowVariablesModal(true);
    } else {
      // Execute command without variables
      void executeCommand(command, {});
    }
  };

  // Execute prompt command
  const executeCommand = async (command: CommandInfo, variables: Record<string, any>) => {
    try {
      setShowVariablesModal(false);

      // Get the full prompt by slug to get the prompt ID
      const promptResponse = await promptApi.getBySlug(command.slug);

      if (promptResponse.error || !promptResponse.data) {
        throw new Error(promptResponse.error || 'Failed to load prompt');
      }

      const prompt = promptResponse.data;

      // Execute the prompt via backend (tracks usage, renders template)
      const executeResponse = await promptApi.execute(prompt.id, {
        variables,
        context_type: 'chat',
        context_id: sessionId,
      });

      if (executeResponse.error || !executeResponse.data) {
        throw new Error(executeResponse.error || 'Failed to execute prompt');
      }

      // Send the rendered content as a message
      await onSendMessage(executeResponse.data.rendered_content);

      setSelectedCommand(null);
    } catch (err) {
      console.error('Failed to execute command:', err);
      // TODO: Show error toast/notification
      setSelectedCommand(null);
      setShowVariablesModal(false);
    }
  };

  const handleSend = async () => {
    if (!inputValue.trim() || sending) return;

    const content = inputValue.trim();
    setInputValue('');

    await onSendMessage(content);
  };

  const handleEditMessage = async (messageId: string, newContent: string) => {
    // When editing, we just resend with the new content
    // The backend will handle this as a new message
    await onSendMessage(newContent);
  };

  const handleResendMessage = async (content: string) => {
    // Resend the exact same content
    await onSendMessage(content);
  };

  return (
    <div className="h-full flex flex-col relative bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
        <div className="flex-1">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            {sessionTitle}
          </h1>
        </div>

        <div className="flex items-center gap-2">
          {/* Voice Call Button */}
          <button
            onClick={() => setShowVoiceCallModal(true)}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 transition-colors"
            title="Voice Call"
            aria-label="Start voice call"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-5 h-5"
            >
              <path
                fillRule="evenodd"
                d="M2 3.5A1.5 1.5 0 013.5 2h1.148a1.5 1.5 0 011.465 1.175l.716 3.223a1.5 1.5 0 01-1.052 1.767l-.933.267c-.41.117-.643.555-.48.95a11.542 11.542 0 006.254 6.254c.395.163.833-.07.95-.48l.267-.933a1.5 1.5 0 011.767-1.052l3.223.716A1.5 1.5 0 0118 15.352V16.5a1.5 1.5 0 01-1.5 1.5H15c-1.149 0-2.263-.15-3.326-.43A13.022 13.022 0 012.43 8.326 13.019 13.019 0 012 5V3.5z"
                clipRule="evenodd"
              />
            </svg>
          </button>

          {/* Settings Button */}
          <button
            onClick={onOpenSettings}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 transition-colors"
            title="Settings"
            aria-label="Open settings"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-5 h-5"
            >
              <path
                fillRule="evenodd"
                d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <MessageList
            messages={messages}
            streamingContent={streamingContent}
            isThinking={isThinking}
            onEditMessage={handleEditMessage}
            onResendMessage={handleResendMessage}
          />
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 dark:border-gray-800 px-6 py-4 bg-white dark:bg-gray-900">
        <MessageInput
          value={inputValue}
          onChange={handleInputChange}
          onSend={handleSend}
          sending={sending}
          streaming={streaming}
          onCancel={onCancelStreaming}
          placeholder="Type your message or / for commands..."
          filteredCommands={filteredCommands}
          onCommandSelect={handleCommandSelect}
          showAutocomplete={showAutocomplete}
          onAutocompleteClose={() => setShowAutocomplete(false)}
        />
      </div>

      {/* Settings Panel */}
      {settingsOpen && (
        <SettingsPanel
          isOpen={settingsOpen}
          onClose={onCloseSettings}
          sessionId={sessionId}
          hyperparams={hyperparams}
          onUpdateHyperparams={onUpdateHyperparams}
        />
      )}

      {/* Prompt Variables Modal */}
      {showVariablesModal && selectedCommand && (
        <PromptVariablesModal
          isOpen={showVariablesModal}
          onClose={() => {
            setShowVariablesModal(false);
            setSelectedCommand(null);
          }}
          onExecute={(variables) => {
            if (selectedCommand) {
              void executeCommand(selectedCommand, variables);
            }
          }}
          commandName={selectedCommand.name}
          commandSlug={selectedCommand.slug}
          commandDescription={selectedCommand.description}
          variables={selectedCommand.variables}
        />
      )}

      {/* Voice Call Modal */}
      <VoiceCallModal
        isOpen={showVoiceCallModal}
        onClose={() => setShowVoiceCallModal(false)}
        onSendMessage={onSendMessage}
        streamingContent={streamingContent}
        isThinking={isThinking}
        sending={sending}
        streaming={streaming}
      />
    </div>
  );
}
