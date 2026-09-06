import { ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/shared/lib/utils";

import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "danger" | "ghost";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  isLoading?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-brand-600 text-white shadow-sm hover:bg-brand-700 active:bg-brand-800 disabled:bg-brand-300 focus-visible:ring-brand-200",
  secondary:
    "bg-gray-100 text-gray-900 hover:bg-gray-200 disabled:opacity-50 focus-visible:ring-gray-200",
  danger:
    "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300 focus-visible:ring-red-200",
  ghost:
    "bg-transparent text-gray-700 hover:bg-gray-100 disabled:opacity-50 focus-visible:ring-gray-200",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs rounded-lg",
  md: "px-4 py-2.5 text-sm rounded-xl",
  lg: "px-5 py-3 text-base rounded-xl",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { variant = "primary", size = "md", isLoading, className, children, disabled, ...props },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          "inline-flex items-center justify-center gap-2 font-medium transition-colors",
          "focus:outline-none focus-visible:ring-4 disabled:cursor-not-allowed",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      >
        {isLoading && <Spinner />}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
