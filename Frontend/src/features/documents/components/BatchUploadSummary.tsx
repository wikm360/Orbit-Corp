import type { Document } from "../types";
import type { UploadReport } from "../hooks/useBatchUpload";

export function BatchUploadSummary({ report, documents, isUploading, onRetryFailed, retrying = false }: {
  report: UploadReport | null;
  documents: Document[];
  isUploading: boolean;
  onRetryFailed?: (ids: string[]) => void;
  retrying?: boolean;
}) {
  if (!report) return null;
  const accepted = report.items.flatMap((item) => item.status === "accepted" && item.document ? [item.document] : []);
  const current = [...new Map(accepted.map((document) => [document.id, documents.find((item) => item.id === document.id) ?? document])).values()];
  const ready = current.filter((document) => document.status === "ready").length;
  const failed = current.filter((document) => document.status === "failed");
  const processing = current.filter((document) => document.status === "processing").length;
  const rejected = report.items.filter((item) => item.status === "rejected");
  return <div role="status" className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-6 text-slate-700">
    <p>{isUploading ? `در حال ارسال: ${report.items.length} از ${report.total} فایل` : `پایان ارسال: ${accepted.length} پذیرفته، ${rejected.length} ردشده`}</p>
    {report.skipped.length > 0 && <p>{report.skipped.length} فایل نامعتبر یا موقت پیش از ارسال فیلتر شد.</p>}
    {current.length > 0 && <>
      <p>{ready} از {current.length} سند آماده · {processing} در حال پردازش · {failed.length} ناموفق</p>
      <progress aria-label="پیشرفت پردازش فایل‌ها" max={current.length} value={ready} className="h-2 w-full accent-teal-600" />
    </>}
    {(report.skipped.length > 0 || rejected.length > 0) && <details>
      <summary className="cursor-pointer">جزئیات فایل‌های ارسال‌نشده</summary>
      <ul className="max-h-40 space-y-1 overflow-y-auto pt-2">
        {[...report.skipped, ...rejected].map((item, index) => <li key={index} className="break-all text-red-700"><bdi>{item.filename}</bdi>: {item.error}</li>)}
      </ul>
    </details>}
    {failed.length > 0 && onRetryFailed && !isUploading && <button type="button" disabled={retrying} onClick={() => onRetryFailed(failed.map((document) => document.id))} className="rounded-lg border border-red-200 px-3 py-1 text-red-700 disabled:opacity-50">{retrying ? "در حال تلاش مجدد…" : "تلاش مجدد برای همه‌ی ناموفق‌ها"}</button>}
  </div>;
}
