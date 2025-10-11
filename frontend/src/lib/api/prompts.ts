/**
 * Prompt Registry API Client
 * Provides functions for managing prompts, categories, ratings, and feedback
 */

import { apiClient } from '../api-client';
import type { PromptTemplate, PromptCategory, ModelParameters, PromptVariable } from '../store';

// Request/Response Types
export interface PromptListParams {
  category_id?: string;
  tags?: string[];
  search?: string;
  public_only?: boolean;
  min_rating?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface PromptCreateRequest {
  name: string;
  slug?: string;
  description?: string;
  content: string;
  category_id?: string;
  tags?: string[];
  variables?: PromptVariable[];
  suggested_model?: string;
  model_parameters?: ModelParameters;
  is_public?: boolean;
  is_command_enabled?: boolean;
}

export interface PromptUpdateRequest extends Partial<PromptCreateRequest> {
  version_notes?: string;
}

export interface PromptExecuteRequest {
  variables?: Record<string, any>;
  context_type?: 'chat' | 'task' | 'direct' | 'command';
  context_id?: string;
  model_override?: string;
  parameter_overrides?: ModelParameters;
}

export interface PromptExecuteResponse {
  execution_id: string;
  prompt_id: string;
  rendered_content: string;
  model_used?: string;
  parameters_used?: ModelParameters;
  execution_time_ms: number;
  success: boolean;
  created_at: string;
}

export interface PromptRatingRequest {
  rating: number; // 1-5
}

export interface PromptFeedbackRequest {
  feedback_type: 'comment' | 'improvement' | 'bug';
  content: string;
}

export interface CategoryCreateRequest {
  name: string;
  slug?: string;
  description?: string;
  parent_id?: string;
}

export interface CommandInfo {
  slug: string;
  name: string;
  description?: string;
  usage: string;
  variables: PromptVariable[];
}

/**
 * Prompt CRUD Operations
 */
export const promptApi = {
  /**
   * List prompts with optional filtering and pagination
   */
  async list(params?: PromptListParams) {
    const queryParams = new URLSearchParams();

    if (params) {
      if (params.category_id) queryParams.append('category_id', params.category_id);
      if (params.tags) params.tags.forEach(tag => queryParams.append('tags', tag));
      if (params.search) queryParams.append('search', params.search);
      if (params.public_only !== undefined) queryParams.append('public_only', String(params.public_only));
      if (params.min_rating !== undefined) queryParams.append('min_rating', String(params.min_rating));
      if (params.sort_by) queryParams.append('sort_by', params.sort_by);
      if (params.sort_order) queryParams.append('sort_order', params.sort_order);
      if (params.page) queryParams.append('page', String(params.page));
      if (params.page_size) queryParams.append('page_size', String(params.page_size));
    }

    const query = queryParams.toString();
    const endpoint = `/api/v1/prompts${query ? `?${query}` : ''}`;

    return apiClient.get<PromptTemplate[]>(endpoint);
  },

  /**
   * Get a single prompt by ID
   */
  async get(promptId: string) {
    return apiClient.get<PromptTemplate>(`/api/v1/prompts/${promptId}`);
  },

  /**
   * Create a new prompt
   */
  async create(data: PromptCreateRequest) {
    return apiClient.post<PromptTemplate>('/api/v1/prompts', data);
  },

  /**
   * Update an existing prompt
   */
  async update(promptId: string, data: PromptUpdateRequest) {
    return apiClient.put<PromptTemplate>(`/api/v1/prompts/${promptId}`, data);
  },

  /**
   * Delete (soft delete) a prompt
   */
  async delete(promptId: string) {
    return apiClient.delete(`/api/v1/prompts/${promptId}`);
  },

  /**
   * Execute a prompt with variables
   */
  async execute(promptId: string, data: PromptExecuteRequest) {
    return apiClient.post<PromptExecuteResponse>(`/api/v1/prompts/${promptId}/execute`, data);
  },

  /**
   * Rate a prompt (1-5 stars)
   */
  async rate(promptId: string, rating: number) {
    return apiClient.post(`/api/v1/prompts/${promptId}/rate`, { rating });
  },

  /**
   * Submit feedback for a prompt
   */
  async submitFeedback(promptId: string, data: PromptFeedbackRequest) {
    return apiClient.post(`/api/v1/prompts/${promptId}/feedback`, data);
  },

  /**
   * Get available chat commands
   */
  async listCommands() {
    return apiClient.get<CommandInfo[]>('/api/v1/prompts/commands/list');
  },
};

/**
 * Category Operations
 */
export const categoryApi = {
  /**
   * List all categories
   */
  async list() {
    return apiClient.get<PromptCategory[]>('/api/v1/prompts/categories/list');
  },

  /**
   * Create a new category
   */
  async create(data: CategoryCreateRequest) {
    return apiClient.post<PromptCategory>('/api/v1/prompts/categories', data);
  },
};
