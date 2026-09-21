"use client";

import { FormEvent, useRef, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

export function UploadForm({ onUpload }: { onUpload: (file: File) => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setError(null);
    setIsUploading(true);
    try {
      await onUpload(file);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setError(friendlyErrorMessage(err, "آپلود سند ناموفق بود."));
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-4">
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <label htmlFor="document-file" className="text-sm font-medium text-gray-700">فایل سند</label>
        <input ref={fileInputRef} id="document-file" type="file" accept=".pdf,.docx,.pptx,.xlsx,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="h-11 min-w-0 rounded-xl border border-gray-200 bg-white text-sm text-gray-500 file:me-3 file:h-full file:border-0 file:border-l file:border-gray-200 file:bg-gray-50 file:px-4 file:text-sm file:font-medium file:text-brand-700" />
      </div>
      <Button type="submit" isLoading={isUploading} disabled={!file} className="h-11">آپلود</Button>
      {error && <p role="alert" className="w-full text-sm text-red-600">{error}</p>}
    </form>
  );
}
