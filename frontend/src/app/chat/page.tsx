'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import ChatWindow from '@/components/chat/ChatWindow';
import { apiClient } from '@/lib/api-client';
import type { ChatSession, ChatSessionCreate, Crew } from '@/types/api';

export default function ChatPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [showNewSessionForm, setShowNewSessionForm] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [selectedCrewId, setSelectedCrewId] = useState<number | undefined>();
  const [crews, setCrews] = useState<Crew[]>([]);
  const [loadingCrews, setLoadingCrews] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (showNewSessionForm) {
      loadCrews();
    }
  }, [showNewSessionForm]);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/api/v1/chat/sessions');
      if (response.data) {
        setSessions(response.data.sessions || []);
        if (response.data.sessions.length > 0) {
          setActiveSessionId(response.data.sessions[0].id);
        }
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCrews = async () => {
    setLoadingCrews(true);
    try {
      const response = await apiClient.get('/api/v1/crews', {
        params: { page: 1, page_size: 100 }
      });
      if (response.data) {
        setCrews(response.data.crews || []);
      }
    } catch (error) {
      console.error('Failed to load crews:', error);
      setCrews([]);
    } finally {
      setLoadingCrews(false);
    }
  };

  const handleCreateSession = async () => {
    if (!newSessionName.trim()) return;

    try {
      const sessionData: ChatSessionCreate = {
        name: newSessionName,
        crew_id: selectedCrewId,
      };

      const response = await apiClient.post('/api/v1/chat/sessions', sessionData);
      if (response.data) {
        setSessions([...sessions, response.data.session]);
        setActiveSessionId(response.data.session.id);
        setShowNewSessionForm(false);
        setNewSessionName('');
        setSelectedCrewId(undefined);
      }
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return (
    <ProtectedRoute>
      <div className="h-screen flex flex-col">
        <div className="px-6 pt-4">
          <Breadcrumbs />
        </div>
        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar - Sessions List */}
          <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Chat Sessions</h2>
            </div>

          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : sessions.length === 0 ? (
              <div className="p-4 text-center text-sm text-gray-500">
                No chat sessions yet
              </div>
            ) : (
              <div className="p-2 space-y-1">
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => setActiveSessionId(session.id)}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                      activeSessionId === session.id
                        ? 'bg-blue-100 text-blue-900'
                        : 'hover:bg-gray-100 text-gray-700'
                    }`}
                  >
                    <p className="font-medium truncate">{session.name}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(session.created_at).toLocaleDateString()}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* New Session Button */}
          <div className="p-4 border-t border-gray-200">
            <button
              onClick={() => setShowNewSessionForm(true)}
              className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              New Session
            </button>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          {activeSessionId && activeSession ? (
            <ChatWindow
              sessionId={activeSessionId}
              crewId={activeSession.crew_id || undefined}
            />
          ) : (
            <div className="flex items-center justify-center h-full bg-white">
              <p className="text-gray-500">Select or create a chat session to begin</p>
            </div>
          )}
        </div>

        {/* New Session Modal */}
        {showNewSessionForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-96">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">New Chat Session</h3>

              <div className="space-y-4">
                <div>
                  <label htmlFor="session_name" className="block text-sm font-medium text-gray-700">
                    Session Name
                  </label>
                  <input
                    id="session_name"
                    type="text"
                    value={newSessionName}
                    onChange={(e) => setNewSessionName(e.target.value)}
                    placeholder="e.g., Research Discussion"
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label htmlFor="crew_id" className="block text-sm font-medium text-gray-700">
                    Crew (Optional)
                  </label>
                  <select
                    id="crew_id"
                    value={selectedCrewId || ''}
                    onChange={(e) => setSelectedCrewId(e.target.value ? Number(e.target.value) : undefined)}
                    disabled={loadingCrews}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    <option value="">
                      {loadingCrews ? 'Loading crews...' : 'No crew'}
                    </option>
                    {crews.map((crew) => (
                      <option key={crew.id} value={crew.id}>
                        {crew.name}
                      </option>
                    ))}
                  </select>
                  {crews.length === 0 && !loadingCrews && (
                    <p className="mt-1 text-xs text-gray-500">
                      No crews available. Create a crew first.
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowNewSessionForm(false);
                    setNewSessionName('');
                    setSelectedCrewId(undefined);
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateSession}
                  disabled={!newSessionName.trim()}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
