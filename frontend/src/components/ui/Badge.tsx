import { type HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium border",
  {
    variants: {
      variant: {
        default:   "bg-surface-3 text-zinc-300 border-surface-4",
        brand:     "bg-brand-500/15 text-brand-400 border-brand-500/30",
        success:   "bg-success/15 text-success border-success/30",
        danger:    "bg-danger/15 text-danger border-danger/30",
        warning:   "bg-warning/15 text-warning border-warning/30",
        info:      "bg-info/15 text-info border-info/30",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

/** Map session/agent status → badge variant */
export function statusVariant(status: string): VariantProps<typeof badgeVariants>["variant"] {
  switch (status) {
    case "running":   return "brand";
    case "completed": return "success";
    case "failed":    return "danger";
    case "cancelled": return "danger";
    case "pending":   return "default";
    case "ready":     return "success";
    case "error":     return "danger";
    default:          return "default";
  }
}
