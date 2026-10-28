"use client";

import { useMemo, useRef, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { toFaDigits } from "@/shared/lib/utils";
import { useBatchUpload } from "../hooks/useBatchUpload";
import { useFileManager } from "../hooks/useFileManager";
import { canDropOn, docKey, folderKey, selectionFromKeys, selectionSize } from "../lib/fileManager";
import type { FileSelection } from "../types";
import { ArchiveImportCard } from "./ArchiveImportCard";
import { ConflictDialog, DeleteDialog, NameDialog } from "./FileDialogs";
import { DRAG_TYPE, FileTable, readDragged } from "./FileTable";
import { StatusBadge } from "./StatusBadge";

const formatMegabytes = (bytes: number) => (bytes / 1024 / 1024).toFixed(bytes >= 10 * 1024 * 1024 ? 0 : 1);

type Dialog = { kind: "new-folder" } | { kind: "rename"; key: string } | { kind: "delete"; selection: FileSelection } | null;

/** Project file manager: folders, cut/copy/paste, drag & drop, per-file processing status, archive upload. */
export function FileManager({ projectId, canManage }: { projectId: string; canManage: boolean }) {
  const fm = useFileManager(projectId);
  const { report, isUploading, progress, run } = useBatchUpload(fm.uploadFiles, { projectFiles: true });
  const [dialog, setDialog] = useState<Dialog>(null);
  const files = useRef<HTMLInputElement>(null);
  const folder = useRef<HTMLInputElement>(null);
  const { listing, selected } = fm;

  const selection = useMemo(() => selectionFromKeys(selected), [selected]);
  const count = selectionSize(selection);
  const cutKeys = useMemo(() => {
    if (fm.clipboard?.mode !== "cut" || fm.clipboard.projectId !== projectId) return new Set<string>();
    return new Set([...fm.clipboard.selection.document_ids.map(docKey), ...fm.clipboard.selection.folder_ids.map(folderKey)]);
  }, [fm.clipboard, projectId]);

  const renameTarget = dialog?.kind === "rename" ? dialog.key : null;
  const renameInitial = renameTarget && listing
    ? (renameTarget.startsWith("f:") ? listing.folders.find((f) => folderKey(f.folder.id) === renameTarget)?.folder.name : listing.documents.find((d) => docKey(d.id) === renameTarget)?.filename) ?? ""
    : "";
  const singleKey = count === 1 ? [...selected][0] : null;

  function pick(input: HTMLInputElement | null, picked: FileList | null) {
    const list = Array.from(picked ?? []);
    if (input) input.value = "";
    if (list.length) void run(list);
  }

  const dropOnFolder = (dragged: FileSelection, target: string | null) => {
    if (canDropOn(dragged, target)) void fm.place("cut", dragged, target);
  };

  const pasteHere = fm.clipboard && fm.clipboard.projectId === projectId;
  const searching = fm.query.trim().length > 0;
  const acceptedFiles = report?.items.filter((item) => item.status === "accepted").length ?? 0;
  const rejected = report?.items.filter((item) => item.status === "rejected") ?? [];

  return <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5" aria-label="مدیریت فایل‌های پروژه">
    <div className="mb-3 flex flex-wrap items-center gap-2">
      {canManage && <>
        <Button type="button" size="sm" onClick={() => setDialog({ kind: "new-folder" })}>پوشهٔ جدید</Button>
        <Button type="button" size="sm" variant="secondary" disabled={isUploading} isLoading={isUploading} onClick={() => files.current?.click()}>آپلود فایل یا آرشیو</Button>
        <Button type="button" size="sm" variant="secondary" disabled={isUploading} onClick={() => folder.current?.click()}>آپلود پوشه</Button>
        <input ref={files} type="file" multiple aria-label="فایل‌های اسناد پروژه" className="hidden" onChange={(event) => pick(files.current, event.target.files)} />
        <input ref={folder} type="file" {...{ webkitdirectory: "" }} aria-label="پوشهٔ اسناد پروژه" className="hidden" onChange={(event) => pick(folder.current, event.target.files)} />
        <span className="mx-1 h-5 w-px bg-gray-200" aria-hidden="true" />
        <Button type="button" size="sm" variant="ghost" disabled={!count} onClick={() => fm.copyToClipboard("cut")}>برش</Button>
        <Button type="button" size="sm" variant="ghost" disabled={!count} onClick={() => fm.copyToClipboard("copy")}>کپی</Button>
        <Button type="button" size="sm" variant="ghost" disabled={!pasteHere || fm.busy} onClick={() => void fm.paste()}>
          چسباندن{pasteHere && fm.clipboard ? ` (${toFaDigits(selectionSize(fm.clipboard.selection))})` : ""}
        </Button>
        <Button type="button" size="sm" variant="ghost" disabled={!singleKey} onClick={() => singleKey && setDialog({ kind: "rename", key: singleKey })}>تغییر نام</Button>
        <Button type="button" size="sm" variant="ghost" disabled={!count || fm.busy} onClick={() => void fm.retry(selection)}>تلاش مجدد</Button>
        <Button type="button" size="sm" variant="ghost" disabled={!count || fm.busy} onClick={() => void fm.cancel(selection)}>لغو پردازش</Button>
        <Button type="button" size="sm" variant="ghost" className="text-red-600 hover:bg-red-50" disabled={!count || fm.busy} onClick={() => setDialog({ kind: "delete", selection })}>حذف</Button>
      </>}
      <div className="ms-auto flex items-center gap-2">
        <input type="search" value={fm.query} onChange={(event) => fm.setQuery(event.target.value)} placeholder="جست‌وجوی نام فایل…" aria-label="جست‌وجوی نام فایل" className="w-44 rounded-lg border border-gray-300 px-3 py-1.5 text-xs focus:border-teal-600 focus:outline-none" />
        <Button type="button" variant="ghost" size="sm" onClick={() => void fm.refresh()} disabled={fm.isLoading}>به‌روزرسانی</Button>
      </div>
    </div>

    {!searching && listing && <nav aria-label="مسیر پوشه" className="mb-3 flex flex-wrap items-center gap-1 text-sm">
      <Crumb label="ریشهٔ پروژه" onOpen={() => fm.open(null)} onDropItems={canManage ? (dragged) => dropOnFolder(dragged, null) : undefined} />
      {listing.breadcrumb.map((crumb, index) => <span key={crumb.id} className="flex items-center gap-1">
        <span aria-hidden="true" className="text-gray-300">/</span>
        {index === listing.breadcrumb.length - 1
          ? <span aria-current="page" className="px-1 font-semibold text-gray-900"><bdi>{crumb.name}</bdi></span>
          : <Crumb label={crumb.name} onOpen={() => fm.open(crumb.id)} onDropItems={canManage ? (dragged) => dropOnFolder(dragged, crumb.id) : undefined} />}
      </span>)}
    </nav>}

    {fm.error && <p role="alert" className="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{fm.error}</p>}

    {report && <div role="status" className="mb-3 space-y-1 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-6 text-slate-700">
      <p>{isUploading ? `در حال ارسال: ${toFaDigits(report.items.length)} از ${toFaDigits(report.total)} فایل` : `پایان ارسال: ${toFaDigits(acceptedFiles)} پذیرفته، ${toFaDigits(rejected.length + report.skipped.length)} ردشده`}</p>
      {isUploading && progress && progress.totalBytes > 0 && <>
        <progress aria-label="پیشرفت آپلود" max={progress.totalBytes} value={progress.loadedBytes} className="h-2 w-full accent-teal-600" />
        <p className="text-slate-500">{toFaDigits(formatMegabytes(progress.loadedBytes))} از {toFaDigits(formatMegabytes(progress.totalBytes))} مگابایت ({toFaDigits(Math.floor((progress.loadedBytes / progress.totalBytes) * 100))}٪) — فایل‌ها پس از رسیدن به سرور در فهرست ظاهر و به‌ترتیب پردازش می‌شوند.</p>
      </>}
      {!isUploading && <p className="text-slate-500">وضعیت پردازش هر فایل در فهرست زیر نمایش داده می‌شود.</p>}
      {(report.skipped.length > 0 || rejected.length > 0) && <details>
        <summary className="cursor-pointer">جزئیات فایل‌های ارسال‌نشده</summary>
        <ul className="max-h-40 space-y-1 overflow-y-auto pt-2">
          {[...report.skipped, ...rejected].map((item, index) => <li key={index} className="break-all text-red-700"><bdi>{item.filename}</bdi>: {item.error}</li>)}
        </ul>
      </details>}
    </div>}

    {!searching && listing && listing.archives.length > 0 && <div className="mb-3 space-y-2">
      {listing.archives.map((archive) => <ArchiveImportCard key={archive.id} archive={archive} canManage={canManage} onDismiss={(id) => void fm.dismissArchive(id)} />)}
    </div>}

    {searching
      ? <SearchResults hits={fm.hits} onShow={(folderId) => fm.open(folderId)} />
      : fm.isLoading && !listing
        ? <div className="space-y-3" aria-label="در حال بارگذاری اسناد">{[0, 1, 2].map((item) => <div key={item} className="h-10 animate-pulse rounded-xl bg-gray-100" />)}</div>
        : listing && <FileTable
          listing={listing}
          selected={selected}
          onToggle={fm.toggle}
          onToggleAll={fm.selectAll}
          onOpen={fm.open}
          canManage={canManage}
          cutKeys={cutKeys}
          onDropOnFolder={dropOnFolder}
          onRetry={(id) => void fm.retry({ document_ids: [id], folder_ids: [] })}
          onCancel={(id) => void fm.cancel({ document_ids: [id], folder_ids: [] })}
          onRename={(key) => setDialog({ kind: "rename", key })}
        />}

    {dialog?.kind === "new-folder" && <NameDialog title="پوشهٔ جدید" submitLabel="ساخت" onSubmit={fm.createFolder} onClose={() => setDialog(null)} />}
    {dialog?.kind === "rename" && <NameDialog title="تغییر نام" initial={renameInitial} submitLabel="ذخیره" onSubmit={(name) => fm.renameItem(dialog.key, name)} onClose={() => setDialog(null)} />}
    {dialog?.kind === "delete" && <DeleteDialog files={dialog.selection.document_ids.length} folders={dialog.selection.folder_ids.length} busy={fm.busy} onClose={() => setDialog(null)} onConfirm={() => { void fm.remove(dialog.selection).then(() => setDialog(null)); }} />}
    {fm.conflict && <ConflictDialog conflict={fm.conflict} onClose={fm.dismissConflict} />}
  </section>;
}

function Crumb({ label, onOpen, onDropItems }: { label: string; onOpen: () => void; onDropItems?: (selection: FileSelection) => void }) {
  const [over, setOver] = useState(false);
  return <button
    type="button"
    onClick={onOpen}
    onDragOver={(event) => { if (onDropItems && event.dataTransfer.types.includes(DRAG_TYPE)) { event.preventDefault(); setOver(true); } }}
    onDragLeave={() => setOver(false)}
    onDrop={(event) => { setOver(false); const dragged = readDragged(event); if (onDropItems && dragged) { event.preventDefault(); onDropItems(dragged); } }}
    className={`rounded-md px-1.5 py-0.5 text-teal-700 hover:bg-teal-50 ${over ? "bg-teal-100 ring-2 ring-teal-300" : ""}`}
  ><bdi>{label}</bdi></button>;
}

function SearchResults({ hits, onShow }: { hits: { document: { id: string; filename: string; status: import("../types").DocumentStatus; folder_id?: string | null }; path: string[] }[] | null; onShow: (folderId: string | null) => void }) {
  if (hits === null) return <p className="text-sm text-gray-400">در حال جست‌وجو…</p>;
  if (hits.length === 0) return <p className="py-6 text-center text-sm text-gray-400">فایلی با این نام پیدا نشد.</p>;
  return <ul className="divide-y divide-gray-100 text-sm" aria-label="نتایج جست‌وجو">
    {hits.map(({ document, path }) => <li key={document.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
      <div className="min-w-0"><p className="break-words font-medium text-gray-800"><bdi>{document.filename}</bdi></p><p className="text-xs text-gray-500"><bdi>{["ریشهٔ پروژه", ...path].join(" / ")}</bdi></p></div>
      <div className="flex items-center gap-2"><StatusBadge status={document.status} /><Button type="button" variant="ghost" size="sm" onClick={() => onShow(document.folder_id ?? null)}>نمایش در پوشه</Button></div>
    </li>)}
  </ul>;
}
