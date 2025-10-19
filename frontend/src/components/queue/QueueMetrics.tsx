"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/lib/store";

interface QueueMetricsProps {
  refreshTrigger: number;
}

interface Metrics {
  queue_depth: number;
  pending_count: number;
  running_count: number;
  completed_last_minute: number;
  failed_last_minute: number;
  processing_rate: number;
  avg_duration_ms: number;
  failure_rate: number;
}

export function QueueMetrics({ refreshTrigger }: QueueMetricsProps) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const { token } = useAuthStore();

  useEffect(() => {
    if (token) {
      fetchMetrics();
    }
  }, [refreshTrigger, token]);

  const fetchMetrics = async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/executions/queue/metrics?timeframe=5m`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setMetrics(data);
      } else {
        console.error("Failed to fetch metrics:", response.statusText);
      }
    } catch (err) {
      console.error("Error fetching metrics:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !metrics) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-sm text-gray-600 mb-1">Queue Depth</p>
        <p className="text-3xl font-bold text-gray-900">{metrics.queue_depth}</p>
        <p className="text-sm text-gray-500 mt-1">
          {metrics.pending_count} pending, {metrics.running_count} running
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-sm text-gray-600 mb-1">Processing Rate</p>
        <p className="text-3xl font-bold text-gray-900">
          {metrics.processing_rate.toFixed(2)}
        </p>
        <p className="text-sm text-gray-500 mt-1">tasks/second</p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-sm text-gray-600 mb-1">Avg Duration</p>
        <p className="text-3xl font-bold text-gray-900">
          {(metrics.avg_duration_ms / 1000).toFixed(1)}s
        </p>
        <p className="text-sm text-gray-500 mt-1">average execution time</p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-sm text-gray-600 mb-1">Failure Rate</p>
        <p
          className={`text-3xl font-bold ${
            metrics.failure_rate > 0.1 ? "text-red-600" : "text-green-600"
          }`}
        >
          {(metrics.failure_rate * 100).toFixed(1)}%
        </p>
        <p className="text-sm text-gray-500 mt-1">
          {metrics.failed_last_minute} failures in 5m
        </p>
      </div>
    </div>
  );
}
