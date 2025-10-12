# Prompt Registry Phase 6: Frontend UI Specification

## Overview
Complete frontend implementation for the Prompt Registry with browse/search, create/edit, rating, and workflow integration capabilities.

## Architecture

### 1. Zustand Store (`frontend/src/lib/store.ts`)

Add PromptStore to existing store:

```typescript
// Prompt State
interface PromptTemplate {
  id: string; // UUID
  tenant_id: number;
  user_id: number;
  category_id: string | null;
  name: string;
  slug: string;
  description: string | null;
  content: string;
  suggested_model: string | null;
  suggested_provider_id: number | null;
  model_parameters: {
    temperature: number;
    top_p: number;
    top_k: number | null;
    max_tokens: number | null;
    frequency_penalty: number;
    presence_penalty: number;
  };
  tags: string[];
  variables: Record<string, {
    type: string;
    description?: string;
    required: boolean;
    default?: any;
  }>;
  is_public: boolean;
  is_active: boolean;
  is_command_enabled: boolean;
  version: number;
  usage_count: number;
  last_used_at: string | null;
  average_rating: number;
  total_ratings: number;
  total_feedback: number;
  created_at: string;
  updated_at: string;
}

interface PromptState {
  prompts: PromptTemplate[];
  currentPrompt: PromptTemplate | null;
  categories: Category[];
  setPrompts: (prompts: PromptTemplate[]) => void;
  setCurrentPrompt: (prompt: PromptTemplate | null) => void;
  addPrompt: (prompt: PromptTemplate) => void;
  updatePrompt: (id: string, prompt: Partial<PromptTemplate>) => void;
  deletePrompt: (id: string) => void;
  setCategories: (categories: Category[]) => void;
}

export const usePromptStore = create<PromptState>((set) => ({
  prompts: [],
  currentPrompt: null,
  categories: [],
  setPrompts: (prompts) => set({ prompts }),
  setCurrentPrompt: (prompt) => set({ currentPrompt: prompt }),
  addPrompt: (prompt) => set((state) => ({ prompts: [...state.prompts, prompt] })),
  updatePrompt: (id, updatedPrompt) =>
    set((state) => ({
      prompts: state.prompts.map((p) =>
        p.id === id ? { ...p, ...updatedPrompt } : p
      ),
    })),
  deletePrompt: (id) =>
    set((state) => ({
      prompts: state.prompts.filter((p) => p.id !== id),
    })),
  setCategories: (categories) => set({ categories }),
}));
```

### 2. Page Structure

```
frontend/src/app/prompts/
├── page.tsx                      # Main prompts list page
├── [id]/
│   ├── page.tsx                  # Prompt detail/edit page
│   └── execute/
│       └── page.tsx              # Prompt execution page
└── new/
    └── page.tsx                  # Create new prompt page
```

### 3. Component Structure

```
frontend/src/components/prompts/
├── PromptList.tsx                # List view with filters
├── PromptCard.tsx                # Individual prompt card
├── PromptEditor.tsx              # Create/edit form
├── PromptVariableEditor.tsx      # Variable management
├── ModelParametersEditor.tsx     # Model params configuration
├── PromptRating.tsx              # Star rating component
├── PromptFeedback.tsx            # Feedback form
├── PromptExecutor.tsx            # Execution interface
├── CommandAutocomplete.tsx       # Chat command autocomplete
└── PromptSuggestions.tsx         # Workflow suggestions
```

## Key Components

### 1. Main Prompts Page (`frontend/src/app/prompts/page.tsx`)

```typescript
'use client';

import { useEffect, useState } from 'react';
import { usePromptStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';
import PromptList from '@/components/prompts/PromptList';
import Navigation from '@/components/shared/Navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

export default function PromptsPage() {
  const { prompts, setPrompts, categories, setCategories } = usePromptStore();
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    search: '',
    category_id: null,
    tags: [],
    min_rating: null,
    sort_by: 'created_at',
    sort_order: 'desc',
  });

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [promptsRes, categoriesRes] = await Promise.all([
          apiClient.get('/api/v1/prompts', { params: filters }),
          apiClient.get('/api/v1/prompts/categories/list'),
        ]);

        if (promptsRes.data) setPrompts(promptsRes.data.prompts || []);
        if (categoriesRes.data) setCategories(categoriesRes.data.categories || []);
      } catch (error) {
        console.error('Failed to load prompts:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [filters]);

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <div className="flex justify-between items-center mb-6">
              <h1 className="text-3xl font-bold">Prompt Registry</h1>
              <button
                onClick={() => window.location.href = '/prompts/new'}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                + New Prompt
              </button>
            </div>

            {/* Filters */}
            <div className="mb-6 space-y-4">
              <input
                type="text"
                placeholder="Search prompts..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg"
              />
              {/* More filters... */}
            </div>

            {loading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : (
              <PromptList prompts={prompts} />
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
```

### 2. Prompt Editor Component

```typescript
'use client';

import { useState } from 'react';
import { apiClient } from '@/lib/api-client';
import PromptVariableEditor from './PromptVariableEditor';
import ModelParametersEditor from './ModelParametersEditor';

interface PromptEditorProps {
  prompt?: PromptTemplate;
  onSave: (prompt: PromptTemplate) => void;
  onCancel: () => void;
}

export default function PromptEditor({ prompt, onSave, onCancel }: PromptEditorProps) {
  const [formData, setFormData] = useState({
    name: prompt?.name || '',
    slug: prompt?.slug || '',
    description: prompt?.description || '',
    content: prompt?.content || '',
    category_id: prompt?.category_id || null,
    tags: prompt?.tags || [],
    suggested_model: prompt?.suggested_model || '',
    suggested_provider_id: prompt?.suggested_provider_id || null,
    model_parameters: prompt?.model_parameters || {
      temperature: 0.7,
      top_p: 1.0,
      top_k: null,
      max_tokens: null,
      frequency_penalty: 0.0,
      presence_penalty: 0.0,
    },
    is_public: prompt?.is_public || false,
    is_command_enabled: prompt?.is_command_enabled || true,
  });

  const [activeTab, setActiveTab] = useState<'content' | 'variables' | 'parameters' | 'settings'>('content');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const res = prompt
        ? await apiClient.put(`/api/v1/prompts/${prompt.id}`, formData)
        : await apiClient.post('/api/v1/prompts', formData);

      if (res.data) {
        onSave(res.data);
      }
    } catch (error) {
      console.error('Failed to save prompt:', error);
      alert('Failed to save prompt');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Info */}
      <div className="space-y-4">
        <input
          type="text"
          placeholder="Prompt Name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          className="w-full px-4 py-2 border rounded-lg"
          required
        />

        <input
          type="text"
          placeholder="Slug (e.g., summarize)"
          value={formData.slug}
          onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
          className="w-full px-4 py-2 border rounded-lg"
        />

        <textarea
          placeholder="Description"
          value={formData.description || ''}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          className="w-full px-4 py-2 border rounded-lg"
          rows={3}
        />
      </div>

      {/* Tabs */}
      <div className="border-b">
        <div className="flex space-x-4">
          {['content', 'variables', 'parameters', 'settings'].map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab as any)}
              className={`px-4 py-2 ${
                activeTab === tab
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-600'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="p-4 border rounded-lg">
        {activeTab === 'content' && (
          <textarea
            placeholder="Prompt content with {variable} placeholders"
            value={formData.content}
            onChange={(e) => setFormData({ ...formData, content: e.target.value })}
            className="w-full px-4 py-2 border rounded-lg font-mono"
            rows={12}
            required
          />
        )}

        {activeTab === 'variables' && (
          <PromptVariableEditor content={formData.content} />
        )}

        {activeTab === 'parameters' && (
          <ModelParametersEditor
            parameters={formData.model_parameters}
            onChange={(params) => setFormData({ ...formData, model_parameters: params })}
          />
        )}

        {activeTab === 'settings' && (
          <div className="space-y-4">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={formData.is_public}
                onChange={(e) => setFormData({ ...formData, is_public: e.target.checked })}
              />
              <span>Make public</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={formData.is_command_enabled}
                onChange={(e) => setFormData({ ...formData, is_command_enabled: e.target.checked })}
              />
              <span>Enable /{formData.slug || 'command'} in chat</span>
            </label>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex justify-end space-x-4">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border rounded-lg hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {prompt ? 'Update' : 'Create'} Prompt
        </button>
      </div>
    </form>
  );
}
```

### 3. Model Parameters Editor

```typescript
interface ModelParametersEditorProps {
  parameters: ModelParameters;
  onChange: (params: ModelParameters) => void;
}

export default function ModelParametersEditor({ parameters, onChange }: ModelParametersEditorProps) {
  return (
    <div className="space-y-4">
      {/* Temperature */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Temperature: {parameters.temperature}
        </label>
        <input
          type="range"
          min="0"
          max="2"
          step="0.1"
          value={parameters.temperature}
          onChange={(e) => onChange({ ...parameters, temperature: parseFloat(e.target.value) })}
          className="w-full"
        />
        <p className="text-sm text-gray-500 mt-1">
          Controls randomness (0 = deterministic, 2 = very creative)
        </p>
      </div>

      {/* Top P */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Top P: {parameters.top_p}
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={parameters.top_p}
          onChange={(e) => onChange({ ...parameters, top_p: parseFloat(e.target.value) })}
          className="w-full"
        />
        <p className="text-sm text-gray-500 mt-1">
          Nucleus sampling threshold
        </p>
      </div>

      {/* Max Tokens */}
      <div>
        <label className="block text-sm font-medium mb-2">Max Tokens</label>
        <input
          type="number"
          value={parameters.max_tokens || ''}
          onChange={(e) => onChange({ ...parameters, max_tokens: e.target.value ? parseInt(e.target.value) : null })}
          className="w-full px-4 py-2 border rounded-lg"
          placeholder="Auto (no limit)"
        />
      </div>

      {/* More parameters... */}
    </div>
  );
}
```

### 4. Rating Component

```typescript
interface PromptRatingProps {
  promptId: string;
  currentRating?: number;
  averageRating: number;
  totalRatings: number;
  onRate: (rating: number) => void;
}

export default function PromptRating({
  promptId,
  currentRating,
  averageRating,
  totalRatings,
  onRate,
}: PromptRatingProps) {
  const [hoveredRating, setHoveredRating] = useState(0);

  const handleRate = async (rating: number) => {
    try {
      await apiClient.post(`/api/v1/prompts/${promptId}/rate`, { rating });
      onRate(rating);
    } catch (error) {
      console.error('Failed to rate prompt:', error);
    }
  };

  return (
    <div className="flex items-center space-x-2">
      <div className="flex">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onMouseEnter={() => setHoveredRating(star)}
            onMouseLeave={() => setHoveredRating(0)}
            onClick={() => handleRate(star)}
            className="text-2xl"
          >
            {(hoveredRating || currentRating || 0) >= star ? '⭐' : '☆'}
          </button>
        ))}
      </div>

      <span className="text-sm text-gray-600">
        {averageRating.toFixed(1)} ({totalRatings} {totalRatings === 1 ? 'rating' : 'ratings'})
      </span>
    </div>
  );
}
```

### 5. Command Autocomplete for Chat

```typescript
'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';

interface CommandAutocompleteProps {
  input: string;
  onSelect: (command: string) => void;
}

export default function CommandAutocomplete({ input, onSelect }: CommandAutocompleteProps) {
  const [commands, setCommands] = useState([]);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (input.startsWith('/')) {
      loadCommands();
      setVisible(true);
    } else {
      setVisible(false);
    }
  }, [input]);

  const loadCommands = async () => {
    try {
      const res = await apiClient.get('/api/v1/prompts/commands/list');
      if (res.data) {
        const filtered = res.data.commands.filter((cmd: any) =>
          cmd.slug.toLowerCase().includes(input.slice(1).toLowerCase())
        );
        setCommands(filtered);
      }
    } catch (error) {
      console.error('Failed to load commands:', error);
    }
  };

  if (!visible || commands.length === 0) return null;

  return (
    <div className="absolute bottom-full left-0 mb-2 w-full bg-white border rounded-lg shadow-lg max-h-64 overflow-y-auto">
      {commands.map((cmd: any) => (
        <button
          key={cmd.slug}
          onClick={() => onSelect(`/${cmd.slug} `)}
          className="w-full px-4 py-2 text-left hover:bg-gray-100 border-b last:border-b-0"
        >
          <div className="font-medium">/{cmd.slug}</div>
          <div className="text-sm text-gray-600">{cmd.description}</div>
          <div className="text-xs text-gray-500 mt-1">{cmd.example}</div>
        </button>
      ))}
    </div>
  );
}
```

## Navigation Integration

Add to `frontend/src/components/shared/Navigation.tsx`:

```typescript
<Link
  href="/prompts"
  className={`flex items-center space-x-3 px-4 py-3 rounded-lg ${
    pathname === '/prompts' ? 'bg-blue-50 text-blue-600' : 'text-gray-700 hover:bg-gray-100'
  }`}
>
  <span className="text-xl">📝</span>
  <span>Prompts</span>
</Link>
```

## API Client Updates

Ensure `frontend/src/lib/api-client.ts` supports UUID parameters and proper error handling for the new endpoints.

## Testing Checklist

- [ ] Can browse prompts with filters
- [ ] Can create new prompt with variables
- [ ] Can edit existing prompt
- [ ] Can rate prompts (1-5 stars)
- [ ] Can add feedback
- [ ] Can execute prompt with variables
- [ ] Can see command list
- [ ] Command autocomplete works in chat
- [ ] Can search prompts by name/description/tags
- [ ] Can filter by category and rating
- [ ] Model parameters editor works
- [ ] Variables are auto-detected from content

## Styling Notes

- Use Tailwind CSS classes consistent with existing components
- Dark mode support via `dark:` classes
- Responsive design for mobile/tablet/desktop
- Loading states with spinners
- Error states with helpful messages
- Success feedback via toasts

## Estimated Implementation Time

- Store setup: 30 minutes
- Main pages (list, detail, create): 2-3 hours
- Editor components: 2-3 hours
- Rating/feedback: 1 hour
- Command autocomplete: 1 hour
- Integration testing: 1-2 hours
- **Total: 8-12 hours**
