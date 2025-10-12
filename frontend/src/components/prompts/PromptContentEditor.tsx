"use client";

import { useEffect, useMemo, useRef } from "react";

interface PromptContentEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  rows?: number;
}

// Escape HTML for safe rendering
function escapeHtml(str: string) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export default function PromptContentEditor({
  value,
  onChange,
  placeholder,
  className = "",
  rows = 10,
}: PromptContentEditorProps) {
  const preRef = useRef<HTMLPreElement | null>(null);
  const taRef = useRef<HTMLTextAreaElement | null>(null);

  // Very light highlighting for {variables}
  const highlightedHtml = useMemo(() => {
    const escaped = escapeHtml(value || "");
    // Highlight {variable_name}
    const withVars = escaped.replace(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g, (_m, varName) => {
      return `<span class=\"inline-block rounded px-1 border border-purple-200 bg-purple-50 text-purple-700\">{${varName}}</span>`;
    });
    // Ensure empty final line renders
    return withVars.endsWith("\n") ? withVars + " " : withVars;
  }, [value]);

  // Keep scroll positions in sync
  const handleScroll = () => {
    if (preRef.current && taRef.current) {
      preRef.current.scrollTop = taRef.current.scrollTop;
      preRef.current.scrollLeft = taRef.current.scrollLeft;
    }
  };

  const lineHeightRem = 1.25; // approx for text-sm
  const minHeightPx = Math.max(2, rows) * 16 * lineHeightRem; // rows * lineHeight * base font

  return (
    <div
      className={`relative w-full border border-gray-300 rounded-lg focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent bg-white ${className}`}
      style={{ minHeight: `${minHeightPx}px` }}
    >
      {/* Highlight layer */}
      <pre
        ref={preRef}
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 overflow-auto whitespace-pre-wrap break-words px-3 py-2 font-mono text-sm text-gray-900 bg-transparent"
        dangerouslySetInnerHTML={{ __html: highlightedHtml || "" }}
      />

      {/* Input layer */}
      <textarea
        ref={taRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onScroll={handleScroll}
        placeholder={placeholder}
        className="relative block w-full h-full resize-y px-3 py-2 font-mono text-sm bg-transparent outline-none border-0 text-transparent caret-blue-600 selection:bg-blue-100"
        style={{ minHeight: `${minHeightPx}px` }}
      />
    </div>
  );
}

