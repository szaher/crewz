'use client';

import { useState } from 'react';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import { usePolicies } from '@/lib/hooks/useAuthorization';
import type { Policy, PolicyCreateRequest, PolicyUpdateRequest } from '@/lib/api/authorization';

/**
 * Policy Management Page
 * Allows tenant admins to create and manage authorization policies
 */
export default function PoliciesPage() {
  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <div className="mb-8">
              <h1 className="text-3xl font-bold">Authorization Policies</h1>
              <p className="text-gray-600 mt-2">
                Manage tenant-level and user-level authorization policies
              </p>
            </div>
            <PoliciesContent />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

function PoliciesContent() {
  const [scope, setScope] = useState<'tenant' | 'user' | 'all'>('all');
  const [activeOnly, setActiveOnly] = useState(true);
  const [page, setPage] = useState(1);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);

  const {
    policies,
    total,
    loading,
    error,
    refetch,
    createPolicy,
    updatePolicy,
    deletePolicy,
  } = usePolicies({ scope: scope === 'all' ? undefined : scope, active_only: activeOnly, page, page_size: 20 });

  const handleCreatePolicy = async (data: PolicyCreateRequest) => {
    try {
      await createPolicy(data);
      setShowCreateModal(false);
      refetch();
    } catch (err) {
      console.error('Failed to create policy:', err);
      throw err;
    }
  };

  const handleUpdatePolicy = async (policyId: string, data: PolicyUpdateRequest) => {
    try {
      await updatePolicy(policyId, data);
      setEditingPolicy(null);
      refetch();
    } catch (err) {
      console.error('Failed to update policy:', err);
      throw err;
    }
  };

  const handleDeletePolicy = async (policyId: string) => {
    if (!confirm('Are you sure you want to delete this policy?')) return;

    try {
      await deletePolicy(policyId);
      refetch();
    } catch (err) {
      console.error('Failed to delete policy:', err);
      alert('Failed to delete policy');
    }
  };

  const totalPages = Math.ceil(total / 20);

  if (loading && policies.length === 0) {
    return <div className="text-center py-8">Loading policies...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex gap-4 items-center">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Scope
            </label>
            <select
              value={scope}
              onChange={(e) => {
                setScope(e.target.value as 'tenant' | 'user' | 'all');
                setPage(1);
              }}
              className="px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="all">All Policies</option>
              <option value="tenant">Tenant Policies</option>
              <option value="user">User Policies</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={activeOnly ? 'active' : 'all'}
              onChange={(e) => {
                setActiveOnly(e.target.value === 'active');
                setPage(1);
              }}
              className="px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="active">Active Only</option>
              <option value="all">All Statuses</option>
            </select>
          </div>

          <div className="ml-auto">
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Create Policy
            </button>
          </div>
        </div>
      </div>

      {/* Policies Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Policy
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Scope
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Pattern
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Effect
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Priority
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {policies.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                  No policies found. Create your first policy to get started.
                </td>
              </tr>
            ) : (
              policies.map((policy) => (
                <tr
                  key={policy.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => setSelectedPolicy(policy)}
                >
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">
                      {policy.name}
                    </div>
                    {policy.description && (
                      <div className="text-sm text-gray-500 mt-1">
                        {policy.description}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded ${
                        policy.scope === 'tenant'
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {policy.scope}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">
                      {policy.resource_pattern}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Action: {policy.action_pattern}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded ${
                        policy.effect === 'allow'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {policy.effect}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {policy.priority}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded ${
                        policy.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {policy.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingPolicy(policy);
                      }}
                      className="text-blue-600 hover:text-blue-900 mr-3"
                    >
                      Edit
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeletePolicy(policy.id);
                      }}
                      className="text-red-600 hover:text-red-900"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-3 py-1">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Modals */}
      {showCreateModal && (
        <CreatePolicyModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreatePolicy}
        />
      )}

      {editingPolicy && (
        <EditPolicyModal
          policy={editingPolicy}
          onClose={() => setEditingPolicy(null)}
          onSubmit={(data) => handleUpdatePolicy(editingPolicy.id, data)}
        />
      )}

      {selectedPolicy && (
        <PolicyDetailSidebar
          policy={selectedPolicy}
          onClose={() => setSelectedPolicy(null)}
        />
      )}
    </div>
  );
}

function CreatePolicyModal({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (data: PolicyCreateRequest) => Promise<void>;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<PolicyCreateRequest>({
    scope: 'tenant',
    name: '',
    description: '',
    resource_pattern: '',
    action_pattern: '*',
    effect: 'allow',
    priority: 100,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await onSubmit(formData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create policy');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b">
          <h2 className="text-xl font-semibold">Create Policy</h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Scope *
            </label>
            <select
              value={formData.scope}
              onChange={(e) =>
                setFormData({ ...formData, scope: e.target.value as 'tenant' | 'user' })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            >
              <option value="tenant">Tenant (applies to all users)</option>
              <option value="user">User (applies to specific user)</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Tenant policies apply to all users. User policies apply to specific users.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Policy Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="Allow all crew read access"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              rows={2}
              placeholder="Optional description"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Resource Pattern *
            </label>
            <input
              type="text"
              value={formData.resource_pattern}
              onChange={(e) =>
                setFormData({ ...formData, resource_pattern: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="crew:* or flow:018e1234* or *:*"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Examples: crew:* (all crews), flow:018e1234* (specific flow), *:* (all resources)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Action Pattern *
            </label>
            <select
              value={formData.action_pattern}
              onChange={(e) =>
                setFormData({ ...formData, action_pattern: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            >
              <option value="*">* (all actions)</option>
              <option value="read">read</option>
              <option value="write">write</option>
              <option value="execute">execute</option>
              <option value="delete">delete</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Effect *
            </label>
            <select
              value={formData.effect}
              onChange={(e) =>
                setFormData({ ...formData, effect: e.target.value as 'allow' | 'deny' })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            >
              <option value="allow">Allow</option>
              <option value="deny">Deny</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <input
              type="number"
              value={formData.priority}
              onChange={(e) =>
                setFormData({ ...formData, priority: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              min={0}
              max={1000}
            />
            <p className="text-xs text-gray-500 mt-1">
              Higher priority policies are evaluated first (0-1000)
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              disabled={loading}
            >
              {loading ? 'Creating...' : 'Create Policy'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditPolicyModal({
  policy,
  onClose,
  onSubmit,
}: {
  policy: Policy;
  onClose: () => void;
  onSubmit: (data: PolicyUpdateRequest) => Promise<void>;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<PolicyUpdateRequest>({
    name: policy.name,
    description: policy.description || '',
    resource_pattern: policy.resource_pattern,
    action_pattern: policy.action_pattern,
    effect: policy.effect,
    priority: policy.priority,
    is_active: policy.is_active,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await onSubmit(formData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update policy');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b">
          <h2 className="text-xl font-semibold">Edit Policy</h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Policy Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              rows={2}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Resource Pattern *
            </label>
            <input
              type="text"
              value={formData.resource_pattern}
              onChange={(e) =>
                setFormData({ ...formData, resource_pattern: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Action Pattern *
            </label>
            <select
              value={formData.action_pattern}
              onChange={(e) =>
                setFormData({ ...formData, action_pattern: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            >
              <option value="*">* (all actions)</option>
              <option value="read">read</option>
              <option value="write">write</option>
              <option value="execute">execute</option>
              <option value="delete">delete</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Effect *
            </label>
            <select
              value={formData.effect}
              onChange={(e) =>
                setFormData({ ...formData, effect: e.target.value as 'allow' | 'deny' })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            >
              <option value="allow">Allow</option>
              <option value="deny">Deny</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <input
              type="number"
              value={formData.priority}
              onChange={(e) =>
                setFormData({ ...formData, priority: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              min={0}
              max={1000}
            />
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="mr-2"
            />
            <label htmlFor="is_active" className="text-sm font-medium text-gray-700">
              Active (uncheck to disable this policy)
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              disabled={loading}
            >
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function PolicyDetailSidebar({
  policy,
  onClose,
}: {
  policy: Policy;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-end z-50" onClick={onClose}>
      <div
        className="bg-white w-full max-w-md h-full overflow-y-auto shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 border-b flex justify-between items-center">
          <h2 className="text-xl font-semibold">Policy Details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Basic Info */}
          <div>
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">
              Basic Information
            </h3>
            <div className="space-y-3">
              <div>
                <div className="text-xs text-gray-500">Name</div>
                <div className="text-sm font-medium">{policy.name}</div>
              </div>
              {policy.description && (
                <div>
                  <div className="text-xs text-gray-500">Description</div>
                  <div className="text-sm">{policy.description}</div>
                </div>
              )}
              <div>
                <div className="text-xs text-gray-500">Scope</div>
                <span
                  className={`inline-block px-2 py-1 text-xs font-medium rounded ${
                    policy.scope === 'tenant'
                      ? 'bg-purple-100 text-purple-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}
                >
                  {policy.scope}
                </span>
              </div>
              <div>
                <div className="text-xs text-gray-500">Status</div>
                <span
                  className={`inline-block px-2 py-1 text-xs font-medium rounded ${
                    policy.is_active
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {policy.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>

          {/* Policy Rules */}
          <div>
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">
              Policy Rules
            </h3>
            <div className="space-y-3">
              <div>
                <div className="text-xs text-gray-500">Resource Pattern</div>
                <div className="text-sm font-mono bg-gray-50 px-2 py-1 rounded">
                  {policy.resource_pattern}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Action Pattern</div>
                <div className="text-sm font-mono bg-gray-50 px-2 py-1 rounded">
                  {policy.action_pattern}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Effect</div>
                <span
                  className={`inline-block px-2 py-1 text-xs font-medium rounded ${
                    policy.effect === 'allow'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {policy.effect}
                </span>
              </div>
              <div>
                <div className="text-xs text-gray-500">Priority</div>
                <div className="text-sm">{policy.priority}</div>
              </div>
            </div>
          </div>

          {/* Conditions */}
          {policy.conditions && Object.keys(policy.conditions).length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">
                Conditions
              </h3>
              <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                {JSON.stringify(policy.conditions, null, 2)}
              </pre>
            </div>
          )}

          {/* Metadata */}
          <div>
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">
              Metadata
            </h3>
            <div className="space-y-2 text-xs text-gray-600">
              <div>
                <span className="font-medium">Policy ID:</span> {policy.id}
              </div>
              <div>
                <span className="font-medium">Tenant ID:</span> {policy.tenant_id}
              </div>
              {policy.scope_id && (
                <div>
                  <span className="font-medium">Scope ID:</span> {policy.scope_id}
                </div>
              )}
              <div>
                <span className="font-medium">Created:</span>{' '}
                {new Date(policy.created_at).toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
