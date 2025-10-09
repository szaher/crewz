'use client';

import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import { useUIStore, useAuthStore, useTenantStore } from '@/lib/store';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';

export default function SettingsPage() {
  const router = useRouter();
  const { theme, setTheme } = useUIStore();
  const { clearAuth, user } = useAuthStore();
  const { currentTenant, setTenant } = useTenantStore();
  const [orgName, setOrgName] = useState(currentTenant?.name || '');
  const [limits, setLimits] = useState({
    max_users:  currentTenant ? (currentTenant as any).max_users ?? 10 : 10,
    max_agents: currentTenant ? (currentTenant as any).max_agents ?? 50 : 50,
    max_flows:  currentTenant ? (currentTenant as any).max_flows ?? 100 : 100,
  });
  const [loadingTenant, setLoadingTenant] = useState(false);
  const [savingTenant, setSavingTenant] = useState(false);
  const isAdmin = user?.role === 'admin';
  const [settingsJson, setSettingsJson] = useState<string>(JSON.stringify(currentTenant?.settings || {}, null, 2));
  const [settingsError, setSettingsError] = useState<string | null>(null);

  useEffect(() => {
    const loadTenant = async () => {
      setLoadingTenant(true);
      const res = await apiClient.get('/api/v1/tenant');
      setLoadingTenant(false);
      if (res.data) {
        const t = res.data;
        setOrgName(t.name);
        setLimits({
          max_users: t.max_users,
          max_agents: t.max_agents,
          max_flows: t.max_flows,
        });
        setSettingsJson(JSON.stringify(t.settings || {}, null, 2));
        // Update local tenant store with any available fields
        setTenant({
          id: t.id,
          name: t.name,
          schema_name: t.schema_name,
          is_active: t.status === 'active',
          settings: t.settings || {},
        } as any);
      }
    };
    void loadTenant();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLogout = () => {
    clearAuth();
    router.push('/login');
  };

  const saveTenant = async () => {
    setSavingTenant(true);
    setSettingsError(null);
    let parsedSettings: any = undefined;
    try {
      parsedSettings = JSON.parse(settingsJson || '{}');
    } catch (e) {
      setSettingsError('Invalid JSON in settings');
      setSavingTenant(false);
      return;
    }
    const res = await apiClient.put('/api/v1/tenant', {
      name: orgName,
      max_users: limits.max_users,
      max_agents: limits.max_agents,
      max_flows: limits.max_flows,
      settings: parsedSettings,
    });
    setSavingTenant(false);
    if (res.data) {
      const t = res.data;
      setTenant({
        id: t.id,
        name: t.name,
        schema_name: t.schema_name,
        is_active: t.status === 'active',
        settings: t.settings || {},
      } as any);
    } else if (res.error) {
      alert(res.error);
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
              <p className="mt-2 text-gray-600 dark:text-gray-400">Manage your preferences</p>
            </div>

            <div className="space-y-8">
              {/* Appearance */}
              <section className="bg-white dark:bg-gray-900 rounded-lg shadow border border-gray-200 dark:border-gray-800">
                <div className="p-6 border-b border-gray-200 dark:border-gray-800">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Appearance</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Customize how the app looks to you.</p>
                </div>
                <div className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-gray-100">Theme</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Choose light, dark, or follow system</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {(['light','dark','system'] as const).map((t) => (
                        <button
                          key={t}
                          onClick={() => setTheme(t)}
                          className={`px-3 py-1.5 rounded-md border text-sm capitalize ${
                            theme === t ? 'bg-blue-600 text-white border-blue-600' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                          }`}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-3">Theme preference is saved on this device.</p>
                </div>
              </section>

              {/* Organization */}
              <section className="bg-white dark:bg-gray-900 rounded-lg shadow border border-gray-200 dark:border-gray-800">
                <div className="p-6 border-b border-gray-200 dark:border-gray-800">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Organization</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Your current workspace details.</p>
                </div>
                <div className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Name</label>
                    <input
                      type="text"
                      disabled={!isAdmin}
                      value={orgName}
                      onChange={(e) => setOrgName(e.target.value)}
                      className={`mt-1 block w-full px-3 py-2 border rounded-md ${!isAdmin ? 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400' : 'border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600'}`}
                    />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {(['max_users','max_agents','max_flows'] as const).map((key) => (
                      <div key={key}>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">{key.replace('_',' ')}</label>
                        <input
                          type="number"
                          min={1}
                          disabled={!isAdmin}
                          value={(limits as any)[key]}
                          onChange={(e) => setLimits({...limits, [key]: Number(e.target.value)})}
                          className={`mt-1 block w-full px-3 py-2 border rounded-md ${!isAdmin ? 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400' : 'border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600'}`}
                        />
                      </div>
                    ))}
                  </div>
                  <div>
                    <div className="flex items-center justify-between">
                      <div className="text-sm text-gray-500 dark:text-gray-400">Settings (JSON)</div>
                      {settingsError && <div className="text-xs text-red-600">{settingsError}</div>}
                    </div>
                    <textarea
                      value={settingsJson}
                      onChange={(e) => setSettingsJson(e.target.value)}
                      disabled={!isAdmin}
                      rows={8}
                      className={`mt-1 block w-full p-3 text-xs font-mono border rounded-md ${!isAdmin ? 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400' : 'border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600'}`}
                    />
                  </div>
                  <div className="pt-2 flex justify-end">
                    <button
                      onClick={saveTenant}
                      disabled={!isAdmin || savingTenant}
                      className={`px-4 py-2 rounded-md text-white ${(!isAdmin || savingTenant) ? 'bg-blue-300' : 'bg-blue-600 hover:bg-blue-700'}`}
                    >
                      {savingTenant ? 'Saving...' : 'Save Settings'}
                    </button>
                  </div>
                </div>
              </section>

              {/* Security */}
              <section className="bg-white dark:bg-gray-900 rounded-lg shadow border border-gray-200 dark:border-gray-800">
                <div className="p-6 border-b border-gray-200 dark:border-gray-800">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Security</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Session and account security options.</p>
                </div>
                <div className="p-6 flex items-center justify-between">
                  <div>
                    <div className="font-medium text-gray-900 dark:text-gray-100">Sign out</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">End your current session on this device.</div>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                  >
                    Log out
                  </button>
                </div>
              </section>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
