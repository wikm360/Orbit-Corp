export type UserRole = "super_admin" | "admin" | "user";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
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
