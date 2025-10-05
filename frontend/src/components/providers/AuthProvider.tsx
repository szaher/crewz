'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';

/**
 * AuthProvider - Initializes authentication on app load
 * Rehydrates auth state from localStorage and sets up API client
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Wait for Zustand to rehydrate from localStorage
    const unsubscribe = useAuthStore.persist.onFinishHydration(() => {
      const { token } = useAuthStore.getState();

      if (token) {
        // Rehydrate API client with token
        apiClient.setToken(token);
      }
    });

    // Also check immediately in case hydration already finished
    const { token } = useAuthStore.getState();
    if (token) {
      apiClient.setToken(token);
    }

    return () => {
      unsubscribe();
    };
  }, []);

  return <>{children}</>;
}
