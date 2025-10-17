'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore, useTenantStore, useUIStore } from '@/lib/store';
import SidebarToggle from '../navigation/SidebarToggle';
import NotificationsBell from '../navigation/NotificationsBell';
import { apiClient } from '@/lib/api-client';
import UserProfileMenu from '../navigation/UserProfileMenu';

export default function Navigation() {
  const router = useRouter();
  const pathname = usePathname();
  const { currentTenant } = useTenantStore();
  const { user } = useAuthStore();
  const { sidebarOpen } = useUIStore();

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: '📊' },
    { name: 'Flows', path: '/flows', icon: '🔀' },
    { name: 'Crews', path: '/crews', icon: '👥' },
    { name: 'Agents', path: '/agents', icon: '🤖' },
    { name: 'Tasks', path: '/tasks', icon: '✅' },
    { name: 'Providers', path: '/providers', icon: '🔌' },
    { name: 'Tools', path: '/tools', icon: '🔧' },
    { name: 'Prompts', path: '/prompts', icon: '📝' },
    { name: 'Executions', path: '/executions', icon: '⚙️' },
    { name: 'Observability', path: '/observability', icon: '📈' },
    { name: 'Chat', path: '/chat', icon: '💬' },
  ];

  const adminItems = user?.role === 'admin' ? [
    { name: 'Users', path: '/users', icon: '🧑‍🤝‍🧑' },
    { name: 'Roles', path: '/roles', icon: '👤' },
    { name: 'Policies', path: '/policies', icon: '🔒' },
    { name: 'Audit Logs', path: '/audit', icon: '📋' },
  ] : [];

  const isActive = (path: string) => {
    return pathname?.startsWith(path);
  };

  if (!sidebarOpen) {
    // Collapsed sidebar: keep a slim rail with only the toggle button
    return (
      <nav className="bg-white border-r border-gray-200 w-12 min-h-screen flex flex-col items-center py-3">
        <SidebarToggle />
      </nav>
    );
  }

  return (
    <nav className="bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 w-64 min-h-screen flex flex-col">
      {/* Logo/Brand + Toggle */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Automation Platform</h1>
          {currentTenant && (
            <p className="text-sm text-gray-500 dark:text-gray-400">{currentTenant.name}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <NotificationsBell />
          <SidebarToggle />
        </div>
      </div>

      {/* Navigation Items */}
      <div className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <button
            key={item.path}
            onClick={() => router.push(item.path)}
            className={`
              w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors
              ${isActive(item.path)
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 font-medium'
                : 'text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800'
              }
            `}
          >
            <span className="text-xl">{item.icon}</span>
            <span className="text-sm">{item.name}</span>
          </button>
        ))}

        {/* Admin Section */}
        {adminItems.length > 0 && (
          <>
            <div className="pt-4 pb-2 px-4">
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Administration
              </h3>
            </div>
            {adminItems.map((item) => (
              <button
                key={item.path}
                onClick={() => router.push(item.path)}
                className={`
                  w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors
                  ${isActive(item.path)
                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 font-medium'
                    : 'text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800'
                  }
                `}
              >
                <span className="text-xl">{item.icon}</span>
                <span className="text-sm">{item.name}</span>
              </button>
            ))}
          </>
        )}
      </div>

      {/* User Profile Menu */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-800">
        <UserProfileMenu />
      </div>
    </nav>
  );
}
