'use client';

import { memo, useState, useEffect, useRef } from 'react';
import type { ChatMessage } from '@/types/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MessageListProps {
  messages: ChatMessage[];
  streamingContent: string;
  isThinking?: boolean;
  onEditMessage?: (messageId: string, newContent: string) => Promise<void>;
  onResendMessage?: (content: string) => Promise<void>;
}

// Memoized individual message component to prevent unnecessary re-renders
const MessageItem = memo(({
  message,
  isLastUserMessage,
  onEdit,
  onResend,
}: {
  message: ChatMessage;
  isLastUserMessage: boolean;
  onEdit?: (messageId: string, newContent: string) => Promise<void>;
  onResend?: (content: string) => Promise<void>;
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [copied, setCopied] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
      // Set cursor to end
      textareaRef.current.setSelectionRange(editContent.length, editContent.length);
    }
  }, [isEditing, editContent.length]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleSpeak = () => {
    if (typeof window === 'undefined') return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(message.content);
    utterance.lang = 'en-US';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditContent(message.content);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditContent(message.content);
  };

  const handleSaveEdit = async () => {
    if (editContent.trim() && onEdit) {
      await onEdit(message.id, editContent.trim());
      setIsEditing(false);
    }
  };

  const handleResend = async () => {
    if (onResend) {
      await onResend(message.content);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSaveEdit();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  const renderMessage = (content: string) => {
    return (
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    );
  };

  return (
    <div
      className={`flex gap-4 ${
        message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
      }`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium ${
            message.role === 'user'
              ? 'bg-blue-600'
              : 'bg-gray-600 dark:bg-gray-700'
          }`}
        >
          {message.role === 'user' ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-5 h-5"
            >
              <path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z" />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-5 h-5"
            >
              <path
                fillRule="evenodd"
                d="M10 1c3.866 0 7 1.79 7 4s-3.134 4-7 4-7-1.79-7-4 3.134-4 7-4zm5.694 8.13c.464-.264.91-.583 1.306-.952V10c0 2.21-3.134 4-7 4s-7-1.79-7-4V8.178c.396.37.842.688 1.306.953C5.838 10.006 7.854 10.5 10 10.5s4.162-.494 5.694-1.37zM3 13.179V15c0 2.21 3.134 4 7 4s7-1.79 7-4v-1.822c-.396.37-.842.688-1.306.953-1.532.875-3.548 1.369-5.694 1.369s-4.162-.494-5.694-1.37A7.009 7.009 0 013 13.179z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </div>
      </div>

      {/* Message Content */}
      <div
        className={`flex-1 max-w-3xl ${
          message.role === 'user' ? 'text-right' : 'text-left'
        }`}
      >
        <div className="relative group">
          {isEditing ? (
            // Edit mode
            <div className="w-full">
              <textarea
                ref={textareaRef}
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full px-4 py-3 rounded-lg border-2 border-blue-500 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none resize-none"
                rows={Math.max(3, editContent.split('\n').length)}
              />
              <div className="flex gap-2 mt-2 justify-end">
                <button
                  onClick={handleCancelEdit}
                  className="px-3 py-1 text-sm rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={!editContent.trim()}
                  className="px-3 py-1 text-sm rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Save & Send
                </button>
              </div>
            </div>
          ) : (
            <>
              <div
                className={`inline-block px-4 py-3 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                }`}
              >
                {message.role === 'user' ? (
                  <div className="whitespace-pre-wrap">{message.content}</div>
                ) : (
                  renderMessage(message.content)
                )}
              </div>

              {/* Action buttons */}
              <div className={`flex gap-1 mt-1 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {/* Copy and Speak buttons for AI messages */}
                {message.role === 'assistant' && (showActions || copied || isSpeaking) && (
                  <>
                    <button
                      onClick={handleCopy}
                      className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 transition-colors"
                      title="Copy response"
                    >
                      {copied ? (
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-green-600">
                          <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                          <path d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z" />
                          <path d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.439A1.5 1.5 0 008.378 6H4.5z" />
                        </svg>
                      )}
                    </button>
                    <button
                      onClick={handleSpeak}
                      className={`p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors ${
                        isSpeaking ? 'text-blue-600 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400'
                      }`}
                      title={isSpeaking ? 'Stop speaking' : 'Read aloud'}
                    >
                      {isSpeaking ? (
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 animate-pulse">
                          <path d="M10 3.75a2 2 0 10-4 0v8.5a2 2 0 104 0v-8.5zM17.25 8a.75.75 0 00-1.5 0v4a2.5 2.5 0 01-5 0V8a.75.75 0 00-1.5 0v4a4 4 0 008 0V8zM7 10.75a.75.75 0 00-1.5 0v1a2.5 2.5 0 005 0v-1a.75.75 0 00-1.5 0v1a1 1 0 11-2 0v-1z" />
                        </svg>
                      ) : (
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                          <path d="M10.5 3.75a2.25 2.25 0 00-4.5 0v8.5a2.25 2.25 0 004.5 0v-8.5zm5.25 0a.75.75 0 00-1.5 0v8.5a.75.75 0 001.5 0v-8.5z" />
                          <path fillRule="evenodd" d="M14 12.75a3.75 3.75 0 01-7.5 0v-8.5a3.75 3.75 0 017.5 0v8.5zm1.5 0v-8.5a5.25 5.25 0 00-10.5 0v8.5a5.25 5.25 0 0010.5 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </button>
                  </>
                )}

                {/* Edit and Resend buttons for last user message */}
                {message.role === 'user' && isLastUserMessage && showActions && (
                  <>
                    <button
                      onClick={handleEdit}
                      className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 transition-colors"
                      title="Edit message"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                        <path d="M5.433 13.917l1.262-3.155A4 4 0 017.58 9.42l6.92-6.918a2.121 2.121 0 013 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 01-.65-.65z" />
                        <path d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0010 3H4.75A2.75 2.75 0 002 5.75v9.5A2.75 2.75 0 004.75 18h9.5A2.75 2.75 0 0017 15.25V10a.75.75 0 00-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5z" />
                      </svg>
                    </button>
                    <button
                      onClick={handleResend}
                      className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 transition-colors"
                      title="Resend message"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                        <path fillRule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </>
                )}
              </div>
            </>
          )}
        </div>

        {/* Timestamp */}
        {!isEditing && (
          <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        )}
      </div>
    </div>
  );
});

MessageItem.displayName = 'MessageItem';

function MessageList({
  messages,
  streamingContent,
  isThinking = false,
  onEditMessage,
  onResendMessage,
}: MessageListProps) {
  const [displayedContent, setDisplayedContent] = useState('');
  const displayIndexRef = useRef(0);
  const animationFrameRef = useRef<number>();
  const lastUpdateRef = useRef(0);

  // Find the last user message index
  const lastUserMessageIndex = messages.reduceRight((acc, message, index) => {
    if (acc === -1 && message.role === 'user') {
      return index;
    }
    return acc;
  }, -1);

  // Typewriter effect for streaming content
  useEffect(() => {
    if (!streamingContent) {
      setDisplayedContent('');
      displayIndexRef.current = 0;
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      return;
    }

    // If new content arrived, animate it
    const animate = (timestamp: number) => {
      // Throttle to ~60fps for smooth animation
      if (timestamp - lastUpdateRef.current < 16) {
        animationFrameRef.current = requestAnimationFrame(animate);
        return;
      }
      lastUpdateRef.current = timestamp;

      if (displayIndexRef.current < streamingContent.length) {
        // Calculate how far behind we are
        const remaining = streamingContent.length - displayIndexRef.current;

        // Adaptive speed: catch up faster when more content arrives
        // Normal: 2-3 chars, Behind: up to 10 chars to catch up quickly
        const charsToAdd = remaining > 50
          ? Math.min(10, remaining)  // Fast catch-up
          : Math.min(3, remaining);   // Normal typing speed

        displayIndexRef.current += charsToAdd;
        setDisplayedContent(streamingContent.substring(0, displayIndexRef.current));
        animationFrameRef.current = requestAnimationFrame(animate);
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [streamingContent]);

  return (
    <div className="px-6 py-4 space-y-6">
      {messages.map((message, index) => (
        <MessageItem
          key={message.id}
          message={message}
          isLastUserMessage={index === lastUserMessageIndex}
          onEdit={onEditMessage}
          onResend={onResendMessage}
        />
      ))}

      {/* Thinking Indicator */}
      {isThinking && !streamingContent && (
        <div className="flex gap-4">
          <div className="flex-shrink-0">
            <div className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-600 dark:bg-gray-700 text-white text-sm font-medium">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path
                  fillRule="evenodd"
                  d="M10 1c3.866 0 7 1.79 7 4s-3.134 4-7 4-7-1.79-7-4 3.134-4 7-4zm5.694 8.13c.464-.264.91-.583 1.306-.952V10c0 2.21-3.134 4-7 4s-7-1.79-7-4V8.178c.396.37.842.688 1.306.953C5.838 10.006 7.854 10.5 10 10.5s4.162-.494 5.694-1.37zM3 13.179V15c0 2.21 3.134 4 7 4s7-1.79 7-4v-1.822c-.396.37-.842.688-1.306.953-1.532.875-3.548 1.369-5.694 1.369s-4.162-.494-5.694-1.37A7.009 7.009 0 013 13.179z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
          </div>
          <div className="flex-1 max-w-3xl">
            <div className="inline-block px-4 py-3 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
              <span className="flex items-center gap-2">
                <span className="text-sm">Thinking</span>
                <span className="flex gap-1">
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                </span>
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Streaming Message with Typewriter Effect */}
      {streamingContent && (
        <div className="flex gap-4">
          {/* Avatar */}
          <div className="flex-shrink-0">
            <div className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-600 dark:bg-gray-700 text-white text-sm font-medium">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path
                  fillRule="evenodd"
                  d="M10 1c3.866 0 7 1.79 7 4s-3.134 4-7 4-7-1.79-7-4 3.134-4 7-4zm5.694 8.13c.464-.264.91-.583 1.306-.952V10c0 2.21-3.134 4-7 4s-7-1.79-7-4V8.178c.396.37.842.688 1.306.953C5.838 10.006 7.854 10.5 10 10.5s4.162-.494 5.694-1.37zM3 13.179V15c0 2.21 3.134 4 7 4s7-1.79 7-4v-1.822c-.396.37-.842.688-1.306.953-1.532.875-3.548 1.369-5.694 1.369s-4.162-.494-5.694-1.37A7.009 7.009 0 013 13.179z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
          </div>

          {/* Message Content with Typewriter Animation */}
          <div className="flex-1 max-w-3xl">
            <div className="inline-block px-4 py-3 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
              <span className="whitespace-pre-wrap font-sans text-sm">{displayedContent}</span>
              <span className="inline-block w-0.5 h-4 ml-1 bg-blue-500 animate-pulse align-middle" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default memo(MessageList);
