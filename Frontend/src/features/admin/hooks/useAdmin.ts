import { useCallback, useEffect, useState } from "react";

import { Document } from "@/features/documents/types";
import { friendlyErrorMessage } from "@/shared/lib/errorMessages";

import { adminApi } from "../api/adminApi";
import { Team, UserWithTeams } from "../types";

export function useAdmin() {
  const [users, setUsers] = useState<UserWithTeams[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    try {
      const [usersData, teamsData, documentsData] = await Promise.all([
        adminApi.listUsers(),
        adminApi.listTeams(),
        adminApi.listAllDocuments(),
      ]);
      setUsers(usersData);
      setTeams(teamsData);
      setDocuments(documentsData);
      setError(null);
    } catch (err) {
      setError(friendlyErrorMessage(err, "دریافت اطلاعات پنل مدیریت ناموفق بود."));
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([adminApi.listUsers(), adminApi.listTeams(), adminApi.listAllDocuments()])
      .then(([usersData, teamsData, documentsData]) => {
        if (cancelled) return;
        setUsers(usersData);
        setTeams(teamsData);
        setDocuments(documentsData);
        setError(null);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(friendlyErrorMessage(err, "دریافت اطلاعات پنل مدیریت ناموفق بود."));
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const createTeam = useCallback(
    async (name: string) => {
      setIsMutating(true);
      setActionError(null);
      try {
        await adminApi.createTeam(name);
        await refresh(false);
      } catch (err) {
        setActionError(friendlyErrorMessage(err, "ایجاد تیم ناموفق بود."));
        throw err;
      } finally {
        setIsMutating(false);
      }
    },
    [refresh]
  );

  const assignUserToTeam = useCallback(
    async (userId: string, teamId: string) => {
      setIsMutating(true);
      setActionError(null);
      try {
        await adminApi.assignUserToTeam(userId, teamId);
        await refresh(false);
      } catch (err) {
        setActionError(friendlyErrorMessage(err, "افزودن کاربر به تیم ناموفق بود."));
        throw err;
      } finally {
        setIsMutating(false);
      }
    },
    [refresh]
  );

  return {
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
  };
}
