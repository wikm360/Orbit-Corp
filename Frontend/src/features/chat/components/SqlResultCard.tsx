"use client";

import { useState } from "react";

import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { cn, toFaDigits } from "@/shared/lib/utils";

import { accountingApi, ExportFormat } from "../api/accountingApi";
import { formatCell, freshnessNotes } from "../lib/sqlResultFormat";
import type { SqlResultArtifact } from "../types";

function IconButton({ label, onClick, disabled, active, children }: {
  label: string; onClick: () => void; disabled?: boolean; active?: boolean; children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      aria-pressed={active}
      className={cn(
        "inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-xs transition-colors disabled:opacity-50",
        active ? "border-teal-300 bg-teal-50 text-teal-700" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-100"
      )}
    >
      {children}
    </button>
  );
}

/**
 * The reference behind a database answer: the exact table the SQL returned, the SQL itself, run metadata,
 * Excel/CSV export of the full result and a thumbs up/down that feeds the quality log.
 */
export function SqlResultCard({ artifact }: { artifact: SqlResultArtifact }) {
  const [sqlOpen, setSqlOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<-1 | 0 | 1>(0);
  const [busy, setBusy] = useState<ExportFormat | "feedback" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const shown = artifact.rows.length;
  const hiddenRows = artifact.row_count > shown;
  const notes = freshnessNotes(artifact.data_as_of ?? {});

  async function copySql() {
    try {
      await navigator.clipboard.writeText(artifact.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setNotice("کپی انجام نشد؛ متن SQL را دستی انتخاب کنید.");
    }
  }

  async function download(format: ExportFormat) {
    setBusy(format);
    setNotice(null);
    try {
      await accountingApi.downloadExport(artifact.query_id, format);
    } catch (error) {
      setNotice(friendlyErrorMessage(error, "دریافت فایل ناموفق بود."));
    } finally {
      setBusy(null);
    }
  }

  async function rate(value: 1 | -1) {
    const next = feedback === value ? 0 : value;
    setBusy("feedback");
    setNotice(null);
    try {
      await accountingApi.sendFeedback(artifact.query_id, next);
      setFeedback(next);
    } catch (error) {
      setNotice(friendlyErrorMessage(error, "ثبت بازخورد ناموفق بود."));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section dir="rtl" aria-label="مرجع پاسخ: نتیجه‌ی پایگاه داده" className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/70">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white px-3 py-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <span aria-hidden="true">🗄️</span>
          <span>مرجع پاسخ: پایگاه داده‌ی مالی راهکاران</span>
          <span className="rounded-full bg-teal-50 px-2 py-0.5 text-xs font-medium text-teal-700">
            {toFaDigits(artifact.row_count)}{artifact.total_exact === false ? "+" : ""} ردیف
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <IconButton label="دریافت فایل اکسل کامل" onClick={() => download("xlsx")} disabled={busy !== null}>
            {busy === "xlsx" ? "…" : "⬇"} اکسل
          </IconButton>
          <IconButton label="دریافت فایل CSV کامل" onClick={() => download("csv")} disabled={busy !== null}>
            {busy === "csv" ? "…" : "⬇"} CSV
          </IconButton>
        </div>
      </header>

      {artifact.rows.length === 0 ? (
        <p className="px-4 py-6 text-center text-sm text-slate-500">هیچ ردیفی با شرط این پرسش پیدا نشد.</p>
      ) : (
        <div className="max-h-[420px] overflow-auto">
          <table className="min-w-full border-separate border-spacing-0 text-[13px] leading-6">
            <thead className="sticky top-0 z-10">
              <tr>
                {artifact.columns.map((column) => (
                  <th
                    key={column.name}
                    scope="col"
                    className={cn(
                      "whitespace-nowrap border-b border-slate-200 bg-slate-100 px-3 py-2 font-semibold text-slate-600",
                      column.kind === "money" || column.kind === "number" || column.kind === "ratio" ? "text-end" : "text-start"
                    )}
                  >
                    {column.name}
                    {column.kind === "money" && <span className="mr-1 text-[11px] font-normal text-slate-400">(ریال)</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {artifact.rows.map((row, rowIndex) => (
                <tr key={rowIndex} className={rowIndex % 2 ? "bg-slate-50" : "bg-white"}>
                  {artifact.columns.map((column, columnIndex) => {
                    const cell = formatCell(column.kind, row[columnIndex]);
                    return (
                      <td
                        key={column.name + columnIndex}
                        title={typeof row[columnIndex] === "string" ? (row[columnIndex] as string) : undefined}
                        className={cn(
                          "border-b border-slate-100 px-3 py-1.5 align-top",
                          cell.align === "end" ? "text-end" : "text-start",
                          cell.numeric && "tabular-nums",
                          !cell.numeric && "max-w-[260px] truncate"
                        )}
                      >
                        <span>{cell.text}</span>
                        {cell.hint && <span className="block text-[11px] leading-4 text-slate-400">{cell.hint}</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(hiddenRows || artifact.truncated) && (
        <p className="border-t border-slate-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-800">
          {hiddenRows
            ? `${toFaDigits(shown)} ردیف از ${toFaDigits(artifact.row_count)}${artifact.total_exact === false ? "+" : ""} ردیف نمایش داده شد.`
            : "نتیجه به سقف ردیف‌های مجاز رسیده است."}{" "}
          برای دریافت همه‌ی ردیف‌ها از دکمه‌ی اکسل استفاده کنید.
        </p>
      )}

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span>⏱ {toFaDigits(artifact.duration_ms)} میلی‌ثانیه</span>
          {notes.map((note) => <span key={note}>📅 {note}</span>)}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-400">این پاسخ مفید بود؟</span>
          <IconButton label="مفید بود" onClick={() => rate(1)} disabled={busy !== null} active={feedback === 1}>👍</IconButton>
          <IconButton label="نادرست یا ناکافی بود" onClick={() => rate(-1)} disabled={busy !== null} active={feedback === -1}>👎</IconButton>
          <IconButton label="نمایش و کپی کوئری SQL" onClick={() => setSqlOpen((open) => !open)} active={sqlOpen}>
            {"</>"} SQL
          </IconButton>
        </div>
      </footer>

      {sqlOpen && (
        <div className="border-t border-slate-200 bg-slate-900 px-3 py-2">
          <div className="mb-1 flex items-center justify-between text-xs text-slate-300">
            <span>کوئری اجراشده (فقط‌خواندنی، روی view های لایه‌ی معنایی)</span>
            <button type="button" onClick={copySql} className="rounded-md border border-slate-600 px-2 py-0.5 hover:bg-slate-800">
              {copied ? "کپی شد ✓" : "کپی"}
            </button>
          </div>
          <pre dir="ltr" className="max-h-64 overflow-auto whitespace-pre-wrap break-words text-left text-[12px] leading-5 text-emerald-200">{artifact.sql}</pre>
        </div>
      )}
      {notice && <p role="alert" className="border-t border-red-100 bg-red-50 px-3 py-1.5 text-xs text-red-700">{notice}</p>}
    </section>
  );
}
