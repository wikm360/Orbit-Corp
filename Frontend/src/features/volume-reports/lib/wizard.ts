/** Validation and helpers of the "new report" wizard and report file selection. */

import type { Document, Folder } from "@/features/documents/types";
import { parseJalaliInput } from "./jalali";
import type { FileSelection, PeriodType, ReportFileInfo } from "../types";

export const SUPPORTED_EXTENSIONS = [".xls", ".xlsx", ".xlsm", ".pdf"];
export const EXCEL_EXTENSIONS = SUPPORTED_EXTENSIONS;
export const isSupportedName = (name: string) => SUPPORTED_EXTENSIONS.some((ext) => name.toLowerCase().endsWith(ext));
export const isExcelName = isSupportedName;

export interface FolderGroup {
  id: string;
  name: string;
  path: string;
  docs: Document[];
  suggestedCompanyId: string | null;
}

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

export function getFolderPath(folderId: string | null | undefined, map: Map<string, Folder>): string[] {
  const parts: string[] = [];
  let cur = folderId;
  const seen = new Set<string>();
  while (cur && map.has(cur) && !seen.has(cur)) {
    seen.add(cur);
    const f = map.get(cur)!;
    parts.unshift(f.name);
    cur = f.parent_id;
  }
  return parts;
}

export function buildFolderGroups(docs: Document[], folders: Folder[], companies: { id: string; name: string }[]): FolderGroup[] {
  const folderMap = new Map<string, Folder>(folders.map((f) => [f.id, f]));
  const map = new Map<string | null, Document[]>();
  for (const d of docs) {
    const fid = d.folder_id ?? null;
    if (!map.has(fid)) map.set(fid, []);
    map.get(fid)!.push(d);
  }

  const result: FolderGroup[] = [];
  const rootDocs = map.get(null) ?? [];
  if (rootDocs.length > 0) {
    result.push({
      id: "__root__",
      name: "فایل‌های ریشه پروژه",
      path: "ریشه پروژه",
      docs: [...rootDocs].sort((a, b) => a.filename.localeCompare(b.filename, "fa")),
      suggestedCompanyId: null,
    });
  }

  const nonRootFolderIds = Array.from(map.keys()).filter((fid): fid is string => fid !== null);
  const folderEntries: FolderGroup[] = [];
  for (const fid of nonRootFolderIds) {
    const fDocs = map.get(fid) ?? [];
    const pathParts = getFolderPath(fid, folderMap);
    const pathStr = pathParts.length > 0 ? pathParts.join(" / ") : "پوشه نامشخص";
    const folderObj = folderMap.get(fid);
    const folderName = folderObj?.name ?? pathStr;
    const suggestedCompanyId = matchSuggestedCompany(folderName, companies) || matchSuggestedCompany(pathStr, companies);
    folderEntries.push({
      id: fid,
      name: folderName,
      path: pathStr,
      docs: [...fDocs].sort((a, b) => a.filename.localeCompare(b.filename, "fa")),
      suggestedCompanyId,
    });
  }

  folderEntries.sort((a, b) => a.path.localeCompare(b.path, "fa"));
  result.push(...folderEntries);
  return result;
}

export function filterFolderGroups(
  folderGroups: FolderGroup[],
  searchQuery: string,
  onlySelected: boolean,
  selection: Record<string, string>,
): FolderGroup[] {
  const q = searchQuery.trim().toLowerCase();
  if (!q && !onlySelected) return folderGroups;
  return folderGroups
    .map((group) => {
      const matchFolder = Boolean(q && (group.name.toLowerCase().includes(q) || group.path.toLowerCase().includes(q)));
      const filteredDocs = group.docs.filter((d) => {
        if (onlySelected && !(d.id in selection)) return false;
        if (!q) return true;
        if (matchFolder) return true;
        return d.filename.toLowerCase().includes(q);
      });
      return { ...group, docs: filteredDocs };
    })
    .filter((group) => group.docs.length > 0);
}

/** A file that is not a normal report file: a monthly volume forecast or a monthly PV plan, with its Jalali month (0 = read it from the file). */
export interface MonthlyChoice { kind: "monthly_plan" | "monthly_pv"; month: number }

export function selectionToPayload(selection: Record<string, string>, monthly: Record<string, MonthlyChoice>): FileSelection[] {
  return Object.entries(selection).map(([document_id, company_id]) => {
    const choice = monthly[document_id];
    return choice
      ? { document_id, company_id, kind: choice.kind, ...(choice.month ? { plan_month: choice.month } : {}) }
      : { document_id, company_id };
  });
}

export function seedSelectionFromReportFiles(files: ReportFileInfo[]): {
  selection: Record<string, string>;
  monthly: Record<string, MonthlyChoice>;
} {
  const selection: Record<string, string> = {};
  const monthly: Record<string, MonthlyChoice> = {};
  for (const f of files) {
    if (!f.document_id) continue;
    selection[f.document_id] = f.company_id;
    if (f.kind === "monthly_plan" || f.kind === "monthly_pv") monthly[f.document_id] = { kind: f.kind, month: f.plan_month ?? 0 };
  }
  return { selection, monthly };
}
