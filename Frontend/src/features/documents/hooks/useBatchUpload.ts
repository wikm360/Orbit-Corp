import { useEffect, useRef, useState } from "react";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { filterUploadFiles, summarizeBatch, uploadFilename, type FilterOptions } from "../lib/batchUpload";
import type { UploadProgress } from "../lib/batchUpload";
import type { BatchUploadItem, BatchUploadResponse } from "../types";

export type BatchUploadHandler = (files: File[], onBatch: (result: BatchUploadResponse) => void, onProgress?: (progress: UploadProgress) => void) => Promise<BatchUploadResponse>;
export interface UploadReport {
  total: number;
  skipped: BatchUploadItem[];
  items: BatchUploadItem[];
}

export function useBatchUpload(onUpload: BatchUploadHandler, filterOptions: FilterOptions = {}) {
  const [report, setReport] = useState<UploadReport | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const mounted = useRef(true);
  const busy = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  async function run(files: File[]) {
    if (busy.current || !files.length) return;
    const { eligible, skipped } = filterUploadFiles(files, filterOptions);
    const initial = { total: eligible.length, skipped, items: [] };
    setReport(initial);
    if (!eligible.length) return;
    busy.current = true;
    setIsUploading(true);
    setProgress({ loadedBytes: 0, totalBytes: eligible.reduce((sum, file) => sum + file.size, 0) });
    let items: BatchUploadItem[] = [];
    try {
      const result = await onUpload(eligible, (batch) => {
        items = [...items, ...batch.items];
        if (mounted.current) setReport({ ...initial, items });
      }, (next) => { if (mounted.current) setProgress(next); });
      if (mounted.current) setReport({ ...initial, items: result.items });
    } catch (error) {
      // Conversation creation can fail before the batch scheduler starts.
      const message = friendlyErrorMessage(error, "آپلود ناموفق بود.");
      const rejected = summarizeBatch(eligible.map((file) => ({ filename: uploadFilename(file), status: "rejected", document: null, error: message })));
      if (mounted.current) setReport({ ...initial, items: [...items, ...rejected.items.filter((item) => !items.some((known) => known.filename === item.filename))] });
    } finally {
      busy.current = false;
      if (mounted.current) { setIsUploading(false); setProgress(null); }
    }
  }
  return { report, isUploading, progress, run };
}
