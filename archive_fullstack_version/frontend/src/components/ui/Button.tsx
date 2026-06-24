import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-0 disabled:pointer-events-none disabled:opacity-40 select-none",
  {
    variants: {
      variant: {
        default:   "bg-brand-500 text-white hover:bg-brand-600 shadow-sm active:scale-[0.98]",
        secondary: "bg-surface-3 text-zinc-200 hover:bg-surface-4 border border-surface-4",
        outline:   "border border-surface-4 text-zinc-300 hover:bg-surface-3 hover:text-zinc-100",
        ghost:     "text-zinc-400 hover:text-zinc-100 hover:bg-surface-3",
        danger:    "bg-danger text-white hover:bg-red-600 shadow-sm",
        success:   "bg-success text-white hover:bg-emerald-600 shadow-sm",
      },
      size: {
        sm:   "h-8  px-3 text-xs",
        md:   "h-9  px-4",
        lg:   "h-11 px-6 text-base",
        icon: "h-9  w-9  p-0",
        "icon-sm": "h-7 w-7 p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
      {children}
    </button>
  )
);

Button.displayName = "Button";
