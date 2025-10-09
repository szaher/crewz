'use client';

import { useRef, useEffect } from 'react';
import type { ChatMessage } from '@/types/api';
import ExecutionTrace from './ExecutionTrace';
import Markdown from '@/components/shared/Markdown';

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
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
        <p className="text-sm">No messages yet. Start the conversation!</p>
      </div>
    );
  }

  return (
    <div className="px-6 py-5 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${
            message.role === 'user'
              ? 'justify-end dark:bg-slate-800/30 dark:rounded-xl dark:px-1.5 dark:py-1'
              : 'justify-start'
          }`}
        >
          <div
            className={`max-w-[75%] rounded-xl px-4 py-3 border shadow-sm ${
              message.role === 'user'
                ? 'bg-gradient-to-b from-sky-50 to-sky-100 text-slate-800 border-sky-200 dark:bg-transparent dark:text-slate-100/90 dark:border-slate-700'
                : message.role === 'assistant'
                ? 'bg-white text-slate-800 border-slate-200 dark:bg-transparent dark:text-slate-200 dark:border-slate-700'
                : 'bg-emerald-50 text-emerald-900 border-emerald-200 dark:bg-emerald-900/25 dark:text-emerald-200 dark:border-emerald-800/60'
            }`}
          >
            {/* Role Badge */}
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[11px] font-medium opacity-75">
                {message.role === 'user' ? 'You' : message.role === 'assistant' ? 'Agent' : 'System'}
              </span>
              <span className="text-[11px] opacity-60">
                {new Date(message.created_at).toLocaleTimeString()}
              </span>
            </div>

            {/* Message Content (Markdown) */}
            <div className={`${message.role === 'user' ? 'prose prose-slate dark:prose-invert' : 'prose prose-slate dark:prose-invert'} max-w-none leading-relaxed text-[15px] prose-a:text-blue-600 dark:prose-a:text-blue-300 prose-code:text-emerald-700 dark:prose-code:text-emerald-200`}
            >
              <Markdown content={message.content} />
            </div>

            {/* Tool Invocations */}
            {message.metadata?.tool_invocations && message.metadata.tool_invocations.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
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
