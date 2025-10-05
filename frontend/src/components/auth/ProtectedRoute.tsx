'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/lib/store';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: 'admin' | 'member' | 'viewer';
}

export default function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, user } = useAuthStore();
  const [isHydrated, setIsHydrated] = useState(false);

  // Wait for Zustand to hydrate from localStorage
  useEffect(() => {
    const unsubscribe = useAuthStore.persist.onFinishHydration(() => {
      setIsHydrated(true);
    });

    // Check if already hydrated
    if (useAuthStore.persist.hasHydrated()) {
      setIsHydrated(true);
    }

    return () => {
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    // Only check auth after hydration is complete
    if (!isHydrated) return;

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
      router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
      return;
    }

    // Check role-based access
    if (requiredRole && user) {
      const roleHierarchy = { viewer: 0, member: 1, admin: 2 };
      const userLevel = roleHierarchy[user.role] || 0;
      const requiredLevel = roleHierarchy[requiredRole] || 0;

      if (userLevel < requiredLevel) {
        router.push('/dashboard?error=unauthorized');
      }
    }
  }, [isHydrated, isAuthenticated, user, requiredRole, router, pathname]);

  // Show loading while hydrating or checking auth
  if (!isHydrated || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return <>{children}</>;
}
