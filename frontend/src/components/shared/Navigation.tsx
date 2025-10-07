'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore, useTenantStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';
import UserProfileMenu from '../navigation/UserProfileMenu';

export default function Navigation() {
  const router = useRouter();
  const pathname = usePathname();
  const { currentTenant } = useTenantStore();

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: '📊' },
    { name: 'Flows', path: '/flows', icon: '🔀' },
    { name: 'Crews', path: '/crews', icon: '👥' },
    { name: 'Providers', path: '/providers', icon: '🔌' },
    { name: 'Tools', path: '/tools', icon: '🔧' },
    { name: 'Observability', path: '/observability', icon: '📈' },
    { name: 'Chat', path: '/chat', icon: '💬' },
  ];

  const isActive = (path: string) => {
    return pathname?.startsWith(path);
  };

  return (
    <nav className="bg-white border-r border-gray-200 w-64 min-h-screen flex flex-col">
      {/* Logo/Brand */}
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-900">CrewAI Platform</h1>
        {currentTenant && (
          <p className="text-sm text-gray-500 mt-1">{currentTenant.name}</p>
        )}
      </div>

      {/* Navigation Items */}
      <div className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.path}
            onClick={() => router.push(item.path)}
            className={`
              w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors
              ${isActive(item.path)
                ? 'bg-blue-50 text-blue-700 font-medium'
                : 'text-gray-700 hover:bg-gray-50'
              }
            `}
          >
            <span className="text-xl">{item.icon}</span>
            <span className="text-sm">{item.name}</span>
          </button>
        ))}
      </div>

      {/* User Profile Menu */}
      <div className="p-4 border-t border-gray-200">
        <UserProfileMenu />
      </div>
    </nav>
  );
}
