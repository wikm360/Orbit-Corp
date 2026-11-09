"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { documentsApi } from "@/features/documents/api/documentsApi";
import type { Document, Folder } from "@/features/documents/types";
import { Button } from "@/shared/components/ui/Button";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { volumeReportApi } from "../api/volumeReportApi";
import { Card, EmptyState, ErrorBox, fieldClass, LoadingBlock } from "../components/common";
import { ProgressCard } from "../components/ProgressCard";
import { ProjectPicker } from "../components/ProjectPicker";
import { SourceDetails } from "../components/SourcesPanel";
import { useRunProgress } from "../hooks/useRunProgress";
import { useWorkspaceProjects } from "../hooks/useWorkspaceProjects";
import { runSoon } from "../lib/defer";
import { suggestPeriodLabel, toFa } from "../lib/jalali";
import { STATUS_LABELS } from "../lib/status";
import { filesReady, isExcelName, matchSuggestedCompany, validateInfo, type InfoDraft } from "../lib/wizard";
import type { Company, Progress, ReportStatus, SelectedFile, SourceInfo } from "../types";

type Step = 1 | 2 | 3 | 4;
const STEP_TITLES: Record<Step, string> = { 1: "مشخصات", 2: "فایل‌ها", 3: "بازبینی و شروع", 4: "پیشرفت" };

interface FolderGroup {
  id: string;
  name: string;
  path: string;
  docs: Document[];
  suggestedCompanyId: string | null;
}

function getFolderPath(folderId: string | null | undefined, map: Map<string, Folder>): string[] {
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

function FileTypeBadge({ filename }: { filename: string }) {
  const isPdf = filename.toLowerCase().endsWith(".pdf");
  if (isPdf) {
    return (
      <span className="inline-flex shrink-0 items-center rounded-md bg-rose-50 px-1.5 py-0.5 text-[10px] font-black tracking-wider text-rose-700 border border-rose-200/70">
        PDF
      </span>
    );
  }
  return (
    <span className="inline-flex shrink-0 items-center rounded-md bg-emerald-50 px-1.5 py-0.5 text-[10px] font-black tracking-wider text-emerald-800 border border-emerald-200/70">
      XLSX
    </span>
  );
}

function FolderCheckbox({
  allSelected,
  someSelected,
  onChange,
  label,
}: {
  allSelected: boolean;
  someSelected: boolean;
  onChange: () => void;
  label: string;
}) {
  return (
    <input
      type="checkbox"
      aria-label={label}
      checked={allSelected}
      ref={(el) => {
        if (el) el.indeterminate = someSelected && !allSelected;
      }}
      onChange={onChange}
      className="h-4 w-4 rounded accent-teal-600 cursor-pointer"
    />
  );
}

function NewReportInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { projects, loading: projectsLoading, error: projectsError, canEditSettings } = useWorkspaceProjects();
  const [step, setStep] = useState<Step>(1);
  const [resumedProject, setResumedProject] = useState("");
  const [pickedProject, setProjectId] = useState(params.get("project") ?? "");
  const projectId = resumedProject || pickedProject || projects[0]?.id || "";
  const [info, setInfo] = useState<InfoDraft>({ title: "", periodType: "month", start: "", end: "", label: "" });
  const [labelEdited, setLabelEdited] = useState(false);
  const [touched, setTouched] = useState(false);
  const [reportId, setReportId] = useState<string | null>(params.get("report"));
  const [docs, setDocs] = useState<Document[] | null>(null);
  const [docsError, setDocsError] = useState<unknown>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [selection, setSelection] = useState<Record<string, string>>({}); // document_id -> company_id
  const [selected, setSelected] = useState<SelectedFile[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [onlySelected, setOnlySelected] = useState(false);
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(new Set());
  const [newCompany, setNewCompany] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [status, setStatus] = useState<ReportStatus>("draft");
  const [progress, setProgress] = useState<Progress | undefined>();
  const [sources, setSources] = useState<SourceInfo[] | null>(null);


  // Resume a draft created earlier (`?report=`): the project and period are already fixed.
  useEffect(() => {
    const existing = params.get("report");
    if (!existing) return;
    volumeReportApi.get(existing).then((r) => {
      setResumedProject(r.project_id);
      setInfo({ title: r.title, periodType: r.period_type, start: "", end: "", label: r.period_label });
      setReportId(r.id);
      setStep(2);
    }).catch((e) => setMessage(friendlyErrorMessage(e, "گزارش پیدا نشد.")));
  }, [params]);

  const loadDocs = useCallback(async () => {
    if (!projectId) return;
    setDocs(null);
    setDocsError(null);
    try {
      const [list, comps, folderList] = await Promise.all([
        documentsApi.list(projectId),
        volumeReportApi.settings.companies(),
        documentsApi.listFolders(projectId).catch(() => []),
      ]);
      setDocs(list.filter((d) => d.status === "ready" && isExcelName(d.filename)));
      setCompanies(comps.filter((c) => c.is_active));
      setFolders(folderList ?? []);
      const preselected = (params.get("docs") ?? "").split(",").filter(Boolean);
      if (preselected.length) setSelection((s) => ({ ...Object.fromEntries(preselected.map((id) => [id, ""])), ...s }));
    } catch (e) { setDocsError(e); }
  }, [projectId, params]);
  useEffect(() => runSoon(() => { if (step === 2) void loadDocs(); }), [step, loadDocs]);

  const validation = useMemo(() => validateInfo(info), [info]);
  function patchInfo(patch: Partial<InfoDraft>) {
    setInfo((current) => {
      const next = { ...current, ...patch };
      if (!labelEdited && !("label" in patch)) {
        const v = validateInfo(next);
        if (v.startIso && v.endIso) next.label = suggestPeriodLabel(next.periodType, v.startIso, v.endIso);
      }
      return next;
    });
  }

  const folderMap = useMemo(() => {
    return new Map<string, Folder>((folders ?? []).map((f) => [f.id, f]));
  }, [folders]);

  const folderGroups = useMemo<FolderGroup[]>(() => {
    if (!docs) return [];
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
        docs: rootDocs.sort((a, b) => a.filename.localeCompare(b.filename, "fa")),
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
      const suggestedCompanyId =
        matchSuggestedCompany(folderName, companies) ||
        matchSuggestedCompany(pathStr, companies);

      folderEntries.push({
        id: fid,
        name: folderName,
        path: pathStr,
        docs: fDocs.sort((a, b) => a.filename.localeCompare(b.filename, "fa")),
        suggestedCompanyId,
      });
    }

    folderEntries.sort((a, b) => a.path.localeCompare(b.path, "fa"));
    result.push(...folderEntries);
    return result;
  }, [docs, folderMap, companies]);

  const filteredGroups = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q && !onlySelected) return folderGroups;

    return folderGroups
      .map((group) => {
        const matchFolder = q && (group.name.toLowerCase().includes(q) || group.path.toLowerCase().includes(q));
        const filteredDocs = group.docs.filter((d) => {
          if (onlySelected && !(d.id in selection)) return false;
          if (!q) return true;
          if (matchFolder) return true;
          return d.filename.toLowerCase().includes(q);
        });
        return { ...group, docs: filteredDocs };
      })
      .filter((group) => group.docs.length > 0);
  }, [folderGroups, searchQuery, onlySelected, selection]);

  const toggleFolderCollapse = (id: string) => {
    setCollapsedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const expandAll = () => setCollapsedFolders(new Set());
  const collapseAll = () => setCollapsedFolders(new Set(folderGroups.map((g) => g.id)));

  const toggleFolderSelect = (group: FolderGroup) => {
    const allSelected = group.docs.every((d) => d.id in selection);
    setSelection((prev) => {
      const next = { ...prev };
      if (allSelected) {
        for (const d of group.docs) delete next[d.id];
      } else {
        for (const d of group.docs) {
          if (!(d.id in next) || !next[d.id]) {
            const autoComp =
              matchSuggestedCompany(d.filename, companies) ||
              group.suggestedCompanyId ||
              "";
            next[d.id] = next[d.id] || autoComp;
          }
        }
      }
      return next;
    });
  };

  const setCompanyForFolder = (group: FolderGroup, companyId: string) => {
    if (!companyId) return;
    setSelection((prev) => {
      const next = { ...prev };
      for (const d of group.docs) {
        next[d.id] = companyId;
      }
      return next;
    });
  };

  async function goFiles() {
    setTouched(true);
    if (Object.keys(validation.errors).length || !projectId) return;
    setBusy(true);
    setMessage(null);
    try {
      if (!reportId) {
        const created = await volumeReportApi.create({
          project_id: projectId, title: info.title.trim(), period_type: info.periodType, period_start: validation.startIso!, period_end: validation.endIso!, period_label: info.label.trim(),
        });
        setReportId(created.id);
      }
      setStep(2);
    } catch (e) { setMessage(friendlyErrorMessage(e, "ساخت گزارش ناموفق بود.")); } finally { setBusy(false); }
  }

  async function goReview() {
    if (!reportId || !filesReady(selection)) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await volumeReportApi.setFiles(reportId, Object.entries(selection).map(([document_id, company_id]) => ({ document_id, company_id })));
      setSelected(result);
      setStep(3);
    } catch (e) { setMessage(friendlyErrorMessage(e, "ثبت فایل‌ها ناموفق بود.")); } finally { setBusy(false); }
  }

  async function addCompany() {
    try {
      const company = await volumeReportApi.settings.createCompany(newCompany.trim());
      setCompanies((c) => [...c, company]);
      setNewCompany("");
    } catch (e) { setMessage(friendlyErrorMessage(e, "افزودن شرکت ناموفق بود (فقط مدیر یا سرپرست تیم).")); }
  }

  async function start() {
    if (!reportId) return;
    setBusy(true);
    setMessage(null);
    try {
      await volumeReportApi.run(reportId);
      setStatus("processing");
      setStep(4);
    } catch (e) { setMessage(friendlyErrorMessage(e, "شروع اجرا ناموفق بود.")); } finally { setBusy(false); }
  }

  useRunProgress(reportId ?? "", step === 4 && status === "processing" && Boolean(reportId), (p) => setProgress(p.progress), async (last) => {
    setStatus(last?.status ?? "failed");
    if (reportId) setSources(await volumeReportApi.sources(reportId).catch(() => []));
  });

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4 md:p-6">
      <header>
        <Link href="/volume-reports" className="text-xs text-teal-700 hover:underline">← همه‌ی گزارش‌ها</Link>
        <h1 className="mt-1 text-lg font-semibold text-slate-900">ساخت گزارش حجم عملیات</h1>
      </header>
      <ol className="flex flex-wrap gap-2 text-xs" aria-label="مراحل">
        {([1, 2, 3, 4] as Step[]).map((s) => (
          <li key={s} aria-current={s === step ? "step" : undefined} className={`rounded-full px-3 py-1 ${s === step ? "bg-teal-700 text-white" : s < step ? "bg-teal-50 text-teal-800" : "bg-slate-100 text-slate-500"}`}>{toFa(s)}. {STEP_TITLES[s]}</li>
        ))}
      </ol>
      {message && <p role="alert" className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{message}</p>}

      {step === 1 && (
        <Card title="مشخصات گزارش">
          {projectsLoading ? <LoadingBlock /> : projectsError ? <ErrorBox error={projectsError} /> : (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2"><ProjectPicker projects={projects} value={projectId} onChange={setProjectId} /></div>
              <label className="space-y-1 text-sm md:col-span-2">عنوان
                <input value={info.title} onChange={(e) => patchInfo({ title: e.target.value })} className={fieldClass} placeholder="گزارش حجم عملیات شهریور ۱۴۰۵" />
                {touched && validation.errors.title && <span className="text-xs text-red-600">{validation.errors.title}</span>}
              </label>
              <fieldset className="space-y-1 text-sm"><legend>نوع دوره</legend>
                <div className="flex gap-4">
                  {([["month", "ماهانه"], ["week", "هفتگی"]] as const).map(([v, l]) => (
                    <label key={v} className="flex items-center gap-1.5"><input type="radio" name="period" checked={info.periodType === v} onChange={() => patchInfo({ periodType: v })} className="accent-teal-600" /> {l}</label>
                  ))}
                </div>
              </fieldset>
              <label className="space-y-1 text-sm">برچسب دوره
                <input value={info.label} onChange={(e) => { setLabelEdited(true); patchInfo({ label: e.target.value }); }} className={fieldClass} placeholder="شهریور ۱۴۰۵" />
                {touched && validation.errors.label && <span className="text-xs text-red-600">{validation.errors.label}</span>}
              </label>
              <label className="space-y-1 text-sm">از تاریخ (شمسی)
                <input dir="ltr" inputMode="numeric" value={info.start} onChange={(e) => patchInfo({ start: e.target.value })} className={`${fieldClass} text-left`} placeholder="1405/06/01" />
                {touched && validation.errors.start && <span className="text-xs text-red-600">{validation.errors.start}</span>}
              </label>
              <label className="space-y-1 text-sm">تا تاریخ (شمسی)
                <input dir="ltr" inputMode="numeric" value={info.end} onChange={(e) => patchInfo({ end: e.target.value })} className={`${fieldClass} text-left`} placeholder="1405/06/31" />
                {touched && validation.errors.end && <span className="text-xs text-red-600">{validation.errors.end}</span>}
              </label>
              <p className="text-xs text-slate-500 md:col-span-2">دوره را شما تعیین می‌کنید؛ ماه نوشته‌شده در عنوان شیت‌ها فقط برای هشدار بررسی می‌شود.</p>
              <div className="md:col-span-2"><Button onClick={() => void goFiles()} isLoading={busy} disabled={!projectId}>بعدی: انتخاب فایل‌ها</Button></div>
            </div>
          )}
        </Card>
      )}

      {step === 2 && (
        <Card title="فایل‌های ورودی پروژه (اکسل و PDF)">
          {docsError ? (
            <ErrorBox error={docsError} onRetry={() => void loadDocs()} />
          ) : !docs ? (
            <LoadingBlock />
          ) : docs.length === 0 ? (
            <EmptyState
              title="فایل اکسل یا PDF آماده‌ای در این پروژه نیست"
              hint="فایل‌های .xls/.xlsx/.xlsm/.pdf باید در فایل‌منیجر پروژه آپلود و پردازششان تمام شده باشد."
              action={
                <Link href="/documents" className="text-sm text-teal-700 underline">
                  رفتن به اسناد
                </Link>
              }
            />
          ) : (
            <div className="space-y-4">
              {/* Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-50 p-3.5 border border-slate-200/80">
                <div className="flex flex-1 min-w-[240px] items-center gap-2">
                  <div className="relative w-full">
                    <input
                      type="search"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="جستجو در فایل‌ها یا پوشه‌ها…"
                      className="w-full rounded-xl border border-slate-200 bg-white pe-3 ps-8 py-2 text-xs text-slate-800 placeholder-slate-400 shadow-2xs focus:border-teal-500 focus:outline-teal-600"
                    />
                    <span className="absolute inset-y-0 start-2.5 flex items-center text-slate-400 text-xs pointer-events-none">
                      🔍
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-xs">
                  <label className="flex items-center gap-1.5 cursor-pointer text-slate-700 select-none font-medium">
                    <input
                      type="checkbox"
                      checked={onlySelected}
                      onChange={(e) => setOnlySelected(e.target.checked)}
                      className="h-4 w-4 rounded accent-teal-600 cursor-pointer"
                    />
                    <span>فقط انتخاب‌شده‌ها ({toFa(Object.keys(selection).length)})</span>
                  </label>

                  <div className="h-4 w-px bg-slate-200" />

                  <button
                    type="button"
                    onClick={expandAll}
                    className="font-medium text-teal-700 hover:underline"
                  >
                    باز کردن همه
                  </button>
                  <span className="text-slate-300">·</span>
                  <button
                    type="button"
                    onClick={collapseAll}
                    className="font-medium text-slate-500 hover:underline"
                  >
                    بستن همه
                  </button>
                </div>
              </div>

              {/* Status info row */}
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 px-1">
                <span>
                  نمایش {toFa(filteredGroups.reduce((acc, g) => acc + g.docs.length, 0))} فایل در{" "}
                  {toFa(filteredGroups.length)} پوشه (مجموع: {toFa(docs.length)} فایل)
                </span>
                <span className="font-semibold text-teal-800">
                  {toFa(Object.keys(selection).length)} فایل انتخاب شده
                </span>
              </div>

              {/* Folder Groups */}
              {filteredGroups.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 p-8 text-center text-xs text-slate-500 bg-slate-50/50">
                  هیچ فایلی با فیلتر یا عبارت جستجوی فعلی همخوانی ندارد.
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredGroups.map((group) => {
                    const isCollapsed = collapsedFolders.has(group.id);
                    const selectedInGroup = group.docs.filter((d) => d.id in selection).length;
                    const isAllSelected = group.docs.length > 0 && selectedInGroup === group.docs.length;
                    const isSomeSelected = selectedInGroup > 0 && !isAllSelected;

                    return (
                      <div
                        key={group.id}
                        className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-2xs transition-shadow hover:shadow-xs"
                      >
                        {/* Folder Header */}
                        <div
                          className="flex flex-wrap items-center justify-between gap-2.5 border-b border-slate-100 bg-slate-50/80 px-4 py-3 cursor-pointer select-none transition hover:bg-slate-100/70"
                          onClick={() => toggleFolderCollapse(group.id)}
                        >
                          <div className="flex min-w-0 flex-1 items-center gap-2.5">
                            <span className="text-xs text-slate-400 font-bold transition-transform">
                              {isCollapsed ? "◀" : "▼"}
                            </span>

                            <div onClick={(e) => e.stopPropagation()}>
                              <FolderCheckbox
                                allSelected={isAllSelected}
                                someSelected={isSomeSelected}
                                onChange={() => toggleFolderSelect(group)}
                                label={`انتخاب همه فایل‌های پوشه ${group.name}`}
                              />
                            </div>

                            <span className="text-base">📁</span>

                            <div className="flex min-w-0 items-center gap-2">
                              <span className="truncate text-sm font-bold text-slate-800">
                                {group.name}
                              </span>
                              {group.path !== group.name && (
                                <span className="hidden text-xs text-slate-400 sm:inline truncate max-w-[200px]">
                                  ({group.path})
                                </span>
                              )}
                            </div>

                            <span className="rounded-full bg-slate-200/70 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                              {toFa(group.docs.length)} فایل
                            </span>

                            {selectedInGroup > 0 && (
                              <span className="rounded-full bg-teal-100 px-2 py-0.5 text-[11px] font-bold text-teal-800">
                                {toFa(selectedInGroup)} انتخاب‌شده
                              </span>
                            )}
                          </div>

                          <div
                            className="flex items-center gap-2"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <select
                              value=""
                              onChange={(e) => setCompanyForFolder(group, e.target.value)}
                              className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 shadow-2xs hover:border-teal-500 focus:outline-teal-600"
                              title="تخصیص شرکت به همه فایل‌های این پوشه"
                            >
                              <option value="">تخصیص شرکت به کل پوشه…</option>
                              {companies.map((c) => (
                                <option key={c.id} value={c.id}>
                                  {c.name}
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>

                        {/* File Items */}
                        {!isCollapsed && (
                          <ul className="divide-y divide-slate-100 bg-white">
                            {group.docs.map((d) => {
                              const on = d.id in selection;
                              const assignedCompany = selection[d.id] ?? "";
                              const isMissingCompany = on && !assignedCompany;

                              return (
                                <li
                                  key={d.id}
                                  className={`flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 transition ${
                                    on ? "bg-teal-50/30" : "hover:bg-slate-50/60"
                                  }`}
                                >
                                  <label className="flex min-w-0 flex-1 items-center gap-2.5 cursor-pointer">
                                    <input
                                      type="checkbox"
                                      checked={on}
                                      onChange={(e) =>
                                        setSelection((s) => {
                                          const next = { ...s };
                                          if (e.target.checked) {
                                            const auto =
                                              matchSuggestedCompany(d.filename, companies) ||
                                              group.suggestedCompanyId ||
                                              "";
                                            next[d.id] = auto;
                                          } else {
                                            delete next[d.id];
                                          }
                                          return next;
                                        })
                                      }
                                      className="h-4 w-4 rounded accent-teal-600 cursor-pointer"
                                    />
                                    <FileTypeBadge filename={d.filename} />
                                    <span
                                      className="truncate text-sm font-medium text-slate-800"
                                      dir="auto"
                                      title={d.filename}
                                    >
                                      {d.filename}
                                    </span>
                                  </label>

                                  {on && (
                                    <div className="flex items-center gap-2 shrink-0">
                                      <select
                                        aria-label={`شرکت ${d.filename}`}
                                        value={assignedCompany}
                                        onChange={(e) =>
                                          setSelection((s) => ({ ...s, [d.id]: e.target.value }))
                                        }
                                        className={`${fieldClass} text-xs py-1.5 max-w-[14rem] ${
                                          isMissingCompany
                                            ? "border-amber-400 bg-amber-50/60 ring-1 ring-amber-300"
                                            : ""
                                        }`}
                                      >
                                        <option value="">شرکت را انتخاب کنید…</option>
                                        {companies.map((c) => (
                                          <option key={c.id} value={c.id}>
                                            {c.name}
                                          </option>
                                        ))}
                                      </select>
                                    </div>
                                  )}
                                </li>
                              );
                            })}
                          </ul>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Missing company warning */}
              {Object.keys(selection).length > 0 &&
                Object.values(selection).some((c) => !c) && (
                  <div className="flex items-center gap-2 rounded-xl bg-amber-50 px-4 py-2.5 text-xs text-amber-900 border border-amber-200/80">
                    <span className="text-sm">⚠️</span>
                    <span>
                      برای{" "}
                      {toFa(Object.values(selection).filter((c) => !c).length)} فایل
                      انتخاب‌شده هنوز شرکتی تعیین نشده است. لطفاً شرکت هر فایل را
                      مشخص کنید تا بتوانید ادامه دهید.
                    </span>
                  </div>
                )}

              {/* Add company section */}
              <div className="flex flex-wrap items-center gap-2 rounded-xl bg-slate-50 p-3 text-xs border border-slate-200/70">
                <span className="text-slate-600 font-medium">شرکت در فهرست نیست؟</span>
                <input
                  aria-label="شرکت جدید"
                  value={newCompany}
                  onChange={(e) => setNewCompany(e.target.value)}
                  placeholder="نام شرکت"
                  className={`${fieldClass} max-w-[14rem]`}
                />
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={!newCompany.trim() || !canEditSettings}
                  onClick={() => void addCompany()}
                >
                  افزودن
                </Button>
                {!canEditSettings && (
                  <span className="text-slate-400">
                    افزودن شرکت فقط برای مدیر یا سرپرست تیم ممکن است.
                  </span>
                )}
              </div>

              {/* Navigation buttons */}
              <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-100">
                <Button variant="ghost" onClick={() => setStep(1)}>
                  قبلی
                </Button>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">
                    {toFa(Object.keys(selection).length)} فایل انتخاب‌شده
                  </span>
                  <Button
                    onClick={() => void goReview()}
                    isLoading={busy}
                    disabled={!filesReady(selection)}
                  >
                    بعدی ({toFa(Object.keys(selection).length)} فایل)
                  </Button>
                </div>
              </div>
            </div>
          )}
        </Card>
      )}

      {step === 3 && (
        <Card title="بازبینی پیش از اجرا">
          <ul className="space-y-2 text-sm">
            {selected.map((f) => {
              const suggested = matchSuggestedCompany(f.suggested_company, companies);
              const current = selection[f.document_id ?? ""] ?? f.company_id;
              return (
                <li key={f.id} className="rounded-xl border border-slate-200 p-3">
                  <div className="font-medium">{f.filename}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                    شرکت: {companies.find((c) => c.id === current)?.name ?? "—"}
                    {f.suggested_company && <span className="rounded bg-sky-50 px-2 py-0.5 text-sky-800">پیشنهاد از روی فایل: {f.suggested_company}</span>}
                    {suggested && suggested !== current && f.document_id && (
                      <Button size="sm" variant="secondary" onClick={() => { setSelection((s) => ({ ...s, [f.document_id!]: suggested })); setStep(2); }}>استفاده از پیشنهاد</Button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs text-slate-500">دوره‌ی گزارش: {info.label || "—"}. شیت‌های برنامه‌ای و پنهان به‌صورت خودکار خوانده نمی‌شوند؛ پس از اجرا فهرست کامل شیت‌ها و هشدارها را می‌بینید.</p>
          <div className="mt-4 flex gap-2"><Button variant="ghost" onClick={() => setStep(2)}>قبلی</Button><Button onClick={() => void start()} isLoading={busy}>شروع اجرا</Button></div>
        </Card>
      )}

      {step === 4 && (
        <div className="space-y-4">
          {status === "processing" ? <ProgressCard progress={progress} /> : (
            <Card title={`اجرا پایان یافت — ${STATUS_LABELS[status]}`}>
              <p className="text-sm text-slate-600">
                {status === "awaiting_user" ? "چند مورد منتظر پاسخ شماست." : status === "needs_review" ? "نتایج آماده‌اند ولی برخی موارد تأیید نشده‌اند." : status === "ready" ? "همه‌چیز تأیید شده و گزارش آماده‌ی انتشار است." : status === "failed" ? "اجرا ناموفق بود؛ جزئیات را در صفحه‌ی گزارش ببینید." : ""}
              </p>
              <div className="mt-3 flex gap-2">
                <Button onClick={() => router.push(`/volume-reports/${reportId}`)}>باز کردن گزارش</Button>
                {(status === "awaiting_user" || status === "needs_review") && <Button variant="secondary" onClick={() => router.push(`/volume-reports?tab=review&project=${projectId}`)}>رفتن به صف بازبینی</Button>}
              </div>
            </Card>
          )}
          {sources && <SourceDetails sources={sources} />}
        </div>
      )}
    </div>
  );
}

export function NewReportScreen() {
  return <Suspense fallback={<LoadingBlock />}><NewReportInner /></Suspense>;
}

