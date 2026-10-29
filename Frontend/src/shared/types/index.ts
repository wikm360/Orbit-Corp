export type UserRole = "super_admin" | "admin" | "user";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  /** Effective access to the Rahkaran accounting tools: super admins always, everyone else only when a super admin granted it. */
  accounting_access: boolean;
  accounting_access_granted_at?: string | null;
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
}

export interface TeamMembership {
  user: User;
  role: "leader" | "member";
}

export interface ProjectMembership {
  user: User;
}
