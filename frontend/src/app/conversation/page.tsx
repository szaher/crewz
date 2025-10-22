'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { useConversationSessions } from '@/hooks/conversation/useConversationSessions';
import { useConversation } from '@/hooks/conversation/useConversation';
import SessionSidebar from '@/components/conversation/SessionSidebar';
import MessageArea from '@/components/conversation/MessageArea';
import EmptyState from '@/components/conversation/EmptyState';

export default function ConversationPage() {
  const router = useRouter();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [hyperparams, setHyperparams] = useState<{
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
    frequency_penalty?: number;
    presence_penalty?: number;
  }>({});

  const sessions = useConversationSessions();
  const conversation = useConversation({
    sessionId: activeSessionId,
    onStreamingStart: () => setSettingsOpen(false),
    hyperparams,
  });

  const activeSession = sessions.sessions.find(s => String(s.id) === activeSessionId);

  const handleCreateSession = async () => {
    try {
      // Create session with default title - will be auto-generated later
      const newSession = await sessions.createSession({
        title: 'New Conversation'
      });
      setActiveSessionId(String(newSession.id));
      router.push(`/conversation?session=${newSession.id}`);
    } catch (err) {
      console.error('Failed to create session:', err);
      throw err;
    }
  };

  const handleSelectSession = (sessionId: string) => {
    setActiveSessionId(sessionId);
    router.push(`/conversation?session=${sessionId}`);
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />

        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="px-6 pt-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
            <Breadcrumbs />
          </div>

          {/* Main Content */}
          <div className="flex-1 flex overflow-hidden">
            {/* Session Sidebar */}
            <SessionSidebar
              sessions={sessions.sessions}
              folders={sessions.folders}
              loading={sessions.loading}
              activeSessionId={activeSessionId}
              selectedFolderId={sessions.selectedFolderId}
              searchQuery={sessions.searchQuery}
              onSelectSession={handleSelectSession}
              onCreateSession={handleCreateSession}
              onUpdateSession={sessions.updateSession}
              onDeleteSession={sessions.deleteSession}
              onSetSearchQuery={sessions.setSearchQuery}
              onSetSelectedFolder={sessions.setSelectedFolderId}
              onCreateFolder={sessions.createFolder}
              onUpdateFolder={sessions.updateFolder}
              onDeleteFolder={sessions.deleteFolder}
            />

            {/* Message Area */}
            <div className="flex-1 min-w-0 flex flex-col">
              {activeSessionId && activeSession ? (
                <MessageArea
                  sessionId={activeSessionId}
                  sessionTitle={activeSession.title}
                  messages={conversation.messages}
                  streamingContent={conversation.streamingContent}
                  isThinking={conversation.isThinking}
                  loading={conversation.loading}
                  sending={conversation.sending}
                  streaming={conversation.streaming}
                  onSendMessage={conversation.sendMessage}
                  onCancelStreaming={conversation.cancelStreaming}
                  onOpenSettings={() => setSettingsOpen(true)}
                  settingsOpen={settingsOpen}
                  onCloseSettings={() => setSettingsOpen(false)}
                  hyperparams={hyperparams}
                  onUpdateHyperparams={setHyperparams}
                />
              ) : (
                <EmptyState
                  onNewSession={handleCreateSession}
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
