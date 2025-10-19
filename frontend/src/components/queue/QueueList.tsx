"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useToast } from "@/components/shared/Toast";
import { useAuthStore } from "@/lib/store";

interface QueueItem {
  execution_id: string;
  execution_type: string;
  entity_id: string;
  entity_name: string | null;
  status: string;
  priority: number;
  queue_position: number | null;
  worker_id: string | null;
  created_at: string;
  started_at: string | null;
  retry_count: number;
  max_retries: number;
}

interface QueueListProps {
  statusFilter: "queued" | "running" | "all";
  refreshTrigger: number;
}

export function QueueList({ statusFilter, refreshTrigger }: QueueListProps) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [cancellingIds, setCancellingIds] = useState<Set<string>>(new Set());
  const { showToast } = useToast();
  const { token } = useAuthStore();

  useEffect(() => {
    if (token) {
      fetchQueueItems();
    }
  }, [statusFilter, refreshTrigger, token]);

  const fetchQueueItems = async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        status_filter: statusFilter,
        skip: "0",
        limit: "50",
      });

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/executions/queue/list?${params}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch queue items: ${response.statusText}`);
      }

      const data = await response.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      console.error("Error fetching queue items:", err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "queued":
        return "bg-yellow-100 text-yellow-800";
      case "running":
        return "bg-blue-100 text-blue-800";
      case "completed":
        return "bg-green-100 text-green-800";
      case "failed":
        return "bg-red-100 text-red-800";
      case "cancelled":
        return "bg-gray-100 text-gray-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getPriorityLabel = (priority: number) => {
    if (priority <= 3) return "High";
    if (priority <= 6) return "Normal";
    return "Low";
  };

  const getPriorityColor = (priority: number) => {
    if (priority <= 3) return "text-red-600 font-semibold";
    if (priority <= 6) return "text-blue-600";
    return "text-gray-600";
  };

  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return "N/A";
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getTimeAgo = (timestamp: string) => {
    const now = new Date();
    const then = new Date(timestamp);
    const seconds = Math.floor((now.getTime() - then.getTime()) / 1000);

    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  const handleCancel = async (executionId: string) => {
    if (!token) {
      showToast("Authentication required", "error");
      return;
    }

    if (!confirm("Are you sure you want to cancel this execution?")) {
      return;
    }

    setCancellingIds((prev) => new Set(prev).add(executionId));

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/executions/${executionId}/cancel`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to cancel execution: ${response.statusText}`);
      }

      // Refresh the list
      fetchQueueItems();
      showToast("Execution cancelled successfully", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to cancel execution", "error");
      console.error("Error cancelling execution:", err);
    } finally {
      setCancellingIds((prev) => {
        const next = new Set(prev);
        next.delete(executionId);
        return next;
      });
    }
  };

  if (loading && items.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading queue items...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
        <p className="font-semibold">Error loading queue items</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <p className="text-gray-600">No items in the queue</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <p className="text-sm text-gray-600">
          Showing {items.length} of {total} items
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Entity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Priority
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Queue Position
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Retries
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {items.map((item) => (
              <tr key={item.execution_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(
                      item.status
                    )}`}
                  >
                    {item.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {item.execution_type}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <div>
                    <p className="text-gray-900 font-medium">
                      {item.entity_name || "Unnamed"}
                    </p>
                    <p className="text-gray-500 text-xs">{item.entity_id?.slice(0, 8)}...</p>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span className={getPriorityColor(item.priority)}>
                    {getPriorityLabel(item.priority)} ({item.priority})
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {item.queue_position !== null ? `#${item.queue_position}` : "—"}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <div>
                    <p>{getTimeAgo(item.created_at)}</p>
                    <p className="text-xs text-gray-400">{formatTime(item.created_at)}</p>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {item.retry_count} / {item.max_retries}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div className="flex items-center gap-3">
                    <Link
                      href={`/executions/${item.execution_id}`}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      View
                    </Link>
                    {(item.status === "queued" || item.status === "running") && (
                      <button
                        onClick={() => handleCancel(item.execution_id)}
                        disabled={cancellingIds.has(item.execution_id)}
                        className="text-red-600 hover:text-red-900 disabled:opacity-50"
                        title="Cancel execution"
                      >
                        {cancellingIds.has(item.execution_id) ? "Cancelling..." : "Cancel"}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
