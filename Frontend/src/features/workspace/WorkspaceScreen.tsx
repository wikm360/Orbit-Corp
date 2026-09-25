"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { loadWorkspace, workspaceApi, WorkspaceOverview } from "@/shared/lib/workspaceApi";
import { ProjectMembership, TeamMembership } from "@/shared/types";

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
      const data = await loadWorkspace(user);
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
    await mutate(() => workspaceApi.addTeamMember(teamId, newTeamMemberId.trim(), "member"));
    setNewTeamMemberId("");
  }

  async function addProjectMember(event: FormEvent) {
    event.preventDefault();
    if (!newProjectMemberId || !activeProjectId) return;
    await mutate(() => workspaceApi.addProjectMember(activeProjectId, newProjectMemberId));
    setNewProjectMemberId("");
  }

  return <main className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6 lg:p-8">
    <div className="page-heading rounded-2xl border border-slate-200 bg-white p-6"><h1 className="text-2xl font-bold text-gray-900">فضای کاری</h1><p className="mt-1 text-sm text-gray-500">تیم‌ها، پروژه‌ها و اعضای هر پروژه</p></div>
    {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {!overview && !error && <p className="text-sm text-gray-500">در حال دریافت اطلاعات...</p>}
    {overview && overview.teams.length === 0 && <p className="rounded-xl bg-white p-4 text-sm text-gray-500">هنوز عضو تیمی نیستید.</p>}
    {overview && overview.teams.length > 0 && <>
      <section className="rounded-2xl border border-gray-200 bg-white p-5">
        <label htmlFor="workspace-team" className="mb-2 block text-sm font-medium">تیم</label>
        <select id="workspace-team" value={teamId} onChange={(event) => setTeamId(event.target.value)} className="w-full max-w-sm rounded-lg border border-gray-200 p-2 text-sm">{overview.teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}</select>
        {selectedTeam?.description && <p className="mt-2 text-sm text-gray-500">{selectedTeam.description}</p>}
        <h2 className="mt-5 font-semibold">اعضای تیم</h2>
        <div className="mt-2 space-y-2">{visibleTeamMembers.map((membership) => <div key={membership.user.id} className="flex flex-wrap items-center gap-2 text-sm"><span className="flex-1 break-all">{membership.user.full_name || membership.user.email} — {membership.role === "leader" ? "سرپرست" : "عضو"}</span>{canManage && membership.role === "member" && <Button type="button" variant="ghost" size="sm" disabled={isBusy} onClick={() => void mutate(() => workspaceApi.removeTeamMember(teamId, membership.user.id))}>حذف</Button>}</div>)}</div>
        {canManage && <form onSubmit={addTeamMember} className="mt-4 flex flex-wrap gap-2"><Input aria-label="شناسه کاربر" placeholder="شناسه کاربر جدید" value={newTeamMemberId} onChange={(event) => setNewTeamMemberId(event.target.value)} /><Button type="submit" disabled={isBusy || !newTeamMemberId.trim()}>افزودن عضو</Button></form>}
      </section>
      <section className="rounded-2xl border border-gray-200 bg-white p-5">
        <h2 className="mb-3 font-semibold">پروژه‌های تیم</h2>
        {canManage && <form onSubmit={createProject} className="mb-4 flex flex-wrap gap-2"><Input aria-label="نام پروژه جدید" placeholder="نام پروژه جدید" value={newProjectName} onChange={(event) => setNewProjectName(event.target.value)} /><Button type="submit" disabled={isBusy || !newProjectName.trim()}>ایجاد پروژه</Button></form>}
        {teamProjects.length === 0 ? <p className="text-sm text-gray-500">پروژه‌ای برای این تیم در دسترس نیست.</p> : <>
          <select aria-label="پروژه" value={activeProjectId} onChange={(event) => setProjectId(event.target.value)} className="w-full max-w-sm rounded-lg border border-gray-200 p-2 text-sm">{teamProjects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select>
          {selectedProject?.description && <p className="mt-2 text-sm text-gray-500">{selectedProject.description}</p>}
          <h3 className="mt-5 font-medium">اعضای پروژه</h3>
          <div className="mt-2 space-y-2">{visibleProjectMembers.map((membership) => <div key={membership.user.id} className="flex flex-wrap items-center gap-2 text-sm"><span className="flex-1 break-all">{membership.user.full_name || membership.user.email}</span>{canManage && <Button type="button" variant="ghost" size="sm" disabled={isBusy} onClick={() => void mutate(() => workspaceApi.removeProjectMember(activeProjectId, membership.user.id))}>حذف</Button>}</div>)}</div>
          {canManage && <form onSubmit={addProjectMember} className="mt-4 flex flex-wrap gap-2"><select aria-label="عضو جدید پروژه" value={newProjectMemberId} onChange={(event) => setNewProjectMemberId(event.target.value)} className="rounded-lg border border-gray-200 p-2 text-sm"><option value="">انتخاب عضو تیم</option>{visibleTeamMembers.filter((member) => !visibleProjectMembers.some((projectMember) => projectMember.user.id === member.user.id)).map((member) => <option key={member.user.id} value={member.user.id}>{member.user.full_name || member.user.email}</option>)}</select><Button type="submit" disabled={isBusy || !newProjectMemberId}>افزودن به پروژه</Button></form>}
        </>}
      </section>
    </>}
  </main>;
}
