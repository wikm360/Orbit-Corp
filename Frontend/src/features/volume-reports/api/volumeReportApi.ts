import { API_BASE_URL, ApiError, apiRequest, authorizedFetch, parseErrorMessage } from "@/shared/lib/apiClient";

import type {
  AnswerPayload, CatalogItem, Company, ConfirmItem, Conversion, DecisionRow, FileSelection, LexiconEntry, LineRow, Question,
  ReportCreate, ReportDetail, ReportStatus, ReportSummary, ResultScope, ResultsResponse, ReviewGroup, SelectedFile, SettingsItem,
  SettingsItemWrite, Site, SiteKind, SourceInfo, ProgressResponse, GateCause, ActivityResponse,
} from "../types";

const BASE = "/volume-reports";
const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const usable = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return usable.length ? `?${new URLSearchParams(usable.map(([k, v]) => [k, String(v)])).toString()}` : "";
};
const send = <T>(path: string, method: string, body?: unknown) => apiRequest<T>(`${BASE}${path}`, { method, body });

export type ExportFormat = "xlsx" | "csv";

export const volumeReportApi = {
  catalog: () => apiRequest<CatalogItem[]>(`${BASE}/catalog`),
  list: (projectId: string, status?: ReportStatus) => apiRequest<ReportSummary[]>(`${BASE}${qs({ project_id: projectId, status })}`),
  create: (payload: ReportCreate) => send<ReportSummary>("", "POST", payload),
  get: (id: string) => apiRequest<ReportDetail>(`${BASE}/${id}`),
  remove: (id: string) => send<void>(`/${id}`, "DELETE"),
  setFiles: (id: string, files: FileSelection[]) => send<SelectedFile[]>(`/${id}/files`, "PUT", { files }),
  run: (id: string) => send<ReportSummary>(`/${id}/run`, "POST"),
  continueRun: (id: string) => send<ReportSummary>(`/${id}/continue`, "POST"),
  recompute: (id: string) => send<{ issues: GateCause[] }>(`/${id}/recompute`, "POST"),
  progress: (id: string) => apiRequest<ProgressResponse>(`${BASE}/${id}/progress`),
  activity: (id: string, afterId = 0) => apiRequest<ActivityResponse>(`${BASE}/${id}/activity${qs({ after_id: afterId || undefined })}`),
  sources: (id: string) => apiRequest<SourceInfo[]>(`${BASE}/${id}/sources`),
  questions: (id: string, status?: string) => apiRequest<Question[]>(`${BASE}/${id}/questions${qs({ status })}`),
  answer: (id: string, questionId: string, payload: AnswerPayload) => send<Question>(`/${id}/questions/${questionId}/answer`, "POST", payload),
  skip: (id: string, questionId: string) => send<Question>(`/${id}/questions/${questionId}/skip`, "POST"),
  groups: (id: string, state: "unconfirmed" | "needs_input" | "all" = "unconfirmed") => apiRequest<ReviewGroup[]>(`${BASE}/${id}/review/groups${qs({ state })}`),
  confirm: (id: string, items: ConfirmItem[]) => send<{ issues: GateCause[] }>(`/${id}/review/confirm`, "POST", { items }),
  results: (id: string, groupBy: ResultScope, include: string[] = []) =>
    apiRequest<ResultsResponse>(`${BASE}/${id}/results${qs({ group_by: groupBy, include: include.join(",") })}`),
  lines: (id: string, filter: { site_id?: string; item_key?: string; effect?: string; limit?: number; offset?: number }) =>
    apiRequest<LineRow[]>(`${BASE}/${id}/lines${qs(filter)}`),
  trace: (id: string, itemKey: string, siteId?: string) => apiRequest<LineRow[]>(`${BASE}/${id}/trace${qs({ item_key: itemKey, site_id: siteId })}`),
  publish: (id: string) => send<ReportSummary>(`/${id}/publish`, "POST"),
  reopen: (id: string) => send<ReportSummary>(`/${id}/reopen`, "POST"),

  async downloadExport(id: string, format: ExportFormat): Promise<void> {
    const response = await authorizedFetch(`${BASE}/${id}/export${qs({ format })}`);
    if (!response.ok) throw new ApiError(response.status, await parseErrorMessage(response));
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `volume-report-${id.slice(0, 8)}.${format}`;
    link.click();
    URL.revokeObjectURL(url);
  },

  settings: {
    companies: () => apiRequest<Company[]>(`${BASE}/settings/companies`),
    createCompany: (name: string) => send<Company>("/settings/companies", "POST", { name, aliases: [], is_active: true }),
    updateCompany: (id: string, company: Omit<Company, "id">) => send<Company>(`/settings/companies/${id}`, "PUT", company),
    sites: (companyId?: string) => apiRequest<Site[]>(`${BASE}/settings/sites${qs({ company_id: companyId })}`),
    updateSite: (id: string, patch: { kind?: SiteKind; kind_confirmed?: boolean; is_active?: boolean }) => send<Site>(`/settings/sites/${id}`, "PUT", patch),
    conversions: () => apiRequest<Conversion[]>(`${BASE}/settings/conversions`),
    saveConversion: (payload: { key: string; item_key?: string | null; site_id?: string | null; value: number; unit: string; note?: string | null }) =>
      send<Conversion>("/settings/conversions", "PUT", payload),
    items: () => apiRequest<SettingsItem[]>(`${BASE}/settings/items`),
    createItem: (item: SettingsItemWrite) => send<SettingsItem>("/settings/items", "POST", item),
    updateItem: (item: SettingsItemWrite) => send<SettingsItem>(`/settings/items/${item.key}`, "PUT", item),
    lexicon: () => apiRequest<LexiconEntry[]>(`${BASE}/settings/lexicon`),
    createLexicon: (entry: Omit<LexiconEntry, "id">) => send<LexiconEntry>("/settings/lexicon", "POST", entry),
    updateLexicon: (entry: Omit<LexiconEntry, "id">) => send<LexiconEntry>(`/settings/lexicon/${entry.token}`, "PUT", entry),
    decisions: (q?: string, includeRevoked = false) => apiRequest<DecisionRow[]>(`${BASE}/settings/decisions${qs({ q, include_revoked: includeRevoked || undefined })}`),
    revokeDecision: (id: string) => send<{ id: string; revoked_at: string }>(`/settings/decisions/${id}/revoke`, "POST"),
  },
};

/**
 * Probe for "is the module switched on?": the backend mounts the router only when VOLUME_REPORT_ENABLED, so when it is off
 * `/volume-reports/catalog` is a plain 404 (a signed-in user always gets 200 otherwise). There is no explicit flag in `/auth/me`.
 */
export async function probeVolumeReports(): Promise<boolean> {
  try {
    const response = await authorizedFetch(`${BASE}/catalog`);
    return response.ok;
  } catch {
    return false;
  }
}

export { API_BASE_URL };
