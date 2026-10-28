import { Button } from "@/shared/components/ui/Button";
import { toFaDigits } from "@/shared/lib/utils";
import type { ArchiveImport } from "../types";

/** Progress of one uploaded archive being unpacked; the extracted files show up in the list below with their own status. */
export function ArchiveImportCard({ archive, onDismiss, canManage }: { archive: ArchiveImport; onDismiss: (id: string) => void; canManage: boolean }) {
  const running = archive.status === "extracting";
  const done = archive.imported_files + archive.failed_files.length + archive.skipped_files;
  const tone = archive.status === "failed" ? "border-red-200 bg-red-50 text-red-800" : running ? "border-amber-200 bg-amber-50 text-amber-900" : "border-slate-200 bg-slate-50 text-slate-700";
  return <div role="status" className={`rounded-xl border p-3 text-xs leading-6 ${tone}`}>
    <div className="flex flex-wrap items-center justify-between gap-2">
      <p className="font-medium"><bdi>{archive.filename}</bdi> — {running ? "در حال باز کردن آرشیو…" : archive.status === "failed" ? "باز کردن آرشیو ناموفق بود" : "آرشیو باز شد"}</p>
      {!running && canManage && <Button type="button" variant="ghost" size="sm" onClick={() => onDismiss(archive.id)} aria-label={`حذف اعلان ${archive.filename}`}>بستن</Button>}
    </div>
    {archive.status === "failed" && archive.error_message && <p>{archive.error_message}</p>}
    {archive.status !== "failed" && <p>
      {toFaDigits(archive.imported_files)} فایل وارد شد
      {archive.skipped_files > 0 && ` · ${toFaDigits(archive.skipped_files)} فایل بی‌مصرف نادیده گرفته شد`}
      {archive.failed_files.length > 0 && ` · ${toFaDigits(archive.failed_files.length)} فایل ناموفق`}
      {running && archive.total_files > 0 && ` · ${toFaDigits(done)} از ${toFaDigits(archive.total_files)}`}
    </p>}
    {archive.failed_files.length > 0 && <details>
      <summary className="cursor-pointer">فایل‌های واردنشده</summary>
      <ul className="max-h-32 space-y-1 overflow-y-auto pt-1">
        {archive.failed_files.map((file, index) => <li key={index} className="break-all"><bdi>{file.path}</bdi>: {file.error}</li>)}
      </ul>
    </details>}
  </div>;
}
