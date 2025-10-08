'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import ChatWindow from '@/components/chat/ChatWindow';
import { apiClient } from '@/lib/api-client';
import type { ChatSession, ChatSessionCreate, Crew } from '@/types/api';

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
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
      // API returns array directly, not wrapped in {sessions: [...]}
      const sessions = Array.isArray(response.data) ? response.data : [];
      setSessions(sessions);
      // Prefer session from URL if provided
      const sessionParam = searchParams?.get('session');
      const sessionIdFromUrl = sessionParam ? Number(sessionParam) : null;
      if (sessionIdFromUrl && sessions.some((s) => s.id === sessionIdFromUrl)) {
        setActiveSessionId(sessionIdFromUrl);
      } else if (sessions.length > 0) {
        setActiveSessionId(sessions[0].id);
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
      setSessions([]); // Set empty array on error
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
        const created = response.data.session ?? response.data;
        setSessions([...sessions, created]);
        setActiveSessionId(created.id);
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
      <div className="flex h-screen bg-gray-50">
        <Navigation />
        <div className="flex-1 overflow-auto">
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
            <QuickChat
              onCreateSession={() => setShowNewSessionForm(true)}
              onGoConfigure={() => router.push('/providers')}
            />
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
        </div>
      </div>
    </ProtectedRoute>
  );
}

function QuickChat({ onCreateSession, onGoConfigure }: { onCreateSession: () => void; onGoConfigure: () => void }) {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [hint, setHint] = useState<{ title: string; body: string; type: 'provider' | 'credentials' } | null>(null);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userText = input;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userText }]);
    setSending(true);
    try {
      const payload = {
        // messages: include prior chat for minimal context
        messages: [
          { role: 'system', content: 'You are a helpful assistant.' },
          ...messages.map((m) => ({ role: m.role, content: m.content })),
          { role: 'user', content: userText },
        ],
      };
      const res = await apiClient.post('/api/v1/chat/direct', payload);
      if (res.error) {
        const errMsg = res.error.toString();
        if (res.status === 400 && errMsg.includes('No default LLM provider configured')) {
          setHint({
            title: 'No default LLM provider',
            body: 'Create a chat session to choose a provider, or set a default provider in your configuration.',
            type: 'provider',
          });
        } else if (res.status === 400 && errMsg.toLowerCase().includes('credentials')) {
          setHint({
            title: 'LLM credentials missing/invalid',
            body: 'Update your LLM provider configuration with a valid API key.',
            type: 'credentials',
          });
        } else {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: `Sorry, I could not respond: ${errMsg}` },
          ]);
        }
        return;
      }
      const content: string = res?.data?.content ?? '';
      if (content) {
        setMessages((prev) => [...prev, { role: 'assistant', content }]);
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I could not respond right now.' },
      ]);
      // eslint-disable-next-line no-console
      console.error('Quick chat failed', e);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="border-b border-gray-200 px-6 py-4">
        <h2 className="text-lg font-semibold text-gray-900">Quick Chat</h2>
        <p className="text-sm text-gray-500">Chat without creating a saved session</p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
        {hint && (
          <div className="p-3 border border-amber-300 bg-amber-50 rounded-md">
            <div className="font-medium text-amber-900">{hint.title}</div>
            <div className="text-sm text-amber-800 mt-1">{hint.body}</div>
            <div className="mt-3 flex gap-2">
              <button
                onClick={onCreateSession}
                className="px-3 py-1.5 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700"
              >
                Create Session
              </button>
              <button
                onClick={onGoConfigure}
                className="px-3 py-1.5 text-sm rounded-md bg-gray-800 text-white hover:bg-gray-900"
              >
                Configure Provider
              </button>
            </div>
          </div>
        )}
        {messages.length === 0 ? (
          <p className="text-gray-500">Say hello to start chatting.</p>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
              <div className={`inline-block px-3 py-2 rounded-lg ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
                {m.content}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="border-t border-gray-200 px-6 py-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            rows={2}
            placeholder="Type your message..."
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 resize-none focus:border-blue-500 focus:outline-none focus:ring-blue-500"
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed self-end"
          >
            {sending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
