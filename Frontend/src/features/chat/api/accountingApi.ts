import { ApiError, apiRequest, authorizedFetch, parseErrorMessage } from "@/shared/lib/apiClient";

export type ExportFormat = "xlsx" | "csv";

export const accountingApi = {
  /** feedback: 1 = helpful, -1 = wrong/unhelpful, 0 = clear. */
  sendFeedback: (queryId: string, feedback: -1 | 0 | 1, note?: string) =>
    apiRequest<unknown>(`/accounting-db/queries/${queryId}/feedback`, { method: "POST", body: { feedback, ...(note ? { note } : {}) } }),

  /** Downloads the full result (up to the server export cap) as an Excel/CSV file. */
  async downloadExport(queryId: string, format: ExportFormat): Promise<void> {
    const response = await authorizedFetch(`/accounting-db/queries/${queryId}/export?format=${format}`);
    if (!response.ok) throw new ApiError(response.status, await parseErrorMessage(response));
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `accounting-result-${queryId.slice(0, 8)}.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};
