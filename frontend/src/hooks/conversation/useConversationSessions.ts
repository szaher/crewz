/**
 * Custom hook for managing conversation sessions
 * Handles CRUD operations for sessions and folders
 */

import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';

export interface ConversationSession {
  id: string;
  title: string;
  folder_id?: string | null;
  created_at: string;
  updated_at: string;
  llm_provider_id?: number;
  system_prompt?: string;
  crew_id?: string | null;
}

export interface ConversationFolder {
  id: string;
  name: string;
}

interface UseConversationSessionsOptions {
  autoLoad?: boolean;
}

export function useConversationSessions(options: UseConversationSessionsOptions = {}) {
  const { autoLoad = true } = options;

  const [sessions, setSessions] = useState<ConversationSession[]>([]);
  const [folders, setFolders] = useState<ConversationFolder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) {
        params.set('q', searchQuery.trim());
      }

      // Add folder_id parameter if a specific folder is selected
      if (selectedFolderId !== null) {
        params.set('folder_id', selectedFolderId);
      }

      const response = await apiClient.get(
        `/api/v1/chat/sessions${params.toString() ? `?${params.toString()}` : ''}`
      );

      let sessionList = Array.isArray(response.data) ? response.data : [];

      // If selectedFolderId is null (viewing "All" / no folder view),
      // filter to show only sessions without a folder
      if (selectedFolderId === null) {
        sessionList = sessionList.filter((session: any) =>
          session.folder_id === null || session.folder_id === undefined
        );
      }

      // Sort by most recent first
      const sorted = sessionList.sort((a: any, b: any) => {
        const aTime = a.updated_at || a.created_at || '';
        const bTime = b.updated_at || b.created_at || '';
        return new Date(bTime).getTime() - new Date(aTime).getTime();
      });

      setSessions(sorted);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedFolderId]);

  const loadFolders = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/v1/chat/folders');
      setFolders(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Failed to load folders:', err);
      setFolders([]);
    }
  }, []);

  const createSession = useCallback(async (data: {
    title: string;
    system_prompt?: string;
    llm_provider_id?: number;
    tool_ids?: number[];
    folder_id?: number;
  }) => {
    try {
      const response = await apiClient.post('/api/v1/chat/sessions', data);

      if (response.error) {
        throw new Error(response.error);
      }

      const newSession = response.data?.session ?? response.data;
      setSessions(prev => [newSession, ...prev]);

      return newSession;
    } catch (err) {
      throw err instanceof Error ? err : new Error('Failed to create session');
    }
  }, []);

  const updateSession = useCallback(async (
    sessionId: string,
    updates: Partial<ConversationSession>
  ) => {
    try {
      const response = await apiClient.put(`/api/v1/chat/sessions/${sessionId}`, updates);

      if (response.error) {
        throw new Error(response.error);
      }

      // If folder_id was updated, reload sessions to ensure proper filtering
      if ('folder_id' in updates) {
        await loadSessions();
      } else {
        setSessions(prev => prev.map(s =>
          String(s.id) === sessionId ? { ...s, ...updates } : s
        ));
      }

      return response.data;
    } catch (err) {
      throw err instanceof Error ? err : new Error('Failed to update session');
    }
  }, [loadSessions]);

  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      const response = await apiClient.delete(`/api/v1/chat/sessions/${sessionId}`);

      if (response.error) {
        throw new Error(response.error);
      }

      setSessions(prev => prev.filter(s => String(s.id) !== sessionId));
    } catch (err) {
      throw err instanceof Error ? err : new Error('Failed to delete session');
    }
  }, []);

  const createFolder = useCallback(async (name: string) => {
    try {
      const response = await apiClient.post('/api/v1/chat/folders', { name });

      if (response.error) {
        throw new Error(response.error);
      }

      await loadFolders();
      return response.data;
    } catch (err) {
      throw err instanceof Error ? err : new Error('Failed to create folder');
    }
  }, [loadFolders]);

  const updateFolder = useCallback(async (folderId: string, name: string) => {
    try {
      const response = await apiClient.put(`/api/v1/chat/folders/${folderId}`, { name });

      if (response.error) {
        throw new Error(response.error);
      }

      await loadFolders();
      return response.data;
    } catch (err) {
      throw err instanceof Error ? err : new Error('Failed to update folder');
    }
  }, [loadFolders]);

  const deleteFolder = useCallback(async (folderId: string) => {
    try {
      const response = await apiClient.delete(`/api/v1/chat/folders/${folderId}`);

      if (response.error) {
        throw new Error(response.error);
      }

      await loadFolders();
      await loadSessions(); // Reload sessions as their folder_id may have changed
    } catch (err) {
      throw err instanceof Error ? err : new Error('Failed to delete folder');
    }
  }, [loadFolders, loadSessions]);

  // Auto-load on mount
  useEffect(() => {
    if (autoLoad) {
      void loadSessions();
      void loadFolders();
    }
  }, [autoLoad, loadSessions, loadFolders]);

  // Reload sessions when filters change
  useEffect(() => {
    if (autoLoad) {
      void loadSessions();
    }
  }, [searchQuery, selectedFolderId, autoLoad, loadSessions]);

  // Periodic refresh disabled - sessions will refresh when needed
  // useEffect(() => {
  //   const interval = setInterval(() => {
  //     void loadSessions();
  //   }, 10000);
  //   return () => clearInterval(interval);
  // }, [loadSessions]);

  return {
    // State
    sessions,
    folders,
    loading,
    error,

    // Filters
    searchQuery,
    setSearchQuery,
    selectedFolderId,
    setSelectedFolderId,

    // Actions
    loadSessions,
    loadFolders,
    createSession,
    updateSession,
    deleteSession,
    createFolder,
    updateFolder,
    deleteFolder,
  };
}
