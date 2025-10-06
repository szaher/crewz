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
    // Set up the unauthorized handler for automatic logout on 401
    apiClient.setUnauthorizedHandler(() => {
      // Clear auth state from store
      useAuthStore.getState().clearAuth();

      // Redirect to login page with session expired message
      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && currentPath !== '/register') {
        window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}&reason=session_expired`;
      }
    });

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

    // Subscribe to auth store changes to keep API client in sync
    const authUnsubscribe = useAuthStore.subscribe((state) => {
      if (state.token) {
        apiClient.setToken(state.token);
      } else {
        apiClient.clearToken();
      }
    });

    return () => {
      unsubscribe();
      authUnsubscribe();
    };
  }, []);

  return <>{children}</>;
}
