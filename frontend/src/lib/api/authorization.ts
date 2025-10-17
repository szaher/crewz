/**
 * Authorization API Client
 * Provides functions for permission checks, role management, policy management, and audit logs
 */

import { apiClient } from '../api-client';

// ============================================================================
// Types
// ============================================================================

export type Action = 'read' | 'write' | 'execute' | 'delete' | '*';
export type Decision = 'allow' | 'deny';
export type Effect = 'allow' | 'deny';
export type PolicyScope = 'tenant' | 'user';

export interface PermissionCheckRequest {
  resource_type: string;
  resource_id?: string | null;
  action: Action;
}

export interface PermissionCheckResponse {
  decision: Decision;
  reason: string;
  latency_ms: number;
}

export interface BulkCheckRequest {
  checks: PermissionCheckRequest[];
}

export interface BulkCheckResponse {
  results: PermissionCheckResponse[];
  total_latency_ms: number;
}

// Role Types
export interface Role {
  id: string;
  tenant_id: string | null;
  name: string;
  slug: string;
  description: string | null;
  is_system_role: boolean;
  is_default: boolean;
  priority: number;
  created_at: string;
}

export interface RoleDetail extends Role {
  permissions: Permission[];
  user_count: number;
}

export interface RoleCreateRequest {
  name: string;
  slug: string;
  description?: string;
  is_default?: boolean;
  priority?: number;
}

export interface RoleUpdateRequest {
  name?: string;
  description?: string;
  is_default?: boolean;
  priority?: number;
}

export interface RoleListResponse {
  roles: Role[];
  total: number;
  page: number;
  page_size: number;
}

// Permission Types
export interface Permission {
  id: string;
  tenant_id: string;
  subject_type: 'user' | 'role';
  subject_id: string;
  resource_type: string;
  resource_id: string | null;
  action: Action;
  effect: Effect;
  conditions: Record<string, any> | null;
  created_at: string;
}

export interface PermissionCreateRequest {
  resource_type: string;
  resource_id?: string | null;
  action: Action;
  effect?: Effect;
  conditions?: Record<string, any>;
}

// Policy Types
export interface Policy {
  id: string;
  tenant_id: string;
  scope: PolicyScope;
  scope_id: string | null;
  name: string;
  description: string | null;
  resource_pattern: string;
  action_pattern: string;
  effect: Effect;
  conditions: Record<string, any> | null;
  priority: number;
  is_active: boolean;
  created_at: string;
}

export interface PolicyCreateRequest {
  scope: PolicyScope;
  scope_id?: string | null;
  name: string;
  description?: string;
  resource_pattern: string;
  action_pattern: string;
  effect: Effect;
  conditions?: Record<string, any>;
  priority?: number;
}

export interface PolicyUpdateRequest {
  name?: string;
  description?: string;
  resource_pattern?: string;
  action_pattern?: string;
  effect?: Effect;
  conditions?: Record<string, any>;
  priority?: number;
  is_active?: boolean;
}

export interface PolicyListResponse {
  policies: Policy[];
  total: number;
}

// Audit Log Types
export interface AuditLog {
  id: string;
  tenant_id: string;
  user_id: string;
  resource_type: string;
  resource_id: string | null;
  action: string;
  decision: Decision;
  reason: string;
  latency_ms: number;
  ip_address: string | null;
  user_agent: string | null;
  timestamp: string;
}

export interface AuditLogListResponse {
  logs: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface InvalidateSessionRequest {
  user_id: string;
  reason?: string;
}

export interface InvalidateSessionResponse {
  invalidated_sessions: number;
  message: string;
}

// ============================================================================
// Permission Check Functions
// ============================================================================

/**
 * Check if user has permission to perform action on resource
 */
export async function checkPermission(
  resourceType: string,
  action: Action,
  resourceId?: string | null
): Promise<PermissionCheckResponse> {
  const response = await apiClient.request<PermissionCheckResponse>('/api/v1/authz/check', {
    method: 'POST',
    body: {
      resource_type: resourceType,
      resource_id: resourceId,
      action,
    },
  });

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}

/**
 * Check multiple permissions in batch (max 20)
 */
export async function bulkCheckPermissions(
  checks: PermissionCheckRequest[]
): Promise<BulkCheckResponse> {
  if (checks.length > 20) {
    throw new Error('Maximum 20 checks allowed per request');
  }

  const response = await apiClient.request<BulkCheckResponse>('/api/v1/authz/bulk-check', {
    method: 'POST',
    body: { checks },
  });

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}

// ============================================================================
// Role Management Functions
// ============================================================================

export interface ListRolesParams {
  include_system?: boolean;
  page?: number;
  page_size?: number;
}

/**
 * List roles for tenant
 */
export async function listRoles(params?: ListRolesParams): Promise<RoleListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.include_system !== undefined) queryParams.set('include_system', String(params.include_system));
  if (params?.page) queryParams.set('page', String(params.page));
  if (params?.page_size) queryParams.set('page_size', String(params.page_size));

  const url = `/api/v1/authz/roles${queryParams.toString() ? `?${queryParams}` : ''}`;
  const response = await apiClient.request<RoleListResponse>(url);

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}

/**
 * Get role details with permissions and user count
 */
export async function getRole(roleId: string): Promise<RoleDetail> {
  const response = await apiClient.request<RoleDetail>(`/api/v1/authz/roles/${roleId}`);

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}

/**
 * Create custom role
 */
export async function createRole(data: RoleCreateRequest): Promise<Role> {
  const response = await apiClient.request<Role>('/api/v1/authz/roles', {
    method: 'POST',
    body: data,
  });

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}

/**
 * Update role
 */
export async function updateRole(roleId: string, data: RoleUpdateRequest): Promise<Role> {
  const response = await apiClient.request<Role>(`/api/v1/authz/roles/${roleId}`, {
    method: 'PUT',
    body: data,
  });

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}

/**
 * Delete role
 */
export async function deleteRole(roleId: string): Promise<void> {
  const response = await apiClient.request<void>(`/api/v1/authz/roles/${roleId}`, {
    method: 'DELETE',
  });

  if (response.error) {
    throw new Error(response.error);
  }
}

/**
 * Add permission to role
 */
export async function addRolePermission(
  roleId: string,
  data: PermissionCreateRequest
): Promise<Permission> {
  const response = await apiClient.request<Permission>(
    `/api/v1/authz/roles/${roleId}/permissions`,
    {
      method: 'POST',
      body: data,
    }
  );

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}

// ============================================================================
// Policy Management Functions
// ============================================================================

export interface ListPoliciesParams {
  scope?: 'tenant' | 'user' | 'all';
  active_only?: boolean;
  page?: number;
  page_size?: number;
}

/**
 * List policies
 */
export async function listPolicies(params?: ListPoliciesParams): Promise<PolicyListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.scope) queryParams.set('scope', params.scope);
  if (params?.active_only !== undefined) queryParams.set('active_only', String(params.active_only));
  if (params?.page) queryParams.set('page', String(params.page));
  if (params?.page_size) queryParams.set('page_size', String(params.page_size));

  const url = `/api/v1/authz/policies${queryParams.toString() ? `?${queryParams}` : ''}`;
  const response = await apiClient.request<PolicyListResponse>(url);

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}

/**
 * Create policy
 */
export async function createPolicy(data: PolicyCreateRequest): Promise<Policy> {
  const response = await apiClient.request<Policy>('/api/v1/authz/policies', {
    method: 'POST',
    body: data,
  });

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}

/**
 * Update policy
 */
export async function updatePolicy(policyId: string, data: PolicyUpdateRequest): Promise<Policy> {
  const response = await apiClient.request<Policy>(`/api/v1/authz/policies/${policyId}`, {
    method: 'PUT',
    body: data,
  });

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}

/**
 * Delete policy
 */
export async function deletePolicy(policyId: string): Promise<void> {
  const response = await apiClient.request<void>(`/api/v1/authz/policies/${policyId}`, {
    method: 'DELETE',
  });

  if (response.error) {
    throw new Error(response.error);
  }
}

// ============================================================================
// Audit Log Functions
// ============================================================================

export interface QueryAuditLogsParams {
  user_id?: string;
  resource_type?: string;
  decision?: Decision;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}

/**
 * Query authorization audit logs
 */
export async function queryAuditLogs(params?: QueryAuditLogsParams): Promise<AuditLogListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.user_id) queryParams.set('user_id', params.user_id);
  if (params?.resource_type) queryParams.set('resource_type', params.resource_type);
  if (params?.decision) queryParams.set('decision', params.decision);
  if (params?.start_time) queryParams.set('start_time', params.start_time);
  if (params?.end_time) queryParams.set('end_time', params.end_time);
  if (params?.page) queryParams.set('page', String(params.page));
  if (params?.page_size) queryParams.set('page_size', String(params.page_size));

  const url = `/api/v1/authz/audit${queryParams.toString() ? `?${queryParams}` : ''}`;
  const response = await apiClient.request<AuditLogListResponse>(url);

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}

// ============================================================================
// Session Management Functions
// ============================================================================

/**
 * Invalidate user sessions (clear permission cache)
 */
export async function invalidateSessions(
  data: InvalidateSessionRequest
): Promise<InvalidateSessionResponse> {
  const response = await apiClient.request<InvalidateSessionResponse>(
    '/api/v1/authz/sessions/invalidate',
    {
      method: 'POST',
      body: data,
    }
  );

  if (response.error) {
    throw new Error(response.error);
  }

  return response.data!;
}
