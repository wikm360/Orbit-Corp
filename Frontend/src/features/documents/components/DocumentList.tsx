import { Button } from "@/shared/components/ui/Button";
import { formatDate } from "@/shared/lib/utils";

import { Document } from "../types";
import { StatusBadge } from "./StatusBadge";

interface DocumentListProps {
  documents: Document[];
  onDelete: (id: string) => void;
  deletingId?: string | null;
}

export function DocumentList({ documents, onDelete, deletingId }: DocumentListProps) {
  if (documents.length === 0) {
    return <p className="text-sm text-gray-400">هنوز سندی آپلود نشده است.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-right text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-gray-500">
          <th className="py-2 font-medium">نام فایل</th>
          <th className="py-2 font-medium">وضعیت</th>
          <th className="py-2 font-medium">تاریخ آپلود</th>
          <th className="py-2 font-medium"></th>
        </tr>
      </thead>
      <tbody>
        {documents.map((doc) => (
          <tr key={doc.id} className="border-b border-gray-100 last:border-0">
            <td className="max-w-xs break-words py-3 pe-3 font-medium text-gray-800">{doc.filename}</td>
            <td className="py-3">
              <StatusBadge status={doc.status} />
              {doc.status === "failed" && doc.error_message && (
                <p className="mt-1 max-w-xs truncate text-xs text-red-500">
                  {doc.error_message}
                </p>
              )}
            </td>
            <td className="whitespace-nowrap py-3 text-gray-500">{formatDate(doc.created_at)}</td>
            <td className="py-3">
              <Button
                variant="ghost"
                size="sm"
                isLoading={deletingId === doc.id}
                disabled={Boolean(deletingId)}
                className="text-red-600 hover:bg-red-50"
                onClick={() => onDelete(doc.id)}
              >
                حذف
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
      </table>
    </div>
  );
}
