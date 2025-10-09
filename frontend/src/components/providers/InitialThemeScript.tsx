'use client';

export default function InitialThemeScript() {
  const code = `(() => {
    try {
      const raw = localStorage.getItem('ui-storage');
      let theme = 'system';
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          const state = parsed?.state ?? parsed;
          if (state && typeof state.theme === 'string') theme = state.theme;
        } catch {}
      }
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      const isDark = theme === 'dark' || (theme === 'system' && prefersDark);
      const root = document.documentElement;
      if (isDark) root.classList.add('dark'); else root.classList.remove('dark');
    } catch {}
  })();`;
  // eslint-disable-next-line @next/next/no-sync-scripts
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}

