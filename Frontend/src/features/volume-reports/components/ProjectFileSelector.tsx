"use client";

import { type ChangeEvent, type Dispatch, type DragEvent, type SetStateAction, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { documentsApi } from "@/features/documents/api/documentsApi";
import type { Document, Folder } from "@/features/documents/types";
import { Button } from "@/shared/components/ui/Button";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { JALALI_MONTHS, toFa } from "../lib/jalali";
import {
  buildFolderGroups, filterFolderGroups, getFolderPath, isExcelName, matchSuggestedCompany, type FolderGroup, type MonthlyChoice,
} from "../lib/wizard";
import type { Company, ReportFileInfo } from "../types";
import { fieldClass } from "./common";

interface UploadTrackItem {
  id: string;
  filename: string;
  status: Document["status"];
  error?: string | null;
}

const ATTACHED_STATUS_STYLE: Record<ReportFileInfo["status"], { label: string; cls: string }> = {
  parsed: { label: "در گزارش · خوانده‌شده", cls: "bg-emerald-50 text-emerald-700 border-emerald-200/80" },
  pending: { label: "در گزارش · در انتظار پردازش", cls: "bg-amber-50 text-amber-800 border-amber-200/80" },
  failed: { label: "در گزارش · ناموفق", cls: "bg-rose-50 text-rose-700 border-rose-200/80" },
};

export function FileTypeBadge({ filename }: { filename: string }) {
  const isPdf = filename.toLowerCase().endsWith(".pdf");
  return isPdf ? (
    <span className="inline-flex shrink-0 items-center rounded-md border border-rose-200/70 bg-rose-50 px-1.5 py-0.5 text-[10px] font-black tracking-wider text-rose-700">
      PDF
    </span>
  ) : (
    <span className="inline-flex shrink-0 items-center rounded-md border border-emerald-200/70 bg-emerald-50 px-1.5 py-0.5 text-[10px] font-black tracking-wider text-emerald-800">
      XLSX
    </span>
  );
}

function FolderCheckbox({
  allSelected, someSelected, disabled, onChange, label,
}: {
  allSelected: boolean; someSelected: boolean; disabled?: boolean; onChange: () => void; label: string;
}) {
  return (
    <input
      type="checkbox"
      aria-label={label}
      checked={allSelected}
      disabled={disabled}
      ref={(el) => {
        if (el) el.indeterminate = someSelected && !allSelected;
      }}
      onChange={onChange}
      className="h-4 w-4 cursor-pointer rounded accent-teal-600 disabled:cursor-not-allowed disabled:opacity-50"
    />
  );
}

export interface ProjectFileSelectorProps {
  projectId: string;
  docs: Document[];
  folders: Folder[];
  companies: Company[];
  selection: Record<string, string>;
  setSelection: Dispatch<SetStateAction<Record<string, string>>>;
  monthly: Record<string, MonthlyChoice>;
  setMonthly: Dispatch<SetStateAction<Record<string, MonthlyChoice>>>;
  canUpload?: boolean;
  canEditSettings?: boolean;
  onAddCompany?: (name: string) => Promise<void>;
  onDocsChange?: (docs: Document[]) => void;
  onPendingUploadsChange?: (hasPending: boolean) => void;
  attachedFilesByDocId?: Map<string, ReportFileInfo>;
  listMaxHeightClass?: string;
}

export function ProjectFileSelector({
  projectId,
  docs,
  folders,
  companies,
  selection,
  setSelection,
  monthly,
  setMonthly,
  canUpload = false,
  canEditSettings = false,
  onAddCompany,
  onDocsChange,
  onPendingUploadsChange,
  attachedFilesByDocId,
  listMaxHeightClass = "max-h-[460px]",
}: ProjectFileSelectorProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [onlySelected, setOnlySelected] = useState(false);
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(new Set());
  const [targetFolderId, setTargetFolderId] = useState("");
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadFraction, setUploadFraction] = useState(0);
  const [uploadNotice, setUploadNotice] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [trackedUploads, setTrackedUploads] = useState<UploadTrackItem[]>([]);
  const [newCompany, setNewCompany] = useState("");
  const [addingCompany, setAddingCompany] = useState(false);

  const companiesRef = useRef(companies);
  const foldersRef = useRef(folders);
  const attachedRef = useRef(attachedFilesByDocId);
  const onDocsChangeRef = useRef(onDocsChange);
  useEffect(() => { companiesRef.current = companies; }, [companies]);
  useEffect(() => { foldersRef.current = folders; }, [folders]);
  useEffect(() => { attachedRef.current = attachedFilesByDocId; }, [attachedFilesByDocId]);
  useEffect(() => { onDocsChangeRef.current = onDocsChange; }, [onDocsChange]);

  const folderMap = useMemo(() => new Map(folders.map((f) => [f.id, f])), [folders]);
  const folderOptions = useMemo(() => {
    return folders
      .map((f) => ({ id: f.id, label: getFolderPath(f.id, folderMap).join(" / ") || f.name }))
      .sort((a, b) => a.label.localeCompare(b.label, "fa"));
  }, [folders, folderMap]);

  const folderGroups = useMemo(() => buildFolderGroups(docs, folders, companies), [docs, folders, companies]);
  const filteredGroups = useMemo(
    () => filterFolderGroups(folderGroups, searchQuery, onlySelected, selection),
    [folderGroups, searchQuery, onlySelected, selection],
  );

  const hasProcessingUploads = trackedUploads.some((t) => t.status === "processing");
  useEffect(() => {
    onPendingUploadsChange?.(uploading || hasProcessingUploads);
  }, [uploading, hasProcessingUploads, onPendingUploadsChange]);

  const autoSelectReadyDocs = useCallback((readyDocs: Document[]) => {
    if (!readyDocs.length) return;
    const fMap = new Map(foldersRef.current.map((f) => [f.id, f]));
    setSelection((prev) => {
      const next = { ...prev };
      for (const doc of readyDocs) {
        if (attachedRef.current?.has(doc.id)) continue;
        if (doc.id in next && next[doc.id]) continue;
        const folderPath = doc.folder_id ? getFolderPath(doc.folder_id, fMap).join(" / ") : "";
        const autoComp =
          matchSuggestedCompany(doc.filename, companiesRef.current) ||
          matchSuggestedCompany(folderPath, companiesRef.current) ||
          "";
        next[doc.id] = autoComp;
      }
      return next;
    });
  }, [setSelection]);

  // Poll project documents while any newly uploaded file is still in worker ingestion.
  const trackingProcessingIds = useMemo(
    () => trackedUploads.filter((u) => u.status === "processing").map((u) => u.id).join(","),
    [trackedUploads],
  );

  useEffect(() => {
    if (!trackingProcessingIds || !projectId) return;
    let active = true;
    const idSet = new Set(trackingProcessingIds.split(",").filter(Boolean));

    const poll = async () => {
      try {
        const list = await documentsApi.list(projectId);
        if (!active) return;
        const readyDocs = list.filter((d) => d.status === "ready" && isExcelName(d.filename));
        onDocsChangeRef.current?.(readyDocs);

        const newlyReady: Document[] = [];
        const byId = new Map(list.map((d) => [d.id, d]));
        setTrackedUploads((prev) =>
          prev.map((item) => {
            if (!idSet.has(item.id)) return item;
            const latest = byId.get(item.id);
            if (!latest) return item;
            if (latest.status === "ready" && item.status !== "ready") newlyReady.push(latest);
            return { ...item, status: latest.status, error: latest.error_message };
          }),
        );
        if (newlyReady.length) autoSelectReadyDocs(newlyReady);
      } catch {
        // Retry on next tick silently while modal remains open.
      }
    };

    const timer = window.setInterval(() => void poll(), 1200);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [trackingProcessingIds, projectId, autoSelectReadyDocs]);

  async function handleUploadFiles(fileList: FileList | File[] | null) {
    if (!fileList || !canUpload) return;
    const raw = Array.from(fileList);
    if (!raw.length) return;

    const valid: File[] = [];
    const rejectedNames: string[] = [];
    for (const f of raw) {
      if (f.name.startsWith("~$")) continue;
      if (!isExcelName(f.name) || f.size === 0) {
        rejectedNames.push(f.name);
        continue;
      }
      valid.push(f);
    }

    setUploadError(null);
    setUploadNotice(null);
    if (!valid.length) {
      setUploadError("فقط فایل‌های غیرخالی اکسل (.xls/.xlsx/.xlsm) و PDF قابل قبول هستند.");
      return;
    }

    setUploading(true);
    setUploadFraction(0);
    try {
      const response = await documentsApi.uploadBatch(projectId, valid, targetFolderId || null, setUploadFraction);
      const acceptedDocs = response.items
        .filter((i): i is Extract<typeof i, { status: "accepted" }> => i.status === "accepted" && Boolean(i.document))
        .map((i) => i.document!);
      const rejectedMsgs = [
        ...rejectedNames.map((n) => `${n}: فرمت پشتیبانی نمی‌شود`),
        ...response.items.filter((i) => i.status === "rejected").map((i) => `${i.filename}: ${i.error}`),
      ];
      if (rejectedMsgs.length) setUploadError(rejectedMsgs.join(" | "));

      if (acceptedDocs.length) {
        setTrackedUploads((prev) => {
          const map = new Map(prev.map((x) => [x.id, x]));
          for (const d of acceptedDocs) {
            map.set(d.id, { id: d.id, filename: d.filename, status: d.status, error: d.error_message });
          }
          return Array.from(map.values());
        });

        const freshList = await documentsApi.list(projectId);
        const readyDocs = freshList.filter((d) => d.status === "ready" && isExcelName(d.filename));
        onDocsChange?.(readyDocs);
        const readyUploaded = acceptedDocs.filter((d) => d.status === "ready" || readyDocs.some((r) => r.id === d.id));
        autoSelectReadyDocs(readyUploaded);

        const waiting = acceptedDocs.length - readyUploaded.length;
        setUploadNotice(
          waiting > 0
            ? `${toFa(acceptedDocs.length)} فایل آپلود شد؛ منتظر پایان پردازش اولیه (${toFa(waiting)} فایل)...`
            : `${toFa(acceptedDocs.length)} فایل آپلود و خودکار انتخاب شد.`,
        );
      }
    } catch (e) {
      setUploadError(friendlyErrorMessage(e, "آپلود فایل ناموفق بود."));
    } finally {
      setUploading(false);
      setUploadFraction(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function onFileInputChange(e: ChangeEvent<HTMLInputElement>) {
    void handleUploadFiles(e.target.files);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    if (canUpload) void handleUploadFiles(e.dataTransfer.files);
  }

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
    const selectableDocs = group.docs.filter((d) => !attachedFilesByDocId?.has(d.id));
    if (!selectableDocs.length) return;
    const allSelected = selectableDocs.every((d) => d.id in selection);
    setSelection((prev) => {
      const next = { ...prev };
      if (allSelected) {
        for (const d of selectableDocs) delete next[d.id];
      } else {
        for (const d of selectableDocs) {
          if (!(d.id in next) || !next[d.id]) {
            next[d.id] = matchSuggestedCompany(d.filename, companies) || group.suggestedCompanyId || "";
          }
        }
      }
      return next;
    });
  };

  const setCompanyForFolder = (group: FolderGroup, companyId: string) => {
    if (!companyId) return;
    const selectableDocs = group.docs.filter((d) => !attachedFilesByDocId?.has(d.id));
    setSelection((prev) => {
      const next = { ...prev };
      for (const d of selectableDocs) next[d.id] = companyId;
      return next;
    });
  };

  async function submitNewCompany() {
    if (!onAddCompany || !newCompany.trim()) return;
    setAddingCompany(true);
    try {
      await onAddCompany(newCompany.trim());
      setNewCompany("");
    } finally {
      setAddingCompany(false);
    }
  }

  const selectedCount = Object.keys(selection).length;
  const missingCompanyCount = Object.values(selection).filter((c) => !c).length;

  return (
    <div className="space-y-4">
      {canUpload ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={`rounded-2xl border-2 border-dashed p-3.5 transition ${
            dragging ? "border-teal-500 bg-teal-50/60" : "border-slate-200 bg-slate-50/70"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-0.5">
              <div className="text-xs font-semibold text-slate-800">آپلود مستقیم فایل‌های جدید (.xlsx / .xls / .xlsm / .pdf)</div>
              <div className="text-[11px] text-slate-500">
                فایل را اینجا بکشید یا انتخاب کنید؛ پس از آماده‌سازی به‌صورت خودکار انتخاب می‌شود.
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {folderOptions.length > 0 && (
                <select
                  aria-label="پوشه مقصد آپلود"
                  value={targetFolderId}
                  onChange={(e) => setTargetFolderId(e.target.value)}
                  className={`${fieldClass} text-xs py-1.5 max-w-[12rem]`}
                >
                  <option value="">پوشه: ریشه پروژه</option>
                  {folderOptions.map((fo) => <option key={fo.id} value={fo.id}>{fo.label}</option>)}
                </select>
              )}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".xls,.xlsx,.xlsm,.pdf"
                onChange={onFileInputChange}
                className="hidden"
              />
              <Button
                type="button"
                size="sm"
                variant="secondary"
                isLoading={uploading}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading ? `در حال آپلود (${toFa(Math.round(uploadFraction * 100))}٪)...` : "انتخاب فایل از سیستم"}
              </Button>
            </div>
          </div>

          {uploadNotice && <p className="mt-2 text-xs text-teal-800">{uploadNotice}</p>}
          {uploadError && <p className="mt-2 text-xs text-red-700">{uploadError}</p>}

          {trackedUploads.length > 0 && (
            <ul className="mt-2.5 flex flex-wrap gap-2">
              {trackedUploads.map((item) => {
                const badge =
                  item.status === "ready" ? { txt: "آماده و انتخاب شد ✓", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" }
                    : item.status === "processing" ? { txt: "در حال آماده‌سازی...", cls: "bg-sky-50 text-sky-800 border-sky-200" }
                      : { txt: `ناموفق (${item.error || item.status})`, cls: "bg-rose-50 text-rose-700 border-rose-200" };
                return (
                  <li key={item.id} className={`inline-flex items-center gap-1.5 rounded-lg border px-2 py-1 text-[11px] ${badge.cls}`}>
                    <span className="max-w-[14rem] truncate font-medium" dir="auto">{item.filename}</span>
                    <span>· {badge.txt}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : (
        <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          شما دسترسی آپلود سند در این پروژه ندارید؛ می‌توانید از فایل‌های آماده‌ی موجود در پروژه انتخاب کنید.
        </p>
      )}

      {docs.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-6 text-center text-xs text-slate-500">
          هنوز فایل اکسل یا PDF آماده‌ای در این پروژه نیست. از بخش بالا فایل آپلود کنید.
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/80 bg-slate-50 p-3">
            <div className="min-w-[220px] flex-1">
              <div className="relative w-full">
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="جستجو در فایل‌ها یا پوشه‌ها…"
                  className="w-full rounded-xl border border-slate-200 bg-white pe-3 ps-8 py-2 text-xs text-slate-800 placeholder-slate-400 shadow-2xs focus:border-teal-500 focus:outline-teal-600"
                />
                <span className="pointer-events-none absolute inset-y-0 start-2.5 flex items-center text-xs text-slate-400">🔍</span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs">
              <label className="flex cursor-pointer select-none items-center gap-1.5 font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={onlySelected}
                  onChange={(e) => setOnlySelected(e.target.checked)}
                  className="h-4 w-4 cursor-pointer rounded accent-teal-600"
                />
                <span>فقط انتخاب‌شده‌ها ({toFa(selectedCount)})</span>
              </label>
              <div className="h-4 w-px bg-slate-200" />
              <button type="button" onClick={expandAll} className="font-medium text-teal-700 hover:underline">باز کردن همه</button>
              <span className="text-slate-300">·</span>
              <button type="button" onClick={collapseAll} className="font-medium text-slate-500 hover:underline">بستن همه</button>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-xs text-slate-500">
            <span>
              نمایش {toFa(filteredGroups.reduce((acc, g) => acc + g.docs.length, 0))} فایل در {toFa(filteredGroups.length)} پوشه (مجموع: {toFa(docs.length)} فایل)
            </span>
            <span className="font-semibold text-teal-800">{toFa(selectedCount)} فایل انتخاب‌شده</span>
          </div>

          {filteredGroups.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-6 text-center text-xs text-slate-500">
              هیچ فایلی با فیلتر یا عبارت جستجوی فعلی همخوانی ندارد.
            </div>
          ) : (
            <div className={`space-y-3 overflow-y-auto pe-1 ${listMaxHeightClass}`}>
              {filteredGroups.map((group) => {
                const isCollapsed = collapsedFolders.has(group.id);
                const selectableDocs = group.docs.filter((d) => !attachedFilesByDocId?.has(d.id));
                const selectedInGroup = selectableDocs.filter((d) => d.id in selection).length;
                const isAllSelected = selectableDocs.length > 0 && selectedInGroup === selectableDocs.length;
                const isSomeSelected = selectedInGroup > 0 && !isAllSelected;

                return (
                  <div key={group.id} className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-2xs transition-shadow hover:shadow-xs">
                    <div
                      className="flex cursor-pointer select-none flex-wrap items-center justify-between gap-2.5 border-b border-slate-100 bg-slate-50/80 px-4 py-2.5 transition hover:bg-slate-100/70"
                      onClick={() => toggleFolderCollapse(group.id)}
                    >
                      <div className="flex min-w-0 flex-1 items-center gap-2.5">
                        <span className="text-xs font-bold text-slate-400">{isCollapsed ? "◀" : "▼"}</span>
                        <div onClick={(e) => e.stopPropagation()}>
                          <FolderCheckbox
                            allSelected={isAllSelected}
                            someSelected={isSomeSelected}
                            disabled={selectableDocs.length === 0}
                            onChange={() => toggleFolderSelect(group)}
                            label={`انتخاب همه فایل‌های پوشه ${group.name}`}
                          />
                        </div>
                        <span className="text-base">📁</span>
                        <div className="flex min-w-0 items-center gap-2">
                          <span className="truncate text-sm font-bold text-slate-800">{group.name}</span>
                          {group.path !== group.name && (
                            <span className="hidden max-w-[200px] truncate text-xs text-slate-400 sm:inline">({group.path})</span>
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

                      {selectableDocs.length > 0 && (
                        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                          <select
                            value=""
                            onChange={(e) => setCompanyForFolder(group, e.target.value)}
                            className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 shadow-2xs hover:border-teal-500 focus:outline-teal-600"
                            title="تخصیص شرکت به همه‌ی فایل‌های قابل‌انتخاب این پوشه"
                          >
                            <option value="">تخصیص شرکت به کل پوشه…</option>
                            {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                          </select>
                        </div>
                      )}
                    </div>

                    {!isCollapsed && (
                      <ul className="divide-y divide-slate-100 bg-white">
                        {group.docs.map((d) => {
                          const attached = attachedFilesByDocId?.get(d.id);
                          const on = d.id in selection;
                          const assignedCompany = selection[d.id] ?? "";
                          const isMissingCompany = on && !assignedCompany;

                          return (
                            <li
                              key={d.id}
                              className={`flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 transition ${
                                attached ? "bg-slate-50/70" : on ? "bg-teal-50/30" : "hover:bg-slate-50/60"
                              }`}
                            >
                              <label className={`flex min-w-0 flex-1 items-center gap-2.5 ${attached ? "cursor-default" : "cursor-pointer"}`}>
                                <input
                                  type="checkbox"
                                  checked={Boolean(attached) || on}
                                  disabled={Boolean(attached)}
                                  onChange={(e) =>
                                    setSelection((s) => {
                                      const next = { ...s };
                                      if (e.target.checked) {
                                        next[d.id] = matchSuggestedCompany(d.filename, companies) || group.suggestedCompanyId || "";
                                      } else {
                                        delete next[d.id];
                                        setMonthly((m) => { const rest = { ...m }; delete rest[d.id]; return rest; });
                                      }
                                      return next;
                                    })
                                  }
                                  className="h-4 w-4 cursor-pointer rounded accent-teal-600 disabled:cursor-not-allowed disabled:opacity-60"
                                />
                                <FileTypeBadge filename={d.filename} />
                                <span className="truncate text-sm font-medium text-slate-800" dir="auto" title={d.filename}>
                                  {d.filename}
                                </span>
                              </label>

                              {attached ? (
                                <div className="flex flex-wrap items-center gap-2 text-xs">
                                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-600">
                                    {companies.find((c) => c.id === attached.company_id)?.name ?? "شرکت ثبت‌شده"}
                                  </span>
                                  <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${ATTACHED_STATUS_STYLE[attached.status].cls}`}>
                                    {ATTACHED_STATUS_STYLE[attached.status].label}
                                  </span>
                                </div>
                              ) : on && (
                                <div className="flex shrink-0 items-center gap-2">
                                  <select
                                    aria-label={`شرکت ${d.filename}`}
                                    value={assignedCompany}
                                    onChange={(e) => setSelection((s) => ({ ...s, [d.id]: e.target.value }))}
                                    className={`${fieldClass} max-w-[14rem] py-1.5 text-xs ${
                                      isMissingCompany ? "border-amber-400 bg-amber-50/60 ring-1 ring-amber-300" : ""
                                    }`}
                                  >
                                    <option value="">شرکت را انتخاب کنید…</option>
                                    {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                                  </select>
                                  <select
                                    aria-label={`نوع فایل ${d.filename}`}
                                    value={monthly[d.id]?.kind ?? "period"}
                                    onChange={(e) => setMonthly((m) => {
                                      const rest = { ...m };
                                      if (e.target.value === "period") delete rest[d.id];
                                      else rest[d.id] = { kind: e.target.value as MonthlyChoice["kind"], month: 0 };
                                      return rest;
                                    })}
                                    className={`${fieldClass} py-1.5 text-xs`}
                                  >
                                    <option value="period">گزارش دوره</option>
                                    <option value="monthly_plan">برنامه‌ی ماهانه‌ی حجم‌ها</option>
                                    <option value="monthly_pv">برنامه‌ی PV ماهانه</option>
                                  </select>
                                  {d.id in monthly && (
                                    <select
                                      aria-label={`ماه برنامه ${d.filename}`}
                                      value={monthly[d.id]?.month ?? 0}
                                      onChange={(e) => setMonthly((m) => ({ ...m, [d.id]: { kind: m[d.id]?.kind ?? "monthly_plan", month: Number(e.target.value) } }))}
                                      className={`${fieldClass} py-1.5 text-xs`}
                                    >
                                      <option value={0}>ماه: از روی فایل</option>
                                      {JALALI_MONTHS.map((name, index) => <option key={name} value={index + 1}>{name}</option>)}
                                    </select>
                                  )}
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
        </>
      )}

      {selectedCount > 0 && missingCompanyCount > 0 && (
        <div className="flex items-center gap-2 rounded-xl border border-amber-200/80 bg-amber-50 px-4 py-2.5 text-xs text-amber-900">
          <span className="text-sm">⚠️</span>
          <span>
            برای {toFa(missingCompanyCount)} فایل انتخاب‌شده هنوز شرکتی تعیین نشده است. لطفاً شرکت هر فایل را مشخص کنید.
          </span>
        </div>
      )}

      {onAddCompany && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-200/70 bg-slate-50 p-3 text-xs">
          <span className="font-medium text-slate-600">شرکت در فهرست نیست؟</span>
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
            isLoading={addingCompany}
            disabled={!newCompany.trim() || !canEditSettings}
            onClick={() => void submitNewCompany()}
          >
            افزودن
          </Button>
          {!canEditSettings && (
            <span className="text-slate-400">افزودن شرکت فقط برای مدیر یا سرپرست تیم ممکن است.</span>
          )}
        </div>
      )}
    </div>
  );
}
