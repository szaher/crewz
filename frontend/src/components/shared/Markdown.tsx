'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

interface MarkdownProps {
  content: string;
}

declare global {
  interface Window { marked?: any; DOMPurify?: any; hljs?: any }
}

export default function Markdown({ content }: MarkdownProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const ensure = async () => {
      if (!window.marked) {
        await new Promise<void>((resolve) => {
          const s = document.createElement('script');
          s.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
          s.async = true;
          s.onload = () => resolve();
          document.body.appendChild(s);
        });
      }
      if (!window.DOMPurify) {
        await new Promise<void>((resolve) => {
          const s = document.createElement('script');
          s.src = 'https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.2/purify.min.js';
          s.async = true;
          s.onload = () => resolve();
          document.body.appendChild(s);
        });
      }
      try { window.marked?.setOptions?.({ gfm: true, breaks: true, headerIds: true, mangle: false }); } catch {}
      setReady(true);
    };
    void ensure();
  }, []);

  const html = useMemo(() => {
    if (!content) return '';
    try {
      const rawHtml = window.marked ? window.marked.parse(content) : content;
      const clean = window.DOMPurify ? window.DOMPurify.sanitize(rawHtml, {
        ALLOWED_ATTR: ['href','target','rel','src','alt','class','title','id','name','lang'],
      }) : rawHtml;
      return clean;
    } catch {
      return content;
    }
  }, [content, ready]);

  useEffect(() => {
    try {
      if (window.hljs && containerRef.current) {
        containerRef.current.querySelectorAll('pre code').forEach((el) => {
          window.hljs.highlightElement(el as HTMLElement);
        });
      }
      // Inject copy buttons on code blocks
      if (containerRef.current) {
        const pres = Array.from(containerRef.current.querySelectorAll('pre')) as HTMLPreElement[];
        pres.forEach((pre) => {
          // Avoid duplicating buttons
          if ((pre as any)._hasCopyButton) return;
          (pre as any)._hasCopyButton = true;
          pre.style.position = pre.style.position || 'relative';

          const btn = document.createElement('button');
          btn.type = 'button';
          btn.textContent = 'Copy';
          btn.className = [
            'absolute', 'top-2', 'right-2', 'px-2', 'py-1', 'text-xs', 'rounded',
            'bg-gray-200', 'hover:bg-gray-300', 'text-gray-800',
            'dark:bg-gray-700', 'dark:hover:bg-gray-600', 'dark:text-gray-100',
            'transition-colors'
          ].join(' ');
          btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const code = pre.querySelector('code');
            const text = code ? (code as HTMLElement).innerText : pre.innerText;
            try {
              if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
              } else {
                const ta = document.createElement('textarea');
                ta.value = text;
                ta.style.position = 'fixed';
                ta.style.opacity = '0';
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
              }
              const prev = btn.textContent;
              btn.textContent = 'Copied!';
              setTimeout(() => { btn.textContent = prev || 'Copy'; }, 1200);
            } catch {
              const prev = btn.textContent;
              btn.textContent = 'Failed';
              setTimeout(() => { btn.textContent = prev || 'Copy'; }, 1200);
            }
          });
          pre.appendChild(btn);
        });
      }
    } catch {}
  }, [html]);

  if (!content) return null;
  return <div ref={containerRef} className="prose prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: html }} />;
}
