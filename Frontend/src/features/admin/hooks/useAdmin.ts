import { useCallback, useEffect, useState } from "react";
import { Document } from "@/features/documents/types";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";
import { Team, TeamMembership, User, UserRole } from "@/shared/types";
import { adminApi } from "../api/adminApi";

export function useAdmin() {
  const [users, setUsers] = useState<User[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [memberships, setMemberships] = useState<Record<string, TeamMembership[]>>({});
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const [usersData, teamsData, documentsData] = await Promise.all([
        adminApi.listUsers(), adminApi.listTeams(), adminApi.listAllDocuments(),
      ]);
      const memberLists = await Promise.all(teamsData.map((team) => adminApi.teamMembers(team.id)));
      setUsers(usersData);
      setTeams(teamsData);
      setDocuments(documentsData);
      setMemberships(Object.fromEntries(teamsData.map((team, index) => [team.id, memberLists[index] ?? []])));
      setError(null);
    } catch (err) {
      setError(friendlyErrorMessage(err, "دریافت اطلاعات پنل مدیریت ناموفق بود."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  const mutate = useCallback(async (action: () => Promise<unknown>) => {
    setIsMutating(true);
    setError(null);
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(friendlyErrorMessage(err, "عملیات ناموفق بود."));
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, [refresh]);

  return {
    users, teams, memberships, documents, isLoading, isMutating, error, refresh,
    createTeam: (name: string, description?: string) => mutate(() => adminApi.createTeam(name, description)),
    assignUserToTeam: (userId: string, teamId: string, role: "leader" | "member") => mutate(() => adminApi.assignUserToTeam(teamId, userId, role)),
    removeUserFromTeam: (userId: string, teamId: string) => mutate(() => adminApi.removeUserFromTeam(teamId, userId)),
    setUserRole: (userId: string, role: UserRole) => mutate(() => adminApi.setUserRole(userId, role)),
  };
}
