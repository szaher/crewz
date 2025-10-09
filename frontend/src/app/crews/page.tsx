'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import CrewBuilder from '@/components/crews/CrewBuilder';
import { useCrews } from '@/lib/hooks/useCrews';

export default function CrewsPage() {
  const router = useRouter();
  const { crews, loading: crewsLoading, error: crewsError, refetch: refetchCrews } = useCrews();
  const searchParams = useSearchParams();
  const loading = crewsLoading;
  const error = crewsError;

  const [showCrewBuilder, setShowCrewBuilder] = useState(false);
  const [editingCrewId, setEditingCrewId] = useState<number | undefined>();

  const loadData = () => {
    refetchCrews();
  };

  // Apply deep-linking filters via query params
  const managerFilter = searchParams?.get('manager_llm_provider_id');

  useEffect(() => {
    // no-op, keeping param for deep linking support if needed
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [managerFilter]);

  const clearFilter = () => {
    // Remove query params by navigating to base route
    router.push('/crews');
  };

  const handleCreateCrew = () => {
    setEditingCrewId(undefined);
    setShowCrewBuilder(true);
  };

  const handleEditCrew = (crewId: number) => {
    setEditingCrewId(crewId);
    setShowCrewBuilder(true);
  };

  const handleSaveCrew = (crewId: number) => {
    setShowCrewBuilder(false);
    void loadData();
  };

  if (showCrewBuilder) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="p-6">
              <Breadcrumbs />
            </div>
            <CrewBuilder
              crewId={editingCrewId}
              onSave={handleSaveCrew}
            />
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
          <div className="max-w-7xl mx-auto p-6">
        <Breadcrumbs />
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-gray-900">Crews</h1>
          <div className="flex gap-2">
            <button
              onClick={handleCreateCrew}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              Create Crew
            </button>
          </div>
        </div>

        {managerFilter && (
          <div className="mb-4 flex items-center gap-3">
            <span className="text-sm text-gray-600">Active filter:</span>
            <span className="inline-flex items-center gap-2 text-xs bg-purple-50 text-purple-700 border border-purple-200 px-2 py-1 rounded">
              Crews · manager provider #{managerFilter}
              <button
                onClick={clearFilter}
                className="ml-1 text-purple-700 hover:text-purple-900"
                aria-label="Clear filter"
                title="Clear filter"
              >
                ✕
              </button>
            </span>
          </div>
        )}

        {/* Content */}
        {error ? (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="text-center max-w-md">
              <p className="text-red-600 mb-4">Failed to load data: {error}</p>
              <button
                onClick={loadData}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          crews.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <p className="text-gray-500 mb-4">No crews yet. Create your first crew to get started.</p>
              <button
                onClick={handleCreateCrew}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                Create Crew
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {(managerFilter
                ? crews.filter((c: any) => (c as any).manager_llm_provider_id === Number(managerFilter))
                : crews
              ).map((crew) => (
              <div
                key={crew.id}
                className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow"
              >
                <h3 className="text-lg font-semibold text-gray-900">{crew.name}</h3>
                <p className="text-sm text-gray-600 mt-2">{crew.description}</p>
                <div className="mt-4 flex items-center gap-2">
                  <span className="px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-800">
                    {crew.process_type}
                  </span>
                  <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800">
                    {crew.agent_ids.length} agent{crew.agent_ids.length !== 1 ? 's' : ''}
                  </span>
                </div>
                <button
                  onClick={() => handleEditCrew(crew.id)}
                  className="mt-4 w-full px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
                >
                  Edit Crew
                </button>
              </div>
            ))}
          </div>
          )
        )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
