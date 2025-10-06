'use client';

import ProtectedRoute from '@/components/auth/ProtectedRoute';
import MetricsDashboard from '@/components/observability/MetricsDashboard';

export default function ObservabilityPage() {
  return (
    <ProtectedRoute>
      <div className="p-6">
        <MetricsDashboard />
      </div>
    </ProtectedRoute>
  );
}
