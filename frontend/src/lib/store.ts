/**
 * Global state management using Zustand
 * Manages user auth, tenant context, and application data
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Auth State
interface User {
  id: number;
  email: string;
  full_name: string;
  tenant_id: number;
  role: 'admin' | 'member' | 'viewer';
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setAuth: (user, token) => set({ user, token, isAuthenticated: true }),
      clearAuth: () => set({ user: null, token: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage',
    }
  )
);

// Tenant State
interface Tenant {
  id: number;
  name: string;
  schema_name: string;
  is_active: boolean;
  settings: Record<string, any>;
}

interface TenantState {
  currentTenant: Tenant | null;
  setTenant: (tenant: Tenant) => void;
  clearTenant: () => void;
}

export const useTenantStore = create<TenantState>()(
  persist(
    (set) => ({
      currentTenant: null,
      setTenant: (tenant) => set({ currentTenant: tenant }),
      clearTenant: () => set({ currentTenant: null }),
    }),
    {
      name: 'tenant-storage',
    }
  )
);

// Flow State
interface Flow {
  id: number;
  name: string;
  description: string;
  version: string;
  is_active: boolean;
  nodes: any[];
  edges: any[];
  variables: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface FlowState {
  flows: Flow[];
  currentFlow: Flow | null;
  setFlows: (flows: Flow[]) => void;
  setCurrentFlow: (flow: Flow | null) => void;
  addFlow: (flow: Flow) => void;
  updateFlow: (id: number, flow: Partial<Flow>) => void;
  deleteFlow: (id: number) => void;
}

export const useFlowStore = create<FlowState>((set) => ({
  flows: [],
  currentFlow: null,
  setFlows: (flows) => set({ flows }),
  setCurrentFlow: (flow) => set({ currentFlow: flow }),
  addFlow: (flow) => set((state) => ({ flows: [...state.flows, flow] })),
  updateFlow: (id, updatedFlow) =>
    set((state) => ({
      flows: state.flows.map((f) => (f.id === id ? { ...f, ...updatedFlow } : f)),
      currentFlow: state.currentFlow?.id === id ? { ...state.currentFlow, ...updatedFlow } : state.currentFlow,
    })),
  deleteFlow: (id) =>
    set((state) => ({
      flows: state.flows.filter((f) => f.id !== id),
      currentFlow: state.currentFlow?.id === id ? null : state.currentFlow,
    })),
}));

// Agent State
interface Agent {
  id: number;
  name: string;
  role: string;
  goal: string;
  backstory: string;

  // LLM configuration
  llm_provider_id: number;
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

interface AgentState {
  agents: Agent[];
  setAgents: (agents: Agent[]) => void;
  addAgent: (agent: Agent) => void;
  updateAgent: (id: number, agent: Partial<Agent>) => void;
  deleteAgent: (id: number) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  agents: [],
  setAgents: (agents) => set({ agents }),
  addAgent: (agent) => set((state) => ({ agents: [...state.agents, agent] })),
  updateAgent: (id, updatedAgent) =>
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, ...updatedAgent } : a)),
    })),
  deleteAgent: (id) =>
    set((state) => ({
      agents: state.agents.filter((a) => a.id !== id),
    })),
}));

// Crew State
interface Crew {
  id: number;
  name: string;
  description: string;
  process_type: 'sequential' | 'hierarchical' | 'consensus';
  agent_ids: number[];
  task_count?: number;
  config: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface CrewState {
  crews: Crew[];
  setCrews: (crews: Crew[]) => void;
  addCrew: (crew: Crew) => void;
  updateCrew: (id: number, crew: Partial<Crew>) => void;
  deleteCrew: (id: number) => void;
}

export const useCrewStore = create<CrewState>((set) => ({
  crews: [],
  setCrews: (crews) => set({ crews }),
  addCrew: (crew) => set((state) => ({ crews: [...state.crews, crew] })),
  updateCrew: (id, updatedCrew) =>
    set((state) => ({
      crews: state.crews.map((c) => (c.id === id ? { ...c, ...updatedCrew } : c)),
    })),
  deleteCrew: (id) =>
    set((state) => ({
      crews: state.crews.filter((c) => c.id !== id),
    })),
}));

// Tool State
interface Tool {
  id: number;
  name: string;
  description: string;
  tool_type: 'function' | 'api' | 'docker';
  docker_image?: string;
  docker_command?: string;
  function_code?: string;
  api_endpoint?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ToolState {
  tools: Tool[];
  setTools: (tools: Tool[]) => void;
  addTool: (tool: Tool) => void;
  updateTool: (id: number, tool: Partial<Tool>) => void;
  deleteTool: (id: number) => void;
}

export const useToolStore = create<ToolState>((set) => ({
  tools: [],
  setTools: (tools) => set({ tools }),
  addTool: (tool) => set((state) => ({ tools: [...state.tools, tool] })),
  updateTool: (id, updatedTool) =>
    set((state) => ({
      tools: state.tools.map((t) => (t.id === id ? { ...t, ...updatedTool } : t)),
    })),
  deleteTool: (id) =>
    set((state) => ({
      tools: state.tools.filter((t) => t.id !== id),
    })),
}));

// Execution State
interface Execution {
  id: number;
  execution_type: 'flow' | 'crew' | 'agent';
  flow_id?: number;
  crew_id?: number;
  agent_id?: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  input_data: Record<string, any>;
  output_data?: Record<string, any>;
  error?: string;
  created_at: string;
  updated_at: string;
}

interface ExecutionState {
  executions: Execution[];
  currentExecution: Execution | null;
  setExecutions: (executions: Execution[]) => void;
  setCurrentExecution: (execution: Execution | null) => void;
  addExecution: (execution: Execution) => void;
  updateExecution: (id: number, execution: Partial<Execution>) => void;
}

export const useExecutionStore = create<ExecutionState>((set) => ({
  executions: [],
  currentExecution: null,
  setExecutions: (executions) => set({ executions }),
  setCurrentExecution: (execution) => set({ currentExecution: execution }),
  addExecution: (execution) => set((state) => ({ executions: [...state.executions, execution] })),
  updateExecution: (id, updatedExecution) =>
    set((state) => ({
      executions: state.executions.map((e) => (e.id === id ? { ...e, ...updatedExecution } : e)),
      currentExecution: state.currentExecution?.id === id ? { ...state.currentExecution, ...updatedExecution } : state.currentExecution,
    })),
}));

// UI State
interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'system',
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'ui-storage',
    }
  )
);
