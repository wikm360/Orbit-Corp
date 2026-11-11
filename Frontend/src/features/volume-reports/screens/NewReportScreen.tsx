"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { documentsApi } from "@/features/documents/api/documentsApi";
import type { Document, Folder } from "@/features/documents/types";
import { Button } from "@/shared/components/ui/Button";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { volumeReportApi } from "../api/volumeReportApi";
import { Card, ErrorBox, fieldClass, LoadingBlock } from "../components/common";
import { ProgressCard } from "../components/ProgressCard";
import { ProjectFileSelector } from "../components/ProjectFileSelector";
import { ProjectPicker } from "../components/ProjectPicker";
import { SourceDetails } from "../components/SourcesPanel";
import { useRunProgress } from "../hooks/useRunProgress";
import { useWorkspaceProjects } from "../hooks/useWorkspaceProjects";
import { runSoon } from "../lib/defer";
import { formatJalaliDate, suggestPeriodLabel, toFa } from "../lib/jalali";
import { STATUS_LABELS } from "../lib/status";
import {
  filesReady, isExcelName, matchSuggestedCompany, seedSelectionFromReportFiles, selectionToPayload,
  validateInfo, type InfoDraft, type MonthlyChoice,
} from "../lib/wizard";
import type { Company, Progress, ReportStatus, SelectedFile, SourceInfo } from "../types";

type Step = 1 | 2 | 3 | 4;
const STEP_TITLES: Record<Step, string> = { 1: "مشخصات", 2: "فایل‌ها", 3: "بازبینی و شروع", 4: "پیشرفت" };

function NewReportInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { projects, loading: projectsLoading, error: projectsError, canEditSettings, canManageDocumentsFor } = useWorkspaceProjects();
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
  const [monthly, setMonthly] = useState<Record<string, MonthlyChoice>>({}); // document_id -> kind + Jalali month of a monthly file (0 = read it from the file)
  const [selected, setSelected] = useState<SelectedFile[]>([]);
  const [hasPendingUploads, setHasPendingUploads] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [status, setStatus] = useState<ReportStatus>("draft");
  const [progress, setProgress] = useState<Progress | undefined>();
  const [sources, setSources] = useState<SourceInfo[] | null>(null);


  // Resume a draft created earlier (`?report=`): the project, period, and previously attached files are pre-populated.
  useEffect(() => {
    const existing = params.get("report");
    if (!existing) return;
    volumeReportApi.get(existing).then((r) => {
      setResumedProject(r.project_id);
      setInfo({ title: r.title, periodType: r.period_type, start: "", end: "", label: r.period_label });
      setReportId(r.id);
      if (r.files.length) {
        const seeded = seedSelectionFromReportFiles(r.files);
        setSelection((prev) => ({ ...seeded.selection, ...prev }));
        setMonthly((prev) => ({ ...seeded.monthly, ...prev }));
      }
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
    if (!reportId || !filesReady(selection) || hasPendingUploads) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await volumeReportApi.setFiles(reportId, selectionToPayload(selection, monthly));
      setSelected(result);
      setStep(3);
    } catch (e) { setMessage(friendlyErrorMessage(e, "ثبت فایل‌ها ناموفق بود.")); } finally { setBusy(false); }
  }

  async function addCompany(name: string) {
    try {
      const company = await volumeReportApi.settings.createCompany(name);
      setCompanies((c) => [...c, company]);
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
          ) : (
            <div className="space-y-4">
              <ProjectFileSelector
                projectId={projectId}
                docs={docs}
                folders={folders}
                companies={companies}
                selection={selection}
                setSelection={setSelection}
                monthly={monthly}
                setMonthly={setMonthly}
                canUpload={canManageDocumentsFor(projectId)}
                canEditSettings={canEditSettings}
                onAddCompany={addCompany}
                onDocsChange={setDocs}
                onPendingUploadsChange={setHasPendingUploads}
              />

              <div className="flex items-center justify-between gap-2 border-t border-slate-100 pt-2">
                <Button variant="ghost" onClick={() => setStep(1)}>
                  قبلی
                </Button>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">
                    {hasPendingUploads
                      ? "منتظر آماده‌سازی فایل‌های آپلودشده…"
                      : `${toFa(Object.keys(selection).length)} فایل انتخاب‌شده`}
                  </span>
                  <Button
                    onClick={() => void goReview()}
                    isLoading={busy}
                    disabled={!filesReady(selection) || hasPendingUploads}
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
                    {(f.kind === "monthly_plan" || f.kind === "monthly_pv") && f.plan && (
                      <span className="rounded bg-indigo-50 px-2 py-0.5 text-indigo-800">
                        {f.kind === "monthly_pv" ? "برنامه‌ی PV ماهانه" : "برنامه‌ی ماهانه‌ی حجم‌ها"} · {formatJalaliDate(f.plan.plan_start)} تا {formatJalaliDate(f.plan.plan_end)} · سهم این گزارش: {toFa(f.plan.overlap_days)} از {toFa(f.plan.plan_days)} روز
                        {f.plan.overlap_days === 0 && (f.kind === "monthly_pv" ? " (دوره‌ی این گزارش در این ماه نیست؛ استفاده نمی‌شود)" : " (دوره‌ی بعد در این ماه نیست؛ استفاده نمی‌شود)")}
                      </span>
                    )}
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

