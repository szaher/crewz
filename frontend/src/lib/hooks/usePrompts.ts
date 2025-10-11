import { useState, useEffect, useCallback } from 'react';
import { promptApi, categoryApi, type PromptListParams } from '../api/prompts';
import type { PromptTemplate, PromptCategory } from '../store';

export function usePrompts(params?: PromptListParams) {
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [categories, setCategories] = useState<PromptCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPrompts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await promptApi.list(params);
      if (response.error) throw new Error(response.error);
      setPrompts(response.data || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch prompts';
      setError(message);
      console.error('Failed to fetch prompts:', err);
    } finally {
      setLoading(false);
    }
  }, [params]);

  const fetchCategories = useCallback(async () => {
    try {
      const response = await categoryApi.list();
      if (response.error) throw new Error(response.error);
      setCategories(response.data || []);
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  }, []);

  useEffect(() => {
    fetchPrompts();
    fetchCategories();
  }, [fetchPrompts, fetchCategories]);

  return {
    prompts,
    categories,
    loading,
    error,
    refetch: fetchPrompts,
  };
}
