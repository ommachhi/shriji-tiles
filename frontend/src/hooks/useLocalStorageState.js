import { useEffect, useState } from "react";

export function useLocalStorageState(key, initialValue) {
  const [state, setState] = useState(() => {
    if (typeof window === "undefined") {
      return typeof initialValue === "function" ? initialValue() : initialValue;
    }

    try {
      const raw = window.localStorage.getItem(key);
      if (raw !== null) {
        return JSON.parse(raw);
      }
    } catch (error) {
      console.warn("Local storage read failed", { key, error });
    }

    return typeof initialValue === "function" ? initialValue() : initialValue;
  });

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    try {
      window.localStorage.setItem(key, JSON.stringify(state));
    } catch (error) {
      console.warn("Local storage write failed", { key, error });
    }
  }, [key, state]);

  return [state, setState];
}
