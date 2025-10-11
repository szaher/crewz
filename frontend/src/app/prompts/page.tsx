'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Navigation from '@/components/shared/Navigation';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import { usePrompts } from '@/lib/hooks/usePrompts';
import { promptApi } from '@/lib/api/prompts';
import type { PromptTemplate } from '@/lib/store';

export default function PromptsPage() {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [minRating, setMinRating] = useState<number>(0);
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [publicOnly, setPublicOnly] = useState<boolean>(false);

  const { prompts, categories, loading, error, refetch } = usePrompts({
    search: search || undefined,
    category_id: selectedCategory || undefined,
    tags: selectedTags.length > 0 ? selectedTags : undefined,
    min_rating: minRating > 0 ? minRating : undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
    public_only: publicOnly,
  });

  // Extract all unique tags from prompts
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    prompts.forEach(p => p.tags?.forEach(t => tagSet.add(t)));
    return Array.from(tagSet).sort();
  }, [prompts]);

  const handleDeletePrompt = async (promptId: string) => {
    if (!confirm('Are you sure you want to delete this prompt?')) return;

    try {
      const response = await promptApi.delete(promptId);
      if (response.error) throw new Error(response.error);
      refetch();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete prompt');
    }
  };

  const handleToggleTag = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  const clearFilters = () => {
    setSearch('');
    setSelectedCategory('');
    setSelectedTags([]);
    setMinRating(0);
    setPublicOnly(false);
  };

  const hasActiveFilters = search || selectedCategory || selectedTags.length > 0 || minRating > 0 || publicOnly;

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        <Navigation />
        <div className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto p-6">
            <Breadcrumbs />

            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Prompt Registry</h1>
                <p className="text-sm text-gray-600 mt-1">
                  Browse, create, and manage reusable prompt templates
                </p>
              </div>
              <button
                onClick={() => router.push('/prompts/new')}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
              >
                + Create Prompt
              </button>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Search */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Search
                  </label>
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search prompts..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Category */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Category
                  </label>
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Categories</option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Min Rating */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Min Rating
                  </label>
                  <select
                    value={minRating}
                    onChange={(e) => setMinRating(Number(e.target.value))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="0">Any Rating</option>
                    <option value="4">4+ Stars</option>
                    <option value="3">3+ Stars</option>
                    <option value="2">2+ Stars</option>
                    <option value="1">1+ Stars</option>
                  </select>
                </div>

                {/* Sort */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Sort By
                  </label>
                  <div className="flex gap-2">
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value)}
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="created_at">Created</option>
                      <option value="rating">Rating</option>
                      <option value="usage">Usage</option>
                      <option value="name">Name</option>
                    </select>
                    <button
                      onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
                      className="px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                      title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}
                    >
                      {sortOrder === 'asc' ? '↑' : '↓'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Tags Filter */}
              {allTags.length > 0 && (
                <div className="mt-4">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Tags
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {allTags.map((tag) => (
                      <button
                        key={tag}
                        onClick={() => handleToggleTag(tag)}
                        className={`px-3 py-1 text-xs rounded-full transition-colors ${
                          selectedTags.includes(tag)
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Public Only Toggle */}
              <div className="mt-4 flex items-center gap-2">
                <input
                  type="checkbox"
                  id="publicOnly"
                  checked={publicOnly}
                  onChange={(e) => setPublicOnly(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <label htmlFor="publicOnly" className="text-sm text-gray-700">
                  Show public prompts only
                </label>
              </div>

              {/* Clear Filters */}
              {hasActiveFilters && (
                <div className="mt-4">
                  <button
                    onClick={clearFilters}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    Clear all filters
                  </button>
                </div>
              )}
            </div>

            {/* Content */}
            {error ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="text-center max-w-md">
                  <p className="text-red-600 mb-4">Failed to load prompts: {error}</p>
                  <button
                    onClick={refetch}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Retry
                  </button>
                </div>
              </div>
            ) : loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : prompts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <p className="text-gray-500 mb-4">
                  {hasActiveFilters
                    ? 'No prompts found matching your filters.'
                    : 'No prompts yet. Create your first prompt to get started.'}
                </p>
                <button
                  onClick={() => router.push('/prompts/new')}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                >
                  Create Prompt
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {prompts.map((prompt) => (
                  <PromptCard
                    key={prompt.id}
                    prompt={prompt}
                    onDelete={handleDeletePrompt}
                    onClick={() => router.push(`/prompts/${prompt.id}`)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

// Prompt Card Component
function PromptCard({
  prompt,
  onDelete,
  onClick
}: {
  prompt: PromptTemplate;
  onDelete: (id: string) => void;
  onClick: () => void;
}) {
  const renderStars = (rating: number) => {
    return (
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <span
            key={star}
            className={`text-sm ${
              star <= rating ? 'text-yellow-400' : 'text-gray-300'
            }`}
          >
            ★
          </span>
        ))}
        <span className="text-xs text-gray-600 ml-1">
          ({prompt.total_ratings})
        </span>
      </div>
    );
  };

  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-900 flex-1">
          {prompt.name}
        </h3>
        {prompt.is_command_enabled && (
          <span
            className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded"
            title="Available as chat command"
          >
            /{prompt.slug}
          </span>
        )}
      </div>

      {prompt.description && (
        <p className="text-sm text-gray-600 mt-2 line-clamp-2">
          {prompt.description}
        </p>
      )}

      {/* Tags */}
      {prompt.tags && prompt.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {prompt.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded"
            >
              {tag}
            </span>
          ))}
          {prompt.tags.length > 3 && (
            <span className="text-xs text-gray-500">
              +{prompt.tags.length - 3} more
            </span>
          )}
        </div>
      )}

      {/* Rating */}
      <div className="mt-4">
        {renderStars(Math.round(prompt.average_rating))}
      </div>

      {/* Stats */}
      <div className="mt-4 flex items-center gap-4 text-xs text-gray-500">
        <span>🔄 {prompt.total_executions} uses</span>
        {prompt.is_public && <span className="text-green-600">🌐 Public</span>}
      </div>

      {/* Actions */}
      <div className="mt-4 flex gap-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
          className="flex-1 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
        >
          View
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(prompt.id);
          }}
          className="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
