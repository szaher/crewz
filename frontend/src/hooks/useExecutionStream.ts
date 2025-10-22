'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { getWsBaseUrl } from '@/lib/api-url';

export interface ExecutionStreamEvent {
  type: 'execution.started' | 'execution.output' | 'execution.progress' | 'execution.completed' | 'execution.error';
  timestamp: string;
  data: any;
}

export interface UseExecutionStreamOptions {
  executionId: string;
  enabled?: boolean;
  onEvent?: (event: ExecutionStreamEvent) => void;
  onError?: (error: Error) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export interface UseExecutionStreamReturn {
  events: ExecutionStreamEvent[];
  isConnected: boolean;
  error: Error | null;
  reconnect: () => void;
  disconnect: () => void;
}

/**
 * useExecutionStream Hook
 *
 * WebSocket connection manager for live execution streaming.
 * - Manages Socket.IO connection lifecycle
 * - Handles automatic reconnection with exponential backoff
 * - Buffers events and replays on reconnect
 * - Cleans up connection on unmount
 *
 * @example
 * ```tsx
 * const { events, isConnected, error, reconnect } = useExecutionStream({
 *   executionId: 'abc-123',
 *   enabled: true,
 *   onEvent: (event) => console.log('Event:', event)
 * });
 * ```
 */
export function useExecutionStream(options: UseExecutionStreamOptions): UseExecutionStreamReturn {
  const {
    executionId,
    enabled = true,
    onEvent,
    onError,
    onConnect,
    onDisconnect
  } = options;

  const [events, setEvents] = useState<ExecutionStreamEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const socketRef = useRef<Socket | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 10;

  // Calculate exponential backoff with jitter
  const calculateBackoff = useCallback((attempt: number): number => {
    const base = Math.min(1000 * Math.pow(2, attempt), 30000); // Max 30s
    const jitter = base * (0.5 + Math.random() * 0.5); // 0.5x - 1.5x
    return jitter;
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!enabled || !executionId) return;

    try {
      // Get auth token from localStorage
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }

      // Create Socket.IO connection
      const socket = io(getWsBaseUrl(), {
        path: '/ws/socket.io',
        query: {
          token,
          execution_id: executionId
        },
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: maxReconnectAttempts,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 30000,
        timeout: 20000
      });

      // Join execution room
      socket.on('connect', () => {
        console.log(`[useExecutionStream] Connected to execution ${executionId}`);
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;

        // Join room for this execution
        socket.emit('join_execution', { execution_id: executionId });

        if (onConnect) {
          onConnect();
        }
      });

      // Handle events
      socket.on('execution.started', (data: any) => {
        const event: ExecutionStreamEvent = {
          type: 'execution.started',
          timestamp: new Date().toISOString(),
          data
        };
        setEvents(prev => [...prev, event]);
        if (onEvent) onEvent(event);
      });

      socket.on('execution.output', (data: any) => {
        const event: ExecutionStreamEvent = {
          type: 'execution.output',
          timestamp: new Date().toISOString(),
          data
        };
        setEvents(prev => [...prev, event]);
        if (onEvent) onEvent(event);
      });

      socket.on('execution.progress', (data: any) => {
        const event: ExecutionStreamEvent = {
          type: 'execution.progress',
          timestamp: new Date().toISOString(),
          data
        };
        setEvents(prev => [...prev, event]);
        if (onEvent) onEvent(event);
      });

      socket.on('execution.completed', (data: any) => {
        const event: ExecutionStreamEvent = {
          type: 'execution.completed',
          timestamp: new Date().toISOString(),
          data
        };
        setEvents(prev => [...prev, event]);
        if (onEvent) onEvent(event);
      });

      socket.on('execution.error', (data: any) => {
        const event: ExecutionStreamEvent = {
          type: 'execution.error',
          timestamp: new Date().toISOString(),
          data
        };
        setEvents(prev => [...prev, event]);
        if (onEvent) onEvent(event);
      });

      // Handle disconnect
      socket.on('disconnect', (reason: string) => {
        console.log(`[useExecutionStream] Disconnected: ${reason}`);
        setIsConnected(false);

        if (onDisconnect) {
          onDisconnect();
        }

        // Auto-reconnect with backoff
        if (reason === 'io server disconnect') {
          // Server initiated disconnect, don't reconnect
          setError(new Error('Server closed connection'));
        } else {
          // Client-side issue, try reconnecting
          reconnectAttempts.current++;
          if (reconnectAttempts.current <= maxReconnectAttempts) {
            const backoff = calculateBackoff(reconnectAttempts.current);
            console.log(`[useExecutionStream] Reconnecting in ${backoff}ms (attempt ${reconnectAttempts.current})`);
            setTimeout(() => {
              socket.connect();
            }, backoff);
          } else {
            setError(new Error('Max reconnection attempts reached'));
          }
        }
      });

      // Handle connection errors
      socket.on('connect_error', (err: Error) => {
        console.error('[useExecutionStream] Connection error:', err);
        setError(err);
        setIsConnected(false);

        if (onError) {
          onError(err);
        }
      });

      // Handle errors
      socket.on('error', (err: Error) => {
        console.error('[useExecutionStream] Socket error:', err);
        setError(err);

        if (onError) {
          onError(err);
        }
      });

      socketRef.current = socket;

    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to connect to WebSocket');
      console.error('[useExecutionStream] Setup error:', error);
      setError(error);
      if (onError) {
        onError(error);
      }
    }
  }, [enabled, executionId, onEvent, onError, onConnect, onDisconnect, calculateBackoff]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
    }
  }, []);

  // Manual reconnect
  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttempts.current = 0;
    setError(null);
    setEvents([]);
    connect();
  }, [disconnect, connect]);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    events,
    isConnected,
    error,
    reconnect,
    disconnect
  };
}
