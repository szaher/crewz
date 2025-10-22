/**
 * SSE client for user notifications
 */

import { getApiBaseUrl } from './api-url';

export interface IncomingNotificationEvent {
  type: 'success' | 'error' | 'info' | 'warning' | 'connected' | 'error';
  title?: string;
  message?: string;
  data?: any;
  timestamp?: string;
}

class NotificationsClient {
  private eventSource: EventSource | null = null;

  constructor() {
    // No baseUrl stored - get it dynamically on connect
  }

  connect(token: string, onEvent: (e: IncomingNotificationEvent) => void, onError?: (error: Event) => void) {
    const url = `${getApiBaseUrl()}/api/v1/notifications/stream?token=${encodeURIComponent(token)}`;
    this.eventSource = new EventSource(url);

    this.eventSource.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        onEvent(data);
      } catch {
        // ignore
      }
    };

    this.eventSource.onerror = (err) => {
      if (onError) onError(err);
      this.disconnect();
    };
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

export default NotificationsClient;

