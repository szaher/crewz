'use client';

import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import { useEffect, useMemo, useState } from 'react';
import { apiClient } from '@/lib/api-client';

type UserRow = {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'member' | 'viewer';
  is_active: boolean;
  created_at: string;
};

export default function UsersPage() {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);

  // Create modal state
  const [showCreate, setShowCreate] = useState(false);
  const [newUser, setNewUser] = useState({
    email: '',
    full_name: '',
    role: 'member' as 'admin' | 'member' | 'viewer',
    password: '',
  });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    void loadUsers();
  }, [page, pageSize]);

  const loadUsers = async () => {
    setLoading(true);
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (q.trim()) params.set('q', q.trim());
    const res = await apiClient.get(`/api/v1/users?${params.toString()}`);
    setLoading(false);
    if (res.data) {
      setUsers(res.data.users || []);
      setTotal(res.data.total || 0);
    } else if (res.error) {
      setError(res.error);
    }
  };

  const createUser = async () => {
    setCreating(true);
    const res = await apiClient.post('/api/v1/users', newUser);
    setCreating(false);
    if (res.data) {
      setShowCreate(false);
      setNewUser({ email: '', full_name: '', role: 'member', password: '' });
      await loadUsers();
    } else if (res.error) {
      alert(res.error);
    }
  };

  // Invite flow
  const [showInvite, setShowInvite] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [inviteUser, setInviteUser] = useState({ email: '', full_name: '', role: 'member' as 'admin'|'member'|'viewer' });
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const sendInvite = async () => {
    setInviting(true);
    const res = await apiClient.post('/api/v1/users/invite', inviteUser);
    setInviting(false);
    if (res.data) {
      const token = res.data.invite_token;
      const url = `${window.location.origin}/accept-invite?token=${encodeURIComponent(token)}`;
      setInviteLink(url);
    } else if (res.error) {
      alert(res.error);
    }
  };

  const updateUser = async (id: number, patch: Partial<UserRow> & { password?: string }) => {
    const res = await apiClient.put(`/api/v1/users/${id}`, patch);
    if (res.error) {
      alert(res.error);
    } else {
      await loadUsers();
    }
  };

  const deleteUser = async (id: number) => {
    if (!confirm('Delete this user?')) return;
    const res = await apiClient.delete(`/api/v1/users/${id}`);
    if (res.error) {
      alert(res.error);
    } else {
      await loadUsers();
    }
  };

  return (
    <ProtectedRoute requiredRole="admin">
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-6xl mx-auto p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">Users</h1>
                <p className="text-sm text-gray-600">Manage members of your organization</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowInvite(true)}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                >
                  Invite User
                </button>
                <button
                  onClick={() => setShowCreate(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  + Add User
                </button>
              </div>
            </div>

            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <input
                  placeholder="Search name or email..."
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { setPage(1); void loadUsers(); } }}
                  className="w-64 px-3 py-2 border border-gray-300 rounded-md"
                />
                <button onClick={() => { setPage(1); void loadUsers(); }} className="px-3 py-2 border rounded-md">Search</button>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span>Rows:</span>
                <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }} className="border-gray-300 rounded-md">
                  {[10,20,50,100].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : error ? (
              <div className="p-4 bg-red-50 border border-red-200 rounded text-red-700">{error}</div>
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Active</th>
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {users.map((u) => (
                      <tr key={u.id}>
                        <td className="px-4 py-3 text-sm text-gray-900">{u.full_name}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{u.email}</td>
                        <td className="px-4 py-3">
                          <select
                            value={u.role}
                            onChange={(e) => updateUser(u.id, { role: e.target.value as any })}
                            className="text-sm border-gray-300 rounded-md"
                          >
                            <option value="admin">admin</option>
                            <option value="member">member</option>
                            <option value="viewer">viewer</option>
                          </select>
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={u.is_active}
                            onChange={(e) => updateUser(u.id, { is_active: e.target.checked })}
                          />
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => deleteUser(u.id)}
                            className="px-3 py-1.5 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="flex items-center justify-between p-3 border-t border-gray-200 text-sm">
                  <div>
                    Showing {(users.length ? (page-1)*pageSize+1 : 0)}–{(page-1)*pageSize+users.length} of {total}
                  </div>
                  <div className="flex items-center gap-2">
                    <button disabled={page<=1} onClick={() => setPage(p => Math.max(1, p-1))} className="px-3 py-1.5 border rounded disabled:opacity-50">Prev</button>
                    <div>Page {page}</div>
                    <button disabled={(page*pageSize)>=total} onClick={() => setPage(p => p+1)} className="px-3 py-1.5 border rounded disabled:opacity-50">Next</button>
                  </div>
                </div>
              </div>
            )}

            {showCreate && (
              <div className="fixed inset-0 bg-black/30 flex items-center justify-center">
                <div className="bg-white rounded-lg shadow-lg border border-gray-200 w-full max-w-md">
                  <div className="p-4 border-b border-gray-200 font-medium">Add User</div>
                  <div className="p-4 space-y-3">
                    <div>
                      <label className="block text-sm text-gray-700">Full Name</label>
                      <input
                        value={newUser.full_name}
                        onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-700">Email</label>
                      <input
                        type="email"
                        value={newUser.email}
                        onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-700">Role</label>
                      <select
                        value={newUser.role}
                        onChange={(e) => setNewUser({ ...newUser, role: e.target.value as any })}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                      >
                        <option value="admin">admin</option>
                        <option value="member">member</option>
                        <option value="viewer">viewer</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-700">Temporary Password</label>
                      <input
                        type="password"
                        value={newUser.password}
                        onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                  </div>
                  <div className="p-4 border-t border-gray-200 flex justify-end gap-2">
                    <button
                      onClick={() => setShowCreate(false)}
                      className="px-4 py-2 rounded-md border border-gray-300"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={createUser}
                      disabled={creating || !newUser.email || !newUser.full_name || !newUser.password}
                      className={`px-4 py-2 rounded-md text-white ${creating ? 'bg-blue-300' : 'bg-blue-600 hover:bg-blue-700'}`}
                    >
                      {creating ? 'Creating...' : 'Create'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {showInvite && (
              <div className="fixed inset-0 bg-black/30 flex items-center justify-center">
                <div className="bg-white rounded-lg shadow-lg border border-gray-200 w-full max-w-md">
                  <div className="p-4 border-b border-gray-200 font-medium">Invite User</div>
                  <div className="p-4 space-y-3">
                    <div>
                      <label className="block text-sm text-gray-700">Full Name</label>
                      <input
                        value={inviteUser.full_name}
                        onChange={(e) => setInviteUser({ ...inviteUser, full_name: e.target.value })}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-700">Email</label>
                      <input
                        type="email"
                        value={inviteUser.email}
                        onChange={(e) => setInviteUser({ ...inviteUser, email: e.target.value })}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-700">Role</label>
                      <select
                        value={inviteUser.role}
                        onChange={(e) => setInviteUser({ ...inviteUser, role: e.target.value as any })}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                      >
                        <option value="admin">admin</option>
                        <option value="member">member</option>
                        <option value="viewer">viewer</option>
                      </select>
                    </div>
                    {inviteLink ? (
                      <div>
                        <div className="text-sm text-gray-700 mb-1">Invitation Link</div>
                        <div className="flex items-center gap-2">
                          <input readOnly value={inviteLink} className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-xs" />
                          <button onClick={() => navigator.clipboard.writeText(inviteLink)} className="px-3 py-2 border rounded">Copy</button>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">Share this link with the user to set their password.</div>
                      </div>
                    ) : null}
                  </div>
                  <div className="p-4 border-t border-gray-200 flex justify-end gap-2">
                    <button
                      onClick={() => { setShowInvite(false); setInviteLink(null); setInviteUser({ email:'', full_name:'', role:'member' }); }}
                      className="px-4 py-2 rounded-md border border-gray-300"
                    >
                      Close
                    </button>
                    {!inviteLink && (
                      <button
                        onClick={sendInvite}
                        disabled={inviting || !inviteUser.email || !inviteUser.full_name}
                        className={`px-4 py-2 rounded-md text-white ${inviting ? 'bg-indigo-300' : 'bg-indigo-600 hover:bg-indigo-700'}`}
                      >
                        {inviting ? 'Sending...' : 'Send Invite'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
