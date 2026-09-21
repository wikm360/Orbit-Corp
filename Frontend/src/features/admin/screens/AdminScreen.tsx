"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { UserRole } from "@/shared/types";
import { DocumentAdminTable } from "../components/DocumentAdminTable";
import { useAdmin } from "../hooks/useAdmin";

const ROLE_LABEL: Record<UserRole, string> = { super_admin: "مدیر ارشد", admin: "مدیر", user: "کاربر" };

export function AdminScreen() {
  const currentUser = useAuthStore((state) => state.user);
  const { users, teams, memberships, documents, isLoading, isMutating, error, refresh, createTeam, assignUserToTeam, removeUserFromTeam, setUserRole } = useAdmin();
  const [newTeamName, setNewTeamName] = useState("");
  const [selectedUser, setSelectedUser] = useState<Record<string, string>>({});
  const [selectedRole, setSelectedRole] = useState<Record<string, "leader" | "member">>({});

  async function handleCreateTeam(event: FormEvent) {
    event.preventDefault();
    if (!newTeamName.trim()) return;
    try { await createTeam(newTeamName.trim()); setNewTeamName(""); } catch { /* Error is shown in the panel. */ }
  }

  if (isLoading) return <main className="mx-auto max-w-6xl p-6 text-sm text-gray-500">در حال بارگذاری پنل مدیریت...</main>;

  return <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6 lg:p-8">
    <div className="flex items-center justify-between gap-3">
      <div><h1 className="text-2xl font-bold text-gray-900">پنل مدیریت</h1><p className="mt-1 text-sm text-gray-500">کاربران، تیم‌ها و اسناد سازمان</p></div>
      <Button type="button" variant="ghost" size="sm" onClick={() => void refresh()} disabled={isMutating}>به‌روزرسانی</Button>
    </div>
    {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <section className="rounded-2xl border border-gray-200 bg-white p-5">
      <h2 className="mb-4 font-semibold text-gray-800">تیم‌ها</h2>
      <form onSubmit={handleCreateTeam} className="mb-5 flex flex-wrap gap-2">
        <Input aria-label="نام تیم جدید" placeholder="نام تیم جدید" maxLength={80} value={newTeamName} onChange={(event) => setNewTeamName(event.target.value)} />
        <Button type="submit" isLoading={isMutating} disabled={!newTeamName.trim()}>ایجاد تیم</Button>
      </form>
      <div className="space-y-5">{teams.map((team) => {
        const currentMembers = memberships[team.id] ?? [];
        const availableUsers = users.filter((user) => !currentMembers.some((member) => member.user.id === user.id));
        return <div key={team.id} className="rounded-xl border border-gray-100 p-4">
          <h3 className="font-medium text-gray-900">{team.name}</h3>
          <div className="mt-3 space-y-2">{currentMembers.map((member) => <div key={member.user.id} className="flex flex-wrap items-center gap-2 text-sm">
            <span className="min-w-0 flex-1 break-all">{member.user.full_name || member.user.email}</span>
            <select aria-label={`نقش ${member.user.email} در ${team.name}`} value={member.role} disabled={isMutating} onChange={(event) => void assignUserToTeam(member.user.id, team.id, event.target.value as "leader" | "member").catch(() => {})} className="rounded-lg border border-gray-200 p-1.5 text-xs"><option value="member">عضو</option><option value="leader">سرپرست</option></select>
            <Button type="button" variant="ghost" size="sm" disabled={isMutating} onClick={() => void removeUserFromTeam(member.user.id, team.id).catch(() => {})}>حذف عضویت</Button>
          </div>)}</div>
          {availableUsers.length > 0 && <div className="mt-4 flex flex-wrap gap-2">
            <select aria-label={`کاربر برای تیم ${team.name}`} value={selectedUser[team.id] ?? ""} onChange={(event) => setSelectedUser((current) => ({ ...current, [team.id]: event.target.value }))} className="rounded-lg border border-gray-200 p-2 text-sm">
              <option value="">انتخاب کاربر</option>{availableUsers.map((user) => <option key={user.id} value={user.id}>{user.full_name || user.email}</option>)}
            </select>
            <select aria-label={`نقش در تیم ${team.name}`} value={selectedRole[team.id] ?? "member"} onChange={(event) => setSelectedRole((current) => ({ ...current, [team.id]: event.target.value as "leader" | "member" }))} className="rounded-lg border border-gray-200 p-2 text-sm">
              <option value="member">عضو</option><option value="leader">سرپرست</option>
            </select>
            <Button type="button" size="sm" disabled={isMutating || !selectedUser[team.id]} onClick={() => void assignUserToTeam(selectedUser[team.id] ?? "", team.id, selectedRole[team.id] ?? "member").then(() => setSelectedUser((current) => ({ ...current, [team.id]: "" }))).catch(() => {})}>افزودن</Button>
          </div>}
        </div>;
      })}</div>
    </section>
    <section className="rounded-2xl border border-gray-200 bg-white p-5">
      <h2 className="mb-4 font-semibold text-gray-800">کاربران</h2>
      <div className="space-y-3">{users.map((user) => <div key={user.id} className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 pb-3 text-sm">
        <span className="break-all">{user.full_name || user.email} — {ROLE_LABEL[user.role]}</span>
        {currentUser?.role === "super_admin" && <select aria-label={`نقش سازمانی ${user.email}`} value={user.role} disabled={isMutating || user.id === currentUser.id} onChange={(event) => void setUserRole(user.id, event.target.value as UserRole).catch(() => {})} className="rounded-lg border border-gray-200 p-2 text-sm">
          <option value="user">کاربر</option><option value="admin">مدیر</option><option value="super_admin">مدیر ارشد</option>
        </select>}
      </div>)}</div>
    </section>
    <section className="rounded-2xl border border-gray-200 bg-white p-5">
      <h2 className="mb-4 font-semibold text-gray-800">همه اسناد</h2>
      <DocumentAdminTable documents={documents} />
    </section>
  </main>;
}
