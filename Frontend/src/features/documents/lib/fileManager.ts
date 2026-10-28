import type { DocumentStatus, FileSelection, StatusCounts } from "../types";
import { toFaDigits } from "@/shared/lib/utils";

/** Selection keys are `d:<id>` (document) / `f:<id>` (folder) so one Set can hold both. */
export const docKey = (id: string) => `d:${id}`;
export const folderKey = (id: string) => `f:${id}`;

export function selectionFromKeys(keys: Iterable<string>): FileSelection {
  const selection: FileSelection = { document_ids: [], folder_ids: [] };
  for (const key of keys) {
    if (key.startsWith("d:")) selection.document_ids.push(key.slice(2));
    else if (key.startsWith("f:")) selection.folder_ids.push(key.slice(2));
  }
  return selection;
}

export const selectionSize = (selection: FileSelection) => selection.document_ids.length + selection.folder_ids.length;

export interface Clipboard {
  mode: "cut" | "copy";
  projectId: string;
  selection: FileSelection;
}

const STATUS_ORDER: DocumentStatus[] = ["ready", "processing", "failed", "cancelled", "unsupported"];
const STATUS_LABEL: Record<DocumentStatus, string> = {
  ready: "آماده",
  processing: "در حال پردازش",
  failed: "ناموفق",
  cancelled: "لغوشده",
  unsupported: "پشتیبانی‌نشده",
};

export function countTotal(counts: StatusCounts): number {
  return STATUS_ORDER.reduce((sum, status) => sum + (counts[status] ?? 0), 0);
}

/** «۴۰ آماده · ۷ در حال پردازش · ۱ ناموفق»; empty string for an empty folder. */
export function summarizeCounts(counts: StatusCounts): string {
  return STATUS_ORDER.filter((status) => (counts[status] ?? 0) > 0)
    .map((status) => `${toFaDigits(counts[status] ?? 0)} ${STATUS_LABEL[status]}`)
    .join(" · ");
}

/** True while anything below still changes on its own (worth polling). */
export function hasActiveWork(listing: { folders: { status_counts: StatusCounts }[]; documents: { status: DocumentStatus }[]; archives: { status: string }[] } | null): boolean {
  if (!listing) return false;
  return listing.documents.some((d) => d.status === "processing")
    || listing.folders.some((f) => (f.status_counts.processing ?? 0) > 0)
    || listing.archives.some((a) => a.status === "extracting");
}

/** The ids a drag carries: the whole selection when the dragged row is part of it, else just that row. */
export function dragSelection(selected: Set<string>, draggedKey: string): FileSelection {
  return selectionFromKeys(selected.has(draggedKey) ? selected : [draggedKey]);
}

/** A folder cannot be dropped onto itself (the server also rejects its own subtree). */
export function canDropOn(selection: FileSelection, targetFolderId: string | null): boolean {
  return targetFolderId === null || !selection.folder_ids.includes(targetFolderId);
}
