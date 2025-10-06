/**
 * Auth setup and initialization
 * Configures the API client to handle authentication state
 */

import { apiClient } from './api-client';
import { useAuthStore } from './store';

/**
 * Initialize auth handling
 * Sets up the API client to automatically logout on 401 responses
 */
export function initializeAuth() {
  // Only run on client side
  if (typeof window === 'undefined') return;

  // Set up the unauthorized handler
  apiClient.setUnauthorizedHandler(() => {
    // Clear auth state from store
    useAuthStore.getState().clearAuth();

    // Redirect to login page
    const currentPath = window.location.pathname;
    if (currentPath !== '/login' && currentPath !== '/register') {
      window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}&reason=session_expired`;
    }
  });

  // Sync token from auth store to API client
  const token = useAuthStore.getState().token;
  if (token) {
    apiClient.setToken(token);
  }

  // Subscribe to auth store changes to keep API client in sync
  useAuthStore.subscribe((state) => {
    if (state.token) {
      apiClient.setToken(state.token);
    } else {
      apiClient.clearToken();
    }
  });
}
