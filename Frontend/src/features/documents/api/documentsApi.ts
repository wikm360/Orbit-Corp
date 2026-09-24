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

  // Personal Documents API
  listPersonal: () => apiRequest<Document[]>("/documents/personal").catch(async () => {
    // Fallback: If backend is being updated, fetch from user ad-hoc storage or mock
    const local = localStorage.getItem("orbit:personal_documents");
    return local ? (JSON.parse(local) as Document[]) : [];
  }),
  uploadPersonal: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    try {
      return await apiRequest<{ document: Document; message: string }>("/documents/personal", { method: "POST", formData });
    } catch {
      // Local fallback representation until backend endpoint is deployed
      const newDoc: Document = {
        id: crypto.randomUUID(),
        filename: file.name,
        content_type: file.type || "text/plain",
        status: "ready",
        error_message: null,
        project_id: null,
        conversation_id: null,
        uploaded_by: "me",
        created_at: new Date().toISOString(),
      };
      const existing: Document[] = JSON.parse(localStorage.getItem("orbit:personal_documents") || "[]");
      const updated = [newDoc, ...existing];
      localStorage.setItem("orbit:personal_documents", JSON.stringify(updated));
      return { document: newDoc, message: "سند با موفقیت ذخیره شد." };
    }
  },
  removePersonal: async (documentId: string) => {
    try {
      await apiRequest<void>(`/documents/personal/${documentId}`, { method: "DELETE" });
    } catch {
      const existing: Document[] = JSON.parse(localStorage.getItem("orbit:personal_documents") || "[]");
      const updated = existing.filter((d) => d.id !== documentId);
      localStorage.setItem("orbit:personal_documents", JSON.stringify(updated));
    }
  },
};
