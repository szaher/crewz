'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import MessageList from './MessageList';
import type { ChatMessage } from '@/types/api';

interface ChatWindowProps {
  sessionId: number;
  sessionTitle: string;
  crewId?: number;
  onManageTools?: () => void;
  onStreamingStart?: () => void;
  onTitleUpdate?: (newTitle: string) => void;
}

export default function ChatWindow({ sessionId, sessionTitle, crewId, onManageTools, onStreamingStart, onTitleUpdate }: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userCount, setUserCount] = useState(0);
  const [provider, setProvider] = useState<any | null>(null);
  const [providerLoading, setProviderLoading] = useState(false);
  const [sessionTools, setSessionTools] = useState<any[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [receivedFirstToken, setReceivedFirstToken] = useState(false);
  const [draftContent, setDraftContent] = useState('');
  const [codeMode, setCodeMode] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editText, setEditText] = useState('');
  // Web audio (speech-to-text and text-to-speech)
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(false);
  const [autoSendVoice, setAutoSendVoice] = useState<boolean>(false);
  const [readAloud, setReadAloud] = useState<boolean>(false);
  const [recognizing, setRecognizing] = useState<boolean>(false);
  const [speechSupported, setSpeechSupported] = useState<boolean>(false);
  const [ttsSupported, setTtsSupported] = useState<boolean>(false);
  const recognitionRef = useRef<any>(null);
  const [showAudioSettings, setShowAudioSettings] = useState<boolean>(false);

  const lastUserMessage = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i]?.role === 'user') return messages[i];
    }
    return null;
  }, [messages]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const res = await apiClient.get(`/api/v1/chat/sessions/${sessionId}/messages`, { headers: {} });
      setLoading(false);
      if (res.data) {
        setMessages(res.data);
      }
    };
    void load();
  }, [sessionId]);

  // Streaming via HTTP SSE endpoint using fetch with Authorization header
  const startStream = async (userText: string, storeUser: boolean) => {
    const token = (apiClient as any).getToken ? (apiClient as any).getToken() : null;
    if (!token) {
      console.error('Missing auth token');
      return;
    }

    // Compute base URL similar to api-client dynamic logic
    const ENV_URL = process.env.NEXT_PUBLIC_API_URL as string | undefined;
    let baseUrl = 'http://localhost:8000';
    if (typeof window !== 'undefined') {
      const dyn = `${window.location.protocol}//${window.location.hostname}:8000`;
      if (ENV_URL && !/^(https?:\/\/)?(localhost|127\.0\.0\.1)(:|$)/i.test(ENV_URL)) {
        baseUrl = ENV_URL;
      } else {
        baseUrl = dyn;
      }
    } else if (ENV_URL) {
      baseUrl = ENV_URL;
    }

    // Build request URL with query params
    const params = new URLSearchParams({ user_message: userText, store_user: String(!!storeUser) });
    const url = `${baseUrl}/api/v1/chat/sessions/${sessionId}/generate/stream?${params.toString()}`;

    // Abort previous stream if running
    if (abortRef.current) {
      try { abortRef.current.abort(); } catch {}
    }
    const controller = new AbortController();
    abortRef.current = controller;

    onStreamingStart?.();
    setStreaming(true);
    setReceivedFirstToken(false);

    // Prepare a draft assistant message for streaming content
    const draftId = `draft-${Date.now()}`;
    let draftContentLocal = '';
    const upsertDraft = (content: string) => {
      const msg = {
        id: draftId,
        session_id: sessionId,
        role: 'assistant',
        content,
        created_at: new Date().toISOString(),
        metadata: {},
      } as ChatMessage;
      setMessages((prev) => {
        const idx = prev.findIndex((m) => m.id === draftId);
        if (idx >= 0) {
          const copy = [...prev];
          copy[idx] = msg;
          return copy;
        }
        return [...prev, msg];
      });
    };

    try {
      const res = await fetch(url, {
        method: 'GET',
        headers: {
          Accept: 'text/event-stream',
          Authorization: `Bearer ${token}`,
        },
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        console.error('Stream request failed', res.status, await res.text().catch(() => ''));
        setStreaming(false);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      // Emit initial thinking state until first token arrives
      // The server should send a status event first, but handle gracefully if not
      // Process stream
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events split by double newline
        let idx;
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const rawEvent = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);

          const lines = rawEvent.split('\n');
          let eventType: string | null = null;
          let dataStr = '';
          for (const line of lines) {
            if (line.startsWith('event:')) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              const d = line.slice(5).trim();
              // data lines may repeat; concatenate with newline as per SSE spec
              dataStr = dataStr ? dataStr + '\n' + d : d;
            }
          }

          if (!eventType) {
            continue;
          }

          try {
            const payload = dataStr ? JSON.parse(dataStr) : {};
            if (eventType === 'status') {
              // thinking
              setStreaming(true);
              setReceivedFirstToken(false);
            } else if (eventType === 'delta') {
              const token = payload.token || '';
              if (token) {
                draftContentLocal += token;
                upsertDraft(draftContentLocal);
                setReceivedFirstToken(true);
              }
            } else if (eventType === 'error') {
              console.error('Stream error event:', payload.error || payload.message || payload);
            } else if (eventType === 'done') {
              // Completed; refresh persisted messages shortly
              setStreaming(false);
              setTimeout(async () => {
                const res2 = await apiClient.get(`/api/v1/chat/sessions/${sessionId}/messages`);
                if (res2.data) {
                  setMessages(res2.data);
                }
              }, 300);
            }
          } catch (e) {
            // Ignore JSON parse errors for now
          }
        }
      }
    } catch (e) {
      if ((e as any)?.name !== 'AbortError') {
        console.error('Streaming request failed', e);
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  };

  // Detect Web Speech API support and restore audio prefs
  useEffect(() => {
    const rec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setSpeechSupported(!!rec);
    // No settings UI — minimalist mic only
  }, []);

  useEffect(() => { try { localStorage.setItem('chat_voice_enabled', String(voiceEnabled)); } catch {} }, [voiceEnabled]);
  useEffect(() => { try { localStorage.setItem('chat_voice_autosend', String(autoSendVoice)); } catch {} }, [autoSendVoice]);
  useEffect(() => { try { localStorage.setItem('chat_voice_readaloud', String(readAloud)); } catch {} }, [readAloud]);

  // Abort any active stream on unmount
  useEffect(() => {
    return () => {
      try { abortRef.current?.abort?.(); } catch {}
    };
  }, []);

  const startRecognition = () => {
    if (!speechSupported || recognizing || sending || streaming) return;
    const Rec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const rec = new Rec();
    recognitionRef.current = rec;
    rec.lang = 'en-US';
    rec.interimResults = true;
    rec.continuous = false;
    let finalText = '';
    setRecognizing(true);
    try {
      rec.onresult = (e: any) => {
        let interim = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const transcript = e.results[i][0].transcript;
          if (e.results[i].isFinal) finalText += transcript + ' ';
          else interim += transcript;
        }
        const merged = (finalText + ' ' + interim).trim();
        setInput(merged);
      };
      rec.onerror = () => { setRecognizing(false); };
      rec.onend = async () => {
        setRecognizing(false);
        recognitionRef.current = null;
        // Do not auto-send; user can review text and press Send
      };
      rec.start();
    } catch {
      setRecognizing(false);
    }
  };

  const stopRecognition = () => {
    try { recognitionRef.current?.stop?.(); } catch {}
    setRecognizing(false);
  };

  const speak = (text: string) => {
    if (!ttsSupported || !readAloud || !text) return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.0;
      u.pitch = 1.0;
      window.speechSynthesis.speak(u);
    } catch {}
  };
  const stopSpeak = () => { try { window.speechSynthesis.cancel(); } catch {} };

  // Load provider/model for this session
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setProviderLoading(true);
        const sessRes = await apiClient.get(`/api/v1/chat/sessions/${sessionId}`);
        const sess = sessRes?.data?.session ?? sessRes?.data ?? null;
        let prov: any | null = null;
        const provId = sess?.llm_provider_id ?? sess?.provider_id ?? sess?.metadata?.llm_provider_id;
        if (provId) {
          const pRes = await apiClient.get(`/api/v1/llm-providers/${provId}`);
          prov = pRes?.data?.provider ?? pRes?.data ?? null;
        } else {
          // try default provider as a fallback
          const defRes = await apiClient.get('/api/v1/llm-providers', { params: { is_default: true, page_size: 1 } });
          const list = defRes?.data?.providers ?? defRes?.data ?? [];
          prov = Array.isArray(list) ? list[0] : null;
        }
        if (!cancelled) setProvider(prov || null);
      } catch (e) {
        if (!cancelled) setProvider(null);
      } finally {
        if (!cancelled) setProviderLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [sessionId]);

  // Load tools configured for this session
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setToolsLoading(true);
        const [toolsRes, sessToolsRes] = await Promise.all([
          apiClient.get('/api/v1/tools'),
          apiClient.get(`/api/v1/chat/sessions/${sessionId}/tools`),
        ]);
        const allTools = toolsRes?.data?.tools ?? toolsRes?.data ?? [];
        const toolIds = (sessToolsRes?.data?.tool_ids ?? sessToolsRes?.data ?? []) as number[];
        const mapped = allTools.filter((t: any) => toolIds.includes(t.id));
        if (!cancelled) setSessionTools(mapped);
      } catch (e) {
        if (!cancelled) setSessionTools([]);
      } finally {
        if (!cancelled) setToolsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [sessionId]);

  // Legacy non-streaming handler - now redirects to streaming
  const handleSend = async () => {
    await handleSendStream();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSendStream();
    }
  };

  // Streaming send via HTTP SSE endpoint
  const handleSendStream = async () => {
    if (!input.trim()) return;

    onStreamingStart?.();
    setSending(true);
    const text = input;
    setInput('');

    try {
      // Optimistically add user message
      const localUser: ChatMessage = {
        id: `local-${Date.now()}`,
        session_id: sessionId,
        role: 'user',
        content: text,
        created_at: new Date().toISOString(),
        metadata: {},
      } as any;
      setMessages((prev) => [...prev, localUser]);
      // Start streaming from backend (store user = true)
      void startStream(text, true);
      setUserCount((c) => c + 1);
    } catch (e) {
      console.error('Failed to send message', e);
    } finally {
      setSending(false);
    }
  };

  // Retry last answer using last user message without storing duplicate user message
  const handleRetryLast = async () => {
    if (!lastUserMessage?.content || streaming || sending) return;
    await handleRetryMessage(lastUserMessage.content);
  };

  const handleRetryMessage = async (content: string) => {
    if (!content || streaming || sending) return;

    setSending(true);
    try {
      // Retry streaming without storing user again
      void startStream(content, false);
    } catch (e) {
      console.error('Failed to retry message', e);
    } finally {
      setSending(false);
    }
  };

  // After third user message, request a succinct session title and update
  useEffect(() => {
    if (userCount === 3) {
      (async () => {
        try {
          // fetch recent messages to give context
          const res = await apiClient.get(`/api/v1/chat/sessions/${sessionId}/messages`);
          const msgs = (res.data || []) as ChatMessage[];
          const mapped = msgs.slice(-12).map((m) => ({ role: m.role, content: m.content }));
          const sys = {
            role: 'system',
            content:
              'You are a helpful assistant. Given the conversation, propose a short, descriptive session title (max 6 words). Return ONLY the title text without quotes or punctuation.'
          } as any;
          const payload = { messages: [sys, ...mapped] };
          const titleRes = await apiClient.post('/api/v1/chat/direct', payload);
          const raw: string = titleRes?.data?.content || '';
          let candidate = raw.trim().replace(/^['"\s]+|[\.\!\?'"]+$/g, '');
          if (!candidate) return;
          // Update on server
          await apiClient.put(`/api/v1/chat/sessions/${sessionId}`, { title: candidate });
          // Notify parent to update local UI if provided
          onTitleUpdate?.(candidate);
        } catch (e) {
          // no-op if backend doesn't support
          console.warn('Failed to auto-title session', e);
        }
      })();
    }
  }, [userCount, sessionId, onTitleUpdate]);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-800 px-6 py-3">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-gray-900 truncate">
              {sessionTitle || `Chat Session #${sessionId}`}
            </h2>
            {crewId && (
              <p className="text-xs text-gray-500">Crew ID: {crewId}</p>
            )}
            {/* context row: provider + tools */}
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 text-xs bg-gray-100 dark:bg-gray-800/80 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-700 px-2 py-1 rounded-full">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="M4.93 19.07l2.83-2.83"/><path d="M16.24 7.76l2.83-2.83"/>
                </svg>
                {providerLoading ? 'Loading provider…' : provider ? `${provider.name || provider.provider_type || 'Provider'}${provider.model_name ? ` · ${provider.model_name}` : ''}` : 'Default Provider'}
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs bg-gray-100 dark:bg-gray-800/80 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-700 px-2 py-1 rounded-full">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d="M12 2l3 7h7l-5.5 4 2 7L12 17l-6.5 3 2-7L2 9h7z"/>
                </svg>
                {toolsLoading ? 'Loading tools…' : sessionTools.length ? `${sessionTools.length} tool${sessionTools.length>1?'s':''}` : 'No tools'}
              </span>
              {sessionTools.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {sessionTools.slice(0, 4).map((t) => (
                    <span key={t.id} className="inline-flex items-center text-[10px] bg-white dark:bg-gray-900/80 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 px-2 py-0.5 rounded-full">
                      {t.name}
                    </span>
                  ))}
                  {sessionTools.length > 4 && (
                    <span className="text-[10px] text-gray-500">+{sessionTools.length - 4} more</span>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="relative flex items-center gap-2 self-start">
            {onManageTools && (
              <button
                onClick={onManageTools}
                className="h-9 px-3 text-sm border rounded hover:bg-gray-100 whitespace-nowrap"
                title="Manage Tools"
                aria-label="Manage tools"
              >
                Manage Tools
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto chat-surface pb-40">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <>
            <MessageList
              messages={messages}
              onRetry={(m) => handleRetryMessage(m.content)}
              onEdit={(m) => { setEditMode(true); setEditText(m.content); }}
            />
            {streaming && !receivedFirstToken && (
              <div className="px-6 pb-4 animate-fadeIn">
                <div className="inline-flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-3 py-1 rounded-full shadow-sm" data-testid="typing-indicator">
                  <span className="inline-flex gap-1">
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </span>
                  <span className="font-medium">🤔 Thinking…</span>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Input */}
      <div className="px-4 py-4">
        <div
          className={`glow-card flex items-end gap-2 p-3 bg-white/80 dark:bg-[#2a2b32]/70 backdrop-blur-md border border-slate-200/70 dark:border-[#2a2b32]/70 rounded-2xl shadow-xl max-w-3xl mx-auto 
            ${recognizing ? 'ring-2 ring-red-500/40 recording' : 'focus-within:ring-2 focus-within:ring-blue-500/40'}`}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Message…"
            rows={1}
            disabled={sending || streaming}
            className="flex-1 bg-transparent text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-300 px-1 py-1 resize-none focus:outline-none max-h-40 min-h-[44px]"
          />
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => (recognizing ? stopRecognition() : startRecognition())}
              disabled={!speechSupported || sending || streaming}
              className={`p-2 rounded-lg border ${recognizing ? 'bg-red-50 border-red-300 text-red-700 animate-pulse' : 'bg-white dark:bg-[#40414f] border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200'} disabled:opacity-50`}
              title={speechSupported ? (recognizing ? 'Stop voice input' : 'Start voice input') : 'Voice input not supported'}
              aria-pressed={recognizing}
              aria-label="Microphone"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                <path d="M12 14a3 3 0 003-3V6a3 3 0 10-6 0v5a3 3 0 003 3z" />
                <path d="M19 11a1 1 0 10-2 0 5 5 0 11-10 0 1 1 0 10-2 0 7 7 0 0012 4.58V17a1 1 0 112 0v-1a1 1 0 10-2 0v.58A7 7 0 0019 11z" />
              </svg>
            </button>
            
            
            <button
              onClick={handleSendStream}
              disabled={!input.trim() || sending || streaming}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sending || streaming ? 'Sending…' : 'Send'}
            </button>
          </div>
        </div>

        {editMode && (
          <div className="mt-3 p-3 bg-white dark:bg-[#40414f] border border-slate-200 dark:border-[#2a2b32] rounded-xl">
            <label className="block text-xs text-gray-500 mb-1">Edit last message</label>
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 bg-transparent text-slate-900 dark:text-slate-100"
            />
            <div className="mt-2 flex items-center gap-2">
              <button
                onClick={async () => {
                  if (!editText.trim() || sending || streaming) return;
                  // Use streaming with edited text; store user so it persists as a new entry
                  setInput(editText);
                  setEditMode(false);
                  setEditText('');
                  await handleSendStream();
                }}
                disabled={!editText.trim() || sending || streaming}
                className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                Send Edited
              </button>
              <button
                onClick={() => { setEditMode(false); setEditText(''); }}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
