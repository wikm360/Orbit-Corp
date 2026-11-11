"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { documentsApi } from "@/features/documents/api/documentsApi";
import type { Document, Folder } from "@/features/documents/types";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { volumeReportApi } from "../api/volumeReportApi";
import { useWorkspaceProjects } from "../hooks/useWorkspaceProjects";
import { runSoon } from "../lib/defer";
import { toFa } from "../lib/jalali";
import { filesReady, isExcelName, selectionToPayload, type MonthlyChoice } from "../lib/wizard";
import type { Company, ReportDetail, ReportFileInfo } from "../types";
import { ErrorBox, LoadingBlock } from "./common";
import { ProjectFileSelector } from "./ProjectFileSelector";

const FILE_STATUS_BADGE: Record<ReportFileInfo["status"], { label: string; cls: string }> = {
  parsed: { label: "خوانده‌شده", cls: "bg-emerald-50 text-emerald-700" },
  pending: { label: "در انتظار پردازش", cls: "bg-amber-50 text-amber-800" },
  failed: { label: "ناموفق", cls: "bg-rose-50 text-rose-700" },
};

function AddReportFilesBody({
  onClose,
  report,
  onChanged,
  onRunStarted,
}: {
  onClose: () => void;
  report: ReportDetail;
  onChanged: () => Promise<void> | void;
  onRunStarted: () => Promise<void> | void;
}) {
  const { canEditSettings, canManageDocumentsFor } = useWorkspaceProjects();
  const canUpload = canManageDocumentsFor(report.project_id);

  const [docs, setDocs] = useState<Document[] | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Record<string, string>>({});
  const [monthly, setMonthly] = useState<Record<string, MonthlyChoice>>({});
  const [hasPendingUploads, setHasPendingUploads] = useState(false);
  const [busyMode, setBusyMode] = useState<"save" | "run" | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoadError(null);
    setDocs(null);
    try {
      const [list, comps, folderList] = await Promise.all([
        documentsApi.list(report.project_id),
        volumeReportApi.settings.companies(),
        documentsApi.listFolders(report.project_id).catch(() => []),
      ]);
      setDocs(list.filter((d) => d.status === "ready" && isExcelName(d.filename)));
      setCompanies(comps.filter((c) => c.is_active));
      setFolders(folderList ?? []);
    } catch (e) {
      setLoadError(e);
    }
  }, [report.project_id]);

  useEffect(() => runSoon(() => void loadData()), [loadData]);

  const attachedByDocId = useMemo(() => {
    const map = new Map<string, ReportFileInfo>();
    for (const f of report.files) {
      if (f.document_id) map.set(f.document_id, f);
    }
    return map;
  }, [report.files]);

  const companyNames = useMemo(() => new Map(companies.map((c) => [c.id, c.name])), [companies]);

  async function handleAddCompany(name: string) {
    try {
      const created = await volumeReportApi.settings.createCompany(name);
      setCompanies((c) => [...c, created]);
    } catch (e) {
      setSubmitError(friendlyErrorMessage(e, "افزودن شرکت ناموفق بود (فقط مدیر یا سرپرست تیم)."));
    }
  }

  async function handleRemoveAttached(file: ReportFileInfo) {
    if (file.status === "parsed" && !window.confirm(`فایل «${file.filename}» قبلاً خوانده شده است. از گزارش حذف شود؟ (پس از حذف باید یک دور جدید اجرا کنید.)`)) {
      return;
    }
    setRemovingId(file.id);
    setSubmitError(null);
    try {
      await volumeReportApi.removeFile(report.id, file.id);
      await onChanged();
    } catch (e) {
      setSubmitError(friendlyErrorMessage(e, "حذف فایل از گزارش ناموفق بود."));
    } finally {
      setRemovingId(null);
    }
  }

  async function submit(andRun: boolean) {
    if (!filesReady(selection)) return;
    setBusyMode(andRun ? "run" : "save");
    setSubmitError(null);
    try {
      const payload = selectionToPayload(selection, monthly);
      await volumeReportApi.addFiles(report.id, payload);
      if (andRun) {
        await volumeReportApi.run(report.id);
        await onRunStarted();
      } else {
        await onChanged();
      }
      onClose();
    } catch (e) {
      setSubmitError(friendlyErrorMessage(e, "افزودن فایل‌ها به گزارش ناموفق بود."));
    } finally {
      setBusyMode(null);
    }
  }

  const newCount = Object.keys(selection).length;
  const readyToSubmit = filesReady(selection) && !hasPendingUploads;

  return (
    <div className="max-h-[78vh] space-y-4 overflow-y-auto pe-1">
      {report.files.length > 0 && (
        <details className="rounded-xl border border-slate-200 bg-slate-50/70 px-3.5 py-2.5 text-xs">
          <summary className="cursor-pointer font-semibold text-slate-700">
            فایل‌های فعلی این گزارش ({toFa(report.files.length)} فایل — {toFa(report.files.filter((f) => f.status === "pending").length)} در انتظار پردازش)
          </summary>
          <ul className="mt-2.5 max-h-40 space-y-1.5 overflow-y-auto border-t border-slate-200/80 pt-2">
            {report.files.map((f) => {
              const st = FILE_STATUS_BADGE[f.status];
              return (
                <li key={f.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 bg-white px-2.5 py-1.5">
                  <div className="flex min-w-0 flex-1 items-center gap-2">
                    <span className="truncate font-medium text-slate-800" dir="auto">{f.filename}</span>
                    <span className="shrink-0 text-[11px] text-slate-500">· {companyNames.get(f.company_id) ?? "—"}</span>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${st.cls}`}>{st.label}</span>
                  </div>
                  <button
                    type="button"
                    disabled={removingId === f.id || busyMode !== null}
                    onClick={() => void handleRemoveAttached(f)}
                    className="shrink-0 text-[11px] text-rose-600 hover:underline disabled:opacity-50"
                  >
                    {removingId === f.id ? "در حال حذف..." : "حذف"}
                  </button>
                </li>
              );
            })}
          </ul>
        </details>
      )}

      {submitError && <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700">{submitError}</p>}

      {loadError ? (
        <ErrorBox error={loadError} onRetry={() => void loadData()} />
      ) : !docs ? (
        <LoadingBlock />
      ) : (
        <ProjectFileSelector
          projectId={report.project_id}
          docs={docs}
          folders={folders}
          companies={companies}
          selection={selection}
          setSelection={setSelection}
          monthly={monthly}
          setMonthly={setMonthly}
          canUpload={canUpload}
          canEditSettings={canEditSettings}
          onAddCompany={handleAddCompany}
          onDocsChange={setDocs}
          onPendingUploadsChange={setHasPendingUploads}
          attachedFilesByDocId={attachedByDocId}
          listMaxHeightClass="max-h-[340px]"
        />
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
        <div className="text-xs text-slate-500">
          {hasPendingUploads
            ? "منتظر آماده‌سازی فایل آپلودشده…"
            : newCount > 0
              ? `${toFa(newCount)} فایل جدید آماده افزودن است (داده‌ها و تصمیم‌های تأییدشده‌ی قبلی حفظ می‌شوند).`
              : "فایل جدیدی را آپلود یا از فهرست پروژه انتخاب کنید."}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" variant="ghost" disabled={busyMode !== null} onClick={onClose}>
            بستن
          </Button>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={!readyToSubmit || busyMode !== null}
            isLoading={busyMode === "save"}
            onClick={() => void submit(false)}
          >
            افزودن بدون اجرا
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={!readyToSubmit || busyMode !== null}
            isLoading={busyMode === "run"}
            onClick={() => void submit(true)}
          >
            افزودن و اجرای دور جدید ({toFa(newCount)} فایل)
          </Button>
        </div>
      </div>
    </div>
  );
}

export function AddReportFilesModal({
  isOpen,
  onClose,
  report,
  onChanged,
  onRunStarted,
}: {
  isOpen: boolean;
  onClose: () => void;
  report: ReportDetail;
  onChanged: () => Promise<void> | void;
  onRunStarted: () => Promise<void> | void;
}) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="افزودن فایل جدید به گزارش" maxWidthClassName="max-w-4xl">
      {isOpen && (
        <AddReportFilesBody
          onClose={onClose}
          report={report}
          onChanged={onChanged}
          onRunStarted={onRunStarted}
        />
      )}
    </Modal>
  );
}
