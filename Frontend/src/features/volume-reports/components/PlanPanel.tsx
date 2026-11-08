"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { cn } from "@/shared/lib/utils";

import { volumeReportApi } from "../api/volumeReportApi";
import { runSoon } from "../lib/defer";
import { formatQuantity, unitLabel } from "../lib/format";
import { formatJalaliDate, toFa } from "../lib/jalali";
import type { PlanVsActual, PlanVsActualRow, ResultScope } from "../types";
import { Card, EmptyState, ErrorBox, LoadingBlock } from "./common";

const SCOPES: { id: Exclude<ResultScope, "company">; label: string }[] = [{ id: "holding", label: "هلدینگ" }, { id: "site", label: "کارگاه" }];

const tone = (pct: number) => (pct >= 100 ? "emerald" : pct >= 80 ? "amber" : "red");
const BAR = { emerald: "bg-emerald-500", amber: "bg-amber-400", red: "bg-red-500" } as const;
const TEXT = { emerald: "text-emerald-700", amber: "text-amber-700", red: "text-red-600" } as const;

function Achievement({ pct }: { pct: string | null }) {
  if (pct === null) return <span className="text-slate-300">—</span>;
  const value = Number.parseFloat(pct);
  const t = tone(value);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-100" role="img" aria-label={`${toFa(pct)} درصد تحقق`}>
        <div className={cn("h-full rounded-full", BAR[t])} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
      <span className={cn("text-[11px] font-medium", TEXT[t])}>{toFa(pct.replace(".", "٫"))}٪</span>
    </div>
  );
}

function ComparisonTable({ rows, showSite }: { rows: PlanVsActualRow[]; showSite: boolean }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-100">
      <table className="w-full min-w-[640px] text-xs">
        <thead className="bg-slate-50 text-slate-600">
          <tr>
            {showSite && <th className="px-3 py-2 text-start font-medium">کارگاه</th>}
            {["آیتم", "واحد", "پیش‌بینی", "واقعی", "اختلاف", "تحقق"].map((h) => <th key={h} className="px-3 py-2 text-start font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const negative = r.variance.startsWith("-");
            return (
              <tr key={`${r.site}-${r.item_key}-${i}`} className="border-t border-slate-100">
                {showSite && <td className="px-3 py-2">{r.site}</td>}
                <td className="px-3 py-2 font-medium text-slate-800">{r.item}</td>
                <td className="px-3 py-2 text-slate-500">{unitLabel(r.unit)}</td>
                <td className="px-3 py-2 whitespace-nowrap">{formatQuantity(r.planned, r.decimals)}</td>
                <td className="px-3 py-2 whitespace-nowrap text-teal-800">{formatQuantity(r.actual, r.decimals)}</td>
                <td className={cn("px-3 py-2 whitespace-nowrap", negative ? "text-red-600" : "text-emerald-700")} dir="ltr">{formatQuantity(r.variance, r.decimals)}</td>
                <td className="px-3 py-2"><Achievement pct={r.achievement_pct} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Forecast ("برنامه / پیش‌بینی") sheets: how last period's forecast fared against this period's actuals, and this
 *  report's own forecast for the period after it. Forecast quantities are never part of the actual totals. */
export function PlanPanel({ reportId, periodEnd, refreshKey }: { reportId: string; periodEnd: string; refreshKey: number }) {
  const [scope, setScope] = useState<Exclude<ResultScope, "company">>("holding");
  const [data, setData] = useState<PlanVsActual | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try { setData(await volumeReportApi.planVsActual(reportId, scope)); } catch (e) { setError(e); }
  }, [reportId, scope]);
  useEffect(() => runSoon(() => { setData(null); void load(); }), [load, refreshKey]);

  if (error) return <ErrorBox error={error} onRetry={() => void load()} />;
  if (!data) return <LoadingBlock />;
  const prev = data.previous_report;

  return (
    <div className="space-y-4">
      <div role="tablist" aria-label="سطح نمایش" className="inline-flex rounded-xl bg-slate-100 p-1">
        {SCOPES.map((s) => (
          <button key={s.id} role="tab" type="button" aria-selected={scope === s.id} onClick={() => setScope(s.id)}
            className={cn("rounded-lg px-4 py-1.5 text-sm", scope === s.id ? "bg-white font-medium text-teal-800 shadow-sm" : "text-slate-600")}>{s.label}</button>
        ))}
      </div>

      <Card title="تحقق پیش‌بینیِ دوره‌ی قبل"
        actions={prev && <Link href={`/volume-reports/${prev.id}`} className="text-xs text-teal-700 hover:underline">گزارش مبدأ: {prev.title} ({prev.period_label})</Link>}>
        {!prev ? (
          <EmptyState title="پیش‌بینی‌ای برای این دوره پیدا نشد" hint="گزارش قبلی همین پروژه باید شیت برنامه/پیش‌بینی داشته و پردازش شده باشد." />
        ) : (
          <div className="space-y-2">
            {!prev.adjacent && <p className="rounded-lg bg-amber-50 px-3 py-1.5 text-xs text-amber-900">⚠ دوره‌ی گزارش مبدأ ({formatJalaliDate(prev.period_start)} تا {formatJalaliDate(prev.period_end)}) بلافاصله پیش از این دوره نیست.</p>}
            {data.rows.length === 0 ? <EmptyState title="ردیفی برای مقایسه نیست" /> : <ComparisonTable rows={data.rows} showSite={scope === "site"} />}
          </div>
        )}
      </Card>

      <Card title={`برنامه‌ی دوره‌ی بعد (پس از ${formatJalaliDate(periodEnd)})`}>
        {data.next_plan.length === 0 ? (
          <EmptyState title="این گزارش شیت پیش‌بینی ندارد" hint="اگر فایل شیت «پیش‌بینی/برنامه» دارد، گزارش را دوباره اجرا کنید." />
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-100">
            <table className="w-full min-w-[420px] text-xs">
              <thead className="bg-slate-50 text-slate-600">
                <tr>{[...(scope === "site" ? ["کارگاه"] : []), "آیتم", "واحد", "مقدار برنامه‌ریزی‌شده"].map((h) => <th key={h} className="px-3 py-2 text-start font-medium">{h}</th>)}</tr>
              </thead>
              <tbody>
                {data.next_plan.map((r, i) => (
                  <tr key={`${r.site_id}-${r.item_key}-${i}`} className="border-t border-slate-100">
                    {scope === "site" && <td className="px-3 py-2">{r.site}</td>}
                    <td className="px-3 py-2 font-medium text-slate-800">{r.item}</td>
                    <td className="px-3 py-2 text-slate-500">{unitLabel(r.unit)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{formatQuantity(r.qty, r.decimals)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
