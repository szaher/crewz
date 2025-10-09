'use client';

import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import { useAuthStore, useTenantStore } from '@/lib/store';
import { useState } from 'react';
import { apiClient } from '@/lib/api-client';

export default function ProfilePage() {
  const { user, token, setAuth } = useAuthStore();
  const { currentTenant } = useTenantStore();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwdMsg, setPwdMsg] = useState<string | null>(null);

  const handleSave = async () => {
    if (!fullName.trim()) return;
    setSaving(true);
    setMessage(null);
    const res = await apiClient.put('/api/v1/users/me', { full_name: fullName });
    setSaving(false);
    if (res.error) {
      setMessage(res.error || 'Failed to update profile');
      return;
    }
    const updated = res.data;
    if (updated && user) {
      // Update local auth user with new name, keep token
      setAuth(
        {
          ...user,
          full_name: updated.full_name,
        },
        token || ''
      );
      setMessage('Profile updated');
    }
  };

  const handleChangePassword = async () => {
    setPwdMsg(null);
    if (!currentPassword || !newPassword || newPassword !== confirmPassword) {
      setPwdMsg('Please enter valid passwords and ensure they match.');
      return;
    }
    const res = await apiClient.post('/api/v1/users/me/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    if (res.error) {
      setPwdMsg(res.error);
    } else {
      setPwdMsg('Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900">Profile</h1>
              <p className="mt-2 text-gray-600">View your account details</p>
            </div>

            <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
              <div className="p-6 flex items-center gap-4 border-b border-gray-200">
                <div className="w-14 h-14 rounded-full bg-blue-600 flex items-center justify-center text-white text-xl font-semibold">
                  {user?.full_name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div>
                  <div className="text-lg font-medium text-gray-900">{user?.full_name || '—'}</div>
                  <div className="text-sm text-gray-500">{user?.email || '—'}</div>
                </div>
              </div>

              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Full Name</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Email</label>
                  <div className="mt-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                    {user?.email || '—'}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Role</label>
                  <div className="mt-1 inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-800">
                    {user?.role || '—'}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Organization</label>
                  <div className="mt-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                    {currentTenant?.name || '—'}
                  </div>
                </div>
              </div>

              <div className="p-6 border-t border-gray-200 flex items-center justify-between">
                <div className="text-sm text-gray-500">
                  Update your name. Email and role are managed by admins.
                </div>
                <button
                  onClick={handleSave}
                  disabled={saving || !fullName.trim()}
                  className={`px-4 py-2 rounded-md text-white ${saving || !fullName.trim() ? 'bg-blue-300' : 'bg-blue-600 hover:bg-blue-700'}`}
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
              {message && (
                <div className="px-6 pb-6 text-sm text-green-700">{message}</div>
              )}
            </div>

            {/* Security settings */}
            <div className="mt-8 bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Security</h2>
                <p className="text-sm text-gray-600 mt-1">Change your account password</p>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Current Password</label>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">New Password</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Confirm New Password</label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600"
                  />
                </div>
              </div>
              <div className="p-6 pt-0 flex items-center justify-end gap-4">
                {pwdMsg && (
                  <div className={`text-sm ${pwdMsg.includes('success') ? 'text-green-700' : 'text-red-700'}`}>{pwdMsg}</div>
                )}
                <button
                  onClick={handleChangePassword}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Update Password
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
