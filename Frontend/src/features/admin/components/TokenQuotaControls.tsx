"use client";

import { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { adminApi } from "../api/adminApi";
import type { TokenUsageReport, User } from "@/shared/types";

const PURPOSE_LABEL: Record<string, string> = { chat: "چت", sql: "پرس‌وجوی مالی", rerank: "رتبه‌بندی جست‌وجو", vr_agent: "گزارش حجم", ocr: "OCR اسناد", embedding: "embedding" };
const fa = (value: number) => value.toLocaleString("fa-IR");

/** Token quota of one user: usage bar and the admin actions (set / extend / reset / remove). `editable` is false for targets the
 *  caller may not manage (the server enforces the same rule). */
export function TokenQuotaControls({ user, editable, busy, onSetLimit, onExtend, onReset }: {
  user: User;
  editable: boolean;
  busy: boolean;
  onSetLimit: (limit: number | null) => Promise<unknown>;
  onExtend: (add: number) => Promise<unknown>;
  onReset: () => Promise<unknown>;
}) {
  const [amount, setAmount] = useState("");
  const [report, setReport] = useState<TokenUsageReport | null>(null);
  const [reportError, setReportError] = useState(false);
  const limit = user.token_limit ?? null;
  const used = user.tokens_used ?? 0;
  const percent = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const exhausted = limit !== null && used >= limit;
  const value = Number(amount.replace(/[^\d]/g, ""));
  const valid = Number.isInteger(value) && value > 0;

  async function toggleReport() {
    if (report) { setReport(null); return; }
    try { setReport(await adminApi.tokenUsage(user.id)); setReportError(false); } catch { setReportError(true); }
  }
  const run = (action: () => Promise<unknown>) => void action().then(() => setAmount("")).catch(() => {});

  if (user.role === "super_admin") return <p className="text-xs text-gray-500">مصرف توکن: نامحدود (مدیر ارشد هرگز محدود نمی‌شود)</p>;

  return <div className="w-full space-y-2 rounded-xl bg-slate-50 p-3 text-xs">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <span className="font-medium text-gray-700">مصرف توکن: {fa(used)}{limit !== null ? ` از ${fa(limit)}` : " (بدون سقف)"}</span>
      <button type="button" className="text-teal-700 hover:underline" onClick={() => void toggleReport()}>{report ? "بستن جزئیات" : "جزئیات مصرف"}</button>
    </div>
    {limit !== null && <div className="h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={`مصرف توکن ${user.email}`}>
      <div className={`h-full rounded-full transition-all ${exhausted ? "bg-rose-500" : percent >= 80 ? "bg-amber-500" : "bg-teal-600"}`} style={{ width: `${percent}%` }} />
    </div>}
    {exhausted && <p className="text-rose-700">سقف تمام شده است؛ کاربر تا تمدید یا ریست نمی‌تواند چت کند.</p>}
    {editable && <div className="flex flex-wrap items-center gap-2">
      <Input aria-label={`تعداد توکن برای ${user.email}`} inputMode="numeric" placeholder="تعداد توکن" value={amount} onChange={(event) => setAmount(event.target.value)} className="w-40" />
      <Button type="button" size="sm" variant="secondary" disabled={busy || !valid} onClick={() => run(() => onSetLimit(value))}>تعیین سقف</Button>
      <Button type="button" size="sm" variant="secondary" disabled={busy || !valid || limit === null} onClick={() => run(() => onExtend(value))}>تمدید (افزودن)</Button>
      <Button type="button" size="sm" variant="ghost" disabled={busy || used === 0} onClick={() => run(onReset)}>ریست مصرف</Button>
      <Button type="button" size="sm" variant="ghost" disabled={busy || limit === null} onClick={() => run(() => onSetLimit(null))}>حذف سقف</Button>
    </div>}
    {reportError && <p className="text-rose-700">دریافت جزئیات مصرف ناموفق بود.</p>}
    {report && <div className="space-y-1 border-t border-slate-200 pt-2 text-gray-700">
      <p>از {new Date(report.period_start).toLocaleDateString("fa-IR")} (دوره‌ی جاری):</p>
      {report.by_purpose.length === 0 ? <p className="text-gray-500">مصرفی ثبت نشده است.</p> : <ul className="space-y-0.5">{report.by_purpose.map((row) => <li key={`${row.purpose}-${row.counts_toward_quota}`}>
        {PURPOSE_LABEL[row.purpose] ?? row.purpose}: {fa(row.prompt_tokens + row.completion_tokens)} توکن ({fa(row.calls)} فراخوانی){row.counts_toward_quota ? "" : " — فقط ثبت، بدون محدودیت"}
      </li>)}</ul>}
      {report.daily.length > 0 && <p className="text-gray-500">مصرف روزانه (۳۰ روز اخیر): {report.daily.slice(-7).map((day) => `${new Date(day.date).toLocaleDateString("fa-IR", { month: "numeric", day: "numeric" })}: ${fa(day.tokens)}`).join(" · ")}</p>}
    </div>}
  </div>;
}
