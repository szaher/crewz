'use client';

import { useState } from 'react';
import type { ConversationFolder } from '@/hooks/conversation/useConversationSessions';

interface FolderListProps {
  folders: ConversationFolder[];
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  onCreateFolder: (name: string) => Promise<any>;
  onUpdateFolder: (folderId: string, name: string) => Promise<any>;
  onDeleteFolder: (folderId: string) => Promise<void>;
}

export default function FolderList({
  folders,
  selectedFolderId,
  onSelectFolder,
  onCreateFolder,
  onUpdateFolder,
  onDeleteFolder,
}: FolderListProps) {
  const [creating, setCreating] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;

    try {
      await onCreateFolder(newFolderName.trim());
      setCreating(false);
      setNewFolderName('');
    } catch (err) {
      console.error('Failed to create folder:', err);
    }
  };

  const handleUpdateFolder = async (folderId: string) => {
    if (!editingName.trim()) return;

    try {
      await onUpdateFolder(folderId, editingName.trim());
      setEditingId(null);
      setEditingName('');
    } catch (err) {
      console.error('Failed to update folder:', err);
    }
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between mb-2 group">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          Folders
        </span>
        <button
          onClick={() => {
            setCreating(true);
            setNewFolderName('');
          }}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity"
          title="New folder"
          aria-label="New folder"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-4 h-4"
          >
            <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
          </svg>
        </button>
      </div>

      {/* Create folder inline form */}
      {creating && (
        <div className="flex items-center gap-1 p-1">
          <input
            autoFocus
            type="text"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                void handleCreateFolder();
              } else if (e.key === 'Escape') {
                setCreating(false);
                setNewFolderName('');
              }
            }}
            placeholder="Folder name"
            className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-700 rounded text-xs bg-white dark:bg-gray-900"
          />
          <button
            onClick={handleCreateFolder}
            className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Add
          </button>
          <button
            onClick={() => {
              setCreating(false);
              setNewFolderName('');
            }}
            className="px-2 py-1 text-xs border rounded hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            ✕
          </button>
        </div>
      )}

      {/* All conversations */}
      <button
        onClick={() => onSelectFolder(null)}
        className={`w-full text-left px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          selectedFolderId === null
            ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
        }`}
      >
        All Conversations
      </button>

      {/* Folder list */}
      {folders.map((folder) => (
        <div key={folder.id} className="group flex items-center gap-1">
          {editingId === folder.id ? (
            <div className="flex-1 flex items-center gap-1">
              <input
                autoFocus
                type="text"
                value={editingName}
                onChange={(e) => setEditingName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    void handleUpdateFolder(folder.id);
                  } else if (e.key === 'Escape') {
                    setEditingId(null);
                    setEditingName('');
                  }
                }}
                className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-700 rounded text-xs bg-white dark:bg-gray-900"
              />
              <button
                onClick={() => handleUpdateFolder(folder.id)}
                className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                ✓
              </button>
              <button
                onClick={() => {
                  setEditingId(null);
                  setEditingName('');
                }}
                className="px-2 py-1 text-xs border rounded hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                ✕
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={() => onSelectFolder(folder.id)}
                className={`flex-1 text-left px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  selectedFolderId === folder.id
                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
              >
                <div className="flex items-center gap-2">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="w-4 h-4"
                  >
                    <path d="M2 4.25A2.25 2.25 0 014.25 2h2.5A2.25 2.25 0 019 4.25v2.5A2.25 2.25 0 016.75 9h-2.5A2.25 2.25 0 012 6.75v-2.5zM2 13.25A2.25 2.25 0 014.25 11h2.5A2.25 2.25 0 019 13.25v2.5A2.25 2.25 0 016.75 18h-2.5A2.25 2.25 0 012 15.75v-2.5zM11 4.25A2.25 2.25 0 0113.25 2h2.5A2.25 2.25 0 0118 4.25v2.5A2.25 2.25 0 0115.75 9h-2.5A2.25 2.25 0 0111 6.75v-2.5zM15.25 11.75a.75.75 0 00-1.5 0v2h-2a.75.75 0 000 1.5h2v2a.75.75 0 001.5 0v-2h2a.75.75 0 000-1.5h-2v-2z" />
                  </svg>
                  <span className="truncate">{folder.name}</span>
                </div>
              </button>
              <button
                onClick={() => {
                  setEditingId(folder.id);
                  setEditingName(folder.name);
                }}
                className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity"
                title="Rename"
                aria-label="Rename folder"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="w-4 h-4"
                >
                  <path d="M5.433 13.917l1.262-3.155A4 4 0 017.58 9.42l6.92-6.918a2.121 2.121 0 013 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 01-.65-.65z" />
                  <path d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0010 3H4.75A2.75 2.75 0 002 5.75v9.5A2.75 2.75 0 004.75 18h9.5A2.75 2.75 0 0017 15.25V10a.75.75 0 00-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5z" />
                </svg>
              </button>
              <button
                onClick={() => onDeleteFolder(folder.id)}
                className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                title="Delete"
                aria-label="Delete folder"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="w-4 h-4"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
