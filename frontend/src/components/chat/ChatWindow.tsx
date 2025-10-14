'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { promptApi } from '@/lib/api/prompts';
import MessageList from './MessageList';
import type { ChatMessage } from '@/types/api';
import type { PromptTemplate, PromptVariable } from '@/lib/store';

interface ChatWindowProps {
  sessionId: string;
  sessionTitle: string;
  crewId?: string;
  onManageTools?: () => void;
  onStreamingStart?: () => void;
  onTitleUpdate?: (newTitle: string) => void;
  onNewSession?: () => void;
  // Optional model parameters to apply during streaming
  hyperparams?: {
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
    frequency_penalty?: number;
    presence_penalty?: number;
  };
}

export default function ChatWindow({ sessionId, sessionTitle, crewId, onManageTools, onStreamingStart, onTitleUpdate, onNewSession, hyperparams }: ChatWindowProps) {
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
  // Slash command support
  const [commands, setCommands] = useState<Array<{ slug: string; name: string; description?: string; usage?: string }>>([]);
  const [showCommandList, setShowCommandList] = useState(false);
  const [commandQuery, setCommandQuery] = useState('');
  const [cmdIndex, setCmdIndex] = useState(0);
  // Prompt variable modal state
  const [showPromptVars, setShowPromptVars] = useState(false);
  const [promptForCommand, setPromptForCommand] = useState<PromptTemplate | null>(null);
  const [promptVarValues, setPromptVarValues] = useState<Record<string, any>>({});
  const [promptVarErrors, setPromptVarErrors] = useState<Record<string, string>>({});
  const [previewContent, setPreviewContent] = useState<string>('');
  // Web audio (speech-to-text and text-to-speech)
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(false);
  const [autoSendVoice, setAutoSendVoice] = useState<boolean>(false);
  const [readAloud, setReadAloud] = useState<boolean>(false);
  const [recognizing, setRecognizing] = useState<boolean>(false);
  const [speechSupported, setSpeechSupported] = useState<boolean>(false);
  const [ttsSupported, setTtsSupported] = useState<boolean>(false);
  const recognitionRef = useRef<any>(null);
  const [showAudioSettings, setShowAudioSettings] = useState<boolean>(false);
  const [voiceLang, setVoiceLang] = useState<string>('en-US');

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

  // Load prompt commands for slash suggestions
  useEffect(() => {
    (async () => {
      try {
        const res = await promptApi.listCommands();
        const data = (res.data as any) || {};
        const list = Array.isArray(data) ? data : (data.commands || []);
        setCommands(list);
      } catch (e) {
        // ignore
        setCommands([]);
      }
    })();
  }, []);

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
    // Include hyperparameters if provided
    if (hyperparams) {
      if (hyperparams.temperature != null) params.set('temperature', String(hyperparams.temperature));
      if (hyperparams.max_tokens != null) params.set('max_tokens', String(hyperparams.max_tokens));
      if (hyperparams.top_p != null) params.set('top_p', String(hyperparams.top_p));
      if (hyperparams.frequency_penalty != null) params.set('frequency_penalty', String(hyperparams.frequency_penalty));
      if (hyperparams.presence_penalty != null) params.set('presence_penalty', String(hyperparams.presence_penalty));
    }
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
              // Optionally read aloud
              try {
                if (readAloud && ttsSupported) {
                  speak(draftContentLocal);
                }
              } catch {}
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

  // Detect Web Speech API + TTS support and restore audio prefs
  useEffect(() => {
    const rec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setSpeechSupported(!!rec);
    // TTS support
    setTtsSupported(typeof window !== 'undefined' && !!(window as any).speechSynthesis && !!(window as any).SpeechSynthesisUtterance);
    // Restore voice language
    try {
      const saved = localStorage.getItem('chat_voice_lang');
      setVoiceLang(saved || (navigator.language || 'en-US'));
    } catch {
      setVoiceLang(navigator.language || 'en-US');
    }
    // No settings UI — minimalist mic only by default
  }, []);

  useEffect(() => { try { localStorage.setItem('chat_voice_enabled', String(voiceEnabled)); } catch {} }, [voiceEnabled]);
  useEffect(() => { try { localStorage.setItem('chat_voice_autosend', String(autoSendVoice)); } catch {} }, [autoSendVoice]);
  useEffect(() => { try { localStorage.setItem('chat_voice_readaloud', String(readAloud)); } catch {} }, [readAloud]);
  useEffect(() => { try { localStorage.setItem('chat_voice_lang', voiceLang); } catch {} }, [voiceLang]);

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
    // Use selected language for multi-lingual support
    rec.lang = voiceLang || (navigator.language || 'en-US');
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
      u.lang = voiceLang || (navigator.language || 'en-US');
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
          const defRes = await apiClient.get('/api/v1/llm-providers?is_default=true&page_size=1');
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
    if (showCommandList) return; // let onKeyDown handle selection
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSendStream();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!showCommandList) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setCmdIndex((i) => Math.min(i + 1, filteredCommands.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setCmdIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const pick = filteredCommands[cmdIndex];
      if (pick) {
        const pairs = parseVarPairs(input);
        applyCommand(pick.slug);
        void openPromptVariableModal(pick.slug, pairs);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setShowCommandList(false);
    }
  };

  // Filter commands by current query
  const filteredCommands = useMemo(() => {
    const q = commandQuery.trim().toLowerCase();
    if (!q) return commands.slice(0, 8);
    return commands
      .filter((c: any) => c.slug?.toLowerCase().startsWith(q) || c.name?.toLowerCase().includes(q))
      .slice(0, 8);
  }, [commands, commandQuery]);

  const applyCommand = (slug: string) => {
    const rest = input.replace(/^\S*/, '').trimStart();
    const prefix = `/${slug}`;
    const newValue = rest ? `${prefix} ${rest}` : `${prefix} `;
    setInput(newValue);
    setShowCommandList(false);
    setCmdIndex(0);
  };

  // Utilities for prompts by slug
  const findPromptBySlug = async (slug: string): Promise<PromptTemplate | null> => {
    try {
      const res = await promptApi.getBySlug(slug);
      return (res.data as any) || null;
    } catch {
      return null;
    }
  };

  // Parse var=value pairs after slug. Supports quoted values.
  const parseVarPairs = (text: string): Record<string, string> => {
    const out: Record<string, string> = {};
    const first = extractFirstToken(text);
    const idx = text.indexOf(first);
    const rest = idx >= 0 ? text.slice(idx + first.length).trim() : '';
    if (!rest) return out;
    const re = /(\w+)=(?:"([^"]*)"|'([^']*)'|([^\s]+))/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(rest)) !== null) {
      const k = m[1];
      const v = (m[2] ?? m[3] ?? m[4] ?? '').toString();
      out[k] = v;
    }
    return out;
  };

  const extractFirstToken = (text: string): string => (text.trimStart().split(/\s+/)[0] || '');
  const isSlashCommand = (text: string): boolean => extractFirstToken(text).startsWith('/');
  const currentSlug = (): string => extractFirstToken(input).replace(/^\//, '');

  const openPromptVariableModal = async (slug: string, prefill?: Record<string, any>) => {
    const prompt = await findPromptBySlug(slug);
    if (!prompt) return;
    setPromptForCommand(prompt);
    // Initialize values from defaults
    const init: Record<string, any> = {};
    const varsArr: PromptVariable[] = Array.isArray((prompt as any).variables)
      ? (prompt as any).variables
      : Object.entries((prompt as any).variables || {}).map(([name, meta]: any) => ({ name, ...(meta || {}) }));
    varsArr.forEach((v) => {
      if (v.default != null) init[v.name] = v.default as any;
    });
    if (prefill) {
      for (const [k, v] of Object.entries(prefill)) init[k] = v;
    }
    setPromptVarValues(init);
    setPromptVarErrors({});
    setShowPromptVars(true);
  };

  const validatePromptVars = (): boolean => {
    const errs: Record<string, string> = {};
    const varsArr: PromptVariable[] = Array.isArray((promptForCommand as any)?.variables)
      ? ((promptForCommand as any).variables as PromptVariable[])
      : Object.entries((promptForCommand as any)?.variables || {}).map(([name, meta]: any) => ({ name, ...(meta || {}) }));
    varsArr.forEach((v) => {
      const required = v.required ?? true;
      if (required && (promptVarValues[v.name] == null || String(promptVarValues[v.name]).trim() === '')) {
        errs[v.name] = 'Required';
      }
    });
    setPromptVarErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handlePromptVarsSubmit = async () => {
    if (!promptForCommand) return;
    if (!validatePromptVars()) return;
    try {
      // Use locally rendered preview content
      const content = (previewContent || '').trim();
      if (!content) return;
      setShowPromptVars(false);
      onStreamingStart?.();
      setSending(true);
      try {
        const localUser: ChatMessage = {
          id: `local-${Date.now()}`,
          session_id: sessionId,
          role: 'user',
          content,
          created_at: new Date().toISOString(),
          metadata: { command_slug: (promptForCommand as any).slug },
        } as any;
        setMessages((prev) => [...prev, localUser]);
        void startStream(content, true);
        setUserCount((c) => c + 1);
      } finally {
        setSending(false);
      }
    } catch (e) {
      console.error('Failed to send rendered prompt', e);
    } finally {
      setPromptForCommand(null);
      setPromptVarValues({});
      setPromptVarErrors({});
      setPreviewContent('');
    }
  };

  // Live local preview of rendered prompt content
  useEffect(() => {
    if (!promptForCommand) {
      setPreviewContent('');
      return;
    }
    const template = ((promptForCommand as any).content || '') as string;
    const rendered = template.replace(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g, (_m, name) => {
      const v = promptVarValues?.[name];
      return v != null && String(v).length > 0 ? String(v) : `{${name}}`;
    });
    setPreviewContent(rendered);
  }, [promptForCommand, promptVarValues]);

  // Streaming send via HTTP SSE endpoint
  const handleSendStream = async () => {
    if (!input.trim()) return;

    // If message starts with /slug, collect variables and render before sending
    if (isSlashCommand(input)) {
      const slug = currentSlug();
      if (slug) {
        setShowCommandList(false);
        await openPromptVariableModal(slug);
        return;
      }
    }

    onStreamingStart?.();
    setShowCommandList(false);
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
            {onNewSession && (
              <button
                onClick={onNewSession}
                className="h-9 w-9 inline-flex items-center justify-center border rounded bg-white hover:bg-gray-100 dark:hover:bg-gray-800"
                title="New Session"
                aria-label="New session"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d="M12 5v14"/>
                  <path d="M5 12h14"/>
                </svg>
              </button>
            )}
            {onManageTools && (
              <button
                onClick={onManageTools}
                className="h-9 w-9 inline-flex items-center justify-center border rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                title="Manage Tools"
                aria-label="Manage tools"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d="M3 6h14"/>
                  <path d="M3 12h18"/>
                  <path d="M3 18h10"/>
                </svg>
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
          className={`relative glow-card flex items-end gap-2 p-3 bg-white/80 dark:bg-[#2a2b32]/70 backdrop-blur-md border border-slate-200/70 dark:border-[#2a2b32]/70 rounded-2xl shadow-xl max-w-3xl mx-auto 
            ${recognizing ? 'ring-2 ring-red-500/40 recording' : 'focus-within:ring-2 focus-within:ring-blue-500/40'}`}
        >
          <textarea
            value={input}
            onChange={(e) => {
              const val = e.target.value;
              setInput(val);
              const first = val.trimStart().split(/\s+/)[0] || '';
              if (first.startsWith('/')) {
                setShowCommandList(true);
                setCommandQuery(first.slice(1));
                setCmdIndex(0);
              } else {
                setShowCommandList(false);
                setCommandQuery('');
              }
            }}
            onKeyDown={handleKeyDown}
            onKeyPress={handleKeyPress}
            placeholder="Message…"
            rows={1}
            disabled={sending || streaming}
            className="flex-1 bg-transparent text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-300 px-1 py-1 resize-none focus:outline-none max-h-40 min-h-[44px]"
          />
          {/* Slash command suggestions */}
          {showCommandList && filteredCommands.length > 0 && (
            <div className="absolute bottom-16 left-4 right-4 max-w-3xl mx-auto">
              <div className="bg-white dark:bg-[#2a2b32] border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden">
                {filteredCommands.map((c, idx) => (
                  <button
                    key={c.slug}
                    onMouseDown={(e) => { e.preventDefault(); applyCommand(c.slug); }}
                    className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between hover:bg-gray-50 dark:hover:bg-[#30313a] ${idx === cmdIndex ? 'bg-gray-100 dark:bg-[#30313a]' : ''}`}
                  >
                    <div>
                      <div className="font-medium text-gray-900 dark:text-gray-100">/{c.slug}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">{c.name}</div>
                    </div>
                    {c.usage && <div className="text-[10px] text-gray-400 ml-3">{c.usage}</div>}
                  </button>
                ))}
              </div>
            </div>
          )}
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
            {/* Language selector */}
            <select
              value={voiceLang}
              onChange={(e) => setVoiceLang(e.target.value)}
              title="Voice language"
              className="px-2 py-1 text-xs border rounded bg-white dark:bg-[#40414f] border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200"
            >
              {['en-US','en-GB','es-ES','fr-FR','de-DE','it-IT','pt-PT','pt-BR','ar-SA','hi-IN','ja-JP','ko-KR','zh-CN','zh-TW'].map((code) => (
                <option key={code} value={code}>{code}</option>
              ))}
            </select>
            {/* Read aloud toggle */}
            <button
              type="button"
              onClick={() => setReadAloud((v) => !v)}
              disabled={!ttsSupported}
              className={`p-2 rounded-lg border ${readAloud ? 'bg-blue-50 border-blue-300 text-blue-700' : 'bg-white dark:bg-[#40414f] border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200'} disabled:opacity-50`}
              title={ttsSupported ? (readAloud ? 'Disable read aloud' : 'Enable read aloud') : 'Text-to-speech not supported'}
              aria-pressed={readAloud}
              aria-label="Read aloud"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                <path d="M3 10v4a1 1 0 001 1h3l4 3V6l-4 3H4a1 1 0 00-1 1z" />
                <path d="M16.5 8.5a5.5 5.5 0 010 7.778" />
                <path d="M14 6a8 8 0 010 12" />
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

      {/* Prompt Variables Modal */}
      {showPromptVars && promptForCommand && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" onClick={() => { setShowPromptVars(false); setPromptForCommand(null); setPromptVarErrors({}); }} />
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative bg-white dark:bg-[#2a2b32] rounded-lg shadow-xl max-w-md w-full p-6">
              <div className="mb-4">
                <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">/{(promptForCommand as any).slug}</h2>
                <p className="text-sm text-gray-600 dark:text-gray-300">{(promptForCommand as any).name}</p>
              </div>
              <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                {/* Command hints */}
                {(() => {
                  const info = commands.find((c: any) => c.slug === (promptForCommand as any).slug) as any;
                  if (!info) return null;
                  const required = info.required_variables || [];
                  const optional = info.optional_variables || [];
                  const example = info.example || info.usage;
                  return (
                    <div className="p-2 border border-gray-200 dark:border-gray-700 rounded-md text-xs text-gray-600 dark:text-gray-300">
                      {example && (
                        <div className="mb-1"><span className="font-semibold">Example:</span> <code>/{example.replace(/^\//,'')}</code></div>
                      )}
                      {(required.length > 0 || optional.length > 0) && (
                        <div className="flex flex-wrap gap-3">
                          {required.length > 0 && (
                            <div><span className="font-semibold">Required:</span> {required.join(', ')}</div>
                          )}
                          {optional.length > 0 && (
                            <div><span className="font-semibold">Optional:</span> {optional.join(', ')}</div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })()}
                {/* Render preview */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">Preview</label>
                  <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md p-3 max-h-60 overflow-auto">
                    <pre className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-100">{previewContent}</pre>
                  </div>
                </div>
                {(Array.isArray((promptForCommand as any).variables)
                  ? (promptForCommand as any).variables
                  : Object.entries((promptForCommand as any).variables || {}).map(([name, meta]: any) => ({ name, ...(meta || {}) }))
                ).map((v: any) => (
                  <div key={v.name}>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
                      {v.name} {v.required ?? true ? <span className="text-red-500">*</span> : null}
                    </label>
                    {v.description && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{v.description}</p>
                    )}
                    <input
                      type="text"
                      value={promptVarValues[v.name] ?? ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        setPromptVarValues((prev) => ({ ...prev, [v.name]: val }));
                        if (promptVarErrors[v.name]) {
                          const n = { ...promptVarErrors } as any;
                          delete n[v.name];
                          setPromptVarErrors(n);
                        }
                      }}
                      placeholder={v.default ?? ''}
                      className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${promptVarErrors[v.name] ? 'border-red-300 bg-red-50' : 'border-gray-300'}`}
                    />
                    {promptVarErrors[v.name] && (
                      <p className="mt-1 text-xs text-red-600">{promptVarErrors[v.name]}</p>
                    )}
                  </div>
                ))}
              </div>
              <div className="mt-6 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => { setShowPromptVars(false); setPromptForCommand(null); setPromptVarErrors({}); }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handlePromptVarsSubmit}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  Run
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
