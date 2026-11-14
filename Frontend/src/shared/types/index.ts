export type UserRole = "super_admin" | "admin" | "user";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  /** Effective access to the Rahkaran accounting tools: super admins always, everyone else only when a super admin granted it. */
  accounting_access: boolean;
  accounting_access_granted_at?: string | null;
  /** Token quota: `token_limit` null = unlimited (super admins are never limited). */
  token_limit?: number | null;
  tokens_used?: number;
  token_period_start?: string | null;
  created_at: string;
}

export interface Team {
  id: string;
  name: string;
  description: string | null;
}

export interface Project {
  id: string;
  team_id: string;
  name: string;
  description: string | null;
  /** What the caller may do in this project: everything for admins/the team leader, else the delegated permissions. */
  my_permissions?: ProjectPermission[];
}

export interface TokenUsageReport {
  limit: number | null;
  used: number;
  period_start: string;
  by_purpose: { purpose: string; prompt_tokens: number; completion_tokens: number; calls: number; counts_toward_quota: boolean }[];
  daily: { date: string; tokens: number }[];
}

export type QuotaWindowName = "five_hour" | "weekly" | "monthly";

/** One window of a user's dollar quota; `limit_usd` null = no cap. `resets_at` is only set while the window is exhausted. */
export interface QuotaWindow {
  name: QuotaWindowName;
  limit_usd: number | null;
  used_usd: number;
  exhausted: boolean;
  overridden: boolean;
  starts_at: string;
  resets_at: string | null;
}

export interface UserQuota {
  enforced: boolean;
  unlimited: boolean;
  windows: QuotaWindow[];
}

/** The caller's own consumption (GET /auth/me/usage): this Jalali month by purpose, what the setup pool paid, daily cost. */
export interface MyUsage {
  month: { start: string; next_start: string };
  month_used_usd: number;
  setup_pool_usd: number;
  by_purpose: { purpose: string; cost_usd: number; calls: number }[];
  daily: { date: string; cost_usd: number }[];
}

export interface QuotaPlan { five_hour_usd: number; weekly_usd: number; monthly_usd: number }

export interface QuotaOverview {
  enforced: boolean;
  setup_pool: { enabled: boolean; budget_usd: number; used_usd: number; remaining_usd: number };
  org: { monthly_cap_usd: number | null; month_used_usd: number; percent: number | null };
  plans: Record<string, QuotaPlan>;
  month: { start: string; next_start: string };
}

export interface ModelPrice { model: string; input_per_m: number; output_per_m: number; per_page_usd: number | null; updated_at: string }

export interface CostSummary {
  days: number;
  total_usd: number;
  by_purpose: { purpose: string; calls: number; cost_usd: number }[];
  by_model: { model: string; calls: number; cost_usd: number }[];
  by_user: { user_id: string; email: string; calls: number; cost_usd: number }[];
}

export type ProjectPermission = "documents" | "memory";

export interface TeamMembership {
  user: User;
  role: "leader" | "member";
}

export interface ProjectMembership {
  user: User;
  permissions?: ProjectPermission[];
}

/** Organisation identity (GET /branding, public). `palette` holds space-separated RGB triplets per shade for the CSS variables. */
export interface Branding {
  name: string;
  short_name: string;
  app_title: string;
  description: string;
  tagline: string;
  product_label: string;
  login_headline: string;
  login_footer: string;
  colors: { brand: string; accent: string; highlight: string };
  palette: { brand: Record<string, string>; accent: Record<string, string>; teal: Record<string, string>; ground: { base: string; button: string } };
  logo_url: string | null;
  updated_at: string | null;
}
