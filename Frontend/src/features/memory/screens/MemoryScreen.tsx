"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { loadWorkspace, type WorkspaceOverview } from "@/shared/lib/workspaceApi";

import { CATEGORY_OPTIONS, MemoryForm } from "../components/MemoryForm";
import { CATEGORY_META, MemoryCard } from "../components/MemoryCard";
import { useProjectMemories } from "../hooks/useProjectMemories";
import type { MemoryCategory, ProjectMemory, ProjectMemoryCreate } from "../types";

type VerificationFilter = "all" | "verified" | "unverified";

function StatCard({ label, value, tone = "slate" }: { label: string; value: number; tone?: "slate" | "teal" | "amber" }) {
  const toneClasses = {
    slate: "bg-slate-50 text-slate-700 ring-slate-200",
    teal: "bg-teal-50 text-teal-700 ring-teal-200",
    amber: "bg-amber-50 text-amber-700 ring-amber-200",
  }[tone];
  return (
    <div className={`rounded-2xl p-4 ring-1 ring-inset ${toneClasses}`}>
      <p className="text-xs opacity-75">{label}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums">{value.toLocaleString("fa-IR")}</p>
    </div>
  );
}

export function MemoryScreen() {
  const user = useAuthStore((state) => state.user);
  const [workspace, setWorkspace] = useState<WorkspaceOverview | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<MemoryCategory | "all">("all");
  const [verification, setVerification] = useState<VerificationFilter>("all");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingMemory, setEditingMemory] = useState<ProjectMemory | null>(null);
  const [deletingMemory, setDeletingMemory] = useState<ProjectMemory | null>(null);

  const managedProjects = useMemo(
    () => workspace?.projects.filter((project) => workspace.managedTeamIds.has(project.team_id)) ?? [],
    [workspace]
  );
  const selectedProject = managedProjects.find((project) => project.id === projectId) ?? null;
  const { memories, isLoading, mutationKey, error, refresh, createMemory, updateMemory, removeMemory } = useProjectMemories(projectId);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    loadWorkspace(user)
      .then((data) => {
        if (cancelled) return;
        setWorkspace(data);
        const manageable = data.projects.filter((project) => data.managedTeamIds.has(project.team_id));
        setProjectId((current) => manageable.some((project) => project.id === current) ? current : manageable[0]?.id ?? null);
      })
      .catch((err) => {
        if (!cancelled) setWorkspaceError(friendlyErrorMessage(err, "دریافت پروژه‌های قابل مدیریت ناموفق بود."));
      });
    return () => { cancelled = true; };
  }, [user]);

  function selectProject(nextProjectId: string) {
    setProjectId(nextProjectId);
    setQuery("");
    setCategory("all");
    setVerification("all");
    setEditingMemory(null);
    setDeletingMemory(null);
  }

  const filteredMemories = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("fa-IR");
    return memories.filter((memory) => {
      if (category !== "all" && memory.category !== category) return false;
      if (verification === "verified" && !memory.is_verified) return false;
      if (verification === "unverified" && memory.is_verified) return false;
      return !normalizedQuery || memory.fact_text.toLocaleLowerCase("fa-IR").includes(normalizedQuery);
    });
  }, [category, memories, query, verification]);

  const verifiedCount = memories.filter((memory) => memory.is_verified).length;
  const unverifiedCount = memories.length - verifiedCount;

  async function handleCreate(payload: ProjectMemoryCreate) {
    await createMemory(payload);
    setIsCreateOpen(false);
  }

  async function handleEdit(payload: ProjectMemoryCreate) {
    if (!editingMemory) return;
    await updateMemory(editingMemory.id, payload);
    setEditingMemory(null);
  }

  async function handleDelete() {
    if (!deletingMemory) return;
    await removeMemory(deletingMemory.id);
    setDeletingMemory(null);
  }

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6 lg:p-8">
      <header className="page-heading overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-teal-50 text-teal-700 ring-1 ring-inset ring-teal-200">
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-6 w-6"><path strokeLinecap="round" strokeLinejoin="round" d="M9.5 4.5A3.5 3.5 0 0 0 6 8v1a3 3 0 0 0-1 5.83V16a4 4 0 0 0 4 4h1V4.5h-.5ZM14.5 4.5A3.5 3.5 0 0 1 18 8v1a3 3 0 0 1 1 5.83V16a4 4 0 0 1-4 4h-1V4.5h.5Z"/><path strokeLinecap="round" d="M7 10h3M14 10h3M7 15h3M14 15h3"/></svg>
            </span>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">حافظه پروژه</h1>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-gray-500">واقعیت‌ها، تصمیم‌ها و قواعد ماندگاری که دستیار در گفتگوهای بعدی این پروژه به خاطر می‌آورد.</p>
            </div>
          </div>
          <Button type="button" onClick={() => setIsCreateOpen(true)} disabled={!projectId || Boolean(mutationKey)}>
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4"><path strokeLinecap="round" d="M12 5v14M5 12h14" /></svg>
            افزودن به حافظه
          </Button>
        </div>
      </header>

      {(workspaceError || error) && (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
          <span>{workspaceError || error}</span>
          {error && <button type="button" className="shrink-0 font-semibold underline underline-offset-4" onClick={() => void refresh()}>تلاش دوباره</button>}
        </div>
      )}

      {!workspace && !workspaceError && (
        <div className="space-y-3" aria-label="در حال دریافت پروژه‌ها"><div className="h-24 animate-pulse rounded-2xl bg-white"/><div className="h-56 animate-pulse rounded-2xl bg-white"/></div>
      )}

      {workspace && managedProjects.length === 0 && (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
          <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-slate-100 text-slate-500">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-6 w-6"><path strokeLinecap="round" strokeLinejoin="round" d="M12 3 4 6v6c0 4.8 3.4 7.7 8 9 4.6-1.3 8-4.2 8-9V6l-8-3Z"/><path strokeLinecap="round" d="M9.5 12h5"/></svg>
          </span>
          <h2 className="mt-4 font-semibold text-slate-800">پروژه قابل مدیریتی ندارید</h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">مدیریت حافظه فقط برای سرپرست تیم پروژه و مدیران سازمان در دسترس است.</p>
        </section>
      )}

      {workspace && managedProjects.length > 0 && (
        <>
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
            <div className="grid gap-5 lg:grid-cols-[minmax(240px,1fr)_minmax(0,2fr)] lg:items-end">
              <div>
                <label htmlFor="memory-project" className="mb-2 block text-sm font-medium text-gray-700">پروژه</label>
                <select id="memory-project" value={projectId ?? ""} onChange={(event) => selectProject(event.target.value)} className="h-11 w-full rounded-xl border border-gray-200 bg-white px-3 text-sm shadow-sm focus:border-teal-400 focus:outline-none focus:ring-4 focus:ring-teal-100">
                  {managedProjects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
                </select>
                {selectedProject?.description && <p className="mt-2 line-clamp-2 text-xs leading-5 text-gray-500">{selectedProject.description}</p>}
              </div>
              <div className="grid grid-cols-3 gap-2 sm:gap-3">
                <StatCard label="کل حافظه" value={memories.length} />
                <StatCard label="تأییدشده" value={verifiedCount} tone="teal" />
                <StatCard label="نیازمند بررسی" value={unverifiedCount} tone="amber" />
              </div>
            </div>
          </section>

          <section className="space-y-4">
            <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm lg:flex-row lg:items-center">
              <label className="relative min-w-0 flex-1">
                <span className="sr-only">جست‌وجو در حافظه</span>
                <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"><circle cx="11" cy="11" r="7"/><path strokeLinecap="round" d="m20 20-4-4"/></svg>
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="جست‌وجو در متن حافظه..." className="h-10 w-full rounded-xl border border-gray-200 bg-slate-50 pr-9 pl-3 text-sm outline-none transition focus:border-teal-400 focus:bg-white focus:ring-4 focus:ring-teal-100" />
              </label>
              <select aria-label="فیلتر دسته‌بندی" value={category} onChange={(event) => setCategory(event.target.value as MemoryCategory | "all")} className="h-10 rounded-xl border border-gray-200 bg-white px-3 text-sm text-gray-700">
                <option value="all">همه دسته‌ها</option>
                {CATEGORY_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
              <select aria-label="فیلتر وضعیت تأیید" value={verification} onChange={(event) => setVerification(event.target.value as VerificationFilter)} className="h-10 rounded-xl border border-gray-200 bg-white px-3 text-sm text-gray-700">
                <option value="all">همه وضعیت‌ها</option><option value="verified">تأییدشده</option><option value="unverified">در انتظار تأیید</option>
              </select>
              <Button type="button" variant="ghost" size="sm" onClick={() => void refresh()} disabled={isLoading || Boolean(mutationKey)} className="h-10">به‌روزرسانی</Button>
            </div>

            {isLoading ? (
              <div className="grid gap-4 lg:grid-cols-2" aria-label="در حال بارگذاری حافظه">
                {[0, 1, 2, 3].map((item) => <div key={item} className="h-48 animate-pulse rounded-2xl border border-slate-100 bg-white" />)}
              </div>
            ) : memories.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
                <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-teal-50 text-teal-600"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-6 w-6"><path strokeLinecap="round" d="M12 5v14M5 12h14"/></svg></span>
                <h2 className="mt-4 font-semibold text-slate-800">حافظه این پروژه هنوز خالی است</h2>
                <p className="mt-2 text-sm text-slate-500">اولین تصمیم، قانون یا نکته مهم پروژه را ثبت کنید.</p>
                <Button type="button" className="mt-5" onClick={() => setIsCreateOpen(true)}>افزودن اولین مورد</Button>
              </div>
            ) : filteredMemories.length === 0 ? (
              <div className="rounded-2xl border border-slate-200 bg-white px-6 py-10 text-center text-sm text-slate-500">
                موردی با فیلترهای فعلی پیدا نشد.
                <button type="button" className="mr-2 font-semibold text-teal-700 underline underline-offset-4" onClick={() => { setQuery(""); setCategory("all"); setVerification("all"); }}>پاک کردن فیلترها</button>
              </div>
            ) : (
              <div className="grid items-start gap-4 lg:grid-cols-2">
                {filteredMemories.map((memory) => (
                  <MemoryCard key={memory.id} memory={memory} mutationKey={mutationKey} onEdit={setEditingMemory} onDelete={setDeletingMemory} onToggleVerification={(item) => updateMemory(item.id, { is_verified: !item.is_verified }).then(() => undefined)} />
                ))}
              </div>
            )}
          </section>
        </>
      )}

      <Modal isOpen={isCreateOpen} onClose={() => { if (!mutationKey) setIsCreateOpen(false); }} title="افزودن به حافظه پروژه">
        <MemoryForm submitLabel="ثبت در حافظه" isSubmitting={mutationKey === "create"} onCancel={() => setIsCreateOpen(false)} onSubmit={handleCreate} />
      </Modal>

      <Modal isOpen={Boolean(editingMemory)} onClose={() => { if (!mutationKey) setEditingMemory(null); }} title="ویرایش حافظه">
        {editingMemory && (
          <MemoryForm key={editingMemory.id} initialValue={{ fact_text: editingMemory.fact_text, category: editingMemory.category }} submitLabel="ذخیره تغییرات" isSubmitting={mutationKey === `update:${editingMemory.id}`} onCancel={() => setEditingMemory(null)} onSubmit={handleEdit} />
        )}
      </Modal>

      <Modal isOpen={Boolean(deletingMemory)} onClose={() => { if (!mutationKey) setDeletingMemory(null); }} title="حذف از حافظه پروژه">
        {deletingMemory && (
          <div>
            <p className="text-sm leading-7 text-gray-600">این مورد برای همیشه از حافظه پروژه حذف می‌شود و دستیار دیگر نمی‌تواند به آن ارجاع دهد.</p>
            <div className="mt-3 rounded-xl bg-slate-50 p-3 text-sm leading-6 text-slate-700"><span className={`ml-2 inline-block h-2 w-2 rounded-full ${CATEGORY_META[deletingMemory.category].dot}`} />{deletingMemory.fact_text}</div>
            <div className="mt-5 flex flex-row-reverse gap-2 border-t border-gray-100 pt-4">
              <Button type="button" variant="danger" isLoading={mutationKey === `delete:${deletingMemory.id}`} onClick={() => void handleDelete().catch(() => {})}>حذف قطعی</Button>
              <Button type="button" variant="ghost" disabled={Boolean(mutationKey)} onClick={() => setDeletingMemory(null)}>انصراف</Button>
            </div>
          </div>
        )}
      </Modal>
    </main>
  );
}
