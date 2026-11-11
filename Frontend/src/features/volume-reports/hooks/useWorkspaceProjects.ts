"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuthStore } from "@/features/auth/hooks/useAuthStore";
import { runSoon } from "../lib/defer";
import { hasProjectPermission, loadWorkspace } from "@/shared/lib/workspaceApi";
import type { Project } from "@/shared/types";

/**
 * Projects the user can pick from. Admins who are not project members still get every project (via the teams endpoints,
 * `loadWorkspace`), not just `/projects/mine`. `canEditSettings` mirrors the backend rule: admin or leader of any team.
 */
export function useWorkspaceProjects() {
  const user = useAuthStore((s) => s.user);
  const [projects, setProjects] = useState<Project[]>([]);
  const [managedTeamIds, setManagedTeamIds] = useState<Set<string>>(new Set());
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
      setManagedTeamIds(overview.managedTeamIds);
      setCanEditSettings(user.role === "admin" || user.role === "super_admin" || overview.managedTeamIds.size > 0);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [user]);

  const canManageDocumentsFor = useCallback((projectId: string): boolean => {
    if (!user) return false;
    if (user.role === "admin" || user.role === "super_admin") return true;
    const project = projects.find((p) => p.id === projectId);
    if (!project) return false;
    return managedTeamIds.has(project.team_id) || hasProjectPermission(project, "documents");
  }, [user, projects, managedTeamIds]);

  useEffect(() => runSoon(() => void reload()), [reload]);
  return { projects, canEditSettings, canManageDocumentsFor, loading, error, reload };
}
