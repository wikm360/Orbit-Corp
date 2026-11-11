"use client";

import { useEffect, useState } from "react";

import { volumeReportApi } from "../api/volumeReportApi";
import { runSoon } from "../lib/defer";
import { toFa } from "../lib/jalali";
import { SHEET_REASON_LABELS, WARNING_LABELS } from "../lib/status";
import type { SourceInfo, SourceReads, SourceWarning } from "../types";
import { Card, EmptyState, ErrorBox, LoadingBlock } from "./common";

export const describeWarning = (w: SourceWarning): string => {
  const base = WARNING_LABELS[w.code] ?? w.code;
  if (w.code === "period_label_mismatch") return `${base} (شیت: ${(w.found ?? []).join("، ")} — واردشده: ${(w.expected ?? []).join("، ")})`;
  if (w.code === "unit_missing") return `${base} (ردیف ${toFa(w.row ?? 0)})`;
  return base;
};

type ReadState = "ok" | "partial" | "none";
interface ReadRow { label: string; state: ReadState; detail: string }

/** The parameters a file was expected to give, one line each: ✓ read, ⚠ read only for part of the sheets, — not found. */
function readRows(reads: SourceReads): ReadRow[] {
  const rows: ReadRow[] = [];
  const sheets = (n: number) => `${toFa(n)} پروژه`;
  rows.push({ label: "حجم عملیات (درآمد)", state: reads.income.actual > 0 ? "ok" : "none", detail: reads.income.actual > 0 ? sheets(reads.income.actual) : "شیت درآمد خوانده نشد" });
  rows.push({ label: "برنامه / پیش‌بینی حجم‌ها", state: reads.income.planned > 0 ? "ok" : "none", detail: reads.income.planned > 0 ? sheets(reads.income.planned) : "در این فایل نیست" });
  for (const basis of ["actual", "planned"] as const) {
    const evm = reads.evm[basis];
    const name = basis === "actual" ? "EVM واقعی (PV · EV · AC · SPI · CPI)" : "EVM پیش‌بینی (PV · EV · AC · SPI · CPI)";
    if (evm.projects > 0 || evm.has_total) {
      rows.push({ label: name, state: evm.projects > 0 && evm.has_total ? "ok" : "partial", detail: `${toFa(evm.projects)} پروژه${evm.has_total ? " + ردیف جمع" : " · بدون ردیف جمع"}` });
    } else {
      rows.push({ label: name, state: "none", detail: "جدول EVM پیدا نشد" });
    }
  }
  for (const basis of ["actual", "planned"] as const) {
    const incomeSheets = reads.income[basis];
    const found = reads.income_totals[basis];
    if (incomeSheets === 0 && found === 0) continue;
    rows.push({
      label: `جمع‌های درآمد ${basis === "actual" ? "واقعی" : "پیش‌بینی"} (صورت‌وضعیت · تعدیل · درآمد کل)`,
      state: found === 0 ? "none" : found < incomeSheets ? "partial" : "ok",
      detail: found === 0 ? "بلوک جمع پیدا نشد" : `${toFa(found)} از ${toFa(Math.max(incomeSheets, found))} پروژه`,
    });
  }
  return rows;
}

const STATE_STYLE: Record<ReadState, { mark: string; tone: string }> = {
  ok: { mark: "✓", tone: "text-emerald-700" },
  partial: { mark: "⚠", tone: "text-amber-700" },
  none: { mark: "—", tone: "text-slate-400" },
};

function ReadChecklist({ reads }: { reads: SourceReads }) {
  return (
    <div className="mb-3 rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2" aria-label="پارامترهای خوانده‌شده">
      <h3 className="mb-1 text-xs font-medium text-slate-600">پارامترهای خوانده‌شده از این فایل</h3>
      <ul className="grid gap-x-6 gap-y-0.5 text-xs md:grid-cols-2">
        {readRows(reads).map((row) => (
          <li key={row.label} className="flex items-baseline gap-2">
            <span className={`w-4 shrink-0 text-center font-bold ${STATE_STYLE[row.state].tone}`}>{STATE_STYLE[row.state].mark}</span>
            <span className="text-slate-700">{row.label}</span>
            <span className={`ms-auto whitespace-nowrap ${STATE_STYLE[row.state].tone}`}>{row.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

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
            {source.reads && <ReadChecklist reads={source.reads} />}
            {source.warnings.length > 0 && (
              <ul className="mb-3 space-y-1" aria-label="هشدارها">
                {source.warnings.map((w, i) => <li key={i} className="rounded-lg bg-amber-50 px-3 py-1.5 text-xs text-amber-900">⚠ {describeWarning(w)}{w.sheet ? ` — ${w.sheet.trim()}` : ""}</li>)}
              </ul>
            )}
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <h3 className="mb-1 text-xs font-medium text-emerald-700">شیت‌های خوانده‌شده ({toFa(used.length)})</h3>
                <ul className="space-y-1 text-xs text-slate-700">
                  {used.map((s) => (
                    <li key={s.sheet}>
                      {s.sheet.trim()} — {s.kind === "evm" ? "خلاصه مالی EVM" : s.site_name}
                      {s.continuation && <span className="ms-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">ادامه‌ی جدول صفحه‌ی قبل</span>}
                      {s.basis === "planned" && <span className="ms-1 rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] text-indigo-700">برنامه / پیش‌بینی</span>}{" "}
                      <span className="text-slate-400">
                        {s.kind === "evm" ? `(${toFa(s.evm_rows ?? 0)} ردیف)` : `(${toFa(s.rows_nonzero ?? 0)} ردیف دارای حجم)`}
                      </span>
                    </li>
                  ))}
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
