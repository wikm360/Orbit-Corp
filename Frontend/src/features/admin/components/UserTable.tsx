import { useState } from "react";

import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";

import { Team, UserWithTeams } from "../types";

interface UserTableProps {
  users: UserWithTeams[];
  teams: Team[];
  onAssign: (userId: string, teamId: string) => Promise<void>;
  isBusy?: boolean;
}

export function UserTable({ users, teams, onAssign, isBusy = false }: UserTableProps) {
  const [selectedTeam, setSelectedTeam] = useState<Record<string, string>>({});
  const [assigningUserId, setAssigningUserId] = useState<string | null>(null);

  if (users.length === 0) {
    return <p className="text-sm text-gray-400">کاربری برای نمایش وجود ندارد.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-right text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-gray-500">
          <th className="py-2 font-medium">ایمیل</th>
          <th className="py-2 font-medium">نقش</th>
          <th className="py-2 font-medium">تیم‌های فعلی</th>
          <th className="py-2 font-medium">افزودن به تیم</th>
        </tr>
      </thead>
      <tbody>
        {users.map((user) => {
          const assignedTeamIds = new Set(user.teams.map((t) => t.id));
          const availableTeams = teams.filter((t) => !assignedTeamIds.has(t.id));

          return (
            <tr key={user.id} className="border-b border-gray-100 last:border-0">
              <td dir="ltr" className="py-3 pe-3 text-left font-medium text-gray-800">{user.email}</td>
              <td className="py-3">
                <Badge tone={user.role === "admin" ? "yellow" : "gray"}>{user.role}</Badge>
              </td>
              <td className="py-2">
                {user.teams.length === 0 ? (
                  <span className="text-xs text-gray-400">بدون تیم</span>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {user.teams.map((team) => (
                      <Badge key={team.id} tone="green">
                        {team.name}
                      </Badge>
                    ))}
                  </div>
                )}
              </td>
              <td className="py-2">
                {availableTeams.length === 0 ? (
                  <span className="text-xs text-gray-400">عضو همه تیم‌هاست</span>
                ) : (
                  <div className="flex items-center gap-2">
                    <select
                      aria-label={`انتخاب تیم برای ${user.email}`}
                      className="rounded-lg border border-gray-200 bg-white px-2 py-2 text-xs outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
                      disabled={isBusy}
                      value={selectedTeam[user.id] ?? ""}
                      onChange={(e) =>
                        setSelectedTeam((prev) => ({ ...prev, [user.id]: e.target.value }))
                      }
                    >
                      <option value="" disabled>
                        انتخاب تیم
                      </option>
                      {availableTeams.map((team) => (
                        <option key={team.id} value={team.id}>
                          {team.name}
                        </option>
                      ))}
                    </select>
                    <Button
                      variant="secondary"
                      size="sm"
                      isLoading={assigningUserId === user.id}
                      disabled={isBusy || !selectedTeam[user.id]}
                      onClick={async () => {
                        const teamId = selectedTeam[user.id];
                        if (teamId) {
                          setAssigningUserId(user.id);
                          try {
                            await onAssign(user.id, teamId);
                            setSelectedTeam((prev) => ({ ...prev, [user.id]: "" }));
                          } catch {
                            // The parent renders the localized action error.
                          } finally {
                            setAssigningUserId(null);
                          }
                        }
                      }}
                    >
                      افزودن
                    </Button>
                  </div>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
      </table>
    </div>
  );
}
