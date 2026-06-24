import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  breadcrumb?: ReactNode;
  className?: string;
}

export function PageHeader({ title, description, actions, breadcrumb, className }: PageHeaderProps) {
  return (
    <div className={cn("flex items-start justify-between gap-4 mb-6", className)}>
      <div className="min-w-0">
        {breadcrumb && (
          <div className="mb-1.5 text-xs text-zinc-500">{breadcrumb}</div>
        )}
        <h1 className="text-xl font-semibold text-zinc-100 tracking-tight truncate">
          {title}
        </h1>
        {description && (
          <p className="mt-1 text-sm text-zinc-400 leading-relaxed">{description}</p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      )}
    </div>
  );
}
