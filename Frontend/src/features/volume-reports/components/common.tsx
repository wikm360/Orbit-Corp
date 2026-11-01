"use client";

import type { ReactNode } from "react";

import { Spinner } from "@/shared/components/ui/Spinner";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { cn } from "@/shared/lib/utils";

import { STATUS_LABELS, STATUS_TONES } from "../lib/status";
import type { ReportStatus } from "../types";

export function ReportStatusBadge({ status }: { status: ReportStatus }) {
  return <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", STATUS_TONES[status])}>{STATUS_LABELS[status]}</span>;
}

export function UnconfirmedMark({ className }: { className?: string }) {
  return (
    <span title="شامل ردیف‌های تأییدنشده" className={cn("rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800", className)}>
      تأییدنشده
    </span>
  );
}

export function LoadingBlock({ label = "در حال دریافت..." }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500">
      <Spinner /> {label}
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-10 text-center">
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorBox({ error, onRetry, fallback = "خطایی رخ داد. دوباره تلاش کنید." }: { error: unknown; onRetry?: () => void; fallback?: string }) {
  return (
    <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      <span>{friendlyErrorMessage(error, fallback)}</span>
      {onRetry && <button type="button" onClick={onRetry} className="shrink-0 rounded-lg border border-red-300 px-3 py-1 text-xs hover:bg-red-100">تلاش مجدد</button>}
    </div>
  );
}

export function Card({ title, actions, children, className }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-2xl border border-black/[0.06] bg-white p-4 shadow-sm", className)}>
      {(title || actions) && (
        <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-sm font-semibold text-slate-800">{title}</h2>}
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: string; badge?: number }[]; value: T; onChange: (id: T) => void }) {
  return (
    <div role="tablist" className="flex gap-1 overflow-x-auto border-b border-slate-200">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          type="button"
          aria-selected={tab.id === value}
          onClick={() => onChange(tab.id)}
          className={cn("whitespace-nowrap border-b-2 px-4 py-2.5 text-sm transition-colors", tab.id === value ? "border-teal-600 font-medium text-teal-700" : "border-transparent text-slate-500 hover:text-slate-800")}
        >
          {tab.label}
          {tab.badge ? <span className="ms-1.5 rounded-full bg-amber-500 px-1.5 py-0.5 text-[10px] text-white">{tab.badge}</span> : null}
        </button>
      ))}
    </div>
  );
}

export const fieldClass = "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100 disabled:bg-slate-50";
