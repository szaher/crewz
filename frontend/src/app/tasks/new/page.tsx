'use client';

import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import TaskForm from '@/components/tasks/TaskForm';
import { TaskCreate } from '@/types/task';
import { getApiBaseUrl } from '@/lib/api-url';

export default function NewTaskPage() {
  const router = useRouter();
  const { token } = useAuthStore();

  const handleSave = async (taskData: TaskCreate) => {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/tasks`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(taskData),
    });

    if (!response.ok) {
      throw new Error('Failed to create task');
    }

    const task = await response.json();
    router.push('/tasks');
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto p-6">
            <Breadcrumbs />
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
              Create New Task
            </h1>
            <TaskForm
              onSave={handleSave}
              onCancel={() => router.push('/tasks')}
            />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
