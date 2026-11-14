"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { loadWorkspace, workspaceApi, WorkspaceOverview } from "@/shared/lib/workspaceApi";
import { DirectoryUser, ProjectMembership, ProjectPermission, TeamMembership } from "@/shared/types";

const PERMISSION_OPTIONS: { key: ProjectPermission; label: string }[] = [
  { key: "documents", label: "مدیریت اسناد" },
  { key: "memory", label: "مدیریت حافظه" },
];

export function WorkspaceScreen() {
  const user = useAuthStore((state) => state.user);
  const [overview, setOverview] = useState<WorkspaceOverview | null>(null);
  const [teamId, setTeamId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [teamMembers, setTeamMembers] = useState<TeamMembership[]>([]);
  const [projectMembers, setProjectMembers] = useState<ProjectMembership[]>([]);
  const [loadedTeamId, setLoadedTeamId] = useState("");
  const [loadedProjectId, setLoadedProjectId] = useState("");
  const [newProjectName, setNewProjectName] = useState("");
  const [newTeamMemberId, setNewTeamMemberId] = useState("");
  const [newProjectMemberId, setNewProjectMemberId] = useState("");
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const [newTeamName, setNewTeamName] = useState("");
  const [newMemberRole, setNewMemberRole] = useState<"leader" | "member">("member");
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedTeam = overview?.teams.find((team) => team.id === teamId);
  const teamProjects = overview?.projects.filter((project) => project.team_id === teamId) ?? [];
  const activeProjectId = teamProjects.some((project) => project.id === projectId) ? projectId : teamProjects[0]?.id ?? "";
  const selectedProject = teamProjects.find((project) => project.id === activeProjectId);
  const visibleTeamMembers = loadedTeamId === teamId ? teamMembers : [];
  const visibleProjectMembers = loadedProjectId === activeProjectId ? projectMembers : [];
  const canManage = overview?.managedTeamIds.has(teamId) ?? false;

  const refreshOverview = useCallback(async () => {
    if (!user) return;
    try {
      const data = await loadWorkspace(user, { manageAll: true });
      setOverview(data);
      setTeamId((current) => data.teams.some((team) => team.id === current) ? current : data.teams[0]?.id ?? "");
      setError(null);
    } catch (err) { setError(friendlyErrorMessage(err, "دریافت فضای کاری ناموفق بود.")); }
  }, [user]);

  useEffect(() => {
    const timer = window.setTimeout(() => void refreshOverview(), 0);
    return () => window.clearTimeout(timer);
  }, [refreshOverview]);
  useEffect(() => {
    if (!user?.workspace_access) return;
    workspaceApi.userDirectory().then(setDirectory).catch((err) => setError(friendlyErrorMessage(err)));
  }, [user?.workspace_access]);
  useEffect(() => {
    if (!teamId) return;
    let cancelled = false;
    workspaceApi.teamMembers(teamId).then((members) => { if (!cancelled) { setTeamMembers(members); setLoadedTeamId(teamId); } }).catch((err) => { if (!cancelled) setError(friendlyErrorMessage(err)); });
    return () => { cancelled = true; };
  }, [teamId, overview]);
  useEffect(() => {
    if (!activeProjectId) return;
    let cancelled = false;
    workspaceApi.projectMembers(activeProjectId).then((members) => { if (!cancelled) { setProjectMembers(members); setLoadedProjectId(activeProjectId); } }).catch((err) => { if (!cancelled) setError(friendlyErrorMessage(err)); });
    return () => { cancelled = true; };
  }, [activeProjectId, overview]);

  async function mutate(action: () => Promise<unknown>) {
    setIsBusy(true); setError(null);
    try { await action(); await refreshOverview(); }
    catch (err) { setError(friendlyErrorMessage(err, "عملیات ناموفق بود.")); }
    finally { setIsBusy(false); }
  }

  async function createProject(event: FormEvent) {
    event.preventDefault();
    if (!newProjectName.trim() || !teamId) return;
    await mutate(() => workspaceApi.createProject(teamId, newProjectName.trim()));
    setNewProjectName("");
  }

  async function addTeamMember(event: FormEvent) {
    event.preventDefault();
    if (!newTeamMemberId.trim() || !teamId) return;
    await mutate(() => workspaceApi.addTeamMember(teamId, newTeamMemberId.trim(), newMemberRole));
    setNewTeamMemberId("");
  }

  async function createTeam(event: FormEvent) {
    event.preventDefault();
    if (!newTeamName.trim()) return;
    await mutate(() => workspaceApi.createTeam(newTeamName.trim()));
    setNewTeamName("");
  }

  async function togglePermission(userId: string, current: ProjectPermission[], permission: ProjectPermission, enabled: boolean) {
    const next = enabled ? [...current, permission] : current.filter((item) => item !== permission);
    await mutate(() => workspaceApi.setMemberPermissions(activeProjectId, userId, next));
  }

  async function addProjectMember(event: FormEvent) {
    event.preventDefault();
    if (!newProjectMemberId || !activeProjectId) return;
    await mutate(() => workspaceApi.addProjectMember(activeProjectId, newProjectMemberId));
    setNewProjectMemberId("");
  }

  if (user && !user.workspace_access) return <main className="mx-auto max-w-5xl p-6"><p role="alert" className="rounded-xl bg-white p-4 text-sm text-gray-600">دسترسی به مدیریت فضای کاری برای شما فعال نیست.</p></main>;

  return <main className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6 lg:p-8">
    <div className="page-heading rounded-2xl border border-slate-200 bg-white p-6"><h1 className="text-2xl font-bold text-gray-900">فضای کاری</h1><p className="mt-1 text-sm text-gray-500">تیم‌ها، پروژه‌ها و اعضای هر پروژه</p></div>
    {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {!overview && !error && <p className="text-sm text-gray-500">در حال دریافت اطلاعات...</p>}
    <section className="rounded-2xl border border-gray-200 bg-white p-5">
      <h2 className="mb-3 font-semibold">تیم جدید</h2>
      <form onSubmit={createTeam} className="flex flex-wrap gap-2"><Input aria-label="نام تیم جدید" placeholder="نام تیم جدید" maxLength={80} value={newTeamName} onChange={(event) => setNewTeamName(event.target.value)} /><Button type="submit" disabled={isBusy || !newTeamName.trim()}>ایجاد تیم</Button></form>
    </section>
    {overview && overview.teams.length === 0 && <p className="rounded-xl bg-white p-4 text-sm text-gray-500">هنوز تیمی ساخته نشده است.</p>}
    {overview && overview.teams.length > 0 && <>
      <section className="rounded-2xl border border-gray-200 bg-white p-5">
        <label htmlFor="workspace-team" className="mb-2 block text-sm font-medium">تیم</label>
        <Select id="workspace-team" value={teamId} onValueChange={setTeamId} options={overview.teams.map((team) => ({ value: team.id, label: team.name, description: team.description }))} className="max-w-sm" />
        {selectedTeam?.description && <p className="mt-2 text-sm text-gray-500">{selectedTeam.description}</p>}
        <h2 className="mt-5 font-semibold">اعضای تیم</h2>
        <div className="mt-2 space-y-2">{visibleTeamMembers.map((membership) => <div key={membership.user.id} className="flex flex-wrap items-center gap-2 text-sm"><span className="flex-1 break-all">{membership.user.full_name || membership.user.email} — {membership.role === "leader" ? "سرپرست" : "عضو"}</span>{canManage && (membership.role === "member" || user?.workspace_access) && <Button type="button" variant="ghost" size="sm" disabled={isBusy} onClick={() => void mutate(() => workspaceApi.removeTeamMember(teamId, membership.user.id))}>حذف</Button>}</div>)}</div>
        {canManage && <form onSubmit={addTeamMember} className="mt-4 flex flex-wrap gap-2"><Select aria-label="کاربر جدید تیم" value={newTeamMemberId} onValueChange={setNewTeamMemberId} options={directory.filter((candidate) => !visibleTeamMembers.some((member) => member.user.id === candidate.id)).map((candidate) => ({ value: candidate.id, label: candidate.full_name || candidate.email, description: candidate.full_name ? candidate.email : undefined }))} placeholder="انتخاب کاربر" className="min-w-56 flex-1 sm:flex-none" /><Select aria-label="نقش در تیم" value={newMemberRole} onValueChange={(next) => setNewMemberRole(next as "leader" | "member")} options={[{ value: "member", label: "عضو" }, { value: "leader", label: "سرپرست" }]} className="w-36" /><Button type="submit" disabled={isBusy || !newTeamMemberId.trim()}>افزودن عضو</Button></form>}
      </section>
      <section className="rounded-2xl border border-gray-200 bg-white p-5">
        <h2 className="mb-3 font-semibold">پروژه‌های تیم</h2>
        {canManage && <form onSubmit={createProject} className="mb-4 flex flex-wrap gap-2"><Input aria-label="نام پروژه جدید" placeholder="نام پروژه جدید" value={newProjectName} onChange={(event) => setNewProjectName(event.target.value)} /><Button type="submit" disabled={isBusy || !newProjectName.trim()}>ایجاد پروژه</Button></form>}
        {teamProjects.length === 0 ? <p className="text-sm text-gray-500">پروژه‌ای برای این تیم در دسترس نیست.</p> : <>
          <Select aria-label="پروژه" value={activeProjectId} onValueChange={setProjectId} options={teamProjects.map((project) => ({ value: project.id, label: project.name, description: project.description }))} className="max-w-sm" />
          {selectedProject?.description && <p className="mt-2 text-sm text-gray-500">{selectedProject.description}</p>}
          <h3 className="mt-5 font-medium">اعضای پروژه</h3>
          <div className="mt-2 space-y-2">{visibleProjectMembers.map((membership) => {
            const isLeader = visibleTeamMembers.some((member) => member.user.id === membership.user.id && member.role === "leader");
            const granted = membership.permissions ?? [];
            return <div key={membership.user.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <span className="min-w-40 flex-1 break-all">{membership.user.full_name || membership.user.email}</span>
              {isLeader ? <span className="text-xs text-gray-500">سرپرست تیم — همه‌ی دسترسی‌ها</span>
                : <span className="flex flex-wrap items-center gap-3">{PERMISSION_OPTIONS.map((option) => canManage
                  ? <label key={option.key} className="flex items-center gap-1.5 text-xs text-gray-700"><input type="checkbox" className="accent-teal-600" disabled={isBusy} checked={granted.includes(option.key)} onChange={(event) => void togglePermission(membership.user.id, granted, option.key, event.target.checked)} />{option.label}</label>
                  : granted.includes(option.key) && <span key={option.key} className="rounded-full bg-teal-50 px-2 py-0.5 text-xs text-teal-800">{option.label}</span>)}</span>}
              {canManage && <Button type="button" variant="ghost" size="sm" disabled={isBusy} onClick={() => void mutate(() => workspaceApi.removeProjectMember(activeProjectId, membership.user.id))}>حذف</Button>}
            </div>;
          })}</div>
          {canManage && <form onSubmit={addProjectMember} className="mt-4 flex flex-wrap gap-2"><Select aria-label="عضو جدید پروژه" value={newProjectMemberId} onValueChange={setNewProjectMemberId} options={visibleTeamMembers.filter((member) => !visibleProjectMembers.some((projectMember) => projectMember.user.id === member.user.id)).map((member) => ({ value: member.user.id, label: member.user.full_name || member.user.email, description: member.role === "leader" ? "سرپرست تیم" : "عضو تیم" }))} placeholder="انتخاب عضو تیم" className="min-w-56 flex-1 sm:flex-none" /><Button type="submit" disabled={isBusy || !newProjectMemberId}>افزودن به پروژه</Button></form>}
        </>}
      </section>
    </>}
  </main>;
}
