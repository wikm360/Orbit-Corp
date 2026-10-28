import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import type { BatchUploadItem, BatchUploadResponse } from "../types";

/** Must match the backend `SUPPORTED_EXTENSIONS` (documents + images, which the backend reads with OCR). */
export const DOCUMENT_ACCEPT = ".pdf,.docx,.pptx,.xlsx,.txt,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff";
export const UNSUPPORTED_FORMAT_MESSAGE = "فرمت فایل مجاز نیست (PDF، DOCX، PPTX، XLSX، TXT یا تصویر PNG، JPG، WEBP، BMP، TIFF).";
export const BATCH_SIZE = 20;
export const UPLOAD_CONCURRENCY = 2;
/** Matches the backend `MAX_UPLOAD_SIZE_MB` (per file). */
export const MAX_FILE_BYTES = 200 * 1024 * 1024;
/** A request carries at most this many bytes of files (a bigger single file goes alone): keeps each request well under
 *  the proxy body limit and makes progress/failure granular. */
export const BATCH_MAX_BYTES = 80 * 1024 * 1024;
/** Matches the backend `MAX_ARCHIVE_SIZE_MB`; the proxy in front of the API may impose a lower limit. */
export const MAX_ARCHIVE_BYTES = 500 * 1024 * 1024;
export const ARCHIVE_EXTENSIONS = [".zip", ".rar", ".7z"];
/** Never worth uploading (CAD fonts/backups/logs, OS metadata): the backend skips the same names inside archives. */
const JUNK_EXTENSIONS = [".shx", ".lsp", ".bak", ".log", ".tmp", ".dwl", ".dwl2"];
const JUNK_NAMES = ["thumbs.db", "desktop.ini", ".ds_store"];

export function uploadFilename(file: File): string {
  return file.webkitRelativePath || file.name;
}

export interface FilterOptions {
  /** Project file manager: any type is stored (unsupported ones are kept as such), archives are unpacked. */
  projectFiles?: boolean;
}

function projectFileError(file: File, filename: string): string | null {
  const name = file.name.toLowerCase();
  const extension = `.${name.split(".").pop()}`;
  const limit = ARCHIVE_EXTENSIONS.includes(extension) ? MAX_ARCHIVE_BYTES : MAX_FILE_BYTES;
  return name.startsWith("~$") || name.startsWith("._") || JUNK_NAMES.includes(name) || JUNK_EXTENSIONS.includes(extension) ? "فایل موقت یا بی‌مصرف نادیده گرفته شد."
    : file.size === 0 ? "فایل خالی است."
    : file.size > limit ? `حجم فایل بیشتر از ${limit / 1024 / 1024} مگابایت است.`
    : filename.length > 500 ? "نام یا مسیر فایل بیشتر از ۵۰۰ کاراکتر است."
    : null;
}

export function filterUploadFiles(files: File[], options: FilterOptions = {}) {
  const eligible: File[] = [];
  const skipped: BatchUploadItem[] = [];
  for (const file of files) {
    const filename = uploadFilename(file);
    const extension = `.${file.name.split(".").pop()?.toLowerCase()}`;
    if (options.projectFiles) {
      const projectError = projectFileError(file, filename);
      if (projectError) skipped.push({ filename, status: "rejected", document: null, error: projectError });
      else eligible.push(file);
      continue;
    }
    const error = file.name.startsWith("~$") ? "فایل موقت نادیده گرفته شد."
      : !DOCUMENT_ACCEPT.split(",").includes(extension) ? UNSUPPORTED_FORMAT_MESSAGE
      : file.size === 0 ? "فایل خالی است."
      : file.size > MAX_FILE_BYTES ? `حجم فایل بیشتر از ${MAX_FILE_BYTES / 1024 / 1024} مگابایت است.`
      : filename.length > 500 ? "نام یا مسیر فایل بیشتر از ۵۰۰ کاراکتر است."
      : null;
    if (error) skipped.push({ filename, status: "rejected", document: null, error });
    else eligible.push(file);
  }
  return { eligible, skipped };
}

export function batchFormData(files: File[], folderId?: string | null): FormData {
  const form = new FormData();
  if (folderId) form.append("folder_id", folderId);
  for (const file of files) form.append("files", file, uploadFilename(file));
  return form;
}

export function summarizeBatch(items: BatchUploadItem[]): BatchUploadResponse {
  const accepted = items.filter((item) => item.status === "accepted").length;
  return { items, accepted, rejected: items.length - accepted };
}

/** Splits files into requests of at most `BATCH_SIZE` files and `BATCH_MAX_BYTES` bytes (a larger file travels alone). */
export function planBatches(files: File[]): File[][] {
  const batches: File[][] = [];
  let current: File[] = [];
  let bytes = 0;
  for (const file of files) {
    if (current.length && (current.length >= BATCH_SIZE || bytes + file.size > BATCH_MAX_BYTES)) {
      batches.push(current);
      current = [];
      bytes = 0;
    }
    current.push(file);
    bytes += file.size;
  }
  if (current.length) batches.push(current);
  return batches;
}

export interface UploadProgress {
  loadedBytes: number;
  totalBytes: number;
}

/** Keep at most two requests in flight; report partial successes even if another request fails. `onProgress` gets the
 *  overall bytes sent (completed requests count in full, in-flight ones by their reported fraction). */
export async function uploadFileBatches(
  files: File[],
  send: (batch: File[], onFraction: (fraction: number) => void) => Promise<BatchUploadResponse>,
  onBatch?: (result: BatchUploadResponse) => void,
  active: () => boolean = () => true,
  onProgress?: (progress: UploadProgress) => void,
): Promise<BatchUploadResponse> {
  const batches = planBatches(files);
  const sizes = batches.map((batch) => batch.reduce((sum, file) => sum + file.size, 0));
  const totalBytes = sizes.reduce((sum, size) => sum + size, 0);
  const sent = batches.map(() => 0);
  const report = () => {
    if (active()) onProgress?.({ loadedBytes: sent.reduce((sum, value) => sum + value, 0), totalBytes });
  };
  report();
  const results: BatchUploadItem[][] = [];
  let next = 0;
  await Promise.all(Array.from({ length: Math.min(UPLOAD_CONCURRENCY, batches.length) }, async () => {
    while (next < batches.length && active()) {
      const index = next++;
      const batch = batches[index];
      if (!batch) break;
      let result: BatchUploadResponse;
      try {
        // The last bytes are only "sent" once the server answered, so cap an in-flight request just below its size.
        result = await send(batch, (fraction) => { sent[index] = Math.min(sizes[index] ?? 0, (sizes[index] ?? 0) * Math.min(fraction, 0.99)); report(); });
      } catch (error) {
        const message = friendlyErrorMessage(error, "ارسال این دسته ناموفق بود.");
        result = summarizeBatch(batch.map((file) => ({ filename: uploadFilename(file), status: "rejected", document: null, error: message })));
      }
      sent[index] = sizes[index] ?? 0;
      report();
      results[index] = result.items;
      if (active()) onBatch?.(result);
    }
  }));
  return summarizeBatch(results.flat());
}
