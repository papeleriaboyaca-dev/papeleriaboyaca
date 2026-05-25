import { create } from "zustand";

type ToastType = "success" | "error" | "info";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastState {
  toasts: Toast[];
  add: (message: string, type?: ToastType) => void;
  remove: (id: string) => void;
}

// Defensivo: si nos llega un objeto (p. ej. detail anidado del backend), lo
// aplastamos a string para que React no intente renderizar un objeto y crashear.
const coerceMessage = (v: unknown): string => {
  if (typeof v === "string") return v;
  if (v == null) return "";
  if (typeof v === "object") {
    const detail = (v as { detail?: unknown; message?: unknown }).detail
      ?? (v as { message?: unknown }).message;
    if (typeof detail === "string") return detail;
    try {
      return JSON.stringify(v);
    } catch {
      return String(v);
    }
  }
  return String(v);
};

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],

  add: (message, type = "info") => {
    const id = crypto.randomUUID();
    const safe = coerceMessage(message);
    set((s) => ({ toasts: [...s.toasts, { id, message: safe, type }] }));
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
    }, 3500);
  },

  remove: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

export const toast = {
  success: (msg: unknown) => useToastStore.getState().add(coerceMessage(msg), "success"),
  error: (msg: unknown) => useToastStore.getState().add(coerceMessage(msg), "error"),
  info: (msg: unknown) => useToastStore.getState().add(coerceMessage(msg), "info"),
};
