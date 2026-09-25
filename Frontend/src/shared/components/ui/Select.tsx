import { SelectHTMLAttributes } from "react";

import { cn } from "@/shared/lib/utils";

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "size"> {
  size?: "sm" | "md";
}

/**
 * Shared, RTL-friendly select control. It intentionally keeps the native
 * element so keyboard navigation and form behaviour work everywhere.
 */
export function Select({ className, size = "md", style, children, ...props }: SelectProps) {
  return (
    <select
      {...props}
      className={cn(
        "w-full appearance-none rounded-xl border border-slate-200 bg-white bg-no-repeat pr-3 pl-10 text-right text-sm text-slate-700 shadow-sm transition duration-150 outline-none hover:border-slate-300 focus:border-teal-500 focus:ring-4 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400 disabled:opacity-70",
        size === "sm" ? "h-9 text-xs" : "h-11",
        className
      )}
      style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2364758b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")`,
        backgroundPosition: "left 0.75rem center",
        backgroundSize: "1rem",
        ...style,
      }}
    >
      {children}
    </select>
  );
}
