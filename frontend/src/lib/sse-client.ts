/**
 * Server-Sent Events (SSE) client for execution streaming
 * Handles real-time updates from backend execution events
 */

import { getApiBaseUrl } from './api-url';

export interface ExecutionEvent {
  type: 'connected' | 'execution_started' | 'node_started' | 'node_completed' | 'node_failed' | 'execution_completed' | 'execution_failed' | 'execution_cancelled' | 'error';
  execution_id?: number;
  node_id?: string;
  node_type?: string;
  output?: any;
  error?: string;
  timestamp?: string;
  data?: any;
}

export type EventCallback = (event: ExecutionEvent) => void;

class SSEClient {
  private eventSource: EventSource | null = null;

  constructor() {
    // No baseUrl stored - get it dynamically on connect
  }

  /**
   * Connect to execution event stream
   */
  connect(executionId: number, token: string, onEvent: EventCallback, onError?: (error: Event) => void) {
    const url = `${getApiBaseUrl()}/api/v1/executions/${executionId}/stream?token=${encodeURIComponent(token)}`;

    // Create EventSource with authorization header (not supported natively, so we append as query param alternative)
    // Note: For production, consider using a library that supports custom headers or implement token via query param
    this.eventSource = new EventSource(url);

    this.eventSource.onmessage = (event) => {
      try {
        const data: ExecutionEvent = JSON.parse(event.data);
        onEvent(data);
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      if (onError) {
        onError(error);
      }
      this.disconnect();
    };

    return this;
  }

  /**
   * Disconnect from event stream
   */
  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.eventSource !== null && this.eventSource.readyState === EventSource.OPEN;
  }
}

export default SSEClient;
