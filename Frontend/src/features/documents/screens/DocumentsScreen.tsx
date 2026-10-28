"use client";

import { useEffect, useState } from "react";
import { Select } from "@/shared/components/ui/Select";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { loadWorkspace, WorkspaceOverview } from "@/shared/lib/workspaceApi";
import { FileManager } from "../components/FileManager";

export function DocumentsScreen() {
  const user = useAuthStore((state) => state.user);
  const [workspace, setWorkspace] = useState<WorkspaceOverview | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  const selectedProject = workspace?.projects.find((project) => project.id === projectId);
  const canManageProject = Boolean(selectedProject && (user?.role === "admin" || user?.role === "super_admin" || workspace?.managedTeamIds.has(selectedProject.team_id)));

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

  return (
    <main className="mx-auto max-w-6xl p-4 sm:p-6 lg:p-8">
      <div className="page-heading mb-6 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <h1 className="text-2xl font-bold text-gray-900">پایگاه اسناد و دانش</h1>
        <p className="mt-1 text-sm leading-6 text-gray-500">
          مدیریت فایل‌ها و پوشه‌های اسناد سازمانی پروژه‌ها جهت استفاده و ارجاع در هوش مصنوعی.
        </p>
      </div>

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
            <Select
              id="documents-project"
              value={projectId ?? ""}
              onValueChange={setProjectId}
              options={workspace.projects.map((project) => ({ value: project.id, label: project.name, description: project.description }))}
            />
          </div>
          {projectId && <FileManager key={projectId} projectId={projectId} canManage={canManageProject} />}
        </>
      )}
    </main>
  );
}
