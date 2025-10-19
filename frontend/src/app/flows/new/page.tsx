'use client';

import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import FlowForm from '@/components/flows/FlowForm';

export default function NewFlowPage() {
  const router = useRouter();

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto p-6">
            <Breadcrumbs />
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
              Create New Flow
            </h1>
            <FlowForm
              onSuccess={(flow) => router.push(`/flows/${flow.id}`)}
              onCancel={() => router.push('/flows')}
            />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
