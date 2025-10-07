'use client';

import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { useLLMProviders, type LLMProvider as ProviderItem } from '@/lib/hooks/useLLMProviders';
import { apiClient } from '@/lib/api-client';

export default function ProvidersPage() {
  const { providers, loading, error, createProvider, updateProvider, deleteProvider, testConnection, setDefault, refetch } = useLLMProviders();
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<ProviderItem | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<Record<number, { ok: boolean; message: string; at: string }>>({});
  const [cannotDelete, setCannotDelete] = useState<Record<number, string>>({});
  const [usage, setUsage] = useState<Record<number, { agents: number; crews: number }>>({});
  const [reassignFor, setReassignFor] = useState<ProviderItem | null>(null);
  const [openMenuId, setOpenMenuId] = useState<number | null>(null);
  const [showUsageFor, setShowUsageFor] = useState<ProviderItem | null>(null);

  // Close kebab menu on outside click / escape (bubble phase so inner stopPropagation works)
  useEffect(() => {
    const onDocClick = () => setOpenMenuId(null);
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpenMenuId(null); };
    if (openMenuId !== null) {
      document.addEventListener('click', onDocClick);
      document.addEventListener('keydown', onKey);
    }
    return () => {
      document.removeEventListener('click', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [openMenuId]);

  useEffect(() => {
    // fetch usage counts for current providers
    const fetchUsage = async () => {
      const entries = await Promise.all(
        providers.map(async (p) => {
          try {
            const res = await apiClient.get(`/api/v1/llm-providers/${p.id}/usage`);
            if (res.error) return [p.id, { agents: 0, crews: 0 }] as const;
            return [p.id, { agents: res.data.agent_count || 0, crews: res.data.crew_count || 0 }] as const;
          } catch {
            return [p.id, { agents: 0, crews: 0 }] as const;
          }
        })
      );
      const map: Record<number, { agents: number; crews: number }> = {};
      for (const [id, val] of entries) map[id] = val;
      setUsage(map);
    };
    if (providers.length) void fetchUsage();
  }, [providers]);

  const handleTest = async (id: number) => {
    setTestingId(id);
    try {
      const res = await testConnection(id);
      setTestResult(prev => ({
        ...prev,
        [id]: { ok: !!res.success, message: res.message || (res.success ? 'OK' : 'Failed'), at: new Date().toLocaleTimeString() },
      }));
    } catch (e: any) {
      setTestResult(prev => ({ ...prev, [id]: { ok: false, message: e?.message || 'Failed', at: new Date().toLocaleTimeString() } }));
    }
    setTestingId(null);
  };

  const handleSetDefault = async (id: number) => {
    try {
      await setDefault(id);
      await refetch();
    } catch (e: any) {
      alert('Failed to set default: ' + (e?.message || 'Unknown error'));
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this provider? This action cannot be undone.')) return;
    try {
      await deleteProvider(id);
      await refetch();
    } catch (e: any) {
      if (e?.status === 409) {
        setCannotDelete(prev => ({ ...prev, [id]: e?.message || 'Provider has dependencies.' }));
      } else {
        alert('Failed to delete: ' + (e?.message || 'Unknown error'));
      }
    }
  };

  return (
    <ProtectedRoute>
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <Breadcrumbs />
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">LLM Providers</h1>
            <p className="text-gray-500 text-sm">Manage and validate LLM provider credentials</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700"
          >
            New Provider
          </button>
        </div>

        {/* Notifications above the table */}
        {!loading && !error && Object.keys(testResult).length > 0 && (
          <div className="p-3 rounded border text-sm bg-gray-50">
            <div className="font-medium mb-1">Recent Tests</div>
            <ul className="list-disc ml-5 space-y-1">
              {providers.filter(p => !!testResult[p.id]).map(p => (
                <li key={p.id} className={testResult[p.id].ok ? 'text-green-700' : 'text-red-700'}>
                  {p.name}: {testResult[p.id].ok ? 'OK' : 'Fail'} — {testResult[p.id].message} ({testResult[p.id].at})
                </li>
              ))}
            </ul>
          </div>
        )}

        {loading ? (
          <div className="py-12 text-center text-gray-500">Loading…</div>
        ) : error ? (
          <div className="py-12 text-center text-red-600">{error}</div>
        ) : (
          <div className="rounded-lg border border-gray-200 bg-white relative h-[70vh] overflow-y-auto">
            <table className="w-full text-sm table-fixed">
              <thead>
                <tr className="bg-gray-50 text-gray-600 sticky top-0 z-10">
                  <th className="px-4 py-2 text-left">Name</th>
                  <th className="px-4 py-2 text-left">Type</th>
                  <th className="px-4 py-2 text-left">Model</th>
                  <th className="px-6 py-2 text-left">Default</th>
                  <th className="px-4 py-2 text-left">Active</th>
                  <th className="px-4 py-2 text-left">Last Test</th>
                  <th className="px-4 py-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {providers.map((p) => (
                  <tr key={p.id} className="odd:bg-white even:bg-gray-50 hover:bg-gray-100">
                    <td className="px-4 py-2 truncate max-w-[240px]">
                      <Tooltip content={p.name}><span>{p.name}</span></Tooltip>
                    </td>
                    <td className="px-4 py-2 capitalize whitespace-nowrap">
                      <Tooltip content={`Provider type: ${p.provider_type}`}><span>{p.provider_type}</span></Tooltip>
                    </td>
                    <td className="px-4 py-2 pr-8 truncate max-w-[260px]">
                      <Tooltip content={p.model_name || '—'}><span>{p.model_name || '—'}</span></Tooltip>
                    </td>
                    <td className="px-6 py-2" aria-label={p.is_default ? 'Default' : 'Not default'}>
                      <Tooltip content={p.is_default ? 'Default provider' : 'Not default'}>
                        <span className="inline-flex items-center"><IconStarOrOutline isDefault={p.is_default} /></span>
                      </Tooltip>
                    </td>
                    <td className="px-4 py-2" aria-label={p.is_active ? 'Active' : 'Inactive'}>
                      <Tooltip content={p.is_active ? 'Active' : 'Inactive'}>
                        <span className="inline-flex items-center"><IconActive isActive={p.is_active} /></span>
                      </Tooltip>
                    </td>
                    <td className="px-4 py-2 text-sm">
                      {testResult[p.id] ? (
                        <Tooltip content={testResult[p.id].message}>
                          <span className={testResult[p.id].ok ? 'text-green-700' : 'text-red-700'}>
                            {testResult[p.id].ok ? 'OK' : 'Fail'} · {testResult[p.id].at}
                          </span>
                        </Tooltip>
                      ) : (
                        <span className="text-gray-500">—</span>
                      )}
                    </td>
                    
                    <td className="px-4 py-2">
                      <div className="relative inline-block text-left">
                        <button
                          onClick={(e) => { e.stopPropagation(); setOpenMenuId(openMenuId === p.id ? null : p.id); }}
                          aria-haspopup="menu"
                          aria-expanded={openMenuId === p.id}
                          title="Actions"
                          className="h-8 w-8 flex items-center justify-center rounded hover:bg-gray-100 border border-gray-200 bg-white"
                        >
                          ⋮
                        </button>
                        {openMenuId === p.id && (
                          <div
                            className="absolute right-0 mt-2 w-44 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 z-50"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <div className="py-1 text-sm">
                              <button
                                onClick={() => { setOpenMenuId(null); setShowUsageFor(p); }}
                                className="w-full px-3 py-2 text-left hover:bg-gray-50"
                                title="Where used"
                              >
                                🔍 Where used
                              </button>
                              <button
                                onClick={() => { setOpenMenuId(null); void handleTest(p.id); }}
                                disabled={testingId === p.id}
                                className={`w-full px-3 py-2 text-left hover:bg-gray-50 ${testingId === p.id ? 'opacity-60 cursor-not-allowed' : ''}`}
                                title="Test"
                              >
                                🧪 Test
                              </button>
                              <button
                                onClick={() => { setOpenMenuId(null); setEditing(p); }}
                                className="w-full px-3 py-2 text-left hover:bg-gray-50"
                                title="Edit"
                              >
                                ✏️ Edit
                              </button>
                              <button
                                onClick={() => { setOpenMenuId(null); setReassignFor(p); }}
                                className="w-full px-3 py-2 text-left hover:bg-gray-50"
                                title="Reassign dependents"
                              >
                                🔁 Reassign
                              </button>
                              {!p.is_default && (
                                <button
                                  onClick={() => { setOpenMenuId(null); void handleSetDefault(p.id); }}
                                  className="w-full px-3 py-2 text-left hover:bg-gray-50"
                                  title="Set default"
                                >
                                  ⭐ Set default
                                </button>
                              )}
                              <button
                                onClick={() => { setOpenMenuId(null); void handleDelete(p.id); }}
                                disabled={!!cannotDelete[p.id]}
                                className={`w-full px-3 py-2 text-left hover:bg-red-50 ${cannotDelete[p.id] ? 'opacity-60 cursor-not-allowed' : 'text-red-700'}`}
                                title={cannotDelete[p.id] || 'Delete'}
                              >
                                🗑️ Delete
                              </button>
                            </div>
                          </div>
                        )}
                        {cannotDelete[p.id] && (
                          <div className="mt-1 text-xs text-amber-700" role="note">
                            {cannotDelete[p.id]}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        

        {showUsageFor && (
          <WhereUsedModal
            provider={showUsageFor}
            counts={usage[showUsageFor.id] || { agents: 0, crews: 0 }}
            onClose={() => setShowUsageFor(null)}
          />
        )}

        {showCreate && (
          <CreateProviderModal
            onClose={() => setShowCreate(false)}
            onCreated={async (createdId) => {
              setShowCreate(false);
              await refetch();
              // Auto-test newly created provider
              await handleTest(createdId);
            }}
          />
        )}

        {editing && (
          <EditProviderModal
            provider={editing}
            onClose={() => setEditing(null)}
            onUpdated={async () => {
              setEditing(null);
              await refetch();
            }}
          />
        )}

        {reassignFor && (
          <ReassignModal
            source={reassignFor}
            providers={providers}
            usage={usage[reassignFor.id] || { agents: 0, crews: 0 }}
            onClose={() => setReassignFor(null)}
            onDone={async () => {
              setReassignFor(null);
              setCannotDelete(prev => ({ ...prev, [reassignFor.id]: '' }));
              await refetch();
            }}
          />
        )}
      </div>
    </ProtectedRoute>
  );
}

function CreateProviderModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: number) => void }) {
  const [form, setForm] = useState({
    name: '',
    provider_type: 'openai',
    model_name: '',
    api_key: '',
    api_base: '',
    is_default: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    const payload: any = { ...form };
    if (!payload.api_key) delete payload.api_key;
    if (!payload.api_base) delete payload.api_base;
    const res = await apiClient.post('/api/v1/llm-providers', payload);
    if (res.error) {
      setError(res.error);
      setSubmitting(false);
      return;
    }
    const provider = res.data?.provider || res.data;
    onCreated(provider.id);
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-[520px] p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Create LLM Provider</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>

        {error && <div className="p-2 text-sm text-red-600 bg-red-50 rounded">{error}</div>}

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium">Name</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1 w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium">Provider Type</label>
            <select value={form.provider_type} onChange={(e) => setForm({ ...form, provider_type: e.target.value })} className="mt-1 w-full border rounded px-3 py-2">
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="ollama">Ollama</option>
              <option value="vllm">vLLM</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium">Model Name</label>
            <input value={form.model_name} onChange={(e) => setForm({ ...form, model_name: e.target.value })} placeholder="e.g., gpt-4" className="mt-1 w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium">API Key</label>
            <input value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder="sk-..." className="mt-1 w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium">API Base URL</label>
            <input value={form.api_base} onChange={(e) => setForm({ ...form, api_base: e.target.value })} placeholder="https://api.openai.com/v1" className="mt-1 w-full border rounded px-3 py-2" />
          </div>
          <label className="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />
            Set as default provider
          </label>
        </div>

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded border">Cancel</button>
          <button onClick={submit} disabled={submitting} className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">
            {submitting ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
}

function EditProviderModal({ provider, onClose, onUpdated }: { provider: ProviderItem; onClose: () => void; onUpdated: () => void }) {
  const [form, setForm] = useState({
    name: provider.name,
    provider_type: provider.provider_type,
    model_name: provider.model_name,
    api_key: '',
    api_base: provider.api_base || '',
    is_default: provider.is_default || false,
    is_active: provider.is_active,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    const payload: any = { ...form };
    if (!payload.api_key) delete payload.api_key; // do not overwrite key if left blank
    if (!payload.api_base) delete payload.api_base;
    const res = await apiClient.put(`/api/v1/llm-providers/${provider.id}`, payload);
    if (res.error) {
      setError(res.error);
      setSubmitting(false);
      return;
    }
    // Optionally re-test after update
    onUpdated();
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-[520px] p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Edit LLM Provider</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>

        {error && <div className="p-2 text-sm text-red-600 bg-red-50 rounded">{error}</div>}

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium">Name</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1 w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium">Provider Type</label>
            <select value={form.provider_type} onChange={(e) => setForm({ ...form, provider_type: e.target.value })} className="mt-1 w-full border rounded px-3 py-2">
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="ollama">Ollama</option>
              <option value="vllm">vLLM</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium">Model Name</label>
            <input value={form.model_name} onChange={(e) => setForm({ ...form, model_name: e.target.value })} placeholder="e.g., gpt-4" className="mt-1 w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium">API Key (leave blank to keep)</label>
            <input value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder="sk-..." className="mt-1 w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium">API Base URL</label>
            <input value={form.api_base} onChange={(e) => setForm({ ...form, api_base: e.target.value })} placeholder="https://api.openai.com/v1" className="mt-1 w-full border rounded px-3 py-2" />
          </div>
          <label className="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />
            Set as default provider
          </label>
          <label className="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
            Active
          </label>
        </div>

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded border">Cancel</button>
          <button onClick={submit} disabled={submitting} className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">
            {submitting ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ReassignModal({ source, providers, usage, onClose, onDone }: {
  source: ProviderItem;
  providers: ProviderItem[];
  usage: { agents: number; crews: number };
  onClose: () => void;
  onDone: () => void;
}) {
  const { reassignDependents } = useLLMProviders();
  const [targetId, setTargetId] = useState<number | ''>('');
  const [scopeAgents, setScopeAgents] = useState(usage.agents > 0);
  const [scopeCrews, setScopeCrews] = useState(usage.crews > 0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const handleSubmit = async () => {
    setError(null);
    setResult(null);
    if (!targetId || (targetId as number) === source.id) {
      setError('Please select a different target provider.');
      return;
    }
    if (!scopeAgents && !scopeCrews) {
      setError('Select at least one dependent type to reassign.');
      return;
    }
    setSubmitting(true);
    try {
      const scope = scopeAgents && scopeCrews ? 'all' : (scopeAgents ? 'agents' : 'crews');
      const res = await reassignDependents(source.id, targetId as number, scope as any);
      setResult(`Reassigned agents: ${res.agents_reassigned}, crews: ${res.crews_reassigned}`);
      setTimeout(onDone, 800);
    } catch (e: any) {
      setError(e?.message || 'Reassign failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-[520px] p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Reassign Dependents</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>

        <p className="text-sm text-gray-600">Move agents and/or crews using <strong>{source.name}</strong> to another provider.</p>

        {error && <div className="p-2 text-sm text-red-600 bg-red-50 rounded">{error}</div>}
        {result && <div className="p-2 text-sm text-green-700 bg-green-50 rounded">{result}</div>}

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium">Target Provider</label>
            <select
              value={targetId}
              onChange={(e) => setTargetId(e.target.value ? Number(e.target.value) : '')}
              className="mt-1 w-full border rounded px-3 py-2"
            >
              <option value="">Select provider…</option>
              {providers.filter(p => p.id !== source.id).map(p => (
                <option key={p.id} value={p.id}>{p.name} ({p.provider_type})</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-4 text-sm">
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={scopeAgents} onChange={(e) => setScopeAgents(e.target.checked)} />
              Agents ({usage.agents})
            </label>
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" checked={scopeCrews} onChange={(e) => setScopeCrews(e.target.checked)} />
              Crews ({usage.crews})
            </label>
          </div>
        </div>

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded border">Cancel</button>
          <button onClick={handleSubmit} disabled={submitting} className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">
            {submitting ? 'Reassigning…' : 'Reassign'}
          </button>
        </div>
      </div>
    </div>
  );
}

// Simple tooltip component using Tailwind and group hover
function Tooltip({ content, children }: { content: string; children: React.ReactNode }) {
  const anchorRef = useRef<HTMLSpanElement | null>(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });

  const updatePosition = () => {
    if (!anchorRef.current) return;
    const rect = anchorRef.current.getBoundingClientRect();
    const top = Math.min(rect.bottom + 8, window.innerHeight - 8); // try to keep inside viewport
    const left = rect.left + rect.width / 2;
    setPos({ top, left });
  };

  useEffect(() => {
    if (!open) return;
    updatePosition();
    const onScroll = () => updatePosition();
    const onResize = () => updatePosition();
    window.addEventListener('scroll', onScroll, true);
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('scroll', onScroll, true);
      window.removeEventListener('resize', onResize);
    };
  }, [open]);

  return (
    <span
      ref={anchorRef}
      className="relative inline-flex align-middle"
      onMouseEnter={() => { setOpen(true); updatePosition(); }}
      onMouseLeave={() => setOpen(false)}
    >
      {children}
      {open && typeof window !== 'undefined' && createPortal(
        <div
          className="pointer-events-none fixed z-[9999] px-2 py-1 text-xs text-white bg-gray-900 rounded shadow whitespace-nowrap"
          style={{ top: pos.top, left: pos.left, transform: 'translateX(-50%)' }}
        >
          {content}
        </div>,
        document.body
      )}
    </span>
  );
}

function IconStarOrOutline({ isDefault }: { isDefault: boolean }) {
  return isDefault ? (
    <IconStar className="h-5 w-5 text-yellow-500" />
  ) : (
    <IconStarOutline className="h-5 w-5 text-gray-400" />
  );
}

function IconActive({ isActive }: { isActive: boolean }) {
  return isActive ? (
    <IconCheckCircle className="h-5 w-5 text-green-600" />
  ) : (
    <IconCircleOff className="h-5 w-5 text-gray-400" />
  );
}

// Lightweight inline SVG icons (no external dependency)
function IconStar({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.803 2.037a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.803-2.037a1 1 0 00-1.175 0l-2.803 2.037c-.785.57-1.84-.197-1.54-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.462a1 1 0 00.95-.69l1.07-3.292z" />
    </svg>
  );
}

function IconStarOutline({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
    </svg>
  );
}

function IconCheckCircle({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414L9 13.414l4.707-4.707z" clipRule="evenodd" />
    </svg>
  );
}

function IconCircleOff({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <line x1="16" y1="8" x2="8" y2="16" />
    </svg>
  );
}

function WhereUsedModal({ provider, counts, onClose }: { provider: ProviderItem; counts: { agents: number; crews: number }; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-lg w-[520px] p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Where used</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>
        <p className="text-sm text-gray-600">Dependencies for <strong>{provider.name}</strong> ({provider.provider_type}).</p>
        <div className="space-y-3 text-sm">
          <div className="flex items-center justify-between">
            <span>Agents</span>
            <a href={`/crews?llm_provider_id=${provider.id}`} className="text-blue-600 hover:underline">{counts.agents}</a>
          </div>
          <div className="flex items-center justify-between">
            <span>Crews (manager)</span>
            <a href={`/crews?manager_llm_provider_id=${provider.id}`} className="text-blue-600 hover:underline">{counts.crews}</a>
          </div>
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button onClick={onClose} className="px-4 py-2 rounded border">Close</button>
        </div>
      </div>
    </div>
  );
}
