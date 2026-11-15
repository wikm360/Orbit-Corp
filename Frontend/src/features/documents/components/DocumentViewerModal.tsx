"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { OrbitIcon } from "@/shared/components/ui/OrbitIcon";
import { Spinner } from "@/shared/components/ui/Spinner";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { toFaDigits } from "@/shared/lib/utils";
import { documentsApi } from "../api/documentsApi";
import type { Document, DocumentPreviewResponse } from "../types";
import { StatusBadge } from "./StatusBadge";

interface DocumentViewerModalProps {
  projectId: string;
  document: Document | null;
  isOpen: boolean;
  onClose: () => void;
}

function getFileExtension(filename: string): string {
  const parts = filename.split(".");
  return parts.length > 1 ? parts.pop()!.toLowerCase() : "";
}

function isPdf(filename: string, contentType?: string | null): boolean {
  return filename.toLowerCase().endsWith(".pdf") || contentType?.includes("pdf") === true;
}

function isImage(filename: string, contentType?: string | null): boolean {
  const ext = getFileExtension(filename);
  return (
    ["png", "jpg", "jpeg", "webp", "bmp", "gif", "svg", "tif", "tiff"].includes(ext) ||
    contentType?.startsWith("image/") === true
  );
}

function isText(filename: string, contentType?: string | null): boolean {
  const ext = getFileExtension(filename);
  return (
    ["txt", "csv", "log", "md", "json", "xml", "html", "yaml", "yml"].includes(ext) ||
    contentType?.startsWith("text/") === true
  );
}

function DocumentViewerDialog({
  projectId,
  document,
  isOpen,
  onClose,
}: {
  projectId: string;
  document: Document;
  isOpen: boolean;
  onClose: () => void;
}) {
  const filename = document.filename;
  const initialDirectRender = isPdf(filename) || isImage(filename) || isText(filename);

  const [activeTab, setActiveTab] = useState<"file" | "ocr">(initialDirectRender ? "file" : "ocr");
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [contentType, setContentType] = useState<string | null>(null);
  const [fileText, setFileText] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(true);
  const [fileError, setFileError] = useState<string | null>(null);

  const [previewData, setPreviewData] = useState<DocumentPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(true);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const [isDownloading, setIsDownloading] = useState(false);
  const [activePage, setActivePage] = useState<number>(1);
  const [copied, setCopied] = useState(false);

  const ext = useMemo(() => getFileExtension(filename), [filename]);
  const canRenderInline = useMemo(
    () => isPdf(filename, contentType) || isImage(filename, contentType) || isText(filename, contentType),
    [filename, contentType]
  );

  useEffect(() => {
    let cancelled = false;
    let createdUrl: string | null = null;

    documentsApi
      .getFileBlob(projectId, document.id)
      .then(async ({ blob, contentType: type }) => {
        if (cancelled) return;
        setContentType(type);
        createdUrl = window.URL.createObjectURL(blob);
        setBlobUrl(createdUrl);
        if (isText(document.filename, type)) {
          const text = await blob.text();
          if (!cancelled) setFileText(text);
        }
      })
      .catch((err) => {
        if (!cancelled) setFileError(friendlyErrorMessage(err, "دریافت فایل از سرور ناموفق بود."));
      })
      .finally(() => {
        if (!cancelled) setFileLoading(false);
      });

    documentsApi
      .getPreview(projectId, document.id)
      .then((data) => {
        if (cancelled) return;
        setPreviewData(data);
        if (!initialDirectRender && data.pages.length === 0) {
          setActiveTab("file");
        }
      })
      .catch((err) => {
        if (!cancelled) setPreviewError(friendlyErrorMessage(err, "دریافت متن استخراج‌شده ناموفق بود."));
      })
      .finally(() => {
        if (!cancelled) setPreviewLoading(false);
      });

    return () => {
      cancelled = true;
      if (createdUrl) window.URL.revokeObjectURL(createdUrl);
    };
  }, [projectId, document.id, document.filename, initialDirectRender]);

  async function handleDownload() {
    setIsDownloading(true);
    try {
      await documentsApi.downloadFile(projectId, document.id, document.filename);
    } catch (err) {
      alert(friendlyErrorMessage(err, "دانلود فایل ناموفق بود."));
    } finally {
      setIsDownloading(false);
    }
  }

  function handleOpenInNewTab() {
    if (!blobUrl) return;
    window.open(blobUrl, "_blank");
  }

  const currentPage = previewData?.pages.find((p) => p.page === activePage) ?? previewData?.pages[0];
  const totalPages = previewData?.total_pages ?? (previewData?.pages.length || 0);

  async function handleCopyText() {
    const textToCopy = currentPage?.text || previewData?.raw_text || "";
    if (!textToCopy) return;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={document.filename}
      maxWidthClassName="max-w-4xl"
    >
      <div className="flex flex-col gap-4">
        {/* Top Action Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 pb-3">
          <div className="flex items-center gap-2">
            <StatusBadge status={document.status} />
            {totalPages > 0 && (
              <span className="text-xs text-gray-500">
                {toFaDigits(totalPages)} صفحه
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {canRenderInline && blobUrl && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleOpenInNewTab}
                title="باز کردن در پنجره جدید"
              >
                <OrbitIcon name="externalLink" className="h-4 w-4 text-gray-600" />
                <span>پنجره جدید</span>
              </Button>
            )}

            <Button
              type="button"
              variant="secondary"
              size="sm"
              isLoading={isDownloading}
              disabled={isDownloading}
              onClick={handleDownload}
              title="دانلود فایل اصلی"
            >
              <OrbitIcon name="download" className="h-4 w-4" />
              <span>دانلود فایل</span>
            </Button>
          </div>
        </div>

        {/* Tab Headers */}
        <div className="flex border-b border-gray-200 text-sm">
          <button
            type="button"
            onClick={() => setActiveTab("file")}
            className={`border-b-2 px-4 py-2 font-medium transition-colors ${
              activeTab === "file"
                ? "border-teal-600 text-teal-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            پیش‌نمایش فایل
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("ocr")}
            className={`border-b-2 px-4 py-2 font-medium transition-colors ${
              activeTab === "ocr"
                ? "border-teal-600 text-teal-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            متن پردازش‌شده / هوش مصنوعی
            {totalPages > 0 && ` (${toFaDigits(totalPages)})`}
          </button>
        </div>

        {/* Tab 1: File Preview */}
        {activeTab === "file" && (
          <div className="min-h-[50vh]">
            {fileLoading && (
              <div className="flex h-72 flex-col items-center justify-center gap-2 text-sm text-gray-400">
                <Spinner className="h-6 w-6 text-teal-600" />
                <span>در حال دریافت پیش‌نمایش فایل...</span>
              </div>
            )}

            {fileError && !fileLoading && (
              <div role="alert" className="rounded-xl bg-red-50 p-4 text-center text-sm text-red-700">
                <p>{fileError}</p>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="mt-3"
                  onClick={handleDownload}
                >
                  تلاش برای دانلود مستقیم
                </Button>
              </div>
            )}

            {!fileLoading && !fileError && blobUrl && (
              <>
                {isPdf(filename, contentType) && (
                  <iframe
                    src={blobUrl}
                    className="h-[65vh] w-full rounded-xl border border-gray-200"
                    title={document.filename}
                  />
                )}

                {isImage(filename, contentType) && (
                  <div className="flex h-[65vh] items-center justify-center overflow-auto rounded-xl bg-slate-100 p-4">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={blobUrl}
                      alt={document.filename}
                      className="max-h-full max-w-full rounded object-contain shadow-sm"
                    />
                  </div>
                )}

                {isText(filename, contentType) && (
                  <div className="h-[65vh] overflow-auto rounded-xl bg-slate-900 p-4 text-xs font-mono text-slate-100 text-left dir-ltr whitespace-pre-wrap">
                    {fileText ?? "در حال بارگذاری متن..."}
                  </div>
                )}

                {!canRenderInline && (
                  <div className="flex h-[55vh] flex-col items-center justify-center rounded-2xl border border-dashed border-gray-200 bg-gray-50 p-6 text-center">
                    <OrbitIcon name="document" className="mb-3 h-12 w-12 text-teal-600" />
                    <h3 className="text-base font-semibold text-gray-800">
                      فرمت <span className="uppercase text-teal-700">.{ext}</span> مستقیماً در مرورگر قابل رندر نیست
                    </h3>
                    <p className="mt-2 max-w-md text-sm text-gray-500">
                      می‌توانید فایل اصلی را دانلود کرده یا متن استخراج‌شده توسط هوش مصنوعی را در تب دوم مشاهده کنید.
                    </p>
                    <div className="mt-5 flex items-center gap-3">
                      <Button type="button" onClick={handleDownload}>
                        <OrbitIcon name="download" className="h-4 w-4" />
                        <span>دانلود فایل اصلی</span>
                      </Button>
                      <Button type="button" variant="secondary" onClick={() => setActiveTab("ocr")}>
                        مشاهده متن استخراج‌شده
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Tab 2: Extracted Text / OCR */}
        {activeTab === "ocr" && (
          <div className="min-h-[50vh]">
            {previewLoading && (
              <div className="flex h-72 flex-col items-center justify-center gap-2 text-sm text-gray-400">
                <Spinner className="h-6 w-6 text-teal-600" />
                <span>در حال دریافت متن پردازش‌شده...</span>
              </div>
            )}

            {previewError && !previewLoading && (
              <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
                {previewError}
              </p>
            )}

            {!previewLoading && !previewError && previewData && (
              <div className="flex flex-col gap-3">
                {/* Pagination Controls & Copy Button */}
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-700">
                  <div className="flex items-center gap-2">
                    {totalPages > 1 && (
                      <>
                        <button
                          type="button"
                          disabled={activePage <= 1}
                          onClick={() => setActivePage((prev) => Math.max(1, prev - 1))}
                          className="rounded-lg border border-gray-200 bg-white px-2.5 py-1 text-gray-700 hover:bg-gray-100 disabled:opacity-40"
                        >
                          صفحه قبلی
                        </button>
                        <span className="font-medium text-gray-800">
                          صفحه {toFaDigits(activePage)} از {toFaDigits(totalPages)}
                        </span>
                        <button
                          type="button"
                          disabled={activePage >= totalPages}
                          onClick={() => setActivePage((prev) => Math.min(totalPages, prev + 1))}
                          className="rounded-lg border border-gray-200 bg-white px-2.5 py-1 text-gray-700 hover:bg-gray-100 disabled:opacity-40"
                        >
                          صفحه بعدی
                        </button>
                      </>
                    )}
                    {totalPages <= 1 && totalPages > 0 && (
                      <span>تک‌صفحه ({toFaDigits(1)} از {toFaDigits(1)})</span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={handleCopyText}
                      title="کپی متن"
                    >
                      <OrbitIcon name={copied ? "check" : "copy"} className="h-4 w-4 text-gray-600" />
                      <span>{copied ? "کپی شد" : "کپی متن"}</span>
                    </Button>
                  </div>
                </div>

                {/* Text Reader */}
                {currentPage && currentPage.text ? (
                  <div
                    dir="auto"
                    className="h-[55vh] overflow-y-auto rounded-xl border border-gray-200 bg-white p-4 text-sm leading-relaxed text-gray-800 whitespace-pre-wrap select-text"
                  >
                    {currentPage.text}
                  </div>
                ) : previewData.pages.length === 0 ? (
                  <div className="flex h-56 flex-col items-center justify-center rounded-xl bg-gray-50 p-4 text-center text-sm text-gray-500">
                    <OrbitIcon name="document" className="mb-2 h-8 w-8 text-gray-400" />
                    <p>متن استخراج‌شده‌ای برای این سند ثبت نشده است.</p>
                    {document.status === "processing" && (
                      <p className="mt-1 text-xs text-amber-600">
                        سند هم‌اکنون در حال پردازش است؛ به محض اتمام پردازش، متن نمایش داده خواهد شد.
                      </p>
                    )}
                    {document.error_message && (
                      <p className="mt-1 text-xs text-red-600">{document.error_message}</p>
                    )}
                  </div>
                ) : (
                  <p className="py-6 text-center text-sm text-gray-400">این صفحه متنی ندارد.</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

export function DocumentViewerModal({ projectId, document, isOpen, onClose }: DocumentViewerModalProps) {
  if (!isOpen || !document) return null;
  return (
    <DocumentViewerDialog
      projectId={projectId}
      document={document}
      isOpen={isOpen}
      onClose={onClose}
    />
  );
}
