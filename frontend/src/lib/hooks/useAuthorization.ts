/**
 * Authorization Hooks
 * React hooks for permission checks, role management, policy management, and audit logs
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  checkPermission,
  bulkCheckPermissions,
  listRoles,
  getRole,
  createRole,
  updateRole,
  deleteRole,
  addRolePermission,
  listPolicies,
  createPolicy,
  updatePolicy,
  deletePolicy,
  queryAuditLogs,
  invalidateSessions,
  type Action,
  type Decision,
  type PermissionCheckRequest,
  type Role,
  type RoleDetail,
  type RoleCreateRequest,
  type RoleUpdateRequest,
  type ListRolesParams,
  type Policy,
  type PolicyCreateRequest,
  type PolicyUpdateRequest,
  type ListPoliciesParams,
  type AuditLog,
  type QueryAuditLogsParams,
  type PermissionCreateRequest,
} from '../api/authorization';

// ============================================================================
// Permission Check Hooks
// ============================================================================

/**
 * Hook to check if user has permission to perform action on resource
 * Returns: { allowed, loading, error, check }
 */
export function usePermission(
  resourceType: string,
  action: Action,
  resourceId?: string | null
) {
  const [allowed, setAllowed] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const check = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await checkPermission(resourceType, action, resourceId);
      setAllowed(result.decision === 'allow');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Permission check failed';
      setError(message);
      setAllowed(false);
      console.error('Permission check error:', err);
    } finally {
      setLoading(false);
    }
  }, [resourceType, action, resourceId]);

  useEffect(() => {
    check();
  }, [check]);

  return { allowed, loading, error, check };
}

/**
 * Hook to check multiple permissions in batch
 * Returns: { results, loading, error, check }
 */
export function useBulkPermissions(checks: PermissionCheckRequest[]) {
  const [results, setResults] = useState<Record<string, Decision>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const check = useCallback(async () => {
    if (checks.length === 0) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await bulkCheckPermissions(checks);
      const resultMap: Record<string, Decision> = {};

      checks.forEach((checkReq, index) => {
        const key = `${checkReq.resource_type}:${checkReq.resource_id || '*'}:${checkReq.action}`;
        resultMap[key] = response.results[index].decision;
      });

      setResults(resultMap);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Bulk permission check failed';
      setError(message);
      console.error('Bulk permission check error:', err);
    } finally {
      setLoading(false);
    }
  }, [JSON.stringify(checks)]);

  useEffect(() => {
    check();
  }, [check]);

  // Helper function to check if a specific permission is allowed
  const isAllowed = useCallback(
    (resourceType: string, action: Action, resourceId?: string | null) => {
      const key = `${resourceType}:${resourceId || '*'}:${action}`;
      return results[key] === 'allow';
    },
    [results]
  );

  return { results, loading, error, check, isAllowed };
}

// ============================================================================
// Role Management Hooks
// ============================================================================

/**
 * Hook to fetch and manage roles
 */
export function useRoles(params?: ListRolesParams) {
  const [roles, setRoles] = useState<Role[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRoles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listRoles(params);
      setRoles(response.roles);
      setTotal(response.total);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch roles';
      setError(message);
      console.error('Failed to fetch roles:', err);
    } finally {
      setLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchRoles();
  }, [fetchRoles]);

  const createNewRole = useCallback(
    async (data: RoleCreateRequest) => {
      try {
        const newRole = await createRole(data);
        setRoles((prev) => [...prev, newRole]);
        setTotal((prev) => prev + 1);
        return newRole;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create role';
        throw new Error(message);
      }
    },
    []
  );

  const updateExistingRole = useCallback(
    async (roleId: string, data: RoleUpdateRequest) => {
      try {
        const updatedRole = await updateRole(roleId, data);
        setRoles((prev) => prev.map((r) => (r.id === roleId ? updatedRole : r)));
        return updatedRole;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update role';
        throw new Error(message);
      }
    },
    []
  );

  const deleteExistingRole = useCallback(async (roleId: string) => {
    try {
      await deleteRole(roleId);
      setRoles((prev) => prev.filter((r) => r.id !== roleId));
      setTotal((prev) => prev - 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete role';
      throw new Error(message);
    }
  }, []);

  return {
    roles,
    total,
    loading,
    error,
    refetch: fetchRoles,
    createRole: createNewRole,
    updateRole: updateExistingRole,
    deleteRole: deleteExistingRole,
  };
}

/**
 * Hook to fetch detailed role information
 */
export function useRoleDetail(roleId: string | null) {
  const [role, setRole] = useState<RoleDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRoleDetail = useCallback(async () => {
    if (!roleId) {
      setRole(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await getRole(roleId);
      setRole(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch role details';
      setError(message);
      console.error('Failed to fetch role details:', err);
    } finally {
      setLoading(false);
    }
  }, [roleId]);

  useEffect(() => {
    fetchRoleDetail();
  }, [fetchRoleDetail]);

  const addPermission = useCallback(
    async (data: PermissionCreateRequest) => {
      if (!roleId) return;

      try {
        const newPermission = await addRolePermission(roleId, data);
        setRole((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            permissions: [...prev.permissions, newPermission],
          };
        });
        return newPermission;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to add permission';
        throw new Error(message);
      }
    },
    [roleId]
  );

  return {
    role,
    loading,
    error,
    refetch: fetchRoleDetail,
    addPermission,
  };
}

// ============================================================================
// Policy Management Hooks
// ============================================================================

/**
 * Hook to fetch and manage policies
 */
export function usePolicies(params?: ListPoliciesParams) {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPolicies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listPolicies(params);
      setPolicies(response.policies);
      setTotal(response.total);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch policies';
      setError(message);
      console.error('Failed to fetch policies:', err);
    } finally {
      setLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchPolicies();
  }, [fetchPolicies]);

  const createNewPolicy = useCallback(
    async (data: PolicyCreateRequest) => {
      try {
        const newPolicy = await createPolicy(data);
        setPolicies((prev) => [...prev, newPolicy]);
        setTotal((prev) => prev + 1);
        return newPolicy;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create policy';
        throw new Error(message);
      }
    },
    []
  );

  const updateExistingPolicy = useCallback(
    async (policyId: string, data: PolicyUpdateRequest) => {
      try {
        const updatedPolicy = await updatePolicy(policyId, data);
        setPolicies((prev) => prev.map((p) => (p.id === policyId ? updatedPolicy : p)));
        return updatedPolicy;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update policy';
        throw new Error(message);
      }
    },
    []
  );

  const deleteExistingPolicy = useCallback(async (policyId: string) => {
    try {
      await deletePolicy(policyId);
      setPolicies((prev) => prev.filter((p) => p.id !== policyId));
      setTotal((prev) => prev - 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete policy';
      throw new Error(message);
    }
  }, []);

  return {
    policies,
    total,
    loading,
    error,
    refetch: fetchPolicies,
    createPolicy: createNewPolicy,
    updatePolicy: updateExistingPolicy,
    deletePolicy: deleteExistingPolicy,
  };
}

// ============================================================================
// Audit Log Hooks
// ============================================================================

/**
 * Hook to query audit logs
 */
export function useAuditLogs(params?: QueryAuditLogsParams) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAuditLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await queryAuditLogs(params);
      setLogs(response.logs);
      setTotal(response.total);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch audit logs';
      setError(message);
      console.error('Failed to fetch audit logs:', err);
    } finally {
      setLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  return {
    logs,
    total,
    loading,
    error,
    refetch: fetchAuditLogs,
  };
}

// ============================================================================
// Session Management Hook
// ============================================================================

/**
 * Hook to invalidate user sessions (clear permission cache)
 */
export function useSessionInvalidation() {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const invalidate = useCallback(async (userId: string, reason?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await invalidateSessions({ user_id: userId, reason });
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to invalidate sessions';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    invalidate,
    loading,
    error,
  };
}
