/** Mirrors the backend contract of `app/features/volume_report` (see Backend/.agents/flows/volume-report.md). Quantities are decimal STRINGS. */

export type PeriodType = "week" | "month";
export type ReportStatus = "draft" | "processing" | "awaiting_user" | "needs_review" | "ready" | "published" | "failed";
export type SiteKind = "road" | "mining" | "other";

export interface Progress { step?: string; done?: number; total?: number; message?: string; agent_step?: number; max_steps?: number }

export interface ReportSummary {
  id: string;
  project_id: string;
  title: string;
  period_type: PeriodType;
  period_start: string;
  period_end: string;
  period_label: string;
  status: ReportStatus;
  progress: Progress;
  version: number;
  supersedes_id: string | null;
  published_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportFileInfo { id: string; document_id: string | null; filename: string; company_id: string; status: "pending" | "parsed" | "failed"; error_message: string | null }
export interface GateCause { code: string; count: number }
export interface CompanyNarrative {
  company_name?: string;
  raw_text: string;
  items: string[];
  updated_at?: string;
}
export interface ReportDetail extends Omit<ReportSummary, "created_at" | "updated_at"> {
  files: ReportFileInfo[];
  issues: GateCause[];
  narratives?: Record<string, CompanyNarrative>;
}

export interface ReportCreate { project_id: string; title: string; period_type: PeriodType; period_start: string; period_end: string; period_label: string }
export interface FileSelection { document_id: string; company_id: string }
export interface SelectedFile { id: string; document_id: string | null; filename: string; company_id: string; status: string; suggested_company: string | null }

export interface ProgressResponse { status: ReportStatus; progress: Progress; error_message: string | null }

export interface SheetLogEntry {
  sheet: string; visibility: string; kind: string; used: boolean; reason: string | null;
  site_name?: string; rows_total?: number; rows_nonzero?: number; rows_nonphysical?: number; header_row?: number | null;
  layout_unknown?: boolean; basis?: "actual" | "planned";
}
export interface SourceWarning { code: string; sheet?: string; row?: number; found?: string[]; expected?: string[]; rows?: number }
export interface SourceInfo { id: string; filename: string; status: string; error_message: string | null; suggested_company: string | null; sheet_log: SheetLogEntry[]; warnings: SourceWarning[] }

export type ResultScope = "holding" | "company" | "site";
export interface ResultRow {
  scope: ResultScope; company_id: string | null; company: string | null; site_id: string | null; site: string | null;
  item_key: string; item: string; decimals: number; sort: number; qty: string; unit: string; n_lines: number; has_unconfirmed: boolean;
}
export type LineEffect =
  | "counted" | "supply_ignored" | "supply_only_not_counted" | "duplicate_ignored" | "excluded" | "unmatched" | "nonphysical"
  | "unit_mismatch" | "no_conversion" | "site_kind_mismatch" | "needs_input";
export interface LineRow {
  line_id: string; document_id: string | null; filename: string; sheet: string; row_no: number; site_id: string; site: string; company: string;
  description: string; unit: string; unit_norm: string; quantity: string; effect: LineEffect; item_key: string | null;
  output_qty: string | null; output_unit: string | null; note: string | null; unconfirmed: boolean; flags: Record<string, unknown>; basis?: "actual" | "planned";
}
export interface ResultsResponse { report_id: string; status: ReportStatus; group_by: ResultScope; rows: ResultRow[]; other?: LineRow[]; problems?: LineRow[]; nonphysical?: LineRow[] }

export interface PlanVsActualRow {
  company: string | null; site: string | null; item_key: string; item: string; unit: string; decimals: number;
  planned: string | null; actual: string | null; variance: string; achievement_pct: string | null;
}
export interface PlanVsActual {
  report_id: string; group_by: ResultScope; rows: PlanVsActualRow[]; next_plan: ResultRow[];
  previous_report: { id: string; title: string; period_label: string; period_start: string; period_end: string; adjacent: boolean } | null;
}

export interface CatalogItem {
  key: string; title_fa: string; description_fa: string; dimension: string; output_unit: string; decimals: number; is_rollup: boolean; rollup_of: string[]; mining_only: boolean;
}

export type Role = "supply" | "execute" | "combined" | "na";
export interface ReviewGroup {
  group_key: string; description: string; unit: string; site_kind: SiteKind; n_lines: number; section_headings: string[]; tokens: string[];
  total_quantity: string; planned_quantity?: string; disposition: string | null; item_key: string | null; role: Role | null; exclude_reason: string | null;
  source: string | null; confirmed: boolean; reason: string | null; confidence: number | null;
}
export interface ConfirmItem {
  group_key: string; item_key?: string | null; exclude_reason?: string | null; disposition?: "unmatched" | "nonphysical" | null;
  role: Role; remember_scope: RememberScope;
}

export type RememberScope = "global" | "line";
export type QuestionKind = "choice" | "multi_choice" | "number" | "text" | "confirm_group";
export type QuestionStatus = "open" | "answered" | "skipped" | "superseded";
export interface QuestionOption { key: string; label: string }
export interface QuestionSpec {
  kind: QuestionKind; prompt: string; group_ids: string[]; options: QuestionOption[];
  number?: { param_key: string; unit: string; min: number; max: number } | null;
  remember_scopes?: RememberScope[]; default_remember?: RememberScope;
  system?: "site_kind" | "no_conversion" | "unit_mismatch" | "layout";
  site_id?: string; item_key?: string | null; sheet?: string; layout?: Record<string, unknown>;
  validation?: { rows: number; nonzero_rows: number; lines: number };
}
export interface Question {
  id: string; kind: QuestionKind; spec: QuestionSpec; group_keys: string[]; impact_score: number; status: QuestionStatus;
  answer: AnswerPayload | null; answered_at: string | null; created_at: string;
}
export interface AnswerPayload { choice_keys: string[]; number?: number | null; text?: string | null; remember_scope: RememberScope }

export interface Company { id: string; name: string; aliases: string[]; is_active: boolean }
export interface Site { id: string; company_id: string; name: string; kind: SiteKind; kind_confirmed: boolean; aliases: string[]; is_active: boolean }
export interface Conversion { id: string; key: string; item_key: string | null; site_id: string | null; value: string; unit: string; note: string | null }
export interface ItemRule {
  id: string; item_key: string | null; site_id: string | null; name: string; phrases: string[]; source_unit: string; factor: string;
  priority: number; note: string | null; is_active: boolean;
}
export interface ItemRuleWrite {
  item_key: string; site_id?: string | null; name: string; phrases: string[]; source_unit: string; factor: number;
  priority?: number; note?: string | null; is_active?: boolean;
}
export interface SettingsItem {
  id: string; key: string; title_fa: string; description_fa: string; dimension: string; output_unit: string; decimals: number; sort_order: number;
  is_rollup: boolean; rollup_of: string[]; mining_only: boolean; is_active: boolean;
}
export type SettingsItemWrite = Omit<SettingsItem, "id">;
export interface LexiconEntry { id: string; token: string; kind: "item_hint" | "role" | "hard_exclusion" | "noise"; phrases: string[]; is_active: boolean }
export interface DecisionRow {
  id: string; description: string; unit: string; site_kind: SiteKind; disposition: string; item_key: string | null; role: Role;
  exclude_reason: string | null; hits: number; source: string; confirmed_at: string | null; revoked_at: string | null; has_embedding: boolean;
}

/** `volume_table` artifact produced by the chat tool `get_volume_report`. */
export interface VolumeTableArtifact {
  type: "volume_table"; version: number; report_id: string; title: string; period: string;
  columns: string[]; rows: string[][]; unit_by_row: string[]; notes: string[];
}

export type ActivityKind = "info" | "step" | "success" | "warn" | "error" | "question";
export interface ActivityItem { id: number; attempt: number; phase: string; kind: ActivityKind; title: string; detail: Record<string, unknown>; created_at: string }
export interface ActivityResponse { status: ReportStatus; progress: Progress; items: ActivityItem[] }

/** EVM summary read from each file (`GET /{id}/evm`). Amounts are rial decimal strings; cpi/spi are null when an operand is missing. */
export interface EvmFigures {
  contract_amount: string | null; bcws: string | null; pv: string | null; ev: string | null; ev_net: string | null; ac: string | null;
  cpi: string | null; spi: string | null;
}
export interface EvmProject extends EvmFigures { project: string | null; filename: string }
export interface EvmTotal extends EvmFigures { projects: number }
export interface EvmCompany {
  company_id: string; company: string; projects: EvmProject[]; total: EvmTotal;
  /** The "جمع" row the file itself printed (only when exactly one file of the company has it). */
  reported_total: (EvmFigures & { projects: number; project: string | null }) | null;
}
export interface EvmBasis { companies: EvmCompany[]; holding: EvmTotal | null }
export interface EvmResponse { report_id: string; actual: EvmBasis; planned: EvmBasis }
