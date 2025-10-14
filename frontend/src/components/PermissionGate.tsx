/**
 * Permission Gate Component
 * Conditionally renders children based on user permissions
 */

import { usePermission } from '../lib/hooks/useAuthorization';
import type { Action } from '../lib/api/authorization';

interface PermissionGateProps {
  /** Resource type (e.g., 'crew', 'flow', 'agent') */
  resourceType: string;
  /** Action to check (read, write, execute, delete, *) */
  action: Action;
  /** Optional specific resource ID */
  resourceId?: string | null;
  /** Content to render if permission is granted */
  children: React.ReactNode;
  /** Optional content to render if permission is denied */
  fallback?: React.ReactNode;
  /** Optional loading component */
  loadingComponent?: React.ReactNode;
  /** If true, shows fallback/nothing instead of children when denied */
  hideOnDenied?: boolean;
}

/**
 * Renders children only if user has permission to perform action on resource
 *
 * @example
 * ```tsx
 * <PermissionGate resourceType="crew" action="write" resourceId={crewId}>
 *   <Button onClick={handleEdit}>Edit Crew</Button>
 * </PermissionGate>
 * ```
 *
 * @example With fallback
 * ```tsx
 * <PermissionGate
 *   resourceType="flow"
 *   action="execute"
 *   fallback={<div>You don't have permission to execute this flow</div>}
 * >
 *   <Button onClick={handleExecute}>Execute Flow</Button>
 * </PermissionGate>
 * ```
 */
export function PermissionGate({
  resourceType,
  action,
  resourceId,
  children,
  fallback = null,
  loadingComponent = null,
  hideOnDenied = false,
}: PermissionGateProps) {
  const { allowed, loading } = usePermission(resourceType, action, resourceId);

  if (loading) {
    return <>{loadingComponent}</>;
  }

  if (!allowed) {
    return hideOnDenied ? null : <>{fallback}</>;
  }

  return <>{children}</>;
}

/**
 * Higher-order component version of PermissionGate
 * Wraps a component and only renders if user has permission
 *
 * @example
 * ```tsx
 * const ProtectedEditButton = withPermission(
 *   ({ onClick }) => <Button onClick={onClick}>Edit</Button>,
 *   'crew',
 *   'write'
 * );
 *
 * // Usage
 * <ProtectedEditButton onClick={handleEdit} />
 * ```
 */
export function withPermission<P extends object>(
  Component: React.ComponentType<P>,
  resourceType: string,
  action: Action,
  getResourceId?: (props: P) => string | null | undefined
) {
  return function PermissionWrappedComponent(props: P) {
    const resourceId = getResourceId ? getResourceId(props) : undefined;

    return (
      <PermissionGate resourceType={resourceType} action={action} resourceId={resourceId}>
        <Component {...props} />
      </PermissionGate>
    );
  };
}
