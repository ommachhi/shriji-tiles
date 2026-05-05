import { useCallback, useState } from "react";

export function useToast() {
  const [toasts, setToasts] = useState([]);

  const showToast = useCallback((message, tone = "info", duration = 4000) => {
    const id = Math.random().toString(36).slice(2, 9);
    const toast = { id, message, tone };

    setToasts((prev) => [...prev, toast]);

    if (duration > 0) {
      const timer = setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);

      return () => clearTimeout(timer);
    }

    return () => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    };
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { toasts, showToast, dismissToast };
}
