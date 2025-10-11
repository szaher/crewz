'use client';

import { useState, useEffect } from 'react';
import { promptApi, categoryApi, type PromptCreateRequest } from '@/lib/api/prompts';
import type { PromptTemplate, PromptCategory, ModelParameters, PromptVariable } from '@/lib/store';
import ModelParametersEditor from './ModelParametersEditor';

interface PromptEditorProps {
  promptId?: string;
  onSave?: (prompt: PromptTemplate) => void;
  onCancel?: () => void;
}

export default function PromptEditor({ promptId, onSave, onCancel }: PromptEditorProps) {
  const [activeTab, setActiveTab] = useState<'content' | 'variables' | 'parameters' | 'settings'>('content');
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState<PromptCategory[]>([]);

  // Form state
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [content, setContent] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [variables, setVariables] = useState<PromptVariable[]>([]);
  const [suggestedModel, setSuggestedModel] = useState('');
  const [modelParameters, setModelParameters] = useState<ModelParameters>({
    temperature: 0.7,
    top_p: 1.0,
    max_tokens: 2000,
  });
  const [isPublic, setIsPublic] = useState(false);
  const [isCommandEnabled, setIsCommandEnabled] = useState(true);

  useEffect(() => {
    loadCategories();
    if (promptId) {
      loadPrompt();
    }
  }, [promptId]);

  const loadCategories = async () => {
    try {
      const response = await categoryApi.list();
      if (response.data) {
        setCategories(response.data);
      }
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  const loadPrompt = async () => {
    if (!promptId) return;

    setLoading(true);
    try {
      const response = await promptApi.get(promptId);
      if (response.error) throw new Error(response.error);

      const prompt = response.data!;
      setName(prompt.name);
      setSlug(prompt.slug);
      setDescription(prompt.description || '');
      setContent(prompt.content);
      setCategoryId(prompt.category_id || '');
      setTags(prompt.tags || []);
      setVariables(prompt.variables || []);
      setSuggestedModel(prompt.suggested_model || '');
      setModelParameters(prompt.model_parameters || {
        temperature: 0.7,
        top_p: 1.0,
        max_tokens: 2000,
      });
      setIsPublic(prompt.is_public);
      setIsCommandEnabled(prompt.is_command_enabled);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to load prompt');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setLoading(true);
    try {
      const data: PromptCreateRequest = {
        name,
        slug: slug || undefined,
        description: description || undefined,
        content,
        category_id: categoryId || undefined,
        tags: tags.length > 0 ? tags : undefined,
        variables: variables.length > 0 ? variables : undefined,
        suggested_model: suggestedModel || undefined,
        model_parameters: modelParameters,
        is_public: isPublic,
        is_command_enabled: isCommandEnabled,
      };

      const response = promptId
        ? await promptApi.update(promptId, data)
        : await promptApi.create(data);

      if (response.error) throw new Error(response.error);

      if (onSave && response.data) {
        onSave(response.data);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save prompt');
    } finally {
      setLoading(false);
    }
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag));
  };

  const extractVariablesFromContent = () => {
    const regex = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
    const matches = content.matchAll(regex);
    const foundVars = new Set<string>();

    for (const match of matches) {
      foundVars.add(match[1]);
    }

    // Add any new variables that don't already exist
    const existingVarNames = new Set(variables.map(v => v.name));
    const newVars: PromptVariable[] = Array.from(foundVars)
      .filter(name => !existingVarNames.has(name))
      .map(name => ({
        name,
        type: 'string',
        required: true,
      }));

    if (newVars.length > 0) {
      setVariables([...variables, ...newVars]);
      setActiveTab('variables');
    }
  };

  if (loading && promptId) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg border border-gray-200">
      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-4 px-6">
          {(['content', 'variables', 'parameters', 'settings'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6">
        {/* Content Tab */}
        {activeTab === 'content' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Code Review Prompt"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Slug
              </label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Auto-generated from name if empty"
              />
              {isCommandEnabled && slug && (
                <p className="text-xs text-gray-500 mt-1">
                  Command: /{slug}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Brief description of this prompt's purpose"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">
                  Prompt Content *
                </label>
                <button
                  type="button"
                  onClick={extractVariablesFromContent}
                  className="text-xs text-blue-600 hover:text-blue-700"
                >
                  Extract Variables
                </button>
              </div>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                required
                rows={10}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                placeholder="Use {variable_name} for dynamic values..."
              />
              <p className="text-xs text-gray-500 mt-1">
                Use {'{variable_name}'} syntax for dynamic values
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category
                </label>
                <select
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">None</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Suggested Model
                </label>
                <input
                  type="text"
                  value={suggestedModel}
                  onChange={(e) => setSuggestedModel(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., gpt-4, claude-3-opus"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tags
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddTag();
                    }
                  }}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Add a tag..."
                />
                <button
                  type="button"
                  onClick={handleAddTag}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
                >
                  Add
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1 px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-full"
                  >
                    {tag}
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(tag)}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Variables Tab */}
        {activeTab === 'variables' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Variables</h3>
              <button
                type="button"
                onClick={() => setVariables([...variables, { name: '', type: 'string', required: true }])}
                className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700"
              >
                + Add Variable
              </button>
            </div>

            {variables.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">
                No variables defined. Use the "Extract Variables" button in the Content tab.
              </p>
            ) : (
              <div className="space-y-4">
                {variables.map((variable, index) => (
                  <div key={index} className="border border-gray-200 rounded-md p-4">
                    <div className="grid grid-cols-2 gap-4 mb-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Name *
                        </label>
                        <input
                          type="text"
                          value={variable.name}
                          onChange={(e) => {
                            const newVars = [...variables];
                            newVars[index].name = e.target.value;
                            setVariables(newVars);
                          }}
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md"
                          placeholder="variable_name"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Type
                        </label>
                        <select
                          value={variable.type || 'string'}
                          onChange={(e) => {
                            const newVars = [...variables];
                            newVars[index].type = e.target.value;
                            setVariables(newVars);
                          }}
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md"
                        >
                          <option value="string">String</option>
                          <option value="number">Number</option>
                          <option value="boolean">Boolean</option>
                        </select>
                      </div>
                    </div>

                    <div className="mb-3">
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Description
                      </label>
                      <input
                        type="text"
                        value={variable.description || ''}
                        onChange={(e) => {
                          const newVars = [...variables];
                          newVars[index].description = e.target.value;
                          setVariables(newVars);
                        }}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md"
                        placeholder="What this variable represents"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Default Value
                        </label>
                        <input
                          type="text"
                          value={variable.default || ''}
                          onChange={(e) => {
                            const newVars = [...variables];
                            newVars[index].default = e.target.value;
                            setVariables(newVars);
                          }}
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md"
                        />
                      </div>
                      <div className="flex items-center">
                        <label className="flex items-center gap-2 text-sm text-gray-700">
                          <input
                            type="checkbox"
                            checked={variable.required ?? true}
                            onChange={(e) => {
                              const newVars = [...variables];
                              newVars[index].required = e.target.checked;
                              setVariables(newVars);
                            }}
                            className="rounded border-gray-300"
                          />
                          Required
                        </label>
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => setVariables(variables.filter((_, i) => i !== index))}
                        className="text-sm text-red-600 hover:text-red-700"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Parameters Tab */}
        {activeTab === 'parameters' && (
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Model Parameters</h3>
            <ModelParametersEditor
              parameters={modelParameters}
              onChange={setModelParameters}
            />
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Settings</h3>

            <div className="space-y-3">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={isPublic}
                  onChange={(e) => setIsPublic(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <div>
                  <div className="text-sm font-medium text-gray-700">Public</div>
                  <div className="text-xs text-gray-500">
                    Make this prompt visible to all users in your organization
                  </div>
                </div>
              </label>

              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={isCommandEnabled}
                  onChange={(e) => setIsCommandEnabled(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <div>
                  <div className="text-sm font-medium text-gray-700">Enable as Chat Command</div>
                  <div className="text-xs text-gray-500">
                    Allow this prompt to be invoked as /{slug || 'slug'} in chat
                  </div>
                </div>
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 px-6 py-4 flex items-center justify-end gap-3">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Saving...' : promptId ? 'Update Prompt' : 'Create Prompt'}
        </button>
      </div>
    </form>
  );
}
