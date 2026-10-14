import { apiRequest } from "@/shared/lib/apiClient";
import { BatchUploadResponse, Document } from "../types";
import { batchFormData } from "../lib/batchUpload";

export const documentsApi = {
  list: (projectId: string) => apiRequest<Document[]>(`/projects/${projectId}/documents`),
  uploadBatch: (projectId: string, files: File[]) => apiRequest<BatchUploadResponse>(`/projects/${projectId}/documents/batch`, { method: "POST", formData: batchFormData(files) }),
  retry: (projectId: string, documentId: string) => apiRequest<Document>(`/projects/${projectId}/documents/${documentId}/retry`, { method: "POST" }),
  upload: (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest<{ document: Document; message: string }>(`/projects/${projectId}/documents`, { method: "POST", formData });
  },
  remove: (projectId: string, documentId: string) => apiRequest<void>(`/projects/${projectId}/documents/${documentId}`, { method: "DELETE" }),

  // Personal Documents API
  listPersonal: () => apiRequest<Document[]>("/documents/personal"),
  uploadPersonal: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest<{ document: Document; message: string }>("/documents/personal", { method: "POST", formData });
  },
  removePersonal: (documentId: string) => apiRequest<void>(`/documents/personal/${documentId}`, { method: "DELETE" }),
};
