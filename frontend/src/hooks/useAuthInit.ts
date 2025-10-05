/**
 * Hook to initialize authentication on app load
 * Rehydrates auth state from localStorage and sets up API client
 */

import { useEffect } from 'react';
import { useAuthStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';

export function useAuthInit() {
  useEffect(() => {
    // Get auth state from Zustand persistence
    const token = useAuthStore.getState().token;

    if (token) {
      // Rehydrate API client with token
      apiClient.setToken(token);
    }
  }, []);
}
