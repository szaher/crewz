'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import { useAuthStore, useNotificationStore } from '@/lib/store';
import { apiClient } from '@/lib/api-client';
import NotificationsClient from '@/lib/notifications-client';
import { useToast } from '@/components/shared/Toast';

export default function NotificationsBell() {
  const ENABLED = (process.env.NEXT_PUBLIC_NOTIFICATIONS_ENABLED ?? 'false') === 'true';
  const { token } = useAuthStore();
  const { unreadCount, recent, pushNotification } = useNotificationStore();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const pathname = usePathname();

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!ENABLED) return;
    if (!token) return;
    // Load unread count initially
    (async () => {
      try {
        const res = await apiClient.get('/api/v1/notifications?unread_only=true&limit=1');
        if (res.data && typeof res.data.unread_count === 'number') {
          useNotificationStore.getState().setUnread(res.data.unread_count);
        }
      } catch {}
    })();
    const client = new NotificationsClient();
    client.connect(
      token,
      (evt) => {
        if (evt.type === 'connected') return;
        const ttype = (['success','error','warning','info'].includes(evt.type) ? evt.type : 'info') as any;
        pushNotification({ type: ttype, title: evt.title || 'Notification', message: evt.message, data: evt.data, created_at: evt.timestamp });
        // If it's a chat_response and user is on chat page, don't toast
        const isChatResponse = evt?.data?.kind === 'chat_response';
        const onChatPage = pathname?.startsWith('/chat');
        if (!(isChatResponse && onChatPage)) {
          showToast(evt.title || evt.message || 'New notification', ttype);
        }
      },
      () => {}
    );
    return () => client.disconnect();
  }, [ENABLED, token, pushNotification, showToast, pathname]);

  if (!ENABLED) return null;
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
        aria-label="Notifications"
      >
        <span className="text-xl">📥</span>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-600 text-white text-[10px] leading-none px-1.5 py-0.5 rounded-full">
            {unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden z-20">
          <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between gap-2">
            <span className="text-sm font-medium">Notifications</span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">{unreadCount} unread</span>
              <button
                className="text-xs px-2 py-1 border rounded hover:bg-gray-50 dark:hover:bg-gray-800"
                onClick={async () => {
                  try {
                    await apiClient.post('/api/v1/notifications/read-all', {});
                    useNotificationStore.getState().setUnread(0);
                    showToast('Marked all as read', 'success');
                  } catch {
                    showToast('Failed to mark as read', 'error');
                  }
                }}
              >
                Mark all read
              </button>
            </div>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {recent.length === 0 ? (
              <div className="p-4 text-sm text-gray-500">No notifications yet</div>
            ) : (
              recent.map((n, idx) => (
                <div key={idx} className="px-3 py-2 border-b border-gray-100 dark:border-gray-800">
                  <div className="text-sm font-medium">{n.title}</div>
                  {n.message && <div className="text-xs text-gray-600 dark:text-gray-400">{n.message}</div>}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
