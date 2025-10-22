'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { useAuthStore } from '@/lib/store';
import { useTenants, TenantDetail } from '@/lib/hooks/useTenants';

export default function TenantDetailPage() {
  const router = useRouter();
  const params = useParams();
  const tenantId = params.id as string;
  const { user } = useAuthStore();
  const { getTenant, updateTenant, approveTenant, suspendTenant, activateTenant, deleteTenant } = useTenants();

  const [tenant, setTenant] = useState<TenantDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<TenantDetail>>({});

  // Check if user is super admin
  const isSuperAdmin = user?.is_super_admin;

  useEffect(() => {
    if (isSuperAdmin && tenantId) {
      loadTenant();
    }
  }, [isSuperAdmin, tenantId]);

  const loadTenant = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getTenant(tenantId);
      setTenant(data);
      setFormData({
        name: data.name,
        max_users: data.max_users,
        max_agents: data.max_agents,
        max_flows: data.max_flows,
        settings: data.settings,
      });
    } catch (err) {
      console.error('[TenantDetail] Load failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to load tenant');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!tenant) return;

    try {
      setLoading(true);
      setError(null);
      const updated = await updateTenant(tenantId, formData);
      setTenant(updated);
      setEditing(false);
      alert('Tenant updated successfully');
    } catch (err) {
      console.error('[TenantDetail] Update failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to update tenant');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusAction = async (action: 'approve' | 'suspend' | 'activate' | 'delete') => {
    const confirmMessages = {
      approve: 'Approve this tenant?',
      suspend: 'Suspend this tenant? Users will not be able to access the system.',
      activate: 'Activate this tenant?',
      delete: 'Delete this tenant? This action cannot be undone.',
    };

    if (!confirm(confirmMessages[action])) return;

    try {
      setLoading(true);
      setError(null);

      switch (action) {
        case 'approve':
          await approveTenant(tenantId);
          break;
        case 'suspend':
          await suspendTenant(tenantId);
          break;
        case 'activate':
          await activateTenant(tenantId);
          break;
        case 'delete':
          await deleteTenant(tenantId);
          router.push('/tenants');
          return;
      }

      await loadTenant();
      alert(`Tenant ${action}d successfully`);
    } catch (err) {
      console.error(`[TenantDetail] ${action} failed:`, err);
      setError(err instanceof Error ? err.message : `Failed to ${action} tenant`);
    } finally {
      setLoading(false);
    }
  };

  if (!isSuperAdmin) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-7xl mx-auto p-6">
              <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                <div className="text-5xl mb-4">🚫</div>
                <h2 className="text-xl font-bold text-red-800 mb-2">Access Denied</h2>
                <p className="text-red-600">You need super admin privileges to view this page.</p>
              </div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  if (loading && !tenant) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-7xl mx-auto p-6">
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  if (error && !tenant) {
    return (
      <ProtectedRoute>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <div className="flex-1 overflow-auto">
            <div className="max-w-7xl mx-auto p-6">
              <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <p className="text-red-800">{error}</p>
                <button
                  onClick={() => router.push('/tenants')}
                  className="mt-4 text-blue-600 hover:text-blue-800"
                >
                  ← Back to Tenants
                </button>
              </div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  if (!tenant) return null;

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <Breadcrumbs />

            {/* Header */}
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  {tenant.name}
                </h1>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                  Tenant ID: {tenant.id}
                </p>
              </div>
              <div className="flex gap-2">
                {!editing && (
                  <button
                    onClick={() => setEditing(true)}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Edit
                  </button>
                )}
                {editing && (
                  <>
                    <button
                      onClick={() => {
                        setEditing(false);
                        setFormData({
                          name: tenant.name,
                          max_users: tenant.max_users,
                          max_agents: tenant.max_agents,
                          max_flows: tenant.max_flows,
                          settings: tenant.settings,
                        });
                      }}
                      className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={loading}
                      className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                      Save
                    </button>
                  </>
                )}
              </div>
            </div>

            {error && (
              <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
                {error}
              </div>
            )}

            <div className="space-y-6">
              {/* Basic Information */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Basic Information
                </h2>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Tenant Name
                    </label>
                    {editing ? (
                      <input
                        type="text"
                        value={formData.name || ''}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      />
                    ) : (
                      <p className="text-gray-900 dark:text-white">{tenant.name}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Schema Name
                    </label>
                    <code className="text-sm bg-gray-100 dark:bg-gray-700 px-3 py-2 rounded text-gray-800 dark:text-gray-200">
                      {tenant.schema_name}
                    </code>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Status
                    </label>
                    <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      tenant.status === 'active'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : tenant.status === 'pending'
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                        : tenant.status === 'suspended'
                        ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                        : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                    }`}>
                      {tenant.status}
                    </span>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      User Count
                    </label>
                    <p className="text-gray-900 dark:text-white">{tenant.user_count}</p>
                  </div>
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      API Key
                    </label>
                    <code className="text-xs bg-gray-100 dark:bg-gray-700 px-3 py-2 rounded text-gray-800 dark:text-gray-200 break-all">
                      {tenant.api_key}
                    </code>
                  </div>
                </div>
              </div>

              {/* Quotas */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Resource Quotas
                </h2>
                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Max Users
                    </label>
                    {editing ? (
                      <input
                        type="number"
                        min="0"
                        value={formData.max_users || 0}
                        onChange={(e) => setFormData({ ...formData, max_users: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      />
                    ) : (
                      <p className="text-gray-900 dark:text-white">{tenant.max_users}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Max Agents
                    </label>
                    {editing ? (
                      <input
                        type="number"
                        min="0"
                        value={formData.max_agents || 0}
                        onChange={(e) => setFormData({ ...formData, max_agents: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      />
                    ) : (
                      <p className="text-gray-900 dark:text-white">{tenant.max_agents}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Max Flows
                    </label>
                    {editing ? (
                      <input
                        type="number"
                        min="0"
                        value={formData.max_flows || 0}
                        onChange={(e) => setFormData({ ...formData, max_flows: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      />
                    ) : (
                      <p className="text-gray-900 dark:text-white">{tenant.max_flows}</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Settings */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Settings (JSON)
                </h2>
                {editing ? (
                  <textarea
                    value={JSON.stringify(formData.settings || {}, null, 2)}
                    onChange={(e) => {
                      try {
                        const parsed = JSON.parse(e.target.value);
                        setFormData({ ...formData, settings: parsed });
                      } catch (err) {
                        // Invalid JSON, don't update
                      }
                    }}
                    rows={10}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  />
                ) : (
                  <pre className="bg-gray-100 dark:bg-gray-700 px-4 py-3 rounded text-sm text-gray-800 dark:text-gray-200 overflow-auto">
                    {JSON.stringify(tenant.settings, null, 2)}
                  </pre>
                )}
              </div>

              {/* Status Actions */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Status Actions
                </h2>
                <div className="flex gap-3">
                  {tenant.status === 'pending' && (
                    <button
                      onClick={() => handleStatusAction('approve')}
                      disabled={loading}
                      className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50"
                    >
                      Approve Tenant
                    </button>
                  )}
                  {tenant.status === 'active' && (
                    <button
                      onClick={() => handleStatusAction('suspend')}
                      disabled={loading}
                      className="px-4 py-2 text-sm font-medium text-white bg-orange-600 rounded-md hover:bg-orange-700 disabled:opacity-50"
                    >
                      Suspend Tenant
                    </button>
                  )}
                  {tenant.status === 'suspended' && (
                    <button
                      onClick={() => handleStatusAction('activate')}
                      disabled={loading}
                      className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50"
                    >
                      Activate Tenant
                    </button>
                  )}
                  <button
                    onClick={() => handleStatusAction('delete')}
                    disabled={loading}
                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
                  >
                    Delete Tenant
                  </button>
                </div>
              </div>

              {/* Metadata */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Metadata
                </h2>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Created At
                    </label>
                    <p className="text-gray-900 dark:text-white">
                      {new Date(tenant.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Updated At
                    </label>
                    <p className="text-gray-900 dark:text-white">
                      {new Date(tenant.updated_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
