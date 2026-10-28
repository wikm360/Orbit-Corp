"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import type { PendingConflict } from "../hooks/useFileManager";

/** Asks for one name (new folder / rename). A server error (e.g. duplicate name) stays in the dialog. */
export function NameDialog({ title, initial = "", submitLabel, onSubmit, onClose }: {
  title: string;
  initial?: string;
  submitLabel: string;
  onSubmit: (name: string) => Promise<void>;
  onClose: () => void;
}) {
  const [name, setName] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSubmit(name.trim());
      onClose();
    } catch (err) {
      setError(friendlyErrorMessage(err, "ذخیره ناموفق بود."));
    } finally {
      setSaving(false);
    }
  }

  return <Modal isOpen onClose={onClose} title={title}>
    <form onSubmit={submit} className="space-y-3">
      <input autoFocus value={name} onChange={(event) => setName(event.target.value)} maxLength={255} aria-label="نام" className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-100" />
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onClose}>انصراف</Button>
        <Button type="submit" disabled={!name.trim()} isLoading={saving}>{submitLabel}</Button>
      </div>
    </form>
  </Modal>;
}

export function DeleteDialog({ files, folders, onConfirm, onClose, busy }: {
  files: number;
  folders: number;
  onConfirm: () => void;
  onClose: () => void;
  busy: boolean;
}) {
  const parts = [folders > 0 && `${folders} پوشه (با همه‌ی محتوایش)`, files > 0 && `${files} فایل`].filter(Boolean).join(" و ");
  return <Modal isOpen onClose={onClose} title="حذف">
    <p className="text-sm leading-7 text-gray-600">{parts} حذف شود؟ این کار قابل بازگشت نیست.</p>
    <div className="mt-6 flex justify-end gap-2">
      <Button variant="ghost" onClick={onClose}>انصراف</Button>
      <Button variant="danger" onClick={onConfirm} isLoading={busy}>حذف</Button>
    </div>
  </Modal>;
}

export function ConflictDialog({ conflict, onClose }: { conflict: PendingConflict; onClose: () => void }) {
  return <Modal isOpen onClose={onClose} title="نام تکراری">
    <p className="text-sm leading-7 text-gray-600">{conflict.message}</p>
    <p className="mt-2 text-sm leading-7 text-gray-600">می‌خواهید هر دو نگه داشته شوند (به نام جدید «نام (۱)»)؟</p>
    <div className="mt-6 flex justify-end gap-2">
      <Button variant="ghost" onClick={onClose}>انصراف</Button>
      <Button onClick={() => void conflict.retryWithRename()}>نگه‌داشتن هر دو</Button>
    </div>
  </Modal>;
}
