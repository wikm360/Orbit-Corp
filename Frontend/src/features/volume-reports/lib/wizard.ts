/** Validation and helpers of the "new report" wizard. */

import { parseJalaliInput } from "./jalali";
import type { PeriodType } from "../types";

export const EXCEL_EXTENSIONS = [".xls", ".xlsx", ".xlsm"];
export const isExcelName = (name: string) => EXCEL_EXTENSIONS.some((ext) => name.toLowerCase().endsWith(ext));

export interface InfoDraft { title: string; periodType: PeriodType; start: string; end: string; label: string }

export interface InfoResult { errors: Partial<Record<keyof InfoDraft, string>>; startIso: string | null; endIso: string | null }

export function validateInfo(d: InfoDraft): InfoResult {
  const errors: InfoResult["errors"] = {};
  const startIso = parseJalaliInput(d.start);
  const endIso = parseJalaliInput(d.end);
  if (!d.title.trim()) errors.title = "عنوان گزارش را وارد کنید.";
  if (!startIso) errors.start = "تاریخ شروع را به‌صورت شمسی وارد کنید (مثلاً ۱۴۰۵/۰۶/۰۱).";
  if (!endIso) errors.end = "تاریخ پایان را به‌صورت شمسی وارد کنید (مثلاً ۱۴۰۵/۰۶/۳۱).";
  if (startIso && endIso && endIso < startIso) errors.end = "تاریخ پایان نباید قبل از شروع باشد.";
  if (!d.label.trim()) errors.label = "برچسب دوره را وارد کنید (مثلاً شهریور ۱۴۰۵).";
  return { errors, startIso, endIso };
}

/** Pre-selects the company whose name contains (or is contained in) the file's suggested company. */
export function matchSuggestedCompany(suggested: string | null | undefined, companies: { id: string; name: string }[]): string | null {
  const clean = (s: string) => s.replace(/^شرکت\s+/, "").replace(/\s+/g, " ").trim();
  if (!suggested) return null;
  const wanted = clean(suggested);
  const hit = companies.find((c) => clean(c.name) === wanted) ?? companies.find((c) => wanted.includes(clean(c.name)) || clean(c.name).includes(wanted));
  return hit?.id ?? null;
}

/** Files can be submitted when every selected file has a company. */
export const filesReady = (selection: Record<string, string>) => Object.keys(selection).length > 0 && Object.values(selection).every(Boolean);
