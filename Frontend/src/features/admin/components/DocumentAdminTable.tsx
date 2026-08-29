import { Document } from "@/features/documents/types";
import { StatusBadge } from "@/features/documents/components/StatusBadge";
import { formatDate } from "@/shared/lib/utils";

export function DocumentAdminTable({ documents }: { documents: Document[] }) {
  if (documents.length === 0) {
    return <p className="text-sm text-gray-400">هیچ سندی در سیستم وجود ندارد.</p>;
  }

  return (
    <table className="w-full text-right text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-gray-500">
          <th className="py-2 font-medium">نام فایل</th>
          <th className="py-2 font-medium">وضعیت</th>
          <th className="py-2 font-medium">تاریخ آپلود</th>
        </tr>
      </thead>
      <tbody>
        {documents.map((doc) => (
          <tr key={doc.id} className="border-b border-gray-100">
            <td className="py-2">{doc.filename}</td>
            <td className="py-2">
              <StatusBadge status={doc.status} />
            </td>
            <td className="py-2 text-gray-500">{formatDate(doc.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
