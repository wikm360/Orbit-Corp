"use client";

import { Button } from "@/shared/components/ui/Button";
import { cn } from "@/shared/lib/utils";

import type { MemoryCategory, ProjectMemory } from "../types";

export const CATEGORY_META: Record<MemoryCategory, { label: string; className: string; dot: string }> = {
  technical_decision: { label: "تصمیم فنی", className: "bg-sky-50 text-sky-700 ring-sky-200", dot: "bg-sky-500" },
  timeline: { label: "زمان‌بندی", className: "bg-amber-50 text-amber-700 ring-amber-200", dot: "bg-amber-500" },
  business_rule: { label: "قانون کسب‌وکار", className: "bg-violet-50 text-violet-700 ring-violet-200", dot: "bg-violet-500" },
  convention: { label: "قرارداد / عرف تیمی", className: "bg-emerald-50 text-emerald-700 ring-emerald-200", dot: "bg-emerald-500" },
};

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("fa-IR", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

interface MemoryCardProps {
  memory: ProjectMemory;
  mutationKey: string | null;
  onEdit: (memory: ProjectMemory) => void;
  onDelete: (memory: ProjectMemory) => void;
  onToggleVerification: (memory: ProjectMemory) => Promise<void>;
}

export function MemoryCard({ memory, mutationKey, onEdit, onDelete, onToggleVerification }: MemoryCardProps) {
  const meta = CATEGORY_META[memory.category];
  const isUpdating = mutationKey === `update:${memory.id}`;
  const isDeleting = mutationKey === `delete:${memory.id}`;

  return (
    <article className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-teal-200 hover:shadow-md sm:p-5">
      <span className={cn("absolute inset-y-0 right-0 w-1", meta.dot)} aria-hidden="true" />

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset", meta.className)}>
            {meta.label}
          </span>
          {memory.is_verified ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2.5 py-1 text-[11px] font-semibold text-teal-700 ring-1 ring-inset ring-teal-200">
              <svg aria-hidden="true" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5"><path strokeLinecap="round" strokeLinejoin="round" d="m5 10 3 3 7-7" /></svg>
              تأییدشده
            </span>
          ) : (
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-500">در انتظار تأیید</span>
          )}
        </div>
        <time dateTime={memory.updated_at} className="text-[11px] text-gray-400">ویرایش {formatDate(memory.updated_at)}</time>
      </div>

      <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-800 sm:text-[15px]">{memory.fact_text}</p>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
        <div className="flex items-center gap-1 text-[11px] text-slate-400">
          <span>ضریب اطمینان</span>
          <span className="ltr font-medium text-slate-500">{Math.round(memory.confidence_score * 100)}%</span>
          <span aria-hidden="true">•</span>
          <span className="ltr font-mono" title={memory.id}>{memory.id.slice(0, 8)}</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            isLoading={isUpdating}
            disabled={Boolean(mutationKey)}
            onClick={() => void onToggleVerification(memory).catch(() => {})}
            className={memory.is_verified ? "text-amber-700 hover:bg-amber-50" : "text-teal-700 hover:bg-teal-50"}
          >
            {memory.is_verified ? "لغو تأیید" : "تأیید صحت"}
          </Button>
          <Button type="button" variant="ghost" size="sm" disabled={Boolean(mutationKey)} onClick={() => onEdit(memory)}>ویرایش</Button>
          <Button type="button" variant="ghost" size="sm" isLoading={isDeleting} disabled={Boolean(mutationKey)} onClick={() => onDelete(memory)} className="text-red-600 hover:bg-red-50">حذف</Button>
        </div>
      </div>
    </article>
  );
}
