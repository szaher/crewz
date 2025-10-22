'use client';

import { useState } from 'react';
import type { ConversationSession, ConversationFolder } from '@/hooks/conversation/useConversationSessions';
import SessionItem from './SessionItem';

interface SessionListProps {
  sessions: ConversationSession[];
  folders: ConversationFolder[];
  loading: boolean;
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onUpdateSession: (sessionId: string, updates: Partial<ConversationSession>) => Promise<void>;
  onDeleteSession: (sessionId: string) => Promise<void>;
}

export default function SessionList({
  sessions,
  folders,
  loading,
  activeSessionId,
  onSelectSession,
  onUpdateSession,
  onDeleteSession,
}: SessionListProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
        No conversations yet
      </div>
    );
  }

  return (
    <div className="p-1 space-y-0.5">
      {sessions.map((session) => (
        <SessionItem
          key={session.id}
          session={session}
          folders={folders}
          isActive={String(session.id) === activeSessionId}
          isEditing={editingId === String(session.id)}
          isDeleting={deleteConfirmId === String(session.id)}
          onSelect={() => onSelectSession(String(session.id))}
          onStartEdit={() => setEditingId(String(session.id))}
          onCancelEdit={() => setEditingId(null)}
          onUpdate={async (updates) => {
            await onUpdateSession(String(session.id), updates);
            setEditingId(null);
          }}
          onStartDelete={() => setDeleteConfirmId(String(session.id))}
          onCancelDelete={() => setDeleteConfirmId(null)}
          onDelete={async () => {
            await onDeleteSession(String(session.id));
            setDeleteConfirmId(null);
          }}
        />
      ))}
    </div>
  );
}
