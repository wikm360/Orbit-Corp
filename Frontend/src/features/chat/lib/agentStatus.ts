import type { AgentStatus, AgentStep } from "../types";

export type ToolIconName =
  | "spark"
  | "document"
  | "search"
  | "memory"
  | "folder"
  | "edit"
  | "check"
  | "eye"
  | "database";

const TOOL_LABELS: Record<string, string> = {
  search_knowledge_base: "جست‌وجو در پایگاه دانش",
  get_document_info: "بررسی مشخصات و اطلاعات سند",
  read_document_pages: "خواندن صفحه‌های سند",
  read_entire_document: "مطالعهٔ کامل سند",
  view_document_page: "بررسی بصری تصویر/نقشهٔ صفحه سند",
  describe_spreadsheet: "بررسی ساختار و ستون‌های شیت اکسل",
  query_spreadsheet: "کوئری و تحلیل داده‌های اکسل",
  browse_folder: "پیمایش پوشه‌ها و فایل‌های پروژه",
  list_user_projects: "بررسی پروژه‌های شما",
  get_current_chat_attachments: "بررسی پیوست‌های گفتگو",
  recall_project_insights: "مرور حافظهٔ پروژه",
  remember_project_insight: "ذخیرهٔ نکته در حافظهٔ پروژه",
  ask_accounting_db: "پرس‌وجو از پایگاه داده‌ی مالی راهکاران",
  // Legacy aliases for backward compatibility:
  get_document_outline: "بررسی فهرست و ساختار سند",
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
  if (activity.status === "preparing") return "در حال آماده‌سازی و بررسی درخواست";
  if (activity.tool && TOOL_LABELS[activity.tool]) return TOOL_LABELS[activity.tool]!;
  if (activity.status === "searching") return "جست‌وجو و بررسی اطلاعات";
  if (activity.status === "reading_documents") return "در حال خواندن اسناد";
  if (activity.status === "querying_database") return "در حال پرس‌وجو از پایگاه داده‌ی مالی";
  // Older servers send a Persian sentence instead of a status code.
  if (/[\u0600-\u06ff]/.test(activity.status)) return activity.status;
  return "در حال بررسی درخواست شما";
}

export function agentStatusDetail(activity: AgentStatus): string | undefined {
  const args = activity.args;
  if (!args || typeof args !== "object") return undefined;

  switch (activity.tool) {
    case "search_knowledge_base": {
      const parts: string[] = [];
      if (typeof args.query === "string" && args.query.trim()) {
        parts.push(`«${args.query.trim()}»`);
      }
      if (typeof args.path_prefix === "string" && args.path_prefix.trim()) {
        parts.push(`در پوشهٔ «${args.path_prefix.trim()}»`);
      }
      return parts.length > 0 ? parts.join(" - ") : undefined;
    }
    case "read_document_pages": {
      const parts: string[] = [];
      if (args.start_page !== undefined && args.end_page !== undefined) {
        if (args.start_page === args.end_page) {
          parts.push(`صفحهٔ ${args.start_page}`);
        } else {
          parts.push(`صفحه‌های ${args.start_page} تا ${args.end_page}`);
        }
      }
      if (typeof args.filename === "string") {
        parts.push(`سند: ${args.filename}`);
      } else if (typeof args.document_id === "string") {
        parts.push(`سند: ${args.document_id.slice(0, 8)}...`);
      }
      return parts.length > 0 ? parts.join(" - ") : undefined;
    }
    case "view_document_page": {
      const parts: string[] = [];
      if (args.page_number !== undefined) {
        parts.push(`تصویر صفحهٔ ${args.page_number}`);
      }
      if (typeof args.filename === "string") {
        parts.push(`از ${args.filename}`);
      }
      return parts.length > 0 ? parts.join(" - ") : undefined;
    }
    case "get_document_info":
    case "read_entire_document": {
      if (typeof args.filename === "string") return `سند: ${args.filename}`;
      if (typeof args.document_id === "string") return `شناسه سند: ${args.document_id.slice(0, 8)}...`;
      return undefined;
    }
    case "browse_folder": {
      if (typeof args.path === "string" && args.path.trim()) {
        return `مسیر: «${args.path.trim()}»`;
      }
      return "پوشهٔ ریشه (سطح اول)";
    }
    case "describe_spreadsheet": {
      if (typeof args.sheet === "string" && args.sheet.trim()) {
        return `شیت: «${args.sheet.trim()}»`;
      }
      return "بررسی کلیهٔ شیت‌ها و ستون‌ها";
    }
    case "query_spreadsheet": {
      if (typeof args.sql === "string" && args.sql.trim()) {
        const sql = args.sql.trim();
        return `SQL: ${sql.slice(0, 50)}${sql.length > 50 ? "..." : ""}`;
      }
      return undefined;
    }
    case "recall_project_insights": {
      if (typeof args.query === "string" && args.query.trim()) {
        return `موضوع: «${args.query.trim()}»`;
      }
      return undefined;
    }
    case "remember_project_insight": {
      if (typeof args.fact === "string" && args.fact.trim()) {
        return `نکته: «${args.fact.trim().slice(0, 50)}...»`;
      }
      return undefined;
    }
    case "ask_accounting_db": {
      if (typeof args.question === "string" && args.question.trim()) {
        return `پرسش مالی: «${args.question.trim()}»`;
      }
      return undefined;
    }
    default:
      return undefined;
  }
}

export function agentToolIcon(tool?: string, status?: string): ToolIconName {
  if (tool === "browse_folder") return "folder";
  if (tool === "search_knowledge_base" || status === "searching") return "search";
  if (
    tool === "read_document_pages" ||
    tool === "read_entire_document" ||
    tool === "get_document_info" ||
    tool === "get_document_outline" ||
    status === "reading_documents"
  ) {
    return "document";
  }
  if (tool === "view_document_page") return "eye";
  if (tool === "describe_spreadsheet" || tool === "query_spreadsheet") return "edit";
  if (tool === "recall_project_insights" || tool === "remember_project_insight") return "memory";
  if (tool === "ask_accounting_db" || status === "querying_database") return "database";
  if (tool === "list_user_projects" || tool === "get_current_chat_attachments") return "folder";
  return "spark";
}

export function recordAgentStep(
  existingSteps: AgentStep[] = [],
  status: AgentStatus
): AgentStep[] {
  const label = agentStatusLabel(status);
  const detail = agentStatusDetail(status);

  // If last step is identical, don't duplicate
  const last = existingSteps[existingSteps.length - 1];
  if (
    last &&
    last.status === status.status &&
    last.tool === status.tool &&
    last.label === label &&
    last.detail === detail
  ) {
    return existingSteps;
  }

  // Mark all previous running steps as completed
  const updated = existingSteps.map((s) =>
    s.state === "running" ? { ...s, state: "completed" as const } : s
  );

  const newStep: AgentStep = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    status: status.status,
    tool: status.tool,
    args: status.args,
    label,
    detail,
    state: "running",
    timestamp: Date.now(),
  };

  return [...updated, newStep];
}

export function completeAgentSteps(steps: AgentStep[]): AgentStep[] {
  return steps.map((s) => (s.state === "running" ? { ...s, state: "completed" as const } : s));
}

export function failAgentSteps(steps: AgentStep[]): AgentStep[] {
  return steps.map((s) => (s.state === "running" ? { ...s, state: "failed" as const } : s));
}
