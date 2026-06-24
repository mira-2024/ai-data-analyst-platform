import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number;       // 0–100
  className?: string;
  trackClassName?: string;
  fillClassName?: string;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
}

const sizeMap = {
  sm: "h-1",
  md: "h-1.5",
  lg: "h-2",
};

export function ProgressBar({
  value,
  className,
  trackClassName,
  fillClassName,
  showLabel = false,
  size = "md",
}: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));

  return (
    <div className={cn("w-full", className)}>
      {showLabel && (
        <div className="flex justify-between text-2xs text-zinc-500 mb-1">
          <span>Progress</span>
          <span>{Math.round(clamped)}%</span>
        </div>
      )}
      <div className={cn("w-full bg-surface-3 rounded-full overflow-hidden", sizeMap[size], trackClassName)}>
        <div
          className={cn(
            "h-full bg-brand-500 rounded-full transition-all duration-500 ease-out",
            fillClassName
          )}
          style={{ width: `${clamped}%` }}
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}
