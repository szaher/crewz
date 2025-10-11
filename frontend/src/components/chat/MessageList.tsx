'use client';

import { useRef, useEffect } from 'react';
import type { ChatMessage } from '@/types/api';
import ExecutionTrace from './ExecutionTrace';
import Markdown from '@/components/shared/Markdown';

interface MessageListProps {
  messages: ChatMessage[];
  onRetry?: (message: ChatMessage) => void;
  onEdit?: (message: ChatMessage) => void;
}

export default function MessageList({ messages, onRetry, onEdit }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive or content updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, messages.length, messages[messages.length - 1]?.content]);

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
        <p className="text-sm">No messages yet. Start the conversation!</p>
      </div>
    );
  }

  // Hide system messages entirely
  const visible = messages.filter((m) => m.role !== 'system');

  return (
    <div className="px-6 py-5 space-y-4">
      {visible.map((message, idx) => {
        const isStreaming = message.id.toString().startsWith('draft-');
        // Use content length in key to force re-render on streaming updates
        const messageKey = isStreaming ? `${message.id}-${message.content?.length || 0}` : message.id;
        return (
        <div
          key={messageKey}
          className={`group relative flex animate-messageSlideIn ${
            message.role === 'user'
              ? 'justify-end dark:bg-slate-800/30 dark:rounded-xl dark:px-1.5 dark:py-1'
              : 'justify-start'
          }`}
          style={{ animationDelay: `${Math.min(idx * 50, 300)}ms` }}
        >
          <div
            className={`relative max-w-[75%] rounded-xl px-4 py-3 border shadow-sm ${
              message.role === 'user'
                ? 'bg-gradient-to-b from-sky-50 to-sky-100 text-slate-800 border-sky-200 dark:bg-transparent dark:text-slate-100/90 dark:border-slate-700'
                : message.role === 'assistant'
                ? 'bg-white text-slate-800 border-slate-200 dark:bg-transparent dark:text-slate-200 dark:border-slate-700'
                : 'bg-emerald-50 text-emerald-900 border-emerald-200 dark:bg-emerald-900/25 dark:text-emerald-200 dark:border-emerald-800/60'
            }`}
          >
            {/* Hover Actions for user messages */}
            {message.role === 'user' && (onRetry || onEdit) && (
              <div className={`absolute top-1 -right-2 opacity-0 group-hover:opacity-100 transition-opacity`}
                   aria-hidden={!onRetry && !onEdit}
              >
                <div className="flex items-center gap-1 bg-white/80 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 rounded-full px-1 py-0.5 shadow-sm">
                  {onRetry && (
                    <button
                      type="button"
                      onClick={() => onRetry?.(message)}
                      className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
                      title="Retry this message"
                      aria-label="Retry"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>
                    </button>
                  )}
                  {onEdit && (
                    <button
                      type="button"
                      onClick={() => onEdit?.(message)}
                      className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
                      title="Edit this message"
                      aria-label="Edit"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"></path></svg>
                    </button>
                  )}
                </div>
              </div>
            )}
            {/* Role Badge */}
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[11px] font-medium opacity-75">
                {message.role === 'user' ? 'You' : message.role === 'assistant' ? 'Agent' : 'System'}
              </span>
              <span className="text-[11px] opacity-60">
                {new Date(message.created_at).toLocaleTimeString()}
              </span>
            </div>

            {/* Message Content (Markdown or streaming) */}
            {isStreaming && message.role === 'assistant' ? (
              <div className="prose prose-slate dark:prose-invert max-w-none leading-relaxed text-[15px] prose-a:text-blue-600 dark:prose-a:text-blue-300 prose-code:text-emerald-700 dark:prose-code:text-emerald-200">
                <div className="relative">
                  {message.content ? (
                    <>
                      <Markdown content={message.content} />
                      <span className="typing-cursor inline-block w-0.5 h-4 ml-1 bg-blue-500 animate-pulse" />
                    </>
                  ) : (
                    <div className="inline-flex items-center gap-1 text-gray-500">
                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className={`${message.role === 'user' ? 'prose prose-slate dark:prose-invert' : 'prose prose-slate dark:prose-invert'} max-w-none leading-relaxed text-[15px] prose-a:text-blue-600 dark:prose-a:text-blue-300 prose-code:text-emerald-700 dark:prose-code:text-emerald-200`}
              >
                <Markdown content={message.content} />
              </div>
            )}

            {/* Tool Invocations */}
            {message.metadata?.tool_invocations && message.metadata.tool_invocations.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                <ExecutionTrace toolInvocations={message.metadata.tool_invocations} />
              </div>
            )}
          </div>
        </div>
      );
      })}
      <div ref={messagesEndRef} />
    </div>
  );
}
