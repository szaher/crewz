'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { useAuthStore } from '@/lib/store';

interface Tenant {
  id: string;
  name: string;
  schema_name: string;
  status: string;
  user_count: number;
  created_at: string;
  max_users?: number;
  max_agents?: number;
  max_flows?: number;
}

interface PendingRegistration {
  id: string;
  company_name: string;
  admin_email: string;
  admin_name: string;
  reason: string;
  sample_data_requested: boolean;
  status: string;
  created_at: string;
  company_size?: string;
  use_case?: string;
}

type TabType = 'all' | 'pending';

export default function TenantsPage() {
  const router = useRouter();
  const { token, user } = useAuthStore();
  const [activeTab, setActiveTab] = useState<TabType>('all');
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [pendingRegistrations, setPendingRegistrations] = useState<PendingRegistration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check if user is super admin
  const isSuperAdmin = user?.is_super_admin;

  const fetchTenants = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('http://localhost:8000/api/v1/admin/tenants', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch tenants');
      }

      const data = await response.json();
      setTenants(data);
    } catch (err) {
      console.error('[Tenants] Fetch failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to load tenants');
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingRegistrations = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('http://localhost:8000/api/v1/admin/tenants/pending', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch pending registrations');
      }

      const data = await response.json();
      setPendingRegistrations(data.registrations || []);
    } catch (err) {
      console.error('[Tenants] Fetch pending failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to load pending registrations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token && isSuperAdmin) {
      if (activeTab === 'all') {
        fetchTenants();
      } else {
        fetchPendingRegistrations();
      }
    } else if (!isSuperAdmin) {
      setLoading(false);
      setError('Access denied. Super admin role required.');
    }
  }, [token, isSuperAdmin, activeTab]);

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

  const handleApprove = async (registrationId: string) => {
    if (!confirm('Approve this tenant registration?')) return;

    try {
      const response = await fetch(`http://localhost:8000/api/v1/admin/tenants/${registrationId}/approve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ notes: '' })
      });

      if (!response.ok) {
        throw new Error('Failed to approve registration');
      }

      const result = await response.json();
      alert(`Tenant approved!\n\nTemporary Password: ${result.admin_user.temporary_password}\n\nPlease save this password and send it to the admin.`);

      // Refresh the list
      fetchPendingRegistrations();
    } catch (err) {
      console.error('[Tenants] Approve failed:', err);
      alert('Failed to approve registration');
    }
  };

  const handleReject = async (registrationId: string) => {
    const reason = prompt('Enter rejection reason (min 10 characters):');
    if (!reason || reason.length < 10) {
      alert('Rejection reason must be at least 10 characters');
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/api/v1/admin/tenants/${registrationId}/reject`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reason })
      });

      if (!response.ok) {
        throw new Error('Failed to reject registration');
      }

      alert('Registration rejected');

      // Refresh the list
      fetchPendingRegistrations();
    } catch (err) {
      console.error('[Tenants] Reject failed:', err);
      alert('Failed to reject registration');
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <Breadcrumbs />

            <div className="mb-6">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tenant Management</h1>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Manage all tenants and pending registrations
              </p>
            </div>

            {/* Tabs */}
            <div className="mb-6 border-b border-gray-200 dark:border-gray-700">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setActiveTab('all')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'all'
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
                >
                  All Tenants ({tenants.length})
                </button>
                <button
                  onClick={() => setActiveTab('pending')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'pending'
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
                >
                  Pending Registrations ({pendingRegistrations.length})
                </button>
              </nav>
            </div>

            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
                {error}
              </div>
            )}

            {/* All Tenants Tab */}
            {activeTab === 'all' && !loading && !error && (
              <>
                {tenants.length === 0 ? (
                  <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="text-5xl mb-4">🏢</div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No tenants found</h3>
                    <p className="text-gray-600 dark:text-gray-400">
                      Approve pending registrations to create tenants
                    </p>
                  </div>
                ) : (
                  <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                      <thead className="bg-gray-50 dark:bg-gray-900">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Tenant
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Schema
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Users
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Created
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                        {tenants.map((tenant) => (
                          <tr key={tenant.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center">
                                <div>
                                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                                    {tenant.name}
                                  </div>
                                  <div className="text-xs text-gray-500 dark:text-gray-400">
                                    ID: {tenant.id.substring(0, 8)}...
                                  </div>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <code className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-800 dark:text-gray-200">
                                {tenant.schema_name}
                              </code>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                              {tenant.user_count}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {tenant.status === 'active' ? (
                                <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                                  Active
                                </span>
                              ) : (
                                <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                                  {tenant.status}
                                </span>
                              )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                              {new Date(tenant.created_at).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              <button
                                onClick={() => router.push(`/tenants/${tenant.id}`)}
                                className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                              >
                                Manage
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}

            {/* Pending Registrations Tab */}
            {activeTab === 'pending' && !loading && !error && (
              <>
                {pendingRegistrations.length === 0 ? (
                  <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="text-5xl mb-4">✅</div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No pending registrations</h3>
                    <p className="text-gray-600 dark:text-gray-400">
                      All registrations have been processed
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {pendingRegistrations.map((registration) => (
                      <div key={registration.id} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                              {registration.company_name}
                            </h3>
                            <div className="mt-2 space-y-1">
                              <p className="text-sm text-gray-600 dark:text-gray-400">
                                <span className="font-medium">Admin:</span> {registration.admin_name} ({registration.admin_email})
                              </p>
                              {registration.company_size && (
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                  <span className="font-medium">Company Size:</span> {registration.company_size}
                                </p>
                              )}
                              {registration.use_case && (
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                  <span className="font-medium">Use Case:</span> {registration.use_case}
                                </p>
                              )}
                              <p className="text-sm text-gray-600 dark:text-gray-400">
                                <span className="font-medium">Reason:</span> {registration.reason}
                              </p>
                              <p className="text-sm text-gray-600 dark:text-gray-400">
                                <span className="font-medium">Sample Data Requested:</span> {registration.sample_data_requested ? 'Yes' : 'No'}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                                Submitted: {new Date(registration.created_at).toLocaleString()}
                              </p>
                            </div>
                          </div>
                          <div className="flex gap-2 ml-4">
                            <button
                              onClick={() => handleApprove(registration.id)}
                              className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => handleReject(registration.id)}
                              className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
                            >
                              Reject
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
