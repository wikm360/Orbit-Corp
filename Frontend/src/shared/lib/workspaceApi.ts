import { apiRequest } from "./apiClient";
import type { Project, ProjectMembership, Team, TeamMembership, User, UserRole } from "@/shared/types";

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
  users: () => apiRequest<User[]>("/admin/users"),
  updateUserRole: (userId: string, role: UserRole) => apiRequest<User>(`/admin/users/${userId}/role`, { method: "PATCH", body: { role } }),
};

export interface WorkspaceOverview {
  teams: Team[];
  projects: Project[];
  managedTeamIds: Set<string>;
}

export async function loadWorkspace(user: User): Promise<WorkspaceOverview> {
  const isAdmin = user.role === "admin" || user.role === "super_admin";
  const teams = isAdmin ? await workspaceApi.allTeams() : await workspaceApi.myTeams();
  const [myProjects, teamProjects, memberships] = await Promise.all([
    workspaceApi.myProjects(),
    Promise.all(teams.map((team) => workspaceApi.teamProjects(team.id))),
    isAdmin ? Promise.resolve([]) : Promise.all(teams.map((team) => workspaceApi.teamMembers(team.id))),
  ]);
  const projects = Array.from(new Map([...myProjects, ...teamProjects.flat()].map((project) => [project.id, project])).values());
  const managedTeamIds = new Set(isAdmin
    ? teams.map((team) => team.id)
    : teams.filter((team, index) => memberships[index]?.some((membership) => membership.user.id === user.id && membership.role === "leader")).map((team) => team.id));
  return { teams, projects, managedTeamIds };
}
