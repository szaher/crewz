'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { useUIStore } from '@/lib/store';
import ChatWindow from '@/components/chat/ChatWindow';
import { apiClient } from '@/lib/api-client';
import Markdown from '@/components/shared/Markdown';
import type { ChatSession } from '@/types/api';
import Modal from '@/components/shared/Modal';

// The content of the Chat page, extracted for reuse by /chat and /chat/[sessionId]
export default function ChatRoot() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  // Ensure sidebar is closed on entering chat
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const [newFolderInline, setNewFolderInline] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showNewSessionForm, setShowNewSessionForm] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [search, setSearch] = useState('');
  const [folders, setFolders] = useState<{id:number; name:string}[]>([]);
  const [selectedFolderId, setSelectedFolderId] = useState<number | null>(null);
  const [selectedProviderId, setSelectedProviderId] = useState<number | ''>('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [providers, setProviders] = useState<any[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [tools, setTools] = useState<any[]>([]);
  const [selectedToolIds, setSelectedToolIds] = useState<number[]>([]);
  const [loadingTools, setLoadingTools] = useState(false);
  const [newSessionFolderId, setNewSessionFolderId] = useState<number | ''>('');
  const [errorModal, setErrorModal] = useState<{open:boolean; title:string; message:string}>({open:false, title:'', message:''});
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState<string>('');
  const [deleteModal, setDeleteModal] = useState<{open:boolean; session: any | null}>({open:false, session: null});
  const [folderModal, setFolderModal] = useState<{open:boolean; mode:'create'|'rename'; folder: any | null; name: string}>({open:false, mode:'create', folder:null, name:''});
  const [folderDeleteModal, setFolderDeleteModal] = useState<{open:boolean; folder:any|null}>({open:false, folder:null});
  const [folderMenuFor, setFolderMenuFor] = useState<number | null>(null);
  const [manageTools, setManageTools] = useState<{open:boolean, toolIds?: number[]}>({open:false});
  const [manageToolsAll, setManageToolsAll] = useState<any[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sessionHyperparams, setSessionHyperparams] = useState<{temperature?: number; max_tokens?: number; top_p?: number; presence_penalty?: number; frequency_penalty?: number}>({});
  const [editingSystemPrompt, setEditingSystemPrompt] = useState<string>('');
  const [defaultSystemPrompt, setDefaultSystemPrompt] = useState<string>('');

  // Generate a random nice session name
  const generateNiceName = () => {
    const adjectives = ['Curious', 'Brisk', 'Calm', 'Clever', 'Bright', 'Daring', 'Eager', 'Gentle', 'Nimble', 'Bold', 'Lively', 'Sunny', 'Witty', 'Swift'];
    const nouns = ['Falcon', 'Panda', 'Otter', 'Sparrow', 'Fox', 'Willow', 'River', 'Comet', 'Quartz', 'Harbor', 'Maple', 'Sage', 'Nimbus', 'Cedar'];
    const adj = adjectives[Math.floor(Math.random() * adjectives.length)];
    const noun = nouns[Math.floor(Math.random() * nouns.length)];
    return `${adj} ${noun}`;
  };

  // Merge default + custom system prompts without duplication
  const mergeSystemPrompts = (base: string, custom: string) => {
    const b = (base || '').trim();
    const c = (custom || '').trim();
    if (!b && !c) return '';
    if (!b) return c;
    if (!c) return b;
    // Avoid duplicating when custom already contains base
    if (c.startsWith(b)) return c;
    return `${b}\n\n${c}`;
  };

  useEffect(() => {
    loadSessions();
    loadFolders();
    // Load tenant default system prompt
    (async () => {
      try {
        const res = await apiClient.get('/api/v1/tenant');
        const dsp = res?.data?.settings?.default_system_prompt || '';
        setDefaultSystemPrompt(dsp || '');
      } catch {}
    })();
    // Show sidebar briefly, then auto-close
    try {
      // Ensure sidebar is visible immediately
      if (!sidebarOpen) toggleSidebar();
      const t = setTimeout(() => {
        if (useUIStore.getState().sidebarOpen) toggleSidebar();
      }, 1500);
      return () => clearTimeout(t);
    } catch {}
  }, []);

  useEffect(() => {
    if (showNewSessionForm) {
      loadProviders();
      loadTools();
      // Prefill with default system prompt if empty
      if (!systemPrompt && defaultSystemPrompt) setSystemPrompt(defaultSystemPrompt);
      // Prefill session name with a random nice name
      if (!newSessionName) setNewSessionName(generateNiceName());
    }
  }, [showNewSessionForm, defaultSystemPrompt]);

  // When active session changes, fetch saved hyperparameters and current system prompt
  useEffect(() => {
    (async () => {
      if (!activeSessionId) return;
      try {
        // load hyperparams from backend
        const res = await apiClient.get(`/api/v1/chat/sessions/${activeSessionId}/params`);
        const hp = res?.data?.hyperparams || {};
        setSessionHyperparams(hp);
      } catch {
        setSessionHyperparams({});
      }
      try {
        // refresh session for up-to-date system prompt
        const sres = await apiClient.get(`/api/v1/chat/sessions/${activeSessionId}`);
        const sess = sres?.data?.session ?? sres?.data ?? null;
        setEditingSystemPrompt(sess?.system_prompt || '');
      } catch {
        // ignore
      }
    })();
  }, [activeSessionId]);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search.trim()) params.set('q', search.trim());
      if (selectedFolderId !== null) params.set('folder_id', String(selectedFolderId));
      const response = await apiClient.get(`/api/v1/chat/sessions${params.toString() ? `?${params.toString()}` : ''}`);
      let _sessions = Array.isArray(response.data) ? response.data : [];
      _sessions = _sessions.sort((a: any, b: any) => {
        const au = a.updated_at || a.created_at || '';
        const bu = b.updated_at || b.created_at || '';
        return new Date(bu).getTime() - new Date(au).getTime();
      });
      setSessions(_sessions);
      // Determine session from path or query param
      let preferredId: string | null = null;
      try {
        if (pathname && pathname.startsWith('/chat/')) {
          const seg = pathname.split('/').filter(Boolean)[1];
          if (seg) preferredId = seg;
        }
      } catch {}
      if (!preferredId) {
        const qp = searchParams?.get('session');
        if (qp) preferredId = qp;
      }
      if (preferredId && _sessions.some((s: any) => String(s.id) === preferredId)) {
        setActiveSessionId(preferredId);
      } else if (_sessions.length > 0) {
        const sid = String((_sessions[0] as any).id);
        setActiveSessionId(sid);
        router.replace(`/chat/${sid}`);
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const loadFolders = async () => {
    try {
      const res = await apiClient.get('/api/v1/chat/folders');
      setFolders(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      setFolders([]);
    }
  };

  const loadProviders = async () => {
    setLoadingProviders(true);
    try {
      const res = await apiClient.get('/api/v1/llm-providers?page=1&page_size=100&is_active=true');
      if (res.data) {
        setProviders(res.data.providers || []);
      }
    } catch (e) {
      console.error('Failed to load providers', e);
      setProviders([]);
    } finally {
      setLoadingProviders(false);
    }
  };

  const loadTools = async () => {
    setLoadingTools(true);
    try {
      const res = await apiClient.get('/api/v1/tools');
      if (res.data) {
        setTools(res.data.tools || []);
      }
    } catch (e) {
      console.error('Failed to load tools', e);
      setTools([]);
    } finally {
      setLoadingTools(false);
    }
  };

  const handleCreateSession = async () => {
    const effectiveName = newSessionName.trim() || `New Chat ${new Date().toLocaleString()}`;

    try {
      const payload: any = {
        title: effectiveName,
        system_prompt: mergeSystemPrompts(defaultSystemPrompt, systemPrompt),
      };
      if (selectedProviderId) payload.llm_provider_id = selectedProviderId;
      if (selectedToolIds.length) payload.tool_ids = selectedToolIds;
      if (newSessionFolderId) payload.folder_id = newSessionFolderId;

      const response = await apiClient.post('/api/v1/chat/sessions', payload);
      if (response.data) {
        const created = response.data.session ?? response.data;
        setSessions([...sessions, created]);
        const sid = String(created.id);
        setActiveSessionId(sid);
        router.push(`/chat/${sid}`);
        setShowNewSessionForm(false);
        setNewSessionName('');
        setSelectedProviderId('');
        setSystemPrompt('');
        setSelectedToolIds([]);
        setNewSessionFolderId('');
      } else if (response.error) {
        const msg = String(response.error);
        setErrorModal({
          open: true,
          title: 'Unable to Create Session',
          message: msg.includes('No default LLM provider') || msg.includes('Default provider')
            ? 'No LLM provider is configured. Please add a provider in Providers or select one when creating a session.'
            : msg,
        });
      }
    } catch (error) {
      console.error('Failed to create session:', error);
      setErrorModal({ open: true, title: 'Unable to Create Session', message: 'An unexpected error occurred while creating the session.' });
    }
  };

  const activeSession = sessions.find((s: any) => String(s.id) === activeSessionId);

  const autoCreateSession = async (title: string) => {
    try {
      const payload: any = { title };
      const response = await apiClient.post('/api/v1/chat/sessions', payload);
      if (response.data) {
        const created = response.data.session ?? response.data;
        setSessions((prev) => [...prev, created]);
        const sid = String(created.id);
        setActiveSessionId(sid);
        router.push(`/chat/${sid}`);
        setShowNewSessionForm(false);
        setNewSessionName('');
        setSelectedProviderId('');
        setSystemPrompt('');
        setSelectedToolIds([]);
      }
    } catch (e) {
      console.error('Auto session creation failed', e);
    }
  };

  // Load tools for Manage Tools modal
  useEffect(() => {
    if (!manageTools.open || !activeSessionId) return;
    (async () => {
      const [toolsRes, sessRes] = await Promise.all([
        apiClient.get('/api/v1/tools'),
        apiClient.get(`/api/v1/chat/sessions/${activeSessionId}/tools`),
      ]);
      setManageToolsAll(toolsRes.data?.tools || []);
      setManageTools({ open:true, toolIds: (sessRes.data?.tool_ids || []) as number[] });
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manageTools.open, activeSessionId]);

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="px-6 pt-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
            <Breadcrumbs />
          </div>
          <div className="flex-1 flex overflow-hidden">
            {/* Sidebar - Sessions List */}
            <div className="w-72 flex-shrink-0 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col overflow-y-auto">
              <div className="p-4 border-b border-gray-200 dark:border-gray-800">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Chat Sessions</h2>
              </div>

              <div className="p-3 border-b border-gray-200 dark:border-gray-800">
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') void loadSessions(); }}
                  placeholder="Search sessions..."
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                />
              </div>

              <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-800">
                <div className="group flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Folders</span>
                  <button
                    className="p-1 border rounded hover:bg-gray-100 dark:hover:bg-gray-800 dark:border-gray-700 opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-label="New folder"
                    title="New folder"
                    onClick={() => { setNewFolderInline(true); setNewFolderName(''); }}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                      <path d="M12 4.5a.75.75 0 01.75.75V11h5.75a.75.75 0 010 1.5H12.75v5.75a.75.75 0 01-1.5 0V12.5H5.5a.75.75 0 010-1.5h5.75V5.25A.75.75 0 0112 4.5z" />
                    </svg>
                  </button>
                </div>
                <div className="space-y-1">
              {newFolderInline && (
                <div className="flex items-center gap-2 p-1">
                  <input
                    autoFocus
                    value={newFolderName}
                    onChange={(e) => setNewFolderName(e.target.value)}
                    onKeyDown={async (e) => {
                      if (e.key === 'Enter') {
                        const name = newFolderName.trim();
                        if (!name) return;
                        const res = await apiClient.post('/api/v1/chat/folders', { name });
                        if (!res.error) {
                          setNewFolderInline(false);
                          setNewFolderName('');
                          await loadFolders();
                        }
                      } else if (e.key === 'Escape') {
                        setNewFolderInline(false); setNewFolderName('');
                      }
                    }}
                    placeholder="Folder name"
                    className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-700 rounded text-sm bg-white dark:bg-gray-900"
                  />
                  <button
                    className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                    onClick={async () => {
                      const name = newFolderName.trim();
                      if (!name) return;
                      const res = await apiClient.post('/api/v1/chat/folders', { name });
                      if (!res.error) {
                        setNewFolderInline(false);
                        setNewFolderName('');
                        await loadFolders();
                      }
                    }}
                  >
                    Save
                  </button>
                  <button
                    className="px-2 py-1 text-xs border rounded"
                    onClick={() => { setNewFolderInline(false); setNewFolderName(''); }}
                  >
                    Cancel
                  </button>
                </div>
              )}
              <button
                onClick={() => { setSelectedFolderId(null); void loadSessions(); }}
                className={`w-full text-left px-3 py-1.5 rounded ${selectedFolderId===null ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}`}
              >All</button>
              {folders.map((f) => (
                <div key={f.id} className="group flex items-center gap-1">
                  <button
                    onClick={() => { setSelectedFolderId(f.id); void loadSessions(); }}
                    className={`flex-1 text-left px-3 py-1.5 rounded ${selectedFolderId===f.id ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}`}
                  >{f.name}</button>
                  <button
                    className="p-1 border rounded hover:bg-gray-100 dark:hover:bg-gray-800 dark:border-gray-700 opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-label="Rename folder"
                    title="Rename"
                    onClick={() => setFolderModal({ open:true, mode:'rename', folder:f, name:f.name })}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                      <path d="M21.731 2.269a2.625 2.625 0 00-3.714 0l-1.157 1.157 3.714 3.714 1.157-1.157a2.625 2.625 0 000-3.714z" />
                      <path d="M3 17.25V21h3.75L19.5 8.25l-3.75-3.75L3 17.25z" />
                    </svg>
                  </button>
                  <button
                    className="p-1 border rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:border-gray-700 opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-label="Delete folder"
                    title="Delete"
                    onClick={() => setFolderDeleteModal({ open:true, folder:f })}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                      <path d="M9 3a1 1 0 00-1 1v1H4.75a.75.75 0 000 1.5h14.5a.75.75 0 000-1.5H16V4a1 1 0 00-1-1H9z" />
                      <path fillRule="evenodd" d="M6.5 8.25a.75.75 0 01.75-.75h9.5a.75.75 0 01.75.75v10a2 2 0 01-2 2h-7a2 2 0 01-2-2v-10zM10 10a.75.75 0 01.75.75v7a.75.75 0 01-1.5 0v-7A.75.75 0 0110 10zm4 0a.75.75 0 01.75.75v7a.75.75 0 01-1.5 0v-7A.75.75 0 0114 10z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>
              ))}
              </div>
              </div>
            

          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : sessions.length === 0 ? (
                  <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
                    No chat sessions yet
                  </div>
                ) : (
                  <div className="p-1 space-y-0.5">
                    {sessions.map((session: any) => (
                  <div key={session.id} className={`group rounded-md px-2 py-1 text-sm ${activeSessionId===String(session.id) ? 'bg-blue-100 text-blue-900 dark:bg-blue-900/30 dark:text-blue-300' : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-200'}`}>
                    <div className="flex items-center justify-between">
                      {editingSessionId === String(session.id) ? (
                        <div className="flex items-center gap-2 flex-1">
                          <input
                            autoFocus
                            value={editingTitle}
                            onChange={(e) => setEditingTitle(e.target.value)}
                            className="flex-1 px-2 py-1 border border-gray-300 rounded"
                          />
                          <button
                            className="text-xs px-2 py-1 border rounded bg-blue-600 text-white hover:bg-blue-700"
                            onClick={async () => {
                              const title = editingTitle.trim();
                              if (!title) { setEditingSessionId(null); return; }
                              const res = await apiClient.put(`/api/v1/chat/sessions/${session.id}`, { title });
                              setEditingSessionId(null);
                              if (!res.error) await loadSessions();
                            }}
                          >
                            Save
                          </button>
                          <button
                            className="text-xs px-2 py-1 border rounded"
                            onClick={() => { setEditingSessionId(null); setEditingTitle(''); }}
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <>
                          <button className="font-medium truncate text-left flex-1" onClick={() => {
                            const sid = String(session.id);
                            setActiveSessionId(sid);
                            router.push(`/chat/${sid}`);
                          }}>
                            {session.title || 'Untitled'}
                          </button>
                          <div className="flex items-center gap-1 relative opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              className="p-1 border rounded hover:bg-gray-100 dark:hover:bg-gray-800 dark:border-gray-700"
                              onClick={() => { setEditingSessionId(String(session.id)); setEditingTitle(session.title || ''); }}
                              aria-label="Rename session"
                              title="Rename"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                                <path d="M21.731 2.269a2.625 2.625 0 00-3.714 0l-1.157 1.157 3.714 3.714 1.157-1.157a2.625 2.625 0 000-3.714z" />
                                <path d="M3 17.25V21h3.75L19.5 8.25l-3.75-3.75L3 17.25z" />
                              </svg>
                              <span className="sr-only">Rename</span>
                            </button>
                            <button
                              className="p-1 border rounded hover:bg-gray-100 dark:hover:bg-gray-800 dark:border-gray-700"
                              aria-label="Move to folder"
                              title={session.folder_id ? `Folder: ${(folders.find((f)=>f.id===session.folder_id)?.name) || 'Unknown'}` : 'Move to folder'}
                              onClick={() => setFolderMenuFor(folderMenuFor === session.id ? null : session.id)}
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                                <path d="M2.25 6.75A2.25 2.25 0 014.5 4.5H7.5l1.5 1.5H19.5A2.25 2.25 0 0121.75 8.25v7.5A2.25 2.25 0 0119.5 18H4.5A2.25 2.25 0 012.25 15.75V6.75z" />
                              </svg>
                            </button>
                            {folderMenuFor === session.id && (
                              <div className="absolute z-10 right-0 top-6 w-48 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded shadow-md p-1">
                                <button
                                  className={`block w-full text-left px-3 py-1.5 rounded ${session.folder_id==null ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}`}
                                  onClick={async () => {
                                    const res = await apiClient.put(`/api/v1/chat/sessions/${session.id}`, { folder_id: null });
                                    if (!res.error) await loadSessions();
                                    setFolderMenuFor(null);
                                  }}
                                >
                                  No Folder
                                </button>
                                {folders.map((f) => (
                                  <button
                                    key={f.id}
                                    className={`block w-full text-left px-3 py-1.5 rounded ${session.folder_id===f.id ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}`}
                                    onClick={async () => {
                                      const res = await apiClient.put(`/api/v1/chat/sessions/${session.id}`, { folder_id: f.id });
                                      if (!res.error) await loadSessions();
                                      setFolderMenuFor(null);
                                    }}
                                  >
                                    {f.name}
                                  </button>
                                ))}
                              </div>
                            )}
                            <button
                              className="p-1 border rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:border-gray-700"
                              onClick={() => setDeleteModal({ open: true, session })}
                              aria-label="Delete session"
                              title="Delete"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                                <path d="M9 3a1 1 0 00-1 1v1H4.75a.75.75 0 000 1.5h14.5a.75.75 0 000-1.5H16V4a1 1 0 00-1-1H9z" />
                                <path fillRule="evenodd" d="M6.5 8.25a.75.75 0 01.75-.75h9.5a.75.75 0 01.75.75v10a2 2 0 01-2 2h-7a2 2 0 01-2-2v-10zM10 10a.75.75 0 01.75.75v7a.75.75 0 01-1.5 0v-7A.75.75 0 0110 10zm4 0a.75.75 0 01.75.75v7a.75.75 0 01-1.5 0v-7A.75.75 0 0114 10z" clipRule="evenodd" />
                              </svg>
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            </div>
            </div>

            <div className="flex-1 min-w-0 flex flex-col">
              {activeSessionId && activeSession ? (
                <div className="flex-1 flex overflow-hidden relative">
                  <div className="w-full h-full flex flex-col bg-white dark:bg-gray-900">
                    <ChatWindow
                  sessionId={activeSessionId as string}
                  sessionTitle={(activeSession as any).title || 'Untitled'}
                  crewId={activeSession.crew_id || undefined}
                  onManageTools={() => setSettingsOpen(true)}
                  onStreamingStart={() => setSettingsOpen(false)}
                  onTitleUpdate={(newTitle) => {
                    setSessions((prev) => prev.map((s: any) => String(s.id) === activeSessionId ? { ...s, title: newTitle } : s));
                  }}
                  onNewSession={() => { setNewSessionName(generateNiceName()); setShowNewSessionForm(true); }}
                  hyperparams={sessionHyperparams}
                />
              </div>
              {/* Right Settings Drawer */}
              {settingsOpen && (
                <div className="absolute right-0 top-0 h-full w-80 bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 shadow-lg z-30 flex flex-col">
                  <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
                    <div className="font-semibold">Session Settings</div>
                    <button className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800" onClick={() => setSettingsOpen(false)} aria-label="Close settings">✕</button>
                  </div>
                  <div className="flex-1 overflow-y-auto p-3 space-y-4">
                    <div>
                      <div className="text-sm font-medium mb-2">Allowed Tools</div>
                      <div className="max-h-64 overflow-y-auto border rounded">
                        {manageToolsAll.length === 0 ? (
                          <div className="p-3 text-sm text-gray-500">No tools available</div>
                        ) : (
                          manageToolsAll.map((t: any) => (
                            <label key={t.id} className="flex items-center gap-2 p-2 border-b last:border-b-0">
                              <input
                                type="checkbox"
                                checked={(manageTools.toolIds || []).includes(t.id)}
                                onChange={(e) => {
                                  const selected = new Set(manageTools.toolIds || []);
                                  if (e.target.checked) selected.add(t.id); else selected.delete(t.id);
                                  setManageTools({ open:true, toolIds: Array.from(selected) });
                                }}
                              />
                              <div>
                                <div className="text-sm font-medium">{t.name} <span className="text-xs text-gray-500">({t.tool_type})</span></div>
                                <div className="text-xs text-gray-500">{t.description}</div>
                              </div>
                            </label>
                          ))
                        )}
                      </div>
                      <div className="mt-2 flex justify-end gap-2">
                        <button onClick={() => setSettingsOpen(false)} className="px-3 py-1.5 border rounded">Close</button>
                        <button
                          onClick={async () => {
                            if (!activeSessionId) return;
                            const res = await apiClient.put(`/api/v1/chat/sessions/${activeSessionId}/tools`, { tool_ids: manageTools.toolIds || [] });
                            if (!res.error) setSettingsOpen(false);
                          }}
                          className="px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                          Save
                        </button>
                      </div>
                    </div>
                    {/* Model Hyperparameters */}
                    <div>
                      <div className="mt-4 text-sm font-medium">Model Parameters</div>
                      <div className="mt-2 space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          <label className="text-xs text-gray-600">Temperature
                            <input type="number" step="0.1" min={0} max={2}
                              value={sessionHyperparams.temperature ?? ''}
                              onChange={(e)=>setSessionHyperparams((p)=>({...p, temperature: e.target.value===''? undefined : Number(e.target.value)}))}
                              className="mt-1 w-full px-2 py-1 border rounded"/>
                          </label>
                          <label className="text-xs text-gray-600">Max Tokens
                            <input type="number" min={1}
                              value={sessionHyperparams.max_tokens ?? ''}
                              onChange={(e)=>setSessionHyperparams((p)=>({...p, max_tokens: e.target.value===''? undefined : Number(e.target.value)}))}
                              className="mt-1 w-full px-2 py-1 border rounded"/>
                          </label>
                          <label className="text-xs text-gray-600">Top P
                            <input type="number" step="0.05" min={0} max={1}
                              value={sessionHyperparams.top_p ?? ''}
                              onChange={(e)=>setSessionHyperparams((p)=>({...p, top_p: e.target.value===''? undefined : Number(e.target.value)}))}
                              className="mt-1 w-full px-2 py-1 border rounded"/>
                          </label>
                          <label className="text-xs text-gray-600">Presence Penalty
                            <input type="number" step="0.1" min={-2} max={2}
                              value={sessionHyperparams.presence_penalty ?? ''}
                              onChange={(e)=>setSessionHyperparams((p)=>({...p, presence_penalty: e.target.value===''? undefined : Number(e.target.value)}))}
                              className="mt-1 w-full px-2 py-1 border rounded"/>
                          </label>
                          <label className="text-xs text-gray-600">Frequency Penalty
                            <input type="number" step="0.1" min={-2} max={2}
                              value={sessionHyperparams.frequency_penalty ?? ''}
                              onChange={(e)=>setSessionHyperparams((p)=>({...p, frequency_penalty: e.target.value===''? undefined : Number(e.target.value)}))}
                              className="mt-1 w-full px-2 py-1 border rounded"/>
                          </label>
                        </div>
                        <p className="text-[11px] text-gray-500">These parameters apply to this session's responses.</p>
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={async ()=>{
                              if (!activeSessionId) return;
                              const body: any = { ...sessionHyperparams };
                              Object.keys(body).forEach((k)=>{ if (body[k] === '' || body[k] == null) delete body[k]; });
                              await apiClient.put(`/api/v1/chat/sessions/${activeSessionId}/params`, body);
                            }}
                            className="px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700"
                          >
                            Save Parameters
                          </button>
                        </div>
                      </div>
                    </div>
                    {/* System Prompt editor */}
                    <div className="mt-4">
                      <div className="text-sm font-medium mb-1">System Prompt</div>
                      <textarea
                        value={editingSystemPrompt}
                        onChange={(e)=>setEditingSystemPrompt(e.target.value)}
                        rows={5}
                        className="w-full px-2 py-1 border rounded"
                      />
                      <div className="mt-2 flex justify-end gap-2">
                        <button onClick={()=>setSettingsOpen(false)} className="px-3 py-1.5 border rounded">Close</button>
                        <button
                          onClick={async ()=>{
                            if (!activeSessionId) return;
                            const merged = mergeSystemPrompts(defaultSystemPrompt, editingSystemPrompt);
                            await apiClient.put(`/api/v1/chat/sessions/${activeSessionId}`, { system_prompt: merged });
                            setSettingsOpen(false);
                          }}
                          className="px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >Save Prompt</button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
              ) : (
                <QuickChat
                  onCreateSession={() => setShowNewSessionForm(true)}
                  onGoConfigure={() => router.push('/providers')}
                  onAutoCreateSession={autoCreateSession}
                />
              )}
            </div>
          </div>
        </div>

      {/* New Session Modal */}
        {showNewSessionForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-96">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">New Chat Session</h3>

              <div className="space-y-4">
                {providers.length === 0 && (
                  <div className="p-3 rounded border border-amber-300 bg-amber-50 text-amber-900 text-sm">
                    No active LLM provider found. You can still create a session, but chatting requires a configured provider. Go to Providers to add one.
                  </div>
                )}
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
                  <label htmlFor="provider_id" className="block text-sm font-medium text-gray-700">
                    Provider
                  </label>
                  <select
                    id="provider_id"
                    value={selectedProviderId}
                    onChange={(e) => setSelectedProviderId(e.target.value ? Number(e.target.value) : '')}
                    disabled={loadingProviders}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    <option value="">Use default provider</option>
                    {providers.map((p: any) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.provider_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="folder_id" className="block text-sm font-medium text-gray-700">Folder (Optional)</label>
                  <select
                    id="folder_id"
                    value={newSessionFolderId}
                    onChange={(e) => setNewSessionFolderId(e.target.value ? Number(e.target.value) : '')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                  >
                    <option value="">None</option>
                    {folders.map((f) => (
                      <option key={f.id} value={f.id}>{f.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="system_prompt" className="block text-sm font-medium text-gray-700">
                    System Prompt (Optional)
                  </label>
                  <textarea
                    id="system_prompt"
                    rows={3}
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                  />
                  {defaultSystemPrompt && !systemPrompt && (
                    <div className="mt-1 text-xs text-gray-500">Default from admin settings applied if left blank.</div>
                  )}
                  <div className="mt-2">
                    <button
                      type="button"
                      onClick={() => {
                        const selected = tools.filter((t: any) => selectedToolIds.includes(t.id));
                        const toolLines = selected.map((t: any) => `- ${t.name}: ${t.description}`);
                        const suggestion = `You can use the following tools when helpful. Return clearly labeled results and cite which tool was used.\nTools:\n${toolLines.join('\n')}`;
                        setSystemPrompt(suggestion);
                      }}
                      disabled={selectedToolIds.length === 0}
                      className="text-xs px-2 py-1 border rounded-md disabled:opacity-50"
                    >
                      Suggest prompt from selected tools
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Tools (Optional)</label>
                  <div className="mt-1 max-h-40 overflow-y-auto border rounded-md p-2">
                    {loadingTools ? (
                      <div className="text-sm text-gray-500">Loading tools...</div>
                    ) : tools.length === 0 ? (
                      <div className="text-sm text-gray-500">No tools available</div>
                    ) : (
                      tools.map((t: any) => (
                        <label key={t.id} className="flex items-center gap-2 py-1 text-sm">
                          <input
                            type="checkbox"
                            checked={selectedToolIds.includes(t.id)}
                            onChange={(e) => {
                              setSelectedToolIds((prev) =>
                                e.target.checked ? [...prev, t.id] : prev.filter((id) => id !== t.id)
                              );
                            }}
                          />
                          <span className="truncate"><span className="font-medium">{t.name}</span> – <span className="text-gray-500">{t.description}</span></span>
                        </label>
                      ))
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowNewSessionForm(false);
                    setNewSessionName('');
                    setSelectedProviderId('');
                    setSystemPrompt('');
                    setSelectedToolIds([]);
                    setNewSessionFolderId('');
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

      {errorModal.open && (
        <Modal isOpen={errorModal.open} onClose={() => setErrorModal({ ...errorModal, open: false })} title={errorModal.title} size="sm">
          <div className="text-sm text-gray-800 whitespace-pre-wrap">{errorModal.message}</div>
          <div className="mt-4 flex justify-end">
            <button onClick={() => setErrorModal({ ...errorModal, open: false })} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">OK</button>
          </div>
        </Modal>
      )}
      {folderModal.open && (
        <Modal
          isOpen={folderModal.open}
          onClose={() => setFolderModal({ open:false, mode:'create', folder:null, name:'' })}
          title={folderModal.mode === 'create' ? 'New Folder' : 'Rename Folder'}
          size="sm"
        >
          <div className="space-y-3">
            <input
              autoFocus
              value={folderModal.name}
              onChange={(e) => setFolderModal({ ...folderModal, name: e.target.value })}
              placeholder="Folder name"
              className="w-full px-3 py-2 border border-gray-300 rounded"
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setFolderModal({ open:false, mode:'create', folder:null, name:'' })} className="px-4 py-2 border rounded">Cancel</button>
              <button
                onClick={async () => {
                  const name = folderModal.name.trim();
                  if (!name) return;
                  if (folderModal.mode === 'create') {
                    const res = await apiClient.post('/api/v1/chat/folders', { name });
                    if (!res.error) await loadFolders();
                  } else if (folderModal.folder) {
                    const res = await apiClient.put(`/api/v1/chat/folders/${folderModal.folder.id}`, { name });
                    if (!res.error) await loadFolders();
                  }
                  setFolderModal({ open:false, mode:'create', folder:null, name:'' });
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Save
              </button>
            </div>
          </div>
        </Modal>
      )}
      {folderDeleteModal.open && (
        <Modal
          isOpen={folderDeleteModal.open}
          onClose={() => setFolderDeleteModal({ open:false, folder:null })}
          title="Delete Folder"
          size="sm"
        >
          <div className="text-sm text-gray-800">Are you sure you want to delete the folder "{folderDeleteModal.folder?.name}"? Sessions inside will be moved to No Folder.</div>
          <div className="mt-4 flex justify-end gap-2">
            <button onClick={() => setFolderDeleteModal({ open:false, folder:null })} className="px-4 py-2 border rounded">Cancel</button>
            <button
              onClick={async () => {
                if (!folderDeleteModal.folder) return;
                const id = folderDeleteModal.folder.id;
                const res = await apiClient.delete(`/api/v1/chat/folders/${id}`);
                if (!res.error) await loadFolders();
                setFolderDeleteModal({ open:false, folder:null });
              }}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        </Modal>
      )}
      {deleteModal.open && (
        <Modal isOpen={deleteModal.open} onClose={() => setDeleteModal({ open:false, session:null })} title="Delete Session" size="sm">
          <div className="text-sm text-gray-800">Are you sure you want to delete the session &quot;{deleteModal.session?.title || 'Untitled'}&quot;?</div>
          <div className="mt-4 flex justify-end gap-2">
            <button onClick={() => setDeleteModal({ open:false, session:null })} className="px-4 py-2 border rounded">Cancel</button>
            <button
              onClick={async () => {
                if (!deleteModal.session) return;
                const id = String(deleteModal.session.id);
                const res = await apiClient.delete(`/api/v1/chat/sessions/${id}`);
                setDeleteModal({ open:false, session:null });
                if (!res.error) {
                  if (activeSessionId === id) setActiveSessionId(null);
                  await loadSessions();
                }
              }}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        </Modal>
      )}
      </div>
    </ProtectedRoute>
  );
}

function QuickChat({ onCreateSession, onGoConfigure, onAutoCreateSession }: { onCreateSession: () => void; onGoConfigure: () => void; onAutoCreateSession: (title: string) => Promise<void> }) {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [hint, setHint] = useState<{ title: string; body: string; type: 'provider' | 'credentials' } | null>(null);
  const [userMsgCount, setUserMsgCount] = useState(0);
  const [err, setErr] = useState<{open:boolean; title:string; message:string}>({open:false, title:'', message:''});

  const handleSend = async () => {
    if (!input.trim()) return;
    const userText = input;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userText }]);
    setSending(true);
    try {
      const payload = {
        messages: [
          {
            role: 'system',
            content:
              'You are a helpful assistant. Always respond in GitHub-Flavored Markdown. Use fenced code blocks with proper language tags (e.g., ```json, ```yaml, ```python, ```javascript) when outputting code, JSON, or YAML. Be concise and structured.'
          },
          ...messages.map((m) => ({ role: m.role, content: m.content })),
          { role: 'user', content: userText },
        ],
      };
      const res = await apiClient.post('/api/v1/chat/direct', payload);
      if (res.data) {
        setMessages((prev) => [...prev, { role: 'assistant', content: res.data.content }]);
        setUserMsgCount((n)=>n+1);
        // Encourage session creation after a few messages
        if (userMsgCount === 1) {
          setHint({
            title: 'Save this conversation?',
            body: 'Create a chat session to choose a provider, or set a default provider in your configuration.',
            type: 'provider',
          });
        }
        if (userMsgCount === 2) {
          try {
            await onAutoCreateSession(messages[0]?.content?.slice(0, 30) || 'New Chat');
          } catch {}
        }
      } else if (res.error) {
        const msg = String(res.error || '');
        // Friendly hints
        if (/No default LLM provider/i.test(msg)) {
          setHint({
            title: 'No provider configured',
            body: 'Create a chat session to choose a provider, or set a default provider in your configuration.',
            type: 'provider',
          });
        } else if (/credentials/i.test(msg)) {
          setHint({
            title: 'Provider credentials missing',
            body: 'Add your provider API key in Providers, then try again.',
            type: 'credentials',
          });
        }
        setErr({ open:true, title: 'Unable to Chat', message: msg });
      }
    } catch (e: any) {
      setErr({ open:true, title: 'Unable to Chat', message: e?.message || 'Unknown error' });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 dark:text-gray-400">
              <div className="text-lg font-medium mb-2">Quick Chat</div>
              <p className="text-sm">Chat without creating a saved session</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((m, idx) => (
                <div key={idx} className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                  <div className="text-xs text-gray-500 mb-1">{m.role === 'user' ? 'You' : 'Assistant'}</div>
                  <Markdown content={m.content} />
                </div>
              ))}
            </div>
          )}

          {hint && (
            <div className="mt-2 rounded-md border p-3 bg-amber-50 border-amber-200 text-amber-900 text-sm">
              <div className="font-medium">{hint.title}</div>
              <div className="mt-1">{hint.body}</div>
              <div className="mt-2 flex gap-2">
                {hint.type === 'provider' ? (
                  <>
                    <button onClick={onCreateSession} className="px-3 py-1.5 border rounded bg-white hover:bg-gray-50">Create Session</button>
                    <button onClick={onGoConfigure} className="px-3 py-1.5 border rounded bg-white hover:bg-gray-50">Go to Providers</button>
                  </>
                ) : (
                  <button onClick={onGoConfigure} className="px-3 py-1.5 border rounded bg-white hover:bg-gray-50">Configure Providers</button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-gray-200 dark:border-gray-800 px-6 py-4">
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
            className="flex-1 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 px-3 py-2 resize-none focus:border-blue-500 focus:outline-none focus:ring-blue-500"
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
      {err.open && (
        <Modal isOpen={err.open} onClose={() => setErr({...err, open:false})} title={err.title} size="sm">
          <div className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{err.message}</div>
          <div className="mt-4 flex justify-end">
            <button onClick={() => setErr({...err, open:false})} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">OK</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
