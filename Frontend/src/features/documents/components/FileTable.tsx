import { Button } from "@/shared/components/ui/Button";
import { OrbitIcon } from "@/shared/components/ui/OrbitIcon";
import { formatDate, toFaDigits } from "@/shared/lib/utils";
import { canDropOn, countTotal, docKey, dragSelection, folderKey, summarizeCounts } from "../lib/fileManager";
import type { FileSelection, FolderListing } from "../types";
import { StatusBadge } from "./StatusBadge";

export const DRAG_TYPE = "application/x-orbit-files";

export function readDragged(event: React.DragEvent): FileSelection | null {
  try {
    const raw = event.dataTransfer.getData(DRAG_TYPE);
    return raw ? (JSON.parse(raw) as FileSelection) : null;
  } catch {
    return null;
  }
}

/** The rows of one folder: subfolders first, then documents. Rows are draggable (managers) and folders are drop targets. */
export function FileTable({ listing, selected, onToggle, onToggleAll, onOpen, canManage, cutKeys, onDropOnFolder, onRetry, onCancel, onRename }: {
  listing: FolderListing;
  selected: Set<string>;
  onToggle: (key: string) => void;
  onToggleAll: (all: boolean) => void;
  onOpen: (folderId: string) => void;
  canManage: boolean;
  cutKeys: Set<string>;
  onDropOnFolder: (selection: FileSelection, target: string) => void;
  onRetry: (documentId: string) => void;
  onCancel: (documentId: string) => void;
  onRename: (key: string) => void;
}) {
  const total = listing.folders.length + listing.documents.length;
  if (total === 0) return <p className="py-6 text-center text-sm text-gray-400">این پوشه خالی است.</p>;
  const allSelected = total > 0 && selected.size === total;

  const dragProps = (key: string) => canManage ? {
    draggable: true,
    onDragStart: (event: React.DragEvent) => {
      event.dataTransfer.setData(DRAG_TYPE, JSON.stringify(dragSelection(selected, key)));
      event.dataTransfer.effectAllowed = "move";
    },
  } : {};

  return <div className="overflow-x-auto">
    <table className="w-full min-w-[680px] text-right text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-gray-500">
          <th className="w-8 py-2"><input type="checkbox" aria-label="انتخاب همه" checked={allSelected} onChange={(event) => onToggleAll(event.target.checked)} /></th>
          <th className="py-2 font-medium">نام</th>
          <th className="py-2 font-medium">وضعیت</th>
          <th className="py-2 font-medium">تاریخ</th>
          <th className="py-2" />
        </tr>
      </thead>
      <tbody>
        {listing.folders.map(({ folder, status_counts }) => {
          const key = folderKey(folder.id);
          const count = countTotal(status_counts);
          const ready = status_counts.ready ?? 0;
          return <tr
            key={key}
            data-testid="folder-row"
            className={`border-b border-gray-100 ${selected.has(key) ? "bg-teal-50" : ""} ${cutKeys.has(key) ? "opacity-50" : ""}`}
            {...dragProps(key)}
            onDragOver={(event) => { if (canManage) event.preventDefault(); }}
            onDrop={(event) => {
              const dragged = readDragged(event);
              if (!canManage || !dragged || !canDropOn(dragged, folder.id)) return;
              event.preventDefault();
              onDropOnFolder(dragged, folder.id);
            }}
          >
            <td className="py-2.5"><input type="checkbox" aria-label={`انتخاب ${folder.name}`} checked={selected.has(key)} onChange={() => onToggle(key)} /></td>
            <td className="max-w-xs py-2.5 pe-3">
              <button type="button" onClick={() => onOpen(folder.id)} className="flex items-center gap-2 text-start font-medium text-gray-900 hover:text-teal-700">
                <OrbitIcon name="folder" className="h-5 w-5 text-amber-500" />
                <span className="break-words"><bdi>{folder.name}</bdi></span>
              </button>
            </td>
            <td className="py-2.5 text-xs text-gray-600">
              {count === 0 ? <span className="text-gray-400">خالی</span> : <>
                <p>{summarizeCounts(status_counts)}</p>
                <progress aria-label={`پیشرفت ${folder.name}`} max={count} value={ready} className="mt-1 h-1.5 w-40 accent-teal-600" />
              </>}
            </td>
            <td className="whitespace-nowrap py-2.5 text-gray-500">{formatDate(folder.created_at)}</td>
            <td className="py-2.5" />
          </tr>;
        })}
        {listing.documents.map((doc) => {
          const key = docKey(doc.id);
          return <tr key={key} data-testid="document-row" className={`border-b border-gray-100 last:border-0 ${selected.has(key) ? "bg-teal-50" : ""} ${cutKeys.has(key) ? "opacity-50" : ""}`} {...dragProps(key)}>
            <td className="py-2.5"><input type="checkbox" aria-label={`انتخاب ${doc.filename}`} checked={selected.has(key)} onChange={() => onToggle(key)} /></td>
            <td className="max-w-xs py-2.5 pe-3 font-medium text-gray-800">
              <span className="flex items-center gap-2"><OrbitIcon name="document" className="h-5 w-5 text-slate-400" /><span className="break-words"><bdi>{doc.filename}</bdi></span></span>
            </td>
            <td className="py-2.5">
              <StatusBadge status={doc.status} />
              {(doc.status === "failed" || doc.status === "unsupported") && doc.error_message && <p className="mt-1 max-w-xs break-words text-xs text-gray-500">{doc.error_message}</p>}
            </td>
            <td className="whitespace-nowrap py-2.5 text-gray-500">{formatDate(doc.created_at)}</td>
            <td className="whitespace-nowrap py-2.5 text-end">
              {canManage && (doc.status === "failed" || doc.status === "cancelled") && <Button type="button" variant="secondary" size="sm" onClick={() => onRetry(doc.id)} aria-label={`تلاش مجدد برای ${doc.filename}`}>تلاش مجدد</Button>}
              {canManage && doc.status === "processing" && <Button type="button" variant="ghost" size="sm" onClick={() => onCancel(doc.id)} aria-label={`لغو پردازش ${doc.filename}`}>لغو</Button>}
              {canManage && <Button type="button" variant="ghost" size="sm" onClick={() => onRename(key)} aria-label={`تغییر نام ${doc.filename}`}>تغییر نام</Button>}
            </td>
          </tr>;
        })}
      </tbody>
    </table>
    <p className="mt-2 text-xs text-gray-400">{toFaDigits(listing.folders.length)} پوشه · {toFaDigits(listing.documents.length)} فایل</p>
  </div>;
}
