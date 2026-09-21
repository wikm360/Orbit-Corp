"use client";

import { useEffect, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { loadWorkspace, WorkspaceOverview } from "@/shared/lib/workspaceApi";
import { DocumentList } from "../components/DocumentList";
import { UploadForm } from "../components/UploadForm";
import { useDocuments } from "../hooks/useDocuments";

export function DocumentsScreen() {
  const user = useAuthStore((state) => state.user);
  const [workspace, setWorkspace] = useState<WorkspaceOverview | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const { documents, isLoading, error, deletingId, refresh, upload, remove } = useDocuments(projectId);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const pendingDocument = documents.find((document) => document.id === pendingDeleteId);
  const selectedProject = workspace?.projects.find((project) => project.id === projectId);
  const canManage = Boolean(selectedProject && workspace?.managedTeamIds.has(selectedProject.team_id));

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    loadWorkspace(user).then((data) => {
      if (cancelled) return;
      setWorkspace(data);
      setProjectId((current) => data.projects.some((project) => project.id === current) ? current : data.projects[0]?.id ?? null);
    }).catch((err) => { if (!cancelled) setWorkspaceError(friendlyErrorMessage(err, "دریافت پروژه‌ها ناموفق بود.")); });
    return () => { cancelled = true; };
  }, [user]);

  async function confirmDelete() {
    if (!pendingDeleteId) return;
    try {
      await remove(pendingDeleteId);
      setPendingDeleteId(null);
    } catch { /* Error is shown above the list. */ }
  }

  return (
    <main className="mx-auto max-w-5xl p-4 sm:p-6 lg:p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">اسناد پروژه</h1>
        <p className="mt-1 text-sm leading-6 text-gray-500">اسناد هر پروژه جداگانه نگهداری و در پاسخ‌های مربوط به همان پروژه استفاده می‌شوند.</p>
      </div>
      {workspaceError && <p role="alert" className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{workspaceError}</p>}
      {!workspace && !workspaceError && <p className="text-sm text-gray-500">در حال دریافت پروژه‌ها...</p>}
      {workspace && workspace.projects.length === 0 && <p className="rounded-xl bg-white p-4 text-sm text-gray-500">پروژه‌ای در دسترس شما نیست. از بخش فضای کاری پروژه بسازید یا درخواست عضویت کنید.</p>}
      {workspace && workspace.projects.length > 0 && <>
        <div className="mb-6 flex flex-col gap-2 sm:max-w-sm">
          <label htmlFor="documents-project" className="text-sm font-medium text-gray-700">پروژه</label>
          <select id="documents-project" value={projectId ?? ""} onChange={(event) => { setPendingDeleteId(null); setProjectId(event.target.value); }} className="h-11 rounded-xl border border-gray-200 bg-white px-3 text-sm">
            {workspace.projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
          </select>
        </div>
        {canManage && <section className="mb-6 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
          <h2 className="mb-4 font-semibold text-gray-800">افزودن سند جدید</h2>
          <UploadForm onUpload={upload} />
        </section>}
        <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="font-semibold text-gray-800">فهرست اسناد</h2>
            <Button type="button" variant="ghost" size="sm" onClick={refresh} disabled={isLoading}>به‌روزرسانی</Button>
          </div>
          {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
          {isLoading ? <div className="space-y-3" aria-label="در حال بارگذاری اسناد">{[0, 1, 2].map((item) => <div key={item} className="h-10 animate-pulse rounded-xl bg-gray-100" />)}</div> : <DocumentList documents={documents} onDelete={setPendingDeleteId} deletingId={deletingId} canDelete={canManage} />}
        </section>
      </>}
      <Modal isOpen={Boolean(pendingDeleteId)} onClose={() => !deletingId && setPendingDeleteId(null)} title="حذف سند">
        <p className="text-sm leading-7 text-gray-600">سند «{pendingDocument?.filename ?? "انتخاب‌شده"}» حذف شود؟</p>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setPendingDeleteId(null)} disabled={Boolean(deletingId)}>انصراف</Button>
          <Button variant="danger" onClick={confirmDelete} isLoading={Boolean(deletingId)}>حذف سند</Button>
        </div>
      </Modal>
    </main>
  );
}
