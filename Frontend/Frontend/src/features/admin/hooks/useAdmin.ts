import { useCallback, useEffect, useState } from "react";

import { Document } from "@/features/documents/types";

import { adminApi } from "../api/adminApi";
import { Team, UserWithTeams } from "../types";

export function useAdmin() {
  const [users, setUsers] = useState<UserWithTeams[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    const [usersData, teamsData, documentsData] = await Promise.all([
      adminApi.listUsers(),
      adminApi.listTeams(),
      adminApi.listAllDocuments(),
    ]);
    setUsers(usersData);
    setTeams(teamsData);
    setDocuments(documentsData);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const createTeam = useCallback(
    async (name: string) => {
      await adminApi.createTeam(name);
      await refresh();
    },
    [refresh]
  );

  const assignUserToTeam = useCallback(
    async (userId: string, teamId: string) => {
      await adminApi.assignUserToTeam(userId, teamId);
      await refresh();
    },
    [refresh]
  );

  return { users, teams, documents, isLoading, createTeam, assignUserToTeam };
}
