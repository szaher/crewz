'use client';

import { useEffect, useState } from 'react';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { useAuthStore, useTenantStore } from '@/lib/store';
import { getApiBaseUrl } from '@/lib/api-url';

export default function TenantSettingsPage() {
  const { token } = useAuthStore();
  const { currentTenant } = useTenantStore();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [tenantName, setTenantName] = useState('');

  useEffect(() => {
    if (currentTenant) {
      setTenantName(currentTenant.name || '');
    }
  }, [currentTenant]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!currentTenant) return;

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      const response = await fetch(`${getApiBaseUrl()}/api/v1/tenants/${currentTenant.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: tenantName
        })
      });

      if (!response.ok) {
        throw new Error('Failed to update tenant settings');
      }

      setSuccess('Tenant settings updated successfully');
    } catch (err) {
      console.error('[TenantSettings] Save failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (!currentTenant) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-7xl mx-auto p-6">
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
                <div className="text-5xl mb-4">⚠️</div>
                <h2 className="text-xl font-bold text-yellow-800 mb-2">No Tenant Found</h2>
                <p className="text-yellow-600">You are not associated with a tenant.</p>
              </div>
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

            <div className="mb-6">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tenant Settings</h1>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Manage your organization's settings
              </p>
            </div>

            {error && (
              <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
                {error}
              </div>
            )}

            {success && (
              <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4 text-green-800">
                {success}
              </div>
            )}

            <form onSubmit={handleSave} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-6">
              {/* Tenant Information */}
              <div>
                <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Tenant Information</h2>

                <div className="space-y-4">
                  <div>
                    <label htmlFor="tenantId" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Tenant ID
                    </label>
                    <input
                      type="text"
                      id="tenantId"
                      value={currentTenant.id}
                      disabled
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-md text-gray-500 dark:text-gray-400 cursor-not-allowed"
                    />
                  </div>

                  <div>
                    <label htmlFor="tenantName" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Organization Name *
                    </label>
                    <input
                      type="text"
                      id="tenantName"
                      value={tenantName}
                      onChange={(e) => setTenantName(e.target.value)}
                      required
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                      placeholder="Enter organization name"
                    />
                  </div>

                  <div>
                    <label htmlFor="schemaName" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Database Schema
                    </label>
                    <input
                      type="text"
                      id="schemaName"
                      value={currentTenant.schema_name || 'N/A'}
                      disabled
                      className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-md text-gray-500 dark:text-gray-400 cursor-not-allowed"
                    />
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Database schema cannot be changed
                    </p>
                  </div>
                </div>
              </div>

              {/* Tenant Statistics */}
              <div>
                <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Statistics</h2>

                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-gray-900 dark:text-white">-</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">Total Users</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-gray-900 dark:text-white">-</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">Executions</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-gray-900 dark:text-white">-</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">Artifacts</div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end space-x-3 pt-6 border-t border-gray-200 dark:border-gray-700">
                <button
                  type="button"
                  onClick={() => {
                    setTenantName(currentTenant.name || '');
                    setError(null);
                    setSuccess(null);
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600"
                >
                  Reset
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
