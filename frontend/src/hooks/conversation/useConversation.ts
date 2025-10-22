/**
 * Custom hook for managing conversation messages
 * Handles message loading, sending, and streaming
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { flushSync } from 'react-dom';
import { apiClient } from '@/lib/api-client';
import { getApiBaseUrl } from '@/lib/api-url';
import type { ChatMessage } from '@/types/api';

interface UseConversationOptions {
  sessionId: string | null;
  onStreamingStart?: () => void;
  onStreamingComplete?: () => void;
  hyperparams?: {
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
    frequency_penalty?: number;
    presence_penalty?: number;
  };
}

export function useConversation(options: UseConversationOptions) {
  const { sessionId, onStreamingStart, onStreamingComplete, hyperparams } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const streamingContentRef = useRef('');
  const lastUpdateTimeRef = useRef(0);

  // Load messages for the session
  const loadMessages = useCallback(async () => {
    if (!sessionId) {
      setMessages([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(`/api/v1/chat/sessions/${sessionId}/messages`);

      if (response.error) {
        throw new Error(response.error);
      }

      setMessages(response.data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load messages');
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Send a message with streaming support using XMLHttpRequest for true streaming
  const sendMessage = useCallback(async (content: string) => {
    if (!sessionId || !content.trim()) {
      return;
    }

    setSending(true);
    setStreaming(true);
    setStreamingContent('');
    setIsThinking(false);
    setError(null);
    streamingContentRef.current = '';

    // Add user message optimistically
    const userMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      created_at: new Date().toISOString(),
      session_id: sessionId,
    };

    flushSync(() => {
      setMessages(prev => [...prev, userMessage]);
    });

    try {
      onStreamingStart?.();

      // Build request body
      const requestBody: any = {
        user_message: content.trim(),
      };

      // Add hyperparameters if provided
      if (hyperparams) {
        if (hyperparams.temperature !== undefined) requestBody.temperature = hyperparams.temperature;
        if (hyperparams.max_tokens !== undefined) requestBody.max_tokens = hyperparams.max_tokens;
        if (hyperparams.top_p !== undefined) requestBody.top_p = hyperparams.top_p;
        if (hyperparams.frequency_penalty !== undefined) requestBody.frequency_penalty = hyperparams.frequency_penalty;
        if (hyperparams.presence_penalty !== undefined) requestBody.presence_penalty = hyperparams.presence_penalty;
      }


      return new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.open('POST', `${getApiBaseUrl()}/api/v1/chat/sessions/${sessionId}/generate/stream`);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Authorization', `Bearer ${localStorage.getItem('access_token')}`);
        xhr.setRequestHeader('Accept', 'text/event-stream');
        xhr.setRequestHeader('Cache-Control', 'no-cache');

        let buffer = '';
        let lastProcessedIndex = 0;
        let chunkCount = 0;

        const processEvent = (event: string, data: string) => {
          try {
            const parsed = JSON.parse(data);

            if (event === 'status') {
              if (parsed.state === 'thinking') {
                setIsThinking(true);
              }
            } else if (event === 'delta') {
              const token = parsed.token || '';
              streamingContentRef.current += token;

              // Throttle updates to every 50ms to prevent infinite loop warning
              const now = Date.now();
              if (now - lastUpdateTimeRef.current >= 50) {
                lastUpdateTimeRef.current = now;

                // Use flushSync ONLY for streamingContent to force immediate update
                // This is necessary because XHR onprogress doesn't trigger React re-renders
                flushSync(() => {
                  setStreamingContent(streamingContentRef.current);
                });

                // Update isThinking without flushSync
                setIsThinking(false);
              }
            } else if (event === 'done') {
              // Final update with complete content before clearing
              flushSync(() => {
                setStreamingContent(streamingContentRef.current);
              });

              // Small delay to allow voice modal to capture final content
              setTimeout(() => {
                setStreamingContent('');
                setIsThinking(false);
                streamingContentRef.current = '';
                void loadMessages();
              }, 100);
            } else if (event === 'error') {
              console.error('Streaming error:', parsed.error);
              setError(parsed.error || 'Streaming error occurred');
              setIsThinking(false);
            }
          } catch (parseErr) {
            console.error('Failed to parse SSE event:', parseErr);
          }
        };

        const parseSSE = (text: string) => {
          const lines = text.split('\n');
          let currentEvent = '';
          let currentData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              currentData = line.slice(6).trim();
            } else if (line === '' || line === '\r') {
              if (currentEvent && currentData) {
                processEvent(currentEvent, currentData);
                currentEvent = '';
                currentData = '';
              }
            }
          }
        };

        xhr.onprogress = () => {
          chunkCount++;
          const newText = xhr.responseText.substring(lastProcessedIndex);

          if (newText) {
            buffer += newText;
            lastProcessedIndex = xhr.responseText.length;
            parseSSE(newText);
          }
        };

        xhr.onload = () => {
          setSending(false);
          setStreaming(false);
          onStreamingComplete?.();
          resolve();
        };

        xhr.onerror = () => {
          console.error('[FRONTEND] XHR Error');
          const errorMessage = 'Failed to send message';
          setError(errorMessage);
          setMessages(prev => prev.filter(m => m.id !== userMessage.id));
          setSending(false);
          setStreaming(false);
          reject(new Error(errorMessage));
        };

        xhr.onabort = () => {
          setError('Message sending cancelled');
          setSending(false);
          setStreaming(false);
          resolve();
        };

        // Store XHR for cancellation
        abortControllerRef.current = { abort: () => xhr.abort() } as any;

        xhr.send(JSON.stringify(requestBody));
      });
    } catch (err: any) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
      setSending(false);
      setStreaming(false);
      abortControllerRef.current = null;
    }
  }, [sessionId, hyperparams, onStreamingStart, onStreamingComplete, loadMessages]);

  // Generate title for the session
  const generateTitle = useCallback(async () => {
    if (!sessionId) return;

    try {
      await fetch(
        `${getApiBaseUrl()}/api/v1/chat/sessions/${sessionId}/generate-title`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );
      // Title is updated on the backend, the session list will refresh and pick it up
    } catch (err) {
      console.error('Failed to generate title:', err);
      // Not critical, just log it
    }
  }, [sessionId]);

  // Cancel ongoing message streaming
  const cancelStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Clean up streaming state
    streamingContentRef.current = '';
    setStreaming(false);
    setSending(false);
    setStreamingContent('');
    setIsThinking(false);
  }, []);

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
    setStreamingContent('');
    setIsThinking(false);
    streamingContentRef.current = '';
    setError(null);
  }, []);

  // Load messages when session changes
  useEffect(() => {
    void loadMessages();
  }, [loadMessages]);

  // Auto-generate title after 4 messages (2 exchanges)
  useEffect(() => {
    if (messages.length === 4 && sessionId) {
      void generateTitle();
    }
  }, [messages.length, sessionId, generateTitle]);

  return {
    // State
    messages,
    loading,
    sending,
    streaming,
    streamingContent,
    isThinking,
    error,

    // Actions
    sendMessage,
    cancelStreaming,
    clearMessages,
    reload: loadMessages,
  };
}
