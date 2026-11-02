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

export type ProjectPermission = "documents" | "memory";

export interface TeamMembership {
  user: User;
  role: "leader" | "member";
}

export interface ProjectMembership {
  user: User;
  permissions?: ProjectPermission[];
}
