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
import { usePersonalDocuments } from "../hooks/usePersonalDocuments";

type DocumentTab = "projects" | "personal";

export function DocumentsScreen() {
  const user = useAuthStore((state) => state.user);
  const [activeTab, setActiveTab] = useState<DocumentTab>("projects");
  const [workspace, setWorkspace] = useState<WorkspaceOverview | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  // Project documents hook
  const {
    documents: projectDocuments,
    isLoading: isProjectLoading,
    error: projectError,
    deletingId: deletingProjectId,
    refresh: refreshProjectDocs,
    upload: uploadProjectDoc,
    remove: removeProjectDoc,
  } = useDocuments(projectId);

  // Personal documents hook
  const {
    documents: personalDocuments,
    isLoading: isPersonalLoading,
    error: personalError,
    deletingId: deletingPersonalId,
    refresh: refreshPersonalDocs,
    upload: uploadPersonalDoc,
    remove: removePersonalDoc,
  } = usePersonalDocuments();

  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const selectedProject = workspace?.projects.find((project) => project.id === projectId);
  const canManageProject = Boolean(selectedProject && workspace?.managedTeamIds.has(selectedProject.team_id));

  const currentDocs = activeTab === "projects" ? projectDocuments : personalDocuments;
  const pendingDocument = currentDocs.find((document) => document.id === pendingDeleteId);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    loadWorkspace(user)
      .then((data) => {
        if (cancelled) return;
        setWorkspace(data);
        setProjectId((current) =>
          data.projects.some((project) => project.id === current) ? current : data.projects[0]?.id ?? null
        );
      })
      .catch((err) => {
        if (!cancelled) setWorkspaceError(friendlyErrorMessage(err, "دریافت پروژه‌ها ناموفق بود."));
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  async function confirmDelete() {
    if (!pendingDeleteId) return;
    try {
      if (activeTab === "projects") {
        await removeProjectDoc(pendingDeleteId);
      } else {
        await removePersonalDoc(pendingDeleteId);
      }
      setPendingDeleteId(null);
    } catch {
      /* Error is shown above the list */
    }
  }

  return (
    <main className="mx-auto max-w-5xl p-4 sm:p-6 lg:p-8">
      <div className="page-heading mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">پایگاه اسناد و دانش</h1>
          <p className="mt-1 text-sm leading-6 text-gray-500">
            مدیریت اسناد سازمانی پروژه‌ها و اسناد شخصی جهت استفاده و ارجاع در هوش مصنوعی.
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="inline-flex rounded-xl bg-gray-100 p-1 text-sm">
          <button
            type="button"
            onClick={() => {
              setActiveTab("projects");
              setPendingDeleteId(null);
            }}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 font-medium transition ${
              activeTab === "projects"
                ? "bg-white text-gray-950 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M3 9h18M9 9v12" />
            </svg>
            اسناد پروژه‌ها
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab("personal");
              setPendingDeleteId(null);
            }}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 font-medium transition ${
              activeTab === "personal"
                ? "bg-white text-gray-950 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6M8 13h8M8 17h6" />
            </svg>
            اسناد شخصی من
            {personalDocuments.length > 0 && (
              <span className="rounded-full bg-brand-100 px-2 py-0.5 text-[11px] font-semibold text-brand-800">
                {personalDocuments.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {activeTab === "projects" ? (
        <>
          {workspaceError && (
            <p role="alert" className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
              {workspaceError}
            </p>
          )}
          {!workspace && !workspaceError && <p className="text-sm text-gray-500">در حال دریافت پروژه‌ها...</p>}
          {workspace && workspace.projects.length === 0 && (
            <p className="rounded-xl bg-white p-4 text-sm text-gray-500">
              پروژه‌ای در دسترس شما نیست. از بخش فضای کاری پروژه بسازید یا درخواست عضویت کنید.
            </p>
          )}
          {workspace && workspace.projects.length > 0 && (
            <>
              <div className="mb-6 flex flex-col gap-2 sm:max-w-sm">
                <label htmlFor="documents-project" className="text-sm font-medium text-gray-700">
                  انتخاب پروژه
                </label>
                <select
                  id="documents-project"
                  value={projectId ?? ""}
                  onChange={(event) => {
                    setPendingDeleteId(null);
                    setProjectId(event.target.value);
                  }}
                  className="h-11 rounded-xl border border-gray-200 bg-white px-3 text-sm"
                >
                  {workspace.projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>

              {canManageProject && (
                <section className="mb-6 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
                  <h2 className="mb-4 font-semibold text-gray-800">افزودن سند جدید به این پروژه</h2>
                  <UploadForm onUpload={uploadProjectDoc} />
                </section>
              )}

              <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 className="font-semibold text-gray-800">فهرست اسناد پروژه</h2>
                  <Button type="button" variant="ghost" size="sm" onClick={refreshProjectDocs} disabled={isProjectLoading}>
                    به‌روزرسانی
                  </Button>
                </div>
                {projectError && (
                  <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
                    {projectError}
                  </p>
                )}
                {isProjectLoading ? (
                  <div className="space-y-3" aria-label="در حال بارگذاری اسناد">
                    {[0, 1, 2].map((item) => (
                      <div key={item} className="h-10 animate-pulse rounded-xl bg-gray-100" />
                    ))}
                  </div>
                ) : (
                  <DocumentList
                    documents={projectDocuments}
                    onDelete={setPendingDeleteId}
                    deletingId={deletingProjectId}
                    canDelete={canManageProject}
                  />
                )}
              </section>
            </>
          )}
        </>
      ) : (
        /* Personal Documents Tab */
        <>
          <section className="mb-6 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
            <h2 className="mb-1 font-semibold text-gray-800">افزودن سند شخصی</h2>
            <p className="mb-4 text-xs text-gray-500">
              اسناد شخصی فقط برای شما قابل دسترسی هستند و در تمام گفتگوهایتان با منشن کردن یا ارجاع در دسترس هوش مصنوعی خواهند بود.
            </p>
            <UploadForm onUpload={uploadPersonalDoc} />
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="font-semibold text-gray-800">اسناد اختصاصی من</h2>
                <span className="text-xs text-gray-500">
                  {personalDocuments.length} سند شخصی بارگذاری‌شده
                </span>
              </div>
              <Button type="button" variant="ghost" size="sm" onClick={refreshPersonalDocs} disabled={isPersonalLoading}>
                به‌روزرسانی
              </Button>
            </div>
            {personalError && (
              <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
                {personalError}
              </p>
            )}
            {isPersonalLoading ? (
              <div className="space-y-3" aria-label="در حال بارگذاری اسناد">
                {[0, 1, 2].map((item) => (
                  <div key={item} className="h-10 animate-pulse rounded-xl bg-gray-100" />
                ))}
              </div>
            ) : (
              <DocumentList
                documents={personalDocuments}
                onDelete={setPendingDeleteId}
                deletingId={deletingPersonalId}
                canDelete={true}
              />
            )}
          </section>
        </>
      )}

      <Modal isOpen={Boolean(pendingDeleteId)} onClose={() => setPendingDeleteId(null)} title="حذف سند">
        <p className="text-sm leading-7 text-gray-600">
          سند «{pendingDocument?.filename ?? "انتخاب‌شده"}» حذف شود؟
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setPendingDeleteId(null)}>
            انصراف
          </Button>
          <Button
            variant="danger"
            onClick={confirmDelete}
            isLoading={Boolean(deletingProjectId || deletingPersonalId)}
          >
            حذف سند
          </Button>
        </div>
      </Modal>
    </main>
  );
}
