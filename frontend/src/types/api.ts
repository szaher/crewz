/**
 * TypeScript type definitions for API requests and responses
 * Based on backend OpenAPI specification
 */

// ============================================================================
// Authentication Types
// ============================================================================

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  tenant_name?: string;
}

export interface RegisterResponse {
  user: User;
  tenant: Tenant;
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
}

// ============================================================================
// Core Entity Types
// ============================================================================

export interface User {
  id: string; // UUID
  email: string;
  full_name: string;
  tenant_id: string; // UUID
  role: 'admin' | 'member' | 'viewer';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Tenant {
  id: string; // UUID
  name: string;
  schema_name: string;
  is_active: boolean;
  settings: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Flow Types
// ============================================================================

export interface FlowNode {
  id: string;
  type: 'agent' | 'crew' | 'tool' | 'flow' | 'router' | 'input' | 'output' | 'decision';
  position: { x: number; y: number };
  data: {
    label: string;
    description?: string;
    // Agent node
    agent_id?: string; // UUID
    task_description?: string;
    // Crew node
    crew_id?: string; // UUID
    // Tool node
    tool_id?: string; // UUID
    // Flow node (hierarchical)
    flow_id?: string; // UUID
    // Router node (conditional)
    condition?: string;
    router_paths?: Array<{ condition: string; next_step_id?: string }>;
    // Common
    config?: Record<string, any>;
  };
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  type?: 'default' | 'conditional';
  data?: {
    condition?: string;
    label?: string;
  };
}

export interface Flow {
  id: string; // UUID
  tenant_id: string; // UUID
  name: string;
  description: string;
  version: string;
  is_active: boolean;
  nodes: FlowNode[];
  edges: FlowEdge[];
  variables: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface FlowCreate {
  name: string;
  description: string;
  version?: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
  variables?: Record<string, any>;
}

export interface FlowUpdate {
  name?: string;
  description?: string;
  version?: string;
  is_active?: boolean;
  nodes?: FlowNode[];
  edges?: FlowEdge[];
  variables?: Record<string, any>;
}

export interface FlowListResponse {
  flows: Flow[];
  total: number;
  page: number;
  page_size: number;
}

export interface FlowResponse {
  flow: Flow;
}

export interface FlowValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

// ============================================================================
// Agent Types
// ============================================================================

export interface LLMConfig {
  provider: string;
  model: string;
  temperature?: number;
  max_tokens?: number;
  api_key?: string;
  base_url?: string;
  extra_params?: Record<string, any>;
}

export interface Agent {
  id: string; // UUID
  name: string;
  role: string;
  goal: string;
  backstory: string;

  // LLM configuration
  llm_provider_id: string; // UUID
  temperature: number;
  max_tokens?: number;

  // Agent behavior
  allow_delegation: boolean;
  verbose: boolean;
  cache: boolean;
  max_iter: number;
  max_rpm?: number;
  max_execution_time?: number;

  // Advanced features
  allow_code_execution: boolean;
  respect_context_window: boolean;
  max_retry_limit: number;

  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  role: string;
  goal: string;
  backstory: string;

  // LLM configuration
  llm_provider_id: string; // UUID
  temperature?: number;
  max_tokens?: number;

  // Agent behavior
  allow_delegation?: boolean;
  verbose?: boolean;
  cache?: boolean;
  max_iter?: number;
  max_rpm?: number;
  max_execution_time?: number;

  // Advanced features
  allow_code_execution?: boolean;
  respect_context_window?: boolean;
  max_retry_limit?: number;

  // Tools
  tool_ids?: number[];
}

export interface AgentUpdate {
  name?: string;
  role?: string;
  goal?: string;
  backstory?: string;

  // LLM configuration
  llm_provider_id?: number;
  temperature?: number;
  max_tokens?: number;

  // Agent behavior
  allow_delegation?: boolean;
  verbose?: boolean;
  cache?: boolean;
  max_iter?: number;
  max_rpm?: number;
  max_execution_time?: number;

  // Advanced features
  allow_code_execution?: boolean;
  respect_context_window?: boolean;
  max_retry_limit?: number;

  // Tools
  tool_ids?: number[];
}

export interface AgentListResponse {
  agents: Agent[];
  total: number;
  page: number;
  page_size: number;
}

export interface AgentResponse {
  agent: Agent;
}

// ============================================================================
// Crew Types
// ============================================================================

export interface Crew {
  id: string; // UUID
  tenant_id: string; // UUID
  name: string;
  description: string;
  process_type: 'sequential' | 'hierarchical' | 'consensus';
  agent_ids: string[]; // UUIDs
  task_delegation_enabled: boolean;
  verbose: boolean;
  config: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CrewCreate {
  name: string;
  description: string;
  process_type: 'sequential' | 'hierarchical' | 'consensus';
  agent_ids: string[]; // UUIDs
  task_ids?: string[]; // UUIDs
  task_delegation_enabled?: boolean;
  verbose?: boolean;
  config?: Record<string, any>;
}

export interface CrewUpdate {
  name?: string;
  description?: string;
  process_type?: 'sequential' | 'hierarchical' | 'consensus';
  agent_ids?: string[]; // UUIDs
  task_ids?: string[]; // UUIDs
  task_delegation_enabled?: boolean;
  verbose?: boolean;
  config?: Record<string, any>;
  is_active?: boolean;
}

export interface CrewListResponse {
  crews: Crew[];
  total: number;
  page: number;
  page_size: number;
}

export interface CrewResponse {
  crew: Crew;
}

// ============================================================================
// Tool Types
// ============================================================================

export interface Tool {
  id: string; // UUID
  name: string;
  description: string;
  tool_type: 'builtin' | 'custom' | 'docker';
  code?: string;
  docker_image?: string;
  docker_command?: string;
  schema: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ToolCreate {
  name: string;
  description: string;
  tool_type: 'builtin' | 'custom' | 'docker';
  code?: string;
  docker_image?: string;
  docker_command?: string;
  schema?: Record<string, any>;
}

export interface ToolUpdate {
  name?: string;
  description?: string;
  docker_image?: string;
  docker_command?: string;
  function_code?: string;
  api_endpoint?: string;
  api_method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  api_headers?: Record<string, string>;
  input_schema?: Record<string, any>;
  output_schema?: Record<string, any>;
  is_active?: boolean;
}

export interface ToolListResponse {
  tools: Tool[];
  total: number;
  page: number;
  page_size: number;
}

export interface ToolResponse {
  tool: Tool;
}

export interface ToolExecuteRequest {
  input_data: string;
}

export interface ToolExecuteResponse {
  output: string;
  execution_time_ms: number;
}

// ============================================================================
// Execution Types
// ============================================================================

export interface Execution {
  id: string; // UUID
  tenant_id: string; // UUID
  execution_type: 'flow' | 'crew' | 'agent' | 'tool' | 'task';
  flow_id?: string; // UUID
  crew_id?: string; // UUID
  agent_id?: string; // UUID
  tool_id?: string; // UUID
  task_id?: string; // UUID
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  input_data: Record<string, any>;
  output_data?: Record<string, any>;
  error?: string;
  execution_time_ms?: number;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ExecutionCreate {
  execution_type: 'flow' | 'crew' | 'agent' | 'tool' | 'task';
  flow_id?: string; // UUID
  crew_id?: string; // UUID
  agent_id?: string; // UUID
  tool_id?: string; // UUID
  task_id?: string; // UUID
  input_data: Record<string, any>;
}

export interface ExecutionListResponse {
  executions: Execution[];
  total: number;
  page: number;
  page_size: number;
}

export interface ExecutionResponse {
  execution: Execution;
}

export interface ExecutionEvent {
  type: 'connected' | 'execution_started' | 'node_started' | 'node_completed' | 'node_failed' | 'execution_completed' | 'execution_failed' | 'execution_cancelled' | 'error';
  execution_id?: string; // UUID
  node_id?: string;
  node_type?: string;
  output?: any;
  error?: string;
  timestamp?: string;
  data?: any;
}

// ============================================================================
// Chat Types
// ============================================================================

export interface ChatSession {
  id: string; // UUID
  tenant_id: string; // UUID
  agent_id?: string; // UUID
  crew_id?: string; // UUID
  name: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string; // UUID
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface ChatSessionCreate {
  agent_id?: string; // UUID
  crew_id?: string; // UUID
  name: string;
  metadata?: Record<string, any>;
}

export interface ChatSessionListResponse {
  sessions: ChatSession[];
  total: number;
  page: number;
  page_size: number;
}

export interface ChatSessionResponse {
  session: ChatSession;
}

export interface ChatMessageListResponse {
  messages: ChatMessage[];
  total: number;
  page: number;
  page_size: number;
}

export interface SendMessageRequest {
  content: string;
}

export interface SendMessageResponse {
  message: ChatMessage;
}

// ============================================================================
// WebSocket Event Types
// ============================================================================

export interface ChatEvent {
  type: 'message' | 'typing' | 'error';
  data: ChatMessage | { typing: boolean } | { error: string };
}

export interface TypingEvent {
  session_id: string; // UUID
  typing: boolean;
}

// ============================================================================
// Pagination & Filtering
// ============================================================================

export interface PaginationParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface FilterParams {
  is_active?: boolean;
  search?: string;
  created_after?: string;
  created_before?: string;
}

// ============================================================================
// Error Response
// ============================================================================

export interface ErrorResponse {
  detail: string;
  status_code: number;
}
