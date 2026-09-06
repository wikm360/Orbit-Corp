import { InputHTMLAttributes, ReactNode, forwardRef, useId } from "react";

import { cn } from "@/shared/lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  /** Icon rendered at the start (right side in RTL) of the field. */
  startIcon?: ReactNode;
  /** Interactive element rendered at the end (left side in RTL), e.g. a show-password toggle. */
  endSlot?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, startIcon, endSlot, className, id, ...props }, ref) => {
    const generatedId = useId();
    const inputId = id ?? generatedId;

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-gray-700">
            {label}
          </label>
        )}
        <div className="relative">
          {startIcon && (
            <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-gray-400">
              {startIcon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={error ? true : undefined}
            className={cn(
              "w-full rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm transition",
              "placeholder:text-gray-400",
              "focus:border-brand-400 focus:outline-none focus:ring-4 focus:ring-brand-100",
              startIcon ? "ps-10" : undefined,
              endSlot ? "pe-11" : undefined,
              error ? "border-red-400 focus:border-red-400 focus:ring-red-100" : undefined,
              className
            )}
            {...props}
          />
          {endSlot && (
            <span className="absolute inset-y-0 end-2 flex items-center">{endSlot}</span>
          )}
        </div>
        {error ? (
          <span className="text-xs text-red-600">{error}</span>
        ) : hint ? (
          <span className="text-xs text-gray-500">{hint}</span>
        ) : null}
      </div>
    );
  }
);

Input.displayName = "Input";
