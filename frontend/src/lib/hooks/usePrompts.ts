import { useState, useEffect, useCallback, useMemo } from 'react';
import { promptApi, categoryApi, type PromptListParams } from '../api/prompts';
import type { PromptTemplate, PromptCategory } from '../store';

export function usePrompts(params?: PromptListParams) {
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [categories, setCategories] = useState<PromptCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Stringify params to avoid infinite loop from object reference changes
  const paramsKey = useMemo(() => JSON.stringify(params || {}), [
    params?.category_id,
    params?.tags,
    params?.search,
    params?.public_only,
    params?.min_rating,
    params?.sort_by,
    params?.sort_order,
    params?.page,
    params?.page_size,
  ]);

  const fetchPrompts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await promptApi.list(params);
      if (response.error) throw new Error(response.error);
      // API returns { prompts: [], total: number, page: number }
      const data = response.data as any;
      setPrompts(data?.prompts || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch prompts';
      setError(message);
      console.error('Failed to fetch prompts:', err);
    } finally {
      setLoading(false);
    }
  }, [paramsKey]); // Use stringified key instead of params object

  const fetchCategories = useCallback(async () => {
    try {
      const response = await categoryApi.list();
      if (response.error) throw new Error(response.error);
      // API returns { categories: [], total: number }
      const data = response.data as any;
      setCategories(data?.categories || []);
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  }, []);

  useEffect(() => {
    fetchPrompts();
  }, [fetchPrompts]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  return {
    prompts,
    categories,
    loading,
    error,
    refetch: fetchPrompts,
  };
}
