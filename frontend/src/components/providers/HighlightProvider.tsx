'use client';

import { useEffect } from 'react';

export function HighlightProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const styleId = 'hljs-style';
    const darkHref = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css';
    const lightHref = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-light.min.css';

    const ensureStyle = () => {
      let link = document.getElementById(styleId) as HTMLLinkElement | null;
      if (!link) {
        link = document.createElement('link');
        link.id = styleId;
        link.rel = 'stylesheet';
        document.head.appendChild(link);
      }
      const isDark = document.documentElement.classList.contains('dark');
      const nextHref = isDark ? darkHref : lightHref;
      if (link.href !== nextHref) link.href = nextHref;
    };

    // Inject highlight.js script if not present
    const scriptId = 'hljs-script';
    if (!document.getElementById(scriptId)) {
      const script = document.createElement('script');
      script.id = scriptId;
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js';
      script.defer = true;
      script.onload = () => {
        try {
          ensureStyle();
          (window as any).hljs?.highlightAll();
        } catch {}
      };
      document.body.appendChild(script);
    } else {
      try {
        ensureStyle();
        (window as any).hljs?.highlightAll();
      } catch {}
    }

    // apply on mount and on html class changes
    ensureStyle();
    const obs = new MutationObserver(() => ensureStyle());
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    return () => {
      obs.disconnect();
    };
  }, []);

  return <>{children}</>;
}
