import { usePathname } from 'next/navigation';
import { useMemo } from 'react';

export interface Breadcrumb {
  label: string;
  href: string;
  isActive: boolean;
}

const ROUTE_LABELS: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/flows': 'Flows',
  '/crews': 'Crews',
  '/agents': 'Agents',
  '/tools': 'Tools',
  '/observability': 'Observability',
  '/chat': 'Chat',
  '/executions': 'Executions',
  '/settings': 'Settings',
  '/profile': 'Profile',
};

export function useNavigation() {
  const pathname = usePathname();

  const breadcrumbs = useMemo<Breadcrumb[]>(() => {
    if (!pathname) return [];

    const segments = pathname.split('/').filter(Boolean);
    const crumbs: Breadcrumb[] = [];

    // Always add home/dashboard
    crumbs.push({
      label: 'Home',
      href: '/dashboard',
      isActive: pathname === '/dashboard',
    });

    let currentPath = '';

    segments.forEach((segment, index) => {
      currentPath += `/${segment}`;
      const isLast = index === segments.length - 1;

      // Skip numeric IDs and 'edit' segments, use parent context
      if (!isNaN(Number(segment))) {
        // For IDs, we'll add a contextual label later
        return;
      }

      if (segment === 'edit') {
        crumbs.push({
          label: 'Edit',
          href: currentPath,
          isActive: isLast,
        });
        return;
      }

      // Use predefined label or capitalize segment
      const label = ROUTE_LABELS[currentPath] || segment.charAt(0).toUpperCase() + segment.slice(1);

      crumbs.push({
        label,
        href: currentPath,
        isActive: isLast,
      });
    });

    return crumbs;
  }, [pathname]);

  const currentPage = useMemo(() => {
    if (!pathname) return 'Home';
    const lastBreadcrumb = breadcrumbs[breadcrumbs.length - 1];
    return lastBreadcrumb?.label || 'Home';
  }, [pathname, breadcrumbs]);

  const isActive = (path: string) => {
    return pathname?.startsWith(path);
  };

  return {
    breadcrumbs,
    currentPage,
    pathname,
    isActive,
  };
}
