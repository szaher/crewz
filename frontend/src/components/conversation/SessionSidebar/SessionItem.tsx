'use client';

import { useState } from 'react';
import type { ConversationSession, ConversationFolder } from '@/hooks/conversation/useConversationSessions';

interface SessionItemProps {
  session: ConversationSession;
  folders: ConversationFolder[];
  isActive: boolean;
  isEditing: boolean;
  isDeleting: boolean;
  onSelect: () => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onUpdate: (updates: Partial<ConversationSession>) => Promise<void>;
  onStartDelete: () => void;
  onCancelDelete: () => void;
  onDelete: () => Promise<void>;
}

export default function SessionItem({
  session,
  folders,
  isActive,
  isEditing,
  isDeleting,
  onSelect,
  onStartEdit,
  onCancelEdit,
  onUpdate,
  onStartDelete,
  onCancelDelete,
  onDelete,
}: SessionItemProps) {
  const [editTitle, setEditTitle] = useState(session.title);
  const [showFolderMenu, setShowFolderMenu] = useState(false);

  const handleSaveEdit = async () => {
    if (!editTitle.trim()) {
      onCancelEdit();
      return;
    }

    await onUpdate({ title: editTitle.trim() });
  };

  const handleMoveToFolder = async (folderId: string | null) => {
    await onUpdate({ folder_id: folderId });
    setShowFolderMenu(false);
  };

  if (isDeleting) {
    return (
      <div className="px-2 py-2 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
        <div className="text-sm text-red-900 dark:text-red-200 mb-2">
          Delete this conversation?
        </div>
        <div className="flex gap-2">
          <button
            onClick={onDelete}
            className="flex-1 px-3 py-1.5 text-xs bg-red-600 text-white rounded hover:bg-red-700"
          >
            Delete
          </button>
          <button
            onClick={onCancelDelete}
            className="flex-1 px-3 py-1.5 text-xs border rounded hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  if (isEditing) {
    return (
      <div className="px-2 py-1 rounded-md bg-gray-50 dark:bg-gray-800">
        <input
          autoFocus
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              void handleSaveEdit();
            } else if (e.key === 'Escape') {
              setEditTitle(session.title);
              onCancelEdit();
            }
          }}
          className="w-full px-2 py-1 border border-gray-300 dark:border-gray-700 rounded text-sm bg-white dark:bg-gray-900 mb-2"
        />
        <div className="flex gap-2">
          <button
            onClick={handleSaveEdit}
            className="flex-1 px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Save
          </button>
          <button
            onClick={() => {
              setEditTitle(session.title);
              onCancelEdit();
            }}
            className="flex-1 px-3 py-1.5 text-xs border rounded hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`group rounded-md px-2 py-1.5 text-sm transition-colors ${
        isActive
          ? 'bg-blue-100 text-blue-900 dark:bg-blue-900/30 dark:text-blue-300'
          : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-200'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <button
          onClick={onSelect}
          className="flex-1 font-medium truncate text-left"
        >
          {session.title || 'Untitled'}
        </button>

        {/* Actions */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          {/* Rename */}
          <button
            onClick={onStartEdit}
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
            title="Rename"
            aria-label="Rename conversation"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-3.5 h-3.5"
            >
              <path d="M5.433 13.917l1.262-3.155A4 4 0 017.58 9.42l6.92-6.918a2.121 2.121 0 013 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 01-.65-.65z" />
              <path d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0010 3H4.75A2.75 2.75 0 002 5.75v9.5A2.75 2.75 0 004.75 18h9.5A2.75 2.75 0 0017 15.25V10a.75.75 0 00-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5z" />
            </svg>
          </button>

          {/* Move to folder */}
          <div className="relative">
            <button
              onClick={() => setShowFolderMenu(!showFolderMenu)}
              className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
              title="Move to folder"
              aria-label="Move to folder"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-3.5 h-3.5"
              >
                <path d="M2 4.25A2.25 2.25 0 014.25 2h2.5A2.25 2.25 0 019 4.25v2.5A2.25 2.25 0 016.75 9h-2.5A2.25 2.25 0 012 6.75v-2.5zM2 13.25A2.25 2.25 0 014.25 11h2.5A2.25 2.25 0 019 13.25v2.5A2.25 2.25 0 016.75 18h-2.5A2.25 2.25 0 012 15.75v-2.5zM11 4.25A2.25 2.25 0 0113.25 2h2.5A2.25 2.25 0 0118 4.25v2.5A2.25 2.25 0 0115.75 9h-2.5A2.25 2.25 0 0111 6.75v-2.5zM15.25 11.75a.75.75 0 00-1.5 0v2h-2a.75.75 0 000 1.5h2v2a.75.75 0 001.5 0v-2h2a.75.75 0 000-1.5h-2v-2z" />
              </svg>
            </button>

            {showFolderMenu && (
              <div className="absolute z-10 right-0 top-full mt-1 w-48 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1">
                <button
                  onClick={() => handleMoveToFolder(null)}
                  className={`block w-full text-left px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 ${
                    session.folder_id == null ? 'text-blue-600 dark:text-blue-400 font-medium' : ''
                  }`}
                >
                  No Folder
                </button>
                {folders.map((folder) => (
                  <button
                    key={folder.id}
                    onClick={() => handleMoveToFolder(folder.id)}
                    className={`block w-full text-left px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 ${
                      session.folder_id === folder.id ? 'text-blue-600 dark:text-blue-400 font-medium' : ''
                    }`}
                  >
                    {folder.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Delete */}
          <button
            onClick={onStartDelete}
            className="p-1.5 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400"
            title="Delete"
            aria-label="Delete conversation"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-3.5 h-3.5"
            >
              <path
                fillRule="evenodd"
                d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
