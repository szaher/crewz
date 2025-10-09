'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import MessageList from './MessageList';
import type { ChatMessage } from '@/types/api';

interface ChatWindowProps {
  sessionId: number;
  sessionTitle: string;
  crewId?: number;
  onManageTools?: () => void;
  onTitleUpdate?: (newTitle: string) => void;
}

export default function ChatWindow({ sessionId, sessionTitle, crewId, onManageTools, onTitleUpdate }: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userCount, setUserCount] = useState(0);
  const [provider, setProvider] = useState<any | null>(null);
  const [providerLoading, setProviderLoading] = useState(false);
  const [sessionTools, setSessionTools] = useState<any[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);

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

  const handleSend = async () => {
    if (!input.trim()) return;
    setSending(true);
    const text = input;
    setInput('');
    try {
      // Append a subtle instruction to always respond in Markdown with proper fenced code
      const mdHint = '\n\nPlease format your entire response in GitHub-Flavored Markdown. Use fenced code blocks with appropriate languages (e.g., ```json, ```yaml, ```python, ```javascript) for any code, JSON, YAML, or logs.';
      const gen = await apiClient.post(`/api/v1/chat/sessions/${sessionId}/generate?user_message=${encodeURIComponent(text + mdHint)}`);
      if (gen.data) {
        const userMsg = gen.data.user_message as ChatMessage;
        const aiMsg = gen.data.ai_response as ChatMessage;
        setMessages((prev) => [...prev, userMsg, aiMsg]);
        // track user messages sent in this session
        setUserCount((c) => c + 1);
      }
    } catch (e) {
      console.error('Failed to send/generate message', e);
    } finally {
      setSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
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
          {onManageTools && (
            <button
              onClick={onManageTools}
              className="h-9 px-3 text-sm border rounded hover:bg-gray-100 whitespace-nowrap self-start"
              title="Manage Tools"
              aria-label="Manage tools"
            >
              Manage Tools
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-gradient-to-b from-white to-slate-50 dark:from-[#2b2f36] dark:to-[#26272b]">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <MessageList messages={messages} />
        )}
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 dark:border-gray-800 px-6 py-4">
        <div className="flex items-end gap-2 p-3 bg-white dark:bg-[#40414f] border border-slate-200 dark:border-[#2a2b32] rounded-xl">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Message…"
            rows={1}
            disabled={sending}
            className="flex-1 bg-transparent text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-300 px-1 py-1 resize-none focus:outline-none max-h-40 min-h-[44px]"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? 'Sending…' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
