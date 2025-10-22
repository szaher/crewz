'use client';

import { io, Socket } from 'socket.io-client';
import { getApiBaseUrl } from '@/lib/api-url';

/**
 * WebSocket Client Service
 *
 * Socket.IO client singleton for managing WebSocket connections.
 * - Provides connection pooling and reuse
 * - Injects JWT authentication automatically
 * - Room management helpers
 * - Connection lifecycle management
 *
 * @example
 * ```ts
 * const client = WebSocketClient.getInstance();
 * const socket = client.connect();
 * client.joinRoom(socket, 'execution:abc-123');
 * ```
 */
class WebSocketClient {
  private static instance: WebSocketClient | null = null;
  private socket: Socket | null = null;
  private connecting: boolean = false;

  private constructor() {
    // Private constructor for singleton
  }

  /**
   * Get singleton instance
   */
  static getInstance(): WebSocketClient {
    if (!WebSocketClient.instance) {
      WebSocketClient.instance = new WebSocketClient();
    }
    return WebSocketClient.instance;
  }

  /**
   * Get auth token from localStorage
   */
  private getAuthToken(): string | null {
    if (typeof window === 'undefined') {
      return null;
    }
    return localStorage.getItem('token');
  }

  /**
   * Connect to WebSocket server
   * Returns existing connection if already connected
   */
  connect(options: {
    url?: string;
    path?: string;
    query?: Record<string, string>;
  } = {}): Socket {
    // Return existing connection if available
    if (this.socket && this.socket.connected) {
      console.log('[WebSocketClient] Reusing existing connection');
      return this.socket;
    }

    // If connection in progress, wait for it
    if (this.connecting && this.socket) {
      console.log('[WebSocketClient] Connection in progress, returning pending socket');
      return this.socket;
    }

    this.connecting = true;

    const {
      url = process.env.NEXT_PUBLIC_WS_URL || getApiBaseUrl(),
      path = '/ws/socket.io',
      query = {}
    } = options;

    // Get auth token
    const token = this.getAuthToken();
    if (!token) {
      console.warn('[WebSocketClient] No auth token found, connection may fail');
    }

    // Create Socket.IO connection with auth
    this.socket = io(url, {
      path,
      query: {
        token: token || '',
        ...query
      },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 30000,
      timeout: 20000,
      autoConnect: true
    });

    // Connection event handlers
    this.socket.on('connect', () => {
      console.log('[WebSocketClient] Connected to WebSocket server');
      this.connecting = false;
    });

    this.socket.on('disconnect', (reason: string) => {
      console.log(`[WebSocketClient] Disconnected: ${reason}`);
      this.connecting = false;
    });

    this.socket.on('connect_error', (error: Error) => {
      console.error('[WebSocketClient] Connection error:', error);
      this.connecting = false;
    });

    this.socket.on('error', (error: Error) => {
      console.error('[WebSocketClient] Socket error:', error);
    });

    return this.socket;
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.socket) {
      console.log('[WebSocketClient] Disconnecting from WebSocket server');
      this.socket.disconnect();
      this.socket = null;
      this.connecting = false;
    }
  }

  /**
   * Join a Socket.IO room
   */
  joinRoom(socket: Socket, roomName: string): void {
    if (!socket || !socket.connected) {
      console.warn('[WebSocketClient] Cannot join room: socket not connected');
      return;
    }

    console.log(`[WebSocketClient] Joining room: ${roomName}`);
    socket.emit('join_room', { room: roomName });
  }

  /**
   * Leave a Socket.IO room
   */
  leaveRoom(socket: Socket, roomName: string): void {
    if (!socket || !socket.connected) {
      console.warn('[WebSocketClient] Cannot leave room: socket not connected');
      return;
    }

    console.log(`[WebSocketClient] Leaving room: ${roomName}`);
    socket.emit('leave_room', { room: roomName });
  }

  /**
   * Get current socket instance
   */
  getSocket(): Socket | null {
    return this.socket;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.socket !== null && this.socket.connected;
  }

  /**
   * Update auth token and reconnect
   */
  updateToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token);
    }

    // Reconnect with new token
    if (this.socket) {
      this.disconnect();
      this.connect();
    }
  }
}

// Export singleton instance
export const websocketClient = WebSocketClient.getInstance();

// Export class for testing
export { WebSocketClient };
