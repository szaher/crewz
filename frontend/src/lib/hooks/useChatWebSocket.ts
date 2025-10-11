import { useEffect, useRef, useCallback, useState } from 'react';
import type { ChatMessage } from '@/types/api';

interface UseChatWebSocketProps {
  sessionId: number;
  token: string | null;
  onMessage: (message: ChatMessage) => void;
  onStatusChange?: (status: 'thinking' | 'responding') => void;
  onError?: (error: string) => void;
}

export function useChatWebSocket({
  sessionId,
  token,
  onMessage,
  onStatusChange,
  onError,
}: UseChatWebSocketProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const draftMessageRef = useRef<{ id: string; content: string } | null>(null);

  const connect = useCallback(() => {
    if (!token || isConnecting || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsConnecting(true);

    // Determine WebSocket URL based on environment
    let wsUrl: string;
    if (typeof window !== 'undefined') {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      // Extract host from API URL
      const apiHost = apiUrl.replace(/^https?:\/\//, '');
      // Determine protocol based on current page protocol
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${apiHost}/api/v1/chat/sessions/${sessionId}/ws?token=${encodeURIComponent(token)}`;
    } else {
      wsUrl = `ws://localhost:8000/api/v1/chat/sessions/${sessionId}/ws?token=${encodeURIComponent(token)}`;
    }

    console.log('[WS] Connecting to:', wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Connected');
      setIsConnected(true);
      setIsConnecting(false);
      reconnectAttempts.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[WS] Received:', data);

        switch (data.type) {
          case 'status':
            if (data.state === 'thinking') {
              onStatusChange?.('thinking');
              // Create draft message
              draftMessageRef.current = {
                id: `draft-${Date.now()}`,
                content: '',
              };
            }
            break;

          case 'delta':
            if (draftMessageRef.current && data.token) {
              draftMessageRef.current.content += data.token;
              onStatusChange?.('responding');

              // Send updated draft message
              onMessage({
                id: draftMessageRef.current.id,
                session_id: sessionId,
                role: 'assistant',
                content: draftMessageRef.current.content,
                created_at: new Date().toISOString(),
                metadata: {},
              } as ChatMessage);
            }
            break;

          case 'done':
            console.log('[WS] Stream complete, length:', data.length);
            draftMessageRef.current = null;
            onStatusChange?.(undefined as any);
            break;

          case 'error':
            console.error('[WS] Error:', data.message);
            onError?.(data.message);
            break;
        }
      } catch (err) {
        console.error('[WS] Failed to parse message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
      setIsConnecting(false);
    };

    ws.onclose = (event) => {
      console.log('[WS] Closed:', event.code, event.reason);
      setIsConnected(false);
      setIsConnecting(false);
      wsRef.current = null;

      // Attempt reconnection if not a normal closure
      if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current++;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`);

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    };
  }, [sessionId, token, onMessage, onStatusChange, onError, isConnecting]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  const sendMessage = useCallback((content: string, storeUser = true) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('[WS] Cannot send message - not connected');
      onError?.('Not connected to server');
      return;
    }

    const message = {
      type: 'message',
      content,
      store_user: storeUser,
    };

    console.log('[WS] Sending:', message);
    wsRef.current.send(JSON.stringify(message));
  }, [onError]);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    isConnecting,
    sendMessage,
    connect,
    disconnect,
  };
}
