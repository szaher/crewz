'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { useLLMProviders, type LLMProvider as ProviderItem } from '@/lib/hooks/useLLMProviders';
import { apiClient } from '@/lib/api-client';

export default function ProvidersPage() {
  const router = useRouter();
  const { providers, loading, error, deleteProvider, testConnection, setDefault, refetch } = useLLMProviders();
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<Record<number, { ok: boolean; message: string; at: string }>>({});
  const [usage, setUsage] = useState<Record<number, { agents: number; crews: number }>>({});
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterActive, setFilterActive] = useState<string>('all');

  useEffect(() => {
    // fetch usage counts for current providers
    const fetchUsage = async () => {
      const entries = await Promise.all(
        providers.map(async (p) => {
          try {
            const res = await apiClient.get(`/api/v1/llm-providers/${p.id}/usage`);
            if (res.error) return [p.id, { agents: 0, crews: 0 }] as const;
            return [p.id, { agents: res.data.agent_count || 0, crews: res.data.crew_count || 0 }] as const;
          } catch {
            return [p.id, { agents: 0, crews: 0 }] as const;
          }
        })
      );
      const map: Record<number, { agents: number; crews: number }> = {};
      for (const [id, val] of entries) map[id] = val;
      setUsage(map);
    };
    if (providers.length) void fetchUsage();
  }, [providers]);

  const handleTest = async (id: number) => {
    setTestingId(id);
    try {
      const res = await testConnection(id);
      setTestResult(prev => ({
        ...prev,
        [id]: { ok: !!res.success, message: res.message || (res.success ? 'OK' : 'Failed'), at: new Date().toLocaleTimeString() },
      }));
    } catch (e: any) {
      setTestResult(prev => ({ ...prev, [id]: { ok: false, message: e?.message || 'Failed', at: new Date().toLocaleTimeString() } }));
    }
    setTestingId(null);
  };

  const handleSetDefault = async (id: number) => {
    try {
      await setDefault(id);
      await refetch();
    } catch (e: any) {
      alert('Failed to set default: ' + (e?.message || 'Unknown error'));
    }
  };

  const handleDelete = async (id: number) => {
    const providerUsage = usage[id] || { agents: 0, crews: 0 };
    if (providerUsage.agents > 0 || providerUsage.crews > 0) {
      alert(`Cannot delete: This provider is used by ${providerUsage.agents} agent(s) and ${providerUsage.crews} crew(s). Please reassign or remove dependencies first.`);
      return;
    }

    if (!confirm('Delete this provider? This action cannot be undone.')) return;

    try {
      await deleteProvider(id);
      await refetch();
    } catch (e: any) {
      alert('Failed to delete: ' + (e?.message || 'Unknown error'));
    }
  };

  // Filter providers
  const filteredProviders = providers.filter(provider => {
    if (search && !provider.name.toLowerCase().includes(search.toLowerCase()) &&
        !provider.model_name.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (filterType !== 'all' && provider.provider_type !== filterType) return false;
    if (filterActive === 'active' && !provider.is_active) return false;
    if (filterActive === 'inactive' && provider.is_active) return false;
    return true;
  });

  const hasActiveFilters = search || filterType !== 'all' || filterActive !== 'all';

  // Extract unique provider types
  const providerTypes = Array.from(new Set(providers.map(p => p.provider_type)));

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <Breadcrumbs />

            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">LLM Providers</h1>
                <p className="text-sm text-gray-600 mt-1">
                  Manage and validate LLM provider credentials
                </p>
              </div>
              <button
                onClick={() => router.push('/providers/new')}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                + New Provider
              </button>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Search */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Search
                  </label>
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search providers..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Type Filter */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Provider Type
                  </label>
                  <select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All Types</option>
                    {providerTypes.map(type => (
                      <option key={type} value={type} className="capitalize">
                        {type}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Status Filter */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Status
                  </label>
                  <select
                    value={filterActive}
                    onChange={(e) => setFilterActive(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All Status</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              {/* Clear Filters */}
              {hasActiveFilters && (
                <div className="mt-4">
                  <button
                    onClick={() => {
                      setSearch('');
                      setFilterType('all');
                      setFilterActive('all');
                    }}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    Clear all filters
                  </button>
                </div>
              )}
            </div>

            {/* Content */}
            {error ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="text-center max-w-md">
                  <p className="text-red-600 mb-4">Failed to load providers: {error}</p>
                  <button
                    onClick={refetch}
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
            ) : filteredProviders.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <p className="text-gray-500 mb-4">
                  {hasActiveFilters
                    ? 'No providers match your filters.'
                    : 'No providers yet. Create your first provider to get started.'}
                </p>
                {!hasActiveFilters && (
                  <button
                    onClick={() => router.push('/providers/new')}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    New Provider
                  </button>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredProviders.map((provider) => (
                  <ProviderCard
                    key={provider.id}
                    provider={provider}
                    usage={usage[provider.id] || { agents: 0, crews: 0 }}
                    testResult={testResult[provider.id]}
                    testing={testingId === provider.id}
                    onTest={() => handleTest(provider.id)}
                    onSetDefault={() => handleSetDefault(provider.id)}
                    onEdit={() => router.push(`/providers/${provider.id}`)}
                    onDelete={() => handleDelete(provider.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

// Provider Card Component
function ProviderCard({
  provider,
  usage,
  testResult,
  testing,
  onTest,
  onSetDefault,
  onEdit,
  onDelete
}: {
  provider: ProviderItem;
  usage: { agents: number; crews: number };
  testResult?: { ok: boolean; message: string; at: string };
  testing: boolean;
  onTest: () => void;
  onSetDefault: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-900 flex-1">
          {provider.name}
        </h3>
        {provider.is_default && (
          <span className="text-yellow-500" title="Default provider">
            ⭐
          </span>
        )}
      </div>

      {/* Provider Type & Model */}
      <div className="space-y-1 mt-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-500">Type:</span>
          <span className="px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-800 capitalize">
            {provider.provider_type}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-500">Model:</span>
          <span className="text-sm text-gray-700">{provider.model_name || '—'}</span>
        </div>
      </div>

      {/* Status & Test Result */}
      <div className="mt-4 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-500">Status:</span>
          {provider.is_active ? (
            <span className="inline-flex items-center gap-1 text-xs text-green-700">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              Active
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs text-gray-500">
              <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
              Inactive
            </span>
          )}
        </div>

        {testResult && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500">Test:</span>
            <span className={`text-xs ${testResult.ok ? 'text-green-700' : 'text-red-700'}`}>
              {testResult.ok ? '✓ OK' : '✗ Failed'} · {testResult.at}
            </span>
          </div>
        )}
      </div>

      {/* Usage Stats */}
      <div className="mt-4 flex items-center gap-4 text-xs text-gray-600">
        <span title="Agents using this provider">
          👤 {usage.agents} agent{usage.agents !== 1 ? 's' : ''}
        </span>
        <span title="Crews using this provider">
          👥 {usage.crews} crew{usage.crews !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Actions */}
      <div className="mt-4 flex flex-col gap-2">
        <div className="flex gap-2">
          <button
            onClick={onTest}
            disabled={testing}
            className="flex-1 px-3 py-2 text-sm font-medium text-purple-600 bg-purple-50 rounded-md hover:bg-purple-100 disabled:opacity-50"
          >
            {testing ? 'Testing...' : '🧪 Test'}
          </button>
          <button
            onClick={onEdit}
            className="flex-1 px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
          >
            Edit
          </button>
        </div>
        <div className="flex gap-2">
          {!provider.is_default && (
            <button
              onClick={onSetDefault}
              className="flex-1 px-3 py-2 text-sm font-medium text-amber-600 bg-amber-50 rounded-md hover:bg-amber-100"
            >
              ⭐ Set Default
            </button>
          )}
          <button
            onClick={onDelete}
            disabled={usage.agents > 0 || usage.crews > 0}
            className="flex-1 px-3 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed"
            title={usage.agents > 0 || usage.crews > 0 ? 'Provider has dependencies' : 'Delete provider'}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
