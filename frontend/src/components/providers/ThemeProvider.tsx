'use client';

import { useEffect } from 'react';
import { useUIStore } from '@/lib/store';

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { theme } = useUIStore();

  useEffect(() => {
    const root = document.documentElement;

    const apply = () => {
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      const isDark = theme === 'dark' || (theme === 'system' && prefersDark);
      root.classList.toggle('dark', isDark);
    };

    apply();

    // Update on system change when using 'system'
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      if (theme === 'system') apply();
    };
    mql.addEventListener?.('change', handler);

    return () => {
      mql.removeEventListener?.('change', handler);
    };
  }, [theme]);

  return <>{children}</>;
}

