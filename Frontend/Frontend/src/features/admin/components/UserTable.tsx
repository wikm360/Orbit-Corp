import { useState } from "react";

import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";

import { Team, UserWithTeams } from "../types";

interface UserTableProps {
  users: UserWithTeams[];
  teams: Team[];
  onAssign: (userId: string, teamId: string) => void;
}

export function UserTable({ users, teams, onAssign }: UserTableProps) {
  const [selectedTeam, setSelectedTeam] = useState<Record<string, string>>({});

  return (
    <table className="w-full text-right text-sm">
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
            <tr key={user.id} className="border-b border-gray-100">
              <td className="py-2">{user.email}</td>
              <td className="py-2">
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
                      className="rounded-md border border-gray-300 px-2 py-1 text-xs"
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
                      onClick={() => {
                        const teamId = selectedTeam[user.id];
                        if (teamId) {
                          onAssign(user.id, teamId);
                          setSelectedTeam((prev) => ({ ...prev, [user.id]: "" }));
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
  );
}
