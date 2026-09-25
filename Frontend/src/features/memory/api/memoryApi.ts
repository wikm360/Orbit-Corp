import { apiRequest } from "@/shared/lib/apiClient";

import type { ProjectMemory, ProjectMemoryCreate, ProjectMemoryUpdate } from "../types";

function memoryPath(projectId: string, memoryId?: string): string {
  const base = `/projects/${encodeURIComponent(projectId)}/memories`;
  return memoryId ? `${base}/${encodeURIComponent(memoryId)}` : base;
}

export const memoryApi = {
  list: (projectId: string) => apiRequest<ProjectMemory[]>(memoryPath(projectId)),
  create: (projectId: string, payload: ProjectMemoryCreate) =>
    apiRequest<ProjectMemory>(memoryPath(projectId), { method: "POST", body: payload }),
  update: (projectId: string, memoryId: string, payload: ProjectMemoryUpdate) =>
    apiRequest<ProjectMemory>(memoryPath(projectId, memoryId), { method: "PATCH", body: payload }),
  remove: (projectId: string, memoryId: string) =>
    apiRequest<void>(memoryPath(projectId, memoryId), { method: "DELETE" }),
};
