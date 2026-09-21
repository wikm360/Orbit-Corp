import { apiRequest } from "@/shared/lib/apiClient";
import { Document } from "../types";

export const documentsApi = {
  list: (projectId: string) => apiRequest<Document[]>(`/projects/${projectId}/documents`),
  upload: (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest<{ document: Document; message: string }>(`/projects/${projectId}/documents`, { method: "POST", formData });
  },
  remove: (projectId: string, documentId: string) => apiRequest<void>(`/projects/${projectId}/documents/${documentId}`, { method: "DELETE" }),
};
