'use client';

import { useRef, useEffect } from 'react';
import type { ChatMessage } from '@/types/api';
import ExecutionTrace from './ExecutionTrace';

interface MessageListProps {
  messages: ChatMessage[];
}

export default function MessageList({ messages }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <p className="text-sm">No messages yet. Start the conversation!</p>
      </div>
    );
  }

  return (
    <div className="px-6 py-4 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[70%] rounded-lg px-4 py-3 ${
              message.role === 'user'
                ? 'bg-blue-600 text-white'
                : message.role === 'assistant'
                ? 'bg-gray-100 text-gray-900'
                : 'bg-yellow-50 text-yellow-900 border border-yellow-200'
            }`}
          >
            {/* Role Badge */}
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium opacity-75">
                {message.role === 'user' ? 'You' : message.role === 'assistant' ? 'Agent' : 'System'}
              </span>
              <span className="text-xs opacity-50">
                {new Date(message.created_at).toLocaleTimeString()}
              </span>
            </div>

            {/* Message Content */}
            <div className="whitespace-pre-wrap break-words">
              {message.content}
            </div>

            {/* Tool Invocations */}
            {message.metadata?.tool_invocations && message.metadata.tool_invocations.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-300">
                <ExecutionTrace toolInvocations={message.metadata.tool_invocations} />
              </div>
            )}
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}
