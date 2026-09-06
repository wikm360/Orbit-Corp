"use client";

import { useState } from "react";

import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";

import { DocumentList } from "../components/DocumentList";
import { UploadForm } from "../components/UploadForm";
import { useDocuments } from "../hooks/useDocuments";

export function DocumentsScreen() {
  const { documents, isLoading, error, deletingId, refresh, upload, remove } = useDocuments();
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const pendingDocument = documents.find((document) => document.id === pendingDeleteId);

  async function confirmDelete() {
    if (!pendingDeleteId) return;
    try {
      await remove(pendingDeleteId);
      setPendingDeleteId(null);
    } catch {
      // The hook exposes the localized error above the list.
    }
  }

  return (
    <main className="mx-auto max-w-5xl p-4 sm:p-6 lg:p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">اسناد سازمانی</h1>
        <p className="mt-1 text-sm leading-6 text-gray-500">اسناد تیم خود را برای جست‌وجو و پاسخ‌گویی دستیار مدیریت کنید.</p>
      </div>

      <section className="mb-6 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
        <h2 className="mb-4 font-semibold text-gray-800">افزودن سند جدید</h2>
        <UploadForm onUpload={upload} />
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="font-semibold text-gray-800">فهرست اسناد</h2>
          <Button type="button" variant="ghost" size="sm" onClick={refresh} disabled={isLoading}>
            به‌روزرسانی
          </Button>
        </div>
        {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        {isLoading ? (
          <div className="space-y-3" aria-label="در حال بارگذاری اسناد">
            {[0, 1, 2].map((item) => <div key={item} className="h-10 animate-pulse rounded-xl bg-gray-100" />)}
          </div>
        ) : (
          <DocumentList documents={documents} onDelete={setPendingDeleteId} deletingId={deletingId} />
        )}
      </section>

      <Modal
        isOpen={Boolean(pendingDeleteId)}
        onClose={() => !deletingId && setPendingDeleteId(null)}
        title="حذف سند"
      >
        <p className="text-sm leading-7 text-gray-600">
          سند «{pendingDocument?.filename ?? "انتخاب‌شده"}» حذف شود؟ این سند دیگر در پاسخ‌های دستیار استفاده نخواهد شد.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setPendingDeleteId(null)} disabled={Boolean(deletingId)}>انصراف</Button>
          <Button variant="danger" onClick={confirmDelete} isLoading={Boolean(deletingId)}>حذف سند</Button>
        </div>
      </Modal>
    </main>
  );
}
