import { apiRequest } from "./apiClient";
import type { Branding, CostSummary, DirectoryUser, ManagedUser, ModelPrice, Project, ProjectMembership, ProjectPermission, QuotaOverview, TokenUsageReport, UserQuota, Team, TeamMembership, User, UserRole } from "@/shared/types";

export const workspaceApi = {
  myTeams: () => apiRequest<Team[]>("/teams/mine"),
  allTeams: () => apiRequest<Team[]>("/teams"),
  createTeam: (name: string, description?: string) => apiRequest<Team>("/teams", { method: "POST", body: { name, description: description || null } }),
  teamMembers: (teamId: string) => apiRequest<TeamMembership[]>(`/teams/${teamId}/members`),
  addTeamMember: (teamId: string, userId: string, role: "leader" | "member") => apiRequest<void>(`/teams/${teamId}/members`, { method: "POST", body: { user_id: userId, role } }),
  removeTeamMember: (teamId: string, userId: string) => apiRequest<void>(`/teams/${teamId}/members/${userId}`, { method: "DELETE" }),
  teamProjects: (teamId: string) => apiRequest<Project[]>(`/teams/${teamId}/projects`),
  myProjects: () => apiRequest<Project[]>("/projects/mine"),
  createProject: (teamId: string, name: string, description?: string) => apiRequest<Project>(`/teams/${teamId}/projects`, { method: "POST", body: { name, description: description || null } }),
  projectMembers: (projectId: string) => apiRequest<ProjectMembership[]>(`/projects/${projectId}/members`),
  addProjectMember: (projectId: string, userId: string) => apiRequest<void>(`/projects/${projectId}/members`, { method: "POST", body: { user_id: userId } }),
  removeProjectMember: (projectId: string, userId: string) => apiRequest<void>(`/projects/${projectId}/members/${userId}`, { method: "DELETE" }),
  setMemberPermissions: (projectId: string, userId: string, permissions: ProjectPermission[]) => apiRequest<ProjectMembership>(`/projects/${projectId}/members/${userId}/permissions`, { method: "PUT", body: { permissions } }),
  setTokenLimit: (userId: string, limit: number | null) => apiRequest<User>(`/admin/users/${userId}/token-limit`, { method: "PUT", body: { limit } }),
  extendTokenLimit: (userId: string, add: number) => apiRequest<User>(`/admin/users/${userId}/token-limit/extend`, { method: "POST", body: { add } }),
  resetTokenUsage: (userId: string) => apiRequest<User>(`/admin/users/${userId}/token-limit/reset`, { method: "POST" }),
  tokenUsage: (userId: string) => apiRequest<TokenUsageReport>(`/admin/users/${userId}/token-usage`),
  quotaOverview: () => apiRequest<QuotaOverview>("/admin/quota"),
  setQuotaEnforced: (enforced: boolean) => apiRequest<QuotaOverview>("/admin/quota/enforced", { method: "PUT", body: { enforced } }),
  setQuotaPlan: (role: string, plan: { five_hour_usd: number; weekly_usd: number; monthly_usd: number }) => apiRequest<QuotaOverview>(`/admin/quota/plans/${role}`, { method: "PUT", body: plan }),
  setSetupPool: (body: { enabled?: boolean; budget_usd?: number }) => apiRequest<QuotaOverview>("/admin/quota/setup-pool", { method: "PUT", body }),
  setOrgCap: (monthlyCapUsd: number | null) => apiRequest<QuotaOverview>("/admin/quota/org-cap", { method: "PUT", body: { monthly_cap_usd: monthlyCapUsd } }),
  userQuota: (userId: string) => apiRequest<UserQuota>(`/admin/users/${userId}/quota`),
  setUserQuota: (userId: string, body: { five_hour_usd: number | null; weekly_usd: number | null; monthly_usd: number | null; unlimited: boolean }) => apiRequest<UserQuota>(`/admin/users/${userId}/quota`, { method: "PUT", body }),
  modelPrices: () => apiRequest<ModelPrice[]>("/admin/model-prices"),
  setModelPrice: (model: string, body: { input_per_m: number; output_per_m: number; per_page_usd: number | null }) => apiRequest<ModelPrice>(`/admin/model-prices/${model}`, { method: "PUT", body }),
  costSummary: (days = 30) => apiRequest<CostSummary>(`/admin/usage/cost-summary?days=${days}`),
  branding: () => apiRequest<Branding>("/branding"),
  updateBranding: (body: Partial<Record<string, string>>) => apiRequest<Branding>("/admin/branding", { method: "PUT", body }),
  uploadBrandLogo: (file: File) => { const formData = new FormData(); formData.append("file", file); return apiRequest<Branding>("/admin/branding/logo", { method: "POST", formData }); },
  deleteBrandLogo: () => apiRequest<Branding>("/admin/branding/logo", { method: "DELETE" }),
  setUserManagementAccess: (userId: string, enabled: boolean) => apiRequest<User>(`/admin/users/${userId}/user-management-access`, { method: "PUT", body: { enabled } }),
  managedUsers: () => apiRequest<ManagedUser[]>("/user-management/users"),
  createManagedUser: (body: { email: string; password: string; full_name: string }) => apiRequest<ManagedUser>("/user-management/users", { method: "POST", body }),
  updateManagedUser: (userId: string, body: { email?: string; full_name?: string }) => apiRequest<ManagedUser>(`/user-management/users/${userId}`, { method: "PATCH", body }),
  resetManagedUserPassword: (userId: string, password: string) => apiRequest<void>(`/user-management/users/${userId}/reset-password`, { method: "POST", body: { password } }),
  deleteManagedUser: (userId: string) => apiRequest<void>(`/user-management/users/${userId}`, { method: "DELETE" }),
  userDirectory: () => apiRequest<DirectoryUser[]>("/teams/directory/users"),
  setWorkspaceAccess: (userId: string, enabled: boolean) => apiRequest<User>(`/admin/users/${userId}/workspace-access`, { method: "PUT", body: { enabled } }),
  users: () => apiRequest<User[]>("/admin/users"),
  updateUserRole: (userId: string, role: UserRole) => apiRequest<User>(`/admin/users/${userId}/role`, { method: "PATCH", body: { role } }),
  setAccountingAccess: (userId: string, enabled: boolean) => apiRequest<User>(`/admin/users/${userId}/accounting-access`, { method: "PUT", body: { enabled } }),
};

export interface WorkspaceOverview {
  teams: Team[];
  projects: Project[];
  managedTeamIds: Set<string>;
}

/** `manageAll`: the workspace admin page — admins and delegated workspace managers see and manage every team. Everything else
 * (sidebar, pickers) keeps the member-scoped view so a manager is not shown projects they cannot open. */
export async function loadWorkspace(user: User, options: { manageAll?: boolean } = {}): Promise<WorkspaceOverview> {
  const isAdmin = user.role === "admin" || user.role === "super_admin" || Boolean(options.manageAll && user.workspace_access);
  const teams = await (isAdmin ? workspaceApi.allTeams() : workspaceApi.myTeams()).catch(() => [] as Team[]);
  const [myProjects, teamProjects, memberships] = await Promise.all([
    workspaceApi.myProjects().catch(() => [] as Project[]),
    Promise.all(teams.map((team) => workspaceApi.teamProjects(team.id).catch(() => [] as Project[]))),
    isAdmin ? Promise.resolve([]) : Promise.all(teams.map((team) => workspaceApi.teamMembers(team.id).catch(() => [] as TeamMembership[]))),
  ]);
  const projects = Array.from(new Map([...myProjects, ...teamProjects.flat()].map((project) => [project.id, project])).values());
  const managedTeamIds = new Set(isAdmin
    ? teams.map((team) => team.id)
    : teams.filter((team, index) => memberships[index]?.some((membership) => membership.user.id === user.id && membership.role === "leader")).map((team) => team.id));
  return { teams, projects, managedTeamIds };
}

/** Whether the caller may use a delegated project permission here: the backend reports the effective set (leaders/admins hold all). */
export const hasProjectPermission = (project: Project | undefined | null, permission: ProjectPermission) => Boolean(project?.my_permissions?.includes(permission));
