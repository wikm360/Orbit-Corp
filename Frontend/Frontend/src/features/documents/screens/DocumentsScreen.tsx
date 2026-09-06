"use client";

import { DocumentList } from "../components/DocumentList";
import { UploadForm } from "../components/UploadForm";
import { useDocuments } from "../hooks/useDocuments";

export function DocumentsScreen() {
  const { documents, isLoading, error, upload, remove } = useDocuments();

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-4 text-xl font-semibold text-gray-900">اسناد سازمانی</h1>

      <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4">
        <UploadForm onUpload={upload} />
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        {isLoading ? (
          <p className="text-sm text-gray-400">در حال بارگذاری...</p>
        ) : error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : (
          <DocumentList documents={documents} onDelete={remove} />
        )}
      </div>
    </div>
  );
}
