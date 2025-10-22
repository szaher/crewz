/**
 * Centralized API URL configuration
 * Handles dynamic hostname detection for LAN/network access
 */

/**
 * Get the API base URL
 * - In browser: Uses dynamic hostname detection (window.location.hostname:8000)
 * - With NEXT_PUBLIC_API_URL set to non-localhost: Uses environment variable
 * - Fallback: http://localhost:8000
 */
export function getApiBaseUrl(): string {
  const ENV_URL = process.env.NEXT_PUBLIC_API_URL;

  if (typeof window !== 'undefined') {
    // Browser environment: use dynamic hostname for LAN access
    const dynamicUrl = `${window.location.protocol}//${window.location.hostname}:8000`;

    // If env is set to a non-localhost URL, use it; otherwise use dynamic host
    if (ENV_URL && !/^(https?:\/\/)?(localhost|127\.0\.0\.1)(:|$)/i.test(ENV_URL)) {
      return ENV_URL;
    }

    return dynamicUrl;
  }

  // Server-side or fallback
  return ENV_URL || 'http://localhost:8000';
}

/**
 * Get WebSocket URL (ws:// or wss://)
 */
export function getWsBaseUrl(): string {
  const apiUrl = getApiBaseUrl();
  return apiUrl.replace(/^http/, 'ws');
}
