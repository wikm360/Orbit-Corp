import type { AgentStatus } from "../types";

const TOOL_LABELS: Record<string, string> = {
  search_knowledge_base: "جست‌وجو در پایگاه دانش",
  list_user_projects: "بررسی پروژه‌های شما",
  recall_project_insights: "مرور حافظهٔ پروژه",
  remember_project_insight: "ذخیرهٔ نکته در حافظهٔ پروژه",
  get_document_outline: "بررسی فهرست و ساختار سند",
  read_document_pages: "خواندن صفحه‌های سند",
  read_entire_document: "مطالعهٔ کامل سند",
  get_current_chat_attachments: "بررسی پیوست‌های گفتگو",
  list_project_documents: "بررسی اسناد پروژه",
};

export function normalizeAgentStatus(value: unknown): AgentStatus | null {
  if (typeof value === "string") return { status: value };
  if (!value || typeof value !== "object" || !("status" in value) || typeof value.status !== "string") return null;
  const payload = value as Record<string, unknown>;
  return {
    status: payload.status as string,
    ...(typeof payload.tool === "string" ? { tool: payload.tool } : {}),
    ...(payload.args && typeof payload.args === "object" && !Array.isArray(payload.args)
      ? { args: payload.args as Record<string, unknown> } : {}),
  };
}

export function agentStatusLabel(activity: AgentStatus): string {
  if (activity.status === "generating") return "در حال نوشتن پاسخ";
  if (activity.tool && TOOL_LABELS[activity.tool]) return TOOL_LABELS[activity.tool]!;
  if (activity.status === "searching") return "جست‌وجو و بررسی اطلاعات";
  if (activity.status === "reading_documents") return "در حال خواندن اسناد";
  // Older servers send a Persian sentence instead of a status code.
  if (/[\u0600-\u06ff]/.test(activity.status)) return activity.status;
  return "در حال بررسی درخواست شما";
}
