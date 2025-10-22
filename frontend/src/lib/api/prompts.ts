/**
 * Prompt Registry API Client
 * Provides functions for managing prompts, categories, ratings, and feedback
 */

import { apiClient } from '../api-client';
import type { PromptTemplate, PromptCategory, ModelParameters, PromptVariable } from '../store';

// Normalize backend prompt 'variables' from object-map to array of { name, ... }
function normalizePromptVariables<T extends { variables?: any }>(prompt: T): T {
  if (prompt && prompt.variables && !Array.isArray(prompt.variables)) {
    const entries = Object.entries(prompt.variables as Record<string, any>);
    (prompt as any).variables = entries.map(([name, meta]) => ({ name, ...(meta || {}) }));
  }
  return prompt;
}

function normalizePromptListResponse(data: any): any {
  if (data && Array.isArray(data.prompts)) {
    data.prompts = data.prompts.map((p: any) => normalizePromptVariables(p));
  }
  return data;
}

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
  suggested_provider_id?: number;
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

// Category responses
export interface CategoryListResponse {
  categories: PromptCategory[];
  total: number;
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

    const res = await apiClient.get<any>(endpoint);
    if (res.data) res.data = normalizePromptListResponse(res.data);
    return res;
  },

  /**
   * Get a single prompt by ID
   */
  async get(promptId: string) {
    const res = await apiClient.get<PromptTemplate>(`/api/v1/prompts/${promptId}`);
    if (res.data) res.data = normalizePromptVariables(res.data as any);
    return res;
  },

  /**
   * Get a prompt by slug
   */
  async getBySlug(slug: string) {
    const res = await apiClient.get<PromptTemplate>(`/api/v1/prompts/by-slug?slug=${encodeURIComponent(slug)}`);
    if (res.data) res.data = normalizePromptVariables(res.data as any);
    return res;
  },

  /**
   * Create a new prompt
   */
  async create(data: PromptCreateRequest) {
    const res = await apiClient.post<PromptTemplate>('/api/v1/prompts', data);
    if (res.data) res.data = normalizePromptVariables(res.data as any);
    return res;
  },

  /**
   * Update an existing prompt
   */
  async update(promptId: string, data: PromptUpdateRequest) {
    const res = await apiClient.put<PromptTemplate>(`/api/v1/prompts/${promptId}`, data);
    if (res.data) res.data = normalizePromptVariables(res.data as any);
    return res;
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
    return apiClient.get<{ commands: CommandInfo[]; total: number }>('/api/v1/prompts/commands/list');
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
    // Backend returns: { categories: PromptCategory[], total: number }
    return apiClient.get<CategoryListResponse>('/api/v1/prompts/categories/list');
  },

  /**
   * Create a new category
   */
  async create(data: CategoryCreateRequest) {
    return apiClient.post<PromptCategory>('/api/v1/prompts/categories', data);
  },
};

/**
 * Suggestion Operations
 */
export interface PromptSuggestionItem {
  prompt_id: string;
  name: string;
  slug: string;
  description?: string;
  confidence: number;
  tags: string[];
  average_rating: number;
  total_executions: number;
  reason: string;
}

export interface SuggestionResponse {
  suggestions: PromptSuggestionItem[];
  context_type: string;
  total: number;
}

export const suggestionApi = {
  /**
   * Suggest prompts for agent configuration
   */
  async suggestForAgent(
    agentName: string,
    agentRole: string,
    agentGoal: string,
    agentBackstory?: string,
    limit: number = 5,
    minConfidence: number = 0.1
  ) {
    const params = new URLSearchParams({
      agent_name: agentName,
      agent_role: agentRole,
      agent_goal: agentGoal,
      limit: String(limit),
      min_confidence: String(minConfidence),
    });

    if (agentBackstory) {
      params.append('agent_backstory', agentBackstory);
    }

    return apiClient.post<SuggestionResponse>(
      `/api/v1/prompts/suggest/agent?${params.toString()}`,
      {}
    );
  },

  /**
   * Suggest prompts for crew configuration
   */
  async suggestForCrew(
    crewName: string,
    crewDescription: string,
    crewProcessType: string = 'sequential',
    limit: number = 5,
    minConfidence: number = 0.1
  ) {
    const params = new URLSearchParams({
      crew_name: crewName,
      crew_description: crewDescription,
      crew_process_type: crewProcessType,
      limit: String(limit),
      min_confidence: String(minConfidence),
    });

    return apiClient.post<SuggestionResponse>(
      `/api/v1/prompts/suggest/crew?${params.toString()}`,
      {}
    );
  },

  /**
   * Suggest prompts for task configuration
   */
  async suggestForTask(
    taskName: string,
    taskDescription: string,
    taskExpectedOutput?: string,
    limit: number = 5,
    minConfidence: number = 0.1
  ) {
    const params = new URLSearchParams({
      task_name: taskName,
      task_description: taskDescription,
      limit: String(limit),
      min_confidence: String(minConfidence),
    });

    if (taskExpectedOutput) {
      params.append('task_expected_output', taskExpectedOutput);
    }

    return apiClient.post<SuggestionResponse>(
      `/api/v1/prompts/suggest/task?${params.toString()}`,
      {}
    );
  },

  /**
   * Suggest prompts for flow configuration
   */
  async suggestForFlow(
    flowName: string,
    flowDescription: string,
    limit: number = 5,
    minConfidence: number = 0.1
  ) {
    const params = new URLSearchParams({
      flow_name: flowName,
      flow_description: flowDescription,
      limit: String(limit),
      min_confidence: String(minConfidence),
    });

    return apiClient.post<SuggestionResponse>(
      `/api/v1/prompts/suggest/flow?${params.toString()}`,
      {}
    );
  },
};
