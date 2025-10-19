import { useState, useCallback } from "react";
import type { ToastType } from "@/components/shared/Toast";

interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = Math.random().toString(36).substring(7);
    setToasts((prev) => [...prev, { id, message, type }]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  return {
    toasts,
    showToast,
    removeToast,
    success: useCallback((message: string) => showToast(message, "success"), [showToast]),
    error: useCallback((message: string) => showToast(message, "error"), [showToast]),
    info: useCallback((message: string) => showToast(message, "info"), [showToast]),
    warning: useCallback((message: string) => showToast(message, "warning"), [showToast]),
  };
}
