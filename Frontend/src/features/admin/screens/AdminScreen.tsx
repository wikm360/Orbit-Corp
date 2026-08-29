"use client";

import { FormEvent, useState } from "react";

import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";

import { DocumentAdminTable } from "../components/DocumentAdminTable";
import { UserTable } from "../components/UserTable";
import { useAdmin } from "../hooks/useAdmin";

export function AdminScreen() {
  const { users, teams, documents, isLoading, createTeam, assignUserToTeam } = useAdmin();
  const [newTeamName, setNewTeamName] = useState("");

  async function handleCreateTeam(event: FormEvent) {
    event.preventDefault();
    if (!newTeamName.trim()) return;
    await createTeam(newTeamName.trim());
    setNewTeamName("");
  }

  if (isLoading) {
    return <p className="p-6 text-sm text-gray-400">در حال بارگذاری...</p>;
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <h1 className="text-xl font-semibold text-gray-900">پنل ادمین</h1>

      <section className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">تیم‌ها</h2>
        <form onSubmit={handleCreateTeam} className="mb-3 flex gap-2">
          <Input
            placeholder="نام تیم جدید"
            value={newTeamName}
            onChange={(e) => setNewTeamName(e.target.value)}
          />
          <Button type="submit">ایجاد تیم</Button>
        </form>
        <div className="flex flex-wrap gap-2">
          {teams.map((team) => (
            <span key={team.id} className="rounded-full bg-gray-100 px-3 py-1 text-xs">
              {team.name}
            </span>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">کاربران</h2>
        <UserTable users={users} teams={teams} onAssign={assignUserToTeam} />
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">همه اسناد</h2>
        <DocumentAdminTable documents={documents} />
      </section>
    </div>
  );
}
