import { useRef, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { useBatchUpload, type BatchUploadHandler } from "../hooks/useBatchUpload";
import { DOCUMENT_ACCEPT, filterUploadFiles, uploadFilename } from "../lib/batchUpload";
import type { Document } from "../types";
import { BatchUploadSummary } from "./BatchUploadSummary";

export function BatchUploadForm({ onUpload, documents, onRetryFailed, retrying }: {
  onUpload: BatchUploadHandler;
  documents: Document[];
  onRetryFailed: (ids: string[]) => void;
  retrying: boolean;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const input = useRef<HTMLInputElement>(null);
  const folder = useRef<HTMLInputElement>(null);
  const { report, isUploading, run } = useBatchUpload(onUpload);
  const { eligible, skipped } = filterUploadFiles(files);
  const skippedReasons = new Map(skipped.map((item) => [item.filename, item.error]));
  const select = (selected: FileList | null) => setFiles(Array.from(selected ?? []));
  return <form className="space-y-3" onSubmit={async (event) => {
    event.preventDefault();
    await run(files);
    setFiles([]);
    if (input.current) input.current.value = "";
    if (folder.current) folder.current.value = "";
  }}>
    <div className="flex flex-wrap gap-2">
      <Button type="button" variant="secondary" disabled={isUploading} onClick={() => input.current?.click()}>انتخاب فایل‌ها</Button>
      <Button type="button" variant="secondary" disabled={isUploading} onClick={() => folder.current?.click()}>انتخاب پوشه</Button>
      <input ref={input} type="file" multiple accept={DOCUMENT_ACCEPT} aria-label="فایل‌های اسناد پروژه" className="hidden" disabled={isUploading} onChange={(event) => select(event.target.files)} />
      <input ref={folder} type="file" {...{ webkitdirectory: "" }} aria-label="پوشهٔ اسناد پروژه" className="hidden" disabled={isUploading} onChange={(event) => select(event.target.files)} />
      <Button type="submit" disabled={!eligible.length || isUploading} isLoading={isUploading}>آپلود فایل‌ها</Button>
    </div>
    {files.length > 0 && <div className="text-xs leading-6 text-slate-600">
      <p>{eligible.length} فایل آمادهٔ ارسال · {skipped.length} فایل فیلترشده</p>
      <ul className="max-h-32 overflow-y-auto">{files.map((file, index) => <li key={index} className="break-all"><bdi>{uploadFilename(file)}</bdi>{skippedReasons.has(uploadFilename(file)) && <span className="text-red-700">: {skippedReasons.get(uploadFilename(file))}</span>}</li>)}</ul>
    </div>}
    <BatchUploadSummary report={report} documents={documents} isUploading={isUploading} onRetryFailed={onRetryFailed} retrying={retrying} />
  </form>;
}
