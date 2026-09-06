import { Document } from "@/features/documents/types";
import { StatusBadge } from "@/features/documents/components/StatusBadge";
import { formatDate } from "@/shared/lib/utils";

export function DocumentAdminTable({ documents }: { documents: Document[] }) {
  if (documents.length === 0) {
    return <p className="text-sm text-gray-400">هیچ سندی در سیستم وجود ندارد.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-right text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-gray-500">
          <th className="py-2 font-medium">نام فایل</th>
          <th className="py-2 font-medium">وضعیت</th>
          <th className="py-2 font-medium">تاریخ آپلود</th>
        </tr>
      </thead>
      <tbody>
        {documents.map((doc) => (
          <tr key={doc.id} className="border-b border-gray-100 last:border-0">
            <td className="max-w-sm break-words py-3 pe-3 font-medium text-gray-800">{doc.filename}</td>
            <td className="py-3">
              <StatusBadge status={doc.status} />
            </td>
            <td className="whitespace-nowrap py-3 text-gray-500">{formatDate(doc.created_at)}</td>
          </tr>
        ))}
      </tbody>
      </table>
    </div>
  );
}
