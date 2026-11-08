"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { volumeReportApi } from "../api/volumeReportApi";
import { runSoon } from "../lib/defer";
import { formatJalaliDate, formatJalaliDateTime, toFa } from "../lib/jalali";
import { PERIOD_LABELS, STATUS_LABELS } from "../lib/status";
import type { ReportStatus, ReportSummary } from "../types";
import { EmptyState, ErrorBox, fieldClass, LoadingBlock, ReportStatusBadge } from "./common";

export function ReportsList({ projectId, refreshKey = 0 }: { projectId: string; refreshKey?: number }) {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [filter, setFilter] = useState<ReportStatus | "">("");

  const load = useCallback(async () => {
    setError(null);
    try { setReports(await volumeReportApi.list(projectId, filter || undefined)); } catch (e) { setError(e); }
  }, [projectId, filter]);
  useEffect(() => runSoon(() => { setReports(null); void load(); }), [load, refreshKey]);

  async function remove(r: ReportSummary) {
    const warning = r.status === "published" ? `«${r.title}» منتشرشده است. با حذف، گزارش و همه‌ی نتایج آن برای همیشه پاک می‌شود. ادامه می‌دهید؟` : `گزارش «${r.title}» برای همیشه حذف شود؟`;
    if (!window.confirm(warning)) return;
    setDeleting(r.id);
    try { await volumeReportApi.remove(r.id); setReports((cur) => cur?.filter((x) => x.id !== r.id) ?? cur); } catch (e) { setError(e); } finally { setDeleting(null); }
  }

  if (error) return <ErrorBox error={error} onRetry={() => void load()} />;
  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 text-xs text-slate-600">
        وضعیت
        <select aria-label="فیلتر وضعیت" value={filter} onChange={(e) => setFilter(e.target.value as ReportStatus | "")} className={`${fieldClass} max-w-[11rem]`}>
          <option value="">همه</option>
          {(Object.keys(STATUS_LABELS) as ReportStatus[]).map((s) => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
        </select>
      </label>
      {!reports ? <LoadingBlock /> : reports.length === 0 ? (
        <EmptyState title="گزارشی ثبت نشده است" hint="با «ساخت گزارش جدید» فایل‌های اکسل همین پروژه را انتخاب و پردازش کنید." />
      ) : (
        <ul className="grid gap-3 md:grid-cols-2" aria-label="فهرست گزارش‌ها">
          {reports.map((r) => (
            <li key={r.id} className="relative">
              <Link href={`/volume-reports/${r.id}`} className="block rounded-2xl border border-black/[0.06] bg-white p-4 shadow-sm transition hover:border-teal-400 hover:shadow">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-slate-900">{r.title}</h3>
                  <ReportStatusBadge status={r.status} />
                </div>
                <p className="mt-2 text-xs text-slate-600">{PERIOD_LABELS[r.period_type]} · {r.period_label}</p>
                <p className="mt-1 text-[11px] text-slate-400">
                  {formatJalaliDate(r.period_start)} تا {formatJalaliDate(r.period_end)} · نسخه‌ی {toFa(r.version)} · به‌روزرسانی {formatJalaliDateTime(r.updated_at)}
                </p>
              </Link>
              {r.status !== "processing" && (
                <button type="button" aria-label={`حذف ${r.title}`} disabled={deleting === r.id} onClick={() => void remove(r)}
                  className="absolute bottom-3 left-3 rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50">
                  {deleting === r.id ? "در حال حذف…" : "حذف"}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
