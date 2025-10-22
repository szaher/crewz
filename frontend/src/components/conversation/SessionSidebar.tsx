'use client';

import { useState } from 'react';
import type { ConversationSession, ConversationFolder } from '@/hooks/conversation/useConversationSessions';
import SessionList from './SessionSidebar/SessionList';
import FolderList from './SessionSidebar/FolderList';
import SessionSearch from './SessionSidebar/SessionSearch';

interface SessionSidebarProps {
  sessions: ConversationSession[];
  folders: ConversationFolder[];
  loading: boolean;
  activeSessionId: string | null;
  selectedFolderId: string | null;
  searchQuery: string;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: () => Promise<void>;
  onUpdateSession: (sessionId: string, updates: Partial<ConversationSession>) => Promise<void>;
  onDeleteSession: (sessionId: string) => Promise<void>;
  onSetSearchQuery: (query: string) => void;
  onSetSelectedFolder: (folderId: string | null) => void;
  onCreateFolder: (name: string) => Promise<any>;
  onUpdateFolder: (folderId: string, name: string) => Promise<any>;
  onDeleteFolder: (folderId: string) => Promise<void>;
}

export default function SessionSidebar({
  sessions,
  folders,
  loading,
  activeSessionId,
  selectedFolderId,
  searchQuery,
  onSelectSession,
  onCreateSession,
  onUpdateSession,
  onDeleteSession,
  onSetSearchQuery,
  onSetSelectedFolder,
  onCreateFolder,
  onUpdateFolder,
  onDeleteFolder,
}: SessionSidebarProps) {
  return (
    <div className="w-80 flex-shrink-0 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Conversations
        </h2>
        <button
          onClick={onCreateSession}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-blue-600 dark:text-blue-400 transition-colors"
          title="New conversation"
          aria-label="New conversation"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="w-5 h-5"
          >
            <path d="M12 4.5a.75.75 0 01.75.75V11h5.75a.75.75 0 010 1.5H12.75v5.75a.75.75 0 01-1.5 0V12.5H5.5a.75.75 0 010-1.5h5.75V5.25A.75.75 0 0112 4.5z" />
          </svg>
        </button>
      </div>

        {/* Search */}
        <div className="p-3 border-b border-gray-200 dark:border-gray-800">
          <SessionSearch
            value={searchQuery}
            onChange={onSetSearchQuery}
            onSearch={() => {/* Search happens automatically via useEffect in hook */}}
          />
        </div>

        {/* Folders */}
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-800">
          <FolderList
            folders={folders}
            selectedFolderId={selectedFolderId}
            onSelectFolder={onSetSelectedFolder}
            onCreateFolder={onCreateFolder}
            onUpdateFolder={onUpdateFolder}
            onDeleteFolder={onDeleteFolder}
          />
        </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto">
        <SessionList
          sessions={sessions}
          folders={folders}
          loading={loading}
          activeSessionId={activeSessionId}
          onSelectSession={onSelectSession}
          onUpdateSession={onUpdateSession}
          onDeleteSession={onDeleteSession}
        />
      </div>
    </div>
  );
}
