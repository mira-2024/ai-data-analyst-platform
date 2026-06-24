/**
 * Minimal toast notification system.
 * Uses a Zustand store so any component can fire toasts without prop drilling.
 */
import { useEffect } from "react";
import { create } from "zustand";
import { X, CheckCircle2, AlertCircle, Info, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
}

interface ToastStore {
  toasts: Toast[];
  add: (toast: Omit<Toast, "id">) => void;
  remove: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  add: (toast) => {
    const id = crypto.randomUUID();
    set((s) => ({ toasts: [...s.toasts, { ...toast, id }] }));
    const duration = toast.duration ?? 4_000;
    if (duration > 0) {
      setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), duration);
    }
  },
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

/** Helper functions for common toast types. */
export const toast = {
  success: (title: string, description?: string) =>
    useToastStore.getState().add({ type: "success", title, description }),
  error:   (title: string, description?: string) =>
    useToastStore.getState().add({ type: "error", title, description, duration: 6_000 }),
  info:    (title: string, description?: string) =>
    useToastStore.getState().add({ type: "info", title, description }),
  warning: (title: string, description?: string) =>
    useToastStore.getState().add({ type: "warning", title, description }),
};

const ICONS: Record<ToastType, typeof CheckCircle2> = {
  success: CheckCircle2,
  error:   AlertCircle,
  info:    Info,
  warning: AlertTriangle,
};

const STYLES: Record<ToastType, string> = {
  success: "border-success/30 bg-success/10",
  error:   "border-danger/30  bg-danger/10",
  info:    "border-info/30    bg-info/10",
  warning: "border-warning/30 bg-warning/10",
};

const ICON_STYLES: Record<ToastType, string> = {
  success: "text-success",
  error:   "text-danger",
  info:    "text-info",
  warning: "text-warning",
};

function ToastItem({ toast: t }: { toast: Toast }) {
  const remove = useToastStore((s) => s.remove);
  const Icon = ICONS[t.type];

  return (
    <div
      className={cn(
        "flex items-start gap-3 p-4 rounded-xl border shadow-card-hover",
        "backdrop-blur-sm bg-surface-2/90 animate-slide-up",
        STYLES[t.type]
      )}
      role="alert"
    >
      <Icon className={cn("w-4 h-4 mt-0.5 shrink-0", ICON_STYLES[t.type])} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-100">{t.title}</p>
        {t.description && (
          <p className="text-xs text-zinc-400 mt-0.5 leading-relaxed">{t.description}</p>
        )}
      </div>
      <button
        onClick={() => remove(t.id)}
        className="text-zinc-500 hover:text-zinc-300 transition-colors shrink-0"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);

  return (
    <div
      className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 w-80 pointer-events-none"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto">
          <ToastItem toast={t} />
        </div>
      ))}
    </div>
  );
}
