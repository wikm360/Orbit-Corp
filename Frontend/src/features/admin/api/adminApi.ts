import { apiRequest } from "@/shared/lib/apiClient";
import { Document } from "@/features/documents/types";
import { User } from "@/shared/types";
import { workspaceApi } from "@/shared/lib/workspaceApi";

export const adminApi = {
  listUsers: workspaceApi.users,
  listTeams: workspaceApi.allTeams,
  createTeam: workspaceApi.createTeam,
  teamMembers: workspaceApi.teamMembers,
  assignUserToTeam: workspaceApi.addTeamMember,
  removeUserFromTeam: workspaceApi.removeTeamMember,
  setUserRole: workspaceApi.updateUserRole,
  listAllDocuments: () => apiRequest<Document[]>("/admin/documents"),
};

export type AdminUser = User;
