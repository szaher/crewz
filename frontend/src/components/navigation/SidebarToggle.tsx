'use client';

import { useUIStore } from '@/lib/store';

export default function SidebarToggle() {
  const { sidebarOpen, toggleSidebar } = useUIStore();

  return (
    <button
      type="button"
      onClick={toggleSidebar}
      className="inline-flex items-center justify-center p-1 text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
      aria-pressed={sidebarOpen}
      aria-label={sidebarOpen ? 'Hide menu' : 'Show menu'}
      title={sidebarOpen ? 'Hide menu' : 'Show menu'}
    >
      {sidebarOpen ? (
        // Icon: collapse (double chevron left)
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-5 h-5"
          aria-hidden
        >
          <path d="M13.5 19.5l-7.5-7.5 7.5-7.5" />
          <path d="M19.5 19.5l-7.5-7.5 7.5-7.5" />
        </svg>
      ) : (
        // Icon: open / hamburger
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
          <path d="M3.75 6.75A.75.75 0 0 1 4.5 6h15a.75.75 0 0 1 0 1.5h-15a.75.75 0 0 1-.75-.75zm0 5.25a.75.75 0 0 1 .75-.75h15a.75.75 0 0 1 0 1.5h-15a.75.75 0 0 1-.75-.75zm0 5.25a.75.75 0 0 1 .75-.75h15a.75.75 0 0 1 0 1.5h-15a.75.75 0 0 1-.75-.75z"/>
        </svg>
      )}
    </button>
  );
}
