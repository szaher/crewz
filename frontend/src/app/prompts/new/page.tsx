'use client';

import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import PromptEditor from '@/components/prompts/PromptEditor';

export default function NewPromptPage() {
  const router = useRouter();

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto p-6">
            <Breadcrumbs />
            <h1 className="text-3xl font-bold text-gray-900 mb-6">
              Create New Prompt
            </h1>
            <PromptEditor
              onSave={(prompt) => {
                router.push(`/prompts/${prompt.id}`);
              }}
              onCancel={() => router.push('/prompts')}
            />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
