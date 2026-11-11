"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { ApiError } from "@/shared/lib/apiClient";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { volumeReportApi, type ExportFormat } from "../api/volumeReportApi";
import { Card, ErrorBox, LoadingBlock, ReportStatusBadge, Tabs } from "../components/common";
import { ActivityPanel } from "../components/ActivityPanel";
import { AddReportFilesModal } from "../components/AddReportFilesModal";
import { EvmPanel } from "../components/EvmPanel";
import { NarrativesPanel } from "../components/NarrativesPanel";
import { PlanPanel } from "../components/PlanPanel";
import { ProgressCard } from "../components/ProgressCard";
import { ResultsView } from "../components/ResultsView";
import { ReviewPanel } from "../components/ReviewPanel";
import { SourcesPanel } from "../components/SourcesPanel";
import { useReportActivity } from "../hooks/useReportActivity";
import { useRunProgress } from "../hooks/useRunProgress";
import { runSoon } from "../lib/defer";
import { formatJalaliDate, formatJalaliDateTime, toFa } from "../lib/jalali";
import { GATE_HINTS, PERIOD_LABELS, gateLabel, parseGateError } from "../lib/status";
import type { CatalogItem, GateCause, Progress, ReportDetail, SourceInfo } from "../types";

type TabId = "results" | "evm" | "plan" | "narratives" | "review" | "sources" | "activity";

export function ReportDetailScreen({ reportId }: { reportId: string }) {
  const router = useRouter();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [tab, setTab] = useState<TabId>("results");
  const [progress, setProgress] = useState<Progress | undefined>();
  const [refreshKey, setRefreshKey] = useState(0);
  const [openQuestions, setOpenQuestions] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [gate, setGate] = useState<GateCause[] | null>(null);
  const [filesModalOpen, setFilesModalOpen] = useState(false);
  const [removingFileId, setRemovingFileId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [detail, items] = await Promise.all([volumeReportApi.get(reportId), volumeReportApi.catalog()]);
      setReport(detail);
      setCatalog(items);
      setProgress(detail.progress);
      setOpenQuestions((await volumeReportApi.questions(reportId, "open").catch(() => [])).length);
      setError(null);
    } catch (e) {
      setError(e);
    }
  }, [reportId]);
  useEffect(() => runSoon(() => void load()), [load]);

  const refresh = useCallback(async () => { await load(); setRefreshKey((k) => k + 1); }, [load]);

  const activity = useReportActivity(reportId, report?.status === "processing");
  useRunProgress(reportId, report?.status === "processing", (p) => setProgress(p.progress), () => { void refresh(); });

  async function act<T>(name: string, fn: () => Promise<T>, done?: string): Promise<T | undefined> {
    setBusy(name);
    setNotice(null);
    try {
      const result = await fn();
      if (done) setNotice(done);
      return result;
    } catch (e) {
      const causes = e instanceof ApiError && e.status === 409 ? parseGateError(e.message) : null;
      if (causes) setGate(causes);
      else setNotice(friendlyErrorMessage(e, "عملیات ناموفق بود."));
      return undefined;
    } finally {
      setBusy(null);
    }
  }

  async function start(kind: "run" | "continue") {
    const result = await act(kind, () => (kind === "run" ? volumeReportApi.run(reportId) : volumeReportApi.continueRun(reportId)));
    if (result) await load();
  }
  async function publish() {
    const result = await act("publish", () => volumeReportApi.publish(reportId), "گزارش منتشر شد.");
    if (result) await refresh();
  }
  async function reopen() {
    const fresh = await act("reopen", () => volumeReportApi.reopen(reportId));
    if (fresh) router.push(`/volume-reports/${fresh.id}`);
  }
  async function remove() {
    const warning = report?.status === "published" ? "این گزارش منتشرشده است. با حذف، گزارش و همه‌ی نتایج و تاریخچه‌ی آن برای همیشه پاک می‌شود و قابل بازگشت نیست. ادامه می‌دهید؟" : "این گزارش برای همیشه حذف شود؟";
    if (!window.confirm(warning)) return;
    const ok = await act("delete", () => volumeReportApi.remove(reportId).then(() => true));
    if (ok) router.push("/volume-reports");
  }
  async function download(format: ExportFormat) {
    await act(`export-${format}`, () => volumeReportApi.downloadExport(reportId, format));
  }
  async function handleRemoveSource(source: SourceInfo) {
    if (source.status === "parsed" && !window.confirm(`فایل «${source.filename}» قبلاً خوانده شده است. از گزارش حذف شود؟ (پس از حذف باید یک دور جدید اجرا کنید.)`)) {
      return;
    }
    setRemovingFileId(source.id);
    setNotice(null);
    try {
      await volumeReportApi.removeFile(reportId, source.id);
      setNotice(`فایل «${source.filename}» از گزارش حذف شد.`);
      await refresh();
    } catch (e) {
      setNotice(friendlyErrorMessage(e, "حذف فایل از گزارش ناموفق بود."));
    } finally {
      setRemovingFileId(null);
    }
  }

  if (error) return <div className="p-6"><ErrorBox error={error} onRetry={() => void load()} /></div>;
  if (!report) return <LoadingBlock />;

  const processing = report.status === "processing";
  const published = report.status === "published";
  const editable = !processing && !published;
  const canContinue = ["awaiting_user", "needs_review", "ready"].includes(report.status);
  const pendingFilesCount = report.files.filter((f) => f.status === "pending").length;

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 md:p-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/volume-reports" className="text-xs text-teal-700 hover:underline">← همه‌ی گزارش‌ها</Link>
          <h1 className="mt-1 text-lg font-semibold text-slate-900">{report.title}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <ReportStatusBadge status={report.status} />
            <span>{PERIOD_LABELS[report.period_type]} · {report.period_label}</span>
            <span>{formatJalaliDate(report.period_start)} تا {formatJalaliDate(report.period_end)}</span>
            <span>نسخه‌ی {toFa(report.version)}</span>
            {published && <span>منتشر در {formatJalaliDateTime(report.published_at)}</span>}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {report.status === "draft" && report.files.length === 0 && <Link href={`/volume-reports/new?report=${report.id}`} className="inline-flex items-center rounded-xl bg-gray-100 px-4 py-2 text-sm hover:bg-gray-200">انتخاب فایل‌ها</Link>}
          {editable && (
            <Button size="sm" variant="secondary" onClick={() => setFilesModalOpen(true)}>
              + افزودن فایل جدید
            </Button>
          )}
          {editable && report.files.length > 0 && (
            <Button
              size="sm"
              variant={pendingFilesCount > 0 && report.status !== "draft" ? "primary" : "secondary"}
              isLoading={busy === "run"}
              onClick={() => void start("run")}
            >
              {report.status === "draft"
                ? "اجرا"
                : pendingFilesCount > 0
                  ? `اجرای دور جدید (${toFa(pendingFilesCount)} فایل جدید)`
                  : "اجرای مجدد"}
            </Button>
          )}
          {!processing && report.status !== "draft" && report.status !== "failed" && <>
            <Link href={`/volume-reports/${report.id}/presentation`} className="inline-flex items-center rounded-xl bg-[#252850] px-4 py-2 text-sm font-medium text-white hover:bg-[#1e2246]">
              پرزنتیشن مدیریتی
            </Link>
            <Button size="sm" variant="ghost" isLoading={busy === "export-xlsx"} onClick={() => void download("xlsx")}>Excel</Button>
            <Button size="sm" variant="ghost" isLoading={busy === "export-csv"} onClick={() => void download("csv")}>CSV</Button>
          </>}
          {editable && ["ready", "needs_review", "awaiting_user"].includes(report.status) && <Button size="sm" isLoading={busy === "publish"} onClick={() => void publish()}>انتشار</Button>}
          {published && <Button size="sm" variant="secondary" isLoading={busy === "reopen"} onClick={() => void reopen()}>بازکردن نسخه‌ی جدید</Button>}
          {!processing && <Button size="sm" variant="danger" isLoading={busy === "delete"} onClick={() => void remove()}>حذف</Button>}
        </div>
      </header>

      {notice && <p role="status" className="rounded-xl bg-slate-100 px-4 py-2 text-sm text-slate-700">{notice}</p>}
      {report.status === "failed" && <ErrorBox error={new Error(report.error_message ?? "")} fallback={`اجرا ناموفق بود${report.error_message ? `: ${report.error_message}` : "."}`} />}
      {editable && pendingFilesCount > 0 && report.status !== "draft" && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-200 bg-teal-50/80 px-4 py-2.5 text-xs text-teal-900">
          <span>
            {toFa(pendingFilesCount)} فایل جدید به گزارش اضافه شده و هنوز پردازش نشده است. برای پارس شدن فایل‌ها و به‌روزرسانی ارقام و تحلیل هوشمند، دور جدید را اجرا کنید.
          </span>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="secondary" onClick={() => setFilesModalOpen(true)}>افزودن فایل بیشتر</Button>
            <Button size="sm" isLoading={busy === "run"} onClick={() => void start("run")}>اجرای دور جدید</Button>
          </div>
        </div>
      )}
      {report.issues.length > 0 && !published && !processing && (
        <p className="rounded-xl bg-amber-50 px-4 py-2 text-xs text-amber-900">
          موارد مانع انتشار: {report.issues.map((i) => `${gateLabel(i.code)} (${toFa(i.count)})`).join("، ")}
        </p>
      )}
      {processing && <ProgressCard progress={progress} />}
      {(processing || report.status === "failed") && <ActivityPanel items={activity.items} loaded={activity.loaded} processing={processing} progress={progress} />}

      {!processing && report.status !== "draft" && report.status !== "failed" && (
        <>
          <Tabs<TabId> value={tab} onChange={setTab} tabs={[{ id: "results", label: "نتایج" }, { id: "evm", label: "شاخص‌های EVM" }, { id: "plan", label: "برنامه و پیش‌بینی" }, { id: "narratives", label: "عملکرد پروژه‌ها" }, { id: "review", label: "بازبینی", badge: openQuestions }, { id: "sources", label: "منابع و هشدارها", badge: pendingFilesCount }, { id: "activity", label: "گزارش فعالیت" }]} />
          {tab === "results" && <ResultsView reportId={reportId} catalog={catalog} refreshKey={refreshKey} />}
          {tab === "evm" && <EvmPanel reportId={reportId} refreshKey={refreshKey} editable={editable} />}
          {tab === "plan" && <PlanPanel reportId={reportId} periodEnd={report.period_end} refreshKey={refreshKey} />}
          {tab === "narratives" && <NarrativesPanel reportId={reportId} refreshKey={refreshKey} />}
          {tab === "review" && (
            <ReviewPanel reportId={reportId} catalog={catalog} editable={editable} canContinue={canContinue} refreshKey={refreshKey}
              onChanged={() => void refresh()} onContinue={async () => { await volumeReportApi.continueRun(reportId); await load(); }} />
          )}
          {tab === "sources" && (
            <SourcesPanel
              reportId={reportId}
              refreshKey={refreshKey}
              editable={editable}
              removingId={removingFileId}
              onOpenAddFiles={() => setFilesModalOpen(true)}
              onRunPending={() => void start("run")}
              onRemoveFile={(s) => void handleRemoveSource(s)}
            />
          )}
          {tab === "activity" && <ActivityPanel items={activity.items} loaded={activity.loaded} processing={false} />}
        </>
      )}
      {report.status === "draft" && report.files.length > 0 && (
        <Card title="فایل‌های انتخاب‌شده"><ul className="space-y-1 text-sm text-slate-700">{report.files.map((f) => <li key={f.id}>{f.filename}</li>)}</ul></Card>
      )}

      <AddReportFilesModal
        isOpen={filesModalOpen}
        onClose={() => setFilesModalOpen(false)}
        report={report}
        onChanged={refresh}
        onRunStarted={load}
      />

      <Modal isOpen={gate !== null} onClose={() => setGate(null)} title="انتشار انجام نشد">
        <p className="text-sm text-slate-700">قفل انتشار (حالت سخت‌گیرانه) تا برطرف‌شدن این موارد فعال است:</p>
        <ul className="mt-3 space-y-2">
          {(gate ?? []).map((c) => (
            <li key={c.code} className="rounded-xl bg-amber-50 px-3 py-2 text-sm">
              <span className="font-medium text-amber-900">{gateLabel(c.code)} — {toFa(c.count)}</span>
              {GATE_HINTS[c.code] && <p className="mt-0.5 text-xs text-amber-800">{GATE_HINTS[c.code]}</p>}
            </li>
          ))}
        </ul>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={() => setGate(null)}>بستن</Button>
          <Button size="sm" onClick={() => { setGate(null); setTab("review"); void refresh(); }}>رفتن به بازبینی</Button>
        </div>
      </Modal>
    </div>
  );
}
