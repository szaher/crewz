'use client';

import { useEffect, useState, useRef } from 'react';
import SSEClient from '@/lib/sse-client';
import { useAuthStore } from '@/lib/store';
import type { ExecutionEvent } from '@/types/api';

interface ExecutionLogsProps {
  executionId: number;
}

export default function ExecutionLogs({ executionId }: ExecutionLogsProps) {
  const { token } = useAuthStore();
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const sseClient = useRef<SSEClient | null>(null);

  useEffect(() => {
    if (!token) return;

    const client = new SSEClient();
    sseClient.current = client;

    client.connect(
      executionId,
      token,
      (event: ExecutionEvent) => {
        setEvents((prev) => [...prev, event]);
        setConnected(true);
      },
      (error) => {
        console.error('SSE error:', error);
        setConnected(false);
      }
    );

    return () => {
      client.disconnect();
    };
  }, [executionId, token]);

  // Auto-scroll to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'connected': return '🔗';
      case 'execution_started': return '▶️';
      case 'node_started': return '⚙️';
      case 'node_completed': return '✅';
      case 'node_failed': return '❌';
      case 'execution_completed': return '🎉';
      case 'execution_failed': return '💥';
      case 'execution_cancelled': return '🛑';
      case 'error': return '⚠️';
      default: return '📝';
    }
  };

  const getEventColor = (type: string) => {
    switch (type) {
      case 'execution_completed':
      case 'node_completed':
        return 'text-green-800 bg-green-50 border-green-200';
      case 'execution_failed':
      case 'node_failed':
      case 'error':
        return 'text-red-800 bg-red-50 border-red-200';
      case 'execution_started':
      case 'node_started':
        return 'text-blue-800 bg-blue-50 border-blue-200';
      case 'execution_cancelled':
        return 'text-gray-800 bg-gray-50 border-gray-200';
      default:
        return 'text-gray-800 bg-white border-gray-200';
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Live Execution Logs</h3>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-gray-300'}`}></div>
          <span className="text-sm text-gray-500">
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Logs */}
      <div className="p-6 max-h-96 overflow-y-auto space-y-2">
        {events.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            Waiting for execution events...
          </p>
        ) : (
          events.map((event, index) => (
            <div
              key={index}
              className={`p-3 rounded border ${getEventColor(event.type)}`}
            >
              <div className="flex items-start gap-3">
                <span className="text-lg">{getEventIcon(event.type)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium capitalize">
                      {event.type.replace(/_/g, ' ')}
                    </p>
                    {event.timestamp && (
                      <span className="text-xs opacity-75">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                  {event.node_id && (
                    <p className="text-xs mt-1 opacity-75">
                      Node: {event.node_id} {event.node_type && `(${event.node_type})`}
                    </p>
                  )}
                  {event.error && (
                    <p className="text-sm mt-2 font-mono">{event.error}</p>
                  )}
                  {event.output && (
                    <pre className="text-xs mt-2 overflow-x-auto">
                      {JSON.stringify(event.output, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}
