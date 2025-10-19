'use client';

import { useEffect, useState } from 'react';

interface QueuePositionProps {
  executionId: string;
  initialPosition?: number | null;
  initialEstimatedWait?: number | null;
}

/**
 * QueuePosition Component (T045)
 *
 * Displays execution queue position and estimated wait time.
 * - Shows position in queue (1, 2, 3, etc.)
 * - Shows estimated wait time in human-readable format
 * - Progress bar visualization
 * - Hidden if queue_position is null (execution not queued)
 * - Updates in real-time via polling or WebSocket
 */
export default function QueuePosition({
  executionId,
  initialPosition = null,
  initialEstimatedWait = null
}: QueuePositionProps) {
  const [position, setPosition] = useState<number | null>(initialPosition);
  const [estimatedWaitSeconds, setEstimatedWaitSeconds] = useState<number | null>(initialEstimatedWait);
  const [isLoading, setIsLoading] = useState(false);

  // Format estimated wait time
  const formatWaitTime = (seconds: number | null): string => {
    if (!seconds || seconds <= 0) return 'Starting soon';

    if (seconds < 60) return `~${Math.round(seconds)}s`;

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);

    if (minutes < 60) {
      return remainingSeconds > 0 ? `~${minutes}m ${remainingSeconds}s` : `~${minutes}m`;
    }

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes > 0 ? `~${hours}h ${remainingMinutes}m` : `~${hours}h`;
  };

  // Calculate progress (inverse of position - lower position = more progress)
  const calculateProgress = (pos: number | null): number => {
    if (!pos) return 0;
    if (pos === 1) return 90; // Almost there
    if (pos === 2) return 70;
    if (pos === 3) return 50;
    if (pos <= 5) return 30;
    if (pos <= 10) return 15;
    return 5;
  };

  // Poll for queue position updates
  useEffect(() => {
    if (position === null) return; // Not queued, don't poll

    const pollInterval = setInterval(async () => {
      try {
        const token = localStorage.getItem('token') || '';
        const response = await fetch(`http://localhost:8000/api/v1/executions/${executionId}/status`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const data = await response.json();

          // Update position and estimated wait
          if (data.queue_position !== undefined) {
            setPosition(data.queue_position);
          }

          // If no longer queued (position is null), stop polling
          if (data.queue_position === null) {
            setPosition(null);
          }
        }
      } catch (err) {
        console.error('[QueuePosition] Failed to fetch status:', err);
      }
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(pollInterval);
  }, [executionId, position]);

  // Don't render if not queued
  if (position === null || position === undefined) {
    return null;
  }

  const progress = calculateProgress(position);
  const waitTime = formatWaitTime(estimatedWaitSeconds);

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div className="flex items-start space-x-3">
        {/* Icon */}
        <div className="flex-shrink-0">
          <div className="bg-blue-100 rounded-full p-2">
            <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h4 className="text-sm font-medium text-blue-900">
                In Queue
              </h4>
              <p className="text-xs text-blue-700 mt-0.5">
                Position #{position} · Estimated wait: {waitTime}
              </p>
            </div>

            {isLoading && (
              <div className="flex-shrink-0">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              </div>
            )}
          </div>

          {/* Progress Bar */}
          <div className="mt-3">
            <div className="bg-blue-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-blue-600 h-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-blue-600 mt-1">
              {position === 1 ? 'Next in line' : `${position - 1} ${position === 2 ? 'job' : 'jobs'} ahead`}
            </p>
          </div>
        </div>
      </div>

      {/* Help Text */}
      {position > 5 && (
        <div className="mt-3 pt-3 border-t border-blue-200">
          <p className="text-xs text-blue-700">
            <span className="font-medium">Tip:</span> Your execution will start automatically when a worker becomes available.
          </p>
        </div>
      )}
    </div>
  );
}
