"use client";

import { useState, useEffect } from "react";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import Navigation from "@/components/shared/Navigation";
import Breadcrumbs from "@/components/navigation/Breadcrumbs";
import { QueueList } from "@/components/queue/QueueList";
import { QueueMetrics } from "@/components/queue/QueueMetrics";

export default function QueuePage() {
  const [statusFilter, setStatusFilter] = useState<"queued" | "running" | "all">("all");
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setRefreshTrigger((prev) => prev + 1);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <Breadcrumbs />

            <div className="mb-8">
              <h1 className="text-3xl font-bold mb-2">Execution Queue</h1>
              <p className="text-gray-600 dark:text-gray-400">
                Monitor and manage your queued and running executions
              </p>
            </div>

            {/* Queue Metrics */}
            <QueueMetrics refreshTrigger={refreshTrigger} />

            {/* Filters */}
            <div className="mb-6 flex gap-4">
              <div className="flex gap-2">
                <button
                  onClick={() => setStatusFilter("all")}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    statusFilter === "all"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setStatusFilter("queued")}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    statusFilter === "queued"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  }`}
                >
                  Queued
                </button>
                <button
                  onClick={() => setStatusFilter("running")}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    statusFilter === "running"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  }`}
                >
                  Running
                </button>
              </div>

              <button
                onClick={() => setRefreshTrigger((prev) => prev + 1)}
                className="ml-auto px-4 py-2 rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300 transition-colors dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
              >
                Refresh
              </button>
            </div>

            {/* Queue List */}
            <QueueList statusFilter={statusFilter} refreshTrigger={refreshTrigger} />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
