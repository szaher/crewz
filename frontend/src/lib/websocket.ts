/**
 * WebSocket client for real-time chat communication
 * Uses Socket.IO for bidirectional messaging
 */

import { io, Socket } from 'socket.io-client';

export interface ChatMessage {
  id: string;
  session_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface ChatEvent {
  type: 'message' | 'typing' | 'error';
  data: ChatMessage | { typing: boolean } | { error: string };
}

export type MessageCallback = (event: ChatEvent) => void;

class WebSocketClient {
  private socket: Socket | null = null;
  private baseUrl: string;

  constructor(baseUrl: string = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  /**
   * Connect to WebSocket server
   */
  connect(token: string, callbacks?: {
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Error) => void;
  }) {
    this.socket = io(this.baseUrl, {
      auth: {
        token,
      },
      transports: ['websocket', 'polling'],
    });

    if (callbacks?.onConnect) {
      this.socket.on('connect', callbacks.onConnect);
    }

    if (callbacks?.onDisconnect) {
      this.socket.on('disconnect', callbacks.onDisconnect);
    }

    if (callbacks?.onError) {
      this.socket.on('error', callbacks.onError);
    }

    return this;
  }

  /**
   * Join a chat session room
   */
  joinSession(sessionId: number) {
    if (this.socket) {
      this.socket.emit('join_session', { session_id: sessionId });
    }
  }

  /**
   * Leave a chat session room
   */
  leaveSession(sessionId: number) {
    if (this.socket) {
      this.socket.emit('leave_session', { session_id: sessionId });
    }
  }

  /**
   * Send a message
   */
  sendMessage(sessionId: number, content: string) {
    if (this.socket) {
      this.socket.emit('send_message', {
        session_id: sessionId,
        content,
      });
    }
  }

  /**
   * Listen for messages
   */
  onMessage(callback: MessageCallback) {
    if (this.socket) {
      this.socket.on('message', (data: ChatMessage) => {
        callback({ type: 'message', data });
      });
    }
  }

  /**
   * Listen for typing indicators
   */
  onTyping(callback: (data: { session_id: number; typing: boolean }) => void) {
    if (this.socket) {
      this.socket.on('typing', callback);
    }
  }

  /**
   * Send typing indicator
   */
  sendTyping(sessionId: number, typing: boolean) {
    if (this.socket) {
      this.socket.emit('typing', { session_id: sessionId, typing });
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.socket !== null && this.socket.connected;
  }
}

export default WebSocketClient;
