import { apiRequest } from "@/shared/lib/apiClient";
import { Document } from "@/features/documents/types";

import { Team, UserWithTeams } from "../types";

export const adminApi = {
  listUsers: () => apiRequest<UserWithTeams[]>("/admin/users"),
  listTeams: () => apiRequest<Team[]>("/admin/teams"),
  createTeam: (name: string) =>
    apiRequest<Team>("/admin/teams", { method: "POST", body: { name } }),
  assignUserToTeam: (userId: string, teamId: string) =>
    apiRequest<void>("/admin/team-memberships", {
      method: "POST",
      body: { user_id: userId, team_id: teamId },
    }),
  listAllDocuments: () => apiRequest<Document[]>("/admin/documents"),
};
