'use client';

import { useEffect, useRef, useState } from 'react';
import { useAuthStore } from '@/lib/store';
import { getWsBaseUrl } from '@/lib/api-url';

interface ExecutionStreamEvent {
  event: string;
  line?: string;
  timestamp?: string;
  stream_type?: 'stdout' | 'stderr';
  message?: string;
  percent?: number;
  current_step?: string;
  total_steps?: number;
  worker_id?: string;
  status?: string;
  result_summary?: string;
  error_type?: string;
  traceback?: string;
}

interface LiveExecutionStreamProps {
  executionId: string;
  enabled?: boolean; // Feature flag - shows message if false
}

/**
 * LiveExecutionStream Component (T044)
 *
 * Real-time execution output streaming via WebSocket.
 * - WebSocket connection to /ws/executions/{id}/stream
 * - Displays output lines with color coding (stdout/stderr)
 * - Auto-scroll to bottom as new lines arrive
 * - Reconnection with exponential backoff
 * - Shows "Live streaming not enabled" if feature flag is false
 */
export default function LiveExecutionStream({ executionId, enabled = false }: LiveExecutionStreamProps) {
  const { token } = useAuthStore();
  const [lines, setLines] = useState<Array<{ text: string; type: 'stdout' | 'stderr'; timestamp?: string }>>([]);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [isReplayMode, setIsReplayMode] = useState(false);
  const [progress, setProgress] = useState<{ percent: number; step: string } | null>(null);
  const [workerInfo, setWorkerInfo] = useState<string | null>(null);
  const streamContainerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    if (streamContainerRef.current) {
      streamContainerRef.current.scrollTop = streamContainerRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [lines]);

  // WebSocket connection with reconnection logic
  useEffect(() => {
    if (!enabled) {
      return; // Don't connect if feature not enabled
    }

    const connect = () => {
      try {
        setConnectionStatus('connecting');

        // Check if token is available
        if (!token) {
          console.error('[LiveStream] No authentication token available');
          setConnectionStatus('error');
          return;
        }

        // WebSocket URL with token
        const wsUrl = getWsBaseUrl();
        const ws = new WebSocket(`${wsUrl}/ws/executions/${executionId}/stream?token=${token}`);

        ws.onopen = () => {
          console.log('[LiveStream] WebSocket connected');
          setConnectionStatus('connected');
          reconnectAttempts.current = 0; // Reset on successful connection
        };

        ws.onmessage = (event) => {
          try {
            const data: ExecutionStreamEvent = JSON.parse(event.data);

            // Handle different event types
            switch (data.event) {
              case 'connection':
                console.log('[LiveStream] Connection acknowledged');
                break;

              case 'replay.start':
                console.log(`[LiveStream] Replaying ${data.message || 0} buffered lines`);
                setIsReplayMode(true);
                break;

              case 'replay.complete':
                console.log('[LiveStream] Replay complete');
                setIsReplayMode(false);
                break;

              case 'execution.output':
                if (data.line) {
                  setLines(prev => [...prev, {
                    text: data.line!,
                    type: data.stream_type || 'stdout',
                    timestamp: data.timestamp
                  }]);
                }
                break;

              case 'execution.started':
                setWorkerInfo(data.worker_id || 'Unknown worker');
                setLines(prev => [...prev, {
                  text: `>>> Execution started on worker: ${data.worker_id || 'unknown'}`,
                  type: 'stdout',
                  timestamp: data.timestamp
                }]);
                break;

              case 'execution.progress':
                if (data.percent !== undefined && data.current_step) {
                  setProgress({ percent: data.percent, step: data.current_step });
                }
                break;

              case 'execution.completed':
                setProgress({ percent: 100, step: 'Completed' });
                setLines(prev => [...prev, {
                  text: `>>> Execution completed: ${data.result_summary || 'Success'}`,
                  type: 'stdout',
                  timestamp: data.timestamp
                }]);
                break;

              case 'execution.error':
                setProgress(null);
                setLines(prev => [...prev, {
                  text: `>>> Execution failed: ${data.message || 'Unknown error'}`,
                  type: 'stderr',
                  timestamp: data.timestamp
                }]);
                if (data.traceback) {
                  setLines(prev => [...prev, {
                    text: data.traceback!,
                    type: 'stderr',
                    timestamp: data.timestamp
                  }]);
                }
                break;

              case 'pong':
                // Heartbeat response
                break;

              default:
                console.log('[LiveStream] Unknown event:', data.event);
            }
          } catch (err) {
            console.error('[LiveStream] Failed to parse message:', err);
          }
        };

        ws.onerror = (error) => {
          console.error('[LiveStream] WebSocket error:', error);
          setConnectionStatus('error');
        };

        ws.onclose = () => {
          console.log('[LiveStream] WebSocket disconnected');
          setConnectionStatus('disconnected');

          // Attempt reconnection with exponential backoff
          if (reconnectAttempts.current < maxReconnectAttempts) {
            const backoffDelay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
            console.log(`[LiveStream] Reconnecting in ${backoffDelay}ms (attempt ${reconnectAttempts.current + 1}/${maxReconnectAttempts})`);

            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectAttempts.current += 1;
              connect();
            }, backoffDelay);
          } else {
            console.log('[LiveStream] Max reconnection attempts reached');
            setConnectionStatus('error');
          }
        };

        wsRef.current = ws;

        // Send periodic pings to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000); // Every 30 seconds

        return () => {
          clearInterval(pingInterval);
        };

      } catch (err) {
        console.error('[LiveStream] Failed to connect:', err);
        setConnectionStatus('error');
      }
    };

    connect();

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [executionId, enabled, token]);

  // Feature flag disabled
  if (!enabled) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
        <div className="text-gray-500">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <p className="text-lg font-medium text-gray-900">Live Streaming Not Enabled</p>
          <p className="mt-1 text-sm text-gray-500">
            Real-time execution streaming is currently disabled. Contact your administrator to enable this feature.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gray-50 border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-3">
            <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <h3 className="text-sm font-medium text-gray-900">Live Execution Stream</h3>
            {workerInfo && (
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                Worker: {workerInfo}
              </span>
            )}
          </div>

          {/* Connection Status */}
          <div className="flex items-center space-x-2">
            {isReplayMode && (
              <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                Replaying buffered output...
              </span>
            )}
            <div className="flex items-center space-x-2">
              <div className={`h-2 w-2 rounded-full ${
                connectionStatus === 'connected' ? 'bg-green-500' :
                connectionStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' :
                connectionStatus === 'error' ? 'bg-red-500' :
                'bg-gray-400'
              }`} />
              <span className="text-xs text-gray-600 capitalize">{connectionStatus}</span>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        {progress && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-600">{progress.step}</span>
              <span className="text-gray-600 font-medium">{progress.percent}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress.percent}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Stream Output */}
      <div
        ref={streamContainerRef}
        className="bg-gray-900 text-gray-100 font-mono text-sm p-4 h-96 overflow-y-auto"
        style={{ fontFamily: 'Monaco, Consolas, "Courier New", monospace' }}
      >
        {lines.length === 0 ? (
          <div className="text-gray-500 italic">Waiting for output...</div>
        ) : (
          lines.map((line, index) => (
            <div
              key={index}
              className={`py-0.5 ${line.type === 'stderr' ? 'text-red-400' : 'text-gray-100'}`}
            >
              {line.text}
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="bg-gray-50 border-t border-gray-200 px-4 py-2 flex items-center justify-between text-xs text-gray-500">
        <span>{lines.length} lines</span>
        <button
          onClick={scrollToBottom}
          className="text-blue-600 hover:text-blue-700 font-medium"
        >
          Scroll to bottom ↓
        </button>
      </div>
    </div>
  );
}
