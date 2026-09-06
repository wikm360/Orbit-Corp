"use client";

import { FormEvent, useState } from "react";

import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";

import { DocumentAdminTable } from "../components/DocumentAdminTable";
import { UserTable } from "../components/UserTable";
import { useAdmin } from "../hooks/useAdmin";

export function AdminScreen() {
  const {
    users,
    teams,
    documents,
    isLoading,
    isMutating,
    error,
    actionError,
    refresh,
    createTeam,
    assignUserToTeam,
  } = useAdmin();
  const [newTeamName, setNewTeamName] = useState("");

  async function handleCreateTeam(event: FormEvent) {
    event.preventDefault();
    if (!newTeamName.trim()) return;
    try {
      await createTeam(newTeamName.trim());
      setNewTeamName("");
    } catch {
      // The hook renders the localized action error.
    }
  }

  if (isLoading) {
    return (
      <main className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6 lg:p-8" aria-label="در حال بارگذاری پنل مدیریت">
        {[0, 1, 2].map((item) => <div key={item} className="h-32 animate-pulse rounded-2xl bg-white" />)}
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6 lg:p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">پنل مدیریت</h1>
          <p className="mt-1 text-sm leading-6 text-gray-500">کاربران، تیم‌ها و اسناد سازمان را از اینجا مدیریت کنید.</p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={() => refresh()} disabled={isMutating}>
          به‌روزرسانی
        </Button>
      </div>

      {(error || actionError) && (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
          <span>{actionError ?? error}</span>
          {error && <Button type="button" variant="ghost" size="sm" onClick={() => refresh()}>تلاش دوباره</Button>}
        </div>
      )}

      <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">تیم‌ها</h2>
          <span className="text-xs text-gray-400">{teams.length.toLocaleString("fa-IR")} تیم</span>
        </div>
        <form onSubmit={handleCreateTeam} className="mb-4 flex flex-col gap-2 sm:flex-row">
          <Input
            aria-label="نام تیم جدید"
            placeholder="نام تیم جدید"
            maxLength={80}
            value={newTeamName}
            onChange={(e) => setNewTeamName(e.target.value)}
            className="sm:min-w-72"
          />
          <Button type="submit" isLoading={isMutating} disabled={!newTeamName.trim()}>ایجاد تیم</Button>
        </form>
        <div className="flex flex-wrap gap-2">
          {teams.map((team) => (
            <span key={team.id} className="rounded-full bg-gray-100 px-3 py-1 text-xs">
              {team.name}
            </span>
          ))}
          {teams.length === 0 && <span className="text-sm text-gray-400">هنوز تیمی ساخته نشده است.</span>}
        </div>
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">کاربران</h2>
          <span className="text-xs text-gray-400">{users.length.toLocaleString("fa-IR")} کاربر</span>
        </div>
        <UserTable users={users} teams={teams} onAssign={assignUserToTeam} isBusy={isMutating} />
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">همه اسناد</h2>
          <span className="text-xs text-gray-400">{documents.length.toLocaleString("fa-IR")} سند</span>
        </div>
        <DocumentAdminTable documents={documents} />
      </section>
    </main>
  );
}
