"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { runSoon } from "../lib/defer";
import { loadWorkspace } from "@/shared/lib/workspaceApi";
import type { Project } from "@/shared/types";

/**
 * Projects the user can pick from. Admins who are not project members still get every project (via the teams endpoints,
 * `loadWorkspace`), not just `/projects/mine`. `canEditSettings` mirrors the backend rule: admin or leader of any team.
 */
export function useWorkspaceProjects() {
  const user = useAuthStore((s) => s.user);
  const [projects, setProjects] = useState<Project[]>([]);
  const [canEditSettings, setCanEditSettings] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const reload = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const overview = await loadWorkspace(user);
      setProjects(overview.projects);
      setCanEditSettings(user.role === "admin" || user.role === "super_admin" || overview.managedTeamIds.size > 0);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => runSoon(() => void reload()), [reload]);
  return { projects, canEditSettings, loading, error, reload };
}
