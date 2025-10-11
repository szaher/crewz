'use client';

import { useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import PromptEditor from '@/components/prompts/PromptEditor';
import PromptViewer from '@/components/prompts/PromptViewer';

export default function PromptDetailPage() {
  const router = useRouter();
  const params = useParams();
  const promptId = params?.id as string;
  const [isEditing, setIsEditing] = useState(false);

  if (isEditing) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-4xl mx-auto p-6">
              <Breadcrumbs />
              <h1 className="text-3xl font-bold text-gray-900 mb-6">
                Edit Prompt
              </h1>
              <PromptEditor
                promptId={promptId}
                onSave={() => {
                  setIsEditing(false);
                }}
                onCancel={() => setIsEditing(false)}
              />
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto p-6">
            <Breadcrumbs />
            <PromptViewer
              promptId={promptId}
              onEdit={() => setIsEditing(true)}
              onDelete={() => router.push('/prompts')}
            />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
