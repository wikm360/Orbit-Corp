import { apiRequest } from "@/shared/lib/apiClient";

import { Document, TeamOption } from "../types";

export const documentsApi = {
  list: () => apiRequest<Document[]>("/documents"),

  myTeams: () => apiRequest<TeamOption[]>("/documents/teams/mine"),

  upload: (teamId: string, file: File) => {
    const formData = new FormData();
    formData.append("team_id", teamId);
    formData.append("file", file);
    return apiRequest<{ document: Document; message: string }>("/documents", {
      method: "POST",
      formData,
    });
  },

  remove: (documentId: string) =>
    apiRequest<void>(`/documents/${documentId}`, { method: "DELETE" }),
};
