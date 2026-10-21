import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import type { BatchUploadItem, BatchUploadResponse } from "../types";

/** Must match the backend `SUPPORTED_EXTENSIONS` (documents + images, which the backend reads with OCR). */
export const DOCUMENT_ACCEPT = ".pdf,.docx,.pptx,.xlsx,.txt,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff";
export const UNSUPPORTED_FORMAT_MESSAGE = "فرمت فایل مجاز نیست (PDF، DOCX، PPTX، XLSX، TXT یا تصویر PNG، JPG، WEBP، BMP، TIFF).";
export const BATCH_SIZE = 20;
export const UPLOAD_CONCURRENCY = 2;
export const MAX_FILE_BYTES = 50 * 1024 * 1024;

export function uploadFilename(file: File): string {
  return file.webkitRelativePath || file.name;
}

export function filterUploadFiles(files: File[]) {
  const eligible: File[] = [];
  const skipped: BatchUploadItem[] = [];
  for (const file of files) {
    const filename = uploadFilename(file);
    const extension = `.${file.name.split(".").pop()?.toLowerCase()}`;
    const error = file.name.startsWith("~$") ? "فایل موقت نادیده گرفته شد."
      : !DOCUMENT_ACCEPT.split(",").includes(extension) ? UNSUPPORTED_FORMAT_MESSAGE
      : file.size === 0 ? "فایل خالی است."
      : file.size > MAX_FILE_BYTES ? "حجم فایل بیشتر از ۵۰ مگابایت است."
      : filename.length > 500 ? "نام یا مسیر فایل بیشتر از ۵۰۰ کاراکتر است."
      : null;
    if (error) skipped.push({ filename, status: "rejected", document: null, error });
    else eligible.push(file);
  }
  return { eligible, skipped };
}

export function batchFormData(files: File[]): FormData {
  const form = new FormData();
  for (const file of files) form.append("files", file, uploadFilename(file));
  return form;
}

export function summarizeBatch(items: BatchUploadItem[]): BatchUploadResponse {
  const accepted = items.filter((item) => item.status === "accepted").length;
  return { items, accepted, rejected: items.length - accepted };
}

/** Keep at most two requests in flight; report partial successes even if another request fails. */
export async function uploadFileBatches(
  files: File[],
  send: (batch: File[]) => Promise<BatchUploadResponse>,
  onBatch?: (result: BatchUploadResponse) => void,
  active: () => boolean = () => true,
): Promise<BatchUploadResponse> {
  const batches: File[][] = [];
  for (let offset = 0; offset < files.length; offset += BATCH_SIZE) batches.push(files.slice(offset, offset + BATCH_SIZE));
  const results: BatchUploadItem[][] = [];
  let next = 0;
  await Promise.all(Array.from({ length: Math.min(UPLOAD_CONCURRENCY, batches.length) }, async () => {
    while (next < batches.length && active()) {
      const index = next++;
      const batch = batches[index];
      if (!batch) break;
      let result: BatchUploadResponse;
      try {
        result = await send(batch);
      } catch (error) {
        const message = friendlyErrorMessage(error, "ارسال این دسته ناموفق بود.");
        result = summarizeBatch(batch.map((file) => ({ filename: uploadFilename(file), status: "rejected", document: null, error: message })));
      }
      results[index] = result.items;
      if (active()) onBatch?.(result);
    }
  }));
  return summarizeBatch(results.flat());
}
