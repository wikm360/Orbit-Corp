"use client";

import { useEffect, useState } from "react";

import { Button } from "@/shared/components/ui/Button";

import { runSoon } from "../lib/defer";
import { volumeReportApi } from "../api/volumeReportApi";
import { ReviewPanel } from "./ReviewPanel";
import { EmptyState, ErrorBox, LoadingBlock, ReportStatusBadge } from "./common";
import type { CatalogItem, ReportSummary } from "../types";

/** The review queue of a project: reports that wait for answers or confirmation, with the review UI inline. */
export function AttentionList({ projectId }: { projectId: string }) {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [active, setActive] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => runSoon(() => setActive(null)), [projectId]);

  useEffect(() => {
    let live = true;
    Promise.all([volumeReportApi.list(projectId), volumeReportApi.catalog()])
      .then(([list, items]) => { if (live) { setReports(list.filter((r) => r.status === "awaiting_user" || r.status === "needs_review")); setCatalog(items); } })
      .catch((e) => { if (live) setError(e); });
    return () => { live = false; };
  }, [projectId, version]);

  if (error) return <ErrorBox error={error} />;
  if (!reports) return <LoadingBlock />;
  if (reports.length === 0) return <EmptyState title="موردی برای بازبینی نیست" hint="گزارش‌هایی که منتظر پاسخ یا تأیید شما باشند اینجا می‌آیند." />;
  const current = reports.find((r) => r.id === active) ?? null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {reports.map((r) => (
          <Button key={r.id} size="sm" variant={r.id === active ? "primary" : "secondary"} onClick={() => setActive(r.id)}>
            {r.title} <ReportStatusBadge status={r.status} />
          </Button>
        ))}
      </div>
      {current ? (
        <ReviewPanel key={current.id} reportId={current.id} catalog={catalog} editable canContinue
          onChanged={() => setVersion((v) => v + 1)}
          onContinue={async () => { await volumeReportApi.continueRun(current.id); setVersion((v) => v + 1); }} />
      ) : <p className="text-sm text-slate-500">یک گزارش را برای بازبینی انتخاب کنید.</p>}
    </div>
  );
}
