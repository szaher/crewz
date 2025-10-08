'use client';

import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import MetricsDashboard from '@/components/observability/MetricsDashboard';

export default function ObservabilityPage() {
  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="p-6">
            <MetricsDashboard />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
