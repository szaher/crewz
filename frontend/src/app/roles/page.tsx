'use client';

import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import { useRoles, useRoleDetail } from '@/lib/hooks/useAuthorization';
import { useState } from 'react';
import type { RoleCreateRequest, RoleUpdateRequest, PermissionCreateRequest, Action } from '@/lib/api/authorization';

export default function RolesPage() {
  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <RolesContent />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

function RolesContent() {
  const [includeSystem, setIncludeSystem] = useState(true);
  const [page, setPage] = useState(1);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  const { roles, total, loading, error, refetch, createRole, updateRole, deleteRole } = useRoles({
    include_system: includeSystem,
    page,
    page_size: 20,
  });

  const handleCreateRole = async (data: RoleCreateRequest) => {
    try {
      await createRole(data);
      setShowCreateModal(false);
      alert('Role created successfully');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create role');
    }
  };

  const handleUpdateRole = async (roleId: string, data: RoleUpdateRequest) => {
    try {
      await updateRole(roleId, data);
      setShowEditModal(false);
      setSelectedRoleId(null);
      alert('Role updated successfully');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update role');
    }
  };

  const handleDeleteRole = async (roleId: string) => {
    if (!confirm('Are you sure you want to delete this role? Users with this role will lose associated permissions.')) {
      return;
    }

    try {
      await deleteRole(roleId);
      alert('Role deleted successfully');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete role');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Role Management</h1>
        <p className="mt-2 text-gray-600">Manage roles and permissions for your organization</p>
      </div>

      {/* Controls */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={includeSystem}
              onChange={(e) => setIncludeSystem(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">Include system roles</span>
          </label>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Create Role
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          <p className="mt-2 text-gray-600">Loading roles...</p>
        </div>
      )}

      {/* Roles Table */}
      {!loading && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Slug
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Priority
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Default
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {roles.map((role) => (
                <tr key={role.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{role.name}</div>
                    {role.description && (
                      <div className="text-sm text-gray-500">{role.description}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <code className="px-2 py-1 bg-gray-100 rounded">{role.slug}</code>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {role.is_system_role ? (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">
                        System
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        Custom
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {role.priority}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {role.is_default ? (
                      <span className="text-green-600">✓</span>
                    ) : (
                      <span className="text-gray-300">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <button
                      onClick={() => {
                        setSelectedRoleId(role.id);
                      }}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      View
                    </button>
                    {!role.is_system_role && (
                      <>
                        <button
                          onClick={() => {
                            setSelectedRoleId(role.id);
                            setShowEditModal(true);
                          }}
                          className="text-yellow-600 hover:text-yellow-900"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteRole(role.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {roles.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No roles found
            </div>
          )}
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Showing <span className="font-medium">{(page - 1) * 20 + 1}</span> to{' '}
            <span className="font-medium">{Math.min(page * 20, total)}</span> of{' '}
            <span className="font-medium">{total}</span> roles
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
              className="px-3 py-1 border rounded disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page * 20 >= total}
              className="px-3 py-1 border rounded disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Create Role Modal */}
      {showCreateModal && (
        <CreateRoleModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateRole}
        />
      )}

      {/* Edit Role Modal */}
      {showEditModal && selectedRoleId && (
        <EditRoleModal
          roleId={selectedRoleId}
          onClose={() => {
            setShowEditModal(false);
            setSelectedRoleId(null);
          }}
          onSubmit={handleUpdateRole}
        />
      )}

      {/* Role Detail Sidebar */}
      {selectedRoleId && !showEditModal && (
        <RoleDetailSidebar
          roleId={selectedRoleId}
          onClose={() => setSelectedRoleId(null)}
        />
      )}
    </div>
  );
}

// Create Role Modal Component
function CreateRoleModal({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (data: RoleCreateRequest) => Promise<void>;
}) {
  const [formData, setFormData] = useState<RoleCreateRequest>({
    name: '',
    slug: '',
    description: '',
    is_default: false,
    priority: 500,
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit(formData);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-bold mb-4">Create Role</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="e.g., Project Manager"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Slug *
            </label>
            <input
              type="text"
              required
              value={formData.slug}
              onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
              placeholder="e.g., project-manager"
              pattern="^[a-z0-9-]+$"
              title="Only lowercase letters, numbers, and hyphens"
            />
            <p className="mt-1 text-xs text-gray-500">Only lowercase letters, numbers, and hyphens</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              rows={3}
              placeholder="Role description..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <input
              type="number"
              min={0}
              max={1000}
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <p className="mt-1 text-xs text-gray-500">Higher priority = evaluated first (0-1000)</p>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_default}
                onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm font-medium text-gray-700">Set as default role for new users</span>
            </label>
          </div>

          <div className="flex gap-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? 'Creating...' : 'Create Role'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Edit Role Modal Component
function EditRoleModal({
  roleId,
  onClose,
  onSubmit,
}: {
  roleId: string;
  onClose: () => void;
  onSubmit: (roleId: string, data: RoleUpdateRequest) => Promise<void>;
}) {
  const { role, loading } = useRoleDetail(roleId);
  const [formData, setFormData] = useState<RoleUpdateRequest>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit(roleId, formData);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !role) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6">Loading...</div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-bold mb-4">Edit Role: {role.name}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <input
              type="text"
              defaultValue={role.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              defaultValue={role.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              rows={3}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <input
              type="number"
              min={0}
              max={1000}
              defaultValue={role.priority}
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                defaultChecked={role.is_default}
                onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm font-medium text-gray-700">Default role</span>
            </label>
          </div>

          <div className="flex gap-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Role Detail Sidebar Component
function RoleDetailSidebar({ roleId, onClose }: { roleId: string; onClose: () => void }) {
  const { role, loading, addPermission } = useRoleDetail(roleId);
  const [showAddPermission, setShowAddPermission] = useState(false);
  const [newPermission, setNewPermission] = useState<PermissionCreateRequest>({
    resource_type: 'crew',
    resource_id: null,
    action: 'read' as Action,
    effect: 'allow',
  });

  const handleAddPermission = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await addPermission(newPermission);
      setShowAddPermission(false);
      setNewPermission({
        resource_type: 'crew',
        resource_id: null,
        action: 'read' as Action,
        effect: 'allow',
      });
      alert('Permission added successfully');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to add permission');
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-xl z-40 overflow-y-auto">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold">Role Details</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {loading && <div>Loading...</div>}

        {role && (
          <div className="space-y-6">
            <div>
              <h3 className="font-semibold text-lg mb-2">{role.name}</h3>
              <p className="text-sm text-gray-600">{role.description}</p>
              <div className="mt-2 flex gap-2">
                <span className="px-2 py-1 text-xs rounded bg-gray-100">
                  Priority: {role.priority}
                </span>
                {role.is_default && (
                  <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800">
                    Default
                  </span>
                )}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold">
                  Permissions ({role.permissions.length})
                </h4>
                <button
                  onClick={() => setShowAddPermission(!showAddPermission)}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  + Add
                </button>
              </div>

              {showAddPermission && (
                <form onSubmit={handleAddPermission} className="mb-4 p-3 bg-gray-50 rounded space-y-2">
                  <select
                    value={newPermission.resource_type}
                    onChange={(e) => setNewPermission({ ...newPermission, resource_type: e.target.value })}
                    className="w-full px-2 py-1 border rounded text-sm"
                  >
                    <option value="crew">Crew</option>
                    <option value="flow">Flow</option>
                    <option value="agent">Agent</option>
                    <option value="task">Task</option>
                    <option value="tool">Tool</option>
                    <option value="execution">Execution</option>
                  </select>
                  <select
                    value={newPermission.action}
                    onChange={(e) => setNewPermission({ ...newPermission, action: e.target.value as Action })}
                    className="w-full px-2 py-1 border rounded text-sm"
                  >
                    <option value="read">Read</option>
                    <option value="write">Write</option>
                    <option value="execute">Execute</option>
                    <option value="delete">Delete</option>
                    <option value="*">All (*)</option>
                  </select>
                  <select
                    value={newPermission.effect}
                    onChange={(e) => setNewPermission({ ...newPermission, effect: e.target.value as 'allow' | 'deny' })}
                    className="w-full px-2 py-1 border rounded text-sm"
                  >
                    <option value="allow">Allow</option>
                    <option value="deny">Deny</option>
                  </select>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setShowAddPermission(false)}
                      className="flex-1 px-2 py-1 text-sm border rounded"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="flex-1 px-2 py-1 text-sm bg-blue-600 text-white rounded"
                    >
                      Add
                    </button>
                  </div>
                </form>
              )}

              <div className="space-y-2">
                {role.permissions.map((perm) => (
                  <div key={perm.id} className="p-3 border rounded text-sm">
                    <div className="font-medium">
                      {perm.resource_type}:{perm.resource_id || '*'}
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-600">
                      <span className="px-2 py-0.5 bg-gray-100 rounded">{perm.action}</span>
                      <span
                        className={`px-2 py-0.5 rounded ${
                          perm.effect === 'allow'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {perm.effect}
                      </span>
                    </div>
                  </div>
                ))}
                {role.permissions.length === 0 && (
                  <p className="text-sm text-gray-500">No permissions yet</p>
                )}
              </div>
            </div>

            <div>
              <h4 className="font-semibold mb-2">User Count</h4>
              <p className="text-2xl font-bold text-blue-600">{role.user_count}</p>
              <p className="text-sm text-gray-600">users have this role</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
