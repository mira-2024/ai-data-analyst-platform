import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

/** Merge Tailwind classes without conflicts. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a bytes count into a human-readable string. */
export function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

/** Format a number with compact notation (1.2K, 3.4M etc.) */
export function formatNumber(n: number, decimals = 1): string {
  if (n === null || n === undefined) return "—";
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(decimals)}M`;
  if (Math.abs(n) >= 1_000)     return `${(n / 1_000).toFixed(decimals)}K`;
  return n.toLocaleString();
}

/** Relative time (e.g. "3 minutes ago") */
export function timeAgo(dateStr: string): string {
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
  } catch {
    return dateStr;
  }
}

/** ISO timestamp → readable date */
export function formatDate(dateStr: string, fmt = "MMM d, yyyy · HH:mm"): string {
  try {
    return format(new Date(dateStr), fmt);
  } catch {
    return dateStr;
  }
}

/** Duration in ms → "1m 23s" */
export function formatDuration(ms: number): string {
  if (ms < 1_000) return `${ms}ms`;
  const s = Math.floor(ms / 1_000);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${rem}s`;
}

/** Truncate a string to N characters with ellipsis. */
export function truncate(str: string, n: number): string {
  return str.length > n ? `${str.slice(0, n)}…` : str;
}

/** Clamp a value between min and max. */
export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/** Map a status string to a Tailwind badge class. */
export function statusBadgeClass(status: string): string {
  switch (status) {
    case "running":   return "badge-running";
    case "completed": return "badge-completed";
    case "failed":    return "badge-failed";
    case "cancelled": return "badge-failed";
    case "pending":   return "badge-pending";
    default:          return "badge-pending";
  }
}

/** Map an agent name to a display label. */
export function agentLabel(name: string): string {
  const map: Record<string, string> = {
    cleaner:     "Data Cleaner",
    analyst:     "Data Analyst",
    visualizer:  "Visualizer",
    storyteller: "Storyteller",
  };
  return map[name] ?? name;
}

/** Map an agent name to a brand colour class. */
export function agentColor(name: string): string {
  const map: Record<string, string> = {
    cleaner:     "text-info",
    analyst:     "text-brand-400",
    visualizer:  "text-success",
    storyteller: "text-warning",
  };
  return map[name] ?? "text-zinc-400";
}
