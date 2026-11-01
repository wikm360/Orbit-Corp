"use client";

import { useEffect, useState } from "react";

import { volumeReportApi } from "../api/volumeReportApi";
import { runSoon } from "../lib/defer";
import { toFa } from "../lib/jalali";
import { SHEET_REASON_LABELS, WARNING_LABELS } from "../lib/status";
import type { SourceInfo, SourceWarning } from "../types";
import { Card, EmptyState, ErrorBox, LoadingBlock } from "./common";

export const describeWarning = (w: SourceWarning): string => {
  const base = WARNING_LABELS[w.code] ?? w.code;
  if (w.code === "period_label_mismatch") return `${base} (شیت: ${(w.found ?? []).join("، ")} — واردشده: ${(w.expected ?? []).join("، ")})`;
  if (w.code === "unit_missing") return `${base} (ردیف ${toFa(w.row ?? 0)})`;
  return base;
};

/** What the run read from each file: used sheets, skipped sheets with the reason, and non-blocking warnings. */
export function SourceDetails({ sources, compact = false }: { sources: SourceInfo[]; compact?: boolean }) {
  if (!sources.length) return <EmptyState title="فایلی انتخاب نشده است" />;
  return (
    <div className="space-y-3">
      {sources.map((source) => {
        const used = source.sheet_log.filter((s) => s.used);
        const skipped = source.sheet_log.filter((s) => !s.used);
        return (
          <Card key={source.id} title={source.filename} actions={<span className="text-xs text-slate-500">{source.status === "failed" ? "ناموفق" : source.status === "parsed" ? "خوانده‌شده" : "در انتظار"}</span>}>
            {source.error_message && <p className="mb-2 text-xs text-red-600">{source.error_message}</p>}
            {source.warnings.length > 0 && (
              <ul className="mb-3 space-y-1" aria-label="هشدارها">
                {source.warnings.map((w, i) => <li key={i} className="rounded-lg bg-amber-50 px-3 py-1.5 text-xs text-amber-900">⚠ {describeWarning(w)}{w.sheet ? ` — ${w.sheet.trim()}` : ""}</li>)}
              </ul>
            )}
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <h3 className="mb-1 text-xs font-medium text-emerald-700">شیت‌های خوانده‌شده ({toFa(used.length)})</h3>
                <ul className="space-y-1 text-xs text-slate-700">
                  {used.map((s) => <li key={s.sheet}>{s.sheet.trim()} — {s.site_name} <span className="text-slate-400">({toFa(s.rows_nonzero ?? 0)} ردیف دارای حجم)</span></li>)}
                  {used.length === 0 && <li className="text-slate-400">هیچ شیتی خوانده نشد.</li>}
                </ul>
              </div>
              {!compact && (
                <div>
                  <h3 className="mb-1 text-xs font-medium text-slate-600">شیت‌های کنار گذاشته‌شده ({toFa(skipped.length)})</h3>
                  <ul className="max-h-40 space-y-1 overflow-auto text-xs text-slate-600">
                    {skipped.map((s) => <li key={s.sheet}>{s.sheet.trim()} <span className="text-slate-400">— {SHEET_REASON_LABELS[s.reason ?? ""] ?? s.reason}</span></li>)}
                  </ul>
                </div>
              )}
            </div>
          </Card>
        );
      })}
    </div>
  );
}

export function SourcesPanel({ reportId, refreshKey }: { reportId: string; refreshKey: number }) {
  const [sources, setSources] = useState<SourceInfo[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    let live = true;
    const cancel = runSoon(() => {
      setError(null);
      volumeReportApi.sources(reportId).then((s) => { if (live) setSources(s); }).catch((e) => { if (live) setError(e); });
    });
    return () => { live = false; cancel(); };
  }, [reportId, refreshKey]);
  if (error) return <ErrorBox error={error} />;
  if (!sources) return <LoadingBlock />;
  return <SourceDetails sources={sources} />;
}
