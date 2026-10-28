import { apiRequest, uploadRequest } from "@/shared/lib/apiClient";
import {
  BatchUploadResponse,
  BulkResult,
  Document,
  DocumentSearchHit,
  FileSelection,
  Folder,
  FolderListing,
  OnConflict,
} from "../types";
import { batchFormData } from "../lib/batchUpload";

const post = <T>(path: string, body: unknown) => apiRequest<T>(path, { method: "POST", body });

export const documentsApi = {
  list: (projectId: string) => apiRequest<Document[]>(`/projects/${projectId}/documents`),
  /** `onProgress` receives the fraction (0..1) of this request's body already sent. */
  uploadBatch: (projectId: string, files: File[], folderId?: string | null, onProgress?: (fraction: number) => void) =>
    onProgress
      ? uploadRequest<BatchUploadResponse>(`/projects/${projectId}/documents/batch`, batchFormData(files, folderId), onProgress)
      : apiRequest<BatchUploadResponse>(`/projects/${projectId}/documents/batch`, { method: "POST", formData: batchFormData(files, folderId) }),
  retry: (projectId: string, documentId: string) => apiRequest<Document>(`/projects/${projectId}/documents/${documentId}/retry`, { method: "POST" }),
  upload: (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest<{ document: Document; message: string }>(`/projects/${projectId}/documents`, { method: "POST", formData });
  },
  remove: (projectId: string, documentId: string) => apiRequest<void>(`/projects/${projectId}/documents/${documentId}`, { method: "DELETE" }),

  // File manager (project scope)
  listFiles: (projectId: string, folderId: string | null) =>
    apiRequest<FolderListing>(`/projects/${projectId}/files${folderId ? `?folder_id=${encodeURIComponent(folderId)}` : ""}`),
  searchFiles: (projectId: string, query: string) =>
    apiRequest<DocumentSearchHit[]>(`/projects/${projectId}/files/search?q=${encodeURIComponent(query)}`),
  createFolder: (projectId: string, name: string, parentId: string | null) =>
    post<Folder>(`/projects/${projectId}/folders`, { name, parent_id: parentId }),
  renameFolder: (projectId: string, folderId: string, name: string) =>
    apiRequest<Folder>(`/projects/${projectId}/folders/${folderId}`, { method: "PATCH", body: { name } }),
  renameDocument: (projectId: string, documentId: string, filename: string) =>
    apiRequest<Document>(`/projects/${projectId}/documents/${documentId}`, { method: "PATCH", body: { filename } }),
  move: (projectId: string, selection: FileSelection, targetFolderId: string | null, onConflict: OnConflict) =>
    post<BulkResult>(`/projects/${projectId}/files/move`, { ...selection, target_folder_id: targetFolderId, on_conflict: onConflict }),
  copy: (projectId: string, selection: FileSelection, targetFolderId: string | null, onConflict: OnConflict) =>
    post<BulkResult>(`/projects/${projectId}/files/copy`, { ...selection, target_folder_id: targetFolderId, on_conflict: onConflict }),
  deleteItems: (projectId: string, selection: FileSelection) => post<BulkResult>(`/projects/${projectId}/files/delete`, selection),
  retryItems: (projectId: string, selection: FileSelection) => post<BulkResult>(`/projects/${projectId}/files/retry`, selection),
  cancelItems: (projectId: string, selection: FileSelection) => post<BulkResult>(`/projects/${projectId}/files/cancel`, selection),
  dismissArchive: (projectId: string, archiveId: string) => apiRequest<void>(`/projects/${projectId}/archives/${archiveId}`, { method: "DELETE" }),
};
